from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File, Form, Query
from app.core.supabase_client import get_supabase
from app.api.api_v1.dependencies import get_current_user, get_current_admin_or_instructor
import logging
import os
import mimetypes

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/tutorials")
async def get_tutorials(
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    topic: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    supabase=Depends(get_supabase)
) -> Any:
    """
    Get all tutorials with optional filters
    """
    try:
        # Start building query
        query = supabase.table("tutorials")\
            .select("*, users(full_name, avatar_url)", count="exact")\
            .eq("is_published", True)
        
        # Apply filters
        if category and category != 'all':
            query = query.eq("category", category)
        
        if difficulty:
            query = query.eq("difficulty", difficulty)
        
        if topic:
            query = query.eq("topic", topic)
        
        # Handle search - search in title and description
        if search:
            search_term = search.strip()
            # Use ilike for case-insensitive search
            query = query.or_(f"title.ilike.%{search_term}%,description.ilike.%{search_term}%")
        
        # Get total count before pagination
        count_result = query.execute()
        total = count_result.count if hasattr(count_result, 'count') else len(count_result.data or [])
        
        # Apply sorting and pagination
        result = query.order("created_at", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()
        
        print(f"Search query: '{search}', Found: {len(result.data)} tutorials")  # Debug log
        
        return {
            "tutorials": result.data,
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        print(f"Error getting tutorials: {e}")
        return {"tutorials": [], "total": 0, "limit": limit, "offset": offset}

@router.get("/tutorials/featured")
async def get_featured_tutorial(
    supabase=Depends(get_supabase)
) -> Any:
    """
    Get featured tutorial (most recent with highest views)
    """
    try:
        result = supabase.table("tutorials")\
            .select("*")\
            .eq("is_published", True)\
            .order("view_count", desc=True)\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        
        return result.data[0] if result.data else None
        
    except Exception as e:
        logger.error(f"Error getting featured tutorial: {e}")
        return None

@router.get("/tutorials/stats")
async def get_tutorial_stats(
    supabase=Depends(get_supabase)
) -> Any:
    """
    Get tutorial statistics by difficulty
    """
    try:
        # Get counts by difficulty
        beginner = supabase.table("tutorials")\
            .select("*", count="exact")\
            .eq("is_published", True)\
            .eq("difficulty", "beginner")\
            .execute()
        
        intermediate = supabase.table("tutorials")\
            .select("*", count="exact")\
            .eq("is_published", True)\
            .eq("difficulty", "intermediate")\
            .execute()
        
        advanced = supabase.table("tutorials")\
            .select("*", count="exact")\
            .eq("is_published", True)\
            .eq("difficulty", "advanced")\
            .execute()
        
        return {
            "beginner": beginner.count if hasattr(beginner, 'count') else 0,
            "intermediate": intermediate.count if hasattr(intermediate, 'count') else 0,
            "advanced": advanced.count if hasattr(advanced, 'count') else 0,
            "total": (beginner.count if hasattr(beginner, 'count') else 0) + 
                     (intermediate.count if hasattr(intermediate, 'count') else 0) + 
                     (advanced.count if hasattr(advanced, 'count') else 0)
        }
        
    except Exception as e:
        logger.error(f"Error getting tutorial stats: {e}")
        return {"beginner": 0, "intermediate": 0, "advanced": 0, "total": 0}

@router.post("/tutorials")
async def create_tutorial(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    category: str = Form(...),
    difficulty: str = Form(...),
    topic: str = Form(...),
    duration: int = Form(0),
    file: Optional[UploadFile] = File(None),
    video_url: Optional[str] = Form(None),
    thumbnail: Optional[UploadFile] = File(None),
    supabase=Depends(get_supabase),
    current_user: dict = Depends(get_current_admin_or_instructor)
) -> Any:
    """
    Upload a new tutorial (admin/instructor only)
    """
    try:
        print(f"Creating tutorial: {title}, Category: {category}, Difficulty: {difficulty}")
        
        tutorial_data = {
            "title": title,
            "description": description,
            "category": category,
            "difficulty": difficulty,
            "topic": topic,
            "duration": duration,
            "uploaded_by": current_user["id"],
            "view_count": 0,
            "is_published": True
        }
        
        # Handle file upload
        if file and file.filename:
            # Validate file type
            if not file.content_type or not file.content_type.startswith(('video/', 'application/', 'text/')):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File type not allowed: {file.content_type}"
                )
            
            # Read file content
            file_content = await file.read()
            file_size = len(file_content)
            
            # Generate unique filename
            import uuid
            file_extension = os.path.splitext(file.filename)[1].lower()
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            file_path = f"tutorials/{unique_filename}"
            
            print(f"Uploading file: {file.filename}, Size: {file_size} bytes")
            
            # Upload to storage using service client
            from app.core.supabase_client import supabase as supabase_client
            service_client = supabase_client.get_service_client()
            storage = service_client.storage.from_("tutorials")
            
            storage.upload(file_path, file_content, {"content-type": file.content_type})
            
            # Get public URL
            tutorial_data["file_url"] = storage.get_public_url(file_path)
            tutorial_data["file_name"] = file.filename
            tutorial_data["file_size"] = file_size
        
        # Handle video URL
        if video_url:
            tutorial_data["video_url"] = video_url
        
        # Handle thumbnail
        if thumbnail and thumbnail.filename:
            thumbnail_content = await thumbnail.read()
            thumbnail_ext = os.path.splitext(thumbnail.filename)[1].lower()
            thumbnail_filename = f"thumbnails/{uuid.uuid4()}{thumbnail_ext}"
            
            from app.core.supabase_client import supabase as supabase_client
            service_client = supabase_client.get_service_client()
            storage = service_client.storage.from_("tutorials")
            
            storage.upload(thumbnail_filename, thumbnail_content, {"content-type": thumbnail.content_type})
            tutorial_data["thumbnail_url"] = storage.get_public_url(thumbnail_filename)
        
        # Insert tutorial
        result = supabase.table("tutorials").insert(tutorial_data).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create tutorial"
            )
        
        print(f"Tutorial created successfully: {result.data[0]['id']}")
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating tutorial: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating tutorial: {str(e)}"
        )

@router.get("/tutorials/{tutorial_id}")
async def get_tutorial(
    tutorial_id: str,
    supabase=Depends(get_supabase)
) -> Any:
    """
    Get a single tutorial by ID
    """
    try:
        # Increment view count
        supabase.table("tutorials")\
            .update({"view_count": supabase.raw("view_count + 1")})\
            .eq("id", tutorial_id)\
            .execute()
        
        # Get tutorial
        result = supabase.table("tutorials")\
            .select("*, users(full_name, avatar_url, bio)")\
            .eq("id", tutorial_id)\
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tutorial not found"
            )
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tutorial: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting tutorial: {str(e)}"
        )

@router.put("/tutorials/{tutorial_id}")
async def update_tutorial(
    tutorial_id: str,
    request: Request,
    supabase=Depends(get_supabase),
    current_user: dict = Depends(get_current_admin_or_instructor)
) -> Any:
    """
    Update a tutorial (admin/instructor only)
    """
    try:
        data = await request.json()
        data["updated_at"] = "now()"
        
        result = supabase.table("tutorials")\
            .update(data)\
            .eq("id", tutorial_id)\
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tutorial not found"
            )
        
        return result.data[0]
        
    except Exception as e:
        logger.error(f"Error updating tutorial: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating tutorial: {str(e)}"
        )

@router.delete("/tutorials/{tutorial_id}")
async def delete_tutorial(
    tutorial_id: str,
    supabase=Depends(get_supabase),
    current_user: dict = Depends(get_current_admin_or_instructor)
) -> Any:
    """
    Delete a tutorial (admin/instructor only)
    """
    try:
        # Get tutorial to get file paths
        tutorial = supabase.table("tutorials")\
            .select("file_url, thumbnail_url")\
            .eq("id", tutorial_id)\
            .execute()
        
        if tutorial.data:
            # Delete files from storage
            from app.core.supabase_client import supabase as supabase_client
            service_client = supabase_client.get_service_client()
            storage = service_client.storage.from_("tutorials")
            
            # Delete main file
            if tutorial.data[0].get("file_url"):
                file_path = tutorial.data[0]["file_url"].split("/storage/v1/object/public/tutorials/")[-1]
                storage.remove([file_path])
            
            # Delete thumbnail
            if tutorial.data[0].get("thumbnail_url"):
                thumb_path = tutorial.data[0]["thumbnail_url"].split("/storage/v1/object/public/tutorials/")[-1]
                storage.remove([thumb_path])
        
        # Delete from database
        result = supabase.table("tutorials")\
            .delete()\
            .eq("id", tutorial_id)\
            .execute()
        
        return {"message": "Tutorial deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting tutorial: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting tutorial: {str(e)}"
        )