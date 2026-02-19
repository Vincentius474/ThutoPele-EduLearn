from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
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

# Courses list page
@web_router.get("/courses", response_class=HTMLResponse)
async def courses_list(
    request: Request,
    category: Optional[str] = None,
    level: Optional[str] = None,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: Optional[dict] = Depends(get_current_user_web)
):
    """Courses listing page"""
    supabase = get_supabase_client()
    course_service = CourseService(supabase)
    
    courses = await course_service.get_courses(
        category=category,
        level=level,
        is_published=True
    )
    
    return templates.TemplateResponse(
        "courses/list.html",
        {
            "request": request,
            "current_user": current_user,
            "courses": courses,
            "selected_category": category,
            "selected_level": level,
            "title": "Courses"
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

# Edit course page
@web_router.get("/courses/{course_id}/edit", response_class=HTMLResponse)
async def edit_course_page(
    request: Request,
    course_id: str,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: dict = Depends(get_current_user_web)
):
    """Edit course page"""
    if not current_user or not current_user.get("is_instructor"):
        return RedirectResponse(url="/courses", status_code=302)
    
    supabase = get_supabase_client()
    course_service = CourseService(supabase)
    
    course = await course_service.get_course(course_id)
    if not course or course["instructor_id"] != current_user["id"]:
        raise HTTPException(status_code=404, detail="Course not found")
    
    return templates.TemplateResponse(
        "courses/edit.html",
        {
            "request": request,
            "current_user": current_user,
            "course": course,
            "title": f"Edit {course['title']}"
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

# Add these routes to your web.py

@web_router.get("/team", response_class=HTMLResponse)
async def team_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates)
):
    """Team page"""
    return templates.TemplateResponse(
        "team.html",
        {
            "request": request,
            "title": "Our Team"
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

@web_router.get("/mission", response_class=HTMLResponse)
async def mission_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates)
):
    """Mission & Vision page"""
    return templates.TemplateResponse(
        "mission.html",
        {
            "request": request,
            "title": "Mission & Vision"
        }
    )

@web_router.get("/contact", response_class=HTMLResponse)
async def contact_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates)
):
    """Contact page"""
    return templates.TemplateResponse(
        "contact.html",
        {
            "request": request,
            "title": "Contact Us"
        }
    )

@web_router.get("/faq", response_class=HTMLResponse)
async def faq_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates)
):
    """FAQ page"""
    return templates.TemplateResponse(
        "faq.html",
        {
            "request": request,
            "title": "Frequently Asked Questions"
        }
    )

@web_router.get("/blog", response_class=HTMLResponse)
async def blog_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates)
):
    """Blog page"""
    return templates.TemplateResponse(
        "blog.html",
        {
            "request": request,
            "title": "Blog"
        }
    )

@web_router.get("/tutorials", response_class=HTMLResponse)
async def tutorials_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates)
):
    """Tutorials page"""
    return templates.TemplateResponse(
        "tutorials.html",
        {
            "request": request,
            "title": "Tutorials"
        }
    )

@web_router.get("/resources", response_class=HTMLResponse)
async def resources_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates)
):
    """Free Resources page"""
    return templates.TemplateResponse(
        "resources.html",
        {
            "request": request,
            "title": "Free Resources"
        }
    )

@web_router.get("/success-stories", response_class=HTMLResponse)
async def success_stories_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates)
):
    """Success Stories page"""
    return templates.TemplateResponse(
        "success_stories.html",
        {
            "request": request,
            "title": "Success Stories"
        }
    )

@web_router.get("/events", response_class=HTMLResponse)
async def events_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates)
):
    """Events page"""
    return templates.TemplateResponse(
        "events.html",
        {
            "request": request,
            "title": "Events"
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