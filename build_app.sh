#!/bin/zsh
# 맥에서 직접 ClaudePet.app 빌드 (권한/격리 문제 없음)
set -e
cd "$(dirname "$0")"
APP=ClaudePet.app
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp claude_pet.py "$APP/Contents/Resources/"
cp -R frames "$APP/Contents/Resources/frames"
cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key><string>ClaudePet</string>
    <key>CFBundleDisplayName</key><string>Claude Pet</string>
    <key>CFBundleIdentifier</key><string>com.yeongyu.claudepet</string>
    <key>CFBundleVersion</key><string>1.0</string>
    <key>CFBundleShortVersionString</key><string>1.0</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>CFBundleExecutable</key><string>ClaudePet</string>
    <key>LSUIElement</key><true/>
    <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
PLIST
cat > "$APP/Contents/MacOS/ClaudePet" <<'LAUNCH'
#!/bin/zsh
DIR="$(cd "$(dirname "$0")/../Resources" && pwd)"
CANDIDATES=(
  /opt/homebrew/bin/python3
  /usr/local/bin/python3
  /Library/Frameworks/Python.framework/Versions/Current/bin/python3
  /usr/bin/python3
)
for PY in $CANDIDATES; do
  if [ -x "$PY" ] && "$PY" -c "import AppKit" >/dev/null 2>&1; then
    exec "$PY" "$DIR/claude_pet.py"
  fi
done
osascript -e 'display dialog "pyobjc가 필요해서 설치할게요 (최초 1회)" buttons {"확인"} default button 1 with title "Claude Pet"'
for PY in $CANDIDATES; do
  if [ -x "$PY" ]; then
    "$PY" -m pip install --user pyobjc-framework-Cocoa >/tmp/claudepet_pip.log 2>&1 || \
    "$PY" -m pip install --user --break-system-packages pyobjc-framework-Cocoa >>/tmp/claudepet_pip.log 2>&1
    if "$PY" -c "import AppKit" >/dev/null 2>&1; then
      exec "$PY" "$DIR/claude_pet.py"
    fi
  fi
done
osascript -e 'display dialog "설치 실패. 터미널에서: pip3 install pyobjc-framework-Cocoa" buttons {"확인"} default button 1 with title "Claude Pet"'
exit 1
LAUNCH
chmod +x "$APP/Contents/MacOS/ClaudePet"
echo "✅ $APP 빌드 완료 — 더블클릭으로 실행하세요"
