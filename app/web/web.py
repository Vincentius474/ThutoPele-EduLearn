from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import logging

from app.api.api_v1.dependencies import get_current_active_user, get_current_admin, get_current_admin_or_instructor, get_current_instructor
from app.api.api_v1.endpoints.tutorials import get_tutorials
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
    
    templates.env.cache_size = 0
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
    """Role-based dashboard"""
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    supabase = get_supabase_client()
    
    # Route to appropriate dashboard based on role
    if current_user.get("is_admin"):
        # Admin dashboard
        return templates.TemplateResponse(
            "dashboard/admin.html",
            {
                "request": request,
                "current_user": current_user,
                "title": "Admin Dashboard"
            }
        )
        
    elif current_user.get("is_instructor"):
        # Instructor dashboard
        return templates.TemplateResponse(
            "dashboard/instructor.html",
            {
                "request": request,
                "current_user": current_user,
                "title": "Instructor Dashboard"
            }
        )
        
    else:
        # Student dashboard
        try:
            enrollments = supabase.table("enrollments")\
                .select("*, courses(*)")\
                .eq("user_id", current_user["id"])\
                .execute()
            
            enrolled_courses = []
            in_progress_courses = []
            completed_courses = 0
            total_hours = 0
            
            for enrollment in enrollments.data:
                if enrollment.get("courses"):
                    course = enrollment["courses"]
                    course["progress"] = enrollment.get("progress", 0)
                    course["enrolled_at"] = enrollment.get("enrolled_at")
                    
                    # Get instructor details
                    instructor = supabase.table("users")\
                        .select("full_name")\
                        .eq("id", course["instructor_id"])\
                        .execute()
                    
                    if instructor.data:
                        course["instructor"] = instructor.data[0]
                    
                    enrolled_courses.append(course)
                    
                    if enrollment.get("progress", 0) == 100:
                        completed_courses += 1
                    elif enrollment.get("progress", 0) > 0:
                        in_progress_courses.append(course)
                    
                    # Calculate total hours (simplified)
                    total_hours += 15
            
            # Get recommended courses
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
            
            # ==================== PROGRAMMING ASSIGNMENTS ====================
            # Get programming assignments for enrolled courses
            programming_assignments = []
            
            for course in enrolled_courses:
                course_assignments = supabase.table("programming_assignments")\
                    .select("*")\
                    .eq("course_id", course["id"])\
                    .execute()
                
                for assignment in course_assignments.data:
                    # Check if student has submitted this assignment
                    submission = supabase.table("code_submissions")\
                        .select("*")\
                        .eq("assignment_id", assignment["id"])\
                        .eq("user_id", current_user["id"])\
                        .order("submitted_at", desc=True)\
                        .limit(1)\
                        .execute()
                    
                    if submission.data:
                        assignment["submission"] = submission.data[0]
                    
                    programming_assignments.append(assignment)
            
            # Sort by due date (if exists) or creation date
            programming_assignments.sort(key=lambda x: x.get("due_date", x.get("created_at", "")), reverse=False)
            
            # ==================== RECENT ACTIVITIES ====================
            recent_activities = []
            
            try:
                # Get recent quiz attempts
                quiz_attempts = supabase.table("quiz_attempts")\
                    .select("*, quizzes(title)")\
                    .eq("user_id", current_user["id"])\
                    .order("created_at", desc=True)\
                    .limit(5)\
                    .execute()
                
                for attempt in quiz_attempts.data:
                    recent_activities.append({
                        "icon": "question-circle",
                        "message": f"Completed quiz: {attempt.get('quizzes', {}).get('title', 'Unknown')} - Score: {attempt.get('score', 0)}%",
                        "created_at": attempt.get("created_at", "")[:10] if attempt.get("created_at") else "Recently"
                    })
            except Exception as e:
                print(f"Error fetching quiz attempts: {e}")
            
            try:
                # Get recent assignment submissions
                submissions = supabase.table("submissions")\
                    .select("*, assignments(title)")\
                    .eq("user_id", current_user["id"])\
                    .order("submitted_at", desc=True)\
                    .limit(5)\
                    .execute()
                
                for submission in submissions.data:
                    recent_activities.append({
                        "icon": "tasks",
                        "message": f"Submitted assignment: {submission.get('assignments', {}).get('title', 'Unknown')}",
                        "created_at": submission.get("submitted_at", "")[:10] if submission.get("submitted_at") else "Recently"
                    })
            except Exception as e:
                print(f"Error fetching submissions: {e}")
            
            try:
                # Get recent programming assignment submissions
                code_submissions = supabase.table("code_submissions")\
                    .select("*, programming_assignments(title)")\
                    .eq("user_id", current_user["id"])\
                    .order("submitted_at", desc=True)\
                    .limit(5)\
                    .execute()
                
                for submission in code_submissions.data:
                    score = submission.get("score", 0)
                    recent_activities.append({
                        "icon": "code",
                        "message": f"Submitted coding assignment: {submission.get('programming_assignments', {}).get('title', 'Unknown')} - Score: {score}%",
                        "created_at": submission.get("submitted_at", "")[:10] if submission.get("submitted_at") else "Recently"
                    })
            except Exception as e:
                print(f"Error fetching code submissions: {e}")
            
            # Sort and limit activities
            recent_activities.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            recent_activities = recent_activities[:10]
            
            return templates.TemplateResponse(
                "dashboard/student.html",
                {
                    "request": request,
                    "current_user": current_user,
                    "enrolled_courses": enrolled_courses,
                    "in_progress_courses": in_progress_courses[:3],
                    "completed_courses": completed_courses,
                    "certificates": completed_courses,
                    "total_hours": total_hours,
                    "recommended_courses": recommended,
                    "programming_assignments": programming_assignments,  # Add this
                    "recent_activities": recent_activities,
                    "title": "My Dashboard"
                }
            )
        except Exception as e:
            print(f"Dashboard error: {e}")
            import traceback
            traceback.print_exc()
            
            # Return basic dashboard if there's an error
            return templates.TemplateResponse(
                "dashboard/student.html",
                {
                    "request": request,
                    "current_user": current_user,
                    "enrolled_courses": [],
                    "in_progress_courses": [],
                    "completed_courses": 0,
                    "certificates": 0,
                    "total_hours": 0,
                    "recommended_courses": [],
                    "programming_assignments": [],  # Add this
                    "recent_activities": [],
                    "title": "My Dashboard"
                }
            )

# ==================== COURSES PAGES ====================

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
    
    # Get course details
    course_result = supabase.table("courses")\
        .select("*")\
        .eq("id", course_id)\
        .execute()
    
    if not course_result.data:
        return templates.TemplateResponse(
            "404.html",
            {"request": request, "title": "Course Not Found"},
            status_code=404
        )
    
    course = course_result.data[0]
    
    # Get instructor details
    instructor = supabase.table("users")\
        .select("id, email, full_name, avatar_url, bio")\
        .eq("id", course["instructor_id"])\
        .execute()
    
    course["instructor"] = instructor.data[0] if instructor.data else {"full_name": "Unknown"}
    
    # Get course materials
    materials = supabase.table("course_materials")\
        .select("*")\
        .eq("course_id", course_id)\
        .order("order_index")\
        .execute()
    
    print(f"Found {len(materials.data)} materials for course {course_id}")  # Debug log
    
    # Check enrollment status
    is_enrolled = False
    progress = 0
    completed_lessons = 0
    has_reviewed = False
    
    if current_user:
        # Check enrollment
        enrollment = supabase.table("enrollments")\
            .select("*")\
            .eq("user_id", current_user["id"])\
            .eq("course_id", course_id)\
            .execute()
        
        if enrollment.data:
            is_enrolled = True
            progress = enrollment.data[0].get("progress", 0)
            
            # Get completed lessons
            if materials.data:
                completed = supabase.table("lesson_progress")\
                    .select("lesson_id")\
                    .eq("user_id", current_user["id"])\
                    .execute()
                
                completed_ids = {item["lesson_id"] for item in completed.data}
                completed_lessons = len(completed_ids)
                
                # Mark materials as completed
                for material in materials.data:
                    material["completed"] = material["id"] in completed_ids
    
    return templates.TemplateResponse(
        "courses/detail.html",
        {
            "request": request,
            "current_user": current_user,
            "course": course,
            "materials": materials.data or [],
            "is_enrolled": is_enrolled,
            "progress": progress,
            "completed_lessons": completed_lessons,
            "total_lessons": len(materials.data),
            "title": course["title"]
        }
    )

# =================== For Instructor Purposes =======================

@web_router.get("/courses/{course_id}/manage", response_class=HTMLResponse)
async def course_management_page(
    request: Request,
    course_id: str,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: dict = Depends(get_current_instructor)
):
    """Course management page"""
    supabase = get_supabase_client()
    
    # Fetch all course data
    result = supabase.table("courses")\
        .select("*")\
        .eq("id", course_id)\
        .execute()
    
    if not result.data:
        return templates.TemplateResponse(
            "404.html",
            {"request": request, "title": "Course Not Found"},
            status_code=404
        )
    
    course = result.data[0]
    
    # Verify instructor owns this course
    if course["instructor_id"] != current_user["id"]:
        return templates.TemplateResponse(
            "403.html",
            {"request": request, "title": "Access Denied"},
            status_code=403
        )
    
    # Fetch materials
    materials = supabase.table("course_materials")\
        .select("*")\
        .eq("course_id", course_id)\
        .order("order_index")\
        .execute()
    
    # Fetch quizzes
    quizzes = supabase.table("quizzes")\
        .select("*")\
        .eq("course_id", course_id)\
        .execute()
    
    # Fetch assignments
    assignments = supabase.table("assignments")\
        .select("*")\
        .eq("course_id", course_id)\
        .execute()
    
    # Fetch announcements
    announcements = supabase.table("announcements")\
        .select("*, users(full_name, avatar_url)")\
        .eq("course_id", course_id)\
        .order("created_at", desc=True)\
        .execute()
    
    # Fetch enrolled students
    students = supabase.table("enrollments")\
        .select("*, users(id, email, full_name, avatar_url)")\
        .eq("course_id", course_id)\
        .execute()
    
    enrolled_students = []
    for enrollment in students.data:
        if enrollment.get("users"):
            student = enrollment["users"]
            student["enrolled_at"] = enrollment["enrolled_at"]
            student["progress"] = enrollment["progress"]
            enrolled_students.append(student)
    
    return templates.TemplateResponse(
        "courses/manage.html",
        {
            "request": request,
            "current_user": current_user,
            "course": course,
            "materials": materials.data or [],
            "quizzes": quizzes.data or [],
            "assignments": assignments.data or [],
            "announcements": announcements.data or [],
            "students": enrolled_students,
            "title": f"Manage {course['title']}"
        }
    )

@web_router.get("/courses/{course_id}/edit", response_class=HTMLResponse)
async def edit_course_page(
    request: Request,
    course_id: str,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: dict = Depends(get_current_instructor)
):
    """Edit course page (instructors only)"""
    supabase = get_supabase_client()
    
    # Get course details
    course_result = supabase.table("courses")\
        .select("*")\
        .eq("id", course_id)\
        .execute()
    
    if not course_result.data:
        return templates.TemplateResponse(
            "404.html",
            {"request": request, "title": "Course Not Found"},
            status_code=404
        )
    
    course = course_result.data[0]
    
    # Check if user owns this course
    if course["instructor_id"] != current_user["id"]:
        return templates.TemplateResponse(
            "403.html",
            {"request": request, "title": "Access Denied"},
            status_code=403
        )
    
    return templates.TemplateResponse(
        "courses/edit.html",
        {
            "request": request,
            "current_user": current_user,
            "course": course,
            "title": f"Edit {course['title']}"
        }
    )

@web_router.get("/instructor/materials", response_class=HTMLResponse)
async def instructor_materials_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: dict = Depends(get_current_instructor)
):
    """Instructor materials management page"""
    supabase = get_supabase_client()
    
    # Get instructor's courses
    courses = supabase.table("courses")\
        .select("*")\
        .eq("instructor_id", current_user["id"])\
        .execute()
    
    return templates.TemplateResponse(
        "instructor/materials.html",
        {
            "request": request,
            "current_user": current_user,
            "courses": courses.data or [],
            "title": "Course Materials"
        }
    )

@web_router.get("/instructor/messages", response_class=HTMLResponse)
async def instructor_messages_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: dict = Depends(get_current_instructor)
):
    """Instructor messages page"""
    supabase = get_supabase_client()
    
    # Get instructor's courses with student counts
    courses = supabase.table("courses")\
        .select("*")\
        .eq("instructor_id", current_user["id"])\
        .execute()
    
    # Add student counts
    for course in courses.data:
        enrollments = supabase.table("enrollments")\
            .select("id", count="exact")\
            .eq("course_id", course["id"])\
            .execute()
        course["student_count"] = enrollments.count if hasattr(enrollments, 'count') else 0
    
    return templates.TemplateResponse(
        "instructor/messages.html",
        {
            "request": request,
            "current_user": current_user,
            "courses": courses.data or [],
            "title": "Message Students"
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

@web_router.get("/courses/{course_id}/learn", response_class=HTMLResponse)
async def student_course_view(
    request: Request,
    course_id: str,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: dict = Depends(get_current_active_user)
):
    """Student course view page"""
    supabase = get_supabase_client()
    
    # Check if student is enrolled
    enrollment = supabase.table("enrollments")\
        .select("*")\
        .eq("user_id", current_user["id"])\
        .eq("course_id", course_id)\
        .execute()
    
    if not enrollment.data:
        return RedirectResponse(url=f"/courses/{course_id}", status_code=302)
    
    # Get course details
    course = supabase.table("courses")\
        .select("*")\
        .eq("id", course_id)\
        .execute()
    
    if not course.data:
        return templates.TemplateResponse(
            "404.html",
            {"request": request, "title": "Course Not Found"},
            status_code=404
        )
    
    # Get instructor
    instructor = supabase.table("users")\
        .select("id, full_name, avatar_url")\
        .eq("id", course.data[0]["instructor_id"])\
        .execute()
    
    # Get materials with completion status
    materials = supabase.table("course_materials")\
        .select("*")\
        .eq("course_id", course_id)\
        .order("order_index")\
        .execute()
    
    # Get completed materials
    completed = supabase.table("lesson_progress")\
        .select("lesson_id")\
        .eq("user_id", current_user["id"])\
        .execute()
    
    completed_ids = {item["lesson_id"] for item in completed.data}
    for material in materials.data:
        material["completed"] = material["id"] in completed_ids
    
    # Get quizzes with attempts
    quizzes = supabase.table("quizzes")\
        .select("*")\
        .eq("course_id", course_id)\
        .execute()
    
    for quiz in quizzes.data:
        questions = supabase.table("quiz_questions")\
            .select("*")\
            .eq("quiz_id", quiz["id"])\
            .execute()
        quiz["questions"] = questions.data
        
        # Get student's attempt
        attempt = supabase.table("quiz_attempts")\
            .select("*")\
            .eq("quiz_id", quiz["id"])\
            .eq("user_id", current_user["id"])\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        if attempt.data:
            quiz["attempt"] = attempt.data[0]
    
    # Get assignments with submissions
    assignments = supabase.table("assignments")\
        .select("*")\
        .eq("course_id", course_id)\
        .execute()
    
    for assignment in assignments.data:
        submission = supabase.table("submissions")\
            .select("*")\
            .eq("assignment_id", assignment["id"])\
            .eq("user_id", current_user["id"])\
            .execute()
        if submission.data:
            assignment["submission"] = submission.data[0]
    
    # Get announcements
    announcements = supabase.table("announcements")\
        .select("*, users(full_name)")\
        .eq("course_id", course_id)\
        .order("created_at", desc=True)\
        .execute()
    
    # Get messages
    messages = supabase.table("course_messages")\
        .select("*")\
        .eq("course_id", course_id)\
        .eq("user_id", current_user["id"])\
        .order("created_at")\
        .execute()
    
    # Get unread count
    unread_count = supabase.table("course_messages")\
        .select("*", count="exact")\
        .eq("course_id", course_id)\
        .eq("user_id", current_user["id"])\
        .eq("is_read", False)\
        .execute()
    
    total_unread = unread_count.count if hasattr(unread_count, 'count') else 0
    
    # Calculate progress
    total_materials = len(materials.data)
    completed_materials = len(completed_ids)
    progress = int((completed_materials / total_materials) * 100) if total_materials > 0 else 0
    
    return templates.TemplateResponse(
        "courses/student_view.html",
        {
            "request": request,
            "current_user": current_user,
            "course": course.data[0],
            "instructor": instructor.data[0] if instructor.data else {},
            "materials": materials.data,
            "quizzes": quizzes.data,
            "assignments": assignments.data,
            "announcements": announcements.data,
            "messages": messages.data,
            "progress": progress,
            "completed_materials": completed_materials,
            "total_materials": total_materials,
            "enrollment_date": enrollment.data[0]["enrolled_at"][:10],
            "unread_count": total_unread,  # Add this
            "title": course.data[0]["title"]
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
    
    # Get featured post
    featured = supabase.table("blog_posts")\
        .select("*, users(full_name, avatar_url)")\
        .eq("is_published", True)\
        .eq("is_featured", True)\
        .order("published_at", desc=True)\
        .limit(1)\
        .execute()
    
    featured_post = featured.data[0] if featured.data else None
    
    # Pagination settings
    limit = 9
    offset = (page - 1) * limit
    
    # Handle search using database function
    if search:
        # Use the database function for efficient search
        result = supabase.rpc(
            "search_blog_posts",
            {
                "search_term": search,
                "category_filter": category if category else None
            }
        ).execute()
        
        posts = result.data
        total = len(posts)
        
        # Apply pagination to results
        paginated_posts = posts[offset:offset + limit]
        total_pages = (total + limit - 1) // limit if total > 0 else 1
        
        return templates.TemplateResponse(
            "blog.html",
            {
                "request": request,
                "current_user": current_user,
                "featured_post": featured_post,
                "posts": paginated_posts,
                "selected_category": category,
                "search_query": search,
                "page": page,
                "total_pages": total_pages,
                "title": f"Blog - Search: {search}"
            }
        )
    
    # Regular query without search
    query = supabase.table("blog_posts")\
        .select("*, users(full_name, avatar_url)", count="exact")\
        .eq("is_published", True)
    
    if category:
        query = query.eq("category", category)
    
    # Get total count
    count_result = query.execute()
    total = count_result.count if hasattr(count_result, 'count') else 0
    
    # Apply sorting and pagination
    result = query.order("published_at", desc=True)\
        .range(offset, offset + limit - 1)\
        .execute()
    
    total_pages = (total + limit - 1) // limit if total > 0 else 1
    
    return templates.TemplateResponse(
        "blog.html",
        {
            "request": request,
            "current_user": current_user,
            "featured_post": featured_post,
            "posts": result.data,
            "selected_category": category,
            "search_query": search,
            "page": page,
            "total_pages": total_pages,
            "title": f"Blog - {category if category else 'All Posts'}"
        }
    )

@web_router.get("/blog/{slug}", response_class=HTMLResponse)
async def blog_post_detail(
    request: Request,
    slug: str,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: Optional[dict] = Depends(get_current_user_from_cookie)
):
    """Blog post detail page"""
    supabase = get_supabase_client()
    
    # Fetch the post
    result = supabase.table("blog_posts")\
        .select("*, users(full_name, avatar_url)")\
        .eq("slug", slug)\
        .eq("is_published", True)\
        .execute()
    
    if not result.data:
        return templates.TemplateResponse(
            "404.html",
            {"request": request, "title": "Post Not Found"},
            status_code=404
        )
    
    post = result.data[0]
    
    # Get comments
    comments = supabase.table("blog_comments")\
        .select("*, users(full_name, avatar_url)")\
        .eq("post_id", post["id"])\
        .eq("is_approved", True)\
        .order("created_at", desc=True)\
        .execute()
    
    post["comments"] = comments.data
    
    return templates.TemplateResponse(
        "blog_detail.html",
        {
            "request": request,
            "current_user": current_user,
            "post": post,
            "title": post["title"]
        }
    )

@web_router.get("/admin/blog/create", response_class=HTMLResponse)
async def create_blog_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: dict = Depends(get_current_admin_or_instructor)
):
    """Create blog post page (admin/instructor only)"""
    return templates.TemplateResponse(
        "admin/create_blog.html",
        {
            "request": request,
            "current_user": current_user,
            "title": "Create Blog Post"
        }
    )

@web_router.get("/admin/blog/{post_id}/edit", response_class=HTMLResponse)
async def edit_blog_page(
    request: Request,
    post_id: str,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: dict = Depends(get_current_admin_or_instructor)
):
    """Edit blog post page (admin/instructor only)"""
    supabase = get_supabase_client()
    
    # Get blog post
    post = supabase.table("blog_posts")\
        .select("*")\
        .eq("id", post_id)\
        .execute()
    
    if not post.data:
        return templates.TemplateResponse(
            "404.html",
            {"request": request, "title": "Post Not Found"},
            status_code=404
        )
    
    return templates.TemplateResponse(
        "admin/edit_blog.html",
        {
            "request": request,
            "current_user": current_user,
            "post": post.data[0],
            "title": f"Edit: {post.data[0]['title']}"
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
    page: int = 1,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: Optional[dict] = Depends(get_current_user_from_cookie)
):
    """Tutorials listing page"""
    supabase = get_supabase_client()
    
    limit = 9
    offset = (page - 1) * limit
    
    if search:
        # Use the search endpoint
        result = await get_tutorials(
            category=category,
            search=search,
            limit=limit,
            offset=offset,
            supabase=supabase
        )
        tutorials = result.get("tutorials", [])
        total = result.get("total", 0)
    else:
        # Regular query
        query = supabase.table("tutorials")\
            .select("*", count="exact")\
            .eq("is_published", True)
        
        if category and category != 'all':
            query = query.eq("category", category)
        
        count_result = query.execute()
        total = count_result.count if hasattr(count_result, 'count') else 0
        
        result = query.order("created_at", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()
        tutorials = result.data
    
    total_pages = (total + limit - 1) // limit if total > 0 else 1
    
    return templates.TemplateResponse(
        "tutorials.html",
        {
            "request": request,
            "current_user": current_user,
            "tutorials": tutorials,
            "selected_category": category,
            "search_query": search,
            "page": page,
            "total_pages": total_pages,
            "title": "Tutorials" + (f" - Search: {search}" if search else "")
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

# ==================== Tutorials =========================

@web_router.get("/tutorials/{tutorial_id}", response_class=HTMLResponse)
async def tutorial_detail(
    request: Request,
    tutorial_id: str,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: Optional[dict] = Depends(get_current_user_from_cookie)
):
    """Tutorial detail page"""
    supabase = get_supabase_client()
    
    # Get tutorial details
    tutorial_result = supabase.table("tutorials")\
        .select("*, users(full_name, avatar_url, bio)")\
        .eq("id", tutorial_id)\
        .execute()
    
    if not tutorial_result.data:
        return templates.TemplateResponse(
            "404.html",
            {"request": request, "title": "Tutorial Not Found"},
            status_code=404
        )
    
    tutorial = tutorial_result.data[0]
    
    # Increment view count
    supabase.table("tutorials")\
        .update({"view_count": tutorial["view_count"] + 1})\
        .eq("id", tutorial_id)\
        .execute()
    
    # Get related tutorials (same category/difficulty)
    related = supabase.table("tutorials")\
        .select("*")\
        .eq("category", tutorial["category"])\
        .neq("id", tutorial_id)\
        .limit(3)\
        .execute()
    
    return templates.TemplateResponse(
        "tutorial_detail.html",
        {
            "request": request,
            "current_user": current_user,
            "tutorial": tutorial,
            "related_tutorials": related.data or [],
            "title": tutorial["title"]
        }
    )

# =================== Events =============================

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
            "title": "Events & Webinars"
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

# =================== Admin =============================

@web_router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: dict = Depends(get_current_admin)
):
    """Admin dashboard"""
    supabase = get_supabase_client()
    
    # Get statistics
    # Total users
    total_users_result = supabase.table("users").select("*", count="exact").execute()
    total_users = total_users_result.count if hasattr(total_users_result, 'count') else 0
    
    # Total instructors
    total_instructors_result = supabase.table("users")\
        .select("*", count="exact")\
        .eq("is_instructor", True)\
        .execute()
    total_instructors = total_instructors_result.count if hasattr(total_instructors_result, 'count') else 0
    
    # Total students (users who are not instructors and not admins)
    total_students_result = supabase.table("users")\
        .select("*", count="exact")\
        .eq("is_instructor", False)\
        .eq("is_admin", False)\
        .execute()
    total_students = total_students_result.count if hasattr(total_students_result, 'count') else 0
    
    # Total courses
    total_courses_result = supabase.table("courses").select("*", count="exact").execute()
    total_courses = total_courses_result.count if hasattr(total_courses_result, 'count') else 0
    
    # Get pending instructor applications
    pending_instructors = supabase.table("instructor_applications")\
        .select("*")\
        .eq("status", "pending")\
        .execute()
    
    # Get pending courses (unpublished)
    pending_courses = supabase.table("courses")\
        .select("*, users(full_name)")\
        .eq("is_published", False)\
        .execute()
    
    # Add instructor names to pending courses
    for course in pending_courses.data:
        course["instructor_name"] = course.get("users", {}).get("full_name", "Unknown")
    
    # Get recent users (last 5)
    recent_users = supabase.table("users")\
        .select("*")\
        .order("created_at", desc=True)\
        .limit(5)\
        .execute()
    
    # Get recent courses (last 5)
    recent_courses = supabase.table("courses")\
        .select("*, users(full_name)")\
        .order("created_at", desc=True)\
        .limit(5)\
        .execute()
    
    # Calculate revenue data for chart (example - you can replace with actual data)
    revenue_data = [12000, 19000, 15000, 25000, 22000, 30000]
    
    # Calculate category distribution for chart
    categories = ['Programming', 'Robotics', 'Artificial Intelligence', 'Machine Learning', 'Networking', 'Cyber Security']
    category_counts = []
    for category in categories:
        count = supabase.table("courses")\
            .select("*", count="exact")\
            .eq("category", category)\
            .execute()
        category_counts.append(count.count if hasattr(count, 'count') else 0)
    
    print(f"{total_users} | {total_instructors} | {total_students}| {total_courses}")

    return templates.TemplateResponse(
        "dashboard/admin.html",
        {
            "request": request,
            "current_user": current_user,
            "total_users": total_users,
            "total_instructors": total_instructors,
            "total_students": total_students,
            "total_courses": total_courses,
            "pending_instructors": pending_instructors.data,
            "pending_courses": pending_courses.data,
            "revenue_data": revenue_data,
            "category_labels": categories,
            "category_data": category_counts,
            "title": "Admin Dashboard"
        }
    )

@web_router.get("/admin/users", response_class=HTMLResponse)
async def admin_users_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: dict = Depends(get_current_admin)
):
    """Admin users management page"""
    supabase = get_supabase_client()
    
    # Get all users
    users = supabase.table("users")\
        .select("*")\
        .order("created_at", desc=True)\
        .execute()
    
    return templates.TemplateResponse(
        "admin/users.html",
        {
            "request": request,
            "current_user": current_user,
            "users": users.data,
            "title": "Manage Users"
        }
    )

@web_router.get("/admin/courses", response_class=HTMLResponse)
async def admin_courses_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: dict = Depends(get_current_admin)
):
    """Admin courses management page"""
    supabase = get_supabase_client()
    
    # Get all courses with instructor info
    courses = supabase.table("courses")\
        .select("*, users(full_name)")\
        .order("created_at", desc=True)\
        .execute()
    
    for course in courses.data:
        course["instructor_name"] = course.get("users", {}).get("full_name", "Unknown")
        
        # Get student count
        enrollments = supabase.table("enrollments")\
            .select("id", count="exact")\
            .eq("course_id", course["id"])\
            .execute()
        course["student_count"] = enrollments.count if hasattr(enrollments, 'count') else 0
    
    return templates.TemplateResponse(
        "admin/courses.html",
        {
            "request": request,
            "current_user": current_user,
            "courses": courses.data,
            "title": "Manage Courses"
        }
    )

@web_router.get("/admin/settings", response_class=HTMLResponse)
async def admin_settings_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: dict = Depends(get_current_admin)
):
    """Admin settings page"""
    return templates.TemplateResponse(
        "admin/settings.html",
        {
            "request": request,
            "current_user": current_user,
            "title": "Admin Settings"
        }
    )

@web_router.get("/admin/invitations", response_class=HTMLResponse)
async def admin_invitations_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: dict = Depends(get_current_admin)
):
    """Admin invitations page"""
    return templates.TemplateResponse(
        "admin/invitations.html",
        {
            "request": request,
            "current_user": current_user,
            "title": "Instructor Invitations"
        }
    )

@web_router.get("/admin/reports", response_class=HTMLResponse)
async def admin_reports_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: dict = Depends(get_current_admin)
):
    """Admin reports page"""
    return templates.TemplateResponse(
        "admin/reports.html",
        {
            "request": request,
            "current_user": current_user,
            "title": "Reports"
        }
    )


# =================== VPL ===============================

@web_router.get("/vpl/assignment/{assignment_id}", response_class=HTMLResponse)
async def vpl_assignment_page(
    request: Request,
    assignment_id: str,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: dict = Depends(get_current_active_user)
):
    """VPL assignment page for students"""
    supabase = get_supabase_client()
    
    # Get assignment details
    assignment = supabase.table("programming_assignments")\
        .select("*")\
        .eq("id", assignment_id)\
        .execute()
    
    if not assignment.data:
        return templates.TemplateResponse(
            "404.html",
            {"request": request, "title": "Assignment Not Found"},
            status_code=404
        )
    
    assignment_data = assignment.data[0]
    course_id = assignment_data["course_id"]
    
    # Check if student is enrolled
    enrollment = supabase.table("enrollments")\
        .select("*")\
        .eq("user_id", current_user["id"])\
        .eq("course_id", course_id)\
        .execute()
    
    if not enrollment.data:
        return templates.TemplateResponse(
            "403.html",
            {"request": request, "title": "Access Denied"},
            status_code=403
        )
    
    # Get existing submission
    submission = supabase.table("code_submissions")\
        .select("*")\
        .eq("assignment_id", assignment_id)\
        .eq("user_id", current_user["id"])\
        .order("submitted_at", desc=True)\
        .limit(1)\
        .execute()
    
    saved_code = submission.data[0]["code"] if submission.data else None
    
    return templates.TemplateResponse(
        "courses/vpl_assignment.html",
        {
            "request": request,
            "current_user": current_user,
            "assignment": assignment_data,
            "saved_code": saved_code,
            "title": assignment_data["title"]
        }
    )

@web_router.get("/vpl/assignment/{assignment_id}/review", response_class=HTMLResponse)
async def vpl_assignment_review(
    request: Request,
    assignment_id: str,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: dict = Depends(get_current_active_user)
):
    """Review page for completed assignment"""
    supabase = get_supabase_client()
    
    # Get assignment details
    assignment = supabase.table("programming_assignments")\
        .select("*")\
        .eq("id", assignment_id)\
        .execute()
    
    if not assignment.data:
        return templates.TemplateResponse(
            "404.html",
            {"request": request, "title": "Assignment Not Found"},
            status_code=404
        )
    
    assignment_data = assignment.data[0]
    course_id = assignment_data["course_id"]
    
    # Check if student is enrolled
    enrollment = supabase.table("enrollments")\
        .select("*")\
        .eq("user_id", current_user["id"])\
        .eq("course_id", course_id)\
        .execute()
    
    if not enrollment.data:
        return templates.TemplateResponse(
            "403.html",
            {"request": request, "title": "Access Denied"},
            status_code=403
        )
    
    # Get latest submission
    submission = supabase.table("code_submissions")\
        .select("*")\
        .eq("assignment_id", assignment_id)\
        .eq("user_id", current_user["id"])\
        .order("submitted_at", desc=True)\
        .limit(1)\
        .execute()
    
    if not submission.data:
        return RedirectResponse(url=f"/vpl/assignment/{assignment_id}", status_code=302)
    
    return templates.TemplateResponse(
        "courses/vpl_review.html",
        {
            "request": request,
            "current_user": current_user,
            "assignment": assignment_data,
            "submission": submission.data[0],
            "title": f"Review: {assignment_data['title']}"
        }
    )

@web_router.get("/playground", response_class=HTMLResponse)
async def vpl_playground(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: dict = Depends(get_current_active_user)
):
    """VPL Playground page for practicing coding"""
    return templates.TemplateResponse(
        "vpl/playground.html",
        {
            "request": request,
            "current_user": current_user,
            "title": "VPL Playground - Practice Coding"
        }
    )


