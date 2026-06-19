@echo off
echo Iniciando Backend (API) en el puerto 8000...
cd mym_desktop\backend
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
pause
