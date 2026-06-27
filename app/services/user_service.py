from typing import Optional, List, Dict, Any
from supabase import Client

class UserService:
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
    
    async def get_users(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all users"""
        result = self.supabase.table("users")\
            .select("*")\
            .range(skip, skip + limit - 1)\
            .execute()
        return result.data
    
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a single user by ID"""
        result = self.supabase.table("users")\
            .select("*")\
            .eq("id", user_id)\
            .execute()
        return result.data[0] if result.data else None
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get a user by email"""
        result = self.supabase.table("users")\
            .select("*")\
            .eq("email", email)\
            .execute()
        return result.data[0] if result.data else None
    
    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user profile"""
        result = self.supabase.table("users").insert(user_data).execute()
        return result.data[0] if result.data else None
    
    async def update_user(self, user_id: str, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing user"""
        result = self.supabase.table("users")\
            .update(user_data)\
            .eq("id", user_id)\
            .execute()
        return result.data[0] if result.data else None
    
    async def delete_user(self, user_id: str) -> bool:
        """Delete a user profile"""
        result = self.supabase.table("users")\
            .delete()\
            .eq("id", user_id)\
            .execute()
        return len(result.data) > 0
    
    async def get_user_courses(self, user_id: str) -> List[Dict[str, Any]]:
        """Get courses a user is enrolled in"""
        enrollments = self.supabase.table("enrollments")\
            .select("*, courses(*)")\
            .eq("user_id", user_id)\
            .execute()
        courses = []
        for enrollment in enrollments.data:
            if enrollment.get("courses"):
                course = enrollment["courses"]
                course["enrollment"] = {
                    "enrolled_at": enrollment["enrolled_at"],
                    "progress": enrollment["progress"],
                    "completed_at": enrollment["completed_at"]
                }
                courses.append(course)
        return courses
    
    async def get_user_taught_courses(self, user_id: str) -> List[Dict[str, Any]]:
        """Get courses a user is teaching"""
        result = self.supabase.table("courses")\
            .select("*")\
            .eq("instructor_id", user_id)\
            .execute()
        return result.data
    
    async def make_instructor(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Make a user an instructor"""
        return await self.update_user(user_id, {"is_instructor": True})