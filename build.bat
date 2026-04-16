@echo off
set "PROJECT_DIR=%~dp0"
set "PYTHON_BIN=python"
if exist "%PROJECT_DIR%.venv\Scripts\python.exe" set "PYTHON_BIN=%PROJECT_DIR%.venv\Scripts\python.exe"

"%PYTHON_BIN%" -c "import tkinter" >nul 2>&1
if errorlevel 1 (
  echo Tkinter/Tk is not available for "%PYTHON_BIN%".
  echo Install Python with Tk support before building the Windows GUI binary.
  exit /b 1
)

"%PYTHON_BIN%" -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name "MikroTik Config Generator" ^
  --add-data "templates;templates" ^
  main.py
