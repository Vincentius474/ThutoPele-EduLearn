from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class InvitationBase(BaseModel):
    email: EmailStr
    full_name: str
    username: str
    
class InvitationCreate(InvitationBase):
    pass

class Invitation(InvitationBase):
    id: str
    code: str
    is_used: bool
    expires_at: datetime
    created_at: datetime
    created_by: Optional[str] = None
    
    class Config:
        from_attributes = True

class InvitationVerify(BaseModel):
    email: EmailStr
    code: str

class InvitationResponse(BaseModel):
    message: str
    valid: bool
    email: Optional[str] = None
    full_name: Optional[str] = None
    username: Optional[str] = None