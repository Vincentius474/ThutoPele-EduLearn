@echo off
echo Starting FastAPI server...
start cmd /k "uvicorn app.main:app --reload"

echo Waiting for server to start...
timeout /t 5 /nobreak

echo Running seed script...
python seed_data.py

echo.
echo Setup complete! Press any key to exit.
pause > nul