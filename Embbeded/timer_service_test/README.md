# Timer Service Test Suite

Script de prueba para validar la sincronización NTP de `timer_service.py` en tu PC (sin necesidad de Raspberry Pi Pico).

## 🎯 Propósito

- Probar que la lógica de sincronización NTP funciona correctamente
- Verificar múltiples servidores NTP
- Validar cálculos de offset UTC y conversiones de tiempo
- Debugging de problemas de sincronización sin necesidad del hardware

## 📋 Requisitos

- Python 3.x (CPython, no MicroPython)
- Conexión a internet para consultas NTP
- No requiere librerías externas (solo stdlib de Python)

## 🚀 Uso

```bash
cd timer_service_test
python test_timer_service.py
```

## 🧪 Tests incluidos

### Test 1: Funciones básicas de tiempo
- Validación de tiempo
- Epoch actual
- Timestamp en nanosegundos
- Formateo ISO 8601

### Test 2: Configuración de offset UTC
- Prueba diferentes zonas horarias (México, NY, Madrid, Tokio)
- Verifica conversión UTC → Local

### Test 3: Sincronización NTP
- Conecta con `pool.ntp.org`
- Compara tiempo NTP vs tiempo del sistema
- Verifica re-sincronización con caché

### Test 4: Múltiples servidores NTP
- Prueba 4 servidores diferentes:
  - pool.ntp.org
  - time.google.com
  - time.cloudflare.com
  - time.windows.com

## 📊 Salida esperada

```
████████████████████████████████████████████████████████████████████
█                                                                      █
█               TIMER SERVICE - TEST SUITE                           █
█                                                                      █
████████████████████████████████████████████████████████████████████

======================================================================
TEST 1: FUNCIONES BÁSICAS DE TIEMPO
======================================================================
...

✓ Sincronización NTP exitosa:
  • Servidor NTP: pool.ntp.org
  • Tiempo NTP:     2026-03-10T12:34:56Z
  • Tiempo Sistema: 2026-03-10T12:34:56Z
  • Diferencia:     0s
  ✓ El reloj del sistema está sincronizado
```

## 🔧 Diferencias con MicroPython

Este test **NO** puede cambiar el reloj del sistema (requiere permisos root/admin).

En **MicroPython** (Raspberry Pi Pico):
- `ntptime.settime()` actualiza el RTC del hardware
- El reloj se mantiene sincronizado

En **CPython** (este test):
- Solo **consulta** servidores NTP
- **Compara** tiempo NTP vs tiempo del sistema
- **Reporta** diferencias pero no modifica el reloj

## ⚠️ Troubleshooting

### Error: "Timeout al conectar"
- Verifica tu conexión a internet
- Algunos firewalls bloquean puerto UDP 123
- Intenta con otro servidor NTP

### Error: "No se pudo resolver DNS"
- Problema de conectividad o DNS
- Verifica que puedas hacer `ping pool.ntp.org`

### Diferencia de tiempo > 5 segundos
- Tu PC está desincronizado
- En Windows: Configura sincronización automática
- En Linux/Mac: Instala `ntpd` o `chrony`

## 🐛 Debugging en Raspberry Pi Pico

Si el NTP no funciona en el Pico pero sí en este test:

1. **Verifica WiFi**: El Pico debe estar conectado a internet
2. **Firewall**: Algunos routers bloquean NTP (puerto UDP 123)
3. **DNS**: El Pico debe poder resolver `pool.ntp.org`
4. **Timeout**: Incrementa timeout en `timer_service.py`
5. **Servidor alternativo**: Usa `time.google.com` en lugar de `pool.ntp.org`

## 📝 Notas

- Este script es **solo para testing en PC**
- El código en la Raspberry Pi Pico usa `timer_service.py` original
- Los resultados de este test indican si la lógica es correcta
- Si falla en el Pico pero funciona aquí, el problema es de red/hardware
