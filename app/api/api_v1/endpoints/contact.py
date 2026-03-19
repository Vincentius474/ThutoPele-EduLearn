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
        
        # Save to database
        try:
            result = supabase.table("contact_messages").insert({
                "name": name,
                "email": email,
                "subject": subject,
                "message": message,
                "created_at": "now()"
            }).execute()
            
            logger.info(f"Message saved successfully")
            
        except Exception as db_error:
            logger.error(f"Database error: {db_error}")
            # Check if it's an RLS error
            error_str = str(db_error)
            if "42501" in error_str or "policy" in error_str.lower():
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Database permission error. Please contact the administrator."
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error: {str(db_error)}"
                )
        
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