from typing import Optional, Dict, Any
from supabase import Client
from app.schemas.user import UserCreate
import logging

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
    
    async def register_user(self, email: str, password: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new user with Supabase Auth"""
        try:
            # Register with Supabase Auth
            auth_response = self.supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": user_data
                }
            })
            
            if not auth_response.user:
                return {"success": False, "error": "Registration failed"}
            
            # Create profile in public.users table
            profile_data = {
                "id": auth_response.user.id,
                "email": email,
                "username": user_data.get("username"),
                "full_name": user_data.get("full_name"),
                "is_instructor": user_data.get("role") == "instructor",
                "is_admin": False
            }
            
            profile_result = self.supabase.table("users").insert(profile_data).execute()
            
            return {
                "success": True,
                "user": auth_response.user,
                "profile": profile_result.data[0] if profile_result.data else None
            }
            
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return {"success": False, "error": str(e)}
    
    async def login_user(self, email: str, password: str) -> Dict[str, Any]:
        """Login user with email and password"""
        try:
            auth_response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if not auth_response.session:
                return {"success": False, "error": "Login failed"}
            
            return {
                "success": True,
                "session": auth_response.session,
                "user": auth_response.user
            }
            
        except Exception as e:
            logger.error(f"Login error: {e}")
            return {"success": False, "error": str(e)}
    
    async def logout_user(self) -> Dict[str, Any]:
        """Logout current user"""
        try:
            self.supabase.auth.sign_out()
            return {"success": True, "message": "Logged out successfully"}
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Get currently authenticated user"""
        try:
            user = self.supabase.auth.get_user()
            if not user or not hasattr(user, 'user'):
                return None
            
            # Get additional profile data
            profile = self.supabase.table("users")\
                .select("*")\
                .eq("id", user.user.id)\
                .execute()
            
            user_data = {
                "id": user.user.id,
                "email": user.user.email,
                "profile": profile.data[0] if profile.data else None
            }
            
            return user_data
            
        except Exception as e:
            logger.error(f"Get current user error: {e}")
            return None
    
    async def reset_password(self, email: str) -> Dict[str, Any]:
        """Send password reset email"""
        try:
            self.supabase.auth.reset_password_for_email(email)
            return {"success": True, "message": "Password reset email sent"}
        except Exception as e:
            logger.error(f"Reset password error: {e}")
            return {"success": False, "error": str(e)}
    
    async def update_password(self, new_password: str) -> Dict[str, Any]:
        """Update user password"""
        try:
            self.supabase.auth.update_user({"password": new_password})
            return {"success": True, "message": "Password updated successfully"}
        except Exception as e:
            logger.error(f"Update password error: {e}")
            return {"success": False, "error": str(e)}