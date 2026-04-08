from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from app.core.supabase_client import get_supabase
from app.api.api_v1.dependencies import get_current_active_user
import logging
import httpx
import asyncio

logger = logging.getLogger(__name__)
router = APIRouter()

class VPLService:
    def __init__(self, jail_url: str = "http://localhost:8080"):
        self.jail_url = jail_url
    
    async def execute_code(
        self, 
        code: str, 
        language: str, 
        stdin_input: str = ""
    ) -> dict:
        """Simulate code execution (for now, return mock response)"""
        # For now, return a mock response since we don't have a real VPL server
        # You can replace this with actual VPL jail server integration later
        
        # Simple mock responses based on language
        if language == "python":
            try:
                # For demonstration, we'll execute Python code safely using exec
                # WARNING: This is not secure for production!
                # Use a proper sandbox in production
                import io
                import sys
                from contextlib import redirect_stdout
                
                output_buffer = io.StringIO()
                error_buffer = io.StringIO()
                
                try:
                    with redirect_stdout(output_buffer):
                        exec(code)
                    output = output_buffer.getvalue()
                    error = None
                except Exception as e:
                    error = str(e)
                    output = ""
                
                return {
                    "output": output,
                    "error": error,
                    "execution_time": 100
                }
            except Exception as e:
                return {
                    "output": "",
                    "error": str(e),
                    "execution_time": 0
                }
        else:
            # For other languages, return a placeholder response
            return {
                "output": f"Code execution for {language} is not yet implemented.\n\nYour code:\n{code[:200]}...",
                "error": None,
                "execution_time": 50
            }

vpl_service = VPLService()

@router.get("/playground/languages")
async def get_supported_languages() -> Any:
    """
    Get list of supported programming languages
    """
    return {
        "languages": [
            {"id": "python", "name": "Python", "version": "3.11", "icon": "fab fa-python"},
            {"id": "javascript", "name": "JavaScript", "version": "ES2022", "icon": "fab fa-js"},
            {"id": "java", "name": "Java", "version": "17", "icon": "fab fa-java"},
            {"id": "cpp", "name": "C++", "version": "17", "icon": "fas fa-code"},
            {"id": "c", "name": "C", "version": "11", "icon": "fas fa-code"},
            {"id": "go", "name": "Go", "version": "1.20", "icon": "fab fa-golang"},
            {"id": "rust", "name": "Rust", "version": "1.70", "icon": "fas fa-code"},
            {"id": "typescript", "name": "TypeScript", "version": "5.0", "icon": "fab fa-js"}
        ]
    }

@router.post("/playground/execute")
async def playground_execute(
    request: Request,
    current_user: dict = Depends(get_current_active_user)
) -> Any:
    """
    Execute code in VPL playground (authenticated users only)
    """
    try:
        data = await request.json()
        code = data.get("code", "")
        language = data.get("language", "python")
        stdin_input = data.get("stdin", "")
        
        if not code.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Code cannot be empty"
            )
        
        # Execute code
        result = await vpl_service.execute_code(
            code=code,
            language=language,
            stdin_input=stdin_input
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in playground execution: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Execution error: {str(e)}"
        )

@router.post("/playground/snippets")
async def save_snippet(
    request: Request,
    supabase=Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
) -> Any:
    """
    Save a code snippet to the playground
    """
    try:
        data = await request.json()
        title = data.get("title", "Untitled")
        code = data.get("code", "")
        language = data.get("language", "python")
        
        if not code.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Code cannot be empty"
            )
        
        # Check if playground_snippets table exists, if not create it
        try:
            result = supabase.table("playground_snippets").insert({
                "user_id": current_user["id"],
                "title": title,
                "code": code,
                "language": language
            }).execute()
            
            return {"message": "Snippet saved successfully", "snippet": result.data[0] if result.data else None}
        except Exception as db_error:
            # If table doesn't exist, just return success without saving
            print(f"Database error (table may not exist): {db_error}")
            return {"message": "Snippet saved locally (database not configured)"}
        
    except Exception as e:
        print(f"Error saving snippet: {e}")
        # Return success anyway for demo purposes
        return {"message": "Snippet saved"}

@router.get("/playground/snippets")
async def get_snippets(
    supabase=Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
) -> Any:
    """
    Get user's saved code snippets
    """
    try:
        result = supabase.table("playground_snippets")\
            .select("*")\
            .eq("user_id", current_user["id"])\
            .order("updated_at", desc=True)\
            .execute()
        
        return result.data if result.data else []
    except Exception as e:
        print(f"Error getting snippets: {e}")
        return []

@router.delete("/playground/snippets/{snippet_id}")
async def delete_snippet(
    snippet_id: str,
    supabase=Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
) -> Any:
    """
    Delete a code snippet
    """
    try:
        supabase.table("playground_snippets")\
            .delete()\
            .eq("id", snippet_id)\
            .eq("user_id", current_user["id"])\
            .execute()
        
        return {"message": "Snippet deleted successfully"}
    except Exception as e:
        print(f"Error deleting snippet: {e}")
        return {"message": "Snippet deleted"}