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

En el primer arranque, el backend espera a que PostgreSQL esté saludable, aplica las migraciones Alembic e importa `paqueterias.csv` y `tarifas.csv` si la base todavía no tiene una importación inicial.

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

Los archivos CSV originales se conservan en `datos/`. La fase 1 procesa `paqueterias.csv` y `tarifas.csv`. Los archivos `tarifas_dhl_v2.csv` y `cotizaciones_historicas.csv` se reservan para la fase 2.

## Importador de tarifas

El importador normaliza nombres de paqueterías, zonas, unidades, precios, días de entrega y fechas. Rechaza filas incompletas, ambiguas o inconsistentes sin inventar valores.

Cada fila procesada queda registrada en `import_records`, vinculada a un lote en `import_batches`. Se conserva el contenido original, el estado y los mensajes de normalización o rechazo.

La carga inicial es idempotente: si ya existe un lote de importación, el arranque no vuelve a cargar los CSV.

Para reiniciar completamente los datos locales y repetir la carga inicial:

```bash
docker compose down -v
docker compose up --build
```

Con los CSV recibidos, la importación inicial de `tarifas.csv` produjo:

- 1 fila aceptada sin cambios.
- 32 filas corregidas mediante normalización.
- 75 filas rechazadas: 73 por datos inválidos o incompletos y 2 duplicadas después de normalizar.

La validación comprueba estructura y consistencia de los datos, pero no certifica que los precios de origen sean comercialmente correctos. Las tarifas se conservan sin inventar ni ajustar importes.

## Estado de fase 1

La aplicación incluye base de datos PostgreSQL 16, migraciones Alembic, importador auditable, API de cotización y leads, frontend Angular y panel Comercial.

Las pruebas automatizadas cubren los flujos críticos del backend y frontend. La autenticación administrativa está pensada para el entorno local de evaluación y requiere endurecimiento antes de un despliegue productivo.