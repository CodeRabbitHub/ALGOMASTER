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
        # Require at least one letter AND at least one digit. (The previous
        # check only rejected passwords that were *entirely* digits or
        # *entirely* letters, so a symbols-only password like "!!!!!!!!"
        # satisfied it despite containing neither a letter nor a number.)
        has_letter = any(c.isalpha() for c in v)
        has_digit = any(c.isdigit() for c in v)
        if not (has_letter and has_digit):
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
    is_admin: bool = False

class UserOut(BaseModel):
    id: str
    email: str
    username: str
    is_admin: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}
