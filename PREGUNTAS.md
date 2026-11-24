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
