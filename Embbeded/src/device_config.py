"""
Gestión de configuración persistente del dispositivo IoT.
Maneja: board_id (MAC), latitud, longitud, y otras configuraciones.
"""

import ujson as json
import network

CONFIG_FILE = "device_config.json"

# Configuración por defecto
DEFAULT_CONFIG = {
    "board_id": None,           # Se inicializa con MAC al primer uso
    "deployment_id": None,      # ID único del deployment actual
    "deployment_counter": 0,    # Contador incremental para deployments
    "latitude": 0.0,            # Configurar desde la UI
    "longitude": 0.0,           # Configurar desde la UI
    "sensor_type": "SCD41",     # Tipo de sensor principal
    "location_name": "",        # Nombre descriptivo opcional
    "sample_interval": 300,     # Intervalo de muestreo del sensor (5 minutos por defecto)
    "questdb_interval": 1200,   # Intervalo de envío a QuestDB (20 minutos por defecto)
    "device_registered": False  # Flag para saber si el device ya está registrado en QuestDB
}

_config_cache = None


def get_mac_address():
    """
    Obtiene la dirección MAC de la interfaz WiFi del Pico W.
    Retorna string en formato: 'AABBCCDDEEFF'
    """
    try:
        wlan = network.WLAN(network.STA_IF)
        mac_bytes = wlan.config('mac')
        # Convertir bytes a string hexadecimal sin separadores
        mac_str = ''.join(['{:02X}'.format(b) for b in mac_bytes])
        return mac_str
    except Exception as e:
        print(f"⚠️ Error obteniendo MAC address: {e}")
        return "UNKNOWN_MAC"


def load_config():
    """
    Carga la configuración desde el archivo JSON.
    Si no existe, crea uno con valores por defecto.
    Retorna diccionario con la configuración.
    """
    global _config_cache

    # Si ya está en cache, retornar
    if _config_cache is not None:
        return _config_cache

    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            print(f"✓ Configuración cargada desde {CONFIG_FILE}")
            _config_cache = config
            return config
    except OSError:
        # Archivo no existe, crear uno nuevo
        print(f"⚠️ {CONFIG_FILE} no encontrado, creando con valores por defecto...")
        config = DEFAULT_CONFIG.copy()
        config["board_id"] = get_mac_address()
        save_config(config)
        _config_cache = config
        return config
    except Exception as e:
        print(f"✗ Error cargando configuración: {e}")
        # En caso de error, usar valores por defecto
        config = DEFAULT_CONFIG.copy()
        config["board_id"] = get_mac_address()
        _config_cache = config
        return config


def save_config(config):
    """
    Guarda la configuración en el archivo JSON.
    Retorna True si tuvo éxito, False si hubo error.
    """
    global _config_cache

    try:
        # Validar que board_id exista
        if not config.get("board_id"):
            config["board_id"] = get_mac_address()

        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f)
        print(f"✓ Configuración guardada en {CONFIG_FILE}")
        _config_cache = config
        return True
    except Exception as e:
        print(f"✗ Error guardando configuración: {e}")
        return False


def get_board_id():
    """Retorna el board_id (MAC address)"""
    config = load_config()
    return config.get("board_id", get_mac_address())


def get_location():
    """Retorna tupla (latitude, longitude)"""
    config = load_config()
    return (
        float(config.get("latitude", 0.0)),
        float(config.get("longitude", 0.0))
    )


def set_location(latitude, longitude, location_name=""):
    """
    Actualiza la ubicación del dispositivo.

    Args:
        latitude: Latitud en grados decimales
        longitude: Longitud en grados decimales
        location_name: Nombre descriptivo opcional

    Returns:
        True si se guardó exitosamente, False si hubo error
    """
    config = load_config()
    config["latitude"] = float(latitude)
    config["longitude"] = float(longitude)
    if location_name:
        config["location_name"] = location_name
    return save_config(config)


def get_sensor_type():
    """Retorna el tipo de sensor principal"""
    config = load_config()
    return config.get("sensor_type", "SCD41")


def get_sample_interval():
    """Retorna el intervalo de muestreo del sensor en segundos"""
    config = load_config()
    return int(config.get("sample_interval", 300))


def get_questdb_interval():
    """Retorna el intervalo de envío a QuestDB en segundos"""
    config = load_config()
    return int(config.get("questdb_interval", 1200))


def set_intervals(sample_interval, questdb_interval):
    """
    Actualiza los intervalos de muestreo y envío.

    Args:
        sample_interval: Intervalo de muestreo del sensor en segundos
        questdb_interval: Intervalo de envío a QuestDB en segundos

    Returns:
        True si se guardó exitosamente, False si hubo error
    """
    config = load_config()
    config["sample_interval"] = int(sample_interval)
    config["questdb_interval"] = int(questdb_interval)
    return save_config(config)


def get_config_dict():
    """Retorna todo el diccionario de configuración"""
    return load_config()


def update_config(updates):
    """
    Actualiza múltiples campos de configuración.

    Args:
        updates: Diccionario con los campos a actualizar

    Returns:
        True si se guardó exitosamente, False si hubo error
    """
    config = load_config()
    config.update(updates)
    return save_config(config)


def reset_config():
    """
    Resetea la configuración a valores por defecto.
    Mantiene el board_id (MAC).
    """
    config = DEFAULT_CONFIG.copy()
    config["board_id"] = get_mac_address()
    return save_config(config)


def print_config():
    """Imprime la configuración actual (útil para debugging)"""
    config = load_config()
    print("\n" + "="*50)
    print("CONFIGURACIÓN DEL DISPOSITIVO")
    print("="*50)
    print(f"Board ID:           {config.get('board_id', 'N/A')}")
    print(f"Deployment ID:      {config.get('deployment_id', '(sin deployment)')}")
    print(f"Sensor Type:        {config.get('sensor_type', 'N/A')}")
    print(f"Latitud:            {config.get('latitude', 0.0)}")
    print(f"Longitud:           {config.get('longitude', 0.0)}")
    print(f"Ubicación:          {config.get('location_name', '(sin nombre)')}")
    print(f"Intervalo Sensing:  {config.get('sample_interval', 300)}s")
    print(f"Intervalo QuestDB:  {config.get('questdb_interval', 1200)}s")
    print(f"Device Registered:  {config.get('device_registered', False)}")
    print("="*50 + "\n")


# ==================== FUNCIONES DE DEPLOYMENT ====================

def get_deployment_id():
    """Retorna el deployment_id actual o None si no existe"""
    config = load_config()
    return config.get("deployment_id")


def set_deployment_id(deployment_id):
    """
    Actualiza el deployment_id en la configuración.

    Args:
        deployment_id: El nuevo ID de deployment

    Returns:
        True si se guardó exitosamente, False si hubo error
    """
    config = load_config()
    config["deployment_id"] = deployment_id
    return save_config(config)


def generate_deployment_id():
    """
    Genera un nuevo deployment_id con formato: {board_id}_{counter:03d}
    Incrementa el contador y lo guarda en la configuración.

    Returns:
        String con el nuevo deployment_id (ej: "AABBCCDDEEFF_001")
    """
    config = load_config()
    board_id = config.get("board_id") or get_mac_address()
    counter = config.get("deployment_counter", 0) + 1

    deployment_id = f"{board_id}_{counter:03d}"

    # Actualizar contador en config
    config["deployment_counter"] = counter
    config["deployment_id"] = deployment_id
    save_config(config)

    return deployment_id


def is_device_registered():
    """Retorna True si el device ya está registrado en QuestDB"""
    config = load_config()
    return config.get("device_registered", False)


def set_device_registered(registered):
    """
    Marca el device como registrado o no registrado.

    Args:
        registered: True si el device está registrado, False si no

    Returns:
        True si se guardó exitosamente, False si hubo error
    """
    config = load_config()
    config["device_registered"] = bool(registered)
    return save_config(config)


def create_new_deployment(latitude, longitude, location_name=""):
    """
    Crea un nuevo deployment: genera ID, actualiza ubicación y guarda config.

    Args:
        latitude: Latitud en grados decimales
        longitude: Longitud en grados decimales
        location_name: Nombre descriptivo opcional del lugar

    Returns:
        String con el nuevo deployment_id generado
    """
    config = load_config()
    board_id = config.get("board_id") or get_mac_address()
    counter = config.get("deployment_counter", 0) + 1

    deployment_id = f"{board_id}_{counter:03d}"

    # Actualizar toda la configuración
    config["deployment_counter"] = counter
    config["deployment_id"] = deployment_id
    config["latitude"] = float(latitude)
    config["longitude"] = float(longitude)
    if location_name:
        config["location_name"] = location_name

    save_config(config)

    return deployment_id


def get_location_name():
    """Retorna el nombre de la ubicación actual"""
    config = load_config()
    return config.get("location_name", "")
