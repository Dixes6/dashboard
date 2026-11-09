from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    login: str
    password: str


class UserResponse(BaseModel):
    id: int
    login: str

    model_config = ConfigDict(from_attributes=True)
