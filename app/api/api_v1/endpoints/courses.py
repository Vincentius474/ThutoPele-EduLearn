from datetime import datetime
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

@router.post("/", response_model=Course)
async def create_course(
    request: Request,
    course_service: CourseService = Depends(get_course_service),
    current_user: dict = Depends(get_current_instructor)
) -> Any:
    """
    Create new course with optional thumbnail
    """
    try:
        # Log user info for debugging
        print(f"Creating course for instructor: {current_user['id']}")
        print(f"Is instructor: {current_user.get('is_instructor')}")
        
        # Parse form data
        form = await request.form()
        print(f"Received form data keys: {list(form.keys())}")
        
        # Handle price conversion safely
        price_str = form.get("price", "0")
        try:
            price = int(float(price_str))
        except (ValueError, TypeError):
            price = 0
        
        # Prepare course data
        course_data = {
            "title": form.get("title"),
            "description": form.get("description"),
            "category": form.get("category"),
            "level": form.get("level"),
            "price": price,
            "is_published": form.get("is_published", "false").lower() == "true",
            "instructor_id": current_user["id"]
        }
        
        # Validate required fields
        if not course_data["title"] or not course_data["description"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Title and description are required"
            )
        
        # Create the course
        print(f"Creating course with data: {course_data}")
        course = await course_service.create_course(course_data)
        
        if not course:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create course"
            )
        
        # Handle thumbnail upload after course is created
        thumbnail = form.get("thumbnail")
        
        if thumbnail and hasattr(thumbnail, "filename") and thumbnail.filename:
            try:
                from app.services.storage_service import StorageService
                storage_service = StorageService(course_service.supabase)
                
                print(f"Attempting to upload thumbnail for course: {course['id']}")
                thumbnail_url = await storage_service.upload_course_image(
                    course["id"],
                    thumbnail
                )
                
                if thumbnail_url:
                    print(f"Thumbnail uploaded successfully: {thumbnail_url}")
                    # Update course with thumbnail URL
                    updated_course = await course_service.update_course(
                        course["id"], 
                        {"thumbnail_url": thumbnail_url}
                    )
                    if updated_course:
                        course = updated_course
                        print(f"Course updated with thumbnail")
                else:
                    print("Thumbnail upload failed but course was created")
            except Exception as e:
                print(f"Thumbnail upload failed (non-critical): {e}")
                # Course already created, just log the error
                import traceback
                traceback.print_exc()
        
        return course
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating course: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating course: {str(e)}"
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

# @router.put("/{course_id}", response_model=Course)
# async def update_course(
#     course_id: str,
#     request: Request,
#     course_service: CourseService = Depends(get_course_service),
#     current_user: dict = Depends(get_current_instructor)
# ) -> Any:
#     """
#     Update a course (instructor only - must own the course)
#     """
#     try:
#         # Check if course exists and user owns it
#         course = await course_service.get_course(course_id)
#         if not course:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Course not found"
#             )
        
#         if course["instructor_id"] != current_user["id"]:
#             raise HTTPException(
#                 status_code=status.HTTP_403_FORBIDDEN,
#                 detail="Not authorized to update this course"
#             )
        
#         # Parse form data
#         form = await request.form()
#         print(f"Updating course {course_id} with data keys: {list(form.keys())}")
        
#         # Handle price conversion safely
#         price_str = form.get("price", "0")
#         try:
#             price = int(float(price_str))
#         except (ValueError, TypeError):
#             price = 0
        
#         # Prepare update data
#         update_data = {
#             "title": form.get("title"),
#             "description": form.get("description"),
#             "category": form.get("category"),
#             "level": form.get("level"),
#             "price": price,
#             "is_published": form.get("is_published", "false").lower() == "true",
#             "updated_at": "now()"
#         }
        
#         # Remove None values
#         update_data = {k: v for k, v in update_data.items() if v is not None}
        
#         # Handle thumbnail upload if present
#         thumbnail = form.get("thumbnail")
#         thumbnail_uploaded = False
        
#         if thumbnail and hasattr(thumbnail, "filename") and thumbnail.filename:
#             try:
#                 from app.services.storage_service import StorageService
#                 storage_service = StorageService(course_service.supabase)
                
#                 print(f"Attempting to upload thumbnail: {thumbnail.filename}")
#                 thumbnail_url = await storage_service.upload_course_image(
#                     course_id,
#                     thumbnail
#                 )
                
#                 if thumbnail_url:
#                     update_data["thumbnail_url"] = thumbnail_url
#                     thumbnail_uploaded = True
#                     print(f"New thumbnail uploaded: {thumbnail_url}")
#                 else:
#                     print("Thumbnail upload failed but continuing with course update")
#             except Exception as e:
#                 print(f"Thumbnail upload error (non-critical): {e}")
#                 # Continue with update even if thumbnail fails
        
#         # Update the course
#         print(f"Updating course with data: {update_data}")
#         updated_course = await course_service.update_course(course_id, update_data)
        
#         if not updated_course:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Failed to update course"
#             )
        
#         return updated_course
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         print(f"Error updating course: {e}")
#         import traceback
#         traceback.print_exc()
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Error updating course: {str(e)}"
#         )

@router.put("/{course_id}", response_model=Course)
async def update_course(
    course_id: str,
    request: Request,
    course_service: CourseService = Depends(get_course_service),
    current_user: dict = Depends(get_current_instructor)
) -> Any:
    """
    Update a course (instructor only - must own the course)
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
        
        # Parse form data
        form = await request.form()
        print(f"Updating course {course_id} with data keys: {list(form.keys())}")
        
        # Handle price conversion safely
        price_str = form.get("price", "0")
        try:
            price = int(float(price_str))
        except (ValueError, TypeError):
            price = 0
        
        # Prepare update data
        update_data = {
            "title": form.get("title"),
            "description": form.get("description"),
            "category": form.get("category"),
            "level": form.get("level"),
            "price": price,
            "is_published": form.get("is_published", "false").lower() == "true"
        }
        
        # Remove None values
        update_data = {k: v for k, v in update_data.items() if v is not None}
        
        # Handle thumbnail upload if present
        thumbnail = form.get("thumbnail")
        thumbnail_uploaded = False
        
        if thumbnail and hasattr(thumbnail, "filename") and thumbnail.filename:
            try:
                from app.services.storage_service import StorageService
                storage_service = StorageService(course_service.supabase)
                
                print(f"Attempting to upload thumbnail: {thumbnail.filename}")
                thumbnail_url = await storage_service.upload_course_image(
                    course_id,
                    thumbnail
                )
                
                if thumbnail_url:
                    update_data["thumbnail_url"] = thumbnail_url
                    thumbnail_uploaded = True
                    print(f"New thumbnail uploaded: {thumbnail_url}")
                else:
                    print("Thumbnail upload failed but continuing with course update")
            except Exception as e:
                print(f"Thumbnail upload error (non-critical): {e}")
                # Continue with update even if thumbnail fails
        
        # Update the course using service role to bypass RLS
        print(f"Updating course with data: {update_data}")
        
        # Try regular update first, fall back to service role if needed
        updated_course = await course_service.update_course(course_id, update_data)
        
        if not updated_course:
            print("Regular update failed, trying with service role")
            updated_course = await course_service.update_course_with_service_role(course_id, update_data)
        
        if not updated_course:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update course"
            )
        
        return updated_course
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating course: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating course: {str(e)}"
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
    
# @router.post("/{course_id}/enroll")
# async def enroll_in_course(
#     course_id: str,
#     supabase=Depends(get_supabase),
#     current_user: dict = Depends(get_current_active_user)
# ) -> Any:
#     """
#     Enroll a student in a course
#     """
#     try:
#         # Check if course exists and is published
#         course = supabase.table("courses")\
#             .select("*")\
#             .eq("id", course_id)\
#             .eq("is_published", True)\
#             .execute()
        
#         if not course.data:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Course not found or not published"
#             )
        
#         # Check if already enrolled
#         existing = supabase.table("enrollments")\
#             .select("*")\
#             .eq("user_id", current_user["id"])\
#             .eq("course_id", course_id)\
#             .execute()
        
#         if existing.data:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Already enrolled in this course"
#             )
        
#         # Create enrollment
#         enrollment_data = {
#             "user_id": current_user["id"],
#             "course_id": course_id,
#             "progress": 0,
#             "enrolled_at": "now()"
#         }
        
#         result = supabase.table("enrollments").insert(enrollment_data).execute()
        
#         if not result.data:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Failed to enroll"
#             )
        
#         return {"message": "Successfully enrolled in course"}
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Error enrolling in course: {str(e)}"
#         )

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
            "enrolled_at": datetime.now().isoformat()
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
        print(f"Error enrolling in course: {e}")
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

@router.get("/test-permissions")
async def test_permissions(
    supabase=Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
) -> Any:
    """
    Test endpoint to check user permissions
    """
    try:
        # Check if user is instructor in database
        user_check = supabase.table("users")\
            .select("is_instructor, is_admin")\
            .eq("id", current_user["id"])\
            .execute()
        
        return {
            "user_id": current_user["id"],
            "email": current_user["email"],
            "is_instructor_from_token": current_user.get("is_instructor", False),
            "is_instructor_from_db": user_check.data[0]["is_instructor"] if user_check.data else False,
            "is_admin_from_token": current_user.get("is_admin", False),
            "is_admin_from_db": user_check.data[0]["is_admin"] if user_check.data else False,
            "can_create_course": user_check.data[0]["is_instructor"] if user_check.data else False
        }
    except Exception as e:
        return {"error": str(e)}

@router.get("/debug-auth")
async def debug_auth(
    request: Request,
    supabase=Depends(get_supabase)
) -> Any:
    """Debug endpoint to check authentication"""
    try:
        # Get token from cookie
        token = request.cookies.get("access_token")
        
        if not token:
            return {"error": "No token found"}
        
        # Get user from token
        user = supabase.auth.get_user(token)
        
        if not user:
            return {"error": "Invalid token"}
        
        # Get user from database
        db_user = supabase.table("users")\
            .select("*")\
            .eq("id", user.user.id)\
            .execute()
        
        return {
            "token_valid": True,
            "user_id": user.user.id,
            "user_email": user.user.email,
            "user_metadata": user.user.user_metadata,
            "db_user": db_user.data[0] if db_user.data else None,
            "token": token[:20] + "..."  # Show first 20 chars only
        }
    except Exception as e:
        return {"error": str(e)}

