# wifi.py - Rutinas robustas de conexión WiFi para Raspberry Pi Pico W / Pico 2 W
# Soporta varias redes con atributo 'priority' y auto-reconnect.

import network
import time

# === LISTA DE REDES ===
# priority: 1 = primera opción, 2 = segunda, etc.
NETWORKS = [
    {"ssid": "Esteban_AA", "password": "pHil76xer*_1", "priority": 4},
    {"ssid": "BIBLIOTECA PUBLICA PILOTO", "password": "", "priority": 3},
    {"ssid": "MOn4Ri", "password": "5A17GedsfRL", "priority": 2},
    {"ssid": "REA", "password": "22826385", "priority": 1},
]

CONNECT_TIMEOUT = 20      # tiempo máximo por intento (segundos)
RETRY_DELAY = 5           # pausa entre reintentos de una misma red (segundos)
CHECK_INTERVAL = 10       # cada cuántos segundos se verifica si sigue conectado

_current_net_index = None
_last_check = 0


def _init_wlan():
    """Reinicia la interfaz WiFi para evitar estados colgados."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(False)
    time.sleep(0.5)
    wlan.active(True)
    return wlan


def _sorted_indices_by_priority():
    # Devolvemos los índices de NETWORKS ordenados por priority ascendente
    indexed = list(enumerate(NETWORKS))
    indexed.sort(key=lambda x: x[1].get("priority", 9999))
    return [idx for idx, _ in indexed]


def _scan_for_ssid(wlan, ssid, verbose=True):
    """Escanea redes y devuelve True si ssid aparece."""
    try:
        nets = wlan.scan()
    except OSError as e:
        if verbose:
            print("Error al escanear redes:", e)
        return False

    found = False

    if verbose:
        print("\n🔍 Redes encontradas:")

    for net in nets:
        name = net[0].decode()
        if verbose:
            print(" -", name)
        if name == ssid:
            found = True

    if verbose:
        if found:
            print(f"\n✅ La red '{ssid}' fue encontrada.")
        else:
            print(f"\n❌ La red '{ssid}' NO aparece en el escaneo.")
            print("   ➤ Verifica hotspot/router encendido.")
            print("   ➤ Debe ser banda 2.4 GHz.")
            print("   ➤ Verifica el nombre EXACTO del SSID.")

    return found


def _connect_once(wlan, ssid, password, do_scan=True, verbose=True):
    """Hace un intento de conexión a una red concreta (una sola vez)."""
    if verbose:
        print("\n📡 WiFi activado. Estado inicial =", wlan.status())
        print(f"   Objetivo: SSID = '{ssid}'")

    if do_scan:
        _scan_for_ssid(wlan, ssid, verbose=verbose)

    if verbose:
        print(f"\n🔗 Intentando conectar a '{ssid}'...")

    wlan.disconnect()
    time.sleep(1)
    wlan.connect(ssid, password)

    t0 = time.time()
    last_status = None

    while True:
        status = wlan.status()

        if status != last_status and verbose:
            print(f"   ↪ Estado WiFi cambió a: {status}")
            last_status = status

        if wlan.isconnected():
            if verbose:
                print("\n🎉 CONECTADO con éxito!")
                print("   IFCONFIG =", wlan.ifconfig())
            return True

        if time.time() - t0 > CONNECT_TIMEOUT:
            if verbose:
                print(f"\n⏳❌ TIMEOUT ({CONNECT_TIMEOUT}s) — No se pudo conectar a '{ssid}'.")
                print("   Estado final =", status)

                if status == network.STAT_WRONG_PASSWORD:
                    print("   ❌ Contraseña incorrecta.")
                elif status == network.STAT_NO_AP_FOUND:
                    print("   ❌ No se encontró el AP.")
                elif status == network.STAT_CONNECT_FAIL:
                    print("   ❌ Fallo general de conexión.")
                elif status == -1:
                    print("   ❌ Error desconocido (WiFi congelado).")
                else:
                    print("   ❓ Estado no documentado:", status)

            return False

        time.sleep(1)


def connect_wifi(do_scan=True, verbose=True, retries_per_network=2):
    """
    Intenta conectar al WiFi usando NETWORKS ordenado por priority.
    Devuelve el objeto wlan (conectado o no).
    """
    global _current_net_index

    wlan = _init_wlan()
    ordered_indices = _sorted_indices_by_priority()

    for net_index in ordered_indices:
        net = NETWORKS[net_index]
        ssid = net["ssid"]
        password = net["password"]

        if verbose:
            print("\n==============================")
            print(f"   🌐 Probando red #{net_index + 1}: {ssid}")
            print("==============================")

        for attempt in range(1, retries_per_network + 1):
            if verbose:
                print(f"\n🔁 Intento {attempt} de {retries_per_network} para '{ssid}'")

            ok = _connect_once(
                wlan,
                ssid,
                password,
                do_scan=(do_scan and attempt == 1),
                verbose=verbose,
            )

            if ok:
                _current_net_index = net_index
                return wlan

            if attempt < retries_per_network:
                if verbose:
                    print(f"   Esperando {RETRY_DELAY}s antes de reintentar '{ssid}'...")
                time.sleep(RETRY_DELAY)

    if verbose:
        print("\n❌ No se pudo conectar a ninguna de las redes configuradas.")
    return wlan


def ensure_connected(wlan, verbose=False):
    """
    Verifica cada cierto tiempo si la conexión sigue activa.
    Si no, intenta reconectar usando la lista NETWORKS (orden priority).
    """
    global _last_check, _current_net_index

    now = time.time()
    if now - _last_check < CHECK_INTERVAL:
        return wlan

    _last_check = now

    if wlan.isconnected():
        return wlan

    if verbose:
        print("\n⚠️ WiFi desconectado. Intentando reconectar...")

    # Orden de reconexión:
    # 1) la red que estaba activa (si se conoce)
    # 2) el resto, según priority
    ordered_indices = _sorted_indices_by_priority()
    start_indices = []

    if _current_net_index is not None and _current_net_index in ordered_indices:
        start_indices.append(_current_net_index)

    for idx in ordered_indices:
        if idx not in start_indices:
            start_indices.append(idx)

    wlan = _init_wlan()

    for idx in start_indices:
        net = NETWORKS[idx]
        ssid = net["ssid"]
        password = net["password"]

        if verbose:
            print(f"\n🔁 Reconexión: probando '{ssid}'")

        ok = _connect_once(
            wlan,
            ssid,
            password,
            do_scan=False,
            verbose=verbose,
        )

        if ok:
            _current_net_index = idx
            return wlan

    if verbose:
        print("\n❌ Falló la reconexión a todas las redes.")
    return wlan


def get_wifi_info(wlan):
    """
    Devuelve un diccionario con información de la conexión WiFi actual.
    Incluye: SSID, IP, calidad de señal (RSSI y porcentaje), estado.
    """
    if not wlan or not wlan.isconnected():
        return {
            "connected": False,
            "ssid": None,
            "ip": None,
            "rssi": None,
            "signal_percent": 0,
            "signal_quality": "Sin conexión"
        }

    try:
        # Obtener SSID de la red actual
        ssid = "Desconocido"
        if _current_net_index is not None and _current_net_index < len(NETWORKS):
            ssid = NETWORKS[_current_net_index]["ssid"]

        # Obtener IP local
        ip = wlan.ifconfig()[0]

        # Obtener RSSI (calidad de señal en dBm)
        rssi = wlan.status('rssi')

        # Calcular porcentaje de señal
        # RSSI típicamente va de -100 (muy mala) a -30 (excelente)
        # Fórmula: (rssi + 100) * 100 / 70, con límites [0, 100]
        if rssi is not None:
            signal_percent = max(0, min(100, (rssi + 100) * 100 // 70))
        else:
            signal_percent = 0

        # Determinar calidad textual
        if signal_percent >= 70:
            signal_quality = "Excelente"
        elif signal_percent >= 50:
            signal_quality = "Buena"
        elif signal_percent >= 30:
            signal_quality = "Regular"
        else:
            signal_quality = "Débil"

        return {
            "connected": True,
            "ssid": ssid,
            "ip": ip,
            "rssi": rssi,
            "signal_percent": signal_percent,
            "signal_quality": signal_quality
        }

    except Exception as e:
        print("⚠️ Error obteniendo información WiFi:", e)
        return {
            "connected": False,
            "ssid": None,
            "ip": None,
            "rssi": None,
            "signal_percent": 0,
            "signal_quality": "Error"
        }


def _authmode_to_string(authmode):
    """Convierte el código de autenticación a texto legible."""
    # Constantes de network.py en MicroPython
    AUTH_MODES = {
        0: "Abierta",
        1: "WEP",
        2: "WPA-PSK",
        3: "WPA2-PSK",
        4: "WPA/WPA2-PSK",
    }
    return AUTH_MODES.get(authmode, f"Desconocido ({authmode})")


def get_nearby_networks(wlan, limit=5):
    """
    Escanea y devuelve las redes WiFi cercanas ordenadas por señal.

    Args:
        wlan: Objeto WLAN activo
        limit: Número máximo de redes a retornar (default 5)

    Returns:
        dict con:
        - "networks": lista de diccionarios con info de cada red
        - "error": mensaje de error si falla el escaneo
    """
    if not wlan:
        return {"networks": [], "error": "WLAN no inicializado"}

    try:
        # Escanear redes
        # Formato de cada tupla: (ssid, bssid, channel, RSSI, authmode, hidden)
        scan_results = wlan.scan()

        if not scan_results:
            return {"networks": [], "error": None}

        # Procesar y ordenar por RSSI (mejor señal primero)
        networks = []

        for net in scan_results:
            ssid = net[0].decode('utf-8', 'ignore')
            # Ignorar redes sin SSID (ocultas sin nombre visible)
            if not ssid or ssid.strip() == "":
                continue

            rssi = net[3]
            authmode = net[4]

            # Calcular porcentaje de señal
            signal_percent = max(0, min(100, (rssi + 100) * 100 // 70))

            # Determinar calidad textual
            if signal_percent >= 70:
                signal_quality = "Excelente"
            elif signal_percent >= 50:
                signal_quality = "Buena"
            elif signal_percent >= 30:
                signal_quality = "Regular"
            else:
                signal_quality = "Débil"

            networks.append({
                "ssid": ssid,
                "rssi": rssi,
                "signal_percent": signal_percent,
                "signal_quality": signal_quality,
                "security": _authmode_to_string(authmode)
            })

        # Ordenar por RSSI descendente (mejor señal primero)
        networks.sort(key=lambda x: x["rssi"], reverse=True)

        # Limitar a las primeras N redes
        networks = networks[:limit]

        return {"networks": networks, "error": None}

    except OSError as e:
        return {"networks": [], "error": f"Error de escaneo: {e}"}
    except Exception as e:
        return {"networks": [], "error": f"Error inesperado: {e}"}
