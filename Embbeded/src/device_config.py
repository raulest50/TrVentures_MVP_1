"""
Gestion de configuracion persistente del dispositivo IoT.
Maneja: board_id (MAC), deployment_id, ubicacion, intervalos y URL base del backend.
"""

import ujson as json
import network

CONFIG_FILE = "device_config.json"

DEFAULT_CONFIG = {
    "board_id": None,
    "board_name": None,
    "deployment_id": None,
    "deployment_counter": 0,
    "latitude": 0.0,
    "longitude": 0.0,
    "sensor_type": "SCD41",
    "location_name": "",
    "sample_interval": 20,         # 20 segundos para lecturas rápidas del sensor
    "questdb_interval": 1200,      # 20 minutos para envío al backend (no saturar)
    "device_registered": False,
    "api_base_url": "https://api.fronteradatalabs.com",
    "cloud_upload_enabled": False,
    "operation_mode": "normal",
    "mdns_enabled": True,
    "mdns_hostname": None,
    "last_local_ip": None,
    "last_local_ssid": None,
}

_config_cache = None


def _is_ascii_alnum(char):
    if not char:
        return False
    code = ord(char)
    return (
        48 <= code <= 57 or
        65 <= code <= 90 or
        97 <= code <= 122
    )


def _to_ascii_lower(char):
    if not char:
        return char
    code = ord(char)
    if 65 <= code <= 90:
        return chr(code + 32)
    return char


def _default_board_name(board_id):
    board_id = str(board_id or get_mac_address()).strip().upper()
    suffix = board_id[-6:] if len(board_id) >= 6 else board_id or "NODE"
    return "node-{}".format(suffix)


def _sanitize_board_name(value, fallback=None):
    raw = str(value or "").strip()
    if not raw:
        raw = fallback or _default_board_name(get_mac_address())

    cleaned = []
    previous_separator = False
    for char in raw:
        if _is_ascii_alnum(char):
            cleaned.append(char)
            previous_separator = False
        elif char in (" ", "-", "_"):
            if not previous_separator and cleaned:
                cleaned.append("-")
            previous_separator = True

    normalized = "".join(cleaned).strip("-")
    if not normalized:
        normalized = fallback or _default_board_name(get_mac_address())
    return normalized[:24]


def _derive_mdns_hostname(board_name, fallback=None):
    source = _sanitize_board_name(board_name, fallback=fallback)
    slug = []
    for char in source:
        lowered = _to_ascii_lower(char)
        if _is_ascii_alnum(lowered):
            slug.append(lowered)
        elif lowered in (" ", "-", "_") and slug and slug[-1] != "-":
            slug.append("-")

    hostname = "".join(slug).strip("-")
    if not hostname:
        hostname = _sanitize_board_name(fallback or _default_board_name(get_mac_address())).lower()
    return hostname[:32]


def _normalize_config(config):
    normalized = DEFAULT_CONFIG.copy()
    if isinstance(config, dict):
        normalized.update(config)

    if not normalized.get("board_id"):
        normalized["board_id"] = get_mac_address()

    fallback_name = _default_board_name(normalized["board_id"])
    normalized["board_name"] = _sanitize_board_name(normalized.get("board_name"), fallback=fallback_name)
    normalized["mdns_enabled"] = bool(normalized.get("mdns_enabled", True))
    normalized["mdns_hostname"] = _derive_mdns_hostname(
        normalized["board_name"],
        fallback=fallback_name,
    )
    normalized["last_local_ip"] = normalized.get("last_local_ip") or None
    normalized["last_local_ssid"] = normalized.get("last_local_ssid") or None

    mode = str(normalized.get("operation_mode", "normal")).strip().lower()
    if mode not in ("setup", "normal"):
        mode = "normal"
    normalized["operation_mode"] = mode

    return normalized


def get_mac_address():
    """
    Obtiene la direccion MAC de la interfaz WiFi del Pico W.
    Retorna string en formato: 'AABBCCDDEEFF'
    """
    try:
        wlan = network.WLAN(network.STA_IF)
        mac_bytes = wlan.config("mac")
        return "".join(["{:02X}".format(b) for b in mac_bytes])
    except Exception as e:
        print(f"Error obteniendo MAC address: {e}")
        return "UNKNOWN_MAC"


def load_config():
    """
    Carga la configuracion desde el archivo JSON.
    Si no existe, crea uno con valores por defecto.
    """
    global _config_cache

    if _config_cache is not None:
        return _config_cache

    try:
        with open(CONFIG_FILE, "r") as f:
            loaded = json.load(f)
            config = _normalize_config(loaded)
            print(f"Configuracion cargada desde {CONFIG_FILE}")
            _config_cache = config
            return config
    except OSError:
        print(f"{CONFIG_FILE} no encontrado, creando con valores por defecto...")
        config = _normalize_config({})
        save_config(config)
        _config_cache = config
        return config
    except Exception as e:
        print(f"Error cargando configuracion: {e}")
        config = _normalize_config({})
        _config_cache = config
        return config


def save_config(config):
    """
    Guarda la configuracion en el archivo JSON.
    Retorna True si tuvo exito, False si hubo error.
    """
    global _config_cache

    try:
        normalized = _normalize_config(config)

        with open(CONFIG_FILE, "w") as f:
            json.dump(normalized, f)

        print(f"Configuracion guardada en {CONFIG_FILE}")
        _config_cache = normalized
        return True
    except Exception as e:
        print(f"Error guardando configuracion: {e}")
        return False


def get_board_id():
    config = load_config()
    return config.get("board_id", get_mac_address())


def get_board_name():
    config = load_config()
    return config.get("board_name", _default_board_name(get_board_id()))


def set_board_name(name):
    config = load_config()
    config["board_name"] = _sanitize_board_name(name, fallback=_default_board_name(config.get("board_id")))
    return save_config(config)


def get_mdns_hostname():
    config = load_config()
    return config.get("mdns_hostname", _derive_mdns_hostname(get_board_name()))


def is_mdns_enabled():
    config = load_config()
    return bool(config.get("mdns_enabled", True))


def set_mdns_enabled(enabled):
    config = load_config()
    config["mdns_enabled"] = bool(enabled)
    return save_config(config)


def set_last_local_network(ip=None, ssid=None):
    config = load_config()
    config["last_local_ip"] = str(ip).strip() if ip else None
    config["last_local_ssid"] = str(ssid).strip() if ssid else None
    return save_config(config)


def get_location():
    config = load_config()
    return (
        float(config.get("latitude", 0.0)),
        float(config.get("longitude", 0.0)),
    )


def set_location(latitude, longitude, location_name=""):
    config = load_config()
    config["latitude"] = float(latitude)
    config["longitude"] = float(longitude)
    if location_name:
        config["location_name"] = location_name
    return save_config(config)


def get_sensor_type():
    config = load_config()
    return config.get("sensor_type", "SCD41")


def get_sample_interval():
    config = load_config()
    return int(config.get("sample_interval", 300))


def get_questdb_interval():
    config = load_config()
    return int(config.get("questdb_interval", 1200))


def set_intervals(sample_interval, questdb_interval):
    config = load_config()
    config["sample_interval"] = int(sample_interval)
    config["questdb_interval"] = int(questdb_interval)
    return save_config(config)


def get_config_dict():
    return _normalize_config(load_config())


def get_api_base_url():
    config = load_config()
    return config.get("api_base_url", "https://api.fronteradatalabs.com")


def update_config(updates):
    config = load_config()
    config.update(updates)
    return save_config(config)


def reset_config():
    config = _normalize_config({})
    return save_config(config)


def print_config():
    config = load_config()
    board_id = config.get("board_id", "N/A")
    board_name = config.get("board_name", "(sin nombre)")
    deployment_id = config.get("deployment_id", "(sin deployment)")
    sensor_type = config.get("sensor_type", "N/A")
    latitude = config.get("latitude", 0.0)
    longitude = config.get("longitude", 0.0)
    location_name = config.get("location_name", "(sin nombre)")
    api_base_url = config.get("api_base_url", "https://api.fronteradatalabs.com")
    sample_interval = config.get("sample_interval", 300)
    questdb_interval = config.get("questdb_interval", 1200)
    device_registered = config.get("device_registered", False)
    cloud_upload_enabled = config.get("cloud_upload_enabled", False)
    operation_mode = config.get("operation_mode", "normal")
    mdns_enabled = config.get("mdns_enabled", True)
    mdns_hostname = config.get("mdns_hostname", "--")
    last_local_ip = config.get("last_local_ip", "--")
    last_local_ssid = config.get("last_local_ssid", "--")

    print("\n" + "=" * 50)
    print("CONFIGURACION DEL DISPOSITIVO")
    print("=" * 50)
    print("Board ID:           {}".format(board_id))
    print("Board Name:         {}".format(board_name))
    print("Deployment ID:      {}".format(deployment_id))
    print("Sensor Type:        {}".format(sensor_type))
    print("Latitud:            {}".format(latitude))
    print("Longitud:           {}".format(longitude))
    print("Ubicacion:          {}".format(location_name))
    print("API Base URL:       {}".format(api_base_url))
    print("Intervalo Sensing:  {}s".format(sample_interval))
    print("Intervalo QuestDB:  {}s".format(questdb_interval))
    print("Device Registered:  {}".format(device_registered))
    print("Cloud Upload:       {}".format(cloud_upload_enabled))
    print("Operation Mode:     {}".format(operation_mode))
    print("mDNS Enabled:       {}".format(mdns_enabled))
    print("mDNS Hostname:      {}".format(mdns_hostname))
    print("Last Local IP:      {}".format(last_local_ip))
    print("Last Local SSID:    {}".format(last_local_ssid))
    print("=" * 50 + "\n")


def get_deployment_id():
    config = load_config()
    return config.get("deployment_id")


def set_deployment_id(deployment_id):
    config = load_config()
    config["deployment_id"] = deployment_id
    return save_config(config)


def _extract_deployment_counter(deployment_id):
    try:
        if not deployment_id or "_" not in deployment_id:
            return None
        suffix = deployment_id.rsplit("_", 1)[1]
        return int(suffix)
    except Exception:
        return None


def peek_next_deployment_id():
    config = load_config()
    board_id = config.get("board_id") or get_mac_address()
    counter = int(config.get("deployment_counter", 0)) + 1
    return f"{board_id}_{counter:03d}"


def activate_deployment(deployment_id, latitude=None, longitude=None, location_name=None):
    config = load_config()
    config["deployment_id"] = deployment_id

    counter = _extract_deployment_counter(deployment_id)
    if counter is not None:
        config["deployment_counter"] = max(int(config.get("deployment_counter", 0)), counter)

    if latitude is not None:
        config["latitude"] = float(latitude)
    if longitude is not None:
        config["longitude"] = float(longitude)
    if location_name is not None:
        config["location_name"] = location_name

    return save_config(config)


def generate_deployment_id():
    deployment_id = peek_next_deployment_id()
    activate_deployment(deployment_id)
    return deployment_id


def is_device_registered():
    config = load_config()
    return config.get("device_registered", False)


def set_device_registered(registered):
    config = load_config()
    config["device_registered"] = bool(registered)
    return save_config(config)


def create_new_deployment(latitude, longitude, location_name=""):
    deployment_id = peek_next_deployment_id()
    activate_deployment(deployment_id, latitude, longitude, location_name or "")
    return deployment_id


def get_location_name():
    config = load_config()
    return config.get("location_name", "")


def is_cloud_upload_enabled():
    config = load_config()
    return bool(config.get("cloud_upload_enabled", False))


def set_cloud_upload_enabled(enabled):
    config = load_config()
    config["cloud_upload_enabled"] = bool(enabled)
    return save_config(config)


def get_operation_mode():
    config = load_config()
    mode = str(config.get("operation_mode", "normal")).strip().lower()
    if mode not in ("setup", "normal"):
        mode = "normal"
    return mode


def set_operation_mode(mode):
    normalized = str(mode or "normal").strip().lower()
    if normalized not in ("setup", "normal"):
        raise ValueError("operation_mode debe ser 'setup' o 'normal'")

    config = load_config()
    config["operation_mode"] = normalized
    return save_config(config)
