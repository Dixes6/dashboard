from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class IncomeCreate(BaseModel):
    amount: int = Field(..., gt=0, description="Сумма дохода в рублях")
    source: str = Field(..., min_length=1, description="Источник дохода")
    occurred_on: date = Field(..., description="Дата поступления")

    @field_validator("source")
    @classmethod
    def validate_source_not_empty(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Источник дохода не может быть пустым")
        return trimmed


class IncomeUpdate(BaseModel):
    amount: int | None = Field(default=None, gt=0)
    source: str | None = Field(default=None, min_length=1)
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


class IncomeResponse(BaseModel):
    id: int
    amount: int
    source: str
    occurred_on: date
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExpenseCreate(BaseModel):
    amount: int = Field(..., gt=0, description="Сумма расхода в рублях")
    description: str = Field(..., min_length=1, description="Описание расхода")
    occurred_on: date = Field(..., description="Дата расхода")

    @field_validator("description")
    @classmethod
    def validate_description_not_empty(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Описание расхода не может быть пустым")
        return trimmed


class ExpenseUpdate(BaseModel):
    amount: int | None = Field(default=None, gt=0)
    description: str | None = Field(default=None, min_length=1)
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


class ExpenseResponse(BaseModel):
    id: int
    amount: int
    description: str
    occurred_on: date
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
