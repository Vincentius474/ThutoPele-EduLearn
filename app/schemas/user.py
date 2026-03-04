from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime

# Token schemas
class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None

# User base schema
class UserBase(BaseModel):
    email: EmailStr
    username: Optional[str] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    is_instructor: bool = False
    is_admin: bool = False
    provider: Optional[str] = None
    provider_id: Optional[str] = None
    expertise: Optional[str] = None
    experience: Optional[str] = None

# Schema for creating a user via email/password
class UserCreate(UserBase):
    password: str
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v

# Schema for updating a user
class UserUpdate(BaseModel):
    username: Optional[str] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    expertise: Optional[str] = None
    experience: Optional[str] = None
    
    class Config:
        from_attributes = True

# Schema for user in database
class UserInDB(UserBase):
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Schema for user response
class User(UserInDB):
    pass

# Schema for instructor registration
class InstructorRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    username: str
    invitation_code: str
    expertise: Optional[str] = None
    experience: Optional[str] = None
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v

# Schema for OAuth user creation
class OAuthUserCreate(BaseModel):
    email: EmailStr
    provider: str
    provider_id: str
    full_name: Optional[str] = None
    username: Optional[str] = None
    avatar_url: Optional[str] = None