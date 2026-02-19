from fastapi import Depends, HTTPException, status, Request
from app.core.supabase_client import get_supabase

async def get_current_user(request: Request, supabase=Depends(get_supabase)):
    """
    Get current authenticated user from Supabase.
    """
    try:
        # Get token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header.replace("Bearer ", "")
        
        # Set the session with the token
        supabase.auth.set_session(token)
        
        # Get user
        user = supabase.auth.get_user()
        
        if not user or not hasattr(user, 'user'):
            return None
        
        # Get additional user data
        profile = supabase.table("users")\
            .select("*")\
            .eq("id", user.user.id)\
            .execute()
        
        user_data = {
            "id": user.user.id,
            "email": user.user.email,
            "is_instructor": profile.data[0].get("is_instructor", False) if profile.data else False,
            "is_admin": profile.data[0].get("is_admin", False) if profile.data else False,
            "full_name": profile.data[0].get("full_name") if profile.data else None,
            "username": profile.data[0].get("username") if profile.data else None
        }
        
        return user_data
        
    except Exception:
        return None

async def get_current_active_user(current_user: dict = Depends(get_current_user)):
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

async def get_current_instructor(current_user: dict = Depends(get_current_active_user)):
    """
    Get current user and verify they are an instructor.
    """
    if not current_user.get("is_instructor"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Instructor privileges required"
        )
    return current_user

async def get_current_admin(current_user: dict = Depends(get_current_active_user)):
    """
    Get current user and verify they are an admin.
    """
    if not current_user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user

# Add this new dependency
async def get_current_admin(current_user: dict = Depends(get_current_active_user)):
    """
    Get current user and verify they are an admin.
    """
    if not current_user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user