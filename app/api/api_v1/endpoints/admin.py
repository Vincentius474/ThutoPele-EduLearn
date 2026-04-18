from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.responses import StreamingResponse
from app.core.supabase_client import get_supabase
from app.api.api_v1.dependencies import get_current_admin
import csv
import io
from datetime import datetime

router = APIRouter()

# ==================== USER MANAGEMENT ====================

@router.get("/admin/users")
async def get_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    supabase=Depends(get_supabase),
    admin: dict = Depends(get_current_admin)
) -> List[dict]:
    """Get all users with pagination"""
    result = supabase.table("users")\
        .select("*")\
        .range(skip, skip + limit - 1)\
        .order("created_at", desc=True)\
        .execute()
    
    return result.data

@router.put("/admin/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    request: Request,
    supabase=Depends(get_supabase),
    admin: dict = Depends(get_current_admin)
) -> dict:
    """Update user role (student/instructor/admin)"""
    data = await request.json()
    role = data.get("role")
    
    update_data = {
        "is_instructor": role == "instructor",
        "is_admin": role == "admin",
        "updated_at": "now()"
    }
    
    result = supabase.table("users")\
        .update(update_data)\
        .eq("id", user_id)\
        .execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": "User role updated"}

@router.put("/admin/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    request: Request,
    supabase=Depends(get_supabase),
    admin: dict = Depends(get_current_admin)
) -> dict:
    """Update user active status"""
    data = await request.json()
    is_active = data.get("is_active", True)
    
    # Note: This updates the profile status
    result = supabase.table("users")\
        .update({"is_active": is_active, "updated_at": "now()"})\
        .eq("id", user_id)\
        .execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": "User status updated"}

@router.delete("/admin/users/{user_id}")
async def delete_user(
    user_id: str,
    supabase=Depends(get_supabase),
    admin: dict = Depends(get_current_admin)
) -> dict:
    """Delete a user"""
    result = supabase.table("users")\
        .delete()\
        .eq("id", user_id)\
        .execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": "User deleted successfully"}

@router.get("/admin/users/export")
async def export_users(
    supabase=Depends(get_supabase),
    admin: dict = Depends(get_current_admin)
):
    """Export users as CSV"""
    result = supabase.table("users")\
        .select("*")\
        .execute()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    if result.data:
        # Write headers
        writer.writerow(result.data[0].keys())
        
        # Write data
        for user in result.data:
            writer.writerow(user.values())
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=users.csv"}
    )

# ==================== COURSE MANAGEMENT ====================

@router.get("/admin/courses")
async def get_all_courses(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    supabase=Depends(get_supabase),
    admin: dict = Depends(get_current_admin)
) -> List[dict]:
    """Get all courses with pagination and instructor info"""
    result = supabase.table("courses")\
        .select("*, users(full_name)")\
        .range(skip, skip + limit - 1)\
        .order("created_at", desc=True)\
        .execute()
    
    courses = []
    for course in result.data:
        # Get student count
        enrollments = supabase.table("enrollments")\
            .select("id", count="exact")\
            .eq("course_id", course["id"])\
            .execute()
        
        course["student_count"] = enrollments.count if hasattr(enrollments, 'count') else 0
        course["instructor_name"] = course.get("users", {}).get("full_name", "Unknown")
        courses.append(course)
    
    return courses

@router.delete("/admin/courses/{course_id}")
async def delete_course(
    course_id: str,
    supabase=Depends(get_supabase),
    admin: dict = Depends(get_current_admin)
) -> dict:
    """Delete a course"""
    result = supabase.table("courses")\
        .delete()\
        .eq("id", course_id)\
        .execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    return {"message": "Course deleted successfully"}

@router.put("/admin/courses/{course_id}/approve")
async def approve_course(
    course_id: str,
    supabase=Depends(get_supabase),
    admin: dict = Depends(get_current_admin)
) -> dict:
    """Approve and publish a course"""
    result = supabase.table("courses")\
        .update({"is_published": True, "updated_at": "now()"})\
        .eq("id", course_id)\
        .execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    return {"message": "Course approved and published"}

# ==================== INSTRUCTOR APPROVALS ====================

@router.get("/admin/instructors/pending")
async def get_pending_instructors(
    supabase=Depends(get_supabase),
    admin: dict = Depends(get_current_admin)
) -> List[dict]:
    """Get pending instructor applications"""
    result = supabase.table("instructor_applications")\
        .select("*")\
        .eq("status", "pending")\
        .order("created_at", desc=True)\
        .execute()
    
    return result.data

@router.post("/admin/instructors/{application_id}/approve")
async def approve_instructor(
    application_id: str,
    supabase=Depends(get_supabase),
    admin: dict = Depends(get_current_admin)
) -> dict:
    """Approve an instructor application"""
    # Get application
    application = supabase.table("instructor_applications")\
        .select("*")\
        .eq("id", application_id)\
        .execute()
    
    if not application.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    # Update user to be instructor
    supabase.table("users")\
        .update({"is_instructor": True, "updated_at": "now()"})\
        .eq("id", application.data[0]["user_id"])\
        .execute()
    
    # Update application status
    supabase.table("instructor_applications")\
        .update({
            "status": "approved",
            "reviewed_by": admin["id"],
            "reviewed_at": "now()"
        })\
        .eq("id", application_id)\
        .execute()
    
    return {"message": "Instructor approved"}

@router.post("/admin/instructors/{application_id}/reject")
async def reject_instructor(
    application_id: str,
    supabase=Depends(get_supabase),
    admin: dict = Depends(get_current_admin)
) -> dict:
    """Reject an instructor application"""
    result = supabase.table("instructor_applications")\
        .update({
            "status": "rejected",
            "reviewed_by": admin["id"],
            "reviewed_at": "now()"
        })\
        .eq("id", application_id)\
        .execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    return {"message": "Instructor application rejected"}

# ==================== COURSE REVIEWS ====================

@router.get("/admin/courses/pending")
async def get_pending_courses(
    supabase=Depends(get_supabase),
    admin: dict = Depends(get_current_admin)
) -> List[dict]:
    """Get pending course reviews (unpublished courses)"""
    result = supabase.table("courses")\
        .select("*, users(full_name)")\
        .eq("is_published", False)\
        .order("created_at", desc=True)\
        .execute()
    
    courses = []
    for course in result.data:
        course["instructor_name"] = course.get("users", {}).get("full_name", "Unknown")
        courses.append(course)
    
    return courses

@router.post("/admin/courses/{course_id}/review")
async def review_course(
    course_id: str,
    request: Request,
    supabase=Depends(get_supabase),
    admin: dict = Depends(get_current_admin)
) -> dict:
    """Add review notes to a course"""
    data = await request.json()
    notes = data.get("notes", "")
    
    result = supabase.table("courses")\
        .update({"admin_notes": notes, "updated_at": "now()"})\
        .eq("id", course_id)\
        .execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    return {"message": "Review notes added"}

@router.post("/admin/courses/{course_id}/reject")
async def reject_course(
    course_id: str,
    supabase=Depends(get_supabase),
    admin: dict = Depends(get_current_admin)
) -> dict:
    """Reject a course"""
    result = supabase.table("courses")\
        .delete()\
        .eq("id", course_id)\
        .execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    return {"message": "Course rejected and deleted"}