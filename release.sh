#!/bin/zsh
# 자체포함 ClaudePet.app 릴리즈: py2app 빌드 → Developer ID 서명 → 공증 → staple → zip
#
#   ./release.sh          # 전체 (build+sign+notarize)
#   ./release.sh build    # py2app 빌드만
#   ./release.sh sign     # Developer ID 서명만
#   ./release.sh notarize # 공증+staple+zip (사전: notary 프로파일 등록 필요)
#
# 공증 자격증명 최초 1회 등록:
#   xcrun notarytool store-credentials claudepet-notary \
#     --apple-id <개발자Apple ID> --team-id RXGNVSLYF5 --password <앱 암호>
set -e
cd "$(dirname "$0")"
PY="${PY:-$HOME/.pyenv/shims/python3}"
ID="Developer ID Application: Yeongyu Yang (RXGNVSLYF5)"
ENT="$(pwd)/entitlements.plist"
APP="dist/ClaudePet.app"
PROFILE="claudepet-notary"
ZIP="release/ClaudePet.zip"

build() {
  rm -rf build dist
  "$PY" setup.py py2app >/tmp/py2app.log 2>&1 || { echo "❌ py2app 실패:"; tail -25 /tmp/py2app.log; exit 1; }
  echo "✅ 빌드: $APP ($(du -sh "$APP" | cut -f1))"
}

sign() {
  # AppleDouble(._*)/.DS_Store/xattr 청소 — framework 루트에 잡파일 있으면
  # Gatekeeper가 "unsealed contents present..."로 거부함
  find "$APP" \( -name "._*" -o -name ".DS_Store" \) -delete
  dot_clean "$APP" 2>/dev/null || true
  xattr -cr "$APP" 2>/dev/null || true

  find "$APP/Contents" \( -name "*.so" -o -name "*.dylib" \) -type f -print0 \
    | while IFS= read -r -d '' f; do
        codesign -f --options runtime --timestamp --entitlements "$ENT" -s "$ID" "$f" 2>/dev/null
      done
  codesign -f --options runtime --timestamp --entitlements "$ENT" -s "$ID" \
    "$APP/Contents/Frameworks/Python.framework/Versions/3.13" 2>/dev/null || true
  for x in python ClaudePet; do
    [ -f "$APP/Contents/MacOS/$x" ] && \
      codesign -f --options runtime --timestamp --entitlements "$ENT" -s "$ID" "$APP/Contents/MacOS/$x" 2>/dev/null
  done
  codesign -f --options runtime --timestamp --entitlements "$ENT" \
    --identifier me.yeongyu.claudepet -s "$ID" "$APP"
  codesign --verify --deep --strict "$APP" && echo "✅ 서명 검증 통과"
}

notarize() {
  mkdir -p release; rm -f "$ZIP"
  # --norsrc: 리소스포크/xattr을 zip에 넣지 않음 → 압축 해제 시 ._* 재생성 방지
  /usr/bin/ditto -c -k --norsrc --keepParent "$APP" "$ZIP"
  echo "→ 공증 제출 (Apple 서버, 보통 1~5분)…"
  xcrun notarytool submit "$ZIP" --keychain-profile "$PROFILE" --wait
  xcrun stapler staple "$APP"
  rm -f "$ZIP"; /usr/bin/ditto -c -k --norsrc --keepParent "$APP" "$ZIP"
  echo "✅ 공증+staple 완료 → $ZIP"
  spctl -a -vv "$APP" 2>&1 | head -3
}

publish() {
  command -v gh >/dev/null 2>&1 || {
    echo "❌ gh CLI 필요: brew install gh && gh auth login (개인 계정으로)"; exit 1; }
  local TAG
  TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.1-beta")
  gh release upload "$TAG" "$ZIP" --clobber
  echo "🚀 GitHub Release 업로드 완료: $TAG ← $ZIP"
  gh release view "$TAG" --json assets -q '.assets[].name' 2>/dev/null || true
}

case "${1:-all}" in
  build)    build ;;
  sign)     sign ;;
  notarize) notarize ;;
  publish)  publish ;;                      # zip을 GitHub Release에 업로드만
  all)      build; sign; notarize ;;
  ship)     build; sign; notarize; publish ;;   # 전 과정 + 업로드까지 한 방
  *) echo "사용법: ./release.sh [build|sign|notarize|publish|all|ship]"; exit 1 ;;
esac
