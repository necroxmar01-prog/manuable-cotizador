from fastapi import FastAPI

from app.api.quotes import router as quotes_router


app = FastAPI(
    title="Manuable Cotizador API",
    version="0.1.0",
    description="API pública de cotizaciones y administración de leads.",
)


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(quotes_router)
