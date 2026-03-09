# Test QuestDB Connection

Scripts de prueba para validar conexión con QuestDB en VPS Hostinger.

## Archivos

- `test_connection.py`: Script principal de prueba que valida conexión, escritura y lectura

## Uso

```bash
# Instalar dependencias
pip install requests

# Ejecutar prueba
python test_connection.py
```

## Configuración

Actualiza estas variables en `test_connection.py`:
- `QUESTDB_HOST`: IP de tu servidor (actualmente: 187.124.90.77)
- `QUESTDB_HTTP_PORT`: Puerto HTTP (actualmente: 9000)

## Seguridad

⚠️ **IMPORTANTE**: Este script es solo para desarrollo. Para producción:
- Implementa autenticación
- Usa HTTPS
- Configura firewall adecuadamente
