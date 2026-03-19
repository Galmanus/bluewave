import uuid

from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    tenant_name: str
    email: EmailStr
    password: str
    full_name: str


class RegisterResponse(BaseModel):
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    message: str = "Tenant created"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
