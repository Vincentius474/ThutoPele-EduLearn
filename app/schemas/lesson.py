from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class LessonBase(BaseModel):
    title: str
    description: Optional[str] = None
    content_type: str  # video, article, quiz, assignment
    content_url: Optional[str] = None
    duration: Optional[int] = None  # in minutes
    order_index: int
    is_free: Optional[bool] = False

class LessonCreate(LessonBase):
    course_id: str

class LessonUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    content_type: Optional[str] = None
    content_url: Optional[str] = None
    duration: Optional[int] = None
    order_index: Optional[int] = None
    is_free: Optional[bool] = None

class Lesson(LessonBase):
    id: str
    course_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True