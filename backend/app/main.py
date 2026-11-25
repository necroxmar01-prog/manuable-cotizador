
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.leads import router as leads_router
from app.api.quotes import router as quotes_router


app = FastAPI(
    title="Manuable Cotizador API",
    version="0.1.0",
    description="API pública de cotizaciones y administración de leads.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(quotes_router)
app.include_router(leads_router)
