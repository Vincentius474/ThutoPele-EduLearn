from supabase import create_client, Client
from .config import settings
import functools

class SupabaseClient:
    def __init__(self):
        self.url = settings.SUPABASE_URL
        self.key = settings.SUPABASE_KEY
        self.client: Client = None
        
    def get_client(self) -> Client:
        """Get or create Supabase client"""
        if not self.client:
            if not self.url or not self.key:
                raise ValueError("Supabase URL and Key must be set in environment variables")
            self.client = create_client(self.url, self.key)
        return self.client
    
    def get_service_client(self) -> Client:
        """Get service role client for admin operations"""
        service_key = settings.SUPABASE_SERVICE_KEY if hasattr(settings, 'SUPABASE_SERVICE_KEY') else self.key
        if not service_key:
            raise ValueError("Supabase service key must be set for admin operations")
        return create_client(self.url, service_key)

# Create singleton instance
supabase = SupabaseClient()

def get_supabase() -> Client:
    """Dependency to get Supabase client"""
    return supabase.get_client()

def get_supabase_service() -> Client:
    """Dependency to get Supabase service client (admin)"""
    return supabase.get_service_client()