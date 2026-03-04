from datetime import timedelta
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse

from app.core.supabase_client import get_supabase
from app.core.config import settings
from app.schemas.user import User, Token
from app.schemas.invitation import InvitationVerify, InvitationResponse
from app.api.api_v1.dependencies import get_current_user

router = APIRouter()

@router.post("/register/student", response_model=dict)
async def register_student(
    request: Request,
    supabase=Depends(get_supabase)
) -> Any:
    """
    Register a new student (no invitation code required).
    The database trigger will automatically create the user profile.
    """
    try:
        # Parse request body
        body = await request.json()
        email = body.get("email")
        password = body.get("password")
        username = body.get("username")
        full_name = body.get("full_name")
        
        # Validate input
        if not all([email, password, username, full_name]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required fields"
            )
        
        # Register with Supabase Auth
        # The database trigger will automatically create the profile
        auth_response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "full_name": full_name,
                    "username": username
                }
            }
        })
        
        if not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed"
            )
        
        return {
            "message": "Student registered successfully",
            "user": {
                "id": auth_response.user.id,
                "email": email,
                "username": username,
                "full_name": full_name
            }
        }
        
    except Exception as e:
        print(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/register/instructor", response_model=dict)
async def register_instructor(
    request: Request,
    supabase=Depends(get_supabase)
) -> Any:
    """
    Register a new instructor (requires valid invitation code).
    """
    try:
        # Parse request body
        body = await request.json()
        email = body.get("email")
        password = body.get("password")
        username = body.get("username")
        full_name = body.get("full_name")
        invitation_code = body.get("invitation_code")
        expertise = body.get("expertise", "")
        experience = body.get("experience", "")
        
        # Validate input
        if not all([email, password, username, full_name, invitation_code]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required fields"
            )
        
        # Verify invitation code
        invitation_result = supabase.table("invitations")\
            .select("*")\
            .eq("email", email)\
            .eq("code", invitation_code)\
            .eq("is_used", False)\
            .execute()
        
        if not invitation_result.data or len(invitation_result.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired invitation code"
            )
        
        invitation = invitation_result.data[0]
        
        # Register with Supabase Auth
        # The trigger will create the profile, but we'll update it with instructor data
        auth_response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "full_name": full_name,
                    "username": username,
                    "is_instructor": True,
                    "expertise": expertise,
                    "experience": experience
                }
            }
        })
        
        if not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed"
            )
        
        # Mark invitation as used
        supabase.table("invitations")\
            .update({"is_used": True, "used_at": "now()"})\
            .eq("id", invitation["id"])\
            .execute()
        
        return {
            "message": "Instructor registered successfully",
            "user": {
                "id": auth_response.user.id,
                "email": email,
                "username": username,
                "full_name": full_name
            }
        }
        
    except Exception as e:
        print(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    supabase=Depends(get_supabase)
) -> Any:
    """
    Login with email and password.
    """
    try:
        # Parse form data
        form_data = await request.form()
        email = form_data.get("username")
        password = form_data.get("password")
        
        # Authenticate with Supabase
        auth_response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if hasattr(auth_response, 'session') and auth_response.session:
            return {
                "access_token": auth_response.session.access_token,
                "refresh_token": auth_response.session.refresh_token,
                "token_type": "bearer"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )


@router.get("/me", response_model=User)
async def get_current_user(
    supabase=Depends(get_supabase),
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Get current authenticated user.
    """
    return current_user


@router.post("/logout")
async def logout(
    supabase=Depends(get_supabase),
) -> Any:
    """
    Logout user.
    """
    try:
        supabase.auth.sign_out()
        return {"message": "Logged out successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/verify-invitation", response_model=InvitationResponse)
async def verify_invitation(
    request: Request,
    supabase=Depends(get_supabase)
) -> Any:
    """
    Verify if an invitation code is valid.
    """
    try:
        body = await request.json()
        email = body.get("email")
        code = body.get("code")
        
        result = supabase.table("invitations")\
            .select("*")\
            .eq("email", email)\
            .eq("code", code)\
            .eq("is_used", False)\
            .execute()
        
        if result.data and len(result.data) > 0:
            invitation = result.data[0]
            return InvitationResponse(
                message="Invitation code is valid",
                valid=True,
                email=invitation["email"],
                full_name=invitation["full_name"],
                username=invitation["username"]
            )
        else:
            return InvitationResponse(
                message="Invalid or expired invitation code",
                valid=False
            )
            
    except Exception as e:
        return InvitationResponse(
            message=f"Error verifying code: {str(e)}",
            valid=False
        )


# Social Login Redirects
@router.get("/google")
async def google_login():
    """Redirect to Google OAuth"""
    return RedirectResponse(url=f"{settings.SUPABASE_URL}/auth/v1/authorize?provider=google")


@router.get("/facebook")
async def facebook_login():
    """Redirect to Facebook OAuth"""
    return RedirectResponse(url=f"{settings.SUPABASE_URL}/auth/v1/authorize?provider=facebook")


@router.get("/github")
async def github_login():
    """Redirect to GitHub OAuth"""
    return RedirectResponse(url=f"{settings.SUPABASE_URL}/auth/v1/authorize?provider=github")


@router.get("/confirm")
async def confirm_redirect(
    request: Request,
    access_token: Optional[str] = None,
    refresh_token: Optional[str] = None
):
    """Handle OAuth and magic link redirects"""
    if access_token:
        response = RedirectResponse(url="/dashboard")
        response.set_cookie(
            key="access_token",
            value=access_token,
            max_age=3600,
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax"
        )
        return response
    
    return RedirectResponse(url="/login?error=authentication_failed")