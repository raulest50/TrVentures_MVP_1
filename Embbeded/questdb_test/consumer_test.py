"""
Script de escritorio para consultar datos de QuestDB y graficar variables ambientales.
Uso administrativo/local. El firmware productivo ya no usa este flujo directo.
"""

import os
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import requests

QUESTDB_SCHEME = "https"
QUESTDB_HOST = "questdb.fronteradatalabs.com"
QUESTDB_USER = os.getenv("QDB_HTTP_USER", "change-me")
QUESTDB_PASSWORD = os.getenv("QDB_HTTP_PASSWORD", "change-me")

BASE_URL = f"{QUESTDB_SCHEME}://{QUESTDB_HOST}"
EXEC_URL = f"{BASE_URL}/exec"

HEADERS = {
    "User-Agent": "FronteraDataLabs questdb_test consumer",
    "Accept": "*/*",
    "Connection": "keep-alive",
}

session = requests.Session()
session.headers.update(HEADERS)
session.auth = (QUESTDB_USER, QUESTDB_PASSWORD)


def consumir_datos(limit=1000):
    query = f"""
    SELECT ts, co2, temp, rh
    FROM telemetria_datos
    ORDER BY ts DESC
    LIMIT {limit};
    """

    try:
        response = session.get(EXEC_URL, params={"query": query}, timeout=(5, 30))
        if response.status_code != 200:
            print(f"Error al consultar: {response.status_code}")
            print(f"Respuesta: {response.text}")
            return None

        data = response.json()
        rows = data.get("dataset", [])
        if not rows:
            print("No hay datos en la tabla telemetria_datos")
            return None

        timestamps = [row[0] for row in rows]
        co2_values = [row[1] for row in rows]
        temp_values = [row[2] for row in rows]
        rh_values = [row[3] for row in rows]

        print(f"{len(rows)} registros leidos exitosamente")
        return {
            "timestamps": timestamps,
            "co2": co2_values,
            "temp": temp_values,
            "rh": rh_values,
        }
    except Exception as e:
        print(f"Error: {e}")
        return None


def graficar_nube_puntos(data):
    if not data:
        print("No hay datos para graficar")
        return

    co2 = np.array(data["co2"])
    temp = np.array(data["temp"])
    rh = np.array(data["rh"])

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle("Variables ambientales - telemetria_datos", fontsize=16, fontweight="bold")

    axes[0].scatter(temp, co2, alpha=0.6, c="blue", edgecolors="black", s=50)
    axes[0].set_xlabel("Temperatura (C)")
    axes[0].set_ylabel("CO2 (ppm)")
    axes[0].set_title("CO2 vs Temperatura")
    axes[0].grid(True, alpha=0.3)

    axes[1].scatter(rh, co2, alpha=0.6, c="green", edgecolors="black", s=50)
    axes[1].set_xlabel("Humedad Relativa (%)")
    axes[1].set_ylabel("CO2 (ppm)")
    axes[1].set_title("CO2 vs Humedad")
    axes[1].grid(True, alpha=0.3)

    axes[2].scatter(rh, temp, alpha=0.6, c="red", edgecolors="black", s=50)
    axes[2].set_xlabel("Humedad Relativa (%)")
    axes[2].set_ylabel("Temperatura (C)")
    axes[2].set_title("Temperatura vs Humedad")
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()


def main():
    print("=" * 60)
    print("CONSUMER TEST - QUESTDB ADMIN")
    print("=" * 60)
    print(f"Host: {BASE_URL}")
    print("Tabla objetivo: telemetria_datos")

    data = consumir_datos(limit=1000)
    if not data:
        print("No se pudieron obtener datos. Verifica HTTPS y credenciales.")
        return

    graficar_nube_puntos(data)
    print("Completado")


if __name__ == "__main__":
    main()
