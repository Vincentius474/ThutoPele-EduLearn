from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import HTTPException
from pathlib import Path
from starlette.responses import HTMLResponse

from app.core.config import settings, get_cors_origins
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
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    debug=settings.DEBUG,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.state.templates = templates

app.include_router(api_router, prefix="/api/v1")
app.include_router(web_router)


@app.middleware("http")
async def maintenance_mode_middleware(request: Request, call_next):
    if settings.MAINTENANCE_MODE and request.url.path not in {"/health", "/maintenance"}:
        return HTMLResponse(
            """
            <html><body style='font-family: Arial, sans-serif; text-align:center; padding:40px;'>
            <h1>Maintenance Mode</h1>
            <p>We are performing scheduled maintenance. Please try again shortly.</p>
            </body></html>
            """,
            status_code=503,
        )
    return await call_next(request)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "environment": settings.ENVIRONMENT, "maintenance_mode": settings.MAINTENANCE_MODE}


@app.get("/maintenance", response_class=HTMLResponse)
async def maintenance_page():
    return HTMLResponse(
        f"""
        <html><body style='font-family: Arial, sans-serif; text-align:center; padding:40px;'>
        <h1>Maintenance Mode</h1>
        <p>{settings.MAINTENANCE_MESSAGE}</p>
        </body></html>
        """
    )


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
    print(f"Environment: {settings.ENVIRONMENT}")
    print(f"Debug mode: {settings.DEBUG}")
    print(f"Maintenance mode: {settings.MAINTENANCE_MODE}")
    print(f"Templates directory: {TEMPLATES_DIR}")
    print(f"Static files directory: {STATIC_DIR}")
    print(f"Templates available in app.state")