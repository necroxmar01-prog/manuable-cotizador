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
