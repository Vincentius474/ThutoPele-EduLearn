from typing import Any, List, Optional
from app.core.supabase_client import get_supabase
from app.api.api_v1.dependencies import get_current_user, get_current_admin_or_instructor
import logging
import mimetypes
import os
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File, Form, Query


logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/resources")
async def get_resources(
    category: Optional[str] = None,
    supabase=Depends(get_supabase)
) -> Any:
    """
    Get all resources (public)
    """
    try:
        query = supabase.table("resources")\
            .select("*, users(full_name, avatar_url)")\
            .eq("is_published", True)\
            .order("created_at", desc=True)
        
        if category and category != 'all':
            query = query.eq("category", category)
        
        result = query.execute()
        return result.data
        
    except Exception as e:
        logger.error(f"Error getting resources: {e}")
        return []

# @router.get("/resources")
# async def get_resources(
#     category: Optional[str] = None,
#     search: Optional[str] = None,
#     sort_by: str = Query("created_at", regex="^(created_at|download_count|title)$"),
#     sort_direction: str = Query("desc", regex="^(asc|desc)$"),
#     limit: int = Query(50, ge=1, le=100),
#     offset: int = Query(0, ge=0),
#     supabase=Depends(get_supabase)
# ) -> Any:
#     """
#     Get all resources with optional filters and search using database function
#     """
#     try:
#         # If search is provided, use the database function for efficient search
#         if search:
#             # Call the database function
#             result = supabase.rpc(
#                 "search_resources",
#                 {
#                     "search_term": search,
#                     "category_filter": category if category and category != 'all' else None,
#                     "sort_by": sort_by,
#                     "sort_direction": sort_direction
#                 }
#             ).execute()
            
#             all_resources = result.data
#             total = len(all_resources)
            
#             # Apply pagination
#             paginated_resources = all_resources[offset:offset + limit]
            
#             # Get uploader details for each resource
#             for resource in paginated_resources:
#                 if resource.get("uploaded_by"):
#                     uploader = supabase.table("users")\
#                         .select("full_name, avatar_url")\
#                         .eq("id", resource["uploaded_by"])\
#                         .execute()
#                     if uploader.data:
#                         resource["uploader"] = uploader.data[0]
            
#             return {
#                 "resources": paginated_resources,
#                 "total": total,
#                 "limit": limit,
#                 "offset": offset
#             }
        
#         # Regular query without search
#         query = supabase.table("resources")\
#             .select("*", count="exact")\
#             .eq("is_published", True)
        
#         if category and category != 'all':
#             query = query.eq("category", category)
        
#         # Apply sorting
#         query = query.order(sort_by, desc=(sort_direction == "desc"))
        
#         # Get total count
#         count_result = query.execute()
#         total = count_result.count if hasattr(count_result, 'count') else 0
        
#         # Apply pagination
#         result = query.range(offset, offset + limit - 1).execute()
        
#         # Get uploader details
#         for resource in result.data:
#             if resource.get("uploaded_by"):
#                 uploader = supabase.table("users")\
#                     .select("full_name, avatar_url")\
#                     .eq("id", resource["uploaded_by"])\
#                     .execute()
#                 if uploader.data:
#                     resource["uploader"] = uploader.data[0]
        
#         return {
#             "resources": result.data,
#             "total": total,
#             "limit": limit,
#             "offset": offset
#         }
        
#     except Exception as e:
#         logger.error(f"Error getting resources: {e}")
#         import traceback
#         traceback.print_exc()
#         return {"resources": [], "total": 0, "limit": limit, "offset": offset}


# @router.get("/resources/popular")
# async def get_popular_resources(
#     limit: int = 4,
#     supabase=Depends(get_supabase)
# ) -> Any:
#     """
#     Get most downloaded resources
#     """
#     try:
#         result = supabase.table("resources")\
#             .select("*")\
#             .eq("is_published", True)\
#             .order("download_count", desc=True)\
#             .limit(limit)\
#             .execute()
        
#         return result.data
        
#     except Exception as e:
#         logger.error(f"Error getting popular resources: {e}")
#         return []

@router.get("/resources/popular")
async def get_popular_resources(
    limit: int = 4,
    supabase=Depends(get_supabase)
) -> Any:
    """
    Get most downloaded resources
    """
    try:
        result = supabase.table("resources")\
            .select("*")\
            .eq("is_published", True)\
            .order("download_count", desc=True)\
            .limit(limit)\
            .execute()
        
        return result.data
        
    except Exception as e:
        logger.error(f"Error getting popular resources: {e}")
        return []

@router.post("/resources")
async def create_resource(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    category: str = Form(...),
    file: UploadFile = File(...),
    supabase=Depends(get_supabase),
    current_user: dict = Depends(get_current_admin_or_instructor)
) -> Any:
    """
    Upload a new resource (admin/instructor only)
    """
    try:
        print(f"Uploading resource: {title}, Category: {category}, File: {file.filename}")
        
        # Validate file type
        if not file.content_type or not file.content_type.startswith(('application/', 'text/', 'image/')):
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
        file_path = f"resources/{unique_filename}"
        
        print(f"File size: {file_size} bytes")
        print(f"Uploading to path: {file_path}")
        
        # Upload to storage using service client
        from app.core.supabase_client import supabase as supabase_client
        service_client = supabase_client.get_service_client()
        storage = service_client.storage.from_("resources")
        
        storage.upload(file_path, file_content, {"content-type": file.content_type})
        
        # Get public URL
        file_url = storage.get_public_url(file_path)
        
        # Create resource record
        resource_data = {
            "title": title,
            "description": description,
            "category": category,
            "file_url": file_url,
            "file_name": file.filename,
            "file_size": file_size,
            "file_type": file.content_type,
            "uploaded_by": current_user["id"],
            "download_count": 0,
            "is_published": True
        }
        
        result = supabase.table("resources").insert(resource_data).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create resource record"
            )
        
        print(f"Resource created successfully: {result.data[0]['id']}")
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating resource: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating resource: {str(e)}"
        )

@router.post("/resources/{resource_id}/download")
async def download_resource(
    resource_id: str,
    supabase=Depends(get_supabase)
) -> Any:
    """
    Increment download count and return file URL
    """
    try:
        # Get resource
        resource = supabase.table("resources")\
            .select("*")\
            .eq("id", resource_id)\
            .execute()
        
        if not resource.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resource not found"
            )
        
        # Increment download count
        supabase.table("resources")\
            .update({"download_count": resource.data[0]["download_count"] + 1})\
            .eq("id", resource_id)\
            .execute()
        
        return {"file_url": resource.data[0]["file_url"]}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading resource: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error downloading resource: {str(e)}"
        )

@router.delete("/resources/{resource_id}")
async def delete_resource(
    resource_id: str,
    supabase=Depends(get_supabase),
    current_user: dict = Depends(get_current_admin_or_instructor)
) -> Any:
    """
    Delete a resource (admin/instructor only)
    """
    try:
        # Get resource to get file path
        resource = supabase.table("resources")\
            .select("*")\
            .eq("id", resource_id)\
            .execute()
        
        if not resource.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resource not found"
            )
        
        # Extract file path from URL
        file_url = resource.data[0]["file_url"]
        file_path = file_url.split("/storage/v1/object/public/resources/")[-1]
        
        # Delete from storage
        from app.core.supabase_client import supabase as supabase_client
        service_client = supabase_client.get_service_client()
        storage = service_client.storage.from_("resources")
        storage.remove([file_path])
        
        # Delete from database
        result = supabase.table("resources")\
            .delete()\
            .eq("id", resource_id)\
            .execute()
        
        return {"message": "Resource deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting resource: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting resource: {str(e)}"
        )