from app.schemas.invitation import Invitation, InvitationCreate
from app.services.invitation_service import InvitationService
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from app.core.supabase_client import get_supabase
from app.api.api_v1.dependencies import get_current_admin
from app.schemas.user import User

router = APIRouter()

@router.get("/users")
async def get_users(
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

@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    request: Request,
    supabase=Depends(get_supabase),
    admin: dict = Depends(get_current_admin)
) -> dict:
    """Update user role"""
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

@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    request: Request,
    supabase=Depends(get_supabase),
    admin: dict = Depends(get_current_admin)
) -> dict:
    """Update user active status"""
    data = await request.json()
    is_active = data.get("is_active", True)
    
    # Note: This updates the profile status, not the auth user
    # You might need additional logic to disable auth user
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

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    supabase=Depends(get_supabase),
    admin: dict = Depends(get_current_admin)
) -> dict:
    """Delete a user"""
    # First delete from auth.users (requires admin API)
    # This is simplified - you'd need to use the admin API
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

@router.get("/users/export")
async def export_users(
    supabase=Depends(get_supabase),
    admin: dict = Depends(get_current_admin)
):
    """Export users as CSV"""
    result = supabase.table("users")\
        .select("*")\
        .execute()
    
    import csv
    from io import StringIO
    from fastapi.responses import StreamingResponse
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Write headers
    if result.data:
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

@router.post("/invitations", response_model=Invitation)
async def create_invitation(
    *,
    supabase=Depends(get_supabase),
    invitation_in: InvitationCreate,
    admin: dict = Depends(get_current_admin)
) -> Any:
    """
    Create a new instructor invitation (admin only).
    """
    invitation_service = InvitationService(supabase)
    
    invitation = await invitation_service.create_invitation(
        email=invitation_in.email,
        full_name=invitation_in.full_name,
        username=invitation_in.username,
        admin_id=admin["id"]
    )
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create invitation"
        )
    
    return invitation

@router.get("/invitations", response_model=List[Invitation])
async def get_invitations(
    *,
    supabase=Depends(get_supabase),
    admin: dict = Depends(get_current_admin)
) -> Any:
    """
    Get all invitations (admin only).
    """
    invitation_service = InvitationService(supabase)
    invitations = await invitation_service.get_invitations()
    return invitations

@router.get("/invitations/pending", response_model=List[Invitation])
async def get_pending_invitations(
    *,
    supabase=Depends(get_supabase),
    admin: dict = Depends(get_current_admin)
) -> Any:
    """
    Get all pending invitations (admin only).
    """
    invitation_service = InvitationService(supabase)
    invitations = await invitation_service.get_invitations()
    # Filter pending invitations
    pending = [inv for inv in invitations if not inv["is_used"]]
    return pending