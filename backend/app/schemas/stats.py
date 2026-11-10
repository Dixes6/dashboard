from datetime import date

from pydantic import BaseModel


class TopServiceResponse(BaseModel):
    name: str
    count: int
    revenue: int


class BestDayResponse(BaseModel):
    date: date
    income: int


class MonthStatsResponse(BaseModel):
    visits_income: int
    other_income: int
    income_total: int
    expenses_total: int
    net_profit_month: int
    net_profit_week: int | None = None
    avg_income_per_day: int | None = None
    completed_visits_count: int
    top_service: TopServiceResponse | None = None
    best_day: BestDayResponse | None = None


class MonthSummaryResponse(BaseModel):
    month: str
    income_total: int
    expenses_total: int
    net_profit: int
