from typing import Optional, List, Dict, Any
from fastapi import UploadFile
from supabase import Client
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class CourseManagementService:
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
    
    # ==================== MATERIALS MANAGEMENT ====================
    async def get_materials(self, course_id: str) -> List[Dict[str, Any]]:
        """Get all materials for a course"""
        try:
            result = self.supabase.table("course_materials")\
                .select("*")\
                .eq("course_id", course_id)\
                .order("order_index")\
                .execute()
            return result.data
        except Exception as e:
            logger.error(f"Error getting materials: {e}")
            return []
    
    async def add_material(self, course_id: str, material_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Add a new material to course"""
        try:
            material_data["course_id"] = course_id
            result = self.supabase.table("course_materials").insert(material_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error adding material: {e}")
            return None
    
    async def update_material(self, material_id: str, material_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update course material"""
        try:
            material_data["updated_at"] = "now()"
            result = self.supabase.table("course_materials")\
                .update(material_data)\
                .eq("id", material_id)\
                .execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error updating material: {e}")
            return None
    
    async def delete_material(self, material_id: str) -> bool:
        """Delete course material"""
        try:
            result = self.supabase.table("course_materials")\
                .delete()\
                .eq("id", material_id)\
                .execute()
            return len(result.data) > 0
        except Exception as e:
            logger.error(f"Error deleting material: {e}")
            return False
    
    # ==================== QUIZ MANAGEMENT ====================
    
    async def create_quiz(self, course_id: str, quiz_data: Dict[str, Any], questions: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Create a quiz with questions"""
        try:
            logger.info(f"Creating quiz for course: {course_id}")
            material_data = {
                "title": quiz_data.get("title"),
                "description": quiz_data.get("description", ""),
                "material_type": "quiz",
                "course_id": course_id,
                "is_published": True,
                "order_index": 0
            }
            
            material_result = self.supabase.table("course_materials").insert(material_data).execute()
            if not material_result.data:
                logger.error("Failed to create material for quiz")
                return None
            
            material = material_result.data[0]
            logger.info(f"Material created: {material['id']}")

            quiz_insert_data = {
                "course_id": course_id,
                "material_id": material["id"],
                "title": quiz_data.get("title"),
                "description": quiz_data.get("description", ""),
                "time_limit": quiz_data.get("time_limit", 30),
                "passing_score": quiz_data.get("passing_score", 70),
                "attempts_allowed": quiz_data.get("attempts_allowed", 1)
            }
            quiz_result = self.supabase.table("quizzes").insert(quiz_insert_data).execute()
            
            if not quiz_result.data:
                logger.error("Failed to create quiz")
                self.supabase.table("course_materials").delete().eq("id", material["id"]).execute()
                return None
            
            quiz = quiz_result.data[0]
            logger.info(f"Quiz created: {quiz['id']}")
            
            for idx, q in enumerate(questions):
                question_data = {
                    "quiz_id": quiz["id"],
                    "question": q.get("question"),
                    "question_type": q.get("question_type", "multiple_choice"),
                    "options": q.get("options", []),
                    "correct_answer": q.get("correct_answer"),
                    "points": q.get("points", 1),
                    "order_index": idx
                }
                self.supabase.table("quiz_questions").insert(question_data).execute()
                logger.info(f"Question {idx + 1} added")
            
            return quiz
            
        except Exception as e:
            logger.error(f"Error creating quiz: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def get_quiz(self, quiz_id: str) -> Optional[Dict[str, Any]]:
        """Get quiz with questions"""
        try:
            quiz = self.supabase.table("quizzes")\
                .select("*")\
                .eq("id", quiz_id)\
                .execute()
            
            if not quiz.data:
                return None

            questions = self.supabase.table("quiz_questions")\
                .select("*")\
                .eq("quiz_id", quiz_id)\
                .order("order_index")\
                .execute()
            
            result = quiz.data[0]
            result["questions"] = questions.data
            return result
        except Exception as e:
            logger.error(f"Error getting quiz: {e}")
            return None
    
    # ==================== ASSIGNMENT MANAGEMENT ====================
    
    async def create_assignment(self, course_id: str, assignment_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new assignment"""
        try:
            logger.info(f"Creating assignment for course: {course_id}")
            material_data = {
                "title": assignment_data.get("title"),
                "description": assignment_data.get("description", ""),
                "material_type": "assignment",
                "course_id": course_id,
                "is_published": True,
                "order_index": 0
            }
            
            material_result = self.supabase.table("course_materials").insert(material_data).execute()
            if not material_result.data:
                logger.error("Failed to create material for assignment")
                return None
            
            material = material_result.data[0]
            logger.info(f"Material created: {material['id']}")

            assignment_insert_data = {
                "course_id": course_id,
                "material_id": material["id"],
                "title": assignment_data.get("title"),
                "description": assignment_data.get("description", ""),
                "due_date": assignment_data.get("due_date"),
                "total_points": assignment_data.get("total_points", 100),
                "submission_type": assignment_data.get("submission_type", "file")
            }
            
            result = self.supabase.table("assignments").insert(assignment_insert_data).execute()
            
            if not result.data:
                logger.error("Failed to create assignment")
                self.supabase.table("course_materials").delete().eq("id", material["id"]).execute()
                return None
            
            logger.info(f"Assignment created: {result.data[0]['id']}")
            return result.data[0]
            
        except Exception as e:
            logger.error(f"Error creating assignment: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def get_submissions(self, assignment_id: str) -> List[Dict[str, Any]]:
        """Get all submissions for an assignment"""
        try:
            result = self.supabase.table("submissions")\
                .select("*, users(full_name, email, avatar_url)")\
                .eq("assignment_id", assignment_id)\
                .order("submitted_at", desc=True)\
                .execute()
            return result.data
        except Exception as e:
            logger.error(f"Error getting submissions: {e}")
            return []
    
    async def grade_submission(self, submission_id: str, score: int, feedback: str) -> bool:
        """Grade a student submission"""
        try:
            result = self.supabase.table("submissions")\
                .update({
                    "score": score,
                    "feedback": feedback,
                    "graded_at": "now()"
                })\
                .eq("id", submission_id)\
                .execute()
            return len(result.data) > 0
        except Exception as e:
            logger.error(f"Error grading submission: {e}")
            return False
    
    # ==================== ANNOUNCEMENTS ====================
    
    async def create_announcement(self, course_id: str, instructor_id: str, announcement_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a course announcement"""
        try:
            logger.info(f"Creating announcement for course: {course_id}")
            
            announcement_insert_data = {
                "course_id": course_id,
                "instructor_id": instructor_id,
                "title": announcement_data.get("title"),
                "content": announcement_data.get("content"),
                "is_important": announcement_data.get("is_important", False),
                "send_email": announcement_data.get("send_email", False)
            }
            
            result = self.supabase.table("announcements").insert(announcement_insert_data).execute()
            
            if not result.data:
                logger.error("Failed to create announcement")
                return None
            logger.info(f"Announcement created: {result.data[0]['id']}")
            return result.data[0]
            
        except Exception as e:
            logger.error(f"Error creating announcement: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def get_announcements(self, course_id: str) -> List[Dict[str, Any]]:
        """Get all announcements for a course"""
        try:
            result = self.supabase.table("announcements")\
                .select("*, users(full_name, avatar_url)")\
                .eq("course_id", course_id)\
                .order("created_at", desc=True)\
                .execute()
            return result.data
        except Exception as e:
            logger.error(f"Error getting announcements: {e}")
            return []
    
    async def delete_announcement(self, announcement_id: str) -> bool:
        """Delete an announcement"""
        try:
            result = self.supabase.table("announcements")\
                .delete()\
                .eq("id", announcement_id)\
                .execute()
            return len(result.data) > 0
        except Exception as e:
            logger.error(f"Error deleting announcement: {e}")
            return False
    
    # ==================== FILE UPLOAD ====================
    
    async def upload_file(self, course_id: str, file: UploadFile, file_type: str) -> Optional[str]:
        """Upload a file to course materials storage"""
        try:
            from app.services.storage_service import StorageService
            
            storage_service = StorageService(self.supabase)
            return await storage_service.upload_course_material(course_id, file, file_type)
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return None