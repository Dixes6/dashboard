from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _validate_occurred_on_bounds(v: date | None) -> date | None:
    if v is None:
        return v
    if v < date(2000, 1, 1):
        raise ValueError("Дата не может быть раньше 2000-01-01")
    today = date.today()
    try:
        max_date = today.replace(year=today.year + 1)
    except ValueError:
        max_date = today.replace(year=today.year + 1, day=28)
    if v > max_date:
        raise ValueError("Дата не может быть позже чем сегодня + 1 год")
    return v


class IncomeCreate(BaseModel):
    amount: int = Field(..., ge=1, le=100_000_000, description="Сумма дохода в рублях")
    source: str = Field(..., min_length=1, max_length=300, description="Источник дохода")
    occurred_on: date = Field(..., description="Дата поступления")

    @field_validator("source")
    @classmethod
    def validate_source_not_empty(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Источник дохода не может быть пустым")
        return trimmed

    @field_validator("occurred_on")
    @classmethod
    def validate_occurred_on(cls, value: date) -> date:
        res = _validate_occurred_on_bounds(value)
        assert res is not None
        return res


class IncomeUpdate(BaseModel):
    amount: int | None = Field(default=None, ge=1, le=100_000_000)
    source: str | None = Field(default=None, min_length=1, max_length=300)
    occurred_on: date | None = None

    @field_validator("source")
    @classmethod
    def validate_source_not_empty(cls, value: str | None) -> str | None:
        if value is not None:
            trimmed = value.strip()
            if not trimmed:
                raise ValueError("Источник дохода не может быть пустым")
            return trimmed
        return value

    @field_validator("occurred_on")
    @classmethod
    def validate_occurred_on(cls, value: date | None) -> date | None:
        return _validate_occurred_on_bounds(value)


class IncomeResponse(BaseModel):
    id: int
    amount: int
    source: str
    occurred_on: date
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExpenseCreate(BaseModel):
    amount: int = Field(..., ge=1, le=100_000_000, description="Сумма расхода в рублях")
    description: str = Field(..., min_length=1, max_length=300, description="Описание расхода")
    occurred_on: date = Field(..., description="Дата расхода")

    @field_validator("description")
    @classmethod
    def validate_description_not_empty(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Описание расхода не может быть пустым")
        return trimmed

    @field_validator("occurred_on")
    @classmethod
    def validate_occurred_on(cls, value: date) -> date:
        res = _validate_occurred_on_bounds(value)
        assert res is not None
        return res


class ExpenseUpdate(BaseModel):
    amount: int | None = Field(default=None, ge=1, le=100_000_000)
    description: str | None = Field(default=None, min_length=1, max_length=300)
    occurred_on: date | None = None

    @field_validator("description")
    @classmethod
    def validate_description_not_empty(cls, value: str | None) -> str | None:
        if value is not None:
            trimmed = value.strip()
            if not trimmed:
                raise ValueError("Описание расхода не может быть пустым")
            return trimmed
        return value

    @field_validator("occurred_on")
    @classmethod
    def validate_occurred_on(cls, value: date | None) -> date | None:
        return _validate_occurred_on_bounds(value)


class ExpenseResponse(BaseModel):
    id: int
    amount: int
    description: str
    occurred_on: date
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
