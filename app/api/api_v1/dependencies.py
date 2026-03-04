from fastapi import Request, Depends, HTTPException, status
from app.core.supabase_client import get_supabase
from typing import Optional
import logging

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
        # Set session with token
        supabase.auth.set_session(token)
        
        # Get user
        user = supabase.auth.get_user()
        
        if not user or not hasattr(user, 'user'):
            return None
        
        # Get additional user data from public.users table
        profile = supabase.table("users")\
            .select("*")\
            .eq("id", user.user.id)\
            .execute()
        
        if not profile.data:
            return None
        
        user_data = {
            "id": user.user.id,
            "email": user.user.email,
            **profile.data[0]
        }
        
        return user_data
        
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        return None

# Alias for backward compatibility - this is what courses.py is importing
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

async def get_current_instructor(
    current_user: dict = Depends(get_current_active_user)
) -> dict:
    """
    Get current user and verify they are an instructor.
    """
    if not current_user.get("is_instructor"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Instructor privileges required"
        )
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