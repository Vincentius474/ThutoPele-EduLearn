from typing import Optional, List, Dict, Any
from supabase import Client
import logging

logger = logging.getLogger(__name__)

class CourseService:
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
    
    async def get_courses(
        self, 
        skip: int = 0, 
        limit: int = 100, 
        category: Optional[str] = None,
        level: Optional[str] = None,
        is_published: Optional[bool] = True
    ) -> List[Dict[str, Any]]:
        """Get courses with optional filters"""
        try:
            query = self.supabase.table("courses").select("*")
            
            if category:
                query = query.eq("category", category)
            if level:
                query = query.eq("level", level)
            if is_published is not None:
                query = query.eq("is_published", is_published)
            
            # Add ordering
            query = query.order("created_at", desc=True)
            
            result = query.range(skip, skip + limit - 1).execute()
            logger.info(f"Retrieved {len(result.data)} courses")
            return result.data
            
        except Exception as e:
            logger.error(f"Error getting courses: {e}")
            return []

    async def create_course(self, course_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new course using service role (bypasses RLS for testing)"""
        try:
            logger.info(f"Attempting to create course: {course_data.get('title')}")
            logger.info(f"Instructor ID: {course_data.get('instructor_id')}")
            
            # Validate required fields
            required_fields = ['title', 'instructor_id']
            for field in required_fields:
                if field not in course_data:
                    logger.error(f"Missing required field: {field}")
                    return None
            
            # Use service client to bypass RLS
            from app.core.supabase_client import supabase
            service_client = supabase.get_service_client()
            
            result = service_client.table("courses").insert(course_data).execute()
            
            if result.data and len(result.data) > 0:
                logger.info(f"✅ Created course: {course_data.get('title')} with ID: {result.data[0]['id']}")
                return result.data[0]
            else:
                logger.error("No data returned from insert operation")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error creating course: {str(e)}")
            if hasattr(e, 'response') and hasattr(e.response, 'json'):
                try:
                    error_detail = e.response.json()
                    logger.error(f"Error details: {error_detail}")
                except:
                    pass
            logger.exception("Full traceback:")
            return None

    async def get_course(self, course_id: str) -> Optional[Dict[str, Any]]:
        """Get a single course by ID"""
        try:
            result = self.supabase.table("courses")\
                .select("*")\
                .eq("id", course_id)\
                .execute()
            
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(f"Error getting course {course_id}: {e}")
            return None

    async def update_course(self, course_id: str, course_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing course"""
        try:
            # Add updated_at timestamp
            course_data["updated_at"] = "now()"
            
            result = self.supabase.table("courses")\
                .update(course_data)\
                .eq("id", course_id)\
                .execute()
            
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error updating course {course_id}: {e}")
            return None
    
    async def delete_course(self, course_id: str) -> bool:
        """Delete a course"""
        try:
            result = self.supabase.table("courses")\
                .delete()\
                .eq("id", course_id)\
                .execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error deleting course {course_id}: {e}")
            return False
    
    async def get_course_with_details(self, course_id: str) -> Optional[Dict[str, Any]]:
        """Get course with instructor and lessons"""
        try:
            course = await self.get_course(course_id)
            if not course:
                return None
            
            # Get instructor details
            instructor = self.supabase.table("users")\
                .select("id, email, full_name, username, avatar_url")\
                .eq("id", course["instructor_id"])\
                .execute()
            
            if instructor.data:
                course["instructor"] = instructor.data[0]
            
            # Get lessons
            lessons = self.supabase.table("lessons")\
                .select("*")\
                .eq("course_id", course_id)\
                .order("order_index")\
                .execute()
            
            course["lessons"] = lessons.data
            
            return course
            
        except Exception as e:
            logger.error(f"Error getting course details for {course_id}: {e}")
            return None
    
    async def get_courses_by_instructor(self, instructor_id: str) -> List[Dict[str, Any]]:
        """Get all courses by a specific instructor"""
        try:
            result = self.supabase.table("courses")\
                .select("*")\
                .eq("instructor_id", instructor_id)\
                .execute()
            
            return result.data
            
        except Exception as e:
            logger.error(f"Error getting courses for instructor {instructor_id}: {e}")
            return []
    
    async def publish_course(self, course_id: str) -> Optional[Dict[str, Any]]:
        """Publish a course"""
        return await self.update_course(course_id, {"is_published": True})
    
    async def unpublish_course(self, course_id: str) -> Optional[Dict[str, Any]]:
        """Unpublish a course"""
        return await self.update_course(course_id, {"is_published": False})