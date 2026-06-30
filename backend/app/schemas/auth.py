from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime
import uuid

class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50, pattern=r'^[a-zA-Z0-9_-]+$')
    password: str = Field(min_length=8, max_length=72)  # 72 = bcrypt hard limit

    @field_validator('password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        if v.isdigit() or v.isalpha():
            raise ValueError('Password must contain both letters and numbers')
        return v

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    email: str

class UserOut(BaseModel):
    id: str
    email: str
    username: str
    created_at: datetime

    model_config = {"from_attributes": True}
