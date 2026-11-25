# Entrega de fase 1

## Entregado

Se implementó una aplicación para cotizar envíos, registrar leads y consultar cotizaciones desde un panel interno para Comercial. Se incorporó la importación auditable de tarifas CSV, con normalización y registro de filas aceptadas, corregidas y rechazadas. La solución utiliza Angular, FastAPI y PostgreSQL, y se ejecuta mediante Docker Compose. Las pruebas automatizadas del backend y frontend cubren los flujos críticos.

## Pendiente

La actualización de tarifas DHL v2 y la incorporación de cotizaciones históricas quedan para la fase 2.

## Riesgos

Los CSV contienen datos incompletos y precios cuya exactitud comercial no está verificada. El acceso administrativo utiliza HTTP Basic sin HTTPS y es exclusivo para evaluación local.

## Recomendación

Validar las tarifas con Comercial, confirmar las reglas para rangos de peso y preparar autenticación segura antes de cualquier despliegue productivo.