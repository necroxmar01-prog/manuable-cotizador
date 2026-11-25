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

14. **Rangos de peso:** se almacenan como límites numéricos en kilogramos. ~~La consulta incluye ambos extremos~~ → **reemplazada en fase 2 por la decisión 22** (`min < peso <= max`).

15. **Duplicados:** se genera una huella SHA-256 de los campos normalizados. Una tarifa idéntica no se inserta dos veces. Cada intento queda registrado en el historial de importación.

16. **Auditoría:** se conserva el contenido original de cada fila, su número de línea, estado y mensajes de normalización o rechazo en `import_records`, vinculados al lote correspondiente en `import_batches`.

17. **Carga inicial:** la importación se ejecuta automáticamente cuando todavía no existe un lote de importación. Si ya existe uno, el arranque no repite la carga. Para repetirla desde cero es necesario eliminar el volumen de PostgreSQL.

18. **Validación de datos comerciales:** el importador comprueba estructura y consistencia, pero no puede certificar que los precios de origen sean comercialmente correctos. No se aplican límites de precio arbitrarios ni se modifican importes por intuición.

19. **DHL v2:** no se incluye en la carga inicial de fase 1. Se carga en fase 2 (decisiones 21 y 28) con su vigencia declarada `2026-12-01`.

## 4. Validación y sanitización de entradas

20. **Reglas reutilizables:** la sanitización y la validación se implementan como responsabilidades separadas. La sanitización controla los caracteres permitidos al escribir o pegar; la validación comprueba que el valor cumpla las reglas establecidas. Ambas se diseñan como funciones reutilizables para aplicarlas consistentemente en distintos campos y formularios.


## 5. Fase 2: mantenimiento

21. **Tarifario vigente por paquetería.** Para cada paquetería se toma el lote de tarifas con la `vigencia_desde` más reciente que ya inició. Ese lote **reemplaza completo** al anterior, aunque sus rangos no coincidan uno a uno. Motivo: DHL v1 tenía un rango 3–6 kg en zona 2 que no existe en v2. Si solo cerráramos rangos idénticos, a partir del 1 de diciembre DHL saldría dos veces para 5.5 kg. Supuesto pendiente de confirmar: cada archivo nuevo de una paquetería trae su tarifario completo (`PREGUNTAS.md`, 9).
22. **Límites de peso `min < peso <= max`.** El criterio inclusivo de fase 1 hacía que con 1, 3, 5, 10 o 20 kg una misma paquetería apareciera dos veces. Las cotizaciones de Comercial lo confirman: COT-0026 (DHL, zona 3, 1 kg) y COT-0028 (Estafeta, zona 4, 1 kg) usan el precio del rango 0–1. Esto responde la pregunta 1 de `PREGUNTAS.md`.
23. **Peso cobrable configurable por datos.** La tabla `carrier_pricing_rules` (alimentada desde `datos/reglas_peso.csv`) define, por paquetería y fecha, si se cobra por peso `real` o `volumetrico` y con qué divisor. Peso volumétrico = L×A×H / divisor, redondeado hacia arriba a gramos. Se cobra el mayor entre real y volumétrico. Sin regla, se cobra por peso real. Cuando Estafeta renueve contrato, basta con agregar `Estafeta,volumetrico,5000,<fecha>`.
24. **Medidas del paquete.** El formulario las exige. En el API son opcionales para no romper integraciones de fase 1. Si faltan y una paquetería cobra por volumétrico, esa paquetería **no se cotiza** (no inventamos el tamaño) y la respuesta incluye un aviso en `notices`. El máximo es 300 cm por lado.
25. **Fechas en hora de Monterrey.** El contenedor corre en UTC. Con `date.today()`, el 30 de noviembre a partir de las 18:00 ya se cotizaría con tarifas de diciembre. Toda vigencia se evalúa con `America/Monterrey` (`app/core/clock.py`; se agrega `tzdata`).
26. **Cotizaciones respetadas 30 días.** Cada cotización guarda una foto inmutable de lo que vio la persona: precio, plazo, peso cobrable, método y tarifa de origen. Nunca se recalcula. `quotes.valid_until` es el fin del día 30 en hora de Monterrey. La migración rellena ese dato para las cotizaciones de fase 1 a partir de su `created_at`. Comercial ve en la vista interna si el precio sigue garantizado y puede buscar por correo. La persona ve su folio y la fecha límite en pantalla.
27. **Cotizaciones telefónicas.** Se cargan desde `cotizaciones_historicas.csv` como `source='telefono'`, con `external_ref` = `cotizacion_id` (único, para que la carga sea idempotente). La hora se fija a las 12:00 de Monterrey porque el CSV solo trae la fecha. Se respeta el precio dado aunque no coincida con la tarifa. Si difiere o no hay tarifa, se deja un aviso en `import_records` (p. ej. COT-0003 frente a la tarifa en cuarentena). No tienen distancia ni días de entrega; esos campos pasan a ser opcionales. No cuentan en las métricas de Growth porque no son uso del cotizador.
28. **Sincronización de `datos/` sin tocar código.** Al arrancar, `python -m app.cli sync-data` importa cada `tarifas*.csv`, `reglas_peso*.csv` y `cotizaciones_historicas*.csv` **una sola vez por contenido** (SHA-256 en `import_batches.file_sha256`). El lote de fase 1, que no tenía hash, se reconoce por nombre. El próximo cambio de tarifas consiste en dejar un CSV nuevo en `datos/` y reiniciar. El importador acepta ambos formatos de encabezado (`peso_min` + `unidad`, o `peso_min_kg`).
29. **Cuarentena de precios atípicos.** Si una tarifa se aleja más de 5× de la mediana de su mismo rango de peso (con al menos 3 referencias), se marca `active=false` con su motivo y su registro de importación pasa a `quarantined`. No se corrige el importe. Afectó a 3 tarifas de fase 1 que se cotizaban en producción (ver `docs/INVESTIGACION_CUSTOMER_CARE.md`). Se aplica en cada arranque, así que también limpia bases de datos ya existentes.
30. **Métricas para Growth.** `GET /api/metrics/quotes?days=N` (protegido) devuelve cotizaciones por día en hora de Monterrey y cuántas terminaron sin opciones. Solo cuenta cotizaciones web. La vista interna muestra el día de hoy, el acumulado de 14 días y la tabla diaria. Reemplaza los contadores de fase 1, que solo sumaban la página visible.
31. **Errores de validación legibles.** Los 422 devuelven `detail` como texto y `errors` con el detalle técnico. Esto corrige el mensaje genérico que veía la clienta con "06600 ".
32. **Fecha simulada para demos.** Con la variable `FECHA_SIMULADA` (ISO 8601; sin zona = hora de Monterrey) se puede mostrar hoy el comportamiento del 1 de diciembre. Afecta las cotizaciones, la vigencia y las métricas, y `/health` la expone para que no pase desapercibida. Vacía por defecto; no debe usarse en producción. Las pruebas automatizadas congelan el reloj sin usarla.
33. **Frontend zoneless.** Angular 21 corre sin `zone.js`; cada respuesta HTTP llama a `markForCheck()`. Sin eso, la pantalla se quedaba en "Consultando..." (bug presente desde v1).

## 6. Pendientes y consideraciones futuras

- Confirmar con Comercial los 3 precios en cuarentena y completar las 75 tarifas rechazadas de fase 1.
- Confirmar que un archivo nuevo de una paquetería es su tarifario completo (decisión 21).
- Definir si el volumétrico se redondea al kilo o al medio kilo, como hacen algunas paqueterías. Hoy se redondea al gramo.
- Búsqueda por ciudad o colonia (requiere catálogo SEPOMEX).
- Validar con Comercial las reglas de presentación de precios (IVA, cargos adicionales).
- Autenticación y HTTPS adecuados para producción. Un formulario de carga de CSV en la vista interna permitiría que Comercial actualice tarifas sin acceso al servidor.
