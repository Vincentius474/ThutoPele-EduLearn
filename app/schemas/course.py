from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime

class CourseBase(BaseModel):
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    level: Optional[str] = None  # Beginner, Intermediate, Advanced
    price: Optional[int] = 0
    is_published: Optional[bool] = False
    
    @validator('category')
    def validate_category(cls, v):
        if v:
            allowed_categories = [
                'Programming', 'Robotics', 'Artificial Intelligence', 
                'Machine Learning', 'Networking', 'Cyber Security'
            ]
            if v not in allowed_categories:
                raise ValueError(f'Category must be one of: {", ".join(allowed_categories)}')
        return v

class CourseCreate(CourseBase):
    pass

class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    level: Optional[str] = None
    price: Optional[int] = None
    is_published: Optional[bool] = None
    
    @validator('category')
    def validate_category(cls, v):
        if v:
            allowed_categories = [
                'Programming', 'Robotics', 'Artificial Intelligence', 
                'Machine Learning', 'Networking', 'Cyber Security'
            ]
            if v not in allowed_categories:
                raise ValueError(f'Category must be one of: {", ".join(allowed_categories)}')
        return v

class Course(CourseBase):
    id: str
    instructor_id: str
    thumbnail_url: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    instructor: Optional[dict] = None
    lessons: Optional[List[dict]] = None
    
    class Config:
        from_attributes = True