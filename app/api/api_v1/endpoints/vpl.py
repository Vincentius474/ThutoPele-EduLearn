# app/api/api_v1/endpoints/vpl.py
from fastapi import APIRouter, Depends, HTTPException, Request, status
from httpx import Client
from app.api.api_v1.dependencies import get_current_active_user
from app.core.supabase_client import get_supabase
from app.services.vpl_service import VPLService

router = APIRouter()

@router.post("/vpl/execute")
async def execute_code(
    request: Request,
    current_user: dict = Depends(get_current_active_user)  # Only authenticated users
):
    """
    Execute code in VPL sandbox (restricted to authenticated users only)
    """
    # Get course and assignment IDs to verify enrollment
    # Forward request to VPL jail server
    # Return execution results

# app/api/api_v1/endpoints/vpl.py (continued)
@router.post("/assignments/{assignment_id}/submit")
async def submit_code_assignment(
    assignment_id: str,
    request: Request,
    current_user: dict = Depends(get_current_active_user),
    supabase: Client = Depends(get_supabase)
):
    """Submit code for programming assignment"""
    data = await request.json()
    code = data.get("code")
    language = data.get("language", "python")
    
    # Verify enrollment
    assignment = supabase.table("programming_assignments")\
        .select("*, courses(instructor_id)")\
        .eq("id", assignment_id)\
        .execute()
    
    if not assignment.data:
        raise HTTPException(404, "Assignment not found")
    
    course_id = assignment.data[0]["course_id"]
    
    enrollment = supabase.table("enrollments")\
        .select("*")\
        .eq("user_id", current_user["id"])\
        .eq("course_id", course_id)\
        .execute()
    
    if not enrollment.data:
        raise HTTPException(403, "Not enrolled in this course")
    
    # Execute code in VPL
    vpl_service = VPLService()
    test_results = await vpl_service.run_tests(
        code=code,
        language=language,
        test_cases=assignment.data[0].get("test_cases", [])
    )
    
    # Save submission
    submission = supabase.table("code_submissions").insert({
        "assignment_id": assignment_id,
        "user_id": current_user["id"],
        "code": code,
        "programming_language": language,
        "execution_output": test_results,
        "score": test_results["score"],
        "submitted_at": "now()"
    }).execute()
    
    return {
        "message": "Code submitted successfully",
        "score": test_results["score"],
        "passed_tests": test_results["passed"],
        "total_tests": test_results["total"],
        "test_results": test_results["results"]
    }