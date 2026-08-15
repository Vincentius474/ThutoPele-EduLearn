from typing import Optional, List
from pydantic_settings import BaseSettings
import os
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    PROJECT_NAME: str = "E-Learning Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() in {"1", "true", "yes"}

    # Application URL
    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8000")

    # Supabase Configuration
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "")

    # JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

    # CORS
    BACKEND_CORS_ORIGINS: str = os.getenv(
        "BACKEND_CORS_ORIGINS",
        "http://localhost:3000,http://localhost:8000"
    )

    # Maintenance mode
    MAINTENANCE_MODE: bool = os.getenv("MAINTENANCE_MODE", "false").lower() in {"1", "true", "yes"}
    MAINTENANCE_MESSAGE: str = os.getenv("MAINTENANCE_MESSAGE", "We are performing scheduled maintenance. Please try again shortly.")

    # Supabase Storage buckets
    COURSE_BUCKET: str = "course-materials"
    PROFILE_BUCKET: str = "profile-pictures"

    class Config:
        case_sensitive = True


settings = Settings()


def get_cors_origins() -> List[str]:
    return [origin.strip() for origin in settings.BACKEND_CORS_ORIGINS.split(",") if origin.strip()]