@echo off
REM Build script for embedded Docker setup on Windows

echo Building Multi-Cloud Integrator with embedded configuration...

REM Backup original .dockerignore if exists
if exist ".dockerignore" (
    copy .dockerignore .dockerignore.backup >nul
)

REM Use the embedded dockerignore
copy .dockerignore.embedded .dockerignore >nul

REM Build the image
docker-compose -f docker-compose.embedded.yml build --no-cache

REM Restore original .dockerignore
if exist ".dockerignore.backup" (
    move .dockerignore.backup .dockerignore >nul
) else (
    del .dockerignore 2>nul
)

echo.
echo ✅ Embedded Docker image built successfully!
echo.
echo Usage examples:
echo   # Run with embedded configuration:
echo   docker-compose -f docker-compose.embedded.yml run --rm multicloud-integrator
echo.
echo   # Check configuration:
echo   docker-compose -f docker-compose.embedded.yml run --rm multicloud-integrator python main.py config-check
echo.
echo   # List providers:
echo   docker-compose -f docker-compose.embedded.yml run --rm multicloud-integrator python main.py providers