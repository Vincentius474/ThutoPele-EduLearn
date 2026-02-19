
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.supabase_client import get_supabase
from app.schemas.user import User, UserUpdate

router = APIRouter()

@router.get("/", response_model=List[User])
async def get_users(
    *,
    supabase=Depends(get_supabase),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """
    Retrieve users.
    """
    result = supabase.table("users")\
        .select("*")\
        .range(skip, skip + limit - 1)\
        .execute()
    
    return result.data

@router.get("/{user_id}", response_model=User)
async def get_user(
    *,
    supabase=Depends(get_supabase),
    user_id: str
) -> Any:
    """
    Get user by ID.
    """
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

@router.put("/{user_id}", response_model=User)
async def update_user(
    *,
    supabase=Depends(get_supabase),
    user_id: str,
    user_in: UserUpdate
) -> Any:
    """
    Update user.
    """
    # Filter out None values
    update_data = {k: v for k, v in user_in.dict().items() if v is not None}
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No data to update"
        )
    
    result = supabase.table("users")\
        .update(update_data)\
        .eq("id", user_id)\
        .execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return result.data[0]