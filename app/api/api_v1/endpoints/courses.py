from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from app.core.supabase_client import get_supabase
from app.services.course_service import CourseService
from app.schemas.course import Course, CourseCreate, CourseUpdate
from app.api.api_v1.dependencies import get_current_user, get_current_instructor
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

async def get_course_service(supabase=Depends(get_supabase)) -> CourseService:
    return CourseService(supabase)

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

@router.post("/", response_model=Course)
async def create_course(
    *,
    course_service: CourseService = Depends(get_course_service),
    course_in: CourseCreate,
    current_user: dict = Depends(get_current_instructor)  # Requires instructor
) -> Any:
    """
    Create new course (instructors only).
    """
    try:
        course_data = course_in.dict()
        course_data["instructor_id"] = current_user["id"]
        
        course = await course_service.create_course(course_data)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Course creation failed"
            )
        
        return course
        
    except HTTPException:
        raise
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