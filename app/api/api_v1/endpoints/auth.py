from datetime import timedelta
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse

from app.core.supabase_client import get_supabase
from app.core.config import settings
from app.schemas.user import User, UserCreate, Token, InstructorRegister
from app.schemas.invitation import InvitationVerify, InvitationResponse
from app.services.auth_service import AuthService
from app.services.invitation_service import InvitationService
from app.api.api_v1.dependencies import get_current_user

router = APIRouter()

@router.post("/register/student", response_model=dict)
async def register_student(
    *,
    supabase=Depends(get_supabase),
    user_in: UserCreate
) -> Any:
    """
    Register a new student (no invitation code required).
    """
    try:
        auth_service = AuthService(supabase)
        result = await auth_service.register_user(
            email=user_in.email,
            password=user_in.password,
            user_data={
                "full_name": user_in.full_name,
                "username": user_in.username,
                "role": "student"
            }
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return {
            "message": "Student registered successfully",
            "user": {
                "id": result["user"].id,
                "email": result["user"].email,
                "username": user_in.username
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/register/instructor", response_model=dict)
async def register_instructor(
    *,
    supabase=Depends(get_supabase),
    user_in: InstructorRegister
) -> Any:
    """
    Register a new instructor (requires valid invitation code).
    """
    try:
        invitation_service = InvitationService(supabase)
        auth_service = AuthService(supabase)
        
        # Verify invitation code
        verification = await invitation_service.verify_invitation(
            email=user_in.email,
            code=user_in.invitation_code
        )
        
        if not verification["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=verification["message"]
            )
        
        invitation = verification["invitation"]
        
        # Register user (as student first)
        result = await auth_service.register_user(
            email=user_in.email,
            password=user_in.password,
            user_data={
                "full_name": user_in.full_name,
                "username": user_in.username,
                "role": "student"  # Register as student first
            }
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        # Create instructor application
        application_data = {
            "user_id": result["user"].id,
            "email": user_in.email,
            "full_name": user_in.full_name,
            "username": user_in.username,
            "expertise": user_in.expertise,
            "experience": user_in.experience,
            "status": "pending"
        }
        
        supabase.table("instructor_applications").insert(application_data).execute()
        
        # Mark invitation as used
        await invitation_service.mark_invitation_used(invitation["id"])
        
        return {
            "message": "Instructor application submitted successfully. Our team will review your application.",
            "user": {
                "id": result["user"].id,
                "email": result["user"].email,
                "username": user_in.username
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/verify-invitation", response_model=InvitationResponse)
async def verify_invitation(
    *,
    supabase=Depends(get_supabase),
    data: InvitationVerify
) -> Any:
    """
    Verify if an invitation code is valid.
    """
    invitation_service = InvitationService(supabase)
    verification = await invitation_service.verify_invitation(
        email=data.email,
        code=data.code
    )
    
    if verification["valid"]:
        invitation = verification["invitation"]
        return InvitationResponse(
            message="Invitation code is valid",
            valid=True,
            email=invitation["email"],
            full_name=invitation["full_name"],
            username=invitation["username"]
        )
    else:
        return InvitationResponse(
            message=verification["message"],
            valid=False
        )

@router.post("/login", response_model=Token)
async def login(
    *,
    supabase=Depends(get_supabase),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    Login with email and password.
    """
    try:
        # Authenticate with Supabase
        auth_response = supabase.auth.sign_in_with_password({
            "email": form_data.username,
            "password": form_data.password
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
    *,
    supabase=Depends(get_supabase),
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Get current authenticated user.
    """
    return current_user

@router.post("/logout")
async def logout(
    *,
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

# New endpoints for additional login methods

@router.post("/magic-link")
async def send_magic_link(
    *,
    supabase=Depends(get_supabase),
    email: str
) -> Any:
    """
    Send a magic link email for passwordless login.
    """
    try:
        # Use Supabase magic link
        supabase.auth.sign_in_with_otp({
            "email": email,
            "options": {
                "email_redirect_to": "http://localhost:8000/api/v1/auth/confirm"
            }
        })
        
        return {"message": "Magic link sent successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/request-otp")
async def request_otp(
    *,
    supabase=Depends(get_supabase),
    email: str
) -> Any:
    """
    Request a one-time password (OTP) for login.
    """
    try:
        # Generate and send OTP
        supabase.auth.sign_in_with_otp({
            "email": email
        })
        
        return {"message": "OTP sent successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/verify-otp")
async def verify_otp(
    *,
    supabase=Depends(get_supabase),
    email: str,
    otp: str
) -> Any:
    """
    Verify OTP and login.
    """
    try:
        # Verify OTP with Supabase
        response = supabase.auth.verify_otp({
            "email": email,
            "token": otp,
            "type": "email"
        })
        
        if response.session:
            return {
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
                "token_type": "bearer"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid OTP"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/forgot-password")
async def forgot_password(
    *,
    supabase=Depends(get_supabase),
    email: str
) -> Any:
    """
    Send password reset email.
    """
    try:
        supabase.auth.reset_password_for_email(
            email,
            {
                "redirect_to": "http://localhost:8000/reset-password"
            }
        )
        
        return {"message": "Password reset email sent"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/reset-password")
async def reset_password(
    *,
    supabase=Depends(get_supabase),
    token: str,
    new_password: str
) -> Any:
    """
    Reset password with token.
    """
    try:
        # First, verify the token by getting the user
        user = supabase.auth.get_user(token)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired token"
            )
        
        # Update the password
        supabase.auth.update_user({
            "password": new_password
        })
        
        return {"message": "Password updated successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
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