"""
Script para consumir datos de QuestDB y graficar las 3 variables ambientales
Lee datos de sensor_scd41_data y genera nube de puntos
"""

import requests
import matplotlib.pyplot as plt
from datetime import datetime
import numpy as np

# Configuración del servidor QuestDB
QUESTDB_HOST = "187.124.90.77"
QUESTDB_HTTP_PORT = 9000

# URLs
BASE_URL = f"http://{QUESTDB_HOST}:{QUESTDB_HTTP_PORT}"
EXEC_URL = f"{BASE_URL}/exec"

# Headers
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': '*/*',
    'Connection': 'keep-alive'
}

# Configuración de sesión
session = requests.Session()
session.headers.update(HEADERS)


def consumir_datos(limit=1000):
    """
    Consume datos de la tabla sensor_scd41_data
    Retorna un diccionario con las 3 variables: co2, temp, rh
    """
    query = f"""
    SELECT timestamp, co2, temp, rh
    FROM sensor_scd41_data
    ORDER BY timestamp DESC
    LIMIT {limit};
    """

    try:
        response = session.get(EXEC_URL, params={'query': query}, timeout=(5, 30))

        if response.status_code == 200:
            data = response.json()
            rows = data.get("dataset", [])

            if not rows:
                print("⚠️ No hay datos en la tabla")
                return None

            # Extraer columnas
            timestamps = [row[0] for row in rows]
            co2_values = [row[1] for row in rows]
            temp_values = [row[2] for row in rows]
            rh_values = [row[3] for row in rows]

            print(f"✓ {len(rows)} registros leídos exitosamente")
            print(f"  CO2: {min(co2_values):.0f} - {max(co2_values):.0f} ppm")
            print(f"  Temp: {min(temp_values):.1f} - {max(temp_values):.1f} °C")
            print(f"  RH: {min(rh_values):.1f} - {max(rh_values):.1f} %")

            return {
                'timestamps': timestamps,
                'co2': co2_values,
                'temp': temp_values,
                'rh': rh_values
            }
        else:
            print(f"✗ Error al consultar: {response.status_code}")
            print(f"  Respuesta: {response.text}")
            return None

    except Exception as e:
        print(f"✗ Error: {e}")
        return None


def graficar_nube_puntos(data):
    """
    Genera gráficos de nube de puntos para las 3 variables
    """
    if not data:
        print("✗ No hay datos para graficar")
        return

    co2 = np.array(data['co2'])
    temp = np.array(data['temp'])
    rh = np.array(data['rh'])

    # Crear figura con 3 subplots
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle('Variables Ambientales - Sensor SCD41', fontsize=16, fontweight='bold')

    # Subplot 1: CO2 vs Temperatura
    axes[0].scatter(temp, co2, alpha=0.6, c='blue', edgecolors='black', s=50)
    axes[0].set_xlabel('Temperatura (°C)', fontsize=12)
    axes[0].set_ylabel('CO2 (ppm)', fontsize=12)
    axes[0].set_title('CO2 vs Temperatura')
    axes[0].grid(True, alpha=0.3)

    # Subplot 2: CO2 vs Humedad
    axes[1].scatter(rh, co2, alpha=0.6, c='green', edgecolors='black', s=50)
    axes[1].set_xlabel('Humedad Relativa (%)', fontsize=12)
    axes[1].set_ylabel('CO2 (ppm)', fontsize=12)
    axes[1].set_title('CO2 vs Humedad')
    axes[1].grid(True, alpha=0.3)

    # Subplot 3: Temperatura vs Humedad
    axes[2].scatter(rh, temp, alpha=0.6, c='red', edgecolors='black', s=50)
    axes[2].set_xlabel('Humedad Relativa (%)', fontsize=12)
    axes[2].set_ylabel('Temperatura (°C)', fontsize=12)
    axes[2].set_title('Temperatura vs Humedad')
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()

    print("\n✓ Gráficos generados exitosamente")


def main():
    print("=" * 60)
    print("CONSUMER TEST - QUESTDB")
    print("=" * 60)
    print()

    # 1. Consumir datos
    print("Consultando base de datos...")
    data = consumir_datos(limit=1000)

    if not data:
        print("\n⚠️ No se pudieron obtener datos. Verifica:")
        print("  - Que el servidor QuestDB esté corriendo")
        print("  - Que la tabla sensor_scd41_data tenga datos")
        return

    print()

    # 2. Graficar
    print("Generando gráficos...")
    graficar_nube_puntos(data)

    print()
    print("=" * 60)
    print("COMPLETADO")
    print("=" * 60)


if __name__ == "__main__":
    main()
