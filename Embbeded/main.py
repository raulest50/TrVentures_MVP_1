import network
import socket
import time
import ujson as json
from machine import Pin, I2C

from scd4x import SCD4X  # asegúrate de tener scd4x.py en la Pico

SSID = "Esteban_AA"
PASSWORD = "pHil76xer*_1"


# ---- Cargar index.html solamente una vez al inicio ----
with open("index.html", "r") as f:
    INDEX_HTML = f.read()


# ---- Conexión WiFi con timeout y mensajes de estado ----
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.disconnect()      # por si quedó algo anterior
    wlan.connect(SSID, PASSWORD)

    print("Conectando a WiFi…")
    t0 = time.time()

    while True:
        if wlan.isconnected():
            print("Conectado:", wlan.ifconfig())
            return wlan

        status = wlan.status()
        # 10 s de espera máximo
        if time.time() - t0 > 10:
            print("ERROR: timeout WiFi, status =", status)
            return wlan  # devolvemos igual, pero sin conexión

        print("   estado WiFi:", status)
        time.sleep(1)


wlan = connect_wifi()



# ---- I2C + SCD41 ----
# Ajusta los pines SDA/SCL según tu cableado real
i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=100_000)
scd = SCD4X(i2c)

scd.start_periodic_measurement()
print("SCD41: medición periódica iniciada (intervalo ~5 s)")
time.sleep(10)  # warm-up inicial para lecturas más estables

latest_readings = {
    "co2": None,
    "temp": None,
    "rh": None,
}


def update_sensor_cache():
    """Lee el sensor solo cuando hay dato nuevo y actualiza latest_readings."""
    try:
        if scd.get_data_ready():
            co2, temp, rh = scd.read_measurement()
            latest_readings["co2"] = float(co2)
            latest_readings["temp"] = float(temp)
            latest_readings["rh"] = float(rh)
    except Exception as e:
        # En un MVP solo mostramos el error y mantenemos la última lectura válida
        print("Error leyendo SCD41:", e)


# ---- Servidor HTTP ----
addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(addr)
s.listen(2)
s.settimeout(0.3)  # para que accept() no bloquee el loop

print("Servidor web en http://%s" % wlan.ifconfig()[0])

HTML_HEADER = (
    "HTTP/1.1 200 OK\r\n"
    "Content-Type: text/html; charset=utf-8\r\n"
    "Connection: close\r\n"
    "\r\n"
)

JSON_HEADER = (
    "HTTP/1.1 200 OK\r\n"
    "Content-Type: application/json\r\n"
    "Connection: close\r\n"
    "\r\n"
)


def handle_client(cl):
    try:
        request = cl.recv(1024)
        if not request:
            return

        first_line = request.split(b"\r\n", 1)[0]
        parts = first_line.split()
        if len(parts) < 2:
            return

        path = parts[1].decode()

        if path == "/" or path.startswith("/index"):
            cl.send(HTML_HEADER)
            cl.send(INDEX_HTML)

        elif path.startswith("/data"):
            cl.send(JSON_HEADER)
            body = json.dumps(latest_readings)
            cl.send(body)

        else:
            cl.send(
                "HTTP/1.1 404 Not Found\r\n"
                "Content-Type: text/plain\r\n"
                "Connection: close\r\n"
                "\r\n"
                "404 - Not found"
            )

    finally:
        cl.close()


# ---- Loop principal ----
while True:
    # 1) Actualizar caché del sensor (si hay dato nuevo)
    update_sensor_cache()

    # 2) Atender conexiones HTTP sin bloquear
    try:
        cl, addr = s.accept()
    except OSError:
        # timeout: no hay cliente en este instante
        continue

    print("Cliente:", addr)
    handle_client(cl)
