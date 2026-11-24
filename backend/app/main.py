from fastapi import FastAPI

app = FastAPI(
    title="Manuable Cotizador API",
    version="0.1.0",
    description="API pública de cotizaciones y administración de leads.",
)


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
