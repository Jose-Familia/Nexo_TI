@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel% equ 0 (
    py -3 main.py
) else (
    python main.py
)
if errorlevel 1 (
    echo.
    echo No se pudo iniciar Nexo TI. Instala Python 3.11 o superior con Tcl/Tk.
    echo Revisa tambien el mensaje anterior para identificar el error.
    pause
)
