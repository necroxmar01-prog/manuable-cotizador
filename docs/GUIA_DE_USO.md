# Guía de uso del cotizador

Esta guía es para quien tenga que levantar, usar o revisar el sistema por primera vez. Explica qué hace cada archivo de `datos/`, cómo se usa el cotizador y la vista interna, cómo se cambian tarifas y qué hacer cuando algo falla.

Los casos de prueba con resultados esperados están en [`PRUEBAS_MANUALES.md`](PRUEBAS_MANUALES.md).

---

## 1. Qué hace el sistema

1. Una persona entra al **cotizador público**. Captura CP de origen, CP de destino, peso, medidas de la caja y su correo.
2. El backend convierte cada CP en coordenadas con la API pública Zippopotam. Calcula la distancia en línea recta y, con ella, la **zona**:

   | Zona | Distancia |
   |---|---|
   | 1 | hasta 100 km |
   | 2 | hasta 500 km |
   | 3 | hasta 1,000 km |
   | 4 | más de 1,000 km |

3. Busca las tarifas vigentes de esa zona y ese peso, y muestra las opciones de la más barata a la más cara.
4. Guarda la cotización como **lead**, con un folio y un precio garantizado por 30 días.
5. Comercial consulta los leads en la **vista interna**. Growth ve ahí mismo cuántas cotizaciones hay por día y cuántas quedaron sin opción.

## 2. Requisitos y arranque

Solo necesitas **Git** y **Docker** (con Docker Compose). No hace falta instalar Python, Node ni PostgreSQL.

```bash
git clone https://github.com/necroxmar01-prog/manuable-cotizador.git
cd manuable-cotizador
docker compose up --build
```

El primer arranque tarda unos minutos porque descarga imágenes e instala dependencias. Está listo cuando el log muestra `Uvicorn running on http://0.0.0.0:8000` y `Local: http://localhost:5173/`.

| Qué | Dónde |
|---|---|
| Cotizador público | http://localhost:5173 |
| Vista interna (Comercial / Growth) | http://localhost:5173/admin · usuario `admin` · contraseña `adminlocalonly` |
| API interactiva (Swagger) | http://localhost:8000/docs |
| Estado del backend | http://localhost:8000/health |

| Para… | Comando |
|---|---|
| Detener | `Ctrl+C` y después `docker compose down` |
| Empezar con base de datos limpia | `docker compose down -v` y luego `docker compose up --build` |
| Correr las pruebas automatizadas | `docker compose run --rm --no-deps backend pytest -q` · `docker compose run --rm --no-deps frontend npm test -- --watch=false` |

Las credenciales de la vista interna se cambian con las variables `ADMIN_USERNAME` y `ADMIN_PASSWORD`. Son solo para uso local: no hay HTTPS.

## 3. Los archivos de datos

Todo lo que el sistema sabe de paqueterías, tarifas y reglas viene de los CSV de `datos/`. **Nunca se modifican**: el sistema los lee, limpia una copia en la base de datos y registra qué hizo con cada fila.

La prueba entregó **4 archivos**. El quinto lo agregamos nosotros:

| Archivo | Origen | Fase |
|---|---|---|
| `paqueterias.csv` | Entregado por Manuable | 1 |
| `tarifas.csv` | Entregado por Manuable | 1 |
| `tarifas_dhl_v2.csv` | Entregado por Manuable | 2 |
| `cotizaciones_historicas.csv` | Entregado por Manuable | 2 |
| `reglas_peso.csv` | **Creado por nosotros** a partir del correo de Héctor (volumétrico de DHL y FedEx desde el 1 de diciembre) | 2 |

El quinto archivo existe porque el correo pide que "el próximo cambio de tarifas no requiera tocar código". Si la regla de volumétrico quedara escrita en el código, el día que Estafeta renueve contrato habría que programar. Con el archivo, solo se agrega una línea (sección 3.4).

En cada arranque, el backend revisa la carpeta e importa **solo los archivos nuevos o modificados**. Los reconoce por su contenido (SHA-256), así que reiniciar no duplica nada. El resultado aparece en el log:

```
paqueterias.csv: catálogo actualizado (4 nuevas)
tarifas.csv: {'accepted': 1, 'corrected': 29, 'rejected': 75, 'quarantined': 3}
tarifas_dhl_v2.csv: {'accepted': 24, 'corrected': 0, 'rejected': 0, 'quarantined': 0}
reglas_peso.csv: {'accepted': 6, 'rejected': 0}
cotizaciones_historicas.csv: {'accepted': 40, 'corrected': 0, 'rejected': 0}
```

En arranques posteriores, cada archivo ya cargado dice `sin cambios, se omite`.

### 3.1 `paqueterias.csv`: catálogo

| Columna | Ejemplo | Uso |
|---|---|---|
| `carrier_id` | `CARR-01` | Identificador estable |
| `nombre` | `DHL` | Nombre canónico; las tarifas deben corresponder a uno de estos |
| `tipo_servicio` | `aéreo` | Se muestra en el cotizador |
| `activo` | `si` / `no` | Una paquetería inactiva no se cotiza |

Contiene DHL, Estafeta, FedEx y Redpack. **Redpack está inactiva** (`activo = no`), por eso nunca aparece en el cotizador aunque tenga tarifas cargadas. Este archivo se vuelve a leer en cada arranque: para activar o desactivar una paquetería basta con editarlo y reiniciar.

### 3.2 `tarifas.csv`: tarifario original (fase 1)

Formato: `paqueteria, zona, peso_min, peso_max, unidad, precio, dias_entrega, vigencia_desde`.

Comercial lo armó juntando correos y hojas de cálculo distintas, así que viene muy desordenado. El importador aplica tres criterios:

**Se corrige** cuando la intención es inequívoca, y la corrección queda registrada:

| Problema en el CSV | Ejemplo | Se guarda como |
|---|---|---|
| Nombre de paquetería con variantes | `dhl`, `D.H.L.`, `DHL Express`, `Federal Express`, `Estafeta  Mexicana`, `Red Pack` | `DHL`, `FedEx`, `Estafeta`, `Redpack` |
| Zona con texto | `ZONA 3`, `zona3`, `Z3` | `3` |
| Precio con formato | `$1,137.24`, `1341.36 MXN`, `311,04` (coma decimal) | `1137.24`, `1341.36`, `311.04` |
| Peso en gramos | `5000–10000 g` | `5–10 kg` |
| Unidad vacía pero límite mayor que 30 | `1000, 3000, (vacío)` | gramos → `1–3 kg` (ningún rango del catálogo pasa de 30 kg) |
| Días con texto | `5 días`, `2-4` | mínimo 5, máximo 5 / mínimo 2, máximo 4 |
| Fechas en varios formatos | `01/01/2026`, `1-ene-2026`, `2026-01-01` | `2026-01-01` |

**Se rechaza** cuando falta información o es contradictoria. No inventamos datos (Comercial pidió explícitamente "no inventen tarifas"):

| Motivo | Filas | Ejemplo (fila del CSV) |
|---|---|---|
| Unidad de peso ausente y no se puede deducir | 35 | `DHL ,zona3,20,30,,"2616,12",3,2026-01-01` (¿20 kg o 20 g?) |
| Sin días de entrega | 26 | `D.H.L.,3,0,1000,g,381.26,,2026-01-01` |
| Sin fecha de vigencia | 24 | `FEDEX,zona3,5000,10000,g,"$1,137.24",3-5,` |
| Sin precio | 8 | `DHL Express,zona3,1,3,,,3,01/01/2026` |
| Duplicada después de normalizar | 2 | Fila 47 = fila 12 (`REDPACK,Z3,3000,5000,g,379.08…`) |
| Precio negativo | 1 | `-703.95` |
| Zona inexistente | 1 | `FedEx,Zona 7,…` |
| Rango invertido | 1 | `Estafeta,Z1,5,3,…` (mínimo 5, máximo 3) |
| Paquetería fuera del catálogo | 1 | `Paquetería Rayo,…` |

Una fila puede tener varios motivos a la vez; en total se rechazan 75 de 108.

**Se pone en cuarentena** cuando la fila es válida pero su precio es absurdo frente al resto. Sigue cargada, pero no se cotiza hasta que Comercial la confirme:

| Fila | Precio en el CSV | Mediana del mismo rango | Evidencia |
|---|---|---|---|
| 53 · DHL zona 4, 10–20 kg | $217,672.00 | $995.80 | COT-0012 se cotizó por teléfono en $2,176.72 |
| 6 · Estafeta zona 3, 3–5 kg | $42,237.00 | $472.50 | COT-0003 se cotizó en $422.37 |
| 63 · Estafeta zona 2, 10–20 kg | $10.40 | $1,181.18 | — |

La regla de cuarentena: el precio se aleja más de 5 veces de la mediana de su rango de peso, y hay al menos 3 tarifas para comparar.

**Resultado:** 1 aceptada tal cual, 29 aceptadas con correcciones, 75 rechazadas y 3 en cuarentena. Por eso hay huecos: no todas las paqueterías cubren todos los pesos y zonas (ver la tabla de cobertura en [`INVESTIGACION_CUSTOMER_CARE.md`](INVESTIGACION_CUSTOMER_CARE.md)).

### 3.3 `tarifas_dhl_v2.csv`: tarifario nuevo de DHL (fase 2)

Formato: `paqueteria, zona, peso_min_kg, peso_max_kg, precio_mxn, dias_entrega, vigencia_desde`. Ya no trae columna `unidad`: la unidad (kg) viene en el nombre de la columna, y el importador acepta los dos formatos.

Son 24 filas, todas válidas: 6 rangos de peso (0–1, 1–3, 3–5, 5–10, 10–20 y 20–30 kg) por 4 zonas, con vigencia desde el **1 de diciembre de 2026**.

**Cómo conviven los dos tarifarios de DHL:** para cada fecha, el sistema usa el tarifario de DHL con la vigencia más reciente que ya empezó.

- Hasta el 30 de noviembre: tarifas de `tarifas.csv`.
- Desde el 1 de diciembre (medianoche en hora de Monterrey): **solo** las de `tarifas_dhl_v2.csv`. El tarifario nuevo reemplaza completo al anterior, incluso rangos que ya no existen, como el 3–6 kg de zona 2.

Estafeta y FedEx siguen usando `tarifas.csv`.

### 3.4 `reglas_peso.csv`: cómo cobra cada paquetería (creado por nosotros)

Este archivo **no venía con la prueba**. Traduce a datos la regla del correo de Héctor: desde el 1 de diciembre, DHL y FedEx cobran por peso volumétrico con divisor 5000, y Estafeta sigue con peso real.

```
paqueteria,metodo,divisor_volumetrico,vigencia_desde
DHL,real,,2026-01-01
Estafeta,real,,2026-01-01
FedEx,real,,2026-01-01
Redpack,real,,2026-01-01
DHL,volumetrico,5000,2026-12-01
FedEx,volumetrico,5000,2026-12-01
```

- **`real`**: se cobra por el peso de la báscula.
- **`volumetrico`**: se cobra el mayor entre el peso real y `largo × ancho × alto / divisor`.

Ejemplo: una caja de 40 × 30 × 30 cm pesa 36,000 / 5000 = **7.2 kg volumétricos**. Si pesa 2 kg reales, DHL cobra 7.2 kg; si pesa 8 kg reales, cobra 8 kg.

Para cada fecha aplica la regla más reciente de cada paquetería. Cuando Estafeta renueve contrato, basta con agregar una línea como `Estafeta,volumetrico,5000,2027-03-01`.

### 3.5 `cotizaciones_historicas.csv`: cotizaciones dadas por teléfono

Formato: `cotizacion_id, fecha, correo, cp_origen, cp_destino, zona, peso_kg, paqueteria, precio_cotizado`.

Son 40 cotizaciones que Comercial dio por teléfono, del 14 de octubre al 9 de noviembre de 2026. Se registran así:

- **Origen** `Teléfono` y el folio original (`COT-0001` …) como referencia. Si el archivo se vuelve a cargar, no se duplican.
- **El precio que se le dio a la persona**, aunque no coincida con la tarifa cargada. Si no coincide, queda un aviso en la auditoría de la carga. Ejemplo: COT-0003 cotizó Estafeta en $422.37, y en el tarifario ese precio está en cuarentena por venir como $42,237.
- **Garantía de 30 días** desde su fecha: COT-0029, del 9 de noviembre, vale hasta el 9 de diciembre.
- **Datos que no se registraron por teléfono:** distancia y días de entrega quedan vacíos. El CSV solo trae la fecha, así que la hora se fija a las 12:00.
- **CP con 0 inicial:** se conserva (`06600`). Si un CP llega con 4 dígitos, porque Excel le quitó el cero, se completa y se registra la corrección.
- **Métricas de Growth:** no cuentan, porque no son uso del cotizador web.

## 4. Usar el cotizador

1. Captura **CP de origen** y **CP de destino** (5 dígitos). Se aceptan espacios pegados por accidente (`" 06600 "`). Si escribes el nombre de una ciudad, aparece un aviso que pide el CP.
2. Captura el **peso** en kg: mayor que 0, hasta 1,000, con máximo 3 decimales.
3. Captura las **medidas** en cm (largo, ancho y alto, hasta 300 cada una). Desde el 1 de diciembre DHL y FedEx las usan para el peso volumétrico.
4. Captura tu **correo**: es el dato que Comercial usa para contactarte.
5. Pulsa **Consultar opciones de envío**.

El resultado muestra:

- **Folio** (`#45`) y la fecha hasta la que se respetan los precios.
- **Distancia aproximada** y **zona**.
- Cada opción con paquetería, tipo de servicio, precio, días estimados y, si aplica, "Se cobra por tamaño de caja: X kg (peso volumétrico)".
- Si no hay tarifa para esa combinación, un mensaje claro. La solicitud igual queda registrada para que Comercial la atienda.

| Mensaje | Qué significa |
|---|---|
| "No encontramos el código postal…" | Zippopotam no conoce ese CP; su cobertura no es total |
| "No fue posible conectar con el servicio de códigos postales" | Zippopotam no responde o no hay internet |
| "Por ahora no tenemos una tarifa…" | El CP existe, pero ninguna paquetería tiene precio para esa zona y ese peso |

## 5. Usar la vista interna

Entra a http://localhost:5173/admin con `admin` / `adminlocalonly`.

**Métricas (Growth)**

| Tarjeta o tabla | Qué muestra |
|---|---|
| Cotizaciones hoy | Cotizaciones web del día, en hora de Monterrey |
| Hoy sin ninguna opción | Las de hoy que no encontraron tarifa |
| Últimos 14 días | Acumulado del periodo |
| Total de leads | Web más teléfono |
| Cotizaciones por día | Desglose día por día |

**Solicitudes recibidas (Comercial)**

- **Folio:** `#N` para las web, `COT-NNNN` para las telefónicas, con una etiqueta Web o Teléfono.
- **Datos de la solicitud:** correo, ruta y zona, peso y medidas, y fecha.
- **Opciones cotizadas:** el precio exacto que vio la persona.
- **Precio garantizado:** etiqueta verde "Hasta dd/mm/aaaa" si sigue vigente, o "Venció dd/mm/aaaa" si ya pasaron los 30 días.
- **Buscar por correo:** sirve cuando alguien llama. Busca su correo y verás qué se le cotizó y si su precio sigue vigente.

## 6. Cambiar tarifas o reglas sin tocar código

1. Prepara el CSV. Para tarifas usa cualquiera de los dos formatos de encabezado (el de `tarifas.csv` o el de `tarifas_dhl_v2.csv`), con su `vigencia_desde`.
2. Guárdalo en `datos/` con un nombre que empiece por `tarifas` (p. ej. `tarifas_estafeta_2027.csv`). Para reglas de peso, edita `reglas_peso.csv` o crea un `reglas_peso_<algo>.csv`.
3. Reinicia el backend con `docker compose restart backend`. También puedes ejecutar `docker compose run --rm backend python -m app.cli sync-data`.
4. Revisa en el log cuántas filas se aceptaron, corrigieron, rechazaron o pusieron en cuarentena. El detalle por fila queda en la base de datos (sección 8).

Antes de cargar, considera esto:

- **El archivo de una paquetería es su tarifario completo.** Desde su vigencia, reemplaza todo lo anterior de esa paquetería. Si mandas solo un rango, solo se cotizará ese rango.
- **Las cotizaciones ya emitidas no cambian de precio.**
- **Fechas futuras:** un archivo con fecha futura se carga hoy y entra en vigor solo en su fecha.

## 7. Ver el sistema en una fecha futura (solo demos)

Para ver hoy cómo cotizará el sistema el 1 de diciembre, define la variable `FECHA_SIMULADA` y recrea el backend.

```powershell
# PowerShell (Windows)
$env:FECHA_SIMULADA="2026-12-01T10:00"
docker compose up -d --force-recreate backend

# Volver a la fecha real
Remove-Item Env:FECHA_SIMULADA
docker compose up -d --force-recreate backend
```

```bash
# Bash (macOS / Linux)
FECHA_SIMULADA=2026-12-01T10:00 docker compose up -d --force-recreate backend
docker compose up -d --force-recreate backend   # sin la variable = fecha real
```

http://localhost:8000/health muestra `fecha_simulada` mientras esté activa. Las cotizaciones que hagas se guardan con esa fecha. **Nunca la uses en producción.**

## 8. Consultar la auditoría en la base de datos

```bash
docker compose exec db psql -U manuable -d manuable
```

```sql
-- Resumen de cada carga
SELECT source_file, kind, accepted_rows, corrected_rows, rejected_rows, quarantined_rows
FROM import_batches ORDER BY id;

-- Qué pasó con cada fila de tarifas.csv y por qué
SELECT r.row_number, r.status, r.messages
FROM import_records r JOIN import_batches b ON b.id = r.batch_id
WHERE b.source_file = 'tarifas.csv' ORDER BY r.row_number;

-- Solo las rechazadas
SELECT r.row_number, r.raw_data, r.messages
FROM import_records r JOIN import_batches b ON b.id = r.batch_id
WHERE b.source_file = 'tarifas.csv' AND r.status = 'rejected';

-- Tarifas en cuarentena
SELECT c.name, t.zone, t.weight_min_kg, t.weight_max_kg, t.price_mxn, t.review_note
FROM tariffs t JOIN carriers c ON c.id = t.carrier_id WHERE NOT t.active;

-- Avisos de las cotizaciones telefónicas que no coinciden con la tarifa
SELECT r.raw_data->>'cotizacion_id' AS folio, r.messages
FROM import_records r JOIN import_batches b ON b.id = r.batch_id
WHERE b.kind = 'historical_quotes' AND r.messages::text <> '[]';
```

`\q` para salir.

## 9. API

La documentación interactiva está en http://localhost:8000/docs.

| Método y ruta | Acceso | Uso |
|---|---|---|
| `POST /api/quotes` | Público | Cotiza y registra el lead |
| `GET /api/leads?page=1&page_size=20&email=…` | Basic auth | Leads con sus cotizaciones |
| `GET /api/metrics/quotes?days=14` | Basic auth | Cotizaciones por día y cuántas sin opciones |
| `GET /health` | Público | Estado (y fecha simulada, si está activa) |

```bash
curl -X POST http://localhost:8000/api/quotes \
  -H "Content-Type: application/json" \
  -d '{"origin_postal_code":"64000","destination_postal_code":"97000","weight_kg":2,
       "length_cm":40,"width_cm":30,"height_cm":30,"email":"prueba@demo.mx"}'

curl -u admin:adminlocalonly "http://localhost:8000/api/leads?email=cliente3"
curl -u admin:adminlocalonly "http://localhost:8000/api/metrics/quotes?days=7"
```

En Windows usa `curl.exe` en lugar de `curl`, o `Invoke-RestMethod` (ejemplo en `PRUEBAS_MANUALES.md`).

Los errores de validación devuelven `422` con un `detail` legible, por ejemplo `"Escribe el código postal de 5 dígitos, no el nombre de la ciudad o colonia."`.

## 10. Problemas comunes

| Síntoma | Causa probable | Solución |
|---|---|---|
| El puerto 5432, 8000 o 5173 está ocupado | Otro PostgreSQL o servidor local | Detén el otro servicio o cambia el puerto en `docker-compose.yml` |
| Todas las cotizaciones dicen "No fue posible conectar con el servicio de códigos postales" | Sin internet o Zippopotam caído | Revisa https://api.zippopotam.us/mx/64000 en el navegador |
| Un CP real dice "No encontramos el código postal" | Zippopotam no lo tiene | Limitación conocida del servicio; prueba con otro CP de la misma zona |
| La vista interna dice "Usuario o contraseña incorrectos" | Credenciales cambiadas por variables de entorno | Revisa `ADMIN_USERNAME` y `ADMIN_PASSWORD` |
| Cambié un CSV y no se refleja | El backend no se reinició | `docker compose restart backend` y revisa el log |
| Los precios de DHL ya son los de diciembre | `FECHA_SIMULADA` activa | Revisa `/health` y quítala (sección 7) |
| Quiero repetir la carga desde cero | — | `docker compose down -v` y `docker compose up --build` |

## 11. Mapa de documentos

| Documento | Para qué |
|---|---|
| `README.md` | Arranque rápido |
| `docs/GUIA_DE_USO.md` | Esta guía |
| `docs/PRUEBAS_MANUALES.md` | Casos de prueba de fase 1 y fase 2 con resultados esperados |
| `docs/INVESTIGACION_CUSTOMER_CARE.md` | Qué encontramos sobre los reportes de Customer Care |
| `docs/EXPOSICION_FASE_2.md` | Guion para explicar la fase 2 |
| `DECISIONES.md` | Decisiones técnicas y supuestos |
| `PREGUNTAS.md` | Dudas para el negocio |
| `ENTREGA_FASE_1.md`, `ENTREGA_FASE_2.md` | Mensajes de entrega a las áreas |
