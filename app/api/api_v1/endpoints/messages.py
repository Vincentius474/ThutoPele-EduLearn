from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from app.core.supabase_client import get_supabase
from app.api.api_v1.dependencies import get_current_instructor, get_current_user
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/instructor/messages")
async def send_message(
    request: Request,
    supabase=Depends(get_supabase),
    current_user: dict = Depends(get_current_instructor)
) -> Any:
    """
    Send a message to students in a course
    """
    try:
        data = await request.json()
        course_id = data.get("course_id")
        message_type = data.get("type", "announcement")
        subject = data.get("subject")
        content = data.get("content")
        send_email = data.get("send_email", False)
        is_important = data.get("is_important", False)
        
        if not all([course_id, subject, content]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Course ID, subject, and content are required"
            )
        
        # Verify instructor owns this course
        course_check = supabase.table("courses")\
            .select("instructor_id")\
            .eq("id", course_id)\
            .execute()
        
        if not course_check.data or course_check.data[0]["instructor_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to send messages for this course"
            )
        
        # Get enrolled students
        students = supabase.table("enrollments")\
            .select("user_id")\
            .eq("course_id", course_id)\
            .execute()
        
        student_ids = [s["user_id"] for s in students.data]
        recipient_count = len(student_ids)
        
        # Create message
        message_data = {
            "course_id": course_id,
            "instructor_id": current_user["id"],
            "type": message_type,
            "subject": subject,
            "content": content,
            "send_email": send_email,
            "is_important": is_important,
            "recipient_count": recipient_count
        }
        
        message_result = supabase.table("messages").insert(message_data).execute()
        
        if not message_result.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create message"
            )
        
        message_id = message_result.data[0]["id"]
        
        # Create message recipients
        if student_ids:
            recipient_data = [
                {"message_id": message_id, "user_id": uid}
                for uid in student_ids
            ]
            supabase.table("message_recipients").insert(recipient_data).execute()
        
        # If send_email is True, you would trigger email notifications here
        if send_email:
            # TODO: Implement email notifications
            pass
        
        return {
            "message": "Message sent successfully",
            "message_id": message_id,
            "recipient_count": recipient_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending message: {str(e)}"
        )

@router.get("/instructor/messages/recent")
async def get_recent_messages(
    supabase=Depends(get_supabase),
    current_user: dict = Depends(get_current_instructor)
) -> Any:
    """
    Get recent messages sent by the instructor
    """
    try:
        messages = supabase.table("messages")\
            .select("*, courses(title)")\
            .eq("instructor_id", current_user["id"])\
            .order("created_at", desc=True)\
            .limit(10)\
            .execute()
        
        result = []
        for msg in messages.data:
            result.append({
                "id": msg["id"],
                "course_id": msg["course_id"],
                "course_title": msg.get("courses", {}).get("title", "Unknown"),
                "type": msg["type"],
                "subject": msg["subject"],
                "content": msg["content"],
                "recipient_count": msg["recipient_count"],
                "created_at": msg["created_at"]
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting messages: {e}")
        return []

@router.get("/instructor/messages/{message_id}")
async def get_message_details(
    message_id: str,
    supabase=Depends(get_supabase),
    current_user: dict = Depends(get_current_instructor)
) -> Any:
    """
    Get detailed message information
    """
    try:
        message = supabase.table("messages")\
            .select("*, courses(title)")\
            .eq("id", message_id)\
            .eq("instructor_id", current_user["id"])\
            .execute()
        
        if not message.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found"
            )
        
        msg = message.data[0]
        
        # Get read statistics
        recipients = supabase.table("message_recipients")\
            .select("read_at", count="exact")\
            .eq("message_id", message_id)\
            .execute()
        
        read_count = sum(1 for r in recipients.data if r.get("read_at"))
        
        return {
            "id": msg["id"],
            "course_id": msg["course_id"],
            "course_title": msg.get("courses", {}).get("title", "Unknown"),
            "type": msg["type"],
            "subject": msg["subject"],
            "content": msg["content"],
            "send_email": msg["send_email"],
            "is_important": msg["is_important"],
            "recipient_count": msg["recipient_count"],
            "read_count": read_count,
            "created_at": msg["created_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting message details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting message details: {str(e)}"
        )

@router.get("/courses/{course_id}/materials")
async def get_course_materials(
    course_id: str,
    supabase=Depends(get_supabase),
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Get materials for a course (students see published only, instructors see all)
    """
    try:
        query = supabase.table("course_materials")\
            .select("*")\
            .eq("course_id", course_id)\
            .order("order_index")
        
        # If user is not the instructor, only show published materials
        if current_user:
            # Check if user is instructor for this course
            course = supabase.table("courses")\
                .select("instructor_id")\
                .eq("id", course_id)\
                .execute()
            
            if not course.data or course.data[0]["instructor_id"] != current_user["id"]:
                query = query.eq("is_published", True)
        else:
            query = query.eq("is_published", True)
        
        result = query.execute()
        return result.data
        
    except Exception as e:
        logger.error(f"Error getting materials: {e}")
        return []

@router.post("/courses/{course_id}/materials")
async def create_material(
    course_id: str,
    request: Request,
    supabase=Depends(get_supabase),
    current_user: dict = Depends(get_current_instructor)
) -> Any:
    """
    Create a new course material
    """
    try:
        # Verify instructor owns this course
        course_check = supabase.table("courses")\
            .select("instructor_id")\
            .eq("id", course_id)\
            .execute()
        
        if not course_check.data or course_check.data[0]["instructor_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to add materials to this course"
            )
        
        # Parse form data
        form = await request.form()
        print(f"Form data keys: {list(form.keys())}")
        
        material_data = {
            "course_id": course_id,
            "title": form.get("title"),
            "description": form.get("description"),
            "material_type": form.get("material_type"),
            "order_index": int(form.get("order_index", 0)),
            "is_published": form.get("is_published", "true").lower() == "true"
        }
        
        # Handle file upload
        file = form.get("file")
        if file and hasattr(file, "filename") and file.filename:
            try:
                print(f"Uploading file: {file.filename}, Type: {file.content_type}")
                
                # Use service client to bypass RLS
                from app.core.supabase_client import supabase as supabase_client
                service_client = supabase_client.get_service_client()
                
                # Read file content
                file_content = await file.read()
                file_path = f"{course_id}/materials/{file.filename}"
                
                print(f"File size: {len(file_content)} bytes")
                print(f"Uploading to path: {file_path}")
                
                # Upload to storage using service client
                storage = service_client.storage.from_("course-materials")
                result = storage.upload(file_path, file_content)
                
                print(f"Upload result: {result}")
                
                # Get public URL
                material_data["content_url"] = storage.get_public_url(file_path)
                material_data["file_name"] = file.filename
                material_data["file_size"] = len(file_content)
                material_data["file_type"] = file.content_type
                
                print(f"File uploaded successfully: {material_data['content_url']}")
                
            except Exception as e:
                print(f"Error uploading file: {e}")
                import traceback
                traceback.print_exc()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File upload failed: {str(e)}"
                )
        
        # Handle external link
        content_url = form.get("content_url")
        if content_url:
            material_data["content_url"] = content_url
        
        # Handle video duration
        duration = form.get("duration")
        if duration:
            material_data["duration"] = int(duration)
        
        # Insert material
        print(f"Inserting material data: {material_data}")
        result = supabase.table("course_materials").insert(material_data).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create material"
            )
        
        print(f"Material created successfully: {result.data[0]['id']}")
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating material: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating material: {str(e)}"
        )

@router.put("/courses/materials/{material_id}")
async def update_material(
    material_id: str,
    request: Request,
    supabase=Depends(get_supabase),
    current_user: dict = Depends(get_current_instructor)
) -> Any:
    """
    Update a course material
    """
    try:
        # Verify instructor owns this material
        material = supabase.table("course_materials")\
            .select("course_id")\
            .eq("id", material_id)\
            .execute()
        
        if not material.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Material not found"
            )
        
        course_id = material.data[0]["course_id"]
        
        course_check = supabase.table("courses")\
            .select("instructor_id")\
            .eq("id", course_id)\
            .execute()
        
        if not course_check.data or course_check.data[0]["instructor_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this material"
            )
        
        data = await request.json()
        data["updated_at"] = "now()"
        
        result = supabase.table("course_materials")\
            .update(data)\
            .eq("id", material_id)\
            .execute()
        
        return result.data[0] if result.data else None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating material: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating material: {str(e)}"
        )

@router.delete("/courses/materials/{material_id}")
async def delete_material(
    material_id: str,
    supabase=Depends(get_supabase),
    current_user: dict = Depends(get_current_instructor)
) -> Any:
    """
    Delete a course material
    """
    try:
        # Verify instructor owns this material
        material = supabase.table("course_materials")\
            .select("course_id")\
            .eq("id", material_id)\
            .execute()
        
        if not material.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Material not found"
            )
        
        course_id = material.data[0]["course_id"]
        
        course_check = supabase.table("courses")\
            .select("instructor_id")\
            .eq("id", course_id)\
            .execute()
        
        if not course_check.data or course_check.data[0]["instructor_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this material"
            )
        
        result = supabase.table("course_materials")\
            .delete()\
            .eq("id", material_id)\
            .execute()
        
        return {"message": "Material deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting material: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting material: {str(e)}"
        )