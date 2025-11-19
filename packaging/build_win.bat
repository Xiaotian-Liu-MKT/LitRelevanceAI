@echo off
setlocal

REM Build Windows executable for LitRelevanceAI (PyQt6 GUI)
echo Installing PyInstaller...
python -m pip install --upgrade pip pyinstaller

echo Building with PyInstaller spec...
pyinstaller "%~dp0pyinstaller\litrx.spec"

if %errorlevel% neq 0 (
  echo Build failed.
  exit /b %errorlevel%
)

echo.
echo Build succeeded. Executable is under dist\LitRelevanceAI\LitRelevanceAI.exe
echo You can distribute the entire dist\LitRelevanceAI folder.
pause
endlocal

