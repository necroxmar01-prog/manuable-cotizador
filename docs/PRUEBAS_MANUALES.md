# Guía de pruebas manuales (fase 1 y fase 2)

Casos para comprobar a mano, desde el navegador o el API, lo que pide cada fase. Cómo funciona cada pantalla y cada archivo de datos está en [`GUIA_DE_USO.md`](GUIA_DE_USO.md). Los resultados esperados se calcularon con los CSV de `datos/` y las coordenadas que devuelve Zippopotam para cada CP.

## Preparación

```bash
docker compose down -v        # base limpia
docker compose up --build
```

- Cotizador: http://localhost:5173
- Vista interna: http://localhost:5173/admin (`admin` / `adminlocalonly`)
- API interactiva: http://localhost:8000/docs

En el log del backend deben aparecer estas líneas:

```
tarifas.csv: {'accepted': 1, 'corrected': 29, 'rejected': 75, 'quarantined': 3}
tarifas_dhl_v2.csv: {'accepted': 24, 'corrected': 0, 'rejected': 0, 'quarantined': 0}
reglas_peso.csv: {'accepted': 6, 'rejected': 0}
cotizaciones_historicas.csv: {'accepted': 40, 'corrected': 0, 'rejected': 0}
```

Si reinicias (`docker compose restart backend`), cada archivo debe decir `sin cambios, se omite`.

### Simular el 1 de diciembre

Las tarifas de DHL y el volumétrico arrancan el 2026-12-01. Para verlo hoy, el backend acepta una fecha simulada (solo para demos):

```powershell
# PowerShell
$env:FECHA_SIMULADA="2026-12-01T10:00:00"
docker compose up -d backend
# Confirmar: http://localhost:8000/health  ->  "fecha_simulada": "2026-12-01T10:00:00-06:00"

# Volver a la fecha real
Remove-Item Env:FECHA_SIMULADA
docker compose up -d backend
```

```bash
# Bash
FECHA_SIMULADA=2026-12-01T10:00:00 docker compose up -d backend
```

Las cotizaciones que hagas con fecha simulada se guardan con esa fecha. Al terminar la demo, `docker compose down -v` deja la base limpia.

## Rutas de referencia (sirven para las dos fases)

| Ruta | CP origen → destino | Distancia aprox. | Zona |
|---|---|---|---|
| Monterrey → San Pedro | 64000 → 66220 | 72 km | 1 |
| Monterrey → Aguascalientes | 64000 → 20000 | 482 km | 2 |
| Monterrey → CDMX | 64000 → 06600 | 726 km | 3 |
| Monterrey → Mérida | 64000 → 97000 | 1,159 km | 4 |

Zippopotam da coordenadas aproximadas por CP; por eso Monterrey–San Pedro aparece a 72 km. La zona se calcula con esas coordenadas.

# Fase 1

Lo que pide la fase 1 y dónde se comprueba:

| Requisito | Cómo comprobarlo |
|---|---|
| Carga de tarifas limpia y auditable | F1.1 |
| Cotizador público (paqueterías, precio, días) | F1.2 |
| Captura del correo; cada cotización se guarda | F1.3 |
| Mensajes claros, nunca pantalla en blanco | F1.4 |
| Vista interna protegida | F1.5 |
| Pruebas automatizadas sin servicios externos | Sección "Pruebas automatizadas" |

## F1.1 Carga de tarifas: qué se cargó, qué se corrigió y qué se rechazó

Con la base limpia (`docker compose down -v` y `docker compose up --build`), el log debe decir:

```
tarifas.csv: {'accepted': 1, 'corrected': 29, 'rejected': 75, 'quarantined': 3}
```

Comprueba filas concretas en la base:

```bash
docker compose exec db psql -U manuable -d manuable -c "SELECT r.row_number, r.status, r.messages FROM import_records r JOIN import_batches b ON b.id = r.batch_id WHERE b.source_file = 'tarifas.csv' AND r.row_number IN (3,16,22,35,45,47,53,90,92) ORDER BY 1;"
```

| Fila | Contenido en el CSV | Estado esperado | Motivo esperado |
|---|---|---|---|
| 45 | `dhl,Zona 1,5,10,kg,$689.00,1-3,2026-01-01` | `corrected` | Paquetería `dhl` → DHL, zona `Zona 1` → 1, precio `$689.00` → 689.00 |
| 92 | `DHL Express,Zona 2,1000,3000,,439.30,2-4,2026-01-01` | `corrected` | Unidad vacía: se infirieron gramos (1–3 kg) |
| 3 | `FEDEX,zona3,5000,10000,g,"$1,137.24",3-5,` | `rejected` | Fecha de vigencia ausente |
| 16 | `Estafeta  Mexicana,zona3,5,10,,-703.95,,2026-01-01` | `rejected` | Unidad ambigua; precio negativo; días ausentes (tres motivos) |
| 22 | `FedEx,Zona 7,0,1,kg,240.00,1,2026-01-01` | `rejected` | Zona fuera del catálogo (1–4) |
| 35 | `Estafeta,Z1,5,3,kg,260.00,3,2026-01-01` | `rejected` | Peso máximo menor que el mínimo |
| 47 | `REDPACK,Z3,3000,5000,g,379.08,6,1-ene-2026` | `rejected` | Duplicada de la fila 12 después de normalizar |
| 90 | `Paquetería Rayo,Zona 1,0,1,kg,99.00,2,2026-01-01` | `rejected` | Paquetería desconocida |
| 53 | `D.H.L.,Zona 4,10,20,KG,217672.00,4-6,01/01/2026` | `quarantined` | Precio atípico frente a la mediana (regla agregada en fase 2) |

## F1.2 Cotizaciones por zona

Usa las rutas de referencia (abajo), medidas **10 × 10 × 10 cm** y cualquier correo. Las medidas se agregaron en la fase 2; antes del 1 de diciembre no cambian ningún precio.

Resultados válidos **antes del 1 de diciembre de 2026**, ordenados del más barato al más caro:

| Zona | Ruta | Peso | Debe salir |
|---|---|---|---|
| 1 | 64000 → 66220 | 2 kg | Estafeta $198.55 · FedEx $369.90 |
| 1 | 64000 → 66220 | 4 kg | FedEx $472.50 |
| 1 | 64000 → 66220 | 8 kg | DHL $689.00 |
| 1 | 64000 → 66220 | 15 kg | Estafeta $812.25 · DHL $1,183.00 |
| 2 | 64000 → 20000 | 2 kg | DHL $439.30 |
| 2 | 64000 → 20000 | 4 kg | DHL $470.00 · FedEx $604.80 |
| 2 | 64000 → 20000 | 8 kg | Estafeta $577.60 |
| 2 | 64000 → 20000 | 25 kg | DHL $2,146.56 |
| 3 | 64000 → 06600 | 0.5 kg | Estafeta $197.11 |
| 3 | 64000 → 06600 | 8 kg | DHL $1,074.84 |
| 3 | 64000 → 06600 | 25 kg | FedEx $2,737.80 |
| 4 | 64000 → 97000 | 8 kg | Estafeta $830.30 · FedEx $1,341.36 |
| 4 | 64000 → 97000 | 25 kg | Estafeta $2,158.78 · DHL $3,085.68 |
| 1 | 64000 → 66220 | 0.5 kg | Sin opciones (solo Redpack tiene ese rango, y está inactiva) |
| 2 | 64000 → 20000 | 15 kg | Sin opciones |

Además:

- **Redpack no aparece nunca:** está inactiva en `paqueterias.csv`.
- **Días de entrega:** cada opción los muestra. Ejemplo: zona 1, 2 kg → Estafeta 3 días, FedEx 1–3 días.
- **Folio y vigencia:** cada cotización muestra su folio (`Folio #N`) y la fecha hasta la que se respeta el precio.

## F1.3 El lead queda guardado

1. Cotiza zona 1, 2 kg con el correo `  Lead.Prueba@Demo.MX  ` (con espacios y mayúsculas).
2. Cotiza zona 1, 0.5 kg (sin opciones) con `sinopcion@demo.mx`.
3. En http://localhost:5173/admin busca `demo.mx`. Deben aparecer las dos:
   - la primera como `lead.prueba@demo.mx`, con Estafeta $198.55 y FedEx $369.90;
   - la segunda con la etiqueta **"Sin opciones"**. También se guarda, porque es un lead que Comercial puede atender.
4. Reinicia con `docker compose restart backend`. Los leads siguen ahí, y el log dice `sin cambios, se omite` para cada CSV: no se duplica nada.

## F1.4 Mensajes claros (nunca pantalla en blanco)

| Entrada | Debe pasar |
|---|---|
| CP destino `99999` | "No encontramos el código postal 99999." |
| CP `6400` (incompleto) | El formulario marca "Debe contener exactamente 5 dígitos numéricos." |
| Peso `0` | El formulario marca el campo; no se envía |
| Peso mayor a 1000 | El campo no lo acepta |
| Correo `ana@correo` | "Ingresa un correo electrónico con formato válido." |
| Campos vacíos | Cada campo obligatorio muestra su mensaje |
| Backend detenido (`docker compose stop backend`) y cotizar | "No pudimos conectar con el cotizador…" (luego `docker compose start backend`) |

La caída de Zippopotam (`503`, "No fue posible conectar con el servicio de códigos postales") se cubre con pruebas automatizadas (`backend/tests/test_quotes.py`), porque no se puede provocar a mano de forma confiable.

## F1.5 La vista interna no está abierta al público

| Prueba | Debe pasar |
|---|---|
| Entrar a `/admin` con contraseña incorrecta | "Usuario o contraseña incorrectos." |
| `curl.exe -i http://localhost:8000/api/leads` (sin credenciales) | `401 Unauthorized` |
| `curl.exe -i -u admin:adminlocalonly http://localhost:8000/api/leads` | `200` con los leads |
| `curl.exe -i http://localhost:8000/api/metrics/quotes` | `401 Unauthorized` |

---

# Fase 2

## F2.1 Escenarios de cotización

Para todos usa el correo `prueba@demo.mx`. "Hoy" significa cualquier fecha antes del 1 de diciembre de 2026.

| # | Qué prueba | Ruta | Peso | Medidas (cm) | Hoy | Con `FECHA_SIMULADA` 1 dic |
|---|---|---|---|---|---|---|
| 1 | Caso normal | Zona 1 | 2 kg | 20×15×10 | Estafeta $198.55 · FedEx $369.90 | Estafeta $198.55 · FedEx $369.90 · DHL $374.09 |
| 2 | **Límite de rango** (antes Estafeta salía dos veces: $232.48 y $365.33) | Zona 4 | **1 kg** | 10×10×10 | Estafeta $232.48 · DHL $449.70 (una vez cada una) | Estafeta $232.48 · DHL $490.17 |
| 3 | **Volumétrico** | Zona 4 | 2 kg | **40×30×30** | Estafeta $365.33 | Estafeta $365.33 (real 2 kg) · FedEx $1,341.36 · DHL $1,381.86 (7.2 kg volumétricos) |
| 4 | Volumétrico, zona 3 | Zona 3 | 2 kg | 40×30×30 | Sin opciones | DHL $1,171.58 (7.2 kg) |
| 5 | **Cuarentena** (DHL $217,672) | Zona 4 | 15 kg | 40×30×20 | Sin opciones (antes ofrecía DHL en $217,672) | DHL $2,372.62 |
| 6 | **Cuarentena** (Estafeta $42,237) | Zona 3 | 4 kg | 20×20×20 | Sin opciones (antes ofrecía Estafeta en $42,237) | DHL $751.58 |
| 7 | **Tarifario completo reemplazado** | Zona 2 | 5.5 kg | 20×20×20 | DHL $470.00 (rango viejo 3–6) · Estafeta $577.60 | Estafeta $577.60 · DHL $961.29 (rango nuevo 5–10) |
| 8 | Sin opciones → métrica de Growth | Zona 1 | 0.5 kg | 10×10×10 | Sin opciones | DHL $266.40 |

Precio de la opción y orden: las opciones salen de la más barata a la más cara. En cada resultado verifica también:

- **Folio** (`Folio #N`) y la frase "Respetamos estos precios hasta el …": hoy + 30 días.
- Con volumétrico: "Se cobra por tamaño de caja: 7.2 kg (peso volumétrico)". Si gana el peso real (caja chica), no aparece esa leyenda.

## F2.2 Customer Care: validaciones del CP

| Entrada en CP | Resultado esperado |
|---|---|
| Pegar ` 06600 ` (espacio antes y después) | El campo queda en `06600` y cotiza normal |
| Escribir `Monterrey` | Aviso: "Escribe el código postal de 5 dígitos, no el nombre de la ciudad." |
| `6600` (4 dígitos) | Error de campo: "Debe contener exactamente 5 dígitos numéricos." |
| `99999` (no existe en Zippopotam) | Mensaje claro de CP no encontrado (no pantalla en blanco) |
| Dejar medidas vacías | No deja enviar: "Indica largo, ancho y alto…" |

En el API (http://localhost:8000/docs → `POST /api/quotes`), los mismos casos devuelven un `detail` legible:

```json
{"origin_postal_code": "Monterrey", "destination_postal_code": "64000", "weight_kg": 1, "email": "prueba@demo.mx"}
```
→ `422` · `"Escribe el código postal de 5 dígitos, no el nombre de la ciudad o colonia."`

```json
{"origin_postal_code": "6600", "destination_postal_code": "64000", "weight_kg": 1, "email": "prueba@demo.mx"}
```
→ `422` · `"El código postal debe tener 5 dígitos. Si empieza con 0, inclúyelo (ej. 06600)."`

```json
{"origin_postal_code": "64000", "destination_postal_code": "06600", "weight_kg": 2, "email": "prueba@demo.mx"}
```
→ Con `FECHA_SIMULADA` 1 dic: `options: []` y `notices: ["DHL y FedEx cobran por peso volumétrico: indica largo, ancho y alto para ver su precio."]`

PowerShell, sin navegador:

```powershell
$body = @{ origin_postal_code=" 64000 "; destination_postal_code="97000"; weight_kg=2;
           length_cm=40; width_cm=30; height_cm=30; email="prueba@demo.mx" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/quotes -ContentType "application/json" -Body $body
```

## F2.3 Vista interna (Comercial y Growth)

1. Entra a `/admin`. Deben verse **40 cotizaciones con badge "Teléfono"** (COT-0001 … COT-0040) más las que hayas hecho.
2. Busca `cliente21`. Debe aparecer **COT-0021**: DHL, zona 3, 0.5 kg, **$381.26**, cotizada el 06/11/2026, precio garantizado **hasta el 06/12/2026**.
   - Con la fecha simulada al 1 de diciembre, una cotización nueva de DHL zona 3 0.5 kg cuesta $415.57. COT-0021 conserva $381.26: si la persona llama antes del 6 de diciembre, ese es el precio que se le cobra.
3. Busca `cliente12`. Debe aparecer COT-0012: DHL $2,176.72 del 15/10/2026, con el badge **"Venció 14/11/2026"**.
4. Métricas: "Cotizaciones hoy" y "Hoy sin ninguna opción" deben subir con tus pruebas web (el escenario 8 suma a "sin opciones"). Las 40 telefónicas **no** cuentan.

| Cuándo revisas | Telefónicas con precio garantizado |
|---|---|
| 25 nov 2026 | 18 de 40 |
| 1 dic 2026 (simulado) | 9 de 40 |

## F2.4 Auditoría de cargas (opcional, en la base)

```bash
docker compose exec db psql -U manuable -d manuable
```

```sql
-- Resumen por archivo
SELECT source_file, kind, accepted_rows, corrected_rows, rejected_rows, quarantined_rows
FROM import_batches ORDER BY id;

-- Tarifas en cuarentena y su motivo
SELECT c.name, t.zone, t.weight_min_kg, t.weight_max_kg, t.price_mxn, t.review_note
FROM tariffs t JOIN carriers c ON c.id = t.carrier_id WHERE NOT t.active;

-- Reglas de peso vigentes
SELECT c.name, r.weight_method, r.volumetric_divisor, r.valid_from
FROM carrier_pricing_rules r JOIN carriers c ON c.id = r.carrier_id ORDER BY c.name, r.valid_from;
```

## F2.5 Próximo cambio de tarifas sin tocar código

1. Crea `datos/tarifas_estafeta_2027.csv`:

   ```
   paqueteria,zona,peso_min_kg,peso_max_kg,precio_mxn,dias_entrega,vigencia_desde
   Estafeta,4,0,1,250.00,6,2027-01-01
   ```

2. `docker compose restart backend`. El log debe decir `tarifas_estafeta_2027.csv: {'accepted': 1, ...}`.
3. Con `FECHA_SIMULADA=2027-01-02T10:00:00`, zona 4, 0.5 kg: Estafeta $250.00. Con la fecha real: Estafeta $232.48.

   Ojo: desde esa fecha ese archivo reemplaza **todo** el tarifario de Estafeta (`DECISIONES.md`, 21), así que en este ejemplo Estafeta solo cotizaría ese rango.

Lo mismo para la regla de Estafeta: agrega `Estafeta,volumetrico,5000,2027-03-01` a `datos/reglas_peso.csv` y reinicia.

## Pruebas automatizadas

```bash
docker compose run --rm --no-deps backend pytest -q                    # 111 pruebas
docker compose run --rm --no-deps frontend npm test -- --watch=false   # 30 pruebas
```

| Archivo | Qué cubre |
|---|---|
| `backend/tests/test_phase2_pricing.py` | Límites de rango, tarifario completo, volumétrico, reglas futuras, cuarentena |
| `backend/tests/test_phase2_sync.py` | Carga real de `datos/`, idempotencia, lote de fase 1, cotizaciones telefónicas, siguiente cambio de tarifas |
| `backend/tests/test_phase2_api.py` | Vigencia de 30 días, medianoche de Monterrey, volumétrico vía API, métricas, búsqueda, fecha simulada |
| `backend/tests/test_quotes.py` | CP con espacios y mensajes de error legibles |
| `frontend-angular/src/app/pages/quote/quote.spec.ts` | CP pegado, aviso de ciudad, medidas, folio y vigencia |
