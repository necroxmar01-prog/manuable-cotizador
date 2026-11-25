from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.leads import router as leads_router
from app.api.metrics import router as metrics_router
from app.api.quotes import router as quotes_router


app = FastAPI(
    title="Manuable Cotizador API",
    version="0.2.0",
    description="API pública de cotizaciones y administración de leads.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """422 con un `detail` legible para mostrarlo tal cual en pantalla.

    En fase 1 el detalle era una lista técnica y el frontend terminaba
    mostrando un mensaje genérico; `errors` conserva el detalle completo.
    """

    errors = exc.errors()
    first = errors[0] if errors else {}
    message = str(first.get("msg", "Datos inválidos.")).removeprefix("Value error, ")
    return JSONResponse(
        status_code=422,
        content={"detail": message, "errors": jsonable_errors(errors)},
    )


def jsonable_errors(errors: list[dict]) -> list[dict]:
    return [
        {"loc": list(e.get("loc", [])), "msg": str(e.get("msg", "")), "type": e.get("type", "")}
        for e in errors
    ]


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(quotes_router)
app.include_router(leads_router)
app.include_router(metrics_router)
