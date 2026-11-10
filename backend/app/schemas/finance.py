from datetime import date

from pydantic import BaseModel


class FinanceEntryResponse(BaseModel):
    kind: str  # "visit" | "manual"
    date: date
    amount: int
    label: str
    ref_id: int


class FinanceEntriesListResponse(BaseModel):
    month: str
    type: str
    total: int
    items: list[FinanceEntryResponse]
    entries: list[FinanceEntryResponse]
