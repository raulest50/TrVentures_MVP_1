# Guia corta de despliegue - Firmware IoT Pico W

> La guia principal y actualizada de operacion vive en [`README.md`](README.md). Este archivo queda como referencia rapida para flashear MicroPython y copiar el firmware a la Pico.

## Archivos a copiar a la Raspberry Pi Pico W

Todos los archivos de `src/` deben copiarse **a la raiz del filesystem** de la Pico:

```text
boot.py
main.py
device_config.py
remote_questdb_service.py
sensor_scd41.py
scd4x.py
timer_service.py
wifi.py
logger.py
index.html
```

Archivos persistentes generados o mantenidos por el nodo:

```text
device_config.json
wifi_config.json
```

## Proceso resumido

### 1. Flashear MicroPython

1. Descarga el `.uf2` mas reciente desde [micropython.org/download/RPI_PICO_W](https://micropython.org/download/RPI_PICO_W/)
2. Conecta la Pico manteniendo presionado `BOOTSEL`
3. Arrastra el `.uf2` al almacenamiento USB
4. La placa reinicia automaticamente

### 2. Subir firmware

1. Abre el proyecto en Thonny, PyCharm o tu herramienta MicroPython favorita
2. Sube todos los archivos de `src/`
3. Verifica que quedaron en la **raiz** del dispositivo, no dentro de una carpeta `src/`

### 3. Verificar archivos

Desde REPL:

```python
import os
print(os.listdir())
```

Debe aparecer un listado similar a:

```text
['boot.py', 'main.py', 'device_config.py', 'remote_questdb_service.py',
 'sensor_scd41.py', 'scd4x.py', 'timer_service.py', 'wifi.py',
 'logger.py', 'index.html']
```

### 4. Reiniciar

Opciones recomendadas:

- `Ctrl + D`
- boton `RESET`
- desconectar y reconectar USB

## Que deberia pasar despues del reinicio

- Si existe una red conocida valida, el nodo intentara `STA` y mostrara su IP.
- Si no existe una red valida o falla la conexion, el nodo debe activar `setup_ap`.
- En `setup_ap`, la UI local queda disponible en `http://192.168.4.1`.

La explicacion completa del flujo de estados y del provisioning WiFi esta en el `README.md`.

## Troubleshooting minimo

### El servidor no arranca

1. Verifica que todos los archivos de `src/` fueron copiados.
2. Revisa especialmente `index.html`, `main.py` y `wifi.py`.
3. Si `boot.py` falla, revisa el REPL para capturar el error de arranque.

### El nodo no conecta a WiFi

1. Busca si aparece el AP `FDL-Setup-...`
2. Conectate al AP del nodo
3. Abre `http://192.168.4.1`
4. Guarda una red valida de 2.4 GHz

### El sensor no reporta datos

1. Espera el primer ciclo de lectura
2. Verifica cableado I2C
3. Revisa logs desde la UI local
