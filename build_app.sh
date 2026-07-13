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
    <key>CFBundleIdentifier</key><string>me.yeongyu.claudepet</string>
    <key>CFBundleVersion</key><string>1.0</string>
    <key>CFBundleShortVersionString</key><string>1.0</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>CFBundleExecutable</key><string>ClaudePet</string>
    <key>LSUIElement</key><true/>
    <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
PLIST

  # 런처는 컴파일된 Mach-O (코드서명하려면 실행파일이 Mach-O여야 함)
  clang -O2 -arch arm64 -arch x86_64 -o "$APP/Contents/MacOS/ClaudePet" launcher.c 2>/dev/null \
    || clang -O2 -o "$APP/Contents/MacOS/ClaudePet" launcher.c
  chmod +x "$APP/Contents/MacOS/ClaudePet"

  # 번들 안에 python 실행파일 복사 → 실행 시 [NSBundle mainBundle]이 ClaudePet.app으로
  # 잡혀 macOS가 문서앱(org.python.python)으로 오인하지 않음 → 보호폴더 프롬프트 제거.
  local PY PYPREFIX PYBIN
  PY=$(find_py)
  if [ -n "$PY" ]; then
    PYPREFIX=$("$PY" -c 'import sys;print(sys.prefix)' 2>/dev/null)
    PYBIN="$PYPREFIX/Resources/Python.app/Contents/MacOS/Python"
    [ -x "$PYBIN" ] || PYBIN="$PY"
    cp "$PYBIN" "$APP/Contents/MacOS/ClaudePet_py"
    chmod +x "$APP/Contents/MacOS/ClaudePet_py"
    echo "🐍 번들 python: $PYBIN"
  else
    echo "⚠️  AppKit 가능한 python을 못 찾음 — 번들 python 없이 빌드(폴백 실행)"
  fi

  sign_app
  echo "✅ 빌드 완료: $(pwd)/$APP"
}

# AppKit 임포트 되는 framework python 하나 찾기
find_py() {
  local c
  for c in "$HOME/.pyenv/shims/python3" /opt/homebrew/bin/python3 \
           /usr/local/bin/python3 \
           /Library/Frameworks/Python.framework/Versions/Current/bin/python3 \
           /usr/bin/python3; do
    [ -x "$c" ] && "$c" -c "import AppKit" >/dev/null 2>&1 && { echo "$c"; return; }
  done
}

# 앱 서명: 정식 Apple 인증서 > 로컬 자체서명(ClaudePet Local) > ad-hoc
# TCC/키체인 권한이 안정적으로 기억되려면 서명이 필요하다.
sign_app() {
  local id; local -a opts
  local ENT="$(cd "$(dirname "$0")" && pwd)/entitlements.plist"
  local pybin="$APP/Contents/MacOS/ClaudePet_py"
  id=$(security find-identity -v -p codesigning 2>/dev/null \
        | grep -Eo '"(Developer ID Application|Apple Development)[^"]*"' | head -1 | tr -d '"')
  if [ -n "$id" ]; then
    # 공증 요건: 하드닝 런타임 + 보안 타임스탬프 + python용 엔타이틀먼트
    opts=(--options runtime --timestamp)
    [ -f "$ENT" ] && opts+=(--entitlements "$ENT")
  else
    id="ClaudePet Local"; opts=()          # 로컬 자체서명 (없으면 codesign 실패 → ad-hoc)
  fi
  # 중첩 실행파일(번들 python) 먼저 서명 → 그다음 번들
  [ -f "$pybin" ] && codesign --force "${opts[@]}" --sign "$id" "$pybin" 2>/dev/null
  if codesign --force --identifier me.yeongyu.claudepet "${opts[@]}" --sign "$id" "$APP" 2>/dev/null; then
    echo "🔏 서명: $id"
  else
    [ -f "$pybin" ] && codesign --force --sign - "$pybin" 2>/dev/null
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
