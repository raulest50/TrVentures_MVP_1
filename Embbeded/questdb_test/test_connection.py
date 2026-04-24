"""
Script de prueba para validar conexion y operaciones basicas con QuestDB.
Uso administrativo/local. El firmware productivo ahora envia al backend API.
"""

import os
import time

import requests

QUESTDB_SCHEME = "https"
QUESTDB_HOST = "questdb.fronteradatalabs.com"
QUESTDB_USER = os.getenv("QDB_HTTP_USER", "change-me")
QUESTDB_PASSWORD = os.getenv("QDB_HTTP_PASSWORD", "change-me")

BASE_URL = f"{QUESTDB_SCHEME}://{QUESTDB_HOST}"
EXEC_URL = f"{BASE_URL}/exec"
WRITE_URL = f"{BASE_URL}/write"

HEADERS = {
    "User-Agent": "FronteraDataLabs questdb_test connection",
    "Accept": "*/*",
    "Connection": "keep-alive",
}

session = requests.Session()
session.headers.update(HEADERS)
session.auth = (QUESTDB_USER, QUESTDB_PASSWORD)


def crear_tabla():
    query = """
    CREATE TABLE IF NOT EXISTS sensor_test (
        timestamp TIMESTAMP,
        sensor_id SYMBOL,
        temperatura DOUBLE,
        humedad DOUBLE
    ) timestamp(timestamp) PARTITION BY DAY;
    """

    try:
        response = session.get(EXEC_URL, params={"query": query}, timeout=(5, 10))
        if response.status_code == 200:
            print("Tabla creada exitosamente")
            return True
        print(f"Error al crear tabla: {response.status_code}")
        print(f"Respuesta: {response.text}")
        return False
    except Exception as e:
        print(f"Error de conexion: {e}")
        return False


def insertar_datos_ficticios():
    datos = [
        ("sensor_01", 25.5, 60.2),
        ("sensor_01", 26.1, 58.7),
        ("sensor_02", 22.3, 65.4),
        ("sensor_02", 23.0, 64.1),
    ]

    print("\nInsertando datos ficticios usando ILP...")
    now_ns = int(time.time() * 1e9)
    lines = []
    for i, (sensor_id, temp, hum) in enumerate(datos):
        ts = now_ns + i * 1_000_000_000
        lines.append(f"sensor_test,sensor_id={sensor_id} temperatura={temp},humedad={hum} {ts}")

    payload = "\n".join(lines)

    try:
        response = session.post(
            WRITE_URL,
            data=payload,
            headers={"Content-Type": "text/plain"},
            timeout=(5, 10),
        )
        if response.status_code in [200, 204]:
            print(f"Insertados {len(datos)} registros exitosamente")
        else:
            print(f"Error al insertar: {response.status_code}")
            print(f"Respuesta: {response.text}")
    except Exception as e:
        print(f"Error: {e}")


def leer_datos():
    query = "SELECT * FROM sensor_test ORDER BY timestamp DESC LIMIT 10;"

    try:
        response = session.get(EXEC_URL, params={"query": query}, timeout=(5, 10))
        if response.status_code == 200:
            data = response.json()
            print("Datos leidos exitosamente:")
            print(data.get("dataset", []))
            return data
        print(f"Error al leer datos: {response.status_code}")
        print(f"Respuesta: {response.text}")
        return None
    except Exception as e:
        print(f"Error al leer: {e}")
        return None


def test_conexion():
    print("Probando conexion con QuestDB...")
    print(f"URL: {EXEC_URL}")

    try:
        response = session.get(
            EXEC_URL,
            params={"query": "SELECT 1;"},
            timeout=(5, 10),
        )
        if response.status_code == 200:
            print("Servidor accesible")
            print(f"Status: {response.status_code}")
            return True
        print(f"Respuesta inesperada: {response.status_code}")
        print(f"Respuesta: {response.text[:200]}")
        return False
    except requests.exceptions.Timeout as e:
        print(f"Timeout - El servidor no responde: {e}")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"Error de conexion: {e}")
        return False
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        return False


def main():
    print("=" * 60)
    print("TEST DE CONEXION Y OPERACIONES CON QUESTDB")
    print("=" * 60)
    print(f"Servidor: {BASE_URL}")

    if not test_conexion():
        print("\nNo se pudo conectar al servidor. Verifica:")
        print("- Que QuestDB este corriendo")
        print("- Que el subdominio responda por HTTPS")
        print("- Que QDB_HTTP_USER y QDB_HTTP_PASSWORD sean correctos")
        return

    print("-" * 60)
    if not crear_tabla():
        return

    print("-" * 60)
    insertar_datos_ficticios()

    print("-" * 60)
    leer_datos()

    print("=" * 60)
    print("PRUEBA COMPLETADA")
    print("=" * 60)


if __name__ == "__main__":
    main()
