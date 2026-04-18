from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.responses import StreamingResponse
from app.core.supabase_client import get_supabase
from app.api.api_v1.dependencies import get_current_admin
import csv
import io
from datetime import datetime

router = APIRouter()

# ==================== DASHBOARD STATS ====================

@router.get("/stats")
async def get_admin_stats(
    supabase=Depends(get_supabase),
    admin: dict = Depends(get_current_admin)
) -> dict:
    """Get dashboard statistics"""
    # Get total users
    total_users = supabase.table("users").select("*", count="exact").execute()
    
    # Get total instructors
    total_instructors = supabase.table("users")\
        .select("*", count="exact")\
        .eq("is_instructor", True)\
        .execute()
    
    # Get total students
    total_students = supabase.table("users")\
        .select("*", count="exact")\
        .eq("is_instructor", False)\
        .eq("is_admin", False)\
        .execute()
    
    # Get total courses
    total_courses = supabase.table("courses").select("*", count="exact").execute()
    
    # Get pending instructor applications
    pending_instructors = supabase.table("instructor_applications")\
        .select("*", count="exact")\
        .eq("status", "pending")\
        .execute()
    
    # Get pending course reviews
    pending_courses = supabase.table("courses")\
        .select("*", count="exact")\
        .eq("is_published", False)\
        .execute()
    
    return {
        "total_users": total_users.count if hasattr(total_users, 'count') else 0,
        "total_instructors": total_instructors.count if hasattr(total_instructors, 'count') else 0,
        "total_students": total_students.count if hasattr(total_students, 'count') else 0,
        "total_courses": total_courses.count if hasattr(total_courses, 'count') else 0,
        "pending_instructors": pending_instructors.count if hasattr(pending_instructors, 'count') else 0,
        "pending_courses": pending_courses.count if hasattr(pending_courses, 'count') else 0
    }

# ==================== USER MANAGEMENT ====================

@router.get("/users")
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
    
    # Add default is_active if not present
    for user in result.data:
        if 'is_active' not in user:
            user['is_active'] = True
    
    return result.data

@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    request: Request,
    supabase=Depends(get_supabase),
    admin: dict = Depends(get_current_admin)
) -> dict:
    """Update user role (student/instructor/admin)"""
    try:
        data = await request.json()
        role = data.get("role")
        
        print(f"Updating user {user_id} role to: {role}")
        
        # First, check if user exists
        user_check = supabase.table("users")\
            .select("id")\
            .eq("id", user_id)\
            .execute()
        
        if not user_check.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Prepare update data based on role
        update_data = {
            "is_instructor": role == "instructor",
            "is_admin": role == "admin",
            "updated_at": "now()"
        }
        
        # If setting to student, ensure both flags are false
        if role == "student":
            update_data["is_instructor"] = False
            update_data["is_admin"] = False
        
        # Use service client to bypass RLS for admin operations
        from app.core.supabase_client import supabase as supabase_client
        service_client = supabase_client.get_service_client()
        
        result = service_client.table("users")\
            .update(update_data)\
            .eq("id", user_id)\
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update user role"
            )
        
        return {"message": f"User role updated to {role} successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating user role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user role: {str(e)}"
        )

@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    request: Request,
    supabase=Depends(get_supabase),
    admin: dict = Depends(get_current_admin)
) -> dict:
    """Update user active status"""
    try:
        data = await request.json()
        is_active = data.get("is_active", True)
        
        print(f"Updating user {user_id} status to: {is_active}")
        
        # First, check if user exists
        user_check = supabase.table("users")\
            .select("id")\
            .eq("id", user_id)\
            .execute()
        
        if not user_check.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Use service client to bypass RLS for admin operations
        from app.core.supabase_client import supabase as supabase_client
        service_client = supabase_client.get_service_client()
        
        result = service_client.table("users")\
            .update({"is_active": is_active, "updated_at": "now()"})\
            .eq("id", user_id)\
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update user status"
            )
        
        return {"message": f"User status updated to {'active' if is_active else 'inactive'} successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating user status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user status: {str(e)}"
        )

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    supabase=Depends(get_supabase),
    admin: dict = Depends(get_current_admin)
) -> dict:
    """Delete a user"""
    try:
        print(f"Deleting user: {user_id}")
        
        # First, check if user exists
        user_check = supabase.table("users")\
            .select("id")\
            .eq("id", user_id)\
            .execute()
        
        if not user_check.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Use service client to bypass RLS for admin operations
        from app.core.supabase_client import supabase as supabase_client
        service_client = supabase_client.get_service_client()
        
        # Delete user from public.users
        result = service_client.table("users")\
            .delete()\
            .eq("id", user_id)\
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to delete user"
            )
        
        # Note: This doesn't delete from auth.users
        # You might want to also disable the auth user
        
        return {"message": "User deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting user: {str(e)}"
        )

@router.get("/users/export")
async def export_users(
    supabase=Depends(get_supabase),
    admin: dict = Depends(get_current_admin)
):
    """Export users as CSV"""
    try:
        result = supabase.table("users")\
            .select("*")\
            .execute()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        if result.data:
            # Write headers
            headers = ['ID', 'Email', 'Username', 'Full Name', 'Is Instructor', 'Is Admin', 'Created At']
            writer.writerow(headers)
            
            # Write data
            for user in result.data:
                writer.writerow([
                    user.get('id', ''),
                    user.get('email', ''),
                    user.get('username', ''),
                    user.get('full_name', ''),
                    user.get('is_instructor', False),
                    user.get('is_admin', False),
                    user.get('created_at', '')
                ])
        
        output.seek(0)
        
        return StreamingResponse(
            iter([output.getvalue().encode('utf-8')]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=users.csv"}
        )
        
    except Exception as e:
        print(f"Error exporting users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting users: {str(e)}"
        )

@router.get("/users/{user_id}")
async def get_user(
    user_id: str,
    supabase=Depends(get_supabase),
    admin: dict = Depends(get_current_admin)
) -> dict:
    """Get a single user by ID"""
    try:
        result = supabase.table("users")\
            .select("*")\
            .eq("id", user_id)\
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting user: {str(e)}"
        )

@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    request: Request,
    supabase=Depends(get_supabase),
    admin: dict = Depends(get_current_admin)
) -> dict:
    """Update a user's profile information"""
    try:
        data = await request.json()
        
        # Check if user exists
        user_check = supabase.table("users")\
            .select("id")\
            .eq("id", user_id)\
            .execute()
        
        if not user_check.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Prepare update data (only allow certain fields)
        update_data = {
            "full_name": data.get("full_name"),
            "username": data.get("username"),
            "bio": data.get("bio"),
            "avatar_url": data.get("avatar_url"),
            "expertise": data.get("expertise"),
            "experience": data.get("experience"),
            "updated_at": "now()"
        }
        
        # Remove None values
        update_data = {k: v for k, v in update_data.items() if v is not None}
        
        # Check if username is unique (excluding current user)
        if "username" in update_data:
            username_check = supabase.table("users")\
                .select("id")\
                .eq("username", update_data["username"])\
                .neq("id", user_id)\
                .execute()
            
            if username_check.data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
        
        # Use service client to bypass RLS for admin operations
        from app.core.supabase_client import supabase as supabase_client
        service_client = supabase_client.get_service_client()
        
        result = service_client.table("users")\
            .update(update_data)\
            .eq("id", user_id)\
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update user"
            )
        
        return {"message": "User updated successfully", "user": result.data[0]}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user: {str(e)}"
        )

# ==================== COURSE MANAGEMENT ====================

@router.get("/courses")
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

@router.delete("/courses/{course_id}")
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

@router.post("/courses/{course_id}/approve")
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

@router.get("/courses/export")
async def export_courses(
    supabase=Depends(get_supabase),
    admin: dict = Depends(get_current_admin)
):
    """Export courses as CSV"""
    result = supabase.table("courses")\
        .select("*, users(full_name)")\
        .execute()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    if result.data:
        # Write headers
        headers = ['id', 'title', 'description', 'category', 'level', 'price', 'is_published', 'instructor_name', 'created_at']
        writer.writerow(headers)
        
        # Write data
        for course in result.data:
            writer.writerow([
                course.get('id', ''),
                course.get('title', ''),
                course.get('description', ''),
                course.get('category', ''),
                course.get('level', ''),
                course.get('price', 0),
                course.get('is_published', False),
                course.get('users', {}).get('full_name', 'Unknown'),
                course.get('created_at', '')
            ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue().encode('utf-8')]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=courses.csv"}
    )

# ==================== INSTRUCTOR APPROVALS ====================

@router.get("/instructors/pending")
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

@router.post("/instructors/{application_id}/approve")
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

@router.post("/instructors/{application_id}/reject")
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

@router.get("/courses/pending")
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