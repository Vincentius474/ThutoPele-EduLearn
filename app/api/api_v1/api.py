# from fastapi import APIRouter
# from app.api.api_v1.endpoints import auth, users, courses, admin

# api_router = APIRouter()

# # Include only ONE auth router
# api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
# api_router.include_router(users.router, prefix="/users", tags=["users"])
# api_router.include_router(courses.router, prefix="/courses", tags=["courses"])
# api_router.include_router(admin.router, prefix="/admin", tags=["admin"])

from fastapi import APIRouter
from app.api.api_v1.endpoints import auth_simple, users, courses, admin

api_router = APIRouter()

api_router.include_router(auth_simple.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(courses.router, prefix="/courses", tags=["courses"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])