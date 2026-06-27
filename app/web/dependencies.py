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
        logger.error(f"Error getting user from cookie: {e}")
        return None

get_current_user_web = get_current_user_from_cookie