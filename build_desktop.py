import os
import sys
import PyInstaller.__main__
import streamlit

# Get streamlit library path
streamlit_dir = os.path.dirname(streamlit.__file__)

# Define static assets and source code files to bundle
# PyInstaller uses ";" as separator on Windows
datas = [
    (os.path.join(streamlit_dir, "static"), "streamlit/static"),
    ("app.py", "."),
    ("analytics.py", "."),
    ("data_loader.py", "."),
]

# Run PyInstaller
PyInstaller.__main__.run([
    "launch_app.py",
    "--onefile",
    "--name=MYM_Analisis_Ventas",
    "--hidden-import=streamlit",
    "--collect-all=streamlit",
    *sum([["--add-data", f"{src};{dst}"] for src, dst in datas], []),
    "--clean",
])
