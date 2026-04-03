from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse
import json

from app.core.supabase_client import get_supabase
from app.services.course_management_service import CourseManagementService
from app.api.api_v1.dependencies import get_current_instructor
from app.schemas.course import Course

router = APIRouter()

async def get_management_service(supabase=Depends(get_supabase)) -> CourseManagementService:
    return CourseManagementService(supabase)

# ==================== COURSE MATERIALS ====================

@router.post("/courses/{course_id}/materials")
async def create_material(
    course_id: str,
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    material_type: str = Form(...),
    file: Optional[UploadFile] = File(None),
    content_url: Optional[str] = Form(None),
    service: CourseManagementService = Depends(get_management_service),
    instructor: dict = Depends(get_current_instructor)
) -> Any:
    """
    Create a new course material (video, document, link, file)
    """
    try:
        # Verify instructor owns this course
        course_check = service.supabase.table("courses")\
            .select("instructor_id")\
            .eq("id", course_id)\
            .execute()
        
        if not course_check.data or course_check.data[0]["instructor_id"] != instructor["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to modify this course"
            )
        
        material_data = {
            "title": title,
            "description": description,
            "material_type": material_type,
            "course_id": course_id
        }
        
        # Handle file upload
        if file:
            file_url = await service.upload_file(course_id, file, "materials")
            if file_url:
                material_data["content_url"] = file_url
                material_data["file_name"] = file.filename
                material_data["file_size"] = file.size
        elif content_url:
            material_data["content_url"] = content_url
        
        # Get max order index
        existing = await service.get_materials(course_id)
        material_data["order_index"] = len(existing)
        
        material = await service.add_material(course_id, material_data)
        
        if not material:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create material"
            )
        
        return material
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating material: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating material: {str(e)}"
        )


@router.get("/courses/materials/{material_id}")
async def get_material(
    material_id: str,
    service: CourseManagementService = Depends(get_management_service),
    instructor: dict = Depends(get_current_instructor)
) -> Any:
    """
    Get a single material by ID
    """
    try:
        result = service.supabase.table("course_materials")\
            .select("*")\
            .eq("id", material_id)\
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Material not found"
            )
        
        material = result.data[0]
        
        # Verify instructor owns this course
        course_check = service.supabase.table("courses")\
            .select("instructor_id")\
            .eq("id", material["course_id"])\
            .execute()
        
        if not course_check.data or course_check.data[0]["instructor_id"] != instructor["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this material"
            )
        
        return material
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting material: {str(e)}"
        )


@router.get("/courses/{course_id}/materials")
async def get_materials(
    course_id: str,
    service: CourseManagementService = Depends(get_management_service),
    instructor: dict = Depends(get_current_instructor)
) -> Any:
    """
    Get all materials for a course
    """
    try:
        materials = await service.get_materials(course_id)
        return materials
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting materials: {str(e)}"
        )

@router.put("/courses/materials/{material_id}")
async def update_material(
    material_id: str,
    request: Request,
    service: CourseManagementService = Depends(get_management_service),
    instructor: dict = Depends(get_current_instructor)
) -> Any:
    """
    Update course material
    """
    try:
        data = await request.json()
        material = await service.update_material(material_id, data)
        
        if not material:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Material not found"
            )
        
        return material
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating material: {str(e)}"
        )

@router.delete("/courses/{course_id}/materials/{material_id}")
async def delete_material(
    course_id: str,
    material_id: str,
    service: CourseManagementService = Depends(get_management_service),
    instructor: dict = Depends(get_current_instructor)
) -> Any:
    """
    Delete a course material
    """
    try:
        # Verify instructor owns this course
        course_check = service.supabase.table("courses")\
            .select("instructor_id")\
            .eq("id", course_id)\
            .execute()
        
        if not course_check.data or course_check.data[0]["instructor_id"] != instructor["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete materials from this course"
            )
        
        deleted = await service.delete_material(material_id)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Material not found"
            )
        
        return {"message": "Material deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting material: {str(e)}"
        )

# ==================== QUIZZES ====================

@router.post("/courses/{course_id}/quizzes")
async def create_quiz(
    course_id: str,
    request: Request,
    service: CourseManagementService = Depends(get_management_service),
    instructor: dict = Depends(get_current_instructor)
) -> Any:
    """
    Create a new quiz with questions
    """
    try:
        data = await request.json()
        print(f"Received quiz data: {data}")
        
        title = data.get("title")
        description = data.get("description", "")
        time_limit = data.get("time_limit", 30)
        passing_score = data.get("passing_score", 70)
        questions = data.get("questions", [])
        
        if not title or not questions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Title and questions are required"
            )
        
        # Prepare quiz data for service (without material - service will create it)
        quiz_data = {
            "title": title,
            "description": description,
            "time_limit": time_limit,
            "passing_score": passing_score
        }
        
        # Let the service handle both material and quiz creation
        quiz = await service.create_quiz(course_id, quiz_data, questions)
        
        if not quiz:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create quiz"
            )
        
        return quiz
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating quiz: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating quiz: {str(e)}"
        )

@router.get("/courses/quizzes/{quiz_id}")
async def get_quiz(
    quiz_id: str,
    service: CourseManagementService = Depends(get_management_service),
    instructor: dict = Depends(get_current_instructor)
) -> Any:
    """
    Get quiz details with questions
    """
    try:
        quiz = await service.get_quiz(quiz_id)
        
        if not quiz:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quiz not found"
            )
        
        return quiz
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting quiz: {str(e)}"
        )

@router.get("/courses/quizzes/{quiz_id}/edit")
async def get_quiz_for_edit(
    quiz_id: str,
    service: CourseManagementService = Depends(get_management_service),
    instructor: dict = Depends(get_current_instructor)
) -> Any:
    """
    Get quiz details for editing
    """
    try:
        # Get quiz with questions
        quiz = await service.get_quiz(quiz_id)
        
        if not quiz:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quiz not found"
            )
        
        # Verify instructor owns this course
        course_check = service.supabase.table("courses")\
            .select("instructor_id")\
            .eq("id", quiz["course_id"])\
            .execute()
        
        if not course_check.data or course_check.data[0]["instructor_id"] != instructor["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to edit this quiz"
            )
        
        return quiz
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting quiz: {str(e)}"
        )

@router.put("/courses/quizzes/{quiz_id}")
async def update_quiz(
    quiz_id: str,
    request: Request,
    service: CourseManagementService = Depends(get_management_service),
    instructor: dict = Depends(get_current_instructor)
) -> Any:
    """
    Update a quiz
    """
    try:
        data = await request.json()
        
        # Get existing quiz to verify ownership
        existing = service.supabase.table("quizzes")\
            .select("course_id, material_id")\
            .eq("id", quiz_id)\
            .execute()
        
        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quiz not found"
            )
        
        course_id = existing.data[0]["course_id"]
        material_id = existing.data[0].get("material_id")
        
        # Verify instructor owns this course
        course_check = service.supabase.table("courses")\
            .select("instructor_id")\
            .eq("id", course_id)\
            .execute()
        
        if not course_check.data or course_check.data[0]["instructor_id"] != instructor["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this quiz"
            )
        
        # Update quiz
        update_data = {
            "title": data.get("title"),
            "description": data.get("description", ""),
            "time_limit": data.get("time_limit", 30),
            "passing_score": data.get("passing_score", 70),
            "updated_at": "now()"
        }
        
        # Remove None values
        update_data = {k: v for k, v in update_data.items() if v is not None}
        
        result = service.supabase.table("quizzes")\
            .update(update_data)\
            .eq("id", quiz_id)\
            .execute()
        
        # Update associated material
        if material_id:
            service.supabase.table("course_materials")\
                .update({
                    "title": data.get("title"),
                    "description": data.get("description", ""),
                    "updated_at": "now()"
                })\
                .eq("id", material_id)\
                .execute()
        
        # Update questions if provided
        questions = data.get("questions", [])
        if questions:
            # Delete existing questions
            service.supabase.table("quiz_questions")\
                .delete()\
                .eq("quiz_id", quiz_id)\
                .execute()
            
            # Insert updated questions
            for idx, q in enumerate(questions):
                question_data = {
                    "quiz_id": quiz_id,
                    "question": q.get("question"),
                    "question_type": q.get("question_type", "multiple_choice"),
                    "options": q.get("options", []),
                    "correct_answer": q.get("correct_answer"),
                    "points": q.get("points", 1),
                    "order_index": idx
                }
                service.supabase.table("quiz_questions").insert(question_data).execute()
        
        return result.data[0] if result.data else None
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating quiz: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating quiz: {str(e)}"
        )

@router.delete("/courses/quizzes/{quiz_id}")
async def delete_quiz(
    quiz_id: str,
    service: CourseManagementService = Depends(get_management_service),
    instructor: dict = Depends(get_current_instructor)
) -> Any:
    """
    Delete a quiz
    """
    try:
        # Get quiz to get course_id for verification
        quiz = service.supabase.table("quizzes")\
            .select("course_id, material_id")\
            .eq("id", quiz_id)\
            .execute()
        
        if not quiz.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quiz not found"
            )
        
        course_id = quiz.data[0]["course_id"]
        material_id = quiz.data[0].get("material_id")
        
        # Verify instructor owns this course
        course_check = service.supabase.table("courses")\
            .select("instructor_id")\
            .eq("id", course_id)\
            .execute()
        
        if not course_check.data or course_check.data[0]["instructor_id"] != instructor["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this quiz"
            )
        
        # Delete associated material first
        if material_id:
            await service.delete_material(material_id)
        
        # Delete quiz (questions will cascade delete)
        result = service.supabase.table("quizzes")\
            .delete()\
            .eq("id", quiz_id)\
            .execute()
        
        return {"message": "Quiz deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting quiz: {str(e)}"
        )

# ==================== ASSIGNMENTS ====================

@router.post("/courses/{course_id}/assignments")
async def create_assignment(
    course_id: str,
    request: Request,
    service: CourseManagementService = Depends(get_management_service),
    instructor: dict = Depends(get_current_instructor)
) -> Any:
    """
    Create a new assignment
    """
    try:
        data = await request.json()
        print(f"Received assignment data: {data}")
        
        title = data.get("title")
        description = data.get("description")
        due_date = data.get("due_date")
        total_points = data.get("total_points", 100)
        submission_type = data.get("submission_type", "file")
        
        if not title or not description:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Title and description are required"
            )
        
        # Prepare assignment data (service will create material)
        assignment_data = {
            "title": title,
            "description": description,
            "due_date": due_date,
            "total_points": total_points,
            "submission_type": submission_type
        }
        
        assignment = await service.create_assignment(course_id, assignment_data)
        
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create assignment"
            )
        
        return assignment
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating assignment: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating assignment: {str(e)}"
        )

@router.get("/courses/assignments/{assignment_id}/submissions")
async def get_submissions(
    assignment_id: str,
    service: CourseManagementService = Depends(get_management_service),
    instructor: dict = Depends(get_current_instructor)
) -> Any:
    """
    Get all submissions for an assignment
    """
    try:
        submissions = await service.get_submissions(assignment_id)
        return submissions
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting submissions: {str(e)}"
        )

@router.get("/courses/assignments/{assignment_id}/edit")
async def get_assignment_for_edit(
    assignment_id: str,
    service: CourseManagementService = Depends(get_management_service),
    instructor: dict = Depends(get_current_instructor)
) -> Any:
    """
    Get assignment details for editing
    """
    try:
        result = service.supabase.table("assignments")\
            .select("*")\
            .eq("id", assignment_id)\
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        
        assignment = result.data[0]
        
        # Verify instructor owns this course
        course_check = service.supabase.table("courses")\
            .select("instructor_id")\
            .eq("id", assignment["course_id"])\
            .execute()
        
        if not course_check.data or course_check.data[0]["instructor_id"] != instructor["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to edit this assignment"
            )
        
        return assignment
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting assignment: {str(e)}"
        )

@router.put("/courses/assignments/{assignment_id}")
async def update_assignment(
    assignment_id: str,
    request: Request,
    service: CourseManagementService = Depends(get_management_service),
    instructor: dict = Depends(get_current_instructor)
) -> Any:
    """
    Update an assignment
    """
    try:
        data = await request.json()
        
        # Get existing assignment to verify ownership
        existing = service.supabase.table("assignments")\
            .select("course_id, material_id")\
            .eq("id", assignment_id)\
            .execute()
        
        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        
        course_id = existing.data[0]["course_id"]
        material_id = existing.data[0].get("material_id")
        
        # Verify instructor owns this course
        course_check = service.supabase.table("courses")\
            .select("instructor_id")\
            .eq("id", course_id)\
            .execute()
        
        if not course_check.data or course_check.data[0]["instructor_id"] != instructor["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this assignment"
            )
        
        # Update assignment
        update_data = {
            "title": data.get("title"),
            "description": data.get("description"),
            "due_date": data.get("due_date"),
            "total_points": data.get("total_points", 100),
            "submission_type": data.get("submission_type", "file"),
            "updated_at": "now()"
        }
        
        # Remove None values
        update_data = {k: v for k, v in update_data.items() if v is not None}
        
        result = service.supabase.table("assignments")\
            .update(update_data)\
            .eq("id", assignment_id)\
            .execute()
        
        # Update associated material
        if material_id:
            service.supabase.table("course_materials")\
                .update({
                    "title": data.get("title"),
                    "description": data.get("description"),
                    "updated_at": "now()"
                })\
                .eq("id", material_id)\
                .execute()
        
        return result.data[0] if result.data else None
        
    except Exception as e:
        print(f"Error updating assignment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating assignment: {str(e)}"
        )

@router.delete("/courses/assignments/{assignment_id}")
async def delete_assignment(
    assignment_id: str,
    service: CourseManagementService = Depends(get_management_service),
    instructor: dict = Depends(get_current_instructor)
) -> Any:
    """
    Delete an assignment
    """
    try:
        # Get assignment to get course_id for verification
        assignment = service.supabase.table("assignments")\
            .select("course_id, material_id")\
            .eq("id", assignment_id)\
            .execute()
        
        if not assignment.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        
        course_id = assignment.data[0]["course_id"]
        material_id = assignment.data[0].get("material_id")
        
        # Verify instructor owns this course
        course_check = service.supabase.table("courses")\
            .select("instructor_id")\
            .eq("id", course_id)\
            .execute()
        
        if not course_check.data or course_check.data[0]["instructor_id"] != instructor["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this assignment"
            )
        
        # Delete associated material first
        if material_id:
            await service.delete_material(material_id)
        
        # Delete assignment
        result = service.supabase.table("assignments")\
            .delete()\
            .eq("id", assignment_id)\
            .execute()
        
        return {"message": "Assignment deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting assignment: {str(e)}"
        )

@router.post("/courses/submissions/{submission_id}/grade")
async def grade_submission(
    submission_id: str,
    request: Request,
    service: CourseManagementService = Depends(get_management_service),
    instructor: dict = Depends(get_current_instructor)
) -> Any:
    """
    Grade a student submission
    """
    try:
        data = await request.json()
        score = data.get("score")
        feedback = data.get("feedback", "")
        
        if score is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Score is required"
            )
        
        graded = await service.grade_submission(submission_id, score, feedback)
        
        if not graded:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Submission not found"
            )
        
        return {"message": "Submission graded successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error grading submission: {str(e)}"
        )

# ==================== ANNOUNCEMENTS ====================

@router.post("/courses/{course_id}/announcements")
async def create_announcement(
    course_id: str,
    request: Request,
    service: CourseManagementService = Depends(get_management_service),
    instructor: dict = Depends(get_current_instructor)
) -> Any:
    """
    Create a course announcement
    """
    try:
        data = await request.json()
        print(f"Received announcement data: {data}")
        
        title = data.get("title")
        content = data.get("content")
        is_important = data.get("is_important", False)
        send_email = data.get("send_email", False)
        
        if not title or not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Title and content are required"
            )
        
        announcement_data = {
            "title": title,
            "content": content,
            "is_important": is_important,
            "send_email": send_email
        }
        
        announcement = await service.create_announcement(
            course_id, 
            instructor["id"], 
            announcement_data
        )
        
        if not announcement:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create announcement"
            )
        
        return announcement
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating announcement: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating announcement: {str(e)}"
        )

@router.get("/courses/{course_id}/announcements")
async def get_announcements(
    course_id: str,
    service: CourseManagementService = Depends(get_management_service),
    instructor: dict = Depends(get_current_instructor)
) -> Any:
    """
    Get all announcements for a course
    """
    try:
        announcements = await service.get_announcements(course_id)
        return announcements
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting announcements: {str(e)}"
        )

@router.put("/courses/announcements/{announcement_id}")
async def update_announcement(
    announcement_id: str,
    request: Request,
    service: CourseManagementService = Depends(get_management_service),
    instructor: dict = Depends(get_current_instructor)
) -> Any:
    """
    Update an announcement
    """
    try:
        data = await request.json()
        
        # Get existing announcement to verify ownership
        existing = service.supabase.table("announcements")\
            .select("instructor_id")\
            .eq("id", announcement_id)\
            .execute()
        
        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Announcement not found"
            )
        
        if existing.data[0]["instructor_id"] != instructor["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this announcement"
            )
        
        update_data = {
            "title": data.get("title"),
            "content": data.get("content"),
            "is_important": data.get("is_important", False),
            "updated_at": "now()"
        }
        
        # Remove None values
        update_data = {k: v for k, v in update_data.items() if v is not None}
        
        result = service.supabase.table("announcements")\
            .update(update_data)\
            .eq("id", announcement_id)\
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Announcement not found"
            )
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating announcement: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating announcement: {str(e)}"
        )

@router.delete("/courses/announcements/{announcement_id}")
async def delete_announcement(
    announcement_id: str,
    service: CourseManagementService = Depends(get_management_service),
    instructor: dict = Depends(get_current_instructor)
) -> Any:
    """
    Delete an announcement
    """
    try:
        # Get announcement to verify ownership
        existing = service.supabase.table("announcements")\
            .select("instructor_id")\
            .eq("id", announcement_id)\
            .execute()
        
        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Announcement not found"
            )
        
        if existing.data[0]["instructor_id"] != instructor["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this announcement"
            )
        
        result = service.supabase.table("announcements")\
            .delete()\
            .eq("id", announcement_id)\
            .execute()
        
        return {"message": "Announcement deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting announcement: {str(e)}"
        )

# ==================== COURSE MANAGEMENT PAGE ====================

@router.get("/courses/{course_id}/manage")
async def get_course_management_data(
    course_id: str,
    service: CourseManagementService = Depends(get_management_service),
    instructor: dict = Depends(get_current_instructor)
) -> Any:
    """
    Get all data needed for course management page
    """
    try:
        # Get course details
        course = service.supabase.table("courses")\
            .select("*")\
            .eq("id", course_id)\
            .execute()
        
        if not course.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        # Verify ownership
        if course.data[0]["instructor_id"] != instructor["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized"
            )
        
        # Get materials
        materials = await service.get_materials(course_id)
        
        # Get quizzes (with question counts)
        quizzes = service.supabase.table("quizzes")\
            .select("*")\
            .eq("course_id", course_id)\
            .execute()
        
        for quiz in quizzes.data:
            questions = service.supabase.table("quiz_questions")\
                .select("id", count="exact")\
                .eq("quiz_id", quiz["id"])\
                .execute()
            quiz["questions_count"] = questions.count if hasattr(questions, 'count') else 0
        
        # Get assignments (with submission counts)
        assignments = service.supabase.table("assignments")\
            .select("*")\
            .eq("course_id", course_id)\
            .execute()
        
        for assignment in assignments.data:
            submissions = service.supabase.table("submissions")\
                .select("id", count="exact")\
                .eq("assignment_id", assignment["id"])\
                .execute()
            assignment["submissions_count"] = submissions.count if hasattr(submissions, 'count') else 0
        
        # Get announcements
        announcements = await service.get_announcements(course_id)
        
        # Get enrolled students with progress
        students = service.supabase.table("enrollments")\
            .select("*, users(id, email, full_name, avatar_url)")\
            .eq("course_id", course_id)\
            .execute()
        
        enrolled_students = []
        for enrollment in students.data:
            if enrollment.get("users"):
                student = enrollment["users"]
                student["enrolled_at"] = enrollment["enrolled_at"]
                student["progress"] = enrollment["progress"]
                enrolled_students.append(student)
        
        return {
            "course": course.data[0],
            "materials": materials,
            "quizzes": quizzes.data,
            "assignments": assignments.data,
            "announcements": announcements,
            "students": enrolled_students
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting course data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting course data: {str(e)}"
        )