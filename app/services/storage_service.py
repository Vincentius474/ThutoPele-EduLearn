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
            file_extension = file.filename.split('.')[-1]
            unique_filename = f"{uuid.uuid4()}.{file_extension}"
            file_path = f"{course_id}/{material_type}/{unique_filename}"
            file_content = await file.read()
            storage = self.supabase.storage.from_("course-materials")
            storage.upload(file_path, file_content)
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
        Upload a course thumbnail/image using service role (bypasses RLS)
        """
        try:
            content_type = file.content_type
            if not content_type or content_type == 'text/plain' or content_type == 'application/octet-stream':
                import mimetypes
                guessed_type, _ = mimetypes.guess_type(file.filename)
                if guessed_type and guessed_type.startswith('image/'):
                    content_type = guessed_type
                    print(f"Guessed content type from extension: {content_type}")
            
            if not content_type or not content_type.startswith('image/'):
                image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']
                file_ext = '.' + file.filename.split('.')[-1].lower() if '.' in file.filename else ''
                
                if file_ext in image_extensions:
                    content_type_map = {
                        '.jpg': 'image/jpeg',
                        '.jpeg': 'image/jpeg',
                        '.png': 'image/png',
                        '.gif': 'image/gif',
                        '.webp': 'image/webp',
                        '.svg': 'image/svg+xml'
                    }
                    content_type = content_type_map.get(file_ext, 'image/jpeg')
                    print(f"Forcing content type based on extension: {content_type}")
                else:
                    raise ValueError(f"File must be an image. Detected: {content_type}, Extension: {file_ext}")
            
            file.file.seek(0, 2)
            file_size = file.file.tell()
            file.file.seek(0)
            
            if file_size > 5 * 1024 * 1024:
                raise ValueError(f"Image too large. Maximum size is 5MB. File size: {file_size} bytes")
 
            import uuid
            import os
            
            file_extension = os.path.splitext(file.filename)[1].lower()
            if not file_extension:
                ext_map = {
                    'image/jpeg': '.jpg',
                    'image/png': '.png',
                    'image/gif': '.gif',
                    'image/webp': '.webp',
                    'image/svg+xml': '.svg'
                }
                file_extension = ext_map.get(content_type, '.jpg')
            
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            file_path = f"{course_id}/{unique_filename}"

            file_content = await file.read()
            print(f"File size: {len(file_content)} bytes")
            
            from app.core.supabase_client import supabase as supabase_client
            service_client = supabase_client.get_service_client()
            storage = service_client.storage.from_("course-images")
            result = storage.upload(
                file_path, 
                file_content,
                {"content-type": content_type}
            )
            public_url = storage.get_public_url(file_path)
            return public_url
            
        except Exception as e:
            print(f"Error uploading course image: {e}")
            import traceback
            traceback.print_exc()
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
            if not file.content_type.startswith('image/'):
                raise ValueError("File must be an image")
            file_extension = file.filename.split('.')[-1]
            file_path = f"{user_id}/avatar.{file_extension}"
            file_content = await file.read()
            storage = self.supabase.storage.from_("avatars")
            storage.upload(file_path, file_content)
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
        

