@echo off
setlocal
chcp 65001 >nul
title Kisisel Hekimim 3.0 - Uygulama Sunucusu
cd /d "%~dp0"
echo =======================================================
echo   KISISEL HEKIMIM 3.0 - UYGULAMA BASLATICISI
echo =======================================================
echo.
where py >nul 2>nul
if not errorlevel 1 (
  py -3 --version >nul 2>nul
  if not errorlevel 1 (
    py -3 server.py
    goto finished
  )
)
where python >nul 2>nul
if not errorlevel 1 (
  python --version >nul 2>nul
  if not errorlevel 1 (
    python server.py
    goto finished
  )
)
echo [HATA] Python 3 bulunamadi. https://www.python.org/downloads/
echo Kurulumda "Add Python to PATH" secenegini isaretleyin.
pause
exit /b 1
:finished
set "KH_EXIT=%errorlevel%"
if not "%KH_EXIT%"=="0" (
  echo.
  echo [HATA] Sunucu beklenmedik sekilde kapandi. Hata kodu: %KH_EXIT%
  echo Ustteki hata mesajini inceleyin.
  pause
)
endlocal
