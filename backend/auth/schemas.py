from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    role: str = "general"


class UserResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: str
    status: str


class RegisterResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: str
    status: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: RegisterResponse