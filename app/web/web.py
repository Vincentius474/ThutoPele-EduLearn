from fastapi import APIRouter, Request, Depends, HTTPException, logger
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from app.services.blog_service import BlogService
from app.web.dependencies import (
    get_templates, 
    get_current_user_web,
    get_supabase_client
)
from app.services.course_service import CourseService
from app.services.user_service import UserService

web_router = APIRouter(tags=["web"])

# Home page
@web_router.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: Optional[dict] = Depends(get_current_user_web)
):
    """Home page"""
    supabase = get_supabase_client()
    course_service = CourseService(supabase)
    
    # Get featured courses
    courses = await course_service.get_courses(
        limit=6,
        is_published=True
    )
    
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "current_user": current_user,
            "courses": courses,
            "title": "Home"
        }
    )

# Login page
@web_router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: Optional[dict] = Depends(get_current_user_web)
):
    """Login page"""
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=302)
    
    return templates.TemplateResponse(
        "auth/login.html",
        {
            "request": request,
            "title": "Login"
        }
    )

# Register page
@web_router.get("/register", response_class=HTMLResponse)
async def register_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: Optional[dict] = Depends(get_current_user_web)
):
    """Register page"""
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=302)
    
    return templates.TemplateResponse(
        "auth/register.html",
        {
            "request": request,
            "title": "Register"
        }
    )

# Dashboard
@web_router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: dict = Depends(get_current_user_web)
):
    """User dashboard"""
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    supabase = get_supabase_client()
    user_service = UserService(supabase)
    
    # Get user's enrolled courses
    enrolled_courses = await user_service.get_user_courses(current_user["id"])
    
    # Get user's taught courses if instructor
    taught_courses = []
    if current_user.get("is_instructor"):
        taught_courses = await user_service.get_user_taught_courses(current_user["id"])
    
    return templates.TemplateResponse(
        "dashboard/index.html",
        {
            "request": request,
            "current_user": current_user,
            "enrolled_courses": enrolled_courses,
            "taught_courses": taught_courses,
            "title": "Dashboard"
        }
    )

# Profile page
@web_router.get("/profile", response_class=HTMLResponse)
async def profile_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: dict = Depends(get_current_user_web)
):
    """User profile page"""
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse(
        "dashboard/profile.html",
        {
            "request": request,
            "current_user": current_user,
            "title": "Profile"
        }
    )

# Course detail page
@web_router.get("/courses/{course_id}", response_class=HTMLResponse)
async def course_detail(
    request: Request,
    course_id: str,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: Optional[dict] = Depends(get_current_user_web)
):
    """Course detail page"""
    supabase = get_supabase_client()
    course_service = CourseService(supabase)
    
    course = await course_service.get_course_with_details(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Check if user is enrolled
    is_enrolled = False
    if current_user:
        enrollment = supabase.table("enrollments")\
            .select("*")\
            .eq("user_id", current_user["id"])\
            .eq("course_id", course_id)\
            .execute()
        is_enrolled = len(enrollment.data) > 0
    
    return templates.TemplateResponse(
        "courses/detail.html",
        {
            "request": request,
            "current_user": current_user,
            "course": course,
            "is_enrolled": is_enrolled,
            "title": course["title"]
        }
    )

# Create course page (instructors only)
@web_router.get("/courses/create", response_class=HTMLResponse)
async def create_course_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: dict = Depends(get_current_user_web)
):
    """Create course page"""
    if not current_user or not current_user.get("is_instructor"):
        return RedirectResponse(url="/courses", status_code=302)
    
    return templates.TemplateResponse(
        "courses/create.html",
        {
            "request": request,
            "current_user": current_user,
            "title": "Create Course"
        }
    )


@web_router.get("/courses", response_class=HTMLResponse)
async def courses_list(
    request: Request,
    category: Optional[str] = None,
    level: Optional[str] = None,
    price: Optional[str] = None,
    sort: str = "newest",
    search: Optional[str] = None,
    page: int = 1,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: Optional[dict] = Depends(get_current_user_web)
):
    """Courses listing page with filtering and search"""
    supabase = get_supabase_client()
    course_service = CourseService(supabase)
    
    # Get courses with filters
    courses = await course_service.get_courses(
        category=category,
        level=level,
        is_published=True
    )
    
    # Enhance courses with instructor data and enrollment counts
    enhanced_courses = []
    for course in courses:
        # Get instructor details
        instructor = supabase.table("users")\
            .select("id, email, full_name, username, avatar_url")\
            .eq("id", course["instructor_id"])\
            .execute()
        
        if instructor.data:
            course["instructor"] = instructor.data[0]
        else:
            # Provide default instructor data if not found
            course["instructor"] = {
                "full_name": "Unknown Instructor",
                "avatar_url": None
            }
        
        # Get enrollment count
        enrollments = supabase.table("enrollments")\
            .select("id", count="exact")\
            .eq("course_id", course["id"])\
            .execute()
        
        course["enrollment_count"] = enrollments.count if hasattr(enrollments, 'count') else 0
        
        # Set default duration if not available
        course["duration"] = course.get("duration", "Self-paced")
        
        enhanced_courses.append(course)
    
    # Apply search filter
    if search:
        search_lower = search.lower()
        enhanced_courses = [
            c for c in enhanced_courses 
            if search_lower in c["title"].lower() or 
               (c.get("description") and search_lower in c["description"].lower())
        ]
    
    # Apply price filter
    if price == "free":
        enhanced_courses = [c for c in enhanced_courses if c.get("price", 0) == 0]
    elif price == "paid":
        enhanced_courses = [c for c in enhanced_courses if c.get("price", 0) > 0]
    
    # Apply sorting
    if sort == "newest":
        enhanced_courses.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    elif sort == "popular":
        enhanced_courses.sort(key=lambda x: x.get("enrollment_count", 0), reverse=True)
    elif sort == "price_low":
        enhanced_courses.sort(key=lambda x: x.get("price", 0))
    elif sort == "price_high":
        enhanced_courses.sort(key=lambda x: x.get("price", 0), reverse=True)
    elif sort == "title":
        enhanced_courses.sort(key=lambda x: x.get("title", ""))
    
    # Pagination
    total_courses = len(enhanced_courses)
    courses_per_page = 9
    total_pages = (total_courses + courses_per_page - 1) // courses_per_page if total_courses > 0 else 1
    start = (page - 1) * courses_per_page
    end = start + courses_per_page
    paginated_courses = enhanced_courses[start:end] if enhanced_courses else []
    
    # Ensure page is within bounds
    if page < 1:
        page = 1
    elif page > total_pages and total_pages > 0:
        page = total_pages
    
    return templates.TemplateResponse(
        "courses/list.html",
        {
            "request": request,
            "current_user": current_user,
            "courses": paginated_courses,
            "total_courses": total_courses,
            "category": category,  # Changed from selected_category to match template
            "level": level,        # Changed from selected_level to match template
            "price": price,        # Changed from selected_price to match template
            "sort": sort,          # Changed from selected_sort to match template
            "search_query": search or "",
            "page": page,
            "total_pages": total_pages,
            "title": "All Courses"
        }
    )

# Logout
@web_router.get("/logout")
async def logout():
    """Logout user"""
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("access_token")
    return response

@web_router.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(
    request: Request,
    token: Optional[str] = None,
    templates: Jinja2Templates = Depends(get_templates)
):
    """Password reset page"""
    if not token:
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse(
        "auth/reset_password.html",
        {
            "request": request,
            "token": token,
            "title": "Reset Password"
        }
    )

@web_router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates)
):
    """Forgot password page"""
    return templates.TemplateResponse(
        "auth/forgot_password.html",  # You can create this simple page
        {
            "request": request,
            "title": "Forgot Password"
        }
    )

@web_router.get("/about", response_class=HTMLResponse)
async def about_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates)
):
    """About Us page"""
    return templates.TemplateResponse(
        "about.html",
        {
            "request": request,
            "title": "About Us"
        }
    )

@web_router.get("/team", response_class=HTMLResponse)
async def team_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: Optional[dict] = Depends(get_current_user_web)
):
    """Our Team page"""
    return templates.TemplateResponse(
        "team.html",
        {
            "request": request,
            "current_user": current_user,
            "title": "Our Team"
        }
    )

@web_router.get("/mission", response_class=HTMLResponse)
async def mission_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: Optional[dict] = Depends(get_current_user_web)
):
    """Mission & Vision page"""
    return templates.TemplateResponse(
        "mission.html",
        {
            "request": request,
            "current_user": current_user,
            "title": "Mission & Vision"
        }
    )

@web_router.get("/contact", response_class=HTMLResponse)
async def contact_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: Optional[dict] = Depends(get_current_user_web)
):
    """Contact page"""
    return templates.TemplateResponse(
        "contact.html",
        {
            "request": request,
            "current_user": current_user,
            "title": "Contact Us"
        }
    )

@web_router.get("/blog/{slug}", response_class=HTMLResponse)
async def blog_post_detail(
    request: Request,
    slug: str,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: Optional[dict] = Depends(get_current_user_web)
):
    """Individual blog post page"""
    try:
        supabase = get_supabase_client()
        blog_service = BlogService(supabase)
        
        post = await blog_service.get_post_by_slug(slug)
        
        if not post:
            return templates.TemplateResponse(
                "404.html",
                {
                    "request": request,
                    "current_user": current_user,
                    "title": "Post Not Found"
                },
                status_code=404
            )
        
        # Get related posts (same category)
        related = await blog_service.get_posts(
            category=post.get("category"),
            limit=3
        )
        # Remove current post from related
        related = [p for p in related if p["slug"] != slug][:3]
        
        return templates.TemplateResponse(
            "blog_post.html",
            {
                "request": request,
                "current_user": current_user,
                "post": post,
                "related_posts": related,
                "title": post["title"]
            }
        )
        
    except Exception as e:
        logger.error(f"Error in blog post detail: {e}")
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "current_user": current_user,
                "error": "Unable to load blog post.",
                "title": "Error"
            },
            status_code=500
        )

@web_router.get("/faq", response_class=HTMLResponse)
async def faq_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: Optional[dict] = Depends(get_current_user_web)
):
    """FAQ page"""
    return templates.TemplateResponse(
        "faq.html",
        {
            "request": request,
            "current_user": current_user,
            "title": "Frequently Asked Questions"
        }
    )

@web_router.get("/help", response_class=HTMLResponse)
async def help_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: Optional[dict] = Depends(get_current_user_web)
):
    """Help Center page"""
    return templates.TemplateResponse(
        "help.html",
        {
            "request": request,
            "current_user": current_user,
            "title": "Help Center"
        }
    )

@web_router.get("/terms", response_class=HTMLResponse)
async def terms_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: Optional[dict] = Depends(get_current_user_web)
):
    """Terms of Service page"""
    return templates.TemplateResponse(
        "terms.html",
        {
            "request": request,
            "current_user": current_user,
            "title": "Terms of Service"
        }
    )

@web_router.get("/privacy", response_class=HTMLResponse)
async def privacy_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: Optional[dict] = Depends(get_current_user_web)
):
    """Privacy Policy page"""
    return templates.TemplateResponse(
        "privacy.html",
        {
            "request": request,
            "current_user": current_user,
            "title": "Privacy Policy"
        }
    )

@web_router.get("/cookie-policy", response_class=HTMLResponse)
async def cookie_policy_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: Optional[dict] = Depends(get_current_user_web)
):
    """Cookie Policy page"""
    return templates.TemplateResponse(
        "cookie_policy.html",
        {
            "request": request,
            "current_user": current_user,
            "title": "Cookie Policy"
        }
    )

@web_router.get("/community-projects", response_class=HTMLResponse)
async def community_projects_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates)
):
    """Community Projects page"""
    return templates.TemplateResponse(
        "community_projects.html",
        {
            "request": request,
            "title": "Community Projects"
        }
    )

@web_router.get("/become-coordinator", response_class=HTMLResponse)
async def become_coordinator_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates)
):
    """Become a Coordinator page"""
    return templates.TemplateResponse(
        "become_coordinator.html",
        {
            "request": request,
            "title": "Become a Course Coordinator"
        }
    )

@web_router.get("/search", response_class=HTMLResponse)
async def search_page(
    request: Request,
    q: Optional[str] = None,
    templates: Jinja2Templates = Depends(get_templates)
):
    """Search results page"""
    # You'll need to implement search logic here
    results = []
    if q:
        # Search in courses, tutorials, etc.
        pass
    
    return templates.TemplateResponse(
        "search_results.html",
        {
            "request": request,
            "query": q,
            "results": results,
            "title": f"Search results for '{q}'" if q else "Search"
        }
    )

@web_router.get("/blog", response_class=HTMLResponse)
async def blog_page(
    request: Request,
    category: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: Optional[dict] = Depends(get_current_user_web)
):
    """Blog listing page"""
    try:
        supabase = get_supabase_client()
        blog_service = BlogService(supabase)
        
        # Get posts with filters
        posts_per_page = 9
        offset = (page - 1) * posts_per_page
        
        posts = await blog_service.get_posts(
            category=category,
            limit=posts_per_page,
            offset=offset
        )
        
        # Get total count
        all_posts = await blog_service.get_posts(category=category)
        total_posts = len(all_posts)
        total_pages = (total_posts + posts_per_page - 1) // posts_per_page if total_posts > 0 else 1
        
        # Get featured post
        featured = await blog_service.get_featured_posts(limit=1)
        featured_post = featured[0] if featured else None
        
        return templates.TemplateResponse(
            "blog.html",
            {
                "request": request,
                "current_user": current_user,
                "posts": posts,
                "featured_post": featured_post,
                "selected_category": category,
                "search_query": search,
                "page": page,
                "total_pages": total_pages,
                "title": "Blog"
            }
        )
    except Exception as e:
        logger.error(f"Error in blog page: {e}")
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "current_user": current_user,
                "error": "Unable to load blog posts",
                "title": "Error"
            }
        )

@web_router.get("/tutorials", response_class=HTMLResponse)
async def tutorials_page(
    request: Request,
    category: Optional[str] = None,
    search: Optional[str] = None,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: Optional[dict] = Depends(get_current_user_web)
):
    """Tutorials page"""
    return templates.TemplateResponse(
        "tutorials.html",
        {
            "request": request,
            "current_user": current_user,
            "selected_category": category,
            "search_query": search,
            "title": "Tutorials"
        }
    )

@web_router.get("/resources", response_class=HTMLResponse)
async def resources_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: Optional[dict] = Depends(get_current_user_web)
):
    """Free resources page"""
    return templates.TemplateResponse(
        "resources.html",
        {
            "request": request,
            "current_user": current_user,
            "title": "Free Resources"
        }
    )

@web_router.get("/success-stories", response_class=HTMLResponse)
async def success_stories_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: Optional[dict] = Depends(get_current_user_web)
):
    """Success stories page"""
    return templates.TemplateResponse(
        "success_stories.html",
        {
            "request": request,
            "current_user": current_user,
            "title": "Success Stories"
        }
    )

@web_router.get("/events", response_class=HTMLResponse)
async def events_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: Optional[dict] = Depends(get_current_user_web)
):
    """Events page"""
    return templates.TemplateResponse(
        "events.html",
        {
            "request": request,
            "current_user": current_user,
            "title": "Events"
        }
    )