from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status, UploadFile, File
from app.core.supabase_client import get_supabase
from app.services.course_service import CourseService
from app.schemas.course import Course, CourseCreate, CourseUpdate
from app.api.api_v1.dependencies import get_current_active_user, get_current_user, get_current_instructor
import logging

from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)
router = APIRouter()

async def get_course_service(supabase=Depends(get_supabase)) -> CourseService:
    return CourseService(supabase)

async def get_storage_service(supabase=Depends(get_supabase)):
    from app.services.storage_service import StorageService
    return StorageService(supabase)

@router.get("/", response_model=List[Course])
async def get_courses(
    *,
    course_service: CourseService = Depends(get_course_service),
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    level: Optional[str] = None,
    current_user: Optional[dict] = Depends(get_current_user)  # Optional - can be None
) -> Any:
    """
    Retrieve courses with optional filters.
    """
    try:
        # If user is instructor, show all courses, otherwise only published
        is_published = None
        if not current_user or not current_user.get("is_instructor"):
            is_published = True
        
        courses = await course_service.get_courses(
            skip=skip,
            limit=limit,
            category=category,
            level=level,
            is_published=is_published
        )
        
        # Get instructor details for each course
        for course in courses:
            supabase = course_service.supabase
            instructor = supabase.table("users")\
                .select("id, email, full_name, username, avatar_url")\
                .eq("id", course["instructor_id"])\
                .execute()
            if instructor.data:
                course["instructor"] = instructor.data[0]
            else:
                course["instructor"] = {
                    "full_name": "Unknown Instructor",
                    "avatar_url": None
                }
        
        return courses
        
    except Exception as e:
        logger.error(f"Error getting courses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving courses"
        )

# @router.post("/", response_model=Course)
# async def create_course(
#     *,
#     course_service: CourseService = Depends(get_course_service),
#     course_in: CourseCreate,
#     current_user: dict = Depends(get_current_instructor)  # Requires instructor
# ) -> Any:
#     """
#     Create new course (instructors only).
#     """
#     try:
#         course_data = course_in.dict()
#         course_data["instructor_id"] = current_user["id"]
        
#         course = await course_service.create_course(course_data)
#         if not course:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Course creation failed"
#             )
        
#         return course
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error creating course: {e}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Error creating course"
#         )

@router.post("/", response_model=Course)
async def create_course(
    request: Request,
    course_service: CourseService = Depends(get_course_service),
    storage_service: StorageService = Depends(get_storage_service),
    current_user: dict = Depends(get_current_instructor)
) -> Any:
    """
    Create new course with optional thumbnail
    """
    try:
        form = await request.form()
        course_data = {
            "title": form.get("title"),
            "description": form.get("description"),
            "category": form.get("category"),
            "level": form.get("level"),
            "price": float(form.get("price", 0)),
            "is_published": form.get("is_published", "false").lower() == "true",
            "instructor_id": current_user["id"]
        }
        
        # Handle thumbnail upload
        thumbnail = form.get("thumbnail")
        if thumbnail and hasattr(thumbnail, "filename") and thumbnail.filename:
            thumbnail_url = await storage_service.upload_course_image(
                "temp",  # We don't have course_id yet
                thumbnail
            )
            if thumbnail_url:
                course_data["thumbnail_url"] = thumbnail_url
        
        course = await course_service.create_course(course_data)
        
        # If we have a thumbnail uploaded before course creation, move it to correct folder
        if thumbnail_url and course:
            # Move file to correct course folder (you'd need to implement this)
            pass
        
        return course
        
    except Exception as e:
        logger.error(f"Error creating course: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating course"
        )


@router.get("/{course_id}", response_model=Course)
async def get_course(
    *,
    course_service: CourseService = Depends(get_course_service),
    course_id: str,
    current_user: Optional[dict] = Depends(get_current_user)  # Optional
) -> Any:
    """
    Get course by ID with all details.
    """
    try:
        course = await course_service.get_course_with_details(course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        return course
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting course {course_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving course"
        )

@router.put("/{course_id}", response_model=Course)
async def update_course(
    *,
    course_service: CourseService = Depends(get_course_service),
    course_id: str,
    course_in: CourseUpdate,
    current_user: dict = Depends(get_current_instructor)  # Requires instructor
) -> Any:
    """
    Update a course (instructor only - must own the course).
    """
    try:
        # Check if course exists and user owns it
        course = await course_service.get_course(course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        if course["instructor_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this course"
            )
        
        # Filter out None values
        update_data = {k: v for k, v in course_in.dict().items() if v is not None}
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No data to update"
            )
        
        updated_course = await course_service.update_course(course_id, update_data)
        return updated_course
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating course {course_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating course"
        )

@router.delete("/{course_id}")
async def delete_course(
    *,
    course_service: CourseService = Depends(get_course_service),
    course_id: str,
    current_user: dict = Depends(get_current_instructor)  # Requires instructor
) -> Any:
    """
    Delete a course (instructor only - must own the course).
    """
    try:
        # Check if course exists and user owns it
        course = await course_service.get_course(course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        if course["instructor_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this course"
            )
        
        deleted = await course_service.delete_course(course_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Course deletion failed"
            )
        
        return {"message": "Course deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting course {course_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting course"
        )

@router.post("/{course_id}/publish")
async def publish_course(
    *,
    course_service: CourseService = Depends(get_course_service),
    course_id: str,
    current_user: dict = Depends(get_current_instructor)  # Requires instructor
) -> Any:
    """
    Publish a course (instructor only - must own the course).
    """
    try:
        # Check if course exists and user owns it
        course = await course_service.get_course(course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        if course["instructor_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to publish this course"
            )
        
        updated_course = await course_service.publish_course(course_id)
        return updated_course
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error publishing course {course_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error publishing course"
        )

@router.post("/{course_id}/unpublish")
async def unpublish_course(
    *,
    course_service: CourseService = Depends(get_course_service),
    course_id: str,
    current_user: dict = Depends(get_current_instructor)  # Requires instructor
) -> Any:
    """
    Unpublish a course (instructor only - must own the course).
    """
    try:
        # Check if course exists and user owns it
        course = await course_service.get_course(course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        if course["instructor_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to unpublish this course"
            )
        
        updated_course = await course_service.unpublish_course(course_id)
        return updated_course
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unpublishing course {course_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error unpublishing course"
        )

@router.post("/{course_id}/thumbnail")
async def upload_course_thumbnail(
    *,
    supabase=Depends(get_supabase),
    course_service: CourseService = Depends(get_course_service),
    course_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_instructor)  # Requires instructor
) -> Any:
    """
    Upload course thumbnail to Supabase Storage.
    """
    try:
        # Check if user owns the course
        course = await course_service.get_course(course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        if course["instructor_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this course"
            )
        
        # Upload to Supabase Storage
        file_content = await file.read()
        file_path = f"courses/{course_id}/thumbnail/{file.filename}"
        
        storage = supabase.storage.from_("course-materials")
        result = storage.upload(file_path, file_content)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File upload failed"
            )
        
        # Get public URL
        public_url = storage.get_public_url(file_path)
        
        # Update course with thumbnail URL
        updated_course = await course_service.update_course(course_id, {"thumbnail_url": public_url})
        
        return {"thumbnail_url": public_url, "course": updated_course}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading thumbnail for course {course_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error uploading thumbnail"
        )
    
@router.post("/{course_id}/enroll")
async def enroll_in_course(
    course_id: str,
    supabase=Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
) -> Any:
    """
    Enroll a student in a course
    """
    try:
        # Check if course exists and is published
        course = supabase.table("courses")\
            .select("*")\
            .eq("id", course_id)\
            .eq("is_published", True)\
            .execute()
        
        if not course.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found or not published"
            )
        
        # Check if already enrolled
        existing = supabase.table("enrollments")\
            .select("*")\
            .eq("user_id", current_user["id"])\
            .eq("course_id", course_id)\
            .execute()
        
        if existing.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already enrolled in this course"
            )
        
        # Create enrollment
        enrollment_data = {
            "user_id": current_user["id"],
            "course_id": course_id,
            "progress": 0,
            "enrolled_at": "now()"
        }
        
        result = supabase.table("enrollments").insert(enrollment_data).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to enroll"
            )
        
        return {"message": "Successfully enrolled in course"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error enrolling in course: {str(e)}"
        )

@router.post("/{course_id}/progress/{material_id}")
async def update_progress(
    course_id: str,
    material_id: str,
    supabase=Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
) -> Any:
    """
    Update student progress when they complete a material
    """
    try:
        # Verify enrollment
        enrollment = supabase.table("enrollments")\
            .select("*")\
            .eq("user_id", current_user["id"])\
            .eq("course_id", course_id)\
            .execute()
        
        if not enrollment.data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enrolled in this course"
            )
        
        # Get total materials count
        materials = supabase.table("course_materials")\
            .select("id", count="exact")\
            .eq("course_id", course_id)\
            .execute()
        
        total_materials = materials.count if hasattr(materials, 'count') else 0
        
        if total_materials == 0:
            return {"progress": 0}
        
        # Mark this material as completed for the user
        # You might want a separate table for completed materials
        # For now, we'll just update progress based on completion
        
        # Get completed materials count (simplified - you'd want a proper completion tracking)
        completed = supabase.table("lesson_progress")\
            .select("id", count="exact")\
            .eq("user_id", current_user["id"])\
            .eq("lesson_id", material_id)\
            .execute()
        
        if not completed.data:
            supabase.table("lesson_progress").insert({
                "user_id": current_user["id"],
                "lesson_id": material_id,
                "completed": True,
                "completed_at": "now()"
            }).execute()
        
        # Get updated completed count
        completed_count = supabase.table("lesson_progress")\
            .select("id", count="exact")\
            .eq("user_id", current_user["id"])\
            .execute()
        
        new_progress = int((completed_count.count / total_materials) * 100)
        
        # Update enrollment progress
        supabase.table("enrollments")\
            .update({"progress": new_progress})\
            .eq("user_id", current_user["id"])\
            .eq("course_id", course_id)\
            .execute()
        
        return {
            "progress": new_progress,
            "completed": completed_count.count,
            "total": total_materials
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating progress: {str(e)}"
        )

@router.post("/{course_id}/reviews")
async def add_review(
    course_id: str,
    request: Request,
    supabase=Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
) -> Any:
    """
    Add a review for a course
    """
    try:
        data = await request.json()
        rating = data.get("rating")
        comment = data.get("comment", "")
        
        if not rating or rating < 1 or rating > 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rating must be between 1 and 5"
            )
        
        # Check if enrolled
        enrollment = supabase.table("enrollments")\
            .select("*")\
            .eq("user_id", current_user["id"])\
            .eq("course_id", course_id)\
            .execute()
        
        if not enrollment.data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only enrolled students can review"
            )
        
        # Check if already reviewed
        existing = supabase.table("reviews")\
            .select("*")\
            .eq("user_id", current_user["id"])\
            .eq("course_id", course_id)\
            .execute()
        
        if existing.data:
            # Update existing review
            result = supabase.table("reviews")\
                .update({
                    "rating": rating,
                    "comment": comment,
                    "updated_at": "now()"
                })\
                .eq("id", existing.data[0]["id"])\
                .execute()
        else:
            # Create new review
            result = supabase.table("reviews").insert({
                "user_id": current_user["id"],
                "course_id": course_id,
                "rating": rating,
                "comment": comment
            }).execute()
        
        return {"message": "Review submitted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error submitting review: {str(e)}"
        )

@router.get("/{course_id}/reviews")
async def get_reviews(
    course_id: str,
    supabase=Depends(get_supabase)
) -> Any:
    """
    Get all reviews for a course
    """
    try:
        reviews = supabase.table("reviews")\
            .select("*, users(full_name, avatar_url)")\
            .eq("course_id", course_id)\
            .order("created_at", desc=True)\
            .execute()
        
        return reviews.data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting reviews: {str(e)}"
        )


