from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, logger, status, UploadFile, File
from app.core.supabase_client import get_supabase
from app.services.course_service import CourseService
from app.schemas.course import Course, CourseCreate, CourseUpdate
from app.api.api_v1.dependencies import get_current_user

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
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Retrieve courses with optional filters.
    """
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
            .select("id, email, full_name, username")\
            .eq("id", course["instructor_id"])\
            .execute()
        if instructor.data:
            course["instructor"] = instructor.data[0]
    
    return courses

# @router.post("/", response_model=Course)
# async def create_course(
#     *,
#     course_service: CourseService = Depends(get_course_service),
#     course_in: CourseCreate,
#     current_user: dict = Depends(get_current_user)
# ) -> Any:
#     """
#     Create new course.
#     """
#     if not current_user.get("is_instructor"):
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Only instructors can create courses"
#         )
    
#     course_data = course_in.dict()
#     course_data["instructor_id"] = current_user["id"]
    
#     course = await course_service.create_course(course_data)
#     if not course:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Course creation failed"
#         )
    
#     return course


@router.post("/", response_model=Course)
async def create_course(
    request: Request,
    course_in: CourseCreate,
    course_service: CourseService = Depends(get_course_service),
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Create new course.
    """
    try:
        # Log the request
        logger.info(f"Create course request from user: {current_user.get('id')}")
        logger.info(f"Course data: {course_in.dict()}")
        
        # Check if user is instructor
        if not current_user.get("is_instructor"):
            logger.warning(f"User {current_user.get('id')} is not an instructor")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only instructors can create courses"
            )
        
        # Prepare course data
        course_data = course_in.dict()
        course_data["instructor_id"] = current_user["id"]
        
        # Create course
        logger.info(f"Creating course with data: {course_data}")
        course = await course_service.create_course(course_data)
        
        if not course:
            logger.error("Course creation failed - no data returned")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Course creation failed"
            )
        
        logger.info(f"Course created successfully: {course.get('id')}")
        return course
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating course: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/{course_id}", response_model=Course)
async def get_course(
    *,
    course_service: CourseService = Depends(get_course_service),
    course_id: str
) -> Any:
    """
    Get course by ID with all details.
    """
    course = await course_service.get_course_with_details(course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    return course

@router.put("/{course_id}", response_model=Course)
async def update_course(
    *,
    course_service: CourseService = Depends(get_course_service),
    course_id: str,
    course_in: CourseUpdate,
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Update a course.
    """
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

@router.delete("/{course_id}")
async def delete_course(
    *,
    course_service: CourseService = Depends(get_course_service),
    course_id: str,
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Delete a course.
    """
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

@router.post("/{course_id}/publish")
async def publish_course(
    *,
    course_service: CourseService = Depends(get_course_service),
    course_id: str,
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Publish a course.
    """
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

@router.post("/{course_id}/unpublish")
async def unpublish_course(
    *,
    course_service: CourseService = Depends(get_course_service),
    course_id: str,
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Unpublish a course.
    """
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