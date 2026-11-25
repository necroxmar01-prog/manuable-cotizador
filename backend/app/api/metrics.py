from collections import Counter
from datetime import datetime, time, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.clock import BUSINESS_TZ, business_date
from app.core.security import require_admin
from app.db.dependencies import get_db
from app.models import Quote, QuoteOption
from app.models.quote import QUOTE_SOURCE_WEB
from app.schemas.lead import DailyQuoteMetrics, QuoteMetricsResponse


router = APIRouter(
    prefix="/api/metrics",
    tags=["Métricas"],
    dependencies=[Depends(require_admin)],
)


@router.get("/quotes", response_model=QuoteMetricsResponse)
def quote_metrics(
    days: int = Query(default=30, ge=1, le=366),
    db: Session = Depends(get_db),
) -> QuoteMetricsResponse:
    """Cotizaciones por día (hora de Monterrey) y cuántas terminaron sin opciones.

    Solo cuenta el cotizador web: las cotizaciones telefónicas cargadas por
    Comercial no son uso del cotizador.
    """

    today = business_date()
    first_day = today - timedelta(days=days - 1)
    since = datetime.combine(first_day, time.min, tzinfo=BUSINESS_TZ)

    option_count = (
        select(QuoteOption.quote_id, func.count(QuoteOption.id).label("n"))
        .group_by(QuoteOption.quote_id)
        .subquery()
    )
    rows = db.execute(
        select(Quote.created_at, func.coalesce(option_count.c.n, 0))
        .outerjoin(option_count, option_count.c.quote_id == Quote.id)
        .where(Quote.source == QUOTE_SOURCE_WEB, Quote.created_at >= since)
    ).all()

    totals: Counter = Counter()
    empty: Counter = Counter()
    for created_at, n_options in rows:
        day = business_date(created_at)
        totals[day] += 1
        if n_options == 0:
            empty[day] += 1

    daily = [
        DailyQuoteMetrics(
            date=(first_day + timedelta(days=i)).isoformat(),
            quotes=totals[first_day + timedelta(days=i)],
            without_options=empty[first_day + timedelta(days=i)],
        )
        for i in range(days)
    ]
    daily.reverse()  # más reciente primero

    return QuoteMetricsResponse(
        days=days,
        total_quotes=sum(totals.values()),
        total_without_options=sum(empty.values()),
        daily=daily,
    )
