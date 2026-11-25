# Tutorial de instalación

Paso a paso para levantar el cotizador desde cero en **macOS (incluido Apple Silicon)**, **Windows** o **Linux**. Solo se instalan dos cosas, Git y Docker. Todo lo demás (PostgreSQL, Python, Node y los datos de ejemplo) corre dentro de contenedores.

Tiempo estimado: 10 a 15 minutos la primera vez, casi todo esperando descargas.

---

## Paso 1. Instalar Git

| Sistema | Cómo |
|---|---|
| macOS | Ya viene; si no, `xcode-select --install` o `brew install git` |
| Windows | Descarga https://git-scm.com/download/win e instala con las opciones por defecto |
| Linux (Debian/Ubuntu) | `sudo apt install git` |

Comprueba en una terminal:

```bash
git --version
```

## Paso 2. Instalar Docker

| Sistema | Cómo |
|---|---|
| macOS | [Docker Desktop para Mac](https://docs.docker.com/desktop/setup/install/mac-install/). En Apple Silicon elige la versión **Apple chip** |
| Windows | [Docker Desktop para Windows](https://docs.docker.com/desktop/setup/install/windows-install/). Durante la instalación deja marcada la opción **WSL 2**; si te lo pide, reinicia |
| Linux | [Docker Engine](https://docs.docker.com/engine/install/) más el plugin `docker-compose-plugin` |

Abre Docker Desktop y espera a que diga **Engine running**. Luego comprueba:

```bash
docker --version
docker compose version
```

Las imágenes que usa el proyecto (`postgres:16-alpine`, `python:3.12-slim` y `node:22-alpine`) existen para Intel y para ARM, así que funcionan igual en Mac con Apple Silicon sin configurar nada.

## Paso 3. Descargar el proyecto

```bash
git clone https://github.com/necroxmar01-prog/manuable-cotizador.git
cd manuable-cotizador
```

> **Windows:** usa una ruta corta y sin sincronizar. Por ejemplo, `C:\proyectos\manuable-cotizador` funciona mejor que una carpeta de OneDrive, que puede bloquear archivos mientras Docker los usa.

## Paso 4. Levantar todo (un solo comando)

```bash
docker compose up --build
```

Esto hace, en orden:

1. Descarga las imágenes y construye backend y frontend. Tarda unos minutos solo la primera vez.
2. Arranca PostgreSQL y espera a que esté listo.
3. Aplica las migraciones de base de datos.
4. Carga los CSV de `datos/`: paqueterías, tarifas, tarifas DHL v2, reglas de peso y las 40 cotizaciones telefónicas.
5. Arranca el API y el frontend.

Está listo cuando el log muestra estas dos líneas:

```
backend-1   | INFO:     Uvicorn running on http://0.0.0.0:8000
frontend-1  |   ➜  Local:   http://localhost:5173/
```

Deja esa terminal abierta: ahí ves el log en vivo.

## Paso 5. Comprobar que funciona

| Abre | Debes ver |
|---|---|
| http://localhost:8000/health | `{"status":"ok"}` |
| http://localhost:5173 | El formulario "Envía fácil. Compara tus opciones." |
| http://localhost:5173/admin | Login. Entra con usuario `admin` y contraseña `adminlocalonly`; deben aparecer las 40 cotizaciones "Teléfono" |
| http://localhost:8000/docs | La documentación interactiva del API |

Primera cotización de prueba:

| Campo | Valor |
|---|---|
| CP origen | `64000` |
| CP destino | `66220` |
| Peso | `2` |
| Medidas | `20` × `15` × `10` |
| Correo | `prueba@demo.mx` |

Antes del 1 de diciembre de 2026 debe mostrar **Estafeta $198.55** y **FedEx $369.90**. Para cotizar se necesita internet, porque el sistema consulta la API pública Zippopotam para convertir el código postal en coordenadas.

## Paso 6. Correr las pruebas automatizadas

En **otra** terminal, dentro de la carpeta del proyecto:

```bash
docker compose run --rm --no-deps backend pytest -q
docker compose run --rm --no-deps frontend npm test -- --watch=false
```

Resultado esperado: `111 passed` en backend y `30 passed` en frontend. No necesitan internet ni la base de datos levantada.

## Paso 7. Detener, reiniciar y limpiar

| Para… | Comando |
|---|---|
| Detener (conserva los datos) | `Ctrl+C` en la terminal del paso 4 y luego `docker compose down` |
| Volver a arrancar | `docker compose up` (sin `--build`, salvo que cambie el código) |
| Arrancar en segundo plano | `docker compose up -d`; para ver el log, `docker compose logs -f backend` |
| Borrar la base de datos y empezar de cero | `docker compose down -v`, luego `docker compose up --build` |
| Liberar espacio en disco | `docker compose down -v --rmi local` |

## Problemas frecuentes

| Síntoma | Solución |
|---|---|
| `Cannot connect to the Docker daemon` / `error during connect` | Docker Desktop no está abierto. Ábrelo y espera a "Engine running" |
| `port is already allocated` (5432, 8000 o 5173) | Otro programa usa ese puerto, a menudo un PostgreSQL local. Detenlo, o cambia el puerto del lado izquierdo en `docker-compose.yml` (p. ej. `"5433:5432"`) |
| Windows: "WSL 2 installation is incomplete" | En PowerShell como administrador, `wsl --install`, y reinicia |
| Windows: "Virtualization must be enabled" | Activa la virtualización (Intel VT-x / AMD-V) en la BIOS |
| El frontend no carga, pero el backend sí | La primera compilación de Angular tarda; espera a ver `Local: http://localhost:5173/` |
| Todas las cotizaciones dicen "No fue posible conectar con el servicio de códigos postales" | Sin internet o Zippopotam caído. Prueba https://api.zippopotam.us/mx/64000 en el navegador |
| Cambié un CSV de `datos/` y no se refleja | `docker compose restart backend` y revisa el log |
| La terminal muestra `Remove-Item … no existe` en Windows | Es inofensivo: la variable que intentabas borrar ya no estaba definida |

## Siguientes pasos

- [`README.md`](README.md): resumen del proyecto.
- [`docs/GUIA_DE_USO.md`](docs/GUIA_DE_USO.md): qué hace cada archivo de datos, cómo se usa cada pantalla y cómo cambiar tarifas.
- [`docs/PRUEBAS_MANUALES.md`](docs/PRUEBAS_MANUALES.md): casos de prueba de fase 1 y fase 2 con sus resultados esperados.
