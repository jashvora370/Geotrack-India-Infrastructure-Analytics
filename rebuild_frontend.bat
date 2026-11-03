@echo off
echo ===================================================
echo   Rebuilding Roadies Frontend
echo ===================================================
set COMPOSE_BAKE=0
set DOCKER_BUILDKIT=1
docker compose stop frontend
docker compose rm -f frontend
docker compose build --no-cache frontend
docker compose up -d frontend
echo.
echo ===================================================
echo Frontend rebuilt and restarted!
echo Please open http://localhost:3000 and do a hard refresh (Ctrl + F5).
echo ===================================================
pause
