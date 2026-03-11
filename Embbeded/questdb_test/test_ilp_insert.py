"""
Test de inserción de datos a QuestDB usando Influx Line Protocol (ILP)
Prueba el nuevo schema de frontera_dtlabs_v2

Este script inserta UN SOLO dato ficticio para verificar que:
1. La conexión a QuestDB funciona
2. El formato ILP es correcto
3. La tabla se crea automáticamente con el schema correcto
4. Los campos se insertan correctamente
"""

import requests
import time
from datetime import datetime, timezone


# ==================== CONFIGURACIÓN ====================

# QuestDB Server (VPS Hostinger)
QUESTDB_HOST = "187.124.90.77"
QUESTDB_PORT = 9000
QUESTDB_WRITE_URL = f"http://{QUESTDB_HOST}:{QUESTDB_PORT}/write"

# Datos ficticios de prueba
TEST_DATA = {
    "table_name": "frontera_dtlabs_v2",
    "board_id": "TEST_MAC_123456",
    "sensor_type": "SCD41",
    "co2": 420.5,
    "temp": 22.3,
    "rh": 55.8,
    "latitude": 6.2442,      # Medellín, Colombia
    "longitude": -75.5812,
    "errors": 0
}


# ==================== FUNCIONES ====================

def get_current_timestamp_ns():
    """Retorna timestamp actual en nanosegundos (UTC)"""
    return int(time.time() * 1_000_000_000)


def build_ilp_line(data):
    """
    Construye línea ILP (Influx Line Protocol) con el nuevo schema.

    Formato ILP:
    table,tag1=val1,tag2=val2 field1=val1,field2=val2,timestamp_field=func() timestamp_ns

    Tags (SYMBOL): board_id, sensor_type
    Fields: co2, temp, rh, latitude, longitude, errors, ingest_time
    Timestamp: sense_time (designated timestamp)
    """

    # Tags (van en la parte del nombre de la tabla, sin comillas)
    tags = f"{data['table_name']},board_id={data['board_id']},sensor_type={data['sensor_type']}"

    # Timestamp (sense_time) en nanosegundos - este será el designated timestamp
    timestamp_ns = get_current_timestamp_ns()

    # Fields (valores numéricos, 'i' para integers)
    # ingest_time NO se envía - QuestDB lo capturará automáticamente
    fields = (
        f"co2={data['co2']},"
        f"temp={data['temp']},"
        f"rh={data['rh']},"
        f"latitude={data['latitude']},"
        f"longitude={data['longitude']},"
        f"errors={data['errors']}i"
    )

    # Construir línea completa
    ilp_line = f"{tags} {fields} {timestamp_ns}"

    return ilp_line


def insert_test_data(verbose=True):
    """
    Inserta un dato de prueba a QuestDB.
    Retorna True si fue exitoso, False si hubo error.
    """

    if verbose:
        print("\n" + "="*70)
        print("INSERTANDO DATO DE PRUEBA A QUESTDB")
        print("="*70)

    # Construir línea ILP
    ilp_line = build_ilp_line(TEST_DATA)

    if verbose:
        print("\n📝 Línea ILP construida:")
        print(f"  {ilp_line}")
        print(f"\n📊 Tamaño: {len(ilp_line)} bytes")

    try:
        # Hacer request HTTP POST
        if verbose:
            print(f"\n🌐 Enviando a: {QUESTDB_WRITE_URL}")

        response = requests.post(
            QUESTDB_WRITE_URL,
            data=ilp_line,
            headers={"Content-Type": "text/plain"},
            timeout=10
        )

        # QuestDB responde 200 o 204 en éxito
        if response.status_code in [200, 204]:
            if verbose:
                print(f"\n✓ ÉXITO - Status Code: {response.status_code}")
                print(f"  • Tabla: {TEST_DATA['table_name']}")
                print(f"  • Board ID: {TEST_DATA['board_id']}")
                print(f"  • CO2: {TEST_DATA['co2']} ppm")
                print(f"  • Temperatura: {TEST_DATA['temp']} °C")
                print(f"  • Humedad: {TEST_DATA['rh']} %")
                print(f"  • Ubicación: ({TEST_DATA['latitude']}, {TEST_DATA['longitude']})")
                print(f"  • Errores: {TEST_DATA['errors']}")
            return True
        else:
            if verbose:
                print(f"\n✗ ERROR - Status Code: {response.status_code}")
                print(f"  Respuesta: {response.text[:500]}")
            return False

    except requests.exceptions.Timeout:
        if verbose:
            print(f"\n✗ ERROR: Timeout al conectar con {QUESTDB_HOST}:{QUESTDB_PORT}")
            print("  • Verifica que QuestDB esté corriendo")
            print("  • Verifica que el puerto 9000 esté abierto")
        return False

    except requests.exceptions.ConnectionError as e:
        if verbose:
            print(f"\n✗ ERROR: No se pudo conectar con {QUESTDB_HOST}:{QUESTDB_PORT}")
            print(f"  • Detalle: {e}")
            print("  • Verifica la IP del servidor")
            print("  • Verifica que QuestDB esté corriendo")
        return False

    except Exception as e:
        if verbose:
            print(f"\n✗ ERROR INESPERADO: {type(e).__name__}")
            print(f"  • {e}")
        return False


def query_test_data():
    """
    Consulta los datos recién insertados para verificar.
    """
    print("\n" + "="*70)
    print("VERIFICANDO DATOS INSERTADOS")
    print("="*70)

    # Construir query SQL
    query = f"""
    SELECT * FROM {TEST_DATA['table_name']}
    WHERE board_id = '{TEST_DATA['board_id']}'
    ORDER BY sense_time DESC
    LIMIT 5;
    """

    query_url = f"http://{QUESTDB_HOST}:{QUESTDB_PORT}/exec"

    try:
        print(f"\n🔍 Consultando datos del board: {TEST_DATA['board_id']}")

        response = requests.get(
            query_url,
            params={'query': query},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            rows = data.get("dataset", [])
            columns = [col["name"] for col in data.get("columns", [])]

            if not rows:
                print("\n⚠️ No se encontraron datos (puede que aún no se hayan procesado)")
                return

            print(f"\n✓ Encontrados {len(rows)} registro(s):")
            print(f"\n📋 Columnas: {', '.join(columns)}")

            for i, row in enumerate(rows, 1):
                print(f"\n  Registro #{i}:")
                for col, val in zip(columns, row):
                    # Formatear timestamps
                    if col in ['sense_time', 'ingest_time'] and isinstance(val, str):
                        try:
                            dt = datetime.fromisoformat(val.replace('Z', '+00:00'))
                            val = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                        except:
                            pass
                    print(f"    • {col}: {val}")
        else:
            print(f"\n✗ Error en query - Status Code: {response.status_code}")
            print(f"  Respuesta: {response.text[:500]}")

    except Exception as e:
        print(f"\n✗ Error al consultar: {e}")


def test_connection():
    """Prueba la conexión básica a QuestDB"""
    print("\n" + "="*70)
    print("PROBANDO CONEXIÓN A QUESTDB")
    print("="*70)

    test_url = f"http://{QUESTDB_HOST}:{QUESTDB_PORT}/exec"

    try:
        print(f"\n🌐 Conectando a: {test_url}")

        response = requests.get(
            test_url,
            params={'query': 'SELECT 1;'},
            timeout=5
        )

        if response.status_code == 200:
            print("\n✓ Servidor QuestDB accesible")
            print(f"  • Status Code: {response.status_code}")
            return True
        else:
            print(f"\n✗ Respuesta inesperada: {response.status_code}")
            return False

    except requests.exceptions.Timeout:
        print(f"\n✗ Timeout - El servidor no responde")
        return False

    except requests.exceptions.ConnectionError:
        print(f"\n✗ Error de conexión - No se puede alcanzar el servidor")
        return False

    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False


def main():
    """Ejecuta el test completo"""
    print("\n" + "█"*70)
    print("█" + " "*68 + "█")
    print("█" + " "*10 + "QUESTDB ILP INSERT TEST - frontera_dtlabs_v2" + " "*16 + "█")
    print("█" + " "*68 + "█")
    print("█"*70)

    print("\n📌 Configuración:")
    print(f"  • Servidor: {QUESTDB_HOST}:{QUESTDB_PORT}")
    print(f"  • Tabla: {TEST_DATA['table_name']}")
    print(f"  • Board ID: {TEST_DATA['board_id']}")

    # Test 1: Verificar conexión
    if not test_connection():
        print("\n" + "="*70)
        print("❌ TEST FALLÓ - No se puede conectar a QuestDB")
        print("="*70)
        print("\n⚠️ Verifica:")
        print("  1. Que el servidor QuestDB esté corriendo")
        print("  2. Que el puerto 9000 esté abierto")
        print("  3. Que la IP sea correcta: " + QUESTDB_HOST)
        return

    # Test 2: Insertar dato
    success = insert_test_data(verbose=True)

    if success:
        # Test 3: Verificar dato insertado
        print("\n⏳ Esperando 2 segundos para que QuestDB procese...")
        time.sleep(2)
        query_test_data()

        print("\n" + "="*70)
        print("✅ TEST COMPLETADO EXITOSAMENTE")
        print("="*70)
        print("\n📊 Próximos pasos:")
        print("  1. Verifica en QuestDB Console: http://187.124.90.77:9000")
        print("  2. Query: SELECT * FROM frontera_dtlabs_v2 LIMIT 10;")
        print("  3. Si no aparecen datos, revisa el formato ILP")
    else:
        print("\n" + "="*70)
        print("❌ TEST FALLÓ - No se pudo insertar el dato")
        print("="*70)
        print("\n🔧 Debugging:")
        print("  • Revisa los logs de QuestDB")
        print("  • Verifica el formato ILP")
        print("  • Intenta insertar manualmente desde QuestDB Console")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrumpido por el usuario")
    except Exception as e:
        print(f"\n\n✗ Error durante el test: {e}")
        import traceback
        traceback.print_exc()
