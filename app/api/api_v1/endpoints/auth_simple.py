from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm

from app.core.supabase_client import get_supabase
from app.core.config import settings
from app.api.api_v1.dependencies import get_current_active_user, get_current_user_from_cookie
from app.schemas.user import Token

router = APIRouter()

# ==================== LOGIN ENDPOINT ====================

@router.post("/login", response_model=Token)
async def login(
    request: Request,
    supabase=Depends(get_supabase)
) -> Any:
    """
    Login with email and password.
    This endpoint is called by the Supabase Auth UI.
    """
    try:
        # Try to parse as JSON first
        try:
            data = await request.json()
            email = data.get("email")
            password = data.get("password")
        except:
            # If not JSON, try form data
            form_data = await request.form()
            email = form_data.get("email") or form_data.get("username")
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
            # Set session cookie
            response = JSONResponse(
                content={
                    "access_token": auth_response.session.access_token,
                    "refresh_token": auth_response.session.refresh_token,
                    "token_type": "bearer"
                }
            )
            
            response.set_cookie(
                key="access_token",
                value=auth_response.session.access_token,
                max_age=60 * 60 * 24 * 7,  # 7 days
                httponly=True,
                secure=False,
                samesite="lax",
                path="/"
            )
            
            if auth_response.session.refresh_token:
                response.set_cookie(
                    key="refresh_token",
                    value=auth_response.session.refresh_token,
                    max_age=60 * 60 * 24 * 30,  # 30 days
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
            max_age=60 * 60 * 24 * 7,  # 7 days
            httponly=True,
            secure=False,  # Set to True in production
            samesite="lax",
            path="/"
        )
        
        if refresh_token:
            response.set_cookie(
                key="refresh_token",
                value=refresh_token,
                max_age=60 * 60 * 24 * 30,  # 30 days
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
    Logout user and clear session from both client and server.
    """
    try:
        # Get token from cookie
        token = request.cookies.get("access_token")
        
        if token:
            try:
                # Sign out from Supabase (revoke token)
                supabase.auth.sign_out()
                print("User signed out from Supabase")
            except Exception as e:
                print(f"Supabase sign-out error (non-critical): {e}")
        
        # Create response
        response = JSONResponse(
            content={
                "message": "Logged out successfully",
                "redirect": "/login"
            }
        )
        
        # Clear all auth cookies
        response.delete_cookie("access_token", path="/")
        response.delete_cookie("refresh_token", path="/")
        
        print("Auth cookies cleared")
        
        return response
        
    except Exception as e:
        print(f"Logout error: {e}")
        # Even if there's an error, try to clear cookies
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

@router.get("/me")
async def get_current_user(
    request: Request,
    supabase=Depends(get_supabase)
) -> Dict[str, Any]:
    """
    Get current authenticated user.
    """
    token = request.cookies.get("access_token")
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        user = supabase.auth.get_user(token)
        
        if not user or not hasattr(user, 'user'):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Get profile from database
        profile = supabase.table("users")\
            .select("*")\
            .eq("id", user.user.id)\
            .execute()
        
        return {
            "id": user.user.id,
            "email": user.user.email,
            **(profile.data[0] if profile.data else {})
        }
        
    except Exception as e:
        print(f"Error getting user: {e}")
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
        
        # Send reset password email via Supabase
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
        
        # Verify token and update password
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
    supabase=Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
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
        
        # First verify current password by attempting to sign in
        try:
            supabase.auth.sign_in_with_password({
                "email": current_user["email"],
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
        
        # Refresh session
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
        
        # Update cookies
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