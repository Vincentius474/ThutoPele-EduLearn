from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from app.core.supabase_client import get_supabase
from app.api.api_v1.dependencies import get_current_user, get_current_admin_or_instructor
import logging
import re

logger = logging.getLogger(__name__)
router = APIRouter()

def generate_slug(title: str) -> str:
    """Generate a URL-friendly slug from a title"""
    # Convert to lowercase and replace spaces with hyphens
    slug = title.lower().strip()
    # Remove special characters
    slug = re.sub(r'[^\w\s-]', '', slug)
    # Replace spaces with hyphens
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug

@router.get("/blog")
async def get_blog_posts(
    category: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(9, ge=1, le=50),
    supabase=Depends(get_supabase)
) -> Any:
    """
    Get all published blog posts with pagination
    """
    try:
        offset = (page - 1) * limit
        
        # Start building query
        query = supabase.table("blog_posts")\
            .select("*, users(full_name, avatar_url)", count="exact")\
            .eq("is_published", True)
        
        # Apply category filter
        if category:
            query = query.eq("category", category)
        
        # Apply search filter
        if search:
            search_term = search.strip()
            query = query.or_(f"title.ilike.%{search_term}%,excerpt.ilike.%{search_term}%")
        
        # Get total count
        count_result = query.execute()
        total = count_result.count if hasattr(count_result, 'count') else 0
        
        # Apply sorting and pagination
        result = query.order("published_at", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()
        
        return {
            "posts": result.data,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit if total > 0 else 1
        }
        
    except Exception as e:
        logger.error(f"Error getting blog posts: {e}")
        return {"posts": [], "total": 0, "page": page, "limit": limit, "total_pages": 1}

@router.get("/blog/featured")
async def get_featured_post(
    supabase=Depends(get_supabase)
) -> Any:
    """
    Get featured blog post
    """
    try:
        result = supabase.table("blog_posts")\
            .select("*, users(full_name, avatar_url)")\
            .eq("is_published", True)\
            .eq("is_featured", True)\
            .order("published_at", desc=True)\
            .limit(1)\
            .execute()
        
        return result.data[0] if result.data else None
        
    except Exception as e:
        logger.error(f"Error getting featured post: {e}")
        return None

@router.get("/blog/{slug}")
async def get_blog_post(
    slug: str,
    supabase=Depends(get_supabase)
) -> Any:
    """
    Get a single blog post by slug
    """
    try:
        # Increment view count
        supabase.table("blog_posts")\
            .update({"view_count": supabase.raw("view_count + 1")})\
            .eq("slug", slug)\
            .execute()
        
        # Get post
        result = supabase.table("blog_posts")\
            .select("*, users(full_name, avatar_url)")\
            .eq("slug", slug)\
            .eq("is_published", True)\
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Blog post not found"
            )
        
        # Get comments for this post
        comments = supabase.table("blog_comments")\
            .select("*, users(full_name, avatar_url)")\
            .eq("post_id", result.data[0]["id"])\
            .eq("is_approved", True)\
            .order("created_at", desc=True)\
            .execute()
        
        post = result.data[0]
        post["comments"] = comments.data
        
        return post
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting blog post: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting blog post: {str(e)}"
        )

@router.post("/blog")
async def create_blog_post(
    request: Request,
    supabase=Depends(get_supabase),
    current_user: dict = Depends(get_current_admin_or_instructor)
) -> Any:
    """
    Create a new blog post (admin/instructor only)
    """
    try:
        data = await request.json()
        
        title = data.get("title")
        if not title:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Title is required"
            )
        
        # Generate slug from title
        base_slug = generate_slug(title)
        slug = base_slug
        
        # Check if slug exists and make it unique
        counter = 1
        while True:
            existing = supabase.table("blog_posts")\
                .select("slug")\
                .eq("slug", slug)\
                .execute()
            if not existing.data:
                break
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        post_data = {
            "title": title,
            "slug": slug,
            "excerpt": data.get("excerpt", ""),
            "content": data.get("content", ""),
            "category": data.get("category", "General"),
            "read_time": data.get("read_time", 5),
            "featured_image": data.get("featured_image"),
            "is_published": data.get("is_published", False),
            "is_featured": data.get("is_featured", False),
            "author_id": current_user["id"],
            "published_at": "now()" if data.get("is_published") else None
        }
        
        result = supabase.table("blog_posts").insert(post_data).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create blog post"
            )
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating blog post: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating blog post: {str(e)}"
        )
    
@router.post("/blog/{post_id}/comments")
async def add_comment(
    post_id: str,
    request: Request,
    supabase=Depends(get_supabase),
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Add a comment to a blog post using post ID
    """
    try:
        data = await request.json()
        content = data.get("content")
        
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Comment content is required"
            )
        
        # Check if post exists
        post = supabase.table("blog_posts")\
            .select("id")\
            .eq("id", post_id)\
            .execute()
        
        if not post.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Blog post not found"
            )
        
        comment_data = {
            "post_id": post_id,
            "user_id": current_user["id"],
            "content": content,
            "is_approved": False  # Comments need approval
        }
        
        result = supabase.table("blog_comments").insert(comment_data).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to add comment"
            )
        
        return {
            "message": "Comment submitted for approval",
            "comment": result.data[0]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding comment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding comment: {str(e)}"
        )

# Alternative endpoint that accepts slug (if you prefer)
@router.post("/blog/slug/{slug}/comments")
async def add_comment_by_slug(
    slug: str,
    request: Request,
    supabase=Depends(get_supabase),
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Add a comment to a blog post using slug
    """
    try:
        data = await request.json()
        content = data.get("content")
        
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Comment content is required"
            )
        
        # Get post by slug
        post = supabase.table("blog_posts")\
            .select("id")\
            .eq("slug", slug)\
            .execute()
        
        if not post.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Blog post not found"
            )
        
        post_id = post.data[0]["id"]
        
        comment_data = {
            "post_id": post_id,
            "user_id": current_user["id"],
            "content": content,
            "is_approved": True
        }
        
        result = supabase.table("blog_comments").insert(comment_data).execute()
        
        return {
            "message": "Comment submitted for approval",
            "comment": result.data[0]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding comment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding comment: {str(e)}"
        )
    
@router.get("/blog/debug-user")
async def debug_user(
    supabase=Depends(get_supabase),
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Debug endpoint to check user permissions
    """
    try:
        # Check user from token
        user_check = supabase.table("users")\
            .select("id, email, is_instructor, is_admin")\
            .eq("id", current_user["id"])\
            .execute()
        
        return {
            "user_id": current_user["id"],
            "user_email": current_user["email"],
            "is_instructor_from_token": current_user.get("is_instructor", False),
            "is_admin_from_token": current_user.get("is_admin", False),
            "user_from_db": user_check.data[0] if user_check.data else None,
            "can_create_blog": (
                current_user.get("is_instructor", False) or 
                current_user.get("is_admin", False)
            )
        }
    except Exception as e:
        return {"error": str(e)}
    
# @router.put("/blog/{post_id}")
# async def update_blog_post(
#     post_id: str,
#     request: Request,
#     supabase=Depends(get_supabase),
#     current_user: dict = Depends(get_current_admin_or_instructor)
# ) -> Any:
#     """
#     Update a blog post (admin/instructor only)
#     """
#     try:
#         data = await request.json()
        
#         # Check if post exists
#         existing = supabase.table("blog_posts")\
#             .select("*")\
#             .eq("id", post_id)\
#             .execute()
        
#         if not existing.data:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Blog post not found"
#             )
        
#         title = data.get("title")
#         if not title:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Title is required"
#             )
        
#         # Prepare update data
#         update_data = {
#             "title": title,
#             "excerpt": data.get("excerpt", ""),
#             "content": data.get("content", ""),
#             "category": data.get("category", "General"),
#             "read_time": data.get("read_time", 5),
#             "featured_image": data.get("featured_image"),
#             "is_published": data.get("is_published", False),
#             "is_featured": data.get("is_featured", False),
#             "updated_at": "now()"
#         }
        
#         # If publishing now and it wasn't published before, set published_at
#         if update_data["is_published"] and not existing.data[0].get("is_published"):
#             update_data["published_at"] = "now()"
        
#         # If title changed, update slug
#         if title != existing.data[0]["title"]:
#             base_slug = generate_slug(title)
#             slug = base_slug
            
#             # Check if slug exists and make it unique
#             counter = 1
#             while True:
#                 existing_slug = supabase.table("blog_posts")\
#                     .select("slug")\
#                     .eq("slug", slug)\
#                     .neq("id", post_id)\
#                     .execute()
#                 if not existing_slug.data:
#                     break
#                 slug = f"{base_slug}-{counter}"
#                 counter += 1
            
#             update_data["slug"] = slug
        
#         # Remove None values
#         update_data = {k: v for k, v in update_data.items() if v is not None}
        
#         result = supabase.table("blog_posts")\
#             .update(update_data)\
#             .eq("id", post_id)\
#             .execute()
        
#         if not result.data:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Failed to update blog post"
#             )
        
#         return result.data[0]
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error updating blog post: {e}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Error updating blog post: {str(e)}"
#         )

@router.put("/blog/{post_id}")
async def update_blog_post(
    post_id: str,
    request: Request,
    supabase=Depends(get_supabase),
    current_user: dict = Depends(get_current_admin_or_instructor)
) -> Any:
    """
    Update a blog post (admin/instructor only)
    """
    try:
        # Get the request data
        data = await request.json()
        # print(f"Received update data keys: {list(data.keys())}")
        
        # Check if post exists
        existing = supabase.table("blog_posts")\
            .select("*")\
            .eq("id", post_id)\
            .execute()
        
        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Blog post not found"
            )
        
        existing_post = existing.data[0]
        
        # Build update dictionary directly
        update_dict = {}
        
        # Only add fields that have changed
        if data.get("title") and data["title"] != existing_post.get("title"):
            update_dict["title"] = data["title"]
            # Generate new slug if title changed
            base_slug = generate_slug(data["title"])
            slug = base_slug
            counter = 1
            while True:
                existing_slug = supabase.table("blog_posts")\
                    .select("slug")\
                    .eq("slug", slug)\
                    .neq("id", post_id)\
                    .execute()
                if not existing_slug.data:
                    break
                slug = f"{base_slug}-{counter}"
                counter += 1
            update_dict["slug"] = slug
        
        # Handle excerpt
        if "excerpt" in data:
            update_dict["excerpt"] = data["excerpt"] or ""
        
        # Handle content - this is the main issue
        if "content" in data and data["content"] != existing_post.get("content"):
            # Ensure content is properly encoded as a string
            update_dict["content"] = str(data["content"])
        
        # Handle category
        if data.get("category") and data["category"] != existing_post.get("category"):
            update_dict["category"] = data["category"]
        
        # Handle read_time
        if data.get("read_time") and data["read_time"] != existing_post.get("read_time"):
            update_dict["read_time"] = data["read_time"]
        
        # Handle featured_image
        if "featured_image" in data:
            update_dict["featured_image"] = data["featured_image"] or None
        
        # Handle is_published
        if "is_published" in data and data["is_published"] != existing_post.get("is_published"):
            update_dict["is_published"] = data["is_published"]
            if data["is_published"] and not existing_post.get("is_published"):
                update_dict["published_at"] = "now()"
        
        # Handle is_featured
        if "is_featured" in data and data["is_featured"] != existing_post.get("is_featured"):
            update_dict["is_featured"] = data["is_featured"]
        
        # Always update updated_at
        update_dict["updated_at"] = "now()"
        
        # print(f"Update dictionary: {update_dict}")
        
        # If nothing to update (only updated_at), return existing post
        if len(update_dict) <= 1:
            return existing_post
        
        # Perform the update using a simpler approach
        # Build the update query manually
        for key, value in update_dict.items():
            if key == "updated_at":
                supabase.table("blog_posts")\
                    .update({key: value})\
                    .eq("id", post_id)\
                    .execute()
            else:
                supabase.table("blog_posts")\
                    .update({key: value})\
                    .eq("id", post_id)\
                    .execute()
        
        # Get the updated post
        result = supabase.table("blog_posts")\
            .select("*")\
            .eq("id", post_id)\
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update blog post"
            )
        
        # print(f"Update successful")
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        # print(f"Error updating blog post: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating blog post: {str(e)}"
        )

        
@router.delete("/blog/{post_id}")
async def delete_blog_post(
    post_id: str,
    supabase=Depends(get_supabase),
    current_user: dict = Depends(get_current_admin_or_instructor)
) -> Any:
    """
    Delete a blog post (admin/instructor only)
    """
    try:
        print(f"Attempting to delete post: {post_id}")
        
        # Check if post exists
        existing = supabase.table("blog_posts")\
            .select("id")\
            .eq("id", post_id)\
            .execute()
        
        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Blog post not found"
            )
        
        print(f"Post found, deleting...")
        
        # Delete the post
        result = supabase.table("blog_posts")\
            .delete()\
            .eq("id", post_id)\
            .execute()
        
        print(f"Delete result: {result}")
        
        return {"message": "Blog post deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting blog post: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting blog post: {str(e)}"
        )

@router.get("/blog/{post_id}/edit")
async def get_blog_post_for_edit(
    post_id: str,
    supabase=Depends(get_supabase),
    current_user: dict = Depends(get_current_admin_or_instructor)
) -> Any:
    """
    Get blog post for editing (admin/instructor only)
    """
    try:
        result = supabase.table("blog_posts")\
            .select("*")\
            .eq("id", post_id)\
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Blog post not found"
            )
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting blog post for edit: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting blog post: {str(e)}"
        )
