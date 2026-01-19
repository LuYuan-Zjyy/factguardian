@echo off
REM Start FactGuardian services with environment variables from .env file

echo ========================================
echo FactGuardian Service Starter
echo ========================================
echo.

REM Get the directory of this script
set SCRIPT_DIR=%~dp0
set ENV_FILE=%SCRIPT_DIR%.env

REM Check if .env file exists
if not exist "%ENV_FILE%" (
    echo [ERROR] .env file not found: %ENV_FILE%
    echo Please create a .env file with the following content:
    echo   DEEPSEEK_API_KEY=your-deepseek-api-key
    echo   OPENAI_API_KEY=your-openai-api-key
    pause
    exit /b 1
)

echo [OK] Found .env file
echo.

REM Parse .env file and set environment variables
echo Loading environment variables...
for /f "usebackq tokens=1,2 delims==" %%a in ("%ENV_FILE%") do (
    if not "%%a"=="" if not "%%a:~0,1%"=="#" (
        set %%a=%%b
        echo   %%a=*** (set)
    )
)
echo.

REM Restart services
echo Restarting FactGuardian services...
docker-compose restart backend

echo.
echo [OK] Services restarted
echo.
echo To check service status:
echo   docker-compose ps
echo.
echo To view logs:
echo   docker-compose logs -f backend
echo.
pause
