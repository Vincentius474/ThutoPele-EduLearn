import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from supabase import Client
import logging

logger = logging.getLogger(__name__)

class InvitationService:
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
    
    def generate_invitation_code(self) -> str:
        """Generate a unique invitation code"""
        alphabet = string.ascii_uppercase + string.digits
        # Format: INST-XXXX-XXXX (e.g., INST-AB12-CD34)
        part1 = ''.join(secrets.choice(alphabet) for _ in range(4))
        part2 = ''.join(secrets.choice(alphabet) for _ in range(4))
        return f"INST-{part1}-{part2}"
    
    async def create_invitation(self, email: str, full_name: str, username: str, admin_id: str) -> Optional[Dict[str, Any]]:
        """Create a new invitation for an instructor"""
        try:
            existing = self.supabase.table("invitations")\
                .select("*")\
                .eq("email", email)\
                .eq("is_used", False)\
                .gt("expires_at", datetime.utcnow().isoformat())\
                .execute()
            
            if existing.data and len(existing.data) > 0:
                logger.info(f"Active invitation already exists for {email}")
                return existing.data[0]

            code = self.generate_invitation_code()
            expires_at = datetime.utcnow() + timedelta(days=7)
            
            invitation_data = {
                "email": email,
                "full_name": full_name,
                "username": username,
                "code": code,
                "is_used": False,
                "expires_at": expires_at.isoformat(),
                "created_by": admin_id
            }
            
            result = self.supabase.table("invitations").insert(invitation_data).execute()
            
            if result.data and len(result.data) > 0:
                logger.info(f"Created invitation for {email} with code: {code}")
                return result.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Error creating invitation: {e}")
            return None
    
    async def verify_invitation(self, email: str, code: str) -> Dict[str, Any]:
        """Verify an invitation code"""
        try:
            result = self.supabase.table("invitations")\
                .select("*")\
                .eq("email", email)\
                .eq("code", code)\
                .eq("is_used", False)\
                .gt("expires_at", datetime.utcnow().isoformat())\
                .execute()
            
            if result.data and len(result.data) > 0:
                invitation = result.data[0]
                return {
                    "valid": True,
                    "invitation": invitation,
                    "message": "Invitation code is valid"
                }
            else:
                return {
                    "valid": False,
                    "invitation": None,
                    "message": "Invalid or expired invitation code"
                }  
        except Exception as e:
            logger.error(f"Error verifying invitation: {e}")
            return {
                "valid": False,
                "invitation": None,
                "message": f"Error verifying invitation: {str(e)}"
            }
    
    async def mark_invitation_used(self, invitation_id: str) -> bool:
        """Mark an invitation as used"""
        try:
            result = self.supabase.table("invitations")\
                .update({"is_used": True, "used_at": datetime.utcnow().isoformat()})\
                .eq("id", invitation_id)\
                .execute()
            return len(result.data) > 0
        except Exception as e:
            logger.error(f"Error marking invitation as used: {e}")
            return False
    
    async def get_invitations(self, admin_id: Optional[str] = None) -> list:
        """Get all invitations (filter by admin if provided)"""
        try:
            query = self.supabase.table("invitations").select("*")
            if admin_id:
                query = query.eq("created_by", admin_id)
            result = query.order("created_at", desc=True).execute()
            return result.data
        except Exception as e:
            logger.error(f"Error getting invitations: {e}")
            return []