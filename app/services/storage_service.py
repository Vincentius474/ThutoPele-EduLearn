from typing import Optional, BinaryIO
from supabase import Client
import logging
import uuid
from fastapi import UploadFile
import mimetypes

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
    
    async def upload_course_material(
        self, 
        course_id: str, 
        file: UploadFile,
        material_type: str
    ) -> Optional[str]:
        """
        Upload a course material file to Supabase Storage
        """
        try:
            # Generate a unique filename to avoid collisions
            file_extension = file.filename.split('.')[-1]
            unique_filename = f"{uuid.uuid4()}.{file_extension}"
            file_path = f"{course_id}/{material_type}/{unique_filename}"
            
            # Read file content
            file_content = await file.read()
            
            # Upload to Supabase Storage
            storage = self.supabase.storage.from_("course-materials")
            storage.upload(file_path, file_content)
            
            # Get public URL
            public_url = storage.get_public_url(file_path)
            
            logger.info(f"File uploaded successfully: {file_path}")
            return public_url
            
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return None
    
    async def upload_course_image(
        self,
        course_id: str,
        file: UploadFile
    ) -> Optional[str]:
        """
        Upload a course thumbnail/image
        """
        try:
            # Validate file type
            if not file.content_type.startswith('image/'):
                raise ValueError("File must be an image")
            
            # Generate unique filename
            file_extension = file.filename.split('.')[-1]
            unique_filename = f"{uuid.uuid4()}.{file_extension}"
            file_path = f"{course_id}/{unique_filename}"
            
            # Read file content
            file_content = await file.read()
            
            # Upload to Supabase Storage
            storage = self.supabase.storage.from_("course-images")
            storage.upload(file_path, file_content)
            
            # Get public URL
            public_url = storage.get_public_url(file_path)
            
            return public_url
            
        except Exception as e:
            logger.error(f"Error uploading course image: {e}")
            return None
    
    async def upload_avatar(
        self,
        user_id: str,
        file: UploadFile
    ) -> Optional[str]:
        """
        Upload a user avatar
        """
        try:
            # Validate file type
            if not file.content_type.startswith('image/'):
                raise ValueError("File must be an image")
            
            # Generate filename
            file_extension = file.filename.split('.')[-1]
            file_path = f"{user_id}/avatar.{file_extension}"
            
            # Read file content
            file_content = await file.read()
            
            # Upload to Supabase Storage
            storage = self.supabase.storage.from_("avatars")
            storage.upload(file_path, file_content)
            
            # Get public URL
            public_url = storage.get_public_url(file_path)
            
            return public_url
            
        except Exception as e:
            logger.error(f"Error uploading avatar: {e}")
            return None
    
    async def delete_file(self, bucket: str, file_path: str) -> bool:
        """
        Delete a file from storage
        """
        try:
            storage = self.supabase.storage.from_(bucket)
            storage.remove([file_path])
            return True
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False
    
    async def get_file_info(self, bucket: str, file_path: str) -> Optional[dict]:
        """
        Get file information
        """
        try:
            storage = self.supabase.storage.from_(bucket)
            result = storage.info(file_path)
            return result
        except Exception as e:
            logger.error(f"Error getting file info: {e}")
            return None
    
    def get_public_url(self, bucket: str, file_path: str) -> str:
        """
        Get public URL for a file
        """
        storage = self.supabase.storage.from_(bucket)
        return storage.get_public_url(file_path)
    
    async def list_course_files(self, course_id: str, material_type: Optional[str] = None) -> list:
        """
        List all files for a course
        """
        try:
            storage = self.supabase.storage.from_("course-materials")
            path = f"{course_id}"
            if material_type:
                path += f"/{material_type}"
            
            result = storage.list(path)
            return result
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []