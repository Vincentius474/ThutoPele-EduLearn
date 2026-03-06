from fastapi import Request, Depends, HTTPException, status
from app.core.supabase_client import get_supabase
from typing import Optional
import logging

from app.web.dependencies import get_supabase_client

logger = logging.getLogger(__name__)

async def get_current_user_from_cookie(
    request: Request,
    supabase=Depends(get_supabase)
) -> Optional[dict]:
    """
    Get current user from cookie token.
    """
    token = request.cookies.get("access_token")
    
    if not token:
        return None
    
    try:
        # Get user from token
        user = supabase.auth.get_user(token)
        
        if not user or not hasattr(user, 'user'):
            return None
        
        # Get profile from database
        profile = supabase.table("users")\
            .select("*")\
            .eq("id", user.user.id)\
            .execute()
        
        # Build user data
        user_data = {
            "id": user.user.id,
            "email": user.user.email
        }
        
        # Add profile data if it exists
        if profile.data and len(profile.data) > 0:
            user_data.update(profile.data[0])
        
        return user_data
        
    except Exception as e:
        logger.error(f"Error getting user from cookie: {e}")
        return None

# Alias for backward compatibility
get_current_user = get_current_user_from_cookie

async def get_current_active_user(
    current_user: Optional[dict] = Depends(get_current_user_from_cookie)
) -> dict:
    """
    Get current active user (raises exception if not authenticated).
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user

# In app/api/api_v1/dependencies.py

async def get_current_instructor(
    current_user: dict = Depends(get_current_active_user)
) -> dict:
    """
    Get current user and verify they are an instructor.
    """
    if not current_user.get("is_instructor"):
        # Double-check in database
        supabase = get_supabase_client()
        result = supabase.table("users")\
            .select("is_instructor")\
            .eq("id", current_user["id"])\
            .execute()
        
        if not result.data or not result.data[0].get("is_instructor"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Instructor privileges required"
            )
        
        # Update the current_user dict
        current_user["is_instructor"] = True
    
    return current_user

async def get_current_admin(
    current_user: dict = Depends(get_current_active_user)
) -> dict:
    """
    Get current user and verify they are an admin.
    """
    if not current_user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user

# Optional: Add token-based authentication for API clients
async def get_current_user_from_token(
    authorization: str = Depends(lambda request: request.headers.get("Authorization", "")),
    supabase=Depends(get_supabase)
) -> Optional[dict]:
    """
    Get current user from Bearer token in Authorization header.
    """
    if not authorization.startswith("Bearer "):
        return None
    
    token = authorization.replace("Bearer ", "")
    
    try:
        user = supabase.auth.get_user(token)
        
        if not user or not hasattr(user, 'user'):
            return None
        
        profile = supabase.table("users")\
            .select("*")\
            .eq("id", user.user.id)\
            .execute()
        
        user_data = {
            "id": user.user.id,
            "email": user.user.email
        }
        
        if profile.data and len(profile.data) > 0:
            user_data.update(profile.data[0])
        
        return user_data
        
    except Exception as e:
        logger.error(f"Error getting user from token: {e}")
        return None