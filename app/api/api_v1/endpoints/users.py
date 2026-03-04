from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.supabase_client import get_supabase
from app.schemas.user import User, UserUpdate
from app.api.api_v1.dependencies import get_current_active_user, get_current_admin

router = APIRouter()

@router.get("/", response_model=List[User])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    supabase=Depends(get_supabase),
    current_user: dict = Depends(get_current_admin)  # Only admins can list all users
) -> Any:
    """
    Retrieve all users (admin only).
    """
    try:
        result = supabase.table("users")\
            .select("*")\
            .range(skip, skip + limit - 1)\
            .order("created_at", desc=True)\
            .execute()
        
        return result.data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving users: {str(e)}"
        )

@router.get("/me", response_model=User)
async def get_current_user_info(
    current_user: dict = Depends(get_current_active_user)
) -> Any:
    """
    Get current user information.
    """
    return current_user

@router.get("/{user_id}", response_model=User)
async def get_user(
    user_id: str,
    supabase=Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
) -> Any:
    """
    Get user by ID.
    """
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving user: {str(e)}"
        )

@router.put("/me", response_model=User)
async def update_current_user(
    user_update: UserUpdate,
    supabase=Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
) -> Any:
    """
    Update current user profile.
    """
    try:
        # Filter out None values
        update_data = {k: v for k, v in user_update.dict().items() if v is not None}
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No data to update"
            )
        
        # Add updated_at timestamp
        update_data["updated_at"] = "now()"
        
        result = supabase.table("users")\
            .update(update_data)\
            .eq("id", current_user["id"])\
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user: {str(e)}"
        )

@router.put("/{user_id}", response_model=User)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    supabase=Depends(get_supabase),
    current_user: dict = Depends(get_current_admin)  # Only admins can update other users
) -> Any:
    """
    Update a user (admin only).
    """
    try:
        # Check if user exists
        check = supabase.table("users")\
            .select("id")\
            .eq("id", user_id)\
            .execute()
        
        if not check.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Filter out None values
        update_data = {k: v for k, v in user_update.dict().items() if v is not None}
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No data to update"
            )
        
        # Add updated_at timestamp
        update_data["updated_at"] = "now()"
        
        result = supabase.table("users")\
            .update(update_data)\
            .eq("id", user_id)\
            .execute()
        
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user: {str(e)}"
        )

@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    supabase=Depends(get_supabase),
    current_user: dict = Depends(get_current_admin)  # Only admins can delete users
) -> Any:
    """
    Delete a user (admin only).
    """
    try:
        # Check if user exists
        check = supabase.table("users")\
            .select("id")\
            .eq("id", user_id)\
            .execute()
        
        if not check.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Delete user profile
        result = supabase.table("users")\
            .delete()\
            .eq("id", user_id)\
            .execute()
        
        # Note: This doesn't delete the auth user
        # For complete deletion, you'd need admin API access
        
        return {"message": "User profile deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting user: {str(e)}"
        )

@router.post("/{user_id}/make-instructor")
async def make_instructor(
    user_id: str,
    supabase=Depends(get_supabase),
    current_user: dict = Depends(get_current_admin)
) -> Any:
    """
    Make a user an instructor (admin only).
    """
    try:
        result = supabase.table("users")\
            .update({"is_instructor": True, "updated_at": "now()"})\
            .eq("id", user_id)\
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {"message": "User is now an instructor"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user: {str(e)}"
        )

@router.post("/{user_id}/make-admin")
async def make_admin(
    user_id: str,
    supabase=Depends(get_supabase),
    current_user: dict = Depends(get_current_admin)
) -> Any:
    """
    Make a user an admin (admin only).
    """
    try:
        result = supabase.table("users")\
            .update({"is_admin": True, "updated_at": "now()"})\
            .eq("id", user_id)\
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {"message": "User is now an admin"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user: {str(e)}"
        )