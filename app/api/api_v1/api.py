from fastapi import APIRouter
from app.api.api_v1.endpoints import auth_simple, blog, tutorials, users, courses, admin, course_management, messages, resources

api_router = APIRouter()

api_router.include_router(auth_simple.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(courses.router, prefix="/courses", tags=["courses"])
api_router.include_router(course_management.router, prefix="", tags=["course-management"])
api_router.include_router(messages.router, prefix="", tags=["messages"])
api_router.include_router(resources.router, prefix="", tags=["resources"])
api_router.include_router(tutorials.router, prefix="", tags=["tutorials"])
api_router.include_router(blog.router, prefix="", tags=["blog"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])