# Preguntas para negocio

Estas preguntas documentan ambigüedades que afectan la cotización. Mientras no haya respuesta, se aplicará un supuesto explícito en `DECISIONES.md`.

1. Cuando el peso coincide exactamente con el límite entre dos rangos (por ejemplo, 1 kg en rangos 0–1 y 1–3), ¿qué rango debe aplicar?
2. Si existen dos tarifas válidas para la misma paquetería, zona y rango con vigencias que se traslapan, ¿cuál prevalece?
3. ¿Los días de entrega son días hábiles o naturales?
4. ¿El precio incluye IVA y algún cargo adicional?
5. ¿Qué mecanismo de acceso y qué usuarios debe tener el panel de Comercial?
6. ¿Confirman que el catálogo válido de zonas es exclusivamente 1, 2, 3 y 4? Se rechazan valores como `Zona 7`.
7. Cuando falta la unidad de peso, ¿Comercial puede confirmar que valores de límites mayores a 30 corresponden a gramos? Mientras tanto, solo se infiere esa unidad con esa condición y se documenta.
8. ¿Se deben rechazar tarifas sin días de entrega o se pueden mostrar con precio y plazo no disponible? Para cumplir la solicitud de mostrar precio y días, inicialmente se rechazan.

## Fase 2

9. Cuando una paquetería manda tarifas nuevas, ¿el archivo es siempre su tarifario **completo**? Supuesto actual: sí. Desde su vigencia reemplaza todo el anterior (`DECISIONES.md`, 21).
10. ¿El peso volumétrico se redondea al kilo, al medio kilo o se cobra exacto? Supuesto actual: exacto, redondeado hacia arriba al gramo.
11. ¿Los 30 días de vigencia son naturales y cuentan desde el día de la cotización? Supuesto actual: sí, hasta las 23:59 del día 30 (hora de Monterrey).
12. Tres tarifas de `tarifas.csv` tienen el punto decimal corrido (DHL z4 10–20 kg = 217,672.00; Estafeta z3 3–5 kg = 42,237.00; Estafeta z2 10–20 kg = 10.40). ¿Cuál es el precio correcto? Mientras tanto están en cuarentena y no se cotizan.
13. ¿Las cotizaciones telefónicas deben aparecer en las métricas de Growth? Supuesto actual: no, porque no son uso del cotizador.

Respuesta deducida de los datos: pregunta 1. Las cotizaciones históricas usan el rango inferior en el límite (1 kg → 0–1 kg).
