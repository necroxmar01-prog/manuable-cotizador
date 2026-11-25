# Decisiones técnicas

## 1. Arquitectura y herramientas

1. **Backend:** FastAPI sobre Python 3.12 por su tipado, validación y generación automática de documentación OpenAPI.
2. **Frontend:** Angular 21 con TypeScript y Bootstrap 5 para construir una interfaz modular, tipada y adaptable.
3. **Base de datos:** PostgreSQL 16, compatible con el requisito de PostgreSQL 15 o superior.
4. **Ejecución:** Docker Compose levanta PostgreSQL, backend y frontend sin requerir Python, Node ni PostgreSQL instalados en la máquina revisora.
5. **Datos originales:** los CSV recibidos se conservan en `datos/` como fuentes de entrada. La normalización se realiza durante la importación, sin modificar los archivos originales.
6. **Tarifas DHL v2:** se conserva como archivo independiente. Su vigencia declarada es `2026-12-01`; no debe reemplazar tarifas anteriores antes de esa fecha.

## 2. Decisiones sobre el cotizador y el acceso

7. **Cotizaciones:** únicamente se ofrecen opciones respaldadas por tarifas disponibles y vigentes. Si no existe una tarifa aplicable, no se inventa ni estima un precio.
8. **Códigos postales:** la consulta de cobertura utiliza el servicio externo correspondiente. Los errores del servicio y los códigos postales no encontrados se comunican mediante respuestas diferenciadas.
9. **Acceso administrativo:** el panel Comercial utiliza autenticación HTTP Basic. El usuario y la contraseña se configuran mediante `ADMIN_USERNAME` y `ADMIN_PASSWORD`, con valores predeterminados destinados exclusivamente al entorno local.
10. **Seguridad:** HTTP Basic sin HTTPS no se considera adecuado para producción. Un despliegue productivo requiere HTTPS y una estrategia de autenticación apropiada.

## 3. Importación y normalización de tarifas

11. **Normalización de paqueterías:** se mantienen los cuatro nombres canónicos del catálogo (`DHL`, `Estafeta`, `FedEx` y `Redpack`). Variantes conocidas como `D.H.L.`, `Federal Express` y `Estafeta Mexicana` se mapean a su nombre canónico. Los nombres desconocidos se rechazan; no se crean paqueterías automáticamente a partir del CSV de tarifas.

12. **Unidades de peso:** los gramos se convierten a kilogramos. Si falta la unidad, solo se infieren gramos cuando alguno de los límites supera 30, tomando como referencia el rango máximo de 30 kg de los datos recibidos. En los demás casos se rechaza la fila por ambigüedad.

13. **Tarifas cotizables:** se rechazan filas sin precio positivo, días de entrega, fecha de vigencia, zona válida (1–4) o rango de peso consistente. No se inventan valores faltantes.

14. **Rangos de peso:** se almacenan como límites numéricos en kilogramos. La consulta de tarifas incluye ambos extremos del rango (`weight_min_kg <= peso <= weight_max_kg`). Si existen rangos contiguos que comparten un límite, ambos pueden coincidir; la política comercial para resolver esos solapamientos queda pendiente de validación.

15. **Duplicados:** se genera una huella SHA-256 de los campos normalizados. Una tarifa idéntica no se inserta dos veces. Cada intento queda registrado en el historial de importación.

16. **Auditoría:** se conserva el contenido original de cada fila, su número de línea, estado y mensajes de normalización o rechazo en `import_records`, vinculados al lote correspondiente en `import_batches`.

17. **Carga inicial:** la importación se ejecuta automáticamente cuando todavía no existe un lote de importación. Si ya existe uno, el arranque no repite la carga. Para repetirla desde cero es necesario eliminar el volumen de PostgreSQL.

18. **Validación de datos comerciales:** el importador comprueba estructura y consistencia, pero no puede certificar que los precios de origen sean comercialmente correctos. No se aplican límites de precio arbitrarios ni se modifican importes por intuición.

19. **DHL v2:** no se incluye en la carga inicial de fase 1. Se reserva para el flujo de actualización de tarifas de fase 2 y conserva su vigencia declarada `2026-12-01`.

## 4. Pendientes y consideraciones futuras

- Definir con Comercial cómo resolver tarifas cuyos rangos de peso se solapan.
- Definir el criterio para tarifas con los mismos parámetros, pero distinto precio o vigencia.
- Validar con Comercial las reglas de redondeo y presentación de precios y pesos.
- Definir la política de expiración de cotizaciones y conservación de sus tarifas originales (*snapshots*).
- Establecer autenticación y protección de comunicaciones adecuadas para un despliegue productivo.

## 5. Validación y sanitización de entradas

20. **Reglas reutilizables:** la sanitización y la validación se implementan como responsabilidades separadas. La sanitización controla los caracteres permitidos al escribir o pegar; la validación comprueba que el valor cumpla las reglas establecidas. Ambas se diseñan como funciones reutilizables para aplicarlas consistentemente en distintos campos y formularios.
