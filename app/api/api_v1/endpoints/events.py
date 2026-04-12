from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from app.core.supabase_client import get_supabase
from app.api.api_v1.dependencies import get_current_user, get_current_admin_or_instructor, get_current_active_user
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/events")
async def get_events(
    event_type: Optional[str] = None,
    category: Optional[str] = None,
    featured_only: bool = False,
    upcoming_only: bool = True,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    supabase=Depends(get_supabase)
) -> Any:
    """
    Get all events with optional filters
    """
    try:
   
        # Start building query
        query = supabase.table("events")\
            .select("*", count="exact")\
            .eq("is_published", True)\
            .order("start_date", desc=False)
        
        # Apply filters
        if event_type:
            query = query.eq("event_type", event_type)
        
        if category:
            query = query.eq("category", category)
        
        if featured_only:
            query = query.eq("is_featured", True)
        
        if upcoming_only:
            # Get events that haven't happened yet (start_date >= today)
            today = datetime.now().strftime("%Y-%m-%d")
            query = query.gte("start_date", today)
        
        # Execute query to get count
        count_result = query.execute()
        total = count_result.count if hasattr(count_result, 'count') else len(count_result.data or [])
        
        # Apply pagination
        result = query.range(offset, offset + limit - 1).execute()
        
        # Calculate spots left for each event
        for event in result.data:
            if event.get("max_attendees"):
                event["spots_left"] = event["max_attendees"] - event.get("current_attendees", 0)
            else:
                event["spots_left"] = None
        
        return {
            "events": result.data,
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        print(f"Error getting events: {e}")
        import traceback
        traceback.print_exc()
        return {"events": [], "total": 0, "limit": limit, "offset": offset}

@router.get("/events/featured")
async def get_featured_event(
    supabase=Depends(get_supabase)
) -> Any:
    """
    Get featured event
    """
    try:
        result = supabase.table("events")\
            .select("*")\
            .eq("is_published", True)\
            .eq("is_featured", True)\
            .order("start_date", desc=False)\
            .limit(1)\
            .execute()
        
        if result.data:
            event = result.data[0]
            if event.get("max_attendees"):
                event["spots_left"] = event["max_attendees"] - event.get("current_attendees", 0)
            return event
        return None
        
    except Exception as e:
        logger.error(f"Error getting featured event: {e}")
        return None

@router.get("/events/{event_id}")
async def get_event(
    event_id: str,
    supabase=Depends(get_supabase)
) -> Any:
    """
    Get a single event by ID
    """
    try:
        result = supabase.table("events")\
            .select("*")\
            .eq("id", event_id)\
            .eq("is_published", True)\
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        
        event = result.data[0]
        if event.get("max_attendees"):
            event["spots_left"] = event["max_attendees"] - event.get("current_attendees", 0)
        
        # Get organizer details
        if event.get("organizer_id"):
            organizer = supabase.table("users")\
                .select("full_name, email, avatar_url")\
                .eq("id", event["organizer_id"])\
                .execute()
            if organizer.data:
                event["organizer"] = organizer.data[0]
        
        return event
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting event: {str(e)}"
        )

@router.post("/events")
async def create_event(
    request: Request,
    supabase=Depends(get_supabase),
    current_user: dict = Depends(get_current_admin_or_instructor)
) -> Any:
    """
    Create a new event (admin/instructor only)
    """
    try:
        data = await request.json()
        
        # Validate required fields
        required_fields = ["title", "event_type", "start_date"]
        for field in required_fields:
            if not data.get(field):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{field} is required"
                )
        
        event_data = {
            "title": data["title"],
            "description": data.get("description", ""),
            "event_type": data["event_type"],
            "category": data.get("category"),
            "start_date": data["start_date"],
            "end_date": data.get("end_date"),
            "start_time": data.get("start_time"),
            "end_time": data.get("end_time"),
            "location": data.get("location"),
            "is_virtual": data.get("is_virtual", False),
            "meeting_link": data.get("meeting_link"),
            "price": data.get("price", 0),
            "is_free": data.get("is_free", True),
            "max_attendees": data.get("max_attendees"),
            "organizer_id": current_user["id"],
            "organizer_name": data.get("organizer_name", current_user.get("full_name")),
            "featured_image": data.get("featured_image"),
            "is_published": data.get("is_published", True),
            "is_featured": data.get("is_featured", False)
        }
        
        result = supabase.table("events").insert(event_data).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create event"
            )
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating event: {str(e)}"
        )

@router.put("/events/{event_id}")
async def update_event(
    event_id: str,
    request: Request,
    supabase=Depends(get_supabase),
    current_user: dict = Depends(get_current_admin_or_instructor)
) -> Any:
    """
    Update an event (admin/instructor only)
    """
    try:
        data = await request.json()
        data["updated_at"] = "now()"
        
        result = supabase.table("events")\
            .update(data)\
            .eq("id", event_id)\
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        
        return result.data[0]
        
    except Exception as e:
        logger.error(f"Error updating event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating event: {str(e)}"
        )

@router.delete("/events/{event_id}")
async def delete_event(
    event_id: str,
    supabase=Depends(get_supabase),
    current_user: dict = Depends(get_current_admin_or_instructor)
) -> Any:
    """
    Delete an event (admin/instructor only)
    """
    try:
        result = supabase.table("events")\
            .delete()\
            .eq("id", event_id)\
            .execute()
        
        return {"message": "Event deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting event: {str(e)}"
        )

@router.post("/events/{event_id}/register")
async def register_for_event(
    event_id: str,
    supabase=Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
) -> Any:
    """
    Register current user for an event
    """
    try:
        # Check if event exists and has spots
        event = supabase.table("events")\
            .select("*")\
            .eq("id", event_id)\
            .execute()
        
        if not event.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        
        event_data = event.data[0]
        
        # Check if already registered
        existing = supabase.table("event_registrations")\
            .select("*")\
            .eq("event_id", event_id)\
            .eq("user_id", current_user["id"])\
            .execute()
        
        if existing.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already registered for this event"
            )
        
        # Check spots availability
        if event_data.get("max_attendees"):
            current = event_data.get("current_attendees", 0)
            if current >= event_data["max_attendees"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Event is full"
                )
        
        # Register user
        registration_data = {
            "event_id": event_id,
            "user_id": current_user["id"]
        }
        
        result = supabase.table("event_registrations").insert(registration_data).execute()
        
        # Update current attendees count
        supabase.table("events")\
            .update({"current_attendees": event_data["current_attendees"] + 1})\
            .eq("id", event_id)\
            .execute()
        
        return {
            "message": "Successfully registered for event",
            "registration": result.data[0] if result.data else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering for event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error registering for event: {str(e)}"
        )