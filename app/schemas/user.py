from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime

# Add this new schema for instructor registration
class InstructorRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    username: str
    invitation_code: str
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v

# Update UserCreate to include role
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    username: str
    role: str = "student"  # "student" or "instructor"
    invitation_code: Optional[str] = None  # Required if role is instructor
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v
    
    @validator('invitation_code')
    def validate_invitation_code(cls, v, values):
        if values.get('role') == 'instructor' and not v:
            raise ValueError('Invitation code is required for instructors')
        return v

# Token schemas
class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None

# User schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    is_active: Optional[bool] = True
    is_instructor: Optional[bool] = False
    
class UserCreate(UserBase):
    password: str
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_instructor: Optional[bool] = None

class UserInDB(UserBase):
    id: str  # Changed to str for UUID
    is_superuser: bool = False
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class User(UserInDB):
    pass