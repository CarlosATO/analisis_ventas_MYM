@echo off
echo Iniciando Dashboard MYM (Backend y Frontend)...

echo Arrancando Backend en nueva ventana...
start "Backend API" cmd /k "cd mym_desktop\backend && .\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"

echo Arrancando Frontend en nueva ventana...
start "Frontend Web" cmd /k "cd mym_desktop\frontend && npm run dev"

echo.
echo ========================================================
echo Los servidores se estan ejecutando en ventanas separadas.
echo - Frontend (App): http://localhost:5173
echo - Backend (API):  http://localhost:8000/docs
echo.
echo Para detenerlos, simplemente cierra sus respectivas ventanas negras.
echo ========================================================
pause
