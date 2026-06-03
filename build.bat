@echo off
setlocal
cd /d "%~dp0"

set "DIST_DIR=%~dp0dist\ScreenRPA"

echo [0/3] Clean previous package output...
if exist "%DIST_DIR%\ScreenRPA.exe" (
  taskkill /f /im ScreenRPA.exe >nul 2>&1
)
if exist "%DIST_DIR%" (
  attrib -r "%DIST_DIR%\*" /s /d >nul 2>&1
  rmdir /s /q "%DIST_DIR%" >nul 2>&1
  if exist "%DIST_DIR%" (
    echo Unable to remove "%DIST_DIR%". Close ScreenRPA or any tool that is using files in this folder.
    goto :fail
  )
)

echo [1/3] Front-end build (Vite^)...
pushd frontend
call npm ci
if errorlevel 1 goto :fail
call npm run build
if errorlevel 1 goto :fail
popd

echo [2/3] PyInstaller packaging (onedir^)...
pushd backend
call python -m pip install -r requirements.txt -q
if errorlevel 1 goto :fail
call python -m PyInstaller "%~dp0packaging\screen-rpa.spec" --distpath "%~dp0dist" --workpath "%~dp0build\pyi" --noconfirm
if errorlevel 1 goto :fail
popd

echo [3/3] Completed.
echo   Run directory: %~dp0dist\ScreenRPA\
echo   Main program:   %~dp0dist\ScreenRPA\ScreenRPA.exe
echo   App icon:       %~dp0logo.ico
echo   Shortcut hotkey (installer): Ctrl+Alt+R
echo   Optional installer: Install Inno Setup and run ISCC packaging\installer.iss
goto :eof

:fail
echo Build failed.
popd 2>nul
exit /b 1
