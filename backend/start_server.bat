@echo off
echo Starting Music-Assist RAG Server...
echo.
cd /d "%~dp0"
python -m uvicorn main:app --port 8000
pause
