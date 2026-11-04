#!/bin/sh
set -e
cd "$(dirname "$0")/.."
ROOT="$(pwd)"

python3 -m venv .buildenv --system-site-packages
.buildenv/bin/python -m pip install --upgrade pyinstaller
.buildenv/bin/python -m PyInstaller --noconfirm --clean --onedir --name LinkGuard \
  --paths desktop --paths shared \
  --add-data "shared/rules.json:." \
  --add-data "assets/linkguard.png:assets" \
  desktop/run.py

rm -rf build/AppDir
mkdir -p build/AppDir/usr/lib
cp -r dist/LinkGuard build/AppDir/usr/lib/linkguard
cp installer/linux/AppRun build/AppDir/AppRun
chmod +x build/AppDir/AppRun
cp installer/linux/linkguard.desktop build/AppDir/linkguard.desktop
cp assets/linkguard.png build/AppDir/linkguard.png
cp assets/linkguard.png build/AppDir/.DirIcon

TOOL=".buildenv/appimagetool"
if [ ! -x "$TOOL" ]; then
  curl -fL -o "$TOOL" https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
  chmod +x "$TOOL"
fi
ARCH=x86_64 "$TOOL" --appimage-extract-and-run build/AppDir dist/LinkGuard-x86_64.AppImage
echo "Built dist/LinkGuard-x86_64.AppImage"
