# Contexto del Proyecto - Firmware IoT para Nodo Ambiental

> Archivo de contexto para coding agents. El codigo de produccion que se copia a la Raspberry Pi Pico W2 vive en `Embbeded/src/`.

## Entorno de ejecucion

- Hardware target: Raspberry Pi Pico W2
- Runtime: MicroPython
- Sensor principal: SCD41
- Restricciones: poca RAM, stdlib reducida, preferir `ujson`, `urequests` y modulos simples

## Codigo de produccion

Los archivos dentro de `src/` son los que se despliegan al dispositivo:

- `main.py`: loop principal
- `device_config.py`: configuracion persistente
- `remote_questdb_service.py`: cliente HTTP del backend IoT
- `timer_service.py`: NTP y timestamps UTC
- `wifi.py`: conexion WiFi
- `index.html`: UI local del nodo

Los archivos fuera de `src/` son apoyo para escritorio o documentacion, no firmware productivo.

## Arquitectura vigente

### Flujo del nodo

1. El nodo obtiene `board_id` desde la MAC.
2. Genera y conserva localmente `deployment_id`.
3. Envia JSON por HTTPS a `https://api.fronteradatalabs.com`.
4. El backend FastAPI traduce esos payloads a escrituras en QuestDB.

### Endpoints de ingest

- `POST /api/iot/devices/register`
- `POST /api/iot/deployments`
- `POST /api/iot/telemetry`

### QuestDB

- QuestDB ya no es el destino directo del firmware en produccion.
- La consola administrativa vive en `https://questdb.fronteradatalabs.com`.
- El dashboard consume lecturas desde `https://api.fronteradatalabs.com`.

## Estado y configuracion local

`device_config.json` guarda, entre otros:

- `board_id`
- `deployment_id`
- `deployment_counter`
- `latitude`
- `longitude`
- `location_name`
- `sample_interval`
- `questdb_interval`
- `device_registered`
- `api_base_url`

`questdb_interval` se conserva como nombre por compatibilidad, aunque el envio real ahora va al backend API.

## Reglas para implementar cambios

- Modificar solo `src/` si el cambio es de firmware real.
- No reintroducir IPs hardcodeadas del VPS en el firmware.
- Mantener timestamps UTC usando `timer_service.get_timestamp_ns()`.
- Preservar la logica local de `deployment_id` en la Pico.
- No hacer que el dashboard hable directo con QuestDB ni con la Pico.

## Nota importante

Hay credenciales WiFi hardcodeadas en `src/wifi.py`. Eso es deuda tecnica de seguridad y debe tratarse aparte de la migracion de URLs.
