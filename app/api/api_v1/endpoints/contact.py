# from typing import Any
# from fastapi import APIRouter, Depends, HTTPException, status, Request
# from pydantic import BaseModel, EmailStr
# import logging
# from datetime import datetime

# from app.core.supabase_client import get_supabase

# logger = logging.getLogger(__name__)
# router = APIRouter()

# class ContactForm(BaseModel):
#     name: str
#     email: EmailStr
#     subject: str
#     message: str

# @router.post("/contact")
# async def submit_contact_form(
#     request: Request,
#     supabase=Depends(get_supabase)
# ) -> Any:
#     """
#     Submit contact form - saves message to database
#     """
#     try:
#         # Parse request body
#         data = await request.json()
        
#         # Validate required fields
#         name = data.get("name")
#         email = data.get("email")
#         subject = data.get("subject")
#         message = data.get("message")
        
#         if not all([name, email, subject, message]):
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="All fields are required"
#             )
        
#         # Log the submission
#         logger.info(f"Contact form submission from: {name} ({email})")
#         logger.info(f"Subject: {subject}")
        
#         # Save to database
#         result = supabase.table("contact_messages").insert({
#             "name": name,
#             "email": email,
#             "subject": subject,
#             "message": message,
#             "created_at": "now()"
#         }).execute()
        
#         if not result.data:
#             raise HTTPException(
#                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 detail="Failed to save message"
#             )
        
#         return {
#             "success": True,
#             "message": "Thank you for your message! We'll get back to you soon."
#         }
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error processing contact form: {e}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Failed to send message. Please try again later."
#         )


from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
import logging
from app.core.supabase_client import get_supabase

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/contact")
async def submit_contact_form(
    request: Request,
    supabase=Depends(get_supabase)
) -> Any:
    """
    Submit contact form - saves message to database
    """
    try:
        # Parse request body
        data = await request.json()
        
        # Validate required fields
        name = data.get("name")
        email = data.get("email")
        subject = data.get("subject")
        message = data.get("message")
        
        if not all([name, email, subject, message]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All fields are required"
            )
        
        # Log the submission
        logger.info(f"Contact form submission from: {name} ({email})")
        
        # Save to database (optional - remove if you don't have the table yet)
        try:
            result = supabase.table("contact_messages").insert({
                "name": name,
                "email": email,
                "subject": subject,
                "message": message,
                "created_at": "now()"
            }).execute()
        except Exception as db_error:
            logger.warning(f"Could not save to database: {db_error}")
            # Continue even if database save fails
        
        return {
            "success": True,
            "message": "Thank you for your message! We'll get back to you soon."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing contact form: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send message. Please try again later."
        )