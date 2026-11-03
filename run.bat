@echo off
echo ===================================================
echo   Starting Roadies
echo ===================================================
echo Disabling Docker Bake to avoid permission prompts...
set COMPOSE_BAKE=0
set DOCKER_BUILDKIT=1
docker compose up --build -d
echo.
echo ===================================================
echo Containers are running in the background!
echo - Frontend:  http://localhost:3000
echo - Backend:   http://localhost:8000/docs
echo ===================================================
echo.
pause
