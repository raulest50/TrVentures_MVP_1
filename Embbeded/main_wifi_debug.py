import network
import socket
import time

SSID = "Esteban_AA"
PASSWORD = "pHil76xer*_1"


def scan_networks(wlan):
    print("\n🔍 Escaneando redes WiFi...")
    nets = wlan.scan()
    found = False
    for net in nets:
        name = net[0].decode()
        print(" - Red encontrada:", name)
        if name == SSID:
            found = True

    if found:
        print(f"\n✅ La red '{SSID}' fue encontrada en el escaneo.")
    else:
        print(f"\n❌ La red '{SSID}' NO aparece en el escaneo.")
        print("   ➤ Verifica que el hotspot esté encendido.")
        print("   ➤ Verifica que esté en banda 2.4 GHz (NO 5 GHz).")
        print("   ➤ Verifica el nombre EXACTO del SSID.")
    return found


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    print("\n📡 WiFi activado. Estado inicial =", wlan.status())

    # Escaneo
    scan_networks(wlan)

    print(f"\n🔗 Intentando conectar a '{SSID}' ...")
    wlan.disconnect()  # limpiar estado
    time.sleep(1)
    wlan.connect(SSID, PASSWORD)

    t0 = time.time()
    last_status = None

    while True:
        status = wlan.status()
        if status != last_status:
            print(f"   ↪ Estado WiFi cambió a: {status}")
            last_status = status

        if wlan.isconnected():
            print("\n🎉 CONECTADO con éxito!")
            print("   IFCONFIG =", wlan.ifconfig())
            return wlan

        # Timeout 20 s
        if time.time() - t0 > 20:
            print("\n⏳❌ TIMEOUT 20 s — No se pudo conectar.")
            print("   Estado final =", status)

            if status == network.STAT_WRONG_PASSWORD:
                print("   ❌ Contraseña incorrecta.")
            elif status == network.STAT_NO_AP_FOUND:
                print("   ❌ No se encontró el AP (SSID incorrecto o fuera de rango).")
            elif status == network.STAT_CONNECT_FAIL:
                print("   ❌ Fallo general de conexión.")
            elif status == -1:
                print("   ❌ Error desconocido / WiFi apagado.")
            else:
                print("   ❓ Estado no documentado:", status)

            return None

        time.sleep(1)


def start_server(ip):
    print("\n🌐 Iniciando servidor HTTP en", ip)

    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(1)

    print(f"🚀 Servidor listo: http://{ip}")

    while True:
        cl, remote = s.accept()
        print("👤 Cliente conectado desde:", remote)

        request = cl.recv(1024)
        print("📨 Request recibido:", request)

        response = """\
HTTP/1.1 200 OK
Content-Type: text/html

<!DOCTYPE html>
<html>
  <head><title>Pico W</title></head>
  <body>
    <h1>Hola Mundo desde Raspberry Pi Pico W</h1>
    <p>Diagnostico WiFi OK.</p>
  </body>
</html>
"""
        cl.send(response)
        cl.close()


# ==================================================================
# 🚀 PROGRAMA PRINCIPAL
# ==================================================================
print("\n============================")
print("     🌐 DIAGNÓSTICO WIFI    ")
print("============================")

wlan = connect_wifi()

if wlan and wlan.isconnected():
    ip = wlan.ifconfig()[0]
    start_server(ip)
else:
    print("\n❌ No se pudo iniciar el servidor por fallo de conexión WiFi.\n")
