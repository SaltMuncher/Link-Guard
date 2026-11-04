@echo off
cd /d "%~dp0\.."
python -m pip install --upgrade pyinstaller || goto :fail
python -m PyInstaller --noconfirm --clean --onefile --noconsole --name LinkGuard ^
  --icon assets\linkguard.ico ^
  --paths desktop --paths shared ^
  --add-data "shared\rules.json;." ^
  --add-data "assets\linkguard.png;assets" ^
  desktop\run.py || goto :fail

set "NSIS=makensis"
where makensis >nul 2>nul || set "NSIS=%ProgramFiles(x86)%\NSIS\makensis.exe"
"%NSIS%" installer\windows\linkguard.nsi || goto :fail
echo.
echo Built dist\LinkGuard.exe and dist\LinkGuard-Setup.exe
pause
exit /b 0
:fail
echo Build failed.
pause
exit /b 1
