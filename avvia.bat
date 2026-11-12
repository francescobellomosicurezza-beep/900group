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

echo App in avvio su http://127.0.0.1:8000  -  chiudi questa finestra per fermarla.
start "" "http://127.0.0.1:8000"
".venv\Scripts\python.exe" manage.py runserver 127.0.0.1:8000
goto fine

:errore
echo.
echo Si e' verificato un errore. Leggi il messaggio sopra.
pause
exit /b 1

:fine
endlocal
