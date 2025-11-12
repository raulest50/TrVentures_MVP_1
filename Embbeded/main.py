import network
import socket
import time

ssid = "WIFI-ITM"
password = ""

# Conexión WiFi
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)
while not wlan.isconnected():
    time.sleep(0.5)
print("Conectado a Wi-Fi:", wlan.ifconfig())

# Servidor HTTP
addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
s = socket.socket()
s.bind(addr)
s.listen(1)

print('Servidor iniciado en http://%s' % wlan.ifconfig()[0])

while True:
    cl, addr = s.accept()
    print('Cliente conectado desde', addr)
    request = cl.recv(1024)
    response = """\
HTTP/1.1 200 OK
Content-Type: text/html

<!DOCTYPE html>
<html>
  <head><title>Pico W</title></head>
  <body>
    <h1>Hola Mundo desde Raspberry Pi Pico W</h1>
    <p>This is very cool test</p>
  </body>
</html>
"""
    cl.send(response)
    cl.close()
