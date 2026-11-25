from math import ceil

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.security import require_admin
from app.db.dependencies import get_db
from app.models import Lead, Quote
from app.schemas.lead import LeadListResponse


router = APIRouter(
    prefix="/api/leads",
    tags=["Leads"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=LeadListResponse)
def list_leads(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    email: str | None = Query(default=None, max_length=254, description="Filtra por correo (contiene)"),
    db: Session = Depends(get_db),
) -> LeadListResponse:
    """Devuelve los leads y sus cotizaciones de forma paginada."""

    filters = []
    if email and email.strip():
        filters.append(Lead.email.ilike(f"%{email.strip().lower()}%"))

    total = db.scalar(select(func.count()).select_from(Lead).where(*filters)) or 0

    leads = db.scalars(
        select(Lead)
        .where(*filters)
        .options(selectinload(Lead.quotes).selectinload(Quote.options))
        .order_by(Lead.created_at.desc(), Lead.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return LeadListResponse(
        items=leads,
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if total else 0,
    )
