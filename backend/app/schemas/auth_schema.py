"""
backend/app/schemas/auth_schema.py
"""

from pydantic import BaseModel


class ManagerLoginRequest(BaseModel):
    username: str
    password: str


class EmployeeLoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    user_id: str | None = None
    role: str
