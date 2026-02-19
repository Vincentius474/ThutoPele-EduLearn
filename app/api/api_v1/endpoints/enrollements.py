
from fastapi import APIRouter, Depends
from app.api.api_v1.dependencies import get_current_user

router = APIRouter()

@router.post("/courses/{course_id}/enroll")
async def enroll_in_course(
    course_id: str,
    user=Depends(get_current_user)
):
    # Add enrollment logic
    pass
