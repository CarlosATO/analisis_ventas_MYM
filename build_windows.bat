@echo off
echo Preparando entorno y compilando Dashboard Comercial MYM...
call .venv\Scripts\activate
pip install -r requirements.txt
python build_desktop.py
pause
