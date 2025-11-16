# Tropico Ventures MVP 1

## Setting Up PyCharm for MicroPython
Se debe descargar una extension para micropython y se debe configurar en settings > Language and framework

## Flashing micropython into pico2W
de la pagina oficial de raspberry se descarga el uf2 mas reciente:
[instrucciones oficiales](https://projects.raspberrypi.org/en/projects/getting-started-with-the-pico/3)

la instalacion es basicamente conectar la pico2w por usb y arrastrar el uf2 file en el almacenamiento de la
pico2w. Despues de arrastrar el archivo la instalacion se hace automaticamente.

## Direccion Ip Pico2W

Una vez la Pico esté conectada a la red, se puede ver la IP desde el REPL:

```
import network
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
print(wlan.ifconfig())
```

## Cómo funciona `main.py` en MicroPython

MicroPython ejecuta automáticamente los archivos especiales:

* **`main.py`** → Se ejecuta al arrancar la placa.
* **`boot.py`** (opcional) → Se ejecuta antes que `main.py`.

Para que tu servidor web o tus procesos IoT inicien automáticamente, solo debes subir un archivo llamado **`main.py`** al sistema de archivos interno de la Pico.

En PyCharm:

1. Click derecho sobre **`main.py`**
2. Seleccionar **Upload to MicroPython device**
3. Reiniciar la placa con el botón **RESET**

> **Importante:** No es necesario ejecutar `main.py` manualmente desde el REPL.
> Hacerlo puede causar errores como `EADDRINUSE` si el servidor ya está escuchando en un puerto.

---

## 5. Uso del REPL sin interferir con el servidor

Es totalmente válido mantener el **REPL por COM** abierto mientras el servidor web está corriendo en la Pico.
El REPL no bloquea ni interrumpe el servidor, siempre que no ejecutes acciones que reinicien o dupliquen el servidor, tales como:

* Ejecutar `import main`
* Reiniciar sockets desde el REPL
* Usar repetidamente `Ctrl + D` sin esperar que el script arranque

Mientras no se reinicie el socket manualmente, puedes usar el REPL para:

* Ver logs (`print`)
* Monitorear la IP
* Inspeccionar variables
* Leer sensores
* Hacer debugging básico

El servidor seguirá **activo y respondiendo** incluso con el REPL abierto.


## Notas de Investigacion Profunda

### Research Notes on IoT Communication

* MQTT is the standard protocol for IoT node-to-server communication.
HTTP can be valid under certain circumstances but MQTT should be preferred when possible.
* If no internet available then redes LoRaWAN, Sigfox o NB-IoT, to cover big distances overa city

