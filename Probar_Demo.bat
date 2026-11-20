@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel% equ 0 (
    py -3 main.py --demo
) else (
    python main.py --demo
)
if errorlevel 1 (
    echo.
    echo No se pudo iniciar la demostracion. Instala Python 3.11 o superior con Tcl/Tk.
    pause
)
