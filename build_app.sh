#!/bin/zsh
# Claude Pet 빌드/설치 스크립트
#
#   ./build_app.sh            # 레포 안에 ClaudePet.app 빌드만
#   ./build_app.sh install    # 빌드 → /Applications 설치 → 재시작 (추천)
#   ./build_app.sh update     # 코드만 갱신 (빠름: claude_pet.py만 교체 후 재시작)
#
set -e
cd "$(dirname "$0")"
APP=ClaudePet.app
DEST="/Applications/$APP"

build() {
  rm -rf "$APP"
  mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
  cp claude_pet.py "$APP/Contents/Resources/"
  cp -R frames "$APP/Contents/Resources/frames"
  find "$APP" -name ".DS_Store" -delete 2>/dev/null || true

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
  "$HOME/.pyenv/shims/python3"
  "$PYENV_ROOT/shims/python3"
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
  echo "✅ 빌드 완료: $(pwd)/$APP"
}

stop_pet() {
  pkill -f "Resources/claude_pet.py" 2>/dev/null && echo "· 실행 중이던 펫 종료" || true
  sleep 0.3
}

case "$1" in
  install)
    build
    stop_pet
    rm -rf "$DEST"
    cp -R "$APP" "$DEST"
    xattr -dr com.apple.quarantine "$DEST" 2>/dev/null || true
    echo "✅ 설치: $DEST"
    open "$DEST"
    echo "🐱 실행!"
    ;;
  update)
    if [ ! -d "$DEST" ]; then
      echo "⚠️  $DEST 가 없어요. 먼저 ./build_app.sh install"
      exit 1
    fi
    stop_pet
    cp claude_pet.py "$DEST/Contents/Resources/claude_pet.py"
    echo "✅ 코드 갱신: $DEST"
    open "$DEST"
    echo "🐱 재시작!"
    ;;
  *)
    build
    echo "설치까지 하려면: ./build_app.sh install"
    ;;
esac
