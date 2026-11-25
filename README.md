# Manuable · Cotizador de envíos

Aplicación fullstack para cotizar envíos, registrar leads y administrar tarifas mediante un panel interno para Comercial.

## Requisitos

- Git
- Docker con Docker Compose

No necesitas instalar Python, Node ni PostgreSQL en tu máquina.

## Levantar todo

Desde la raíz del repositorio:

```bash
docker compose up --build
```

En cada arranque, el backend espera a que PostgreSQL esté saludable, aplica las migraciones Alembic y sincroniza la carpeta `datos/` (ver *Actualizar tarifas*). Cada archivo se importa una sola vez por contenido.

Servicios:

- Frontend Angular: http://localhost:5173
- API: http://localhost:8000
- Documentación OpenAPI: http://localhost:8000/docs
- Health check: http://localhost:8000/health
- PostgreSQL: localhost:5432 (base `manuable`, usuario `manuable`)

Para detener los servicios: `Ctrl+C` y después `docker compose down`.

Para borrar también los datos locales de PostgreSQL: `docker compose down -v`. Esta operación elimina los datos persistidos y permite repetir la carga inicial.

## Ejecutar pruebas automatizadas

Desde la raíz del repositorio:

```bash
docker compose run --rm --no-deps backend pytest -q
docker compose run --rm --no-deps frontend npm test -- --watch=false
```

Las pruebas del backend utilizan SQLite en memoria y simulan los servicios externos cuando corresponde. Las pruebas del frontend se ejecutan con Vitest. No necesitan una instancia de PostgreSQL ni servicios externos.

## Funcionalidad

- Importación y normalización de tarifas desde CSV.
- Cotización mediante códigos postales de origen y destino, peso y consulta de tarifas disponibles.
- Registro de leads y sus cotizaciones.
- Panel interno para Comercial con autenticación HTTP Basic, consulta paginada de leads y métricas básicas.
- Mensajes diferenciados cuando un código postal no está cubierto, falla el servicio postal o no existen tarifas disponibles.

## Acceso al panel Comercial

La configuración local predeterminada es:

- Usuario: `admin`
- Contraseña: `adminlocalonly`

Se puede cambiar mediante las variables de entorno `ADMIN_USERNAME` y `ADMIN_PASSWORD` antes de levantar los servicios.

**Seguridad:** el acceso utiliza HTTP Basic sin HTTPS. Las credenciales predeterminadas son únicamente para desarrollo local. Esta configuración no debe exponerse directamente en producción; se requiere HTTPS y una estrategia de autenticación adecuada para el entorno de despliegue.

## Datos de entrada

Los CSV originales se conservan sin modificar en `datos/`:

| Archivo | Contenido |
|---|---|
| `paqueterias.csv` | Catálogo de paqueterías (se actualiza en cada arranque). |
| `tarifas*.csv` | Tarifarios. Cada uno con su `vigencia_desde`; p. ej. `tarifas_dhl_v2.csv` aplica desde el 2026-12-01. |
| `reglas_peso*.csv` | Cómo cobra cada paquetería: peso `real` o `volumetrico` (con divisor), desde qué fecha. |
| `cotizaciones_historicas*.csv` | Cotizaciones dadas por teléfono; se registran con su precio y vigencia de 30 días. |

## Actualizar tarifas o reglas de peso (sin tocar código)

1. Deja el CSV nuevo en `datos/`, con un nombre que empiece por `tarifas` o `reglas_peso` (p. ej. `tarifas_estafeta_2027.csv`).
2. Reinicia el backend (`docker compose restart backend`) o ejecuta:

   ```bash
   docker compose run --rm backend python -m app.cli sync-data
   ```

Un tarifario nuevo de una paquetería reemplaza completo al anterior desde su `vigencia_desde` (hora de Monterrey). Las cotizaciones ya emitidas conservan su precio 30 días. Ejemplo para cuando Estafeta pase a volumétrico: agregar a `datos/reglas_peso.csv` la línea `Estafeta,volumetrico,5000,AAAA-MM-DD`.

El resultado de cada carga (aceptadas, corregidas, rechazadas y en cuarentena, con su motivo) queda en `import_batches` / `import_records`.

### Simular una fecha (solo demos)

Para ver hoy cómo cotizará el sistema en otra fecha (p. ej. el 1 de diciembre, cuando entran las tarifas DHL v2 y el volumétrico):

```bash
FECHA_SIMULADA=2026-12-01T10:00:00 docker compose up -d backend    # PowerShell: $env:FECHA_SIMULADA="2026-12-01T10:00:00"
```

`GET /health` muestra la fecha simulada cuando está activa. No se debe definir en producción.

## Importador de tarifas

El importador normaliza nombres de paqueterías, zonas, unidades, precios, días de entrega y fechas. Rechaza filas incompletas, ambiguas o inconsistentes sin inventar valores.

Cada fila procesada queda registrada en `import_records`, vinculada a un lote en `import_batches`. Se conserva el contenido original, el estado y los mensajes de normalización o rechazo.

La carga inicial es idempotente: si ya existe un lote de importación, el arranque no vuelve a cargar los CSV.

Para reiniciar completamente los datos locales y repetir la carga inicial:

```bash
docker compose down -v
docker compose up --build
```

Con los CSV recibidos, la importación produce:

- `tarifas.csv`: 1 aceptada sin cambios, 29 corregidas mediante normalización, 75 rechazadas (73 por datos inválidos o incompletos y 2 duplicadas) y 3 en cuarentena por precio atípico (fase 2).
- `tarifas_dhl_v2.csv`: 24 aceptadas.
- `reglas_peso.csv`: 6 reglas.
- `cotizaciones_historicas.csv`: 40 cotizaciones telefónicas registradas.

La validación comprueba estructura y consistencia de los datos, pero no certifica que los precios de origen sean comercialmente correctos. Las tarifas se conservan sin inventar ni ajustar importes.

## Fase 2

- Tarifas DHL v2 y peso volumétrico (DHL y FedEx) desde el 2026-12-01, configurables por datos.
- Cotizaciones con folio y precio garantizado 30 días; cotizaciones telefónicas registradas.
- Métricas de Growth (`GET /api/metrics/quotes`) en la vista interna.
- Investigación de Customer Care: [`docs/INVESTIGACION_CUSTOMER_CARE.md`](docs/INVESTIGACION_CUSTOMER_CARE.md).
- Datos y escenarios para probar a mano: [`docs/PRUEBAS_MANUALES.md`](docs/PRUEBAS_MANUALES.md).
- Resumen técnico de la solución (arquitectura, decisiones y demo): [`docs/EXPOSICION_FASE_2.md`](docs/EXPOSICION_FASE_2.md).
- Detalle de decisiones en `DECISIONES.md` (sección 5) y mensaje al negocio en `ENTREGA_FASE_2.md`.

## Estado de fase 1

La aplicación incluye base de datos PostgreSQL 16, migraciones Alembic, importador auditable, API de cotización y leads, frontend Angular y panel Comercial.

Las pruebas automatizadas cubren los flujos críticos del backend y frontend. La autenticación administrativa está pensada para el entorno local de evaluación y requiere endurecimiento antes de un despliegue productivo.