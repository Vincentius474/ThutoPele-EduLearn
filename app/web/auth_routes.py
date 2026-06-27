from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.core.config import settings
from app.web.dependencies import get_templates, get_current_user_from_cookie

router = APIRouter()

@router.get("/auth", response_class=HTMLResponse)
async def auth_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: dict = Depends(get_current_user_from_cookie)
):
    """Supabase Auth UI page"""
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=302)
    
    return templates.TemplateResponse(
        "auth/supabase_auth.html",
        {
            "request": request,
            "supabase_url": settings.SUPABASE_URL,
            "supabase_anon_key": settings.SUPABASE_KEY,
            "title": "Authentication"
        }
    )

@router.get("/login", response_class=HTMLResponse)
async def login_redirect():
    """Redirect to auth page"""
    return RedirectResponse(url="/auth", status_code=302)

@router.get("/register", response_class=HTMLResponse)
async def register_redirect():
    """Redirect to auth page"""
    return RedirectResponse(url="/auth", status_code=302)

@router.get("/register/student", response_class=HTMLResponse)
async def register_student_redirect():
    """Redirect to auth page"""
    return RedirectResponse(url="/auth", status_code=302)

@router.get("/register/instructor", response_class=HTMLResponse)
async def register_instructor_redirect():
    """Redirect to auth page"""
    return RedirectResponse(url="/auth", status_code=302)