from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import logging

from app.api.api_v1.dependencies import get_current_active_user, get_current_instructor
from app.web.dependencies import get_templates, get_current_user_from_cookie, get_supabase_client
from app.services.course_service import CourseService
from app.services.blog_service import BlogService
from app.services.user_service import UserService
from app.web.auth_routes import router as auth_router

logger = logging.getLogger(__name__)

web_router = APIRouter()

# Include auth routes
web_router.include_router(auth_router)

# ==================== HOME PAGE ====================

@web_router.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: Optional[dict] = Depends(get_current_user_from_cookie)
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

# ==================== DASHBOARD ====================

@web_router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: dict = Depends(get_current_user_from_cookie)
):
    """User dashboard"""
    if not current_user:
        return RedirectResponse(url="/auth", status_code=302)
    
    supabase = get_supabase_client()
    user_service = UserService(supabase)
    
    # Route to appropriate dashboard based on role
    if current_user.get("is_admin"):
        # Admin dashboard data
        total_users = supabase.table("users").select("*", count="exact").execute()
        total_instructors = supabase.table("users").select("*", count="exact").eq("is_instructor", True).execute()
        total_students = total_users.count - total_instructors.count if hasattr(total_users, 'count') else 0
        total_courses = supabase.table("courses").select("*", count="exact").execute()
        
        # Get pending instructor applications
        pending_instructors = supabase.table("instructor_applications")\
            .select("*")\
            .eq("status", "pending")\
            .execute()
        
        # Get pending course reviews
        pending_courses = supabase.table("courses")\
            .select("*, users(full_name)")\
            .eq("is_published", False)\
            .execute()
        
        # Get recent users
        recent_users = supabase.table("users")\
            .select("*")\
            .order("created_at", desc=True)\
            .limit(5)\
            .execute()
        
        return templates.TemplateResponse(
            "dashboard/admin.html",
            {
                "request": request,
                "current_user": current_user,
                "total_users": total_users.count if hasattr(total_users, 'count') else 0,
                "total_instructors": total_instructors.count if hasattr(total_instructors, 'count') else 0,
                "total_students": total_students,
                "total_courses": total_courses.count if hasattr(total_courses, 'count') else 0,
                "pending_instructors": pending_instructors.data or [],
                "pending_courses": pending_courses.data or [],
                "recent_users": recent_users.data or [],
                "title": "Admin Dashboard"
            }
        )
        
    elif current_user.get("is_instructor"):
        # Instructor dashboard data
        courses = supabase.table("courses")\
            .select("*")\
            .eq("instructor_id", current_user["id"])\
            .execute()
        
        published_courses = [c for c in courses.data if c.get("is_published")] if courses.data else []
        draft_courses = [c for c in courses.data if not c.get("is_published")] if courses.data else []
        
        # Get total students across all courses
        total_students = 0
        if courses.data:
            for course in courses.data:
                enrollments = supabase.table("enrollments")\
                    .select("*", count="exact")\
                    .eq("course_id", course["id"])\
                    .execute()
                total_students += enrollments.count if hasattr(enrollments, 'count') else 0
        
        # Get recent reviews
        course_ids = [c["id"] for c in courses.data] if courses.data else []
        recent_reviews = []
        if course_ids:
            recent_reviews = supabase.table("reviews")\
                .select("*, users(full_name), courses(title)")\
                .in_("course_id", course_ids)\
                .order("created_at", desc=True)\
                .limit(5)\
                .execute()
        
        return templates.TemplateResponse(
            "dashboard/instructor.html",
            {
                "request": request,
                "current_user": current_user,
                "total_courses": len(courses.data) if courses.data else 0,
                "published_courses": published_courses,
                "draft_courses": draft_courses,
                "total_students": total_students,
                "avg_rating": "4.5",
                "total_earnings": "0",
                "recent_reviews": recent_reviews.data if hasattr(recent_reviews, 'data') else [],
                "title": "Instructor Dashboard"
            }
        )
        
    else:
        # Student dashboard data
        enrollments = supabase.table("enrollments")\
            .select("*, courses(*)")\
            .eq("user_id", current_user["id"])\
            .execute()
        
        enrolled_courses = []
        in_progress_courses = []
        completed_courses = 0
        
        if enrollments.data:
            for enrollment in enrollments.data:
                if enrollment.get("courses"):
                    course = enrollment["courses"]
                    course["progress"] = enrollment.get("progress", 0)
                    course["enrollment"] = enrollment
                    enrolled_courses.append(course)
                    
                    if enrollment.get("progress", 0) == 100:
                        completed_courses += 1
                    elif enrollment.get("progress", 0) > 0:
                        in_progress_courses.append(course)
        
        # Get recommended courses (based on categories of enrolled courses)
        categories = list(set([c.get("category") for c in enrolled_courses if c.get("category")]))
        recommended = []
        if categories:
            recommended_query = supabase.table("courses")\
                .select("*")\
                .eq("is_published", True)\
                .in_("category", categories)\
                .limit(5)\
                .execute()
            recommended = recommended_query.data or []
        
        return templates.TemplateResponse(
            "dashboard/student.html",
            {
                "request": request,
                "current_user": current_user,
                "enrolled_courses": enrolled_courses,
                "in_progress_courses": in_progress_courses[:3],
                "completed_courses": completed_courses,
                "certificates": completed_courses,
                "total_hours": "24",
                "recommended_courses": recommended,
                "title": "My Dashboard"
            }
        )

# ==================== COURSES PAGES ====================
# Add these instructor routes BEFORE the course detail route
@web_router.get("/courses/create", response_class=HTMLResponse)
async def create_course_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: dict = Depends(get_current_instructor)
):
    """Create course page (instructors only)"""
    return templates.TemplateResponse(
        "courses/create.html",
        {
            "request": request,
            "current_user": current_user,
            "title": "Create Course"
        }
    )

@web_router.get("/my-taught-courses", response_class=HTMLResponse)
async def my_taught_courses_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: dict = Depends(get_current_instructor)
):
    """My taught courses page (instructors only)"""
    supabase = get_supabase_client()
    
    # Get courses taught by this instructor
    courses = supabase.table("courses")\
        .select("*")\
        .eq("instructor_id", current_user["id"])\
        .order("created_at", desc=True)\
        .execute()
    
    # Calculate total students
    total_students = 0
    for course in courses.data or []:
        enrollments = supabase.table("enrollments")\
            .select("id", count="exact")\
            .eq("course_id", course["id"])\
            .execute()
        course["student_count"] = enrollments.count if hasattr(enrollments, 'count') else 0
        total_students += course["student_count"]
    
    return templates.TemplateResponse(
        "instructor/my_courses.html",  # This template exists now
        {
            "request": request,
            "current_user": current_user,
            "courses": courses.data or [],
            "total_students": total_students,
            "title": "My Taught Courses"
        }
    )

@web_router.get("/instructor/analytics", response_class=HTMLResponse)
async def instructor_analytics(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: dict = Depends(get_current_instructor)
):
    """Instructor analytics page"""
    supabase = get_supabase_client()
    
    # Get instructor's courses
    courses = supabase.table("courses")\
        .select("*")\
        .eq("instructor_id", current_user["id"])\
        .execute()
    
    # Calculate stats
    total_courses = len(courses.data)
    total_students = 0
    total_revenue = 0
    
    for course in courses.data:
        # Get enrollments
        enrollments = supabase.table("enrollments")\
            .select("id", count="exact")\
            .eq("course_id", course["id"])\
            .execute()
        total_students += enrollments.count if hasattr(enrollments, 'count') else 0
        
        # Calculate revenue (simplified)
        if course.get("price", 0) > 0:
            total_revenue += course["price"] * (enrollments.count if hasattr(enrollments, 'count') else 0)
    
    return templates.TemplateResponse(
        "instructor/analytics.html",
        {
            "request": request,
            "current_user": current_user,
            "total_courses": total_courses,
            "total_students": total_students,
            "total_earnings": total_revenue,
            "avg_rating": "4.5",
            "courses": courses.data,
            "title": "Analytics"
        }
    )

@web_router.get("/instructor/earnings", response_class=HTMLResponse)
async def instructor_earnings(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: dict = Depends(get_current_instructor)
):
    """Instructor earnings page"""
    supabase = get_supabase_client()
    
    # Get instructor's courses
    courses = supabase.table("courses")\
        .select("*")\
        .eq("instructor_id", current_user["id"])\
        .execute()
    
    # Calculate earnings
    total_revenue = 0
    monthly_revenue = 0
    transactions = []
    
    for course in courses.data:
        if course.get("price", 0) > 0:
            enrollments = supabase.table("enrollments")\
                .select("*, users(full_name)")\
                .eq("course_id", course["id"])\
                .execute()
            
            for enrollment in enrollments.data:
                amount = course["price"]
                total_revenue += amount
                monthly_revenue += amount
                
                transactions.append({
                    "date": enrollment.get("enrolled_at", "2024-01-01"),
                    "course_title": course["title"],
                    "student_name": enrollment.get("users", {}).get("full_name", "Student"),
                    "amount": amount
                })
    
    return templates.TemplateResponse(
        "instructor/earnings.html",
        {
            "request": request,
            "current_user": current_user,
            "total_revenue": total_revenue,
            "monthly_revenue": monthly_revenue,
            "total_students": len(transactions),
            "lifetime_sales": len(transactions),
            "transactions": transactions,
            "title": "Earnings"
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
    current_user: Optional[dict] = Depends(get_current_user_from_cookie)
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
    
    # Enhance courses with instructor data
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
    
    return templates.TemplateResponse(
        "courses/list.html",
        {
            "request": request,
            "current_user": current_user,
            "courses": paginated_courses,
            "total_courses": total_courses,
            "category": category or "",
            "level": level or "",
            "price": price or "",
            "sort": sort,
            "search_query": search or "",
            "page": page,
            "total_pages": total_pages,
            "title": "All Courses"
        }
    )

@web_router.get("/courses/{course_id}", response_class=HTMLResponse)
async def course_detail(
    request: Request,
    course_id: str,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: Optional[dict] = Depends(get_current_user_from_cookie)
):
    """Course detail page"""
    supabase = get_supabase_client()
    course_service = CourseService(supabase)
    
    course = await course_service.get_course_with_details(course_id)
    if not course:
        return templates.TemplateResponse(
            "404.html",
            {
                "request": request,
                "current_user": current_user,
                "title": "Course Not Found"
            },
            status_code=404
        )
    
    # Check if user is enrolled
    is_enrolled = False
    if current_user:
        enrollment = supabase.table("enrollments")\
            .select("*")\
            .eq("user_id", current_user["id"])\
            .eq("course_id", course_id)\
            .execute()
        is_enrolled = len(enrollment.data) > 0 if enrollment.data else False
    
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

# ==================== Courses | Certificates =======================

@web_router.get("/my-courses", response_class=HTMLResponse)
async def my_courses_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: dict = Depends(get_current_active_user)
):
    """My Courses page"""
    supabase = get_supabase_client()
    
    # Get enrolled courses with progress
    enrollments = supabase.table("enrollments")\
        .select("*, courses(*)")\
        .eq("user_id", current_user["id"])\
        .execute()
    
    in_progress = []
    completed = []
    
    for enrollment in enrollments.data:
        if enrollment.get("courses"):
            course = enrollment["courses"]
            course["progress"] = enrollment.get("progress", 0)
            course["enrolled_at"] = enrollment.get("enrolled_at")
            
            if enrollment.get("progress", 0) >= 100:
                course["completed_at"] = enrollment.get("completed_at")
                completed.append(course)
            else:
                in_progress.append(course)
    
    # Get wishlist (you'd need a wishlist table)
    wishlist = []
    
    return templates.TemplateResponse(
        "my_courses.html",
        {
            "request": request,
            "current_user": current_user,
            "in_progress_courses": in_progress,
            "completed_courses": completed,
            "wishlist_courses": wishlist,
            "title": "My Courses"
        }
    )

@web_router.get("/my-certificates", response_class=HTMLResponse)
async def my_certificates_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: dict = Depends(get_current_active_user)
):
    """My Certificates page"""
    supabase = get_supabase_client()
    
    # Get certificates (you'd need a certificates table)
    certificates = []
    
    # For now, generate from completed courses
    enrollments = supabase.table("enrollments")\
        .select("*, courses(title)")\
        .eq("user_id", current_user["id"])\
        .gte("progress", 100)\
        .execute()
    
    for i, enrollment in enumerate(enrollments.data):
        certificates.append({
            "id": f"cert_{i}",
            "course_title": enrollment.get("courses", {}).get("title", "Course"),
            "issued_date": enrollment.get("completed_at", "2024-01-01")
        })
    
    return templates.TemplateResponse(
        "my_certificates.html",
        {
            "request": request,
            "current_user": current_user,
            "certificates": certificates,
            "title": "My Certificates"
        }
    )

@web_router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: dict = Depends(get_current_active_user)
):
    """Settings page"""
    return templates.TemplateResponse(
        "dashboard/settings.html",
        {
            "request": request,
            "current_user": current_user,
            "title": "Settings"
        }
    )

# ==================== BLOG PAGES ====================

@web_router.get("/blog", response_class=HTMLResponse)
async def blog_page(
    request: Request,
    category: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: Optional[dict] = Depends(get_current_user_from_cookie)
):
    """Blog listing page"""
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
    
    # Get categories with counts
    categories = await blog_service.get_categories()
    
    # Get recent posts for sidebar
    recent_posts = await blog_service.get_recent_posts(limit=5)
    
    return templates.TemplateResponse(
        "blog.html",
        {
            "request": request,
            "current_user": current_user,
            "posts": posts,
            "featured_post": featured_post,
            "categories": categories,
            "recent_posts": recent_posts,
            "selected_category": category,
            "search_query": search,
            "page": page,
            "total_pages": total_pages,
            "total_posts": total_posts,
            "title": "Blog" + (f" - {category}" if category else "")
        }
    )

@web_router.get("/blog/{slug}", response_class=HTMLResponse)
async def blog_post_detail(
    request: Request,
    slug: str,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: Optional[dict] = Depends(get_current_user_from_cookie)
):
    """Individual blog post page"""
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

# ==================== STATIC PAGES ====================

@web_router.get("/about", response_class=HTMLResponse)
async def about_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: Optional[dict] = Depends(get_current_user_from_cookie)
):
    """About Us page"""
    return templates.TemplateResponse(
        "about.html",
        {
            "request": request,
            "current_user": current_user,
            "title": "About Us"
        }
    )

@web_router.get("/team", response_class=HTMLResponse)
async def team_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: Optional[dict] = Depends(get_current_user_from_cookie)
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
    current_user: Optional[dict] = Depends(get_current_user_from_cookie)
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
    current_user: Optional[dict] = Depends(get_current_user_from_cookie)
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

@web_router.get("/faq", response_class=HTMLResponse)
async def faq_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: Optional[dict] = Depends(get_current_user_from_cookie)
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

@web_router.get("/terms", response_class=HTMLResponse)
async def terms_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: Optional[dict] = Depends(get_current_user_from_cookie)
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
    current_user: Optional[dict] = Depends(get_current_user_from_cookie)
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
    current_user: Optional[dict] = Depends(get_current_user_from_cookie)
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

# ==================== RESOURCE PAGES ====================

@web_router.get("/tutorials", response_class=HTMLResponse)
async def tutorials_page(
    request: Request,
    category: Optional[str] = None,
    search: Optional[str] = None,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: Optional[dict] = Depends(get_current_user_from_cookie)
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
    current_user: Optional[dict] = Depends(get_current_user_from_cookie)
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
    current_user: Optional[dict] = Depends(get_current_user_from_cookie)
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
    current_user: Optional[dict] = Depends(get_current_user_from_cookie)
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

@web_router.get("/community-projects", response_class=HTMLResponse)
async def community_projects_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: Optional[dict] = Depends(get_current_user_from_cookie)
):
    """Community Projects page"""
    return templates.TemplateResponse(
        "community_projects.html",
        {
            "request": request,
            "current_user": current_user,
            "title": "Community Projects"
        }
    )

@web_router.get("/become-coordinator", response_class=HTMLResponse)
async def become_coordinator_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: Optional[dict] = Depends(get_current_user_from_cookie)
):
    """Become a Coordinator page"""
    return templates.TemplateResponse(
        "become_coordinator.html",
        {
            "request": request,
            "current_user": current_user,
            "title": "Become a Course Coordinator"
        }
    )

# ==================== SEARCH ====================

@web_router.get("/search", response_class=HTMLResponse)
async def search_page(
    request: Request,
    q: Optional[str] = None,
    page: int = 1,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: Optional[dict] = Depends(get_current_user_from_cookie)
):
    """Search results page"""
    supabase = get_supabase_client()
    results = []
    
    if q:
        # Search in courses
        courses = supabase.table("courses")\
            .select("*")\
            .eq("is_published", True)\
            .ilike("title", f"%{q}%")\
            .execute()
        
        # Search in blog posts
        posts = supabase.table("blog_posts")\
            .select("*")\
            .eq("is_published", True)\
            .ilike("title", f"%{q}%")\
            .execute()
        
        results = {
            "courses": courses.data if courses.data else [],
            "posts": posts.data if posts.data else []
        }
    
    return templates.TemplateResponse(
        "search_results.html",
        {
            "request": request,
            "current_user": current_user,
            "query": q,
            "results": results,
            "page": page,
            "title": f"Search results for '{q}'" if q else "Search"
        }
    )

# ==================== PROFILE ====================

@web_router.get("/profile", response_class=HTMLResponse)
async def profile_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: dict = Depends(get_current_active_user)
):
    """User profile page"""
    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "current_user": current_user,
            "title": "My Profile"
        }
    )

@web_router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: dict = Depends(get_current_user_from_cookie)
):
    """User settings page"""
    if not current_user:
        return RedirectResponse(url="/auth", status_code=302)
    
    return templates.TemplateResponse(
        "dashboard/settings.html",
        {
            "request": request,
            "current_user": current_user,
            "title": "Settings"
        }
    )

# ==================== ERROR HANDLERS ====================

@web_router.get("/404", response_class=HTMLResponse)
async def not_found_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: Optional[dict] = Depends(get_current_user_from_cookie)
):
    """404 Not Found page"""
    return templates.TemplateResponse(
        "404.html",
        {
            "request": request,
            "current_user": current_user,
            "title": "Page Not Found"
        },
        status_code=404
    )

@web_router.get("/500", response_class=HTMLResponse)
async def server_error_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: Optional[dict] = Depends(get_current_user_from_cookie)
):
    """500 Server Error page"""
    return templates.TemplateResponse(
        "500.html",
        {
            "request": request,
            "current_user": current_user,
            "title": "Server Error"
        },
        status_code=500
    )