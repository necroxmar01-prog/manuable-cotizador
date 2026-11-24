# Manuable · Cotizador de envíos

Aplicación fullstack para cotizar envíos, registrar leads y administrar tarifas.

## Requisitos

- Git
- Docker con Docker Compose

No necesitas instalar Python, Node ni PostgreSQL en tu máquina.

## Levantar todo

Desde la raíz del repositorio:

```bash
docker compose up --build
```

En el primer arranque, el backend espera a que PostgreSQL esté saludable, aplica las migraciones Alembic e importa `paqueterias.csv` y `tarifas.csv` si la base todavía no tiene una importación inicial.

Servicios:

- Frontend: http://localhost:5173
- API: http://localhost:8000
- Documentación OpenAPI: http://localhost:8000/docs
- Health check: http://localhost:8000/health
- PostgreSQL: localhost:5432 (base `manuable`, usuario `manuable`)

Para detener los servicios: `Ctrl+C` y después `docker compose down`.
Para borrar también los datos locales de PostgreSQL: `docker compose down -v`.

## Ejecutar pruebas automatizadas

```bash
docker compose run --rm backend pytest -q
```

## Datos de entrada

Los archivos CSV originales están en `datos/`. `tarifas_dhl_v2.csv` y `cotizaciones_historicas.csv` se reservan para la fase 2.

## Importador de tarifas

El importador de fase 1 procesa `paqueterias.csv` y `tarifas.csv`. Normaliza nombres, zonas, unidades, precios, días y fechas; rechaza filas incompletas o ambiguas y registra cada fila en `import_records`, vinculada a un lote en `import_batches`.

La carga inicial es idempotente: si ya existe un lote de importación, el arranque no vuelve a cargar el CSV. Para reiniciar completamente los datos locales y repetir la carga inicial:

```bash
docker compose down -v
docker compose up --build
```

## Estado

- Base de datos PostgreSQL 16 y migración inicial Alembic.
- Modelos para paqueterías, tarifas y auditoría de importaciones.
- Importador conservador de tarifas con pruebas unitarias.
- Cotizador, leads, autenticación y panel comercial pendientes.

Con los CSV recibidos actualmente, la importación de `tarifas.csv` produce 33 tarifas guardadas: 1 fila aceptada sin cambios y 32 filas corregidas por normalización. Se rechazan 75 filas: 73 por datos inválidos o incompletos y 2 duplicadas después de normalizar. Cada rechazo conserva su motivo en la base de datos.
