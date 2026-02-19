from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.supabase_client import get_supabase
from app.schemas.invitation import Invitation, InvitationCreate
from app.services.invitation_service import InvitationService
from app.api.api_v1.dependencies import get_current_admin

router = APIRouter()

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