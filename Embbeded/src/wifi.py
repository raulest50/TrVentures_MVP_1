"""
Provisioning WiFi para Raspberry Pi Pico W / Pico 2 W.

- Guarda redes conocidas en wifi_config.json
- Intenta conectar en modo STA
- Si falla, activa un SoftAP de setup protegido por password
- Expone utilidades para la UI local y para reconexion automatica
"""

import network
import time
import ujson as json
import device_config

try:
    import machine
except ImportError:
    machine = None


CONFIG_FILE = "wifi_config.json"
DEFAULT_CONNECT_TIMEOUT = 20
DEFAULT_RETRY_BACKOFF = 5
DEFAULT_AP_START_DELAY = 15
CHECK_INTERVAL = 10
DEFAULT_AP_CHANNEL = 6

_sta_wlan = None
_ap_wlan = None
_last_check = 0
_current_ssid = None
_mode = "offline"
_last_connection_attempt = 0
_last_connection_error = None
_last_test_result = None
_mdns_status = "not_applied"


def _get_sta_wlan():
    global _sta_wlan
    if _sta_wlan is None:
        _sta_wlan = network.WLAN(network.STA_IF)
    return _sta_wlan


def _get_ap_wlan():
    global _ap_wlan
    if _ap_wlan is None:
        _ap_wlan = network.WLAN(network.AP_IF)
    return _ap_wlan


def _get_mac_suffix():
    try:
        wlan = _get_sta_wlan()
        mac_bytes = wlan.config("mac")
        hex_mac = "".join(["{:02X}".format(b) for b in mac_bytes])
        return hex_mac[-8:], hex_mac[-6:]
    except Exception:
        return "00000000", "000000"


def _build_setup_ap_ssid():
    board_name = device_config.get_board_name()
    return "FDL-Setup-{}".format(board_name)


def _build_default_config():
    return {
        "known_networks": [],
        "last_connected_ssid": None,
        "setup_ap": {
            "ssid": _build_setup_ap_ssid(),
            "password": "fdlsetup2026",
            "channel": DEFAULT_AP_CHANNEL,
            "enabled": True,
        },
        "fallback": {
            "auto_ap_enabled": True,
            "connect_timeout_seconds": DEFAULT_CONNECT_TIMEOUT,
            "retry_backoff_seconds": DEFAULT_RETRY_BACKOFF,
            "ap_start_delay_seconds": DEFAULT_AP_START_DELAY,
        },
    }


def _normalize_network_entry(entry):
    return {
        "ssid": str(entry.get("ssid", "")).strip(),
        "password": str(entry.get("password", "")),
        "priority": int(entry.get("priority", 9999)),
        "enabled": bool(entry.get("enabled", True)),
    }


def _sanitize_config(config):
    defaults = _build_default_config()
    sanitized = {
        "known_networks": [],
        "last_connected_ssid": config.get("last_connected_ssid"),
        "setup_ap": defaults["setup_ap"].copy(),
        "fallback": defaults["fallback"].copy(),
    }

    setup_ap = config.get("setup_ap", {})
    if isinstance(setup_ap, dict):
        sanitized["setup_ap"]["ssid"] = str(setup_ap.get("ssid", defaults["setup_ap"]["ssid"])).strip() or defaults["setup_ap"]["ssid"]
        sanitized["setup_ap"]["password"] = str(setup_ap.get("password", defaults["setup_ap"]["password"])).strip() or defaults["setup_ap"]["password"]
        sanitized["setup_ap"]["channel"] = int(setup_ap.get("channel", defaults["setup_ap"]["channel"]))
        sanitized["setup_ap"]["enabled"] = bool(setup_ap.get("enabled", True))

    fallback = config.get("fallback", {})
    if isinstance(fallback, dict):
        sanitized["fallback"]["auto_ap_enabled"] = bool(
            fallback.get("auto_ap_enabled", defaults["fallback"]["auto_ap_enabled"])
        )
        sanitized["fallback"]["connect_timeout_seconds"] = int(
            fallback.get("connect_timeout_seconds", defaults["fallback"]["connect_timeout_seconds"])
        )
        sanitized["fallback"]["retry_backoff_seconds"] = int(
            fallback.get("retry_backoff_seconds", defaults["fallback"]["retry_backoff_seconds"])
        )
        sanitized["fallback"]["ap_start_delay_seconds"] = int(
            fallback.get("ap_start_delay_seconds", defaults["fallback"]["ap_start_delay_seconds"])
        )

    known_networks = config.get("known_networks", [])
    if isinstance(known_networks, list):
        for entry in known_networks:
            if not isinstance(entry, dict):
                continue
            normalized = _normalize_network_entry(entry)
            if normalized["ssid"]:
                sanitized["known_networks"].append(normalized)

    return sanitized


def _apply_mdns_hostname():
    global _mdns_status

    if not hasattr(network, "hostname"):
        _mdns_status = "unsupported"
        return None

    try:
        if device_config.is_mdns_enabled():
            hostname = device_config.get_mdns_hostname()
        else:
            hostname = "pico-node"
        network.hostname(hostname)
        _mdns_status = "applied" if device_config.is_mdns_enabled() else "disabled"
        return hostname
    except Exception as e:
        print("mDNS hostname no pudo aplicarse: {}".format(e))
        _mdns_status = "error"
        return None


def load_wifi_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
        config = _sanitize_config(config)
        return config
    except OSError:
        config = _build_default_config()
        save_wifi_config(config)
        return config
    except Exception as e:
        print("WiFi config corrupto o invalido: {}".format(e))
        config = _build_default_config()
        save_wifi_config(config)
        return config


def save_wifi_config(config):
    sanitized = _sanitize_config(config)
    with open(CONFIG_FILE, "w") as f:
        json.dump(sanitized, f)
    return sanitized


def _sorted_networks(config):
    networks = [entry for entry in config["known_networks"] if entry.get("enabled", True)]
    networks.sort(key=lambda entry: entry.get("priority", 9999))
    return networks


def _get_network_order(config):
    ordered = _sorted_networks(config)
    last_connected_ssid = config.get("last_connected_ssid")
    prioritized = []

    if last_connected_ssid:
        for entry in ordered:
            if entry["ssid"] == last_connected_ssid:
                prioritized.append(entry)
                break

    for entry in ordered:
        if entry not in prioritized:
            prioritized.append(entry)

    return prioritized


def _scan_networks(wlan):
    try:
        return wlan.scan()
    except Exception:
        return []


def _scan_visible_ssids(wlan):
    visible = []
    for net in _scan_networks(wlan):
        try:
            ssid = net[0].decode("utf-8", "ignore")
        except Exception:
            ssid = ""
        if ssid:
            visible.append(ssid)
    return visible


def _init_sta():
    wlan = _get_sta_wlan()
    try:
        wlan.active(False)
        time.sleep(0.3)
    except Exception:
        pass
    _apply_mdns_hostname()
    wlan.active(True)
    return wlan


def stop_setup_ap():
    global _mode
    ap = _get_ap_wlan()
    try:
        ap.active(False)
    except Exception:
        pass

    if _mode == "setup_ap":
        _mode = "offline"


def start_setup_ap(verbose=True):
    global _mode
    config = load_wifi_config()
    setup_ap = config["setup_ap"]
    ap = _get_ap_wlan()

    ap.active(False)
    time.sleep(0.2)
    ap.active(True)

    try:
        ap.config(
            ssid=setup_ap["ssid"],
            key=setup_ap["password"],
            security=network.AUTH_WPA2_PSK,
            channel=setup_ap["channel"],
        )
    except Exception:
        ap.config(
            ssid=setup_ap["ssid"],
            password=setup_ap["password"],
            channel=setup_ap["channel"],
        )

    _mode = "setup_ap"

    if verbose:
        try:
            ip = ap.ifconfig()[0]
        except Exception:
            ip = "192.168.4.1"
        print("\nWiFi setup AP activo")
        print("  SSID: {}".format(setup_ap["ssid"]))
        print("  Password: {}".format(setup_ap["password"]))
        print("  URL: http://{}".format(ip))

    return ap


def _connect_once(wlan, entry, timeout_seconds, visible_ssids, verbose=True):
    global _current_ssid, _mode, _last_connection_error

    ssid = entry["ssid"]
    password = entry["password"]

    if visible_ssids and ssid not in visible_ssids:
        if verbose:
            print("WiFi: '{}' no esta visible en el escaneo.".format(ssid))
        _last_connection_error = "ssid_not_visible"
        return False

    try:
        wlan.disconnect()
        time.sleep(0.5)
    except Exception:
        pass

    if verbose:
        print("WiFi: intentando conectar a '{}'...".format(ssid))

    wlan.connect(ssid, password)
    started_at = time.time()

    while time.time() - started_at < timeout_seconds:
        if wlan.isconnected():
            _current_ssid = ssid
            _mode = "sta"
            _last_connection_error = None
            config = load_wifi_config()
            config["last_connected_ssid"] = ssid
            save_wifi_config(config)
            try:
                ip = wlan.ifconfig()[0]
            except Exception:
                ip = None
            device_config.set_last_local_network(ip=ip, ssid=ssid)
            stop_setup_ap()
            return True

        time.sleep(1)

    status = None
    try:
        status = wlan.status()
    except Exception:
        pass

    if status == network.STAT_WRONG_PASSWORD:
        _last_connection_error = "wrong_password"
    elif status == network.STAT_NO_AP_FOUND:
        _last_connection_error = "no_ap_found"
    else:
        _last_connection_error = "connect_fail"

    return False


def connect_wifi(do_scan=True, verbose=True, retries_per_network=1):
    global _mode, _last_connection_attempt

    config = load_wifi_config()
    networks = _get_network_order(config)
    wlan = _init_sta()
    _mode = "offline"
    _last_connection_attempt = time.time()

    if not networks:
        if verbose:
            print("WiFi: no hay redes guardadas.")
        if config["fallback"]["auto_ap_enabled"]:
            start_setup_ap(verbose=verbose)
        return wlan

    visible_ssids = _scan_visible_ssids(wlan) if do_scan else []
    timeout_seconds = config["fallback"]["connect_timeout_seconds"]
    retry_backoff = config["fallback"]["retry_backoff_seconds"]

    for entry in networks:
        for attempt in range(retries_per_network):
            if _connect_once(wlan, entry, timeout_seconds, visible_ssids, verbose=verbose):
                return wlan
            if attempt < retries_per_network - 1:
                time.sleep(retry_backoff)

    if config["fallback"]["auto_ap_enabled"]:
        start_setup_ap(verbose=verbose)

    return wlan


def ensure_connected(wlan, verbose=False):
    global _last_check

    now = time.time()
    if now - _last_check < CHECK_INTERVAL:
        return wlan
    _last_check = now

    if wlan and wlan.isconnected():
        stop_setup_ap()
        return wlan

    config = load_wifi_config()
    fallback = config["fallback"]
    delay_seconds = fallback["ap_start_delay_seconds"]

    if config["known_networks"]:
        wlan = connect_wifi(do_scan=False, verbose=verbose, retries_per_network=1)
        if wlan and wlan.isconnected():
            return wlan

    if fallback["auto_ap_enabled"]:
        if (time.time() - _last_connection_attempt) >= delay_seconds:
            start_setup_ap(verbose=verbose)

    return wlan


def get_wifi_mode():
    return _mode


def get_active_ip():
    if _mode == "sta":
        try:
            return _get_sta_wlan().ifconfig()[0]
        except Exception:
            return None
    if _mode == "setup_ap":
        try:
            return _get_ap_wlan().ifconfig()[0]
        except Exception:
            return None
    return None


def get_wifi_info(wlan):
    config = load_wifi_config()
    info = {
        "connected": bool(wlan and wlan.isconnected()),
        "ssid": _current_ssid,
        "ip": get_active_ip(),
        "rssi": None,
        "signal_percent": 0,
        "signal_quality": "Sin conexion",
        "mode": get_wifi_mode(),
        "last_connected_ssid": config.get("last_connected_ssid"),
        "auto_ap_enabled": config["fallback"]["auto_ap_enabled"],
        "setup_ap_ssid": config["setup_ap"]["ssid"],
        "last_connection_error": _last_connection_error,
        "mdns_enabled": device_config.is_mdns_enabled(),
        "mdns_hostname": device_config.get_mdns_hostname(),
        "mdns_status": _mdns_status,
    }

    if wlan and wlan.isconnected():
        try:
            rssi = wlan.status("rssi")
            info["rssi"] = rssi
            signal_percent = max(0, min(100, (rssi + 100) * 100 // 70))
            info["signal_percent"] = signal_percent
            if signal_percent >= 70:
                info["signal_quality"] = "Excelente"
            elif signal_percent >= 50:
                info["signal_quality"] = "Buena"
            elif signal_percent >= 30:
                info["signal_quality"] = "Regular"
            else:
                info["signal_quality"] = "Debil"
        except Exception:
            info["signal_quality"] = "Desconocida"
    elif info["mode"] == "setup_ap":
        info["signal_quality"] = "Modo setup"

    return info


def _authmode_to_string(authmode):
    auth_modes = {
        0: "Abierta",
        1: "WEP",
        2: "WPA-PSK",
        3: "WPA2-PSK",
        4: "WPA/WPA2-PSK",
    }
    return auth_modes.get(authmode, "Desconocido ({})".format(authmode))


def get_nearby_networks(wlan, limit=8):
    wlan = wlan or _get_sta_wlan()
    config = load_wifi_config()
    try:
        if not wlan.active():
            wlan.active(True)
        scan_results = wlan.scan()
    except OSError as e:
        return {
            "networks": [],
            "error": "Error de escaneo: {}".format(e),
            "mode": get_wifi_mode(),
            "last_connected_ssid": config.get("last_connected_ssid"),
            "fallback": config.get("fallback", {}),
        }
    except Exception as e:
        return {
            "networks": [],
            "error": "Error inesperado: {}".format(e),
            "mode": get_wifi_mode(),
            "last_connected_ssid": config.get("last_connected_ssid"),
            "fallback": config.get("fallback", {}),
        }

    networks = []
    for net in scan_results:
        ssid = net[0].decode("utf-8", "ignore")
        if not ssid:
            continue

        rssi = net[3]
        authmode = net[4]
        signal_percent = max(0, min(100, (rssi + 100) * 100 // 70))

        if signal_percent >= 70:
            signal_quality = "Excelente"
        elif signal_percent >= 50:
            signal_quality = "Buena"
        elif signal_percent >= 30:
            signal_quality = "Regular"
        else:
            signal_quality = "Debil"

        networks.append({
            "ssid": ssid,
            "rssi": rssi,
            "signal_percent": signal_percent,
            "signal_quality": signal_quality,
            "security": _authmode_to_string(authmode),
        })

    networks.sort(key=lambda item: item["rssi"], reverse=True)
    return {
        "networks": networks[:limit],
        "error": None,
        "mode": get_wifi_mode(),
        "last_connected_ssid": config.get("last_connected_ssid"),
        "fallback": config.get("fallback", {}),
    }


def get_wifi_config_summary():
    config = load_wifi_config()
    summary_networks = []
    for entry in _sorted_networks(config):
        summary_networks.append({
            "ssid": entry["ssid"],
            "priority": entry["priority"],
            "enabled": entry["enabled"],
            "has_password": bool(entry["password"]),
        })

    return {
        "mode": get_wifi_mode(),
        "ip": get_active_ip(),
        "last_connected_ssid": config.get("last_connected_ssid"),
        "known_networks": summary_networks,
        "setup_ap": {
            "ssid": config["setup_ap"]["ssid"],
            "password": config["setup_ap"]["password"],
            "channel": config["setup_ap"]["channel"],
            "enabled": config["setup_ap"]["enabled"],
        },
        "fallback": config["fallback"],
    }


def add_or_update_network(ssid, password, priority=10, enabled=True):
    config = load_wifi_config()
    ssid = str(ssid).strip()
    if not ssid:
        raise ValueError("ssid es obligatorio")

    updated = False
    for entry in config["known_networks"]:
        if entry.get("ssid") == ssid:
            if password is not None:
                entry["password"] = str(password)
            entry["priority"] = int(priority)
            entry["enabled"] = bool(enabled)
            updated = True
            break

    if not updated:
        if password is None or str(password) == "":
            raise ValueError("password es obligatorio para una red nueva")
        config["known_networks"].append({
            "ssid": ssid,
            "password": str(password),
            "priority": int(priority),
            "enabled": bool(enabled),
        })

    save_wifi_config(config)
    return get_wifi_config_summary()


def delete_network(ssid):
    config = load_wifi_config()
    ssid = str(ssid).strip()
    config["known_networks"] = [
        entry for entry in config["known_networks"] if entry.get("ssid") != ssid
    ]
    if config.get("last_connected_ssid") == ssid:
        config["last_connected_ssid"] = None
    save_wifi_config(config)
    return get_wifi_config_summary()


def reset_wifi_config():
    global _current_ssid, _mode, _last_connection_error

    config = _build_default_config()
    save_wifi_config(config)
    _current_ssid = None
    _mode = "offline"
    _last_connection_error = None

    try:
        _get_sta_wlan().disconnect()
    except Exception:
        pass

    start_setup_ap(verbose=True)
    return get_wifi_config_summary()


def update_setup_ap_password(password):
    config = load_wifi_config()
    password = str(password).strip()
    if len(password) < 8:
        raise ValueError("password del setup AP debe tener al menos 8 caracteres")

    config["setup_ap"]["password"] = password
    save_wifi_config(config)

    if get_wifi_mode() == "setup_ap":
        start_setup_ap(verbose=False)

    return get_wifi_config_summary()


def connect_to_known_network(ssid=None, verbose=True):
    config = load_wifi_config()
    if ssid:
        config["last_connected_ssid"] = ssid
        save_wifi_config(config)
    return connect_wifi(do_scan=True, verbose=verbose, retries_per_network=1)


def get_setup_ap_credentials():
    config = load_wifi_config()
    return config["setup_ap"]["ssid"], config["setup_ap"]["password"]


def sync_identity_settings(restart_ap=False):
    config = load_wifi_config()
    config["setup_ap"]["ssid"] = _build_setup_ap_ssid()
    save_wifi_config(config)

    if restart_ap and get_wifi_mode() == "setup_ap":
        start_setup_ap(verbose=False)

    return get_wifi_config_summary()


def get_last_test_result():
    return _last_test_result or {
        "success": False,
        "ssid": None,
        "ip": None,
        "message": "Sin prueba reciente",
    }


def test_wifi_credentials(ssid, password, timeout_seconds=None):
    global _last_test_result, _last_connection_error

    ssid = str(ssid or "").strip()
    password = "" if password is None else str(password)
    if not ssid:
        raise ValueError("ssid es obligatorio")

    wlan = _init_sta()
    visible_ssids = _scan_visible_ssids(wlan)
    if visible_ssids and ssid not in visible_ssids:
        _last_connection_error = "ssid_not_visible"
        _last_test_result = {
            "success": False,
            "ssid": ssid,
            "ip": None,
            "message": "La red no aparece en el escaneo actual",
        }
        return _last_test_result

    try:
        wlan.disconnect()
        time.sleep(0.4)
    except Exception:
        pass

    wlan.connect(ssid, password)
    started_at = time.time()
    timeout_seconds = timeout_seconds or DEFAULT_CONNECT_TIMEOUT

    while time.time() - started_at < timeout_seconds:
        if wlan.isconnected():
            ip = None
            try:
                ip = wlan.ifconfig()[0]
            except Exception:
                ip = None
            try:
                wlan.disconnect()
            except Exception:
                pass

            _last_connection_error = None
            _last_test_result = {
                "success": True,
                "ssid": ssid,
                "ip": ip,
                "message": "Conexion valida. El guardado final y el reinicio siguen siendo requeridos.",
            }
            return _last_test_result
        time.sleep(1)

    status = None
    try:
        status = wlan.status()
    except Exception:
        status = None

    if status == network.STAT_WRONG_PASSWORD:
        _last_connection_error = "wrong_password"
        message = "Password incorrecta"
    elif status == network.STAT_NO_AP_FOUND:
        _last_connection_error = "no_ap_found"
        message = "No se encontro el AP"
    else:
        _last_connection_error = "connect_fail"
        message = "No se pudo establecer la conexion"

    try:
        wlan.disconnect()
    except Exception:
        pass

    _last_test_result = {
        "success": False,
        "ssid": ssid,
        "ip": None,
        "message": message,
    }
    return _last_test_result
