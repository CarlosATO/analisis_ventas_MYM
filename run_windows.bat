@echo off
echo Iniciando dashboard MYM...
python -m venv .venv
call .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
pause
