@echo off
echo Activating a virtual environment...

:: Проверка дали папката venv съществува
if not exist "venv\Scripts\activate" (
    echo [ERROR] The venv folder was not found!
    pause
    exit /b
)

:: Activation and startup
call venv\Scripts\activate
python app.py

:: Keeps the window open when an error occurs or the program is closed
:: pause