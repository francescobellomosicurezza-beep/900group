@echo off
setlocal
cd /d "%~dp0"
title Novecento - Ordini

where py >nul 2>nul
if %errorlevel%==0 (
    set "PY=py -3"
) else (
    where python >nul 2>nul
    if errorlevel 1 (
        echo.
        echo Python non trovato. Installalo da https://www.python.org/downloads/
        echo e durante l'installazione spunta "Add python.exe to PATH".
        echo.
        pause
        exit /b 1
    )
    set "PY=python"
)

if not exist ".venv\Scripts\python.exe" (
    echo Preparazione ambiente, solo la prima volta...
    %PY% -m venv .venv || goto errore
)

".venv\Scripts\python.exe" -m pip install -q --disable-pip-version-check -r requirements.txt || goto errore
".venv\Scripts\python.exe" manage.py migrate -v 0 || goto errore
".venv\Scripts\python.exe" manage.py dati_demo || goto errore

for /f "usebackq delims=" %%p in (`".venv\Scripts\python.exe" manage.py porta_libera --da 8900`) do set "PORTA=%%p"
if not defined PORTA goto errore
set "URL=http://127.0.0.1:%PORTA%"

echo Novecento in avvio su %URL%  -  chiudi questa finestra per fermarla.
start "" /b powershell -NoProfile -Command "Start-Sleep -Seconds 3; Start-Process '%URL%'"
".venv\Scripts\python.exe" manage.py runserver 127.0.0.1:%PORTA%
goto fine

:errore
echo.
echo Si e' verificato un errore. Leggi il messaggio sopra.
pause
exit /b 1

:fine
endlocal
