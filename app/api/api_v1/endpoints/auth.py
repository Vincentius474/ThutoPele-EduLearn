from typing import Any, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.security import HTTPBearer

from app.core.supabase_client import get_supabase
from app.core.config import settings
from app.schemas.user import User, Token
from app.schemas.invitation import InvitationResponse
from app.api.api_v1.dependencies import get_current_user_from_cookie

router = APIRouter()
security = HTTPBearer()

# ==================== EMAIL/PASSWORD AUTH ====================

@router.post("/register/student", response_model=dict)
async def register_student(
    request: Request,
    supabase=Depends(get_supabase)
) -> Any:
    """
    Register a new student (no invitation code required).
    """
    try:
        body = await request.json()
        email = body.get("email")
        password = body.get("password")
        username = body.get("username")
        full_name = body.get("full_name")
        
        if not all([email, password, username, full_name]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required fields"
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

@router.post("/login", response_model=Token)
async def login(
    request: Request,
    supabase=Depends(get_supabase)
) -> Any:
    """
    Login with email and password.
    """
    try:
        form_data = await request.form()
        email = form_data.get("username")
        password = form_data.get("password")
        
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

# ==================== SOCIAL AUTH (GITHUB & GOOGLE) ====================

@router.get("/login/{provider}")
async def social_login(
    provider: str,
    supabase=Depends(get_supabase)
) -> RedirectResponse:
    """
    Redirect to social provider login (github or google).
    """
    try:
        if provider not in ["github", "google"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provider must be 'github' or 'google'"
            )
        
        print(f"Initiating {provider} login")
        
        # Generate Supabase OAuth URL
        redirect_to = f"{settings.BASE_URL}/api/v1/auth/callback"
        
        response = supabase.auth.sign_in_with_oauth({
            "provider": provider,
            "options": {
                "redirect_to": redirect_to
            }
        })
        
        if hasattr(response, 'url') and response.url:
            print(f"Redirecting to {provider}")
            return RedirectResponse(response.url)
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate {provider} OAuth URL"
            )
            
    except Exception as e:
        print(f"{provider} login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication with {provider} failed"
        )


@router.get("/callback")
async def oauth_callback(
    request: Request,
    supabase=Depends(get_supabase)
) -> RedirectResponse:
    """
    Handle OAuth callback from Supabase.
    """
    try:
        # Log all query parameters for debugging
        print(f"Full callback URL: {request.url}")
        print(f"All query params: {dict(request.query_params)}")
        
        # Get the authorization code
        code = request.query_params.get("code")
        
        print(f"Callback received - code present: {code is not None}")
        
        if not code:
            error = request.query_params.get("error")
            error_description = request.query_params.get("error_description")
            if error:
                print(f"OAuth error: {error} - {error_description}")
                return RedirectResponse(
                    url=f"{settings.BASE_URL}/login?error={error}",
                    status_code=302
                )
            
            return RedirectResponse(
                url=f"{settings.BASE_URL}/login?error=no_code",
                status_code=302
            )
        
        # Exchange code for session
        try:
            print(f"Exchanging code for session...")
            session_data = supabase.auth.exchange_code_for_session({
                "auth_code": code
            })
            print(f"Session exchange successful")
        except Exception as e:
            print(f"Error exchanging code: {str(e)}")
            return RedirectResponse(
                url=f"{settings.BASE_URL}/login?error=exchange_failed",
                status_code=302
            )
        
        if not session_data or not hasattr(session_data, 'session') or not session_data.session:
            print("No session in response")
            return RedirectResponse(
                url=f"{settings.BASE_URL}/login?error=no_session",
                status_code=302
            )
        
        # Get user data
        user_id = session_data.user.id
        user_email = session_data.user.email
        
        print(f"User authenticated: {user_email} (ID: {user_id})")
        
        # Set cookie and redirect to dashboard
        response = RedirectResponse(
            url=f"{settings.BASE_URL}/dashboard",
            status_code=302
        )
        
        response.set_cookie(
            key="access_token",
            value=session_data.session.access_token,
            max_age=60 * 60 * 24 * 7,  # 7 days
            httponly=True,
            secure=False,  # Set to True in production
            samesite="lax",
            path="/"
        )
        
        print(f"Login successful, redirecting to dashboard")
        return response
        
    except Exception as e:
        print(f"Callback error: {str(e)}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(
            url=f"{settings.BASE_URL}/login?error=callback_failed",
            status_code=302
        )


# ==================== COMMON ENDPOINTS ====================

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
            supabase.auth.sign_out()
        
        response = JSONResponse(
            content={"message": "Logged out successfully"}
        )
        response.delete_cookie("access_token", path="/")
        
        return response
        
    except Exception as e:
        print(f"Logout error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/verify-invitation")
async def verify_invitation(
    request: Request,
    supabase=Depends(get_supabase)
) -> InvitationResponse:
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