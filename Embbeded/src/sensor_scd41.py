import time
from machine import Pin, I2C
from scd4x import SCD4X

# Intervalo entre lecturas "lógicas" (tu dashboard)
SAMPLE_INTERVAL = 20       # segundos

# Ventana de warm-up durante la cual ignoramos errores del sensor
WARMUP_SECONDS = 30        # ajustable según veas

# Estado global interno del módulo
_i2c = None
_scd = None
_last_sample = 0
START_TIME = time.time()

latest_readings = {
    "co2": None,
    "temp": None,
    "rh": None,
    "last_ok": None,
    "errors": 0,
}


def init_sensor():
    """
    Inicializa el bus I2C y el SCD41, y arranca la medición periódica.
    Debe llamarse una sola vez al inicio del programa.
    """
    global _i2c, _scd, START_TIME, _last_sample

    _i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=100_000)
    _scd = SCD4X(_i2c)

    _scd.start_periodic_measurement()
    print("SCD41: medición periódica iniciada (intervalo hardware ~5 s)")

    # Warm-up inicial recomendado por Sensirion
    time.sleep(10)

    START_TIME = time.time()
    _last_sample = 0


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

    now = time.time()
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
