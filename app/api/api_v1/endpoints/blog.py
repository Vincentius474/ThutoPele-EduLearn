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