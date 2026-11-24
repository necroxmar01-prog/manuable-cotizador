# Decisiones técnicas

## Iniciales

1. **Backend:** FastAPI sobre Python 3.12 por su tipado, validación y documentación OpenAPI automática.
2. **Frontend:** React + TypeScript + Vite para una interfaz tipada y un entorno de desarrollo ligero.
3. **Base de datos:** PostgreSQL 16, compatible con el requisito de PostgreSQL 15 o superior.
4. **Ejecución:** Docker Compose levanta base de datos, backend y frontend sin requerir Python ni Node instalados en la máquina revisora.
5. **Datos originales:** los CSV recibidos se conservan en `datos/` como fuentes de entrada. La normalización se implementará en el importador y no modificará estos archivos.
6. **Tarifas DHL v2:** se conserva como archivo independiente. Su vigencia declarada es 2026-12-01; no debe reemplazar tarifas anteriores antes de esa fecha.

## Pendiente de decisión

- Política exacta para resolver rangos de peso contiguos (por ejemplo, 0–1 y 1–3 kg) sin solapamientos.
- Criterio para tarifas duplicadas con distinto precio o vigencia.
- Política de redondeo de peso y precio.
- Mecanismo y secreto de acceso al panel interno.
- Política de expiración de cotizaciones y almacenamiento de snapshots.

## Importación inicial de tarifas

7. **Normalización de paqueterías:** se mantienen los cuatro nombres canónicos del catálogo (`DHL`, `Estafeta`, `FedEx`, `Redpack`). Variantes conocidas como `D.H.L.`, `Federal Express` y `Estafeta Mexicana` se mapean a su paquetería canónica. Nombres desconocidos se rechazan; no se crean paqueterías a partir del CSV de tarifas.
8. **Unidades:** gramos se convierten a kilogramos. Si falta la unidad, solo se infiere gramos cuando algún límite supera 30 (máximo de referencia de los rangos expresados en kg de estos datos); si no, se rechaza por ambigüedad.
9. **Tarifas cotizables:** se rechazan filas sin precio positivo, días de entrega, fecha de vigencia, zona 1–4 o rango de peso válido. No se inventan valores faltantes.
10. **Rangos de peso:** se almacenan como límites numéricos en kg. La regla de inclusión exacta en los límites se definirá en el servicio de cotización; pendiente de confirmación de Comercial.
11. **Duplicados:** se genera una huella SHA-256 de los campos normalizados; una tarifa idéntica no se inserta dos veces. Cada intento queda en el historial de importación.
12. **Auditoría:** se conserva el contenido original de cada fila, su número de línea, estado y mensajes de normalización/rechazo en `import_records`.
13. **DHL v2:** no se importa en la carga inicial de fase 1. Se reserva para el flujo de actualización de fase 2 y conserva su vigencia `2026-12-01`.
