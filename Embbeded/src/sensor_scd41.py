import timer_service
from machine import Pin, I2C
from scd4x import SCD4X

# Intervalo entre lecturas "lógicas" (tu dashboard)
# Se carga desde device_config.json al iniciar (ver main.py)
SAMPLE_INTERVAL = 20       # 20 segundos por defecto (configurable en tiempo de ejecución)

# Ventana de warm-up durante la cual ignoramos errores del sensor
WARMUP_SECONDS = 30        # ajustable según veas

# Estado global interno del módulo
_i2c = None
_scd = None
_last_sample = -999999  # Valor negativo para forzar lectura inmediata en el primer ciclo
START_TIME = timer_service.get_current_epoch_utc()

latest_readings = {
    "co2": None,      # null hasta que haya lectura válida
    "temp": None,     # null hasta que haya lectura válida
    "rh": None,       # null hasta que haya lectura válida
    "last_ok": 0,
    "errors": 0,
    "sample_interval": SAMPLE_INTERVAL,
}


def init_sensor():
    """
    Inicializa el bus I2C y el SCD41, y arranca la medición periódica.
    Debe llamarse una sola vez al inicio del programa.
    """
    global _i2c, _scd, START_TIME, _last_sample

    import time  # Necesario solo para sleep

    _i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=100_000)
    _scd = SCD4X(_i2c)

    _scd.start_periodic_measurement()
    print("SCD41: medición periódica iniciada (intervalo hardware ~5 s)")

    # Warm-up inicial recomendado por Sensirion
    time.sleep(10)

    START_TIME = timer_service.get_current_epoch_utc()
    # Mantener _last_sample negativo para forzar lectura inmediata en el próximo ciclo
    # No resetear a 0 aquí


def set_sample_interval(seconds):
    """
    Cambia el intervalo de muestreo dinámicamente.
    Actualiza tanto la variable global como el diccionario latest_readings.
    """
    global SAMPLE_INTERVAL
    SAMPLE_INTERVAL = seconds
    latest_readings["sample_interval"] = seconds
    print(f"⏱ Intervalo de muestreo cambiado a {seconds} segundos")


def update_sensor():
    """
    Actualiza latest_readings como máximo una vez cada SAMPLE_INTERVAL.
    Tolera errores del bus I2C y fase de warm-up del sensor.
    Llamar a esta función en el loop principal.
    """
    global _last_sample

    if _scd is None:
        # init_sensor() no ha sido llamado todavía
        return

    now = timer_service.get_current_epoch_utc()
    if now - _last_sample < SAMPLE_INTERVAL:
        return  # aún no toca nueva lectura

    _last_sample = now
    in_warmup = (now - START_TIME) < WARMUP_SECONDS

    try:
        if _scd.get_data_ready():
            co2, temp, rh = _scd.read_measurement()

            latest_readings["co2"] = float(co2)
            latest_readings["temp"] = float(temp)
            latest_readings["rh"] = float(rh)
            latest_readings["last_ok"] = now

            msg = f"SCD41 → CO2={co2}, Temp={temp}, RH={rh}"
            if in_warmup:
                print("WARM-UP", msg)
            else:
                print("OK", msg)
        else:
            if in_warmup:
                print("⏳ SCD41 (warm-up): aún sin datos listos.")
            else:
                print("⏳ SCD41: No hay datos listos aún (data_ready=0)")

    except Exception as e:
        if in_warmup:
            print("⚠️ Warm-up SCD41, error esperado:", e)
            print("   → Se ignora y se intentará de nuevo.")
        else:
            latest_readings["errors"] += 1
            print("⚠️ Error leyendo SCD41:", e)
            print("   → Se mantiene la última lectura válida")


def get_latest_readings():
    """Devuelve el diccionario con las últimas lecturas del sensor."""
    return latest_readings
