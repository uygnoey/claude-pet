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

  # 런처는 컴파일된 Mach-O — 코드서명하려면 실행파일이 Mach-O여야 하고,
  # python을 exec가 아닌 fork+wait(자식)로 띄워야 책임 프로세스가 이 서명된
  # 번들(ClaudePet)로 남는다 → macOS가 권한을 python3.13이 아닌 앱에 기억.
  clang -O2 -arch arm64 -arch x86_64 -o "$APP/Contents/MacOS/ClaudePet" launcher.c 2>/dev/null \
    || clang -O2 -o "$APP/Contents/MacOS/ClaudePet" launcher.c
  chmod +x "$APP/Contents/MacOS/ClaudePet"

  sign_app
  echo "✅ 빌드 완료: $(pwd)/$APP"
}

# 앱 서명: 정식 Apple 인증서 > 로컬 자체서명(ClaudePet Local) > ad-hoc
# TCC/키체인 권한이 안정적으로 기억되려면 서명이 필요하다.
sign_app() {
  local id
  id=$(security find-identity -v -p codesigning 2>/dev/null \
        | grep -Eo '"(Developer ID Application|Apple Development)[^"]*"' | head -1 | tr -d '"')
  [ -z "$id" ] && id="ClaudePet Local"   # 자체서명 (없으면 아래 codesign이 실패 → ad-hoc)
  if codesign --force --identifier com.yeongyu.claudepet --sign "$id" "$APP" 2>/dev/null; then
    echo "🔏 서명: $id"
  else
    codesign --force --sign - "$APP" 2>/dev/null && echo "🔏 서명: ad-hoc (인증서 없음)"
  fi
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
    APP="$DEST" sign_app          # 설치본 재서명 (복사 후 봉인 보장)
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
    APP="$DEST" sign_app          # py 교체로 깨진 서명 봉인 재적용 (같은 인증서 → 권한 유지)
    echo "✅ 코드 갱신: $DEST"
    open "$DEST"
    echo "🐱 재시작!"
    ;;
  *)
    build
    echo "설치까지 하려면: ./build_app.sh install"
    ;;
esac
