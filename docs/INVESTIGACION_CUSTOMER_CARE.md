# Investigación de los reportes de Customer Care (fase 2)

Reporte de Mariana, Customer Care:

> "el cotizador se traba a veces cuando pones el CP con espacios o cuando escribes la ciudad. una clienta nos dijo que puso "06600 " y no le salió nada. también varios nos preguntan por qué les sale una paquetería y a su vecino otra con el mismo CP."

## 1. "Se traba cuando escribes la ciudad". Era un problema de experiencia de uso.

El campo de CP borraba en silencio todo lo que no fuera dígito. Si alguien escribía "Monterrey", las letras desaparecían y el campo se veía congelado, sin ningún mensaje que lo explicara.

**Corrección:** el campo sigue aceptando solo dígitos, pero ahora muestra "Escribe el código postal de 5 dígitos, no el nombre de la ciudad". El API también responde con ese texto si recibe letras. Buscar por ciudad sería una funcionalidad nueva; no se implementó (ver Recomendaciones).

## 2. "Puse "06600 " y no salió nada". Era un bug.

El CP 06600 sí existe en Zippopotam (Juárez, CDMX); lo verificamos. La falla tenía dos causas que se combinaban:

- El input tenía `maxlength="5"`. Al pegar " 06600" (con espacio inicial, muy común al copiar de un correo o de WhatsApp), el navegador cortaba el texto a " 0660" **antes** de limpiarlo. El resultado era "0660", un CP inválido.
- En v1 el backend rechazaba espacios con un 422 cuyo `detail` era una lista técnica. El frontend no podía mostrarla y enseñaba un mensaje genérico.

**Corrección:** se quitó `maxlength` del CP (la limpieza ya lo limita a 5 dígitos). El backend acepta espacios en cualquier posición, incluidos tabuladores y espacios duros (` `), y los 422 ahora traen un `detail` legible. También hay mensajes específicos para los errores más comunes: CP de 4 dígitos ("si empieza con 0, inclúyelo") y nombre de ciudad. Además, las coordenadas de cada CP se guardan en caché para no repetir consultas lentas a Zippopotam.

## 3. "A mí me sale una paquetería y a mi vecino otra con el mismo CP". Es normal en su mayor parte, con un bug incluido.

Las opciones dependen de **CP de origen + CP de destino + peso** (y, desde el 1 de diciembre, de las **medidas** de la caja). Dos vecinos con el mismo destino pero distinto peso caen en rangos distintos. Las tarifas tienen muchos huecos: de 108 filas de `tarifas.csv`, 75 se rechazaron porque les faltaba información (unidad, días o vigencia). Por eso cada paquetería cubre solo algunos rangos.

Esta es la cobertura al 25 de noviembre (Redpack está inactiva en el catálogo):

| Zona | 0–1 kg | 1–3 kg | 3–5 kg | 5–10 kg | 10–20 kg | 20–30 kg |
|---|---|---|---|---|---|---|
| 1 | — | Estafeta, FedEx | FedEx | DHL | DHL, Estafeta | — |
| 2 | — | DHL | DHL, FedEx | Estafeta | — | DHL |
| 3 | Estafeta | — | — | DHL | — | FedEx |
| 4 | DHL, Estafeta | Estafeta | — | Estafeta, FedEx | — | DHL, Estafeta |

Desde el 1 de diciembre, con el tarifario nuevo de DHL, todos los rangos tienen al menos una opción:

| Zona | 0–1 kg | 1–3 kg | 3–5 kg | 5–10 kg | 10–20 kg | 20–30 kg |
|---|---|---|---|---|---|---|
| 1 | DHL | DHL, Estafeta, FedEx | DHL, FedEx | DHL | DHL, Estafeta | DHL |
| 2 | DHL | DHL | DHL, FedEx | DHL, Estafeta | DHL | DHL |
| 3 | DHL, Estafeta | DHL | DHL | DHL | DHL | DHL, FedEx |
| 4 | DHL, Estafeta | DHL, Estafeta | DHL | DHL, Estafeta, FedEx | DHL | DHL, Estafeta |

**Bug encontrado:** en los pesos exactos de frontera (1, 3, 5, 10 y 20 kg) los rangos se consultaban como inclusivos en los dos extremos. Un paquete de 1 kg caía en 0–1 y en 1–3 a la vez, y la **misma paquetería aparecía dos veces con precios distintos**. Las cotizaciones históricas de Comercial confirman la regla correcta (COT-0026: DHL, zona 3, 1 kg = precio del rango 0–1). Ahora se usa `mínimo < peso ≤ máximo`.

**Hallazgo adicional (grave):** tres tarifas tenían el punto decimal corrido y se cotizaban así en producción:

| Tarifa | Precio cargado | Evidencia |
|---|---|---|
| DHL zona 4, 10–20 kg | $217,672.00 | COT-0012 cotizó $2,176.72 |
| Estafeta zona 3, 3–5 kg | $42,237.00 | COT-0003 cotizó $422.37 |
| Estafeta zona 2, 10–20 kg | $10.40 | Mediana del rango ≈ $1,180 |

Las tres quedaron **en cuarentena**: no se cotizan hasta que Comercial confirme el precio. No se corrigieron por intuición.

## Recomendaciones

1. Comercial: completar las tarifas rechazadas (la lista con su motivo está en `import_records`) y confirmar los 3 precios en cuarentena.
2. Producto: decidir si se quiere búsqueda por ciudad o colonia. Requiere un catálogo de CP (SEPOMEX); Zippopotam no busca por nombre.
3. Customer Care: pedir a la persona el **folio** que ahora aparece en pantalla. Con el folio se ve exactamente qué se le cotizó y hasta cuándo se respeta.
