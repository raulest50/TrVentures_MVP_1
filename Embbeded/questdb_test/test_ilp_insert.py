"""
Test de insercion de datos a QuestDB usando Influx Line Protocol (ILP).
Uso administrativo/local. El firmware productivo ya no usa este flujo directo.
"""

import os
import time
from datetime import datetime

import requests

QUESTDB_SCHEME = "https"
QUESTDB_HOST = "questdb.fronteradatalabs.com"
QUESTDB_USER = os.getenv("QDB_HTTP_USER", "change-me")
QUESTDB_PASSWORD = os.getenv("QDB_HTTP_PASSWORD", "change-me")
QUESTDB_WRITE_URL = f"{QUESTDB_SCHEME}://{QUESTDB_HOST}/write"

TEST_DATA = {
    "table_name": "frontera_dtlabs_v2",
    "board_id": "TEST_MAC_123456",
    "sensor_type": "SCD41",
    "co2": 420.5,
    "temp": 22.3,
    "rh": 55.8,
    "latitude": 6.2442,
    "longitude": -75.5812,
    "errors": 0,
}


def get_current_timestamp_ns():
    return int(time.time() * 1_000_000_000)


def build_ilp_line(data):
    tags = f"{data['table_name']},board_id={data['board_id']},sensor_type={data['sensor_type']}"
    timestamp_ns = get_current_timestamp_ns()
    fields = (
        f"co2={data['co2']},"
        f"temp={data['temp']},"
        f"rh={data['rh']},"
        f"latitude={data['latitude']},"
        f"longitude={data['longitude']},"
        f"errors={data['errors']}i"
    )
    return f"{tags} {fields} {timestamp_ns}"


def insert_test_data(verbose=True):
    if verbose:
        print("=" * 70)
        print("INSERTANDO DATO DE PRUEBA A QUESTDB")
        print("=" * 70)

    ilp_line = build_ilp_line(TEST_DATA)
    if verbose:
        print(f"Linea ILP: {ilp_line}")
        print(f"Destino: {QUESTDB_WRITE_URL}")

    try:
        response = requests.post(
            QUESTDB_WRITE_URL,
            data=ilp_line,
            headers={"Content-Type": "text/plain"},
            auth=(QUESTDB_USER, QUESTDB_PASSWORD),
            timeout=10,
        )
        if response.status_code in [200, 204]:
            print("Exito insertando dato de prueba")
            return True

        print(f"Error - Status Code: {response.status_code}")
        print(f"Respuesta: {response.text[:500]}")
        return False
    except requests.exceptions.Timeout:
        print(f"Timeout al conectar con {QUESTDB_HOST}")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"No se pudo conectar con {QUESTDB_HOST}: {e}")
        return False
    except Exception as e:
        print(f"Error inesperado: {type(e).__name__}: {e}")
        return False


def query_test_data():
    print("=" * 70)
    print("VERIFICANDO DATOS INSERTADOS")
    print("=" * 70)

    query = f"""
    SELECT * FROM {TEST_DATA['table_name']}
    WHERE board_id = '{TEST_DATA['board_id']}'
    ORDER BY timestamp DESC
    LIMIT 5;
    """

    query_url = f"{QUESTDB_SCHEME}://{QUESTDB_HOST}/exec"
    try:
        response = requests.get(
            query_url,
            params={"query": query},
            auth=(QUESTDB_USER, QUESTDB_PASSWORD),
            timeout=10,
        )
        if response.status_code == 200:
            data = response.json()
            print(data.get("dataset", []))
        else:
            print(f"Error en query - Status Code: {response.status_code}")
            print(f"Respuesta: {response.text[:500]}")
    except Exception as e:
        print(f"Error al consultar: {e}")


def test_connection():
    test_url = f"{QUESTDB_SCHEME}://{QUESTDB_HOST}/exec"
    try:
        response = requests.get(
            test_url,
            params={"query": "SELECT 1;"},
            auth=(QUESTDB_USER, QUESTDB_PASSWORD),
            timeout=5,
        )
        if response.status_code == 200:
            print("Servidor QuestDB accesible")
            return True
        print(f"Respuesta inesperada: {response.status_code}")
        return False
    except Exception as e:
        print(f"Error de conexion: {e}")
        return False


def main():
    print("QUESTDB ILP INSERT TEST")
    print(f"Servidor: {QUESTDB_SCHEME}://{QUESTDB_HOST}")
    print(f"Tabla: {TEST_DATA['table_name']}")
    print(f"Board ID: {TEST_DATA['board_id']}")

    if not test_connection():
        print("Verifica HTTPS y credenciales de QuestDB.")
        return

    if insert_test_data(verbose=True):
        print("Esperando 2 segundos para que QuestDB procese...")
        time.sleep(2)
        query_test_data()
        print("Verifica tambien en QuestDB Console: https://questdb.fronteradatalabs.com")
    else:
        print("No se pudo insertar el dato de prueba")


if __name__ == "__main__":
    main()
