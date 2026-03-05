from typing import Any, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import HTTPBearer

from app.core.supabase_client import get_supabase
from app.core.config import settings
from app.schemas.user import User, Token
from app.schemas.invitation import InvitationResponse
from app.api.api_v1.dependencies import get_current_user_from_cookie

router = APIRouter()
security = HTTPBearer()

# ==================== REGISTRATION ENDPOINTS ====================

@router.post("/register/student", response_model=dict)
async def register_student(
    request: Request,
    supabase=Depends(get_supabase)
) -> Any:
    """
    Register a new student (no invitation code required).
    """
    try:
        # Parse request body
        body = await request.json()
        email = body.get("email")
        password = body.get("password")
        username = body.get("username")
        full_name = body.get("full_name")
        
        print(f"Student registration attempt for: {email}")
        
        # Validate input
        if not all([email, password, username, full_name]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required fields: email, password, username, full_name"
            )
        
        # Register with Supabase Auth
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
                detail="Registration failed - no user returned"
            )
        
        print(f"User created successfully with ID: {auth_response.user.id}")
        
        return {
            "message": "Student registered successfully",
            "user": {
                "id": auth_response.user.id,
                "email": email,
                "username": username,
                "full_name": full_name
            }
        }
        
    except HTTPException:
        raise
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
        
        print(f"Instructor registration attempt for: {email}")
        
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
        
        print(f"Instructor created successfully with ID: {auth_response.user.id}")
        
        return {
            "message": "Instructor registered successfully",
            "user": {
                "id": auth_response.user.id,
                "email": email,
                "username": username,
                "full_name": full_name
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# ==================== LOGIN ENDPOINT ====================

@router.post("/login", response_model=Token)
async def login(
    request: Request,
    supabase=Depends(get_supabase)
) -> Any:
    """
    Login with email and password.
    """
    try:
        # Try to parse as JSON first
        try:
            data = await request.json()
            email = data.get("email") or data.get("username")
            password = data.get("password")
        except:
            # If not JSON, try form data
            form_data = await request.form()
            email = form_data.get("username") or form_data.get("email")
            password = form_data.get("password")
        
        if not email or not password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email and password are required"
            )
        
        # Authenticate with Supabase
        auth_response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if hasattr(auth_response, 'session') and auth_response.session:
            # Get user profile
            profile = supabase.table("users")\
                .select("*")\
                .eq("id", auth_response.user.id)\
                .execute()
            
            user_profile = profile.data[0] if profile.data else {}
            
            response = JSONResponse(
                content={
                    "access_token": auth_response.session.access_token,
                    "refresh_token": auth_response.session.refresh_token,
                    "token_type": "bearer",
                    "user": {
                        "id": auth_response.user.id,
                        "email": auth_response.user.email,
                        "username": user_profile.get("username"),
                        "full_name": user_profile.get("full_name"),
                        "is_instructor": user_profile.get("is_instructor", False),
                        "is_admin": user_profile.get("is_admin", False)
                    }
                }
            )
            
            # Set cookies
            response.set_cookie(
                key="access_token",
                value=auth_response.session.access_token,
                max_age=60 * 60 * 24 * 7,
                httponly=True,
                secure=False,
                samesite="lax",
                path="/"
            )
            
            if auth_response.session.refresh_token:
                response.set_cookie(
                    key="refresh_token",
                    value=auth_response.session.refresh_token,
                    max_age=60 * 60 * 24 * 30,
                    httponly=True,
                    secure=False,
                    samesite="lax",
                    path="/"
                )
            
            return response
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
    except Exception as e:
        print(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

@router.get("/login")
async def login_page_redirect():
    """Redirect to the Supabase Auth UI page"""
    return RedirectResponse(url="/auth")

@router.post("/set-session")
async def set_session(
    request: Request,
    supabase=Depends(get_supabase)
) -> JSONResponse:
    """
    Set session from Supabase client-side auth.
    """
    try:
        data = await request.json()
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No access token provided"
            )
        
        # Verify the token is valid
        user = supabase.auth.get_user(access_token)
        
        if not user or not hasattr(user, 'user'):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Set session cookie
        response = JSONResponse(content={"success": True})
        response.set_cookie(
            key="access_token",
            value=access_token,
            max_age=60 * 60 * 24 * 7,
            httponly=True,
            secure=False,
            samesite="lax",
            path="/"
        )
        
        if refresh_token:
            response.set_cookie(
                key="refresh_token",
                value=refresh_token,
                max_age=60 * 60 * 24 * 30,
                httponly=True,
                secure=False,
                samesite="lax",
                path="/"
            )
        
        return response
        
    except Exception as e:
        print(f"Error setting session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set session"
        )

# ==================== LOGOUT ENDPOINT ====================

@router.post("/logout")
async def logout(
    request: Request,
    supabase=Depends(get_supabase)
) -> JSONResponse:
    """
    Logout user and clear session.
    """
    try:
        token = request.cookies.get("access_token")
        
        if token:
            try:
                supabase.auth.sign_out()
                print("User signed out from Supabase")
            except Exception as e:
                print(f"Supabase sign-out error (non-critical): {e}")
        
        response = JSONResponse(
            content={
                "message": "Logged out successfully",
                "redirect": "/login"
            }
        )
        
        response.delete_cookie("access_token", path="/")
        response.delete_cookie("refresh_token", path="/")
        
        return response
        
    except Exception as e:
        print(f"Logout error: {e}")
        response = JSONResponse(
            content={"message": "Logged out", "redirect": "/login"},
            status_code=200
        )
        response.delete_cookie("access_token", path="/")
        response.delete_cookie("refresh_token", path="/")
        return response

@router.get("/logout")
async def logout_get(
    request: Request,
    supabase=Depends(get_supabase)
) -> RedirectResponse:
    """
    GET endpoint for logout.
    """
    token = request.cookies.get("access_token")
    
    if token:
        try:
            supabase.auth.sign_out()
        except:
            pass
    
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    
    return response

# ==================== USER INFO ENDPOINTS ====================

@router.get("/me", response_model=User)
async def get_current_user(
    request: Request,
    supabase=Depends(get_supabase)
) -> Any:
    """
    Get current authenticated user.
    """
    try:
        token = request.cookies.get("access_token")
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )
        
        user = supabase.auth.get_user(token)
        
        if not user or not hasattr(user, 'user'):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        profile = supabase.table("users")\
            .select("*")\
            .eq("id", user.user.id)\
            .execute()
        
        user_data = {
            "id": user.user.id,
            "email": user.user.email,
            **(profile.data[0] if profile.data else {})
        }
        
        return user_data
        
    except Exception as e:
        print(f"Get current user error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )

@router.get("/session")
async def get_session(
    request: Request,
    supabase=Depends(get_supabase)
) -> Dict[str, Any]:
    """
    Get current session info.
    """
    token = request.cookies.get("access_token")
    
    if not token:
        return {"authenticated": False}
    
    try:
        user = supabase.auth.get_user(token)
        
        if not user or not hasattr(user, 'user'):
            return {"authenticated": False}
        
        profile = supabase.table("users")\
            .select("*")\
            .eq("id", user.user.id)\
            .execute()
        
        return {
            "authenticated": True,
            "user": {
                "id": user.user.id,
                "email": user.user.email,
                **(profile.data[0] if profile.data else {})
            }
        }
        
    except Exception:
        return {"authenticated": False}

# ==================== PASSWORD MANAGEMENT ====================

@router.post("/forgot-password")
async def forgot_password(
    request: Request,
    supabase=Depends(get_supabase)
) -> JSONResponse:
    """
    Send password reset email.
    """
    try:
        data = await request.json()
        email = data.get("email")
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is required"
            )
        
        supabase.auth.reset_password_for_email(
            email,
            {
                "redirect_to": f"{settings.BASE_URL}/reset-password"
            }
        )
        
        return JSONResponse(
            content={"message": "Password reset email sent"}
        )
        
    except Exception as e:
        print(f"Forgot password error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send reset email"
        )

@router.post("/reset-password")
async def reset_password(
    request: Request,
    supabase=Depends(get_supabase)
) -> JSONResponse:
    """
    Reset password with token.
    """
    try:
        data = await request.json()
        token = data.get("token")
        new_password = data.get("new_password")
        
        if not token or not new_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token and new password are required"
            )
        
        if len(new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters"
            )
        
        supabase.auth.update_user({
            "password": new_password
        })
        
        return JSONResponse(
            content={"message": "Password updated successfully"}
        )
        
    except Exception as e:
        print(f"Reset password error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password"
        )

@router.post("/change-password")
async def change_password(
    request: Request,
    supabase=Depends(get_supabase)
) -> JSONResponse:
    """
    Change password for authenticated user.
    """
    try:
        data = await request.json()
        current_password = data.get("current_password")
        new_password = data.get("new_password")
        
        if not current_password or not new_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password and new password are required"
            )
        
        if len(new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be at least 8 characters"
            )
        
        # Get current user
        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )
        
        user = supabase.auth.get_user(token)
        if not user or not hasattr(user, 'user'):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Verify current password by attempting to sign in
        try:
            supabase.auth.sign_in_with_password({
                "email": user.user.email,
                "password": current_password
            })
        except:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect"
            )
        
        # Update password
        supabase.auth.update_user({
            "password": new_password
        })
        
        return JSONResponse(
            content={"message": "Password changed successfully"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Change password error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )

# ==================== TOKEN REFRESH ====================

@router.post("/refresh")
async def refresh_token(
    request: Request,
    supabase=Depends(get_supabase)
) -> JSONResponse:
    """
    Refresh access token using refresh token.
    """
    try:
        data = await request.json()
        refresh_token = data.get("refresh_token")
        
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refresh token required"
            )
        
        session = supabase.auth.refresh_session(refresh_token)
        
        if not session or not hasattr(session, 'session'):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        response = JSONResponse(
            content={
                "access_token": session.session.access_token,
                "refresh_token": session.session.refresh_token,
                "token_type": "bearer"
            }
        )
        
        response.set_cookie(
            key="access_token",
            value=session.session.access_token,
            max_age=60 * 60 * 24 * 7,
            httponly=True,
            secure=False,
            samesite="lax",
            path="/"
        )
        
        response.set_cookie(
            key="refresh_token",
            value=session.session.refresh_token,
            max_age=60 * 60 * 24 * 30,
            httponly=True,
            secure=False,
            samesite="lax",
            path="/"
        )
        
        return response
        
    except Exception as e:
        print(f"Refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to refresh token"
        )

# ==================== INVITATION VERIFICATION ====================

@router.post("/verify-invitation")
async def verify_invitation(
    request: Request,
    supabase=Depends(get_supabase)
) -> dict:
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
            return {
                "valid": True,
                "message": "Invitation code is valid",
                "email": invitation["email"],
                "full_name": invitation["full_name"],
                "username": invitation["username"]
            }
        else:
            return {
                "valid": False,
                "message": "Invalid or expired invitation code"
            }
            
    except Exception as e:
        return {
            "valid": False,
            "message": f"Error verifying code: {str(e)}"
        }