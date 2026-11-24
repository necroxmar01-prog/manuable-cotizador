# Manuable · Cotizador de envíos

Aplicación fullstack para cotizar envíos, registrar leads y administrar tarifas.

## Requisitos

- Git
- Docker con Docker Compose

No necesitas instalar Python ni Node.js en tu máquina.

## Levantar todo

Desde la raíz del repositorio:

```bash
docker compose up --build
```

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

Los archivos CSV originales están en `datos/`. `tarifas_dhl_v2.csv` corresponde al archivo adicional compartido para la fase 2 y declara vigencia desde el 1 de diciembre de 2026.

## Estado

Esqueleto inicial: servicios Docker, endpoint de salud y prueba mínima. El importador, el modelo de datos y los flujos funcionales se implementarán por etapas.
