# Firmware IoT - Frontera DataLabs

Guia principal para preparar y operar un nodo ambiental con **Raspberry Pi Pico 2 W**, sensor **SCD41** y MicroPython. El objetivo es que una persona nueva pueda dejar un nodo midiendo sin asistencia: preparar hardware, copiar firmware, configurar WiFi, entrar a la UI local y crear un deployment.

El firmware que se copia a la placa vive en [`src/`](src/).

## Que vas a lograr

Al terminar esta guia tendras:

1. Una Pico 2 W con MicroPython instalado.
2. El firmware copiado en la raiz del filesystem de la placa.
3. Un nombre unico de board.
4. Una red WiFi guardada.
5. Acceso local a la UI del nodo en modo setup o modo STA.
6. Un deployment con nombre, latitud y longitud.

## Compra y preparacion

Hardware minimo:

- Raspberry Pi Pico 2 W.
- Sensor SCD41 en breakout.
- Cable USB de datos.
- Cables Dupont o soldadura para I2C.
- Fuente USB estable.
- PC con Thonny, PyCharm con soporte MicroPython, `mpremote` o una herramienta equivalente.

Conexiones funcionales:

| Senal | Pico 2 W | SCD41 breakout | Notas |
|---|---|---|---|
| Alimentacion 3.3V | `3V3(OUT)` | `VCC` | Alimentacion del modulo |
| Tierra | `GND` | `GND` | Tierra comun |
| I2C SDA | `GP0` | `SDA` | Definido en `sensor_scd41.py` |
| I2C SCL | `GP1` | `SCL` | Definido en `sensor_scd41.py` |

Tambien puedes revisar el diagrama en [`docs/hardware/wiring.svg`](docs/hardware/wiring.svg). La fuente editable vive en [`docs/hardware/wiring.yaml`](docs/hardware/wiring.yaml).

## Mapa mental del nodo

El nodo tiene dos modos importantes:

- `setup_ap`: la Pico crea su propia red WiFi `FDL-Setup-*`. Se usa para configurar board, redes WiFi y recuperar el nodo cuando no puede conectarse.
- `STA`: la Pico se conecta a una red WiFi existente. Es el modo normal de operacion.

Direcciones utiles:

- En `setup_ap`: abre `http://192.168.4.1`.
- En `STA`: abre `http://<ip-del-nodo>`.
- En `STA` con mDNS disponible: abre `http://<mdns_hostname>.local`.

El acceso `.local` es comodo, pero depende del sistema operativo y de la red. Si no responde, usa la IP que aparece en el REPL o en el router.

## Instalar MicroPython

1. Ve a [micropython.org/download](https://micropython.org/download/).
2. Busca la placa Raspberry Pi Pico 2 W y descarga el `.uf2` mas reciente.
3. Desconecta la Pico.
4. Manteniendo presionado `BOOTSEL`, conecta la Pico al PC por USB.
5. Cuando aparezca como almacenamiento USB, arrastra el `.uf2` descargado.
6. Espera a que la placa reinicie automaticamente.

Resultado esperado: la Pico ya no aparece como unidad USB normal y queda lista para usar por REPL MicroPython.

## Copiar el firmware

Todos los archivos dentro de `src/` deben copiarse a la **raiz** del filesystem de la Pico. No los copies dentro de una carpeta `src`.

Archivos esperados en la Pico:

```text
boot.py
main.py
device_config.py
cloud_buffer.py
remote_questdb_service.py
sensor_scd41.py
scd4x.py
timer_service.py
wifi.py
logger.py
index.html
setup.html
```

Verificacion desde REPL:

```python
import os
print(os.listdir())
```

Resultado esperado: el listado contiene todos los archivos anteriores en la raiz.

El nodo crea o mantiene estos archivos persistentes:

```text
wifi_config.json
device_config.json
cloud_buffer.json
```

No necesitas crearlos manualmente para un primer arranque limpio.

## Primer arranque

Reinicia la placa con una de estas opciones:

- `Ctrl + D` desde el REPL.
- Boton `RESET`, si tu placa o montaje lo tiene.
- Desconectar y reconectar USB.

Comportamiento esperado:

1. `boot.py` prepara el arranque.
2. `main.py` carga configuracion local.
3. El nodo intenta conectar por WiFi.
4. Si no tiene una red valida, activa `setup_ap`.

Si estas mirando el REPL, deberias ver mensajes del modo WiFi actual, la IP y la URL local disponible.

## Modo setup

Usa modo setup cuando el nodo es nuevo, cambio de red o no logra conectarse por `STA`.

1. En tu PC, abre la lista de redes WiFi.
2. Conectate a una red con nombre `FDL-Setup-*`.
3. Usa la clave inicial `fdlsetup2026`, salvo que ya la hayas cambiado.
4. Abre `http://192.168.4.1`.
5. En la UI local, revisa la identidad del nodo.
6. Define o confirma el nombre de board.
7. Escanea redes WiFi.
8. Guarda una red de 2.4 GHz con su password.
9. Deja que el nodo intente conectar.

Resultado esperado: cuando la red guardada funciona, el nodo apaga el AP de setup y entra a `STA`.

## Modo STA

`STA` es el modo normal. La Pico esta conectada a tu red WiFi y sirve la UI local desde esa red.

Para entrar:

1. Mira en el REPL la IP reportada por el nodo.
2. Abre `http://<ip-del-nodo>`.
3. Si mDNS esta habilitado, intenta tambien `http://<mdns_hostname>.local`.

Ejemplo:

```text
http://192.168.1.42
http://node-A1B2C3.local
```

En este modo puedes ver lecturas, estado del backend, backlog local, intervalos y crear un deployment.

## Crear un deployment

Un deployment representa una instalacion fisica del nodo en un lugar concreto. Crealo solamente cuando el nodo ya esta ubicado donde va a medir.

1. Entra a la UI local en modo `STA`.
2. Busca la tarjeta **Deployment local**.
3. Escribe latitud.
4. Escribe longitud.
5. Escribe un nombre claro del lugar.
6. Desbloquea la creacion.
7. Presiona **Crear nuevo deployment**.
8. Revisa el resumen y confirma.

Ejemplos de nombres:

```text
unal medellin - lab photonics 109
oficina principal - sala sensores
invernadero norte - modulo 02
```

Resultado esperado: la UI muestra el nuevo `deployment_id` y el nodo conserva ese deployment como activo.

## Que hace cada archivo persistente

`wifi_config.json` guarda conectividad:

- redes conocidas;
- ultima red conectada;
- configuracion del AP de setup;
- parametros de fallback.

`device_config.json` guarda identidad y operacion:

- `board_id`;
- `board_name`;
- `mdns_hostname`;
- `deployment_id`;
- `latitude`;
- `longitude`;
- `location_name`;
- intervalos;
- URL base del backend.

`cloud_buffer.json` guarda muestras pendientes cuando la subida a nube esta deshabilitada o falla temporalmente.

## Operacion diaria

En la UI local puedes:

- ver estado WiFi;
- distinguir `STA`, `setup_ap` y `offline`;
- cambiar a modo setup para reconfigurar redes;
- ver lecturas del sensor;
- cambiar intervalos de muestreo y envio;
- crear deployments;
- habilitar o deshabilitar subida a la nube;
- revisar backlog local;
- limpiar backlog;
- revisar logs y estado del backend.

Evita ejecutar repetidamente `import main` desde el REPL. Para reiniciar el firmware, usa `Ctrl + D` o reinicia la placa.

## Checklist final

Antes de entregar un nodo:

- La Pico tiene MicroPython instalado.
- Todos los archivos de `src/` estan en la raiz.
- El sensor SCD41 esta conectado por I2C.
- El nodo entra a `setup_ap` si no hay WiFi.
- El nodo entra a `STA` con una red valida de 2.4 GHz.
- La UI abre por IP.
- La UI abre por `.local` si mDNS esta disponible.
- El board name es unico y reconocible.
- El deployment tiene nombre, latitud y longitud correctos.
- El backend responde o el backlog local esta entendido.

## Troubleshooting rapido

### No aparece `FDL-Setup-*`

1. Espera 20 a 40 segundos despues del reinicio.
2. Revisa el REPL para confirmar si el nodo entro a `STA`.
3. Si esta en `STA`, entra por la IP reportada.
4. Si hay error de arranque, revisa que `setup.html`, `index.html`, `main.py` y `wifi.py` esten copiados.

### No puedo entrar a `http://192.168.4.1`

1. Confirma que tu PC esta conectado al AP `FDL-Setup-*`.
2. Desactiva temporalmente VPNs que cambien rutas locales.
3. Olvida redes `FDL-Setup-*` antiguas en Windows y reconecta.
4. Reinicia la Pico y espera a que el AP vuelva a aparecer.

### El nodo no conecta a la red WiFi

1. Confirma que la red es 2.4 GHz.
2. Revisa password.
3. Desde setup, escanea redes cercanas.
4. Elimina o corrige credenciales viejas.
5. Usa `Reset WiFi` si el estado quedo inconsistente.

### `.local` no abre

1. Usa primero la IP del nodo.
2. Confirma que PC y Pico estan en la misma red.
3. Revisa que mDNS este habilitado en la UI.
4. En algunas redes corporativas o VLANs, `.local` puede estar bloqueado.

### No hay lecturas del sensor

1. Espera el primer ciclo de warm-up.
2. Revisa `VCC`, `GND`, `SDA` y `SCL`.
3. Confirma que `sensor_scd41.py` y `scd4x.py` estan copiados.
4. Revisa logs desde la UI.

### El backend no responde

La UI local sigue funcionando aunque el backend falle. Revisa internet, DNS y alcance a `https://api.fronteradatalabs.com`. Si la nube esta deshabilitada o falla, las muestras pueden quedar en backlog local.

## URLs del sistema

- `https://api.fronteradatalabs.com`: backend que recibe devices, deployments y telemetria.
- `https://dashboard.fronteradatalabs.com`: dashboard principal.
- `https://questdb.fronteradatalabs.com`: consola administrativa de QuestDB.

El firmware de produccion no debe escribir directo a QuestDB publico.

## Documentacion complementaria

- [`DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md): guia corta para flashear y copiar firmware.
- [`AI_CONTEXT.md`](AI_CONTEXT.md): contexto tecnico para agentes y desarrollo.
