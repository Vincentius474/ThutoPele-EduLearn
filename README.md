"# ThutoPele EduLearn

## Overview

**ThutoPele EduLearn** is a FastAPI-powered e-learning platform built with server-rendered templates, REST APIs, and Supabase integration. The platform supports student, instructor, and admin experiences with course listings, tutorials, blogs, events, enrollment management, authentication, and a role-based dashboard.

## Key Features

- FastAPI backend with Jinja2 rendered web pages
- Supabase database authentication, storage, and realtime services
- Role-based dashboards for students, instructors, and administrators
- Course browsing, tutorials, blog posts, events, and contact pages
- Programming assignment and quiz activity features in student dashboard
- Static assets served from `/static`
- API versioning with `/api/v1` prefix
- Health check endpoint at `/health`

## Tech Stack

- Python 3.x
- FastAPI
- Uvicorn
- Supabase (Postgres + Auth + Storage)
- Jinja2 templates
- Pydantic and Pydantic Settings
- HTTPX
- pytest / pytest-asyncio

## Repository Structure

- `app/` - main application package
  - `api/` - API router definitions and endpoint modules
  - `core/` - configuration, security, Supabase client, and dependencies
  - `models/` - data models and schemas
  - `schemas/` - Pydantic request/response schemas
  - `services/` - business logic services
  - `templates/` - HTML templates for web views
  - `utils/` - helper utilities
  - `web/` - web routes and authentication pages
- `static/` - CSS, images, and client-side JavaScript files
- `tests/` - automated test suite
- `run.py` - application startup entrypoint
- `requirements.txt` - Python dependencies
- `seed_data.py` - optional script to populate sample Supabase data

## Prerequisites

- Python 3.11+ (or compatible 3.x)
- A Supabase project with API credentials
- Git (optional)

## Installation

1. Clone the repository:

```bash
git clone https://github.com/your-org/ThutoPele-EduLearn.git
cd "ThutoPele EduLearn"
```

2. Create and activate a virtual environment:

```bash
python -m venv .venv
.\.venv\Scripts\activate
```

3. Install requirements:

```bash
pip install -r requirements.txt
```

## Environment Variables

Create a `.env` file in the project root with values for your Supabase project and application secrets. Example:

```dotenv
BASE_URL=http://localhost:8000
SUPABASE_URL=https://your-supabase-url.supabase.co
SUPABASE_KEY=your-public-supabase-key
SUPABASE_SERVICE_KEY=your-service-role-key
SUPABASE_JWT_SECRET=your-jwt-secret
SECRET_KEY=your-fastapi-secret-key
```

> Note: `SUPABASE_SERVICE_KEY` is required only for server-side administration tasks and seeding.

## Running the Application

Start the development server:

```bash
python run.py
```

Then open:

```text
http://localhost:8000
```

### Alternative run command

```bash
uvicorn app.main:app --reload
```

## API Endpoints

The application exposes a versioned API under `/api/v1`.

- `/api/v1/auth` - authentication endpoints
- `/api/v1/users` - user management
- `/api/v1/courses` - course listings and details
- `/api/v1/admin` - administration endpoints
- `/api/v1/vpl` - virtual programming lab related endpoints

The OpenAPI documentation is available at:

```text
http://localhost:8000/api/v1/openapi.json
```

## Seed Data

The repository includes `seed_data.py` to load sample courses, users, and related content into Supabase.

Run the server first, then execute:

```bash
python seed_data.py
```

This script expects Supabase credentials in `.env` and will connect to `http://localhost:8000/health` to verify the API is available.

## Testing

Run the automated tests with:

```bash
pytest
```

The `tests/` directory contains API and integration tests for core functionality.

## Development Notes

- Templates are located in `app/templates/`
- Static assets are mounted from `static/` and served at `/static`
- The app uses `app.core.config.Settings` to load environment configuration
- The primary application object is defined in `app/api/api_v1/api.py`

## Deployment

For production deployment, use a process manager and secure environment variables. Example with Uvicorn:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Ensure `DEBUG` mode is disabled and secret keys are kept safe.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Install dependencies
4. Add tests for new behavior
5. Open a pull request

## License


" 
