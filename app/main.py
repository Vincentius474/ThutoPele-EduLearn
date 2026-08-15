from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import HTTPException
from pathlib import Path

from app.core.config import settings
from app.api.api_v1.api import api_router
from app.web.web import web_router
from app.utils.category_icons import category_icons, category_names, get_category_icon, get_category_color

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR.parent / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.cache_size = 0
templates.env.globals["category_icons"] = category_icons
templates.env.globals["category_names"] = category_names
templates.env.globals["get_category_icon"] = get_category_icon
templates.env.globals["get_category_color"] = get_category_color

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.state.templates = templates

app.include_router(api_router, prefix="/api/v1")
app.include_router(web_router)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return templates.TemplateResponse(
        "404.html",
        {"request": request, "title": "Page Not Found"},
        status_code=404
    )

@app.on_event("startup")
async def startup_event():
    """Validate templates on startup"""
    print(f"Templates directory: {TEMPLATES_DIR}")
    print(f"Static files directory: {STATIC_DIR}")
    print(f"Templates available in app.state")