from typing import Any, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.security import HTTPBearer

from app.core.supabase_client import get_supabase
from app.core.config import settings
from app.schemas.user import User
from app.api.api_v1.dependencies import get_current_user_from_cookie

router = APIRouter()
security = HTTPBearer()

@router.get("/login/{provider}")
async def social_login(
    provider: str,
    supabase=Depends(get_supabase)
) -> RedirectResponse:
    """
    Redirect user to social OAuth login page.
    Supported providers: github, google
    """
    try:
        # Validate provider
        if provider not in ["github", "google"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provider must be 'github' or 'google'"
            )
        
        print(f"Initiating {provider} login")
        
        # IMPORTANT: The redirect should go to Supabase, not our app
        # Supabase will handle the OAuth flow and redirect back to our callback
        redirect_to = f"{settings.BASE_URL}/api/v1/auth/callback"
        
        print(f"Redirect URL for Supabase: {redirect_to}")
        
        # Get the Supabase OAuth URL
        response = supabase.auth.sign_in_with_oauth({
            "provider": provider,
            "options": {
                "redirect_to": redirect_to
            }
        })
        
        if hasattr(response, 'url') and response.url:
            print(f"Redirecting to Supabase OAuth URL")
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
    Handle OAuth callback from providers.
    Exchanges the code for a session and redirects to dashboard.
    """
    try:
        # Get the code and provider from query parameters
        code = request.query_params.get("code")
        next_param = request.query_params.get("next", "")
        
        print(f"Callback received - code: {code[:20] if code else 'None'}...")
        print(f"Next param: {next_param}")
        print(f"Full URL: {request.url}")
        print(f"Query params: {dict(request.query_params)}")
        
        if not code:
            # Check if there's an error parameter
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
            session_data = supabase.auth.exchange_code_for_session({
                "auth_code": code
            })
            
            print(f"Session data received: {session_data is not None}")
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
        user_metadata = session_data.user.user_metadata
        
        print(f"User authenticated: {user_email} (ID: {user_id})")
        
        # Determine provider from user metadata
        provider = "unknown"
        if user_metadata and 'iss' in user_metadata:
            if 'google' in user_metadata['iss']:
                provider = 'google'
            elif 'github' in user_metadata['iss']:
                provider = 'github'
        
        # Extract user info from metadata
        username = None
        full_name = None
        avatar_url = None
        
        if provider == "github":
            username = user_metadata.get("user_name") or user_email.split('@')[0]
            full_name = user_metadata.get("name") or username
            avatar_url = user_metadata.get("avatar_url")
        elif provider == "google":
            username = user_email.split('@')[0]
            full_name = user_metadata.get("full_name") or user_metadata.get("name") or username
            avatar_url = user_metadata.get("avatar_url") or user_metadata.get("picture")
        
        # Check if user profile exists
        profile_result = supabase.table("users")\
            .select("*")\
            .eq("id", user_id)\
            .execute()
        
        if not profile_result.data:
            # Create new profile
            profile_data = {
                "id": user_id,
                "email": user_email,
                "username": username,
                "full_name": full_name,
                "avatar_url": avatar_url,
                "is_instructor": False,
                "is_admin": False,
                "provider": provider,
                "provider_id": user_metadata.get("provider_id") or user_metadata.get("sub")
            }
            
            print(f"Creating new user profile: {profile_data}")
            try:
                supabase.table("users").insert(profile_data).execute()
                print("Profile created successfully")
            except Exception as e:
                print(f"Error creating profile: {str(e)}")
        else:
            # Update existing profile with latest info
            update_data = {
                "username": username,
                "full_name": full_name,
                "avatar_url": avatar_url,
                "updated_at": "now()"
            }
            try:
                supabase.table("users")\
                    .update(update_data)\
                    .eq("id", user_id)\
                    .execute()
                print("Profile updated successfully")
            except Exception as e:
                print(f"Error updating profile: {str(e)}")
        
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
            secure=False,  # Set to True in production with HTTPS
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
    

@router.get("/me", response_model=User)
async def get_current_user(
    request: Request,
    supabase=Depends(get_supabase)
) -> Any:
    """
    Get current authenticated user from cookie.
    """
    try:
        token = request.cookies.get("access_token")
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )
        
        # Get user from token
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
        
        if not profile.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        user_data = {
            "id": user.user.id,
            "email": user.user.email,
            **profile.data[0]
        }
        
        return user_data
        
    except HTTPException:
        raise
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
            # Sign out from Supabase
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
        
        # Get profile from database
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
    except Exception as e:
        print(f"Session check error: {str(e)}")
        return {"authenticated": False}
