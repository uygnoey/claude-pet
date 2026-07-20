#!/bin/zsh
# 자체포함 ClaudePet.app 릴리즈: py2app 빌드 → Developer ID 서명 → 공증 → staple → zip
#
#   ./release.sh           # 전체 (build+sign+notarize, + universal2 python 있으면 유니버설도)
#   ./release.sh build     # py2app 빌드만 (현재 머신 아키텍처)
#   ./release.sh sign      # Developer ID 서명만
#   ./release.sh notarize  # 공증+staple+zip (사전: notary 프로파일 등록 필요)
#   ./release.sh universal # 유니버설(arm64+x86_64) 빌드+서명+공증 → ClaudePet-universal.zip
#   ./release.sh dmg       # 수동 설치용 dmg 생성+공증 (앱 빌드/공증 후) → ClaudePet.dmg
#
# 유니버설 빌드 사전 준비 (최초 1회):
#   python.org 공식 macOS 설치본(universal2) 설치 후
#   /Library/Frameworks/Python.framework/Versions/Current/bin/python3 -m pip install py2app pyobjc
#
# 공증 자격증명 최초 1회 등록:
#   xcrun notarytool store-credentials claudepet-notary \
#     --apple-id <개발자Apple ID> --team-id RXGNVSLYF5 --password <앱 암호>
set -e
cd "$(dirname "$0")"
PY="${PY:-$HOME/.pyenv/shims/python3}"
# 유니버설 빌드용 python — python.org 공식 설치본(universal2)이어야 함
UPY="${UPY:-/Library/Frameworks/Python.framework/Versions/Current/bin/python3}"
ID="Developer ID Application: Yeongyu Yang (RXGNVSLYF5)"
ENT="$(pwd)/entitlements.plist"
APP="dist/ClaudePet.app"
UDIST="dist-universal"
UAPP="$UDIST/ClaudePet.app"
PROFILE="claudepet-notary"
ZIP="release/ClaudePet.zip"
UZIP="release/ClaudePet-universal.zip"
DMG="release/ClaudePet.dmg"           # arm64(Apple Silicon) 수동 설치 dmg. 자동업데이트는 zip 사용
UDMG="release/ClaudePet-universal.dmg" # 유니버설(Intel+ARM) 수동 설치 dmg
NOTES="RELEASE_NOTES.md"   # 릴리즈 노트 고정 파일 (git 히스토리 노출 대신 이 내용 사용)

build() {
  rm -rf build dist
  "$PY" setup.py py2app >/tmp/py2app.log 2>&1 || { echo "❌ py2app 실패:"; tail -25 /tmp/py2app.log; exit 1; }
  echo "✅ 빌드: $APP ($(du -sh "$APP" | cut -f1))"
}

# 유니버설(arm64+x86_64) 빌드 — Intel Mac 지원용. 기존 build()와 별개 산출물.
# pyenv 파이썬은 단일 아키텍처라 못 쓰고, python.org universal2 설치본이 필요.
build_universal() {
  if [ ! -x "$UPY" ]; then
    echo "❌ universal2 python 없음: $UPY"
    echo "   python.org 공식 설치본 설치 후: $UPY -m pip install py2app pyobjc"
    return 1
  fi
  local real archs
  real=$("$UPY" -c 'import sys; print(sys.executable)')
  archs=$(lipo -archs "$real" 2>/dev/null || true)
  case "$archs" in
    *x86_64*arm64*|*arm64*x86_64*) ;;
    *) echo "❌ $UPY 는 universal2가 아님 (archs: ${archs:-알수없음})"
       echo "   python.org 공식 macOS 설치본(universal2)을 설치하세요"; return 1 ;;
  esac
  "$UPY" -c 'import py2app, objc' 2>/dev/null || {
    echo "❌ py2app/pyobjc 미설치: $UPY -m pip install py2app pyobjc"; return 1; }

  rm -rf build "$UDIST"
  "$UPY" setup.py py2app --arch universal2 --dist-dir "$UDIST" >/tmp/py2app-universal.log 2>&1 \
    || { echo "❌ universal py2app 실패:"; tail -25 /tmp/py2app-universal.log; exit 1; }
  archs=$(lipo -archs "$UAPP/Contents/MacOS/python" 2>/dev/null || true)
  case "$archs" in
    *x86_64*arm64*|*arm64*x86_64*) ;;
    *) echo "❌ 산출물이 유니버설이 아님 (archs: ${archs:-알수없음}) — /tmp/py2app-universal.log 확인"; exit 1 ;;
  esac
  echo "✅ 유니버설 빌드: $UAPP ($(du -sh "$UAPP" | cut -f1), archs: $archs)"
}

sign() {
  local app="${1:-$APP}"
  # AppleDouble(._*)/.DS_Store/xattr 청소 — framework 루트에 잡파일 있으면
  # Gatekeeper가 "unsealed contents present..."로 거부함
  find "$app" \( -name "._*" -o -name ".DS_Store" \) -delete
  dot_clean "$app" 2>/dev/null || true
  xattr -cr "$app" 2>/dev/null || true

  find "$app/Contents" \( -name "*.so" -o -name "*.dylib" \) -type f -print0 \
    | while IFS= read -r -d '' f; do
        codesign -f --options runtime --timestamp --entitlements "$ENT" -s "$ID" "$f" 2>/dev/null
      done
  # 내장 Python.framework 버전(3.13 등)은 빌드에 쓴 파이썬을 따라감 → 버전 무관하게 서명
  local fw
  for fw in "$app"/Contents/Frameworks/Python.framework/Versions/*(N); do
    [ -d "$fw" ] && [ ! -L "$fw" ] && \
      codesign -f --options runtime --timestamp --entitlements "$ENT" -s "$ID" "$fw" 2>/dev/null || true
  done
  for x in python ClaudePet; do
    [ -f "$app/Contents/MacOS/$x" ] && \
      codesign -f --options runtime --timestamp --entitlements "$ENT" -s "$ID" "$app/Contents/MacOS/$x" 2>/dev/null
  done
  codesign -f --options runtime --timestamp --entitlements "$ENT" \
    --identifier me.yeongyu.claudepet -s "$ID" "$app"
  codesign --verify --deep --strict "$app" && echo "✅ 서명 검증 통과: $app"
}

# 공증 전송 — Apple 서버 TLS/네트워크 일시 오류(-1200 등)에 대비해 재시도
notary_submit() {
  local file="$1" i
  for i in 1 2 3 4 5; do
    if xcrun notarytool submit "$file" --keychain-profile "$PROFILE" --wait; then
      return 0
    fi
    echo "⚠️  공증 전송 실패 (시도 $i/5) — 20초 후 재시도…"; sleep 20
  done
  echo "❌ 공증 5회 연속 실패: $file"; return 1
}

notarize() {
  local app="${1:-$APP}" zip="${2:-$ZIP}"
  mkdir -p release; rm -f "$zip"
  # --norsrc: 리소스포크/xattr을 zip에 넣지 않음 → 압축 해제 시 ._* 재생성 방지
  /usr/bin/ditto -c -k --norsrc --keepParent "$app" "$zip"
  echo "→ 공증 제출 (Apple 서버, 보통 1~5분)…"
  notary_submit "$zip"
  xcrun stapler staple "$app"
  rm -f "$zip"; /usr/bin/ditto -c -k --norsrc --keepParent "$app" "$zip"
  echo "✅ 공증+staple 완료 → $zip"
  spctl -a -vv "$app" 2>&1 | head -3
}

# 유니버설 전체 파이프라인 (빌드→서명→공증)
universal() {
  build_universal
  sign "$UAPP"
  notarize "$UAPP" "$UZIP"
}

# 앱 하나를 드래그-설치 dmg로 패키징 + 공증 + staple. $1=app 디렉터리, $2=dmg 경로.
# 내부 앱은 이미 서명+공증+staple 된 상태 → dmg 컨테이너만 추가 공증.
one_dmg() {
  local app="$1" dmg="$2"
  [ -d "$app" ] || { echo "⚠️  $app 없음 — $dmg 건너뜀"; return 0; }
  local stage; stage=$(mktemp -d)
  /usr/bin/ditto "$app" "$stage/ClaudePet.app"
  ln -s /Applications "$stage/Applications"   # 드래그 설치용 심볼릭
  mkdir -p release; rm -f "$dmg"
  hdiutil create -volname "ClaudePet" -srcfolder "$stage" -ov -format UDZO "$dmg" >/dev/null
  rm -rf "$stage"
  echo "→ dmg 공증 제출: $dmg (Apple 서버, 보통 1~5분)…"
  notary_submit "$dmg"
  xcrun stapler staple "$dmg"
  xcrun stapler validate "$dmg" >/dev/null 2>&1 && echo "✅ dmg 완료 → $dmg ($(du -sh "$dmg" | cut -f1))"
}

# 수동 다운로드용 DMG (드래그 → Applications). 자동업데이트는 zip이 담당.
# zip과 동일하게 arm64용 + 유니버설(Intel)용 둘 다 만든다.
make_dmg() {
  one_dmg "$APP" "$DMG"                        # arm64 (Apple Silicon) — 항상
  [ -d "$UAPP" ] && one_dmg "$UAPP" "$UDMG"    # 유니버설(Intel+ARM) — universal 빌드 있을 때
}

# all/ship 에서: universal2 python 있으면 유니버설도 만들고, 없으면 조용히 건너뜀
maybe_universal() {
  if [ -x "$UPY" ]; then
    universal
  else
    echo "⚠️  universal2 python($UPY) 없음 — 유니버설 빌드 건너뜀 (arm64 zip만 배포)"
  fi
}

# 현재 버전 (claude_pet.py의 APP_VERSION이 유일한 진실)
cur_version() {
  grep -Eo 'APP_VERSION = "[^"]+"' claude_pet.py | cut -d'"' -f2
}

# ./release.sh ship 0.2  →  APP_VERSION 갱신 + 커밋 + 태그 + 푸시
bump_version() {
  local NEW="$1"
  [ -z "$NEW" ] && return 0
  NEW="${NEW#v}"
  sed -i '' -E "s/^APP_VERSION = \"[^\"]+\"/APP_VERSION = \"$NEW\"/" claude_pet.py
  git add claude_pet.py
  git commit -m "v$NEW"
  git tag "v$NEW"
  git push && git push --tags
  echo "🔖 버전 업: v$NEW (커밋+태그+푸시 완료)"
}

publish() {
  command -v gh >/dev/null 2>&1 || {
    echo "❌ gh CLI 필요: brew install gh && gh auth login (개인 계정으로)"; exit 1; }
  local TAG="v$(cur_version)"
  local -a files=("$ZIP")
  [ -f "$UZIP" ] && files+=("$UZIP")        # 유니버설 zip 있으면 같이 업로드
  [ -f "$DMG" ]  && files+=("$DMG")         # arm64 dmg
  [ -f "$UDMG" ] && files+=("$UDMG")        # 유니버설 dmg
  if gh release view "$TAG" >/dev/null 2>&1; then
    gh release upload "$TAG" "${files[@]}" --clobber
    gh release edit "$TAG" --notes-file "$NOTES"   # 노트도 고정본으로 갱신
    echo "🚀 기존 릴리즈에 업로드: $TAG ← ${files[*]}"
  else
    gh release create "$TAG" "${files[@]}" --title "ClaudePet $TAG" --notes-file "$NOTES"
    echo "🚀 새 릴리즈 생성: $TAG ← ${files[*]}"
  fi
}

case "${1:-all}" in
  build)     build ;;
  sign)      sign ;;
  notarize)  notarize ;;
  universal) universal ;;                   # 유니버설(arm64+x86_64) 빌드+서명+공증
  dmg)       make_dmg ;;                     # 수동 설치용 dmg 생성+공증 (앱 빌드/공증 선행 필요)
  publish)   publish ;;                     # zip/dmg를 GitHub Release에 업로드만
  all)       build; sign; notarize; maybe_universal; make_dmg ;;
  ship)      bump_version "$2"; build; sign; notarize; maybe_universal; make_dmg; publish ;;
  *) echo "사용법: ./release.sh [build|sign|notarize|universal|dmg|publish|all|ship [새버전]]"
     echo "  예: ./release.sh ship 0.2   # 버전업+빌드+공증+dmg+새 릴리즈 생성까지 한 방"
     exit 1 ;;
esac
