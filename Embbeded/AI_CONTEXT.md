# Contexto del Proyecto - Firmware IoT para Nodo de Adquisición Ambiental

> **ARCHIVO EXCLUSIVO PARA IA / CODING AGENTS**
> Este documento proporciona contexto esencial del proyecto para evitar errores de planeación e implementación.

---

## 1. Entorno de Ejecución

### Hardware Target
- **Dispositivo**: Raspberry Pi Pico W2
- **Microcontrolador**: RP2040 (Dual-core ARM Cortex-M0+)
- **Conectividad**: WiFi 2.4 GHz integrado
- **Sensor Principal**: Sensirion SCD41 (CO2, Temperatura, Humedad Relativa)
- **Interfaz de Sensor**: I2C (SDA=GPIO0, SCL=GPIO1, frecuencia 100kHz)

### Software Runtime
- **Sistema Operativo**: MicroPython (firmware optimizado para microcontroladores)
- **Versión Python**: Compatible con sintaxis Python 3.x básica
- **Limitaciones**:
  - No disponible CPython stdlib completo
  - Módulos específicos de MicroPython (prefijo `u`: `ujson`, `urequests`, `utime`)
  - RAM limitada (~264 KB usables)
  - No hay sistema de archivos completo (solo almacenamiento flash interno)

---

## 2. Estructura del Proyecto

### Directorio `src/` (Código de Producción)
**IMPORTANTE**: Los archivos dentro de `src/` son el código que **SE COPIA A LA RASPBERRY PI PICO W2**.

Contenido:
```
src/
├── main.py                      # Punto de entrada principal del firmware
├── device_config.py             # Gestión de configuración persistente (JSON)
├── sensor_scd41.py              # Driver del sensor SCD41
├── remote_questdb_service.py    # Cliente para enviar datos a QuestDB
├── timer_service.py             # Sincronización NTP y gestión de timestamps
├── wifi.py                      # Manejo de conexión WiFi multi-red
├── scd4x.py                     # Librería de bajo nivel para SCD4x
└── index.html                   # Interfaz web de configuración/monitoreo
```

**Workflow de despliegue**:
1. Desarrollar/modificar código en `src/`
2. Copiar archivos de `src/` a la Raspberry Pi Pico W2 (via USB/Thonny/mpremote)
3. La Raspberry ejecuta `main.py` automáticamente al encenderse

### Archivos en la Raíz (Código de Pruebas Locales)
**IMPORTANTE**: Estos archivos **NO se copian a la Raspberry**, son solo para desarrollo/pruebas en PC local.

- `questdb_test/`: Scripts para probar conexión a QuestDB desde PC
- `timer_service_test/`: Pruebas del servicio de tiempo
- `main_wifi_debug.py`: Debug de WiFi en PC
- `.venv/`, `poetry.lock`, `pyproject.toml`: Entorno de desarrollo Python local

**Propósito**: Afinar algoritmos y probar lógica en PC antes de desplegar a la Raspberry.

---

## 3. Arquitectura de Software

### Flujo Principal (Loop en `main.py:384-403`)
```
1. Mantener conexión WiFi activa (auto-reconexión)
2. Leer sensor SCD41 cada SAMPLE_INTERVAL (5 min por defecto)
3. Enviar datos a QuestDB cada QUESTDB_INTERVAL (20 min por defecto)
4. Atender peticiones HTTP del servidor web embebido (puerto 80)
```

### Gestión de Configuración (`device_config.py`)
- Configuración persistente en archivo JSON (`device_config.json`)
- Campos clave:
  - `board_id`: MAC address (identificador único del dispositivo)
  - `deployment_id`: ID del deployment actual (formato: `{board_id}_{counter:03d}`)
  - `latitude`, `longitude`, `location_name`: Ubicación del dispositivo
  - `sample_interval`: Intervalo de muestreo del sensor (segundos)
  - `questdb_interval`: Intervalo de envío a QuestDB (segundos)
  - `device_registered`: Flag de registro en QuestDB

### Sincronización de Tiempo (`timer_service.py`)
- Sincronización NTP al inicio (servidor: `pool.ntp.org`)
- Timestamps siempre en **UTC** (nanosegundos para QuestDB)
- Offset UTC configurable para visualización local
- Re-sincronización cada 6 horas

### Adquisición de Datos (`sensor_scd41.py`)
- Sensor opera en modo de medición periódica (hardware: ~5s por lectura)
- Software lee datos cada `SAMPLE_INTERVAL` (configurable)
- Warm-up de 30s al inicio (errores ignorados)
- Tolerancia a fallas de I2C (mantiene última lectura válida)
- Datos retornados: `{co2, temp, rh, last_ok, errors, sample_interval}`

---

## 4. Integración con QuestDB

### Servidor QuestDB
- **Host**: 187.124.90.77 (VPS Hostinger)
- **Puerto**: 9000
- **Endpoint de escritura**: `http://187.124.90.77:9000/write`
- **Protocolo**: ILP (Influx Line Protocol)
- **Método HTTP**: POST con `Content-Type: text/plain`

### Arquitectura de 3 Tablas

#### Tabla 1: `devices`
**Propósito**: Registro único de cada dispositivo IoT

**Esquema**:
- `board_id` (tag): MAC address del dispositivo
- `sensor_type` (tag): Tipo de sensor (ej: "SCD41")
- `registered` (field, integer): Flag de registro (1i)
- `timestamp` (designated timestamp): Nanosegundos UTC

**Escritura**: Una sola vez por dispositivo (función `register_device()`)

**Ejemplo ILP**:
```
devices,board_id=28CDC3F8AFC0,sensor_type=SCD41 registered=1i 1704127800000000000
```

#### Tabla 2: `deployments`
**Propósito**: Historial de ubicaciones/despliegues del dispositivo

**Esquema**:
- `deployment_id` (tag): ID único del deployment (ej: "28CDC3F8AFC0_001")
- `board_id` (tag): Referencia al dispositivo
- `latitude` (field, float): Latitud en grados decimales
- `longitude` (field, float): Longitud en grados decimales
- `location_name` (field, string): Nombre descriptivo del lugar
- `timestamp` (designated timestamp): Nanosegundos UTC

**Escritura**: Cada vez que se cambia la ubicación del dispositivo

**Ejemplo ILP**:
```
deployments,deployment_id=28CDC3F8AFC0_001,board_id=28CDC3F8AFC0 latitude=6.2476,longitude=-75.5658,location_name="Laboratorio Principal" 1704127800000000000
```

#### Tabla 3: `telemetry`
**Propósito**: Datos ambientales capturados por el sensor

**Esquema**:
- `deployment_id` (tag): Referencia al deployment actual
- `co2` (field, float): Concentración de CO2 en ppm
- `temp` (field, float): Temperatura en °C
- `rh` (field, float): Humedad relativa en %
- `errors` (field, integer): Contador de errores del sensor
- `timestamp` (designated timestamp): Nanosegundos UTC

**Escritura**: Cada `questdb_interval` segundos (20 min por defecto)

**Ejemplo ILP**:
```
telemetry,deployment_id=28CDC3F8AFC0_001 co2=450.0,temp=23.5,rh=58.2,errors=0i 1704127800000000000
```

### Relación entre Tablas
```
devices (1) ----< (N) deployments (1) ----< (N) telemetry
   ^                      ^
   |                      |
board_id         deployment_id
```

### Flujo de Registro y Deployment
1. **Primera ejecución del dispositivo**:
   - Obtener `board_id` (MAC address)
   - Registrar en tabla `devices` (una sola vez)
   - Crear deployment inicial en tabla `deployments`
   - Guardar `deployment_id` en `device_config.json`

2. **Cambio de ubicación** (via endpoint `/device/config`):
   - Generar nuevo `deployment_id` (incrementar counter)
   - Crear nueva entrada en tabla `deployments`
   - Actualizar `device_config.json`

3. **Envío de telemetría**:
   - Leer datos del sensor
   - Insertar en tabla `telemetry` con `deployment_id` actual
   - Timestamp UTC sincronizado con NTP

---

## 5. API REST Embebida

El firmware expone un servidor HTTP en puerto 80 con los siguientes endpoints:

### Endpoints Disponibles

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/` o `/index` | GET | Interfaz web de configuración (HTML) |
| `/data` | GET | Últimas lecturas del sensor (JSON) |
| `/wifi` | GET | Información WiFi actual (JSON) |
| `/wifi/scan` | GET | Escanear redes WiFi cercanas (JSON) |
| `/questdb` | GET | Estadísticas de envío a QuestDB (JSON) |
| `/time` | GET | Estado de sincronización NTP (JSON) |
| `/device/config` | GET | Configuración del dispositivo (JSON) |
| `/device/config` | POST | Crear nuevo deployment con ubicación |
| `/config` | GET | Intervalos de muestreo/envío (JSON) |
| `/config` | POST | Cambiar intervalos de muestreo/envío |

**Ejemplo de uso**: `http://<IP_DEL_PICO>/data`

---

## 6. Consideraciones para Coding Agents

### ✅ HACER

1. **Usar sintaxis MicroPython**:
   - Importar módulos con prefijo `u`: `ujson`, `urequests`, `utime`
   - Usar `machine.Pin`, `machine.I2C` para hardware
   - Timestamps en nanosegundos para QuestDB: `timer_service.get_timestamp_ns()`

2. **Modificar solo archivos en `src/`**:
   - El código de producción vive en `src/`
   - Archivos fuera de `src/` son solo para pruebas locales

3. **Gestión de errores**:
   - WiFi puede desconectarse → usar `ensure_connected()`
   - Sensor puede fallar temporalmente → mantener última lectura válida
   - QuestDB puede estar offline → incrementar `_error_count`, no bloquear

4. **Configuración persistente**:
   - Usar `device_config.py` para configuraciones que deben sobrevivir reinicios
   - Guardar cambios con `save_config()`

### ❌ NO HACER

1. **No usar librerías de CPython estándar**:
   - ❌ `import json` → ✅ `import ujson as json`
   - ❌ `import requests` → ✅ `import urequests`
   - ❌ `import datetime` → ✅ usar `timer_service`

2. **No asumir filesystem completo**:
   - No hay `/tmp/`, `/var/`, etc.
   - Solo flash interno limitado (~2 MB)

3. **No crear archivos nuevos innecesarios**:
   - RAM limitada
   - Preferir editar código existente

4. **No usar threading/multiprocessing**:
   - MicroPython tiene threading limitado
   - Loop principal es single-threaded

5. **No hardcodear timestamps**:
   - Siempre usar `timer_service.get_timestamp_ns()` para QuestDB
   - Siempre usar `timer_service.get_current_epoch_utc()` para lógica de intervalos

---

## 7. Workflow de Desarrollo Recomendado

1. **Entender el contexto** (leer este archivo)
2. **Analizar el código existente** en `src/`
3. **Probar algoritmos localmente** (usar scripts en raíz si es necesario)
4. **Implementar cambios en `src/`** (código de producción)
5. **Considerar limitaciones de MicroPython** (RAM, módulos disponibles)
6. **Probar en Raspberry Pi Pico W2** (copiar archivos de `src/`)

---

## 8. Comandos Útiles para Despliegue

### Copiar archivos a la Raspberry Pi Pico W2
```bash
# Con mpremote (recomendado)
mpremote connect /dev/ttyACM0 fs cp src/main.py :main.py
mpremote connect /dev/ttyACM0 fs cp src/device_config.py :device_config.py
# ... (copiar todos los archivos de src/)

# Con Thonny IDE (interfaz gráfica)
# Drag & drop archivos desde src/ a la Raspberry Pi
```

### Ver logs en tiempo real
```bash
mpremote connect /dev/ttyACM0 repl
# O usar Thonny IDE → View → Plotter
```

### Resetear configuración
```python
# Desde REPL de MicroPython
>>> import device_config
>>> device_config.reset_config()
>>> import machine
>>> machine.reset()
```

---

## 9. Referencias Rápidas

### Intervalos Configurables
- `sample_interval`: Frecuencia de lectura del sensor (5 min default)
- `questdb_interval`: Frecuencia de envío a QuestDB (20 min default)
- Ambos configurables via `/config` endpoint (POST)

### Identificadores Únicos
- `board_id`: MAC address (ej: "28CDC3F8AFC0") - fijo por dispositivo
- `deployment_id`: `{board_id}_{counter:03d}` (ej: "28CDC3F8AFC0_001") - cambia con ubicación

### Datos del Sensor SCD41
- **CO2**: 400-5000 ppm (precisión ±30 ppm)
- **Temperatura**: -10 a 60°C (precisión ±0.8°C)
- **Humedad Relativa**: 0-100% (precisión ±6%)
- **Tiempo de respuesta**: ~60 segundos para CO2 estable

---

**Última actualización**: 2026-04-10
**Versión del firmware**: MVP 1.0
**Autor**: FronteraDataLabs - TropicoVentures
