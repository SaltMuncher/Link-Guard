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

APPIMAGETOOL_VERSION="1.9.1"
APPIMAGETOOL_SHA256="ed4ce84f0d9caff66f50bcca6ff6f35aae54ce8135408b3fa33abfc3cb384eb0"
APPIMAGETOOL_URL="https://github.com/AppImage/appimagetool/releases/download/$APPIMAGETOOL_VERSION/appimagetool-x86_64.AppImage"

TOOL=".buildenv/appimagetool"
if [ ! -x "$TOOL" ] || ! echo "$APPIMAGETOOL_SHA256  $TOOL" | sha256sum -c - >/dev/null 2>&1; then
  curl -fL -o "$TOOL.tmp" "$APPIMAGETOOL_URL"
  if ! echo "$APPIMAGETOOL_SHA256  $TOOL.tmp" | sha256sum -c -; then
    rm -f "$TOOL.tmp"
    echo "appimagetool checksum mismatch, refusing to run it" >&2
    exit 1
  fi
  chmod +x "$TOOL.tmp"
  mv "$TOOL.tmp" "$TOOL"
fi
ARCH=x86_64 "$TOOL" --appimage-extract-and-run build/AppDir dist/LinkGuard-x86_64.AppImage
echo "Built dist/LinkGuard-x86_64.AppImage"