# from fastapi import Request, Depends
# from fastapi.templating import Jinja2Templates
# from app.core.supabase_client import get_supabase, supabase
# from typing import Optional
# from app.core.config import settings

# def get_templates(request: Request) -> Jinja2Templates:
#     """Get templates from app state"""
#     return request.app.state.templates

# def get_supabase_client():
#     """Get Supabase client"""
#     return supabase.get_client()

# async def get_current_user_web(request: Request) -> Optional[dict]:
#     """Get current user for web routes"""
#     try:
#         # Get token from cookie
#         token = request.cookies.get("access_token")
#         if not token:
#             return None
        
#         supabase = get_supabase_client()
        
#         # Set session with token
#         supabase.auth.set_session(token)
        
#         # Get user
#         user = supabase.auth.get_user()
        
#         if not user or not hasattr(user, 'user'):
#             return None
        
#         # Get additional user data
#         profile = supabase.table("users")\
#             .select("*")\
#             .eq("id", user.user.id)\
#             .execute()
        
#         user_data = {
#             "id": user.user.id,
#             "email": user.user.email,
#             "is_instructor": profile.data[0].get("is_instructor", False) if profile.data else False,
#             "is_admin": profile.data[0].get("is_admin", False) if profile.data else False,
#             "full_name": profile.data[0].get("full_name") if profile.data else None,
#             "username": profile.data[0].get("username") if profile.data else None,
#             "avatar_url": profile.data[0].get("avatar_url") if profile.data else None
#         }
        
#         return user_data
        
#     except Exception as e:
#         print(f"Error getting current user: {e}")
#         return None


# from fastapi import Request, Depends
# from fastapi.templating import Jinja2Templates
# from app.core.supabase_client import get_supabase
# from typing import Optional
# import logging

# logger = logging.getLogger(__name__)

# def get_templates(request: Request) -> Jinja2Templates:
#     """Get templates from app state"""
#     return request.app.state.templates

# def get_supabase_client():
#     """Get Supabase client for web routes"""
#     from app.core.supabase_client import supabase
#     return supabase.get_client()

# async def get_current_user_from_cookie(
#     request: Request,
#     supabase=Depends(get_supabase_client)
# ) -> Optional[dict]:
#     """
#     Get current user from cookie token for web routes.
#     """
#     token = request.cookies.get("access_token")
    
#     if not token:
#         return None
    
#     try:
#         # Get user from token
#         user = supabase.auth.get_user(token)
        
#         if not user or not hasattr(user, 'user'):
#             return None
        
#         # Get profile from database
#         profile = supabase.table("users")\
#             .select("*")\
#             .eq("id", user.user.id)\
#             .execute()
        
#         # Build user data
#         user_data = {
#             "id": user.user.id,
#             "email": user.user.email
#         }
        
#         # Add profile data if it exists
#         if profile.data and len(profile.data) > 0:
#             user_data.update(profile.data[0])
        
#         return user_data
        
#     except Exception as e:
#         logger.error(f"Error getting user from cookie: {e}")
#         return None

# # Alias for backward compatibility
# get_current_user_web = get_current_user_from_cookie

from fastapi import Request, Depends
from fastapi.templating import Jinja2Templates
from app.core.supabase_client import get_supabase, supabase
from typing import Optional
import logging

logger = logging.getLogger(__name__)

def get_templates(request: Request) -> Jinja2Templates:
    """Get templates from app state with error handling"""
    try:
        return request.app.state.templates
    except AttributeError:
        # Fallback: create new templates instance
        from pathlib import Path
        templates_dir = Path(__file__).parent.parent / "templates"
        return Jinja2Templates(directory=str(templates_dir))

def get_supabase_client():
    """Get Supabase client for web routes"""
    try:
        return supabase.get_client()
    except Exception as e:
        logger.error(f"Error getting Supabase client: {e}")
        raise

async def get_current_user_from_cookie(
    request: Request,
    supabase=Depends(get_supabase_client)
) -> Optional[dict]:
    """
    Get current user from cookie token for web routes.
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
get_current_user_web = get_current_user_from_cookie