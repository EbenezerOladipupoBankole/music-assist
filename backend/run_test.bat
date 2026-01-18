@echo off
echo Running Comprehensive User Test...
echo.
echo Make sure the server is running on port 8000!
echo.
timeout /t 3
cd /d "%~dp0"
python comprehensive_user_test.py
pause
