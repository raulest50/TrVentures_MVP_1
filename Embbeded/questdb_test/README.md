# QuestDB Test Utilities

Estos scripts son utilidades locales de escritorio para administracion y pruebas directas sobre QuestDB.

Importante:

- El firmware productivo en `Embbeded/src/` ya no debe escribir directo a QuestDB.
- El nodo IoT ahora debe enviar JSON al backend en `https://api.fronteradatalabs.com`.
- Este directorio se conserva solo para pruebas administrativas o de diagnostico sobre `https://questdb.fronteradatalabs.com`.

## Requisitos

- Python con `requests`
- Variables de entorno:
  - `QDB_HTTP_USER`
  - `QDB_HTTP_PASSWORD`

Ejemplo:

```bash
export QDB_HTTP_USER=tu_usuario
export QDB_HTTP_PASSWORD=tu_password
```

## Scripts

### `test_connection.py`

Prueba conectividad basica, crea una tabla de ejemplo y verifica lectura/escritura.

```bash
python test_connection.py
```

### `test_ilp_insert.py`

Inserta un dato de prueba usando ILP directo sobre QuestDB.

```bash
python test_ilp_insert.py
```

### `consumer_test.py`

Consulta `telemetria_datos` y grafica variables ambientales.

```bash
python consumer_test.py
```

## Host y endpoints

- Host: `https://questdb.fronteradatalabs.com`
- SQL queries: `GET /exec?query=...`
- ILP ingestion: `POST /write`

## Nota operativa

Para flujo de producto:

- Dashboard -> `https://dashboard.fronteradatalabs.com`
- API backend -> `https://api.fronteradatalabs.com`
- QuestDB admin -> `https://questdb.fronteradatalabs.com`
