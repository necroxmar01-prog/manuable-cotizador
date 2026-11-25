# Guía de pruebas manuales (fase 2)

Datos para comprobar a mano, desde el navegador o el API, todo lo que cambió en la fase 2. Los resultados esperados se calcularon con los CSV de `datos/` y las coordenadas que devuelve Zippopotam para cada CP.

## 0. Preparación

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

## 1. Rutas de referencia

| Ruta | CP origen → destino | Distancia aprox. | Zona |
|---|---|---|---|
| Monterrey → San Pedro | 64000 → 66220 | 72 km | 1 |
| Monterrey → Aguascalientes | 64000 → 20000 | 482 km | 2 |
| Monterrey → CDMX | 64000 → 06600 | 726 km | 3 |
| Monterrey → Mérida | 64000 → 97000 | 1,159 km | 4 |

Zippopotam da coordenadas aproximadas por CP; por eso Monterrey–San Pedro aparece a 72 km. La zona se calcula con esas coordenadas.

## 2. Escenarios de cotización

Para todos usa el correo `prueba@demo.mx`. "Hoy" significa cualquier fecha antes del 1 de diciembre de 2026.

| # | Qué prueba | Ruta | Peso | Medidas (cm) | Hoy | Con `FECHA_SIMULADA` 1 dic |
|---|---|---|---|---|---|---|
| 1 | Caso normal | Zona 1 | 2 kg | 20×15×10 | Estafeta $198.55 · FedEx $369.90 | Estafeta $198.55 · FedEx $369.90 · DHL $374.09 |
| 2 | **Límite de rango** (antes salía DHL dos veces) | Zona 4 | **1 kg** | 10×10×10 | Estafeta $232.48 · DHL $449.70 (una vez cada una) | Estafeta $232.48 · DHL $490.17 |
| 3 | **Volumétrico** | Zona 4 | 2 kg | **40×30×30** | Estafeta $365.33 | Estafeta $365.33 (real 2 kg) · FedEx $1,341.36 · DHL $1,381.86 (7.2 kg volumétricos) |
| 4 | Volumétrico, zona 3 | Zona 3 | 2 kg | 40×30×30 | Sin opciones | DHL $1,171.58 (7.2 kg) |
| 5 | **Cuarentena** (DHL $217,672) | Zona 4 | 15 kg | 40×30×20 | Sin opciones (antes ofrecía DHL en $217,672) | DHL $2,372.62 |
| 6 | **Cuarentena** (Estafeta $42,237) | Zona 3 | 4 kg | 20×20×20 | Sin opciones (antes ofrecía Estafeta en $42,237) | DHL $751.58 |
| 7 | **Tarifario completo reemplazado** | Zona 2 | 5.5 kg | 20×20×20 | DHL $470.00 (rango viejo 3–6) · Estafeta $577.60 | Estafeta $577.60 · DHL $961.29 (rango nuevo 5–10) |
| 8 | Sin opciones → métrica de Growth | Zona 1 | 0.5 kg | 10×10×10 | Sin opciones | DHL $266.40 |

Precio de la opción y orden: las opciones salen de la más barata a la más cara. En cada resultado verifica también:

- **Folio** (`Folio #N`) y la frase "Respetamos estos precios hasta el …": hoy + 30 días.
- Con volumétrico: "Se cobra por tamaño de caja: 7.2 kg (peso volumétrico)". Si gana el peso real (caja chica), no aparece esa leyenda.

## 3. Customer Care: validaciones del CP

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

## 4. Vista interna (Comercial y Growth)

1. Entra a `/admin`. Deben verse **40 cotizaciones con badge "Teléfono"** (COT-0001 … COT-0040) más las que hayas hecho.
2. Busca `cliente21`. Debe aparecer **COT-0021**: DHL, zona 3, 0.5 kg, **$381.26**, cotizada el 06/11/2026, precio garantizado **hasta el 06/12/2026**.
   - Con la fecha simulada al 1 de diciembre, una cotización nueva de DHL zona 3 0.5 kg cuesta $415.57. COT-0021 conserva $381.26: si la persona llama antes del 6 de diciembre, ese es el precio que se le cobra.
3. Busca `cliente12`. Debe aparecer COT-0012: DHL $2,176.72 del 15/10/2026, con el badge **"Venció 14/11/2026"**.
4. Métricas: "Cotizaciones hoy" y "Hoy sin ninguna opción" deben subir con tus pruebas web (el escenario 8 suma a "sin opciones"). Las 40 telefónicas **no** cuentan.

| Cuándo revisas | Telefónicas con precio garantizado |
|---|---|
| 25 nov 2026 | 18 de 40 |
| 1 dic 2026 (simulado) | 9 de 40 |

## 5. Auditoría de cargas (opcional, en la base)

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

## 6. Próximo cambio de tarifas sin tocar código

1. Crea `datos/tarifas_estafeta_2027.csv`:

   ```
   paqueteria,zona,peso_min_kg,peso_max_kg,precio_mxn,dias_entrega,vigencia_desde
   Estafeta,4,0,1,250.00,6,2027-01-01
   ```

2. `docker compose restart backend`. El log debe decir `tarifas_estafeta_2027.csv: {'accepted': 1, ...}`.
3. Con `FECHA_SIMULADA=2027-01-02T10:00:00`, zona 4, 0.5 kg: Estafeta $250.00. Con la fecha real: Estafeta $232.48.

   Ojo: desde esa fecha ese archivo reemplaza **todo** el tarifario de Estafeta (`DECISIONES.md`, 21), así que en este ejemplo Estafeta solo cotizaría ese rango.

Lo mismo para la regla de Estafeta: agrega `Estafeta,volumetrico,5000,2027-03-01` a `datos/reglas_peso.csv` y reinicia.

## 7. Pruebas automatizadas

```bash
docker compose run --rm --no-deps backend pytest -q                    # 111 pruebas
docker compose run --rm --no-deps frontend npm test -- --watch=false   # 29 pruebas
```

| Archivo | Qué cubre |
|---|---|
| `backend/tests/test_phase2_pricing.py` | Límites de rango, tarifario completo, volumétrico, reglas futuras, cuarentena |
| `backend/tests/test_phase2_sync.py` | Carga real de `datos/`, idempotencia, lote de fase 1, cotizaciones telefónicas, siguiente cambio de tarifas |
| `backend/tests/test_phase2_api.py` | Vigencia de 30 días, medianoche de Monterrey, volumétrico vía API, métricas, búsqueda, fecha simulada |
| `backend/tests/test_quotes.py` | CP con espacios y mensajes de error legibles |
| `frontend-angular/src/app/pages/quote/quote.spec.ts` | CP pegado, aviso de ciudad, medidas, folio y vigencia |
