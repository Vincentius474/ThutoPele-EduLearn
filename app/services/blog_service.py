from typing import Optional, List, Dict, Any
from supabase import Client
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class BlogService:
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
    
    async def get_posts(
        self,
        category: Optional[str] = None,
        featured_only: bool = False,
        limit: int = 10,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get blog posts with optional filters"""
        try:
            query = self.supabase.table("blog_posts")\
                .select("*")\
                .eq("is_published", True)
            
            if category:
                query = query.eq("category", category)
            
            if featured_only:
                query = query.eq("is_featured", True)
            
            # Order by published date (newest first)
            query = query.order("published_at", desc=True)
            
            # Apply pagination
            result = query.range(offset, offset + limit - 1).execute()
            
            # Get author details for each post
            posts = result.data if result.data else []
            for post in posts:
                if post.get("author_id"):
                    author = self.supabase.table("users")\
                        .select("id, full_name, email, avatar_url, bio")\
                        .eq("id", post["author_id"])\
                        .execute()
                    if author.data:
                        post["author"] = author.data[0]
            
            return posts
            
        except Exception as e:
            logger.error(f"Error getting blog posts: {e}")
            return []
    
    async def get_post_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        """Get a single blog post by slug"""
        try:
            result = self.supabase.table("blog_posts")\
                .select("*")\
                .eq("slug", slug)\
                .eq("is_published", True)\
                .execute()
            
            if result.data and len(result.data) > 0:
                post = result.data[0]
                
                # Get author details
                if post.get("author_id"):
                    author = self.supabase.table("users")\
                        .select("id, full_name, email, avatar_url, bio")\
                        .eq("id", post["author_id"])\
                        .execute()
                    if author.data:
                        post["author"] = author.data[0]
                
                # Get comments
                comments = self.supabase.table("blog_comments")\
                    .select("*, users(full_name, avatar_url)")\
                    .eq("post_id", post["id"])\
                    .eq("is_approved", True)\
                    .order("created_at", desc=True)\
                    .execute()
                
                post["comments"] = comments.data if comments.data else []
                
                # Increment view count
                self.supabase.table("blog_posts")\
                    .update({"views": post.get("views", 0) + 1})\
                    .eq("id", post["id"])\
                    .execute()
                
                return post
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting blog post {slug}: {e}")
            return None
    
    async def get_categories(self) -> List[Dict[str, Any]]:
        """Get all categories with post counts"""
        try:
            result = self.supabase.table("blog_posts")\
                .select("category", count="exact")\
                .eq("is_published", True)\
                .execute()
            
            # Count posts per category
            categories = {}
            for post in result.data:
                cat = post.get("category")
                if cat:
                    categories[cat] = categories.get(cat, 0) + 1
            
            # Format as list
            category_list = [
                {"name": name, "count": count}
                for name, count in categories.items()
            ]
            
            return sorted(category_list, key=lambda x: x["name"])
            
        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            return []
    
    async def get_recent_posts(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent blog posts"""
        return await self.get_posts(limit=limit)
    
    async def get_featured_posts(self, limit: int = 3) -> List[Dict[str, Any]]:
        """Get featured blog posts"""
        return await self.get_posts(featured_only=True, limit=limit)
    
    async def search_posts(self, query: str) -> List[Dict[str, Any]]:
        """Search blog posts"""
        try:
            # This is a simple search - consider using PostgreSQL full-text search for production
            result = self.supabase.table("blog_posts")\
                .select("*")\
                .eq("is_published", True)\
                .execute()
            
            posts = result.data if result.data else []
            
            # Filter posts containing the search query
            query_lower = query.lower()
            filtered = [
                post for post in posts
                if query_lower in post.get("title", "").lower() or
                   query_lower in post.get("excerpt", "").lower() or
                   query_lower in post.get("content", "").lower()
            ]
            
            return filtered[:10]  # Limit results
            
        except Exception as e:
            logger.error(f"Error searching posts: {e}")
            return []