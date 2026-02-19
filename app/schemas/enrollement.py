from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class EnrollmentBase(BaseModel):
    user_id: str
    course_id: str
    progress: Optional[int] = 0

class EnrollmentCreate(EnrollmentBase):
    pass

class Enrollment(EnrollmentBase):
    id: str
    enrolled_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class LessonProgress(BaseModel):
    id: str
    user_id: str
    lesson_id: str
    completed: bool
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True