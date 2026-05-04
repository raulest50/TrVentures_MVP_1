"""
Gestion de configuracion persistente del dispositivo IoT.
Maneja: board_id (MAC), deployment_id, ubicacion, intervalos y URL base del backend.
"""

import ujson as json
import network

CONFIG_FILE = "device_config.json"

DEFAULT_CONFIG = {
    "board_id": None,
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
}

_config_cache = None


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
            config = json.load(f)
            print(f"Configuracion cargada desde {CONFIG_FILE}")
            _config_cache = config
            return config
    except OSError:
        print(f"{CONFIG_FILE} no encontrado, creando con valores por defecto...")
        config = DEFAULT_CONFIG.copy()
        config["board_id"] = get_mac_address()
        save_config(config)
        _config_cache = config
        return config
    except Exception as e:
        print(f"Error cargando configuracion: {e}")
        config = DEFAULT_CONFIG.copy()
        config["board_id"] = get_mac_address()
        _config_cache = config
        return config


def save_config(config):
    """
    Guarda la configuracion en el archivo JSON.
    Retorna True si tuvo exito, False si hubo error.
    """
    global _config_cache

    try:
        if not config.get("board_id"):
            config["board_id"] = get_mac_address()

        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f)

        print(f"Configuracion guardada en {CONFIG_FILE}")
        _config_cache = config
        return True
    except Exception as e:
        print(f"Error guardando configuracion: {e}")
        return False


def get_board_id():
    config = load_config()
    return config.get("board_id", get_mac_address())


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
    return load_config()


def get_api_base_url():
    config = load_config()
    return config.get("api_base_url", "https://api.fronteradatalabs.com")


def update_config(updates):
    config = load_config()
    config.update(updates)
    return save_config(config)


def reset_config():
    config = DEFAULT_CONFIG.copy()
    config["board_id"] = get_mac_address()
    return save_config(config)


def print_config():
    config = load_config()
    board_id = config.get("board_id", "N/A")
    deployment_id = config.get("deployment_id", "(sin deployment)")
    sensor_type = config.get("sensor_type", "N/A")
    latitude = config.get("latitude", 0.0)
    longitude = config.get("longitude", 0.0)
    location_name = config.get("location_name", "(sin nombre)")
    api_base_url = config.get("api_base_url", "https://api.fronteradatalabs.com")
    sample_interval = config.get("sample_interval", 300)
    questdb_interval = config.get("questdb_interval", 1200)
    device_registered = config.get("device_registered", False)

    print("\n" + "=" * 50)
    print("CONFIGURACION DEL DISPOSITIVO")
    print("=" * 50)
    print("Board ID:           {}".format(board_id))
    print("Deployment ID:      {}".format(deployment_id))
    print("Sensor Type:        {}".format(sensor_type))
    print("Latitud:            {}".format(latitude))
    print("Longitud:           {}".format(longitude))
    print("Ubicacion:          {}".format(location_name))
    print("API Base URL:       {}".format(api_base_url))
    print("Intervalo Sensing:  {}s".format(sample_interval))
    print("Intervalo QuestDB:  {}s".format(questdb_interval))
    print("Device Registered:  {}".format(device_registered))
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
