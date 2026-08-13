#!/bin/zsh
# 자체포함 ClaudePet.app 릴리즈: py2app 빌드 → Developer ID 서명 → 공증 → staple → zip
#
#   ./release.sh           # 인자 없음 → 사용법만 출력하고 종료(1). 예전에는 이게
#                          #   전체(build+sign+notarize+universal+dmg)를 돌렸다.
#   ./release.sh all       # 전체. 문서상 [NEVER] — 단계별 기록이 남지 않는다.
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

# 동봉 펫 자산 게이트. 산출물 안의 .claude_pet 이 저장소 소스와 같은지 확인한다.
# setup.py 는 '선언'만, build_app.sh 는 '복사'만 할 뿐 아무도 확인하지 않았다 —
# 빠진 채로 서명·공증까지 가면 사용자에게는 '펫이 안 생긴다'로만 보인다.
# build_universal() 이 이미 lipo -archs 로 산출물을 사후 검증하는 것과 같은 모양·같은 강도.
verify_bundled_pet_payload() {
  local app="$1"
  "$PY" verify_pet_payload.py "$app/Contents/Resources/.claude_pet" || {
    echo "❌ 동봉 펫 자산 검사 실패 — 서명/업로드하지 않습니다: $app"; return 1; }
}

# 업로드 '직전'에는 디렉터리가 아니라 올라갈 파일 자체를 열어서 확인한다.
# zip/dmg 는 만든 뒤에 dist/ 가 바뀌었을 수도, 파일만 따로 손댔을 수도 있다 —
# 빌드된 디렉터리를 확인하는 것은 '배포되는 것'이 아니라 '한때 있던 사본'을
# 확인하는 것이다. (업데이터 preflight 가 추출본이 아닌 옛 사본을 보던 것과 같은 실수)
verify_upload_artifact() {
  local artifact="$1" tmp root rc=0 mounted=0
  # 없는 파일은 통과가 아니라 실패다. 예전에는 여기서 return 0 이었는데,
  # 그러면 '올릴 파일이 아예 없을 때' 게이트가 성공을 보고한다 — 검사를 못 한
  # 것과 검사를 통과한 것이 똑같이 보이는, 게이트가 가져서는 안 되는 모양이다.
  if [ ! -f "$artifact" ]; then
    echo "❌ 업로드 대상이 없습니다: $artifact"; return 1
  fi
  # ── 풀기 '전에' 아카이브를 본다 ──────────────────────────────────────
  # 이것만이 바이트가 디스크에 닿기 전에 돌 수 있는 검사다. 풀고 나서 훑는
  # 것으로는 대체되지 않는다: 밖으로 나가는 멤버는 우리가 훑을 폴더 바깥에
  # 이미 쓰인 뒤이고, 우리는 안쪽만 훑으므로 영영 안 보인다. 업데이터의 zip
  # 검사를 ditto 앞으로 옮긴 것과 같은 이유이고, 순서가 곧 검사다 —
  # 아래 extract 뒤로 내리면 이 줄은 아무것도 막지 못한다.
  if ! "$PY" verify_release_artifact.py scan "$artifact"; then
    echo "❌ 업로드 대상 아카이브 안전성 검사 실패: $artifact"; return 1
  fi
  tmp=$(mktemp -d) || return 1
  root="$tmp"
  case "$artifact" in
    *.zip)
      ditto -x -k "$artifact" "$tmp" >/dev/null 2>&1 || rc=1
      ;;
    *.dmg)
      mkdir -p "$tmp/mnt" || rc=1                      # 없으면 attach 가 실패한다
      root="$tmp/mnt"
      [ $rc -eq 0 ] && { hdiutil attach "$artifact" -nobrowse -readonly -quiet \
                           -mountpoint "$tmp/mnt" && mounted=1 || rc=1; }
      ;;
    *) echo "❌ 검사할 줄 모르는 업로드 형식: $artifact"; rc=1 ;;
  esac
  if [ $rc -eq 0 ]; then
    # 앱은 '정확히 하나', 최상위에 있어야 한다. 여러 개거나 엉뚱한 깊이에 있으면
    # 무엇을 배포하는지 우리가 모른다는 뜻이므로, 아무거나 골라 검사하면 안 된다.
    #
    # 이름을 박아 넣고 세면 안 된다. 예전에는 ClaudePet.app(N) 으로 글롭해서
    # 개수가 0 아니면 1 이었고 — '여러 개' 분기는 실행될 수 없는 죽은 코드였다.
    # 정작 그 분기의 메시지는 (${#apps[@]}개) 로 여러 개를 상정하고 있었으니,
    # 의도는 적혀 있는데 코드가 그 의도를 구현하지 않는 상태였다. 그런 코드는
    # 읽는 사람에게 '검사된다'고 말하면서 검사하지 않는다. 최상위 .app 을 전부
    # 센 뒤 이름을 따로 확인하면, 분기가 실제로 닿을 수 있게 되고 주석도 참이 된다.
    local -a apps nested
    apps=("$root"/*.app(N))
    # 하위에 숨은 .app 까지 본다. 진짜 산출물에는 번들 안팎을 통틀어
    # ClaudePet.app 하나뿐이다(zip·universal zip 양쪽에서 확인). py2app 이
    # Python.app 을 끌고 들어오는 식의 변화는 조용히 통과시키지 말고 여기서
    # 멈춰야 한다 — 게이트의 목적은 '우리가 무엇을 배포하는지 안다'이고,
    # 설명하지 못하는 내용물을 통과시키는 것은 게이트가 아니다.
    # (**/ 는 심볼릭 링크를 따라가지 않는다 — 순환을 만들지 않기 위해 그대로 둔다.)
    nested=("$root"/**/*.app(N))
    if [ ${#apps[@]} -ne 1 ]; then
      echo "❌ 업로드 대상 최상위에 앱(.app)이 정확히 하나가 아님 (${#apps[@]}개): $artifact"
      [ ${#apps[@]} -gt 0 ] && printf '   발견: %s\n' "${apps[@]:t}"
      rc=1
    elif [ "${apps[1]:t}" != "ClaudePet.app" ]; then
      echo "❌ 업로드 대상 최상위 앱의 이름이 ClaudePet.app 이 아님 (${apps[1]:t}): $artifact"
      rc=1
    elif [ ${#nested[@]} -ne 1 ]; then
      echo "❌ 업로드 대상 안에 설명되지 않는 .app 이 있음 (${#nested[@]}개): $artifact"
      printf '   발견: %s\n' "${nested[@]#$root/}"
      rc=1
    elif [ -L "${apps[1]}" ] || [ ! -d "${apps[1]}" ]; then
      echo "❌ 업로드 대상의 ClaudePet.app 이 실제 폴더가 아님: $artifact"; rc=1
    else
      "$PY" verify_pet_payload.py "${apps[1]}/Contents/Resources/.claude_pet" \
        || { echo "❌ 업로드 대상의 펫 자산 검사 실패: $artifact"; rc=1; }
      # 아키텍처 기준은 산출물 이름에서 온다. '이 기기'로 두면 arm64 머신에서
      # 만든 universal 산출물이 x86_64 슬라이스를 잃어도 통과한다 — Intel
      # 사용자만 겪는 사고이고, 만든 사람 기기에서는 절대 안 보인다.
      #
      # uname -m 은 '이 기기'다. 이름에서 정할 수 없는 산출물을 만나면 기준을
      # 기기에 묻는 대신 멈춘다 — 예전에는 --arches 가 비면 거절하도록 해 놓고
      # 그 자리에 uname -m 을 넣어 주고 있었다. 막으려던 값을 우리가 손에
      # 쥐여 준 셈이라, 게이트는 있었지만 아무것도 막지 못했다. Rosetta 아래서는
      # 멀쩡한 arm64 산출물을 거절하고, Intel 머신에서는 arm64 슬라이스가 없는
      # zip 을 통과시킨다 — 다운로드한 arm64 사용자 전원이 거기서 실패한다.
      local arches
      case "${artifact:t:l}" in
        *-universal.zip|*-universal.dmg) arches="arm64,x86_64" ;;
        claudepet.zip|claudepet.dmg)     arches="arm64" ;;
        *) echo "❌ 이름에서 아키텍처 기준을 정할 수 없는 산출물: $artifact"
           echo "   (기준을 '이 기기'로 대신하지 않습니다 — 그건 검사가 아닙니다)"
           arches="" ;;
      esac
      # 번들 신원·버전·아키텍처·서명·공증·티켓. 여기 다시 적지 않고 업데이터의
      # preflight 를 그대로 부른다 — 같은 검사를 두 벌 적으면 반드시 갈라지고,
      # 갈라지면 게이트가 통과시킨 것을 사용자의 업데이터가 거부한다.
      if [ -z "$arches" ]; then
        rc=1
      elif ! "$PY" verify_release_artifact.py app "${apps[1]}" \
              --expect-version "$(cur_version)" --arches "$arches"; then
        echo "❌ 업로드 대상 번들 검사 실패: $artifact"; rc=1
      fi
    fi
  fi
  # 마운트 해제 실패는 '정리 실패'가 아니라 게이트 실패다. 예전에는 || true 가
  # 삼켰고, 그 뒤의 rm -rf "$tmp" 는 아직 붙어 있는 볼륨 '안으로' 들어갔다 —
  # 정리하려던 코드가 마운트된 dmg 의 내용을 지우러 가는 모양이다. 게다가 검사
  # 결과는 rc 그대로 0 이라, 붙잡힌 볼륨을 남긴 채 gh 업로드까지 그대로 갔다.
  # 그래서 여기서는 셋 다 한다: 실패로 만들고, 마운트는 억지로 떼지 않고 남기고,
  # 어디에 남았는지 말한다. (-force 로 떼지 않는 이유: 무엇이 붙잡고 있는지
  #  모르는 채로 떼는 것은 진단을 지우는 것이지 고치는 게 아니다.)
  if [ $mounted -eq 1 ]; then
    if ! hdiutil detach "$tmp/mnt" -quiet; then
      echo "❌ dmg 마운트 해제 실패 — 볼륨이 아직 붙어 있습니다: $tmp/mnt"
      echo "   붙어 있는 동안은 임시 폴더를 지우지 않습니다(지우면 볼륨 안을 지웁니다)."
      echo "   손으로: hdiutil detach '$tmp/mnt' && rm -rf '$tmp'"
      return 1
    fi
  fi
  rm -rf "$tmp"
  return $rc
}

build() {
  rm -rf build dist
  "$PY" setup.py py2app >/tmp/py2app.log 2>&1 || { echo "❌ py2app 실패:"; tail -25 /tmp/py2app.log; exit 1; }
  verify_bundled_pet_payload "$APP" || exit 1
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
  verify_bundled_pet_payload "$UAPP" || exit 1
  echo "✅ 유니버설 빌드: $UAPP ($(du -sh "$UAPP" | cut -f1), archs: $archs)"
}

# 서명 단계의 성질: **"서명 성공"이라고 기록한 운영자가 틀릴 수 있으면 안 된다.**
# 이 함수는 [ASK-OP] 경로에 있고, 그 경로의 계약은 '단계마다 결과를 기록하고 첫
# 실패에서 멈춘다'이다. 실패할 수 없는 단계는 아무것도 기록하지 않는다 —
# 예전에는 프레임워크와 MacOS/* 서명이 `2>/dev/null … || true` 였고, 마지막
# --verify 는 AND-리스트여서 신호가 '✅ 가 안 보인다' 하나뿐이었다. 이제는
# codesign 이 한 말을 그대로(요약하지 않고) 흘려보내고 즉시 멈춘다.
sign() {
  local app="${1:-$APP}"
  # 엔타이틀먼트 없이 서명한 산출물은 서명은 성공하고 실행이 깨진다. 없으면
  # '빼고 서명'이 아니라 거절이다 — 아래 codesign 들은 전부 $ENT 를 쓴다.
  if [ ! -f "$ENT" ]; then
    echo "❌ 엔타이틀먼트 파일이 없습니다 — 서명하지 않습니다: $ENT"; return 1
  fi
  # AppleDouble(._*)/.DS_Store/xattr 청소 — framework 루트에 잡파일 있으면
  # Gatekeeper가 "unsealed contents present..."로 거부함
  find "$app" \( -name "._*" -o -name ".DS_Store" \) -delete
  dot_clean "$app" 2>/dev/null || true
  xattr -cr "$app" 2>/dev/null || true

  # 키체인/TCC 프롬프트가 'Python' 대신 앱 이름으로 뜨게 — 실제 호출 주체가
  # 번들 Python.framework라, 그 표시 이름(CFBundleName)을 ClaudePet으로 바꾼다.
  # (서명 전 unsigned 앱에서만 수정 가능 → sign()의 코드서명 직전에 실행.
  #  plist가 바뀌므로 아래에서 프레임워크를 다시 서명해야 sealed resource가 맞음)
  local ip
  while IFS= read -r ip; do
    /usr/libexec/PlistBuddy -c 'Set :CFBundleName ClaudePet' "$ip" 2>/dev/null \
      || /usr/libexec/PlistBuddy -c 'Add :CFBundleName string ClaudePet' "$ip" 2>/dev/null
  done < <(find "$app/Contents/Frameworks/Python.framework" \
             -path "*/Resources/Info.plist" -type f 2>/dev/null)

  # while 은 파이프라인의 서브셸에서 돈다 — 거기서 return 해도 이 함수는 안
  # 멈춘다. 그래서 서브셸을 exit 1 로 끝내고, 파이프라인의 상태를 여기서 본다.
  if ! find "$app/Contents" \( -name "*.so" -o -name "*.dylib" \) -type f -print0 \
       | while IFS= read -r -d '' f; do
           if ! codesign -f --options runtime --timestamp --entitlements "$ENT" -s "$ID" "$f"; then
             echo "❌ 확장모듈 서명 실패: $f"; exit 1
           fi
         done; then
    echo "❌ 내장 확장모듈(.so/.dylib) 서명 실패 — 여기서 멈춥니다: $app"; return 1
  fi
  # 내장 Python.framework 버전(3.13 등)은 빌드에 쓴 파이썬을 따라감 → 버전 무관하게 서명
  local fw
  for fw in "$app"/Contents/Frameworks/Python.framework/Versions/*(N); do
    # 링크·비디렉터리는 서명 대상이 아니다(건너뛰는 것과 실패하는 것은 다르다).
    if [ -L "$fw" ] || [ ! -d "$fw" ]; then continue; fi
    if ! codesign -f --options runtime --timestamp --entitlements "$ENT" -s "$ID" "$fw"; then
      echo "❌ 프레임워크 서명 실패 — 그 위에 번들을 서명하지 않고 멈춥니다: $fw"; return 1
    fi
  done
  local x
  for x in python ClaudePet; do
    if [ ! -f "$app/Contents/MacOS/$x" ]; then continue; fi
    if ! codesign -f --options runtime --timestamp --entitlements "$ENT" -s "$ID" "$app/Contents/MacOS/$x"; then
      echo "❌ 실행파일 서명 실패 — 여기서 멈춥니다: $app/Contents/MacOS/$x"; return 1
    fi
  done
  if ! codesign -f --options runtime --timestamp --entitlements "$ENT" \
       --identifier me.yeongyu.claudepet -s "$ID" "$app"; then
    echo "❌ 번들 서명 실패: $app"; return 1
  fi
  # AND-리스트로 적으면 안 된다: 이 줄이 함수의 마지막 명령이라 상태가 그대로
  # 함수의 상태가 되고, 실패했을 때 보이는 것은 '✅ 가 없다'뿐이다.
  if ! codesign --verify --deep --strict "$app"; then
    echo "❌ 서명 검증 실패 — 이 산출물은 공증·배포로 보내지 마세요: $app"; return 1
  fi
  echo "✅ 서명 검증 통과: $app"
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

# 실패한 dmg 를 '배포 목록에서 고를 수 없는 이름'으로 치운다.
# publish 는 파일 내용이 아니라 `[ -f "$DMG" ]` — 즉 이름만 — 으로 올릴 것을 고른다.
# 그래서 만들다 만 dmg, 공증이 안 붙은 dmg, 티켓 검증에 실패한 dmg 가 정규 이름에
# 남아 있으면 다음 publish 가 그걸 그대로 올린다. 사용자에게 닿는 쪽은 이쪽이다.
#
# 지우기보다 치우는 쪽이 낫다 — 실패한 산출물 자체가 다음 진단의 재료다. 이름은
# 여전히 *.dmg 라 .gitignore 가 그대로 덮고, publish 가 고르는 네 이름
# ($ZIP/$UZIP/$DMG/$UDMG) 중 어느 것도 아니다.
#
# 성공(치웠거나, 애초에 없거나)이면 0, 치우지도 지우지도 못했으면 1. 부르는 쪽은
# 어느 쪽이든 자기 실패를 그대로 들고 나간다 — 이 함수의 0 은 '문제 없음'이 아니라
# '정규 이름에 파일이 없음'이라는 뜻이다.
quarantine_dmg() {
  local dmg="$1" bad
  bad="${dmg:r}-failed.dmg"
  # 만들기 전에 실패했으면 치울 것이 없다. 그것도 '정규 이름에 없음'이므로 0.
  if [ ! -e "$dmg" ]; then
    return 0
  fi
  if mv -f "$dmg" "$bad"; then
    echo "   실패한 dmg 는 배포 대상에서 치웠습니다: $bad"
    return 0
  fi
  if rm -f "$dmg"; then
    echo "   치울 수 없어 지웠습니다: $dmg"
    return 0
  fi
  echo "   ⚠️  치우지도 지우지도 못했습니다 — 이대로 두면 publish 가 이 파일을 고릅니다."
  echo "      손으로 지운 뒤 다시 실행하세요: $dmg"
  return 1
}

# 앱 하나를 드래그-설치 dmg로 패키징 + 공증 + staple. $1=app 디렉터리, $2=dmg 경로.
# 내부 앱은 이미 서명+공증+staple 된 상태 → dmg 컨테이너만 추가 공증.
#
# ── 실패는 전부 같은 자리로 내려온다 ────────────────────────────────────────
# 어느 단계(hdiutil create / notary_submit / stapler staple / stapler validate)가
# 실패하든 셋을 다 한다: (1) 임시 스테이지를 남기지 않는다, (2) 정규 이름의 dmg 를
# 없애거나 치운다, (3) 0 이 아닌 값을 돌려준다.
#
# 그래서 각 단계를 `if !` 로 감싸 rc 를 손으로 들고 다닌다. 실패한 명령을 그냥
# 늘어놓으면 zsh 의 ERR_EXIT 가 함수 '중간에서' 프로세스를 끝내 버려서, 그 아래
# 적어 둔 정리 코드는 한 줄도 실행되지 않는다 — 정리를 '나중에 적는 것'만으로는
# 정리가 되지 않는다. (trap 도 답이 아니다: zsh 의 trap 은 사람들이 기대하는 것과
# 달리 함수 스코프가 아니고 함수 return 이 아니라 프로세스 종료에서 돈다.)
# AND-리스트(`a && b`)로 적는 것도 안 된다 — ERR_EXIT 는 AND-OR 리스트에서 아예
# 돌지 않고, 마지막 줄이면 그 상태가 조용히 함수의 상태가 된다.
one_dmg() {
  local app="$1" dmg="$2"
  # 없는 앱은 '건너뜀'이 아니라 실패다. 무엇을 만들지 말지는 부르는 쪽이 이미
  # 정하고 있다 — make_dmg 는 arm64 를 '항상', 유니버설을 `[ -d "$UAPP" ]` 일
  # 때만 부른다. 여기서 또 조용히 건너뛰면 그 구분이 지워져서 둘 다 선택사항이
  # 되고, `./release.sh dmg` 는 아무것도 만들지 않은 채 0 으로 끝난다 —
  # '검사하지 못한 것'과 '통과한 것'이 같아 보이는, 게이트가 가져서는 안 되는
  # 모양이다(verify_upload_artifact 의 '없는 파일은 통과가 아니라 실패다'와 같은 이유).
  if [ ! -d "$app" ]; then
    echo "❌ dmg 로 만들 앱이 없습니다 — $dmg 를 만들지 않습니다: $app"
    echo "   (앱을 먼저 빌드·서명·공증하세요. 여기서 조용히 건너뛰면 배포 목록에서만 티가 납니다.)"
    return 1
  fi
  local stage rc=0
  if ! stage=$(mktemp -d); then
    echo "❌ dmg 스테이지용 임시 폴더를 만들지 못했습니다 — $dmg 를 만들지 않습니다"
    return 1
  fi
  # 스테이지를 만드는 세 단계. 어디서 실패하든 아래 '스테이지 정리'로 내려간다.
  if [ $rc -eq 0 ]; then
    if ! /usr/bin/ditto "$app" "$stage/ClaudePet.app"; then
      echo "❌ dmg 스테이지로 앱을 복사하지 못했습니다: $app"; rc=1
    fi
  fi
  if [ $rc -eq 0 ]; then
    if ! ln -s /Applications "$stage/Applications"; then   # 드래그 설치용 심볼릭
      echo "❌ dmg 스테이지에 /Applications 심볼릭을 만들지 못했습니다: $stage"; rc=1
    fi
  fi
  # mkdir/rm 도 벗겨 두면 안 된다 — 여기서 죽으면 ERR_EXIT 가 스테이지 정리를
  # 건너뛴다. 실패해도 rc 로 바꿔서 반드시 아래로 내려가게 한다.
  if [ $rc -eq 0 ]; then
    if ! mkdir -p release; then
      echo "❌ release/ 폴더를 만들지 못했습니다 — $dmg 를 만들지 않습니다"; rc=1
    fi
  fi
  if [ $rc -eq 0 ]; then
    if ! rm -f "$dmg"; then
      echo "❌ 이전 dmg 를 치우지 못해 새로 만들지 않습니다: $dmg"; rc=1
    fi
  fi
  if [ $rc -eq 0 ]; then
    if ! hdiutil create -volname "ClaudePet" -srcfolder "$stage" -ov -format UDZO "$dmg" >/dev/null; then
      echo "❌ dmg 생성 실패 (hdiutil create) → $dmg"; rc=1
    fi
  fi
  # 스테이지는 성공·실패와 무관하게 '항상' 여기서 사라진다. 못 지웠으면 그것도
  # 실패다 — 남은 자리를 경로로 말한다(마운트 해제 실패를 다루는 방식과 같다).
  if ! rm -rf "$stage"; then
    echo "❌ dmg 임시 스테이지를 지우지 못했습니다 — 손으로 지우세요: $stage"
    rc=1
  fi
  if [ $rc -ne 0 ]; then
    # hdiutil 이 -ov 로 덮어쓰다 중간에 죽으면 반쯤 쓴 파일이 정규 이름에 남는다.
    # 그것도 publish 가 고르는 이름이므로 여기서 치운다.
    if ! quarantine_dmg "$dmg"; then
      echo "   (치우기까지 실패했습니다 — 이 단계는 어차피 실패로 끝납니다.)"
    fi
    return 1
  fi
  echo "→ dmg 공증 제출: $dmg (Apple 서버, 보통 1~5분)…"
  if ! notary_submit "$dmg"; then
    echo "❌ dmg 공증 실패 → $dmg"
    if ! quarantine_dmg "$dmg"; then
      echo "   (치우기까지 실패했습니다 — 이 단계는 어차피 실패로 끝납니다.)"
    fi
    return 1
  fi
  if ! xcrun stapler staple "$dmg"; then
    echo "❌ dmg staple 실패 (티켓이 붙지 않았습니다) → $dmg"
    if ! quarantine_dmg "$dmg"; then
      echo "   (치우기까지 실패했습니다 — 이 단계는 어차피 실패로 끝납니다.)"
    fi
    return 1
  fi
  # ── 검증 실패는 '말하고', 남기지 않는다 ────────────────────────────────
  # 예전에는 이 줄이 `xcrun stapler validate "$dmg" >/dev/null 2>&1 && echo ✅`
  # 하나였다. 두 가지가 동시에 잘못돼 있었다:
  #
  #  1. **아무 말도 하지 않는다.** 이 AND-리스트가 함수의 마지막 명령이라 그
  #     상태가 곧 함수의 상태가 되고, zsh 의 ERR_EXIT 는 '부른 자리'에서 터진다.
  #     사용자가 보는 것은 ✅ 가 없다는 것뿐 — 무엇이 왜 실패했는지 어디에도
  #     찍히지 않는다. 게다가 출력을 >/dev/null 2>&1 로 버렸으니 진단할 재료도
  #     함께 사라진다.
  #  2. **실패한 dmg 가 디스크에 그대로 남는다.** publish 는 release/ClaudePet.dmg
  #     를 '이름으로' 고른다. 그래서 티켓이 붙지 않은 dmg 가 다음 publish 의
  #     업로드 대상이 된다 — 사용자에게 닿는 쪽은 이쪽이다.
  #
  # rc 만 봐서도 안 된다: stapler validate 는 "The validate action failed!" 를
  # 찍으면서 0 을 돌려주는 경우가 있다. 그래서 출력과 rc 를 둘 다 본다.
  local vout vrc=0
  vout=$(xcrun stapler validate "$dmg" 2>&1) || vrc=$?
  # (실제로 찍히는 문장은 "The validate action failed!" 이다. 앞부분만 보면
  #  느낌표·마침표 유무나 접두어가 달라져도 계속 잡힌다.)
  case "$vout" in
    *"validate action failed"*) vrc=1 ;;
  esac
  if [ $vrc -ne 0 ]; then
    echo "❌ dmg 공증 티켓 검증 실패 (rc=$vrc) → $dmg"
    if [ -n "$vout" ]; then
      echo "   stapler validate 가 말한 것:"
      # (@f): 줄 단위로 쪼갠 것을 따옴표 안에서도 '여러 낱말'로 유지한다.
      # "${(f)…}" 로 적으면 zsh 가 다시 한 낱말로 합쳐서, 여러 줄짜리 진단이
      # 공백으로 이어 붙은 한 줄이 된다 — 진단을 찍으려고 넣은 줄이 진단을 뭉갠다.
      printf '     %s\n' "${(@f)vout}"
    else
      echo "   stapler validate 는 아무 말도 하지 않았습니다(출력 없음, rc 만 실패)."
    fi
    # 티켓이 붙지 않은 dmg 는 배포 목록에서 고를 수 없는 이름으로 치운다.
    # (다른 실패 경로와 같은 자리 — quarantine_dmg 참조.)
    if ! quarantine_dmg "$dmg"; then
      echo "   (치우기까지 실패했습니다 — 이 단계는 어차피 실패로 끝납니다.)"
    fi
    return 1
  fi
  echo "✅ dmg 완료 → $dmg ($(du -sh "$dmg" | cut -f1))"
}

# 수동 다운로드용 DMG (드래그 → Applications). 자동업데이트는 zip이 담당.
# zip과 동일하게 arm64용 + 유니버설(Intel)용 둘 다 만든다.
make_dmg() {
  one_dmg "$APP" "$DMG"                        # arm64 (Apple Silicon) — 항상
  # 유니버설(Intel+ARM)은 universal 빌드가 있을 때만 — 그 '선택'은 여기 있는 게
  # 맞다. 다만 AND-리스트로 적으면 안 됐다: 이 줄이 함수의 마지막 명령이라,
  # universal 빌드가 없을 때 `[ -d ]` 의 1 이 그대로 make_dmg 의 상태가 되고
  # zsh 의 ERR_EXIT 가 '부른 자리'에서 터진다. arm64 dmg 를 멀쩡히 만들어 놓고
  # 아무 말 없이 1 로 끝나는 것이다 — one_dmg 의 validate 와 완전히 같은 모양의
  # 조용한 중단이, 바로 그 아래 줄에 하나 더 있었다.
  if [ -d "$UAPP" ]; then
    one_dmg "$UAPP" "$UDMG"
  else
    echo "⚠️  유니버설 앱이 없어 유니버설 dmg 는 만들지 않습니다 — arm64 dmg 만: $UAPP"
  fi
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

# APP_VERSION 갱신 + 커밋 + 태그 + 푸시.
#
# [NEVER] 이 함수를 부르는 유일한 경로는 `ship` 이고, `ship` 은 금지된 legacy
# 통합 명령이다 — 실행하지 말 것. 예전에는 여기에 `./release.sh ship 0.2` 라는
# 사용 예가 적혀 있었는데, 금지된 명령을 권장처럼 보이게 했다.
#
# 금지 이유는 이 함수가 하는 일 자체가 아니라 순서다. 아래는 `git push &&
# git push --tags` 로 끝나고 그것이 `ship` 사슬의 '첫' 단계라, 한 줄도 빌드되기
# 전에 커밋과 태그가 GitHub 에 올라간다. 빌드가 그다음 실패하면 태그는 이미
# 공개돼 있고 업데이터는 존재하지 않는 버전을 권하고 있다.
#
# 또 `git add claude_pet.py` 만 하므로 릴리즈 노트·문서·테스트는 커밋에서
# 조용히 빠진다. 버전 범프와 릴리즈 커밋은 손으로, 경로를 하나씩 적어서 한다.
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

# 릴리즈 본문 생성: 설치 안내(전체) + "변경 내역"은 현재 버전 항목만.
# (누적 changelog 전체 대신 해당 버전만 노출) → $1에 기록.
gen_release_notes() {
  local ver="**v$(cur_version)**"
  awk -v ver="$ver" '
    function trim(s){ sub(/[ \t\r]+$/,"",s); return s }
    !inlog && /^###/ && /변경 내역/ { print; inlog=1; keep=0; next }
    !inlog { print; next }
    { if (trim($0) ~ /^\*\*v[0-9]/) keep=(trim($0)==ver)?1:0; if (keep) print }
  ' "$NOTES" > "$1"
}

publish() {
  command -v gh >/dev/null 2>&1 || {
    echo "❌ gh CLI 필요: brew install gh && gh auth login (개인 계정으로)"; exit 1; }
  local TAG="v$(cur_version)"
  # 넷은 '있으면 올린다'가 아니라 '없으면 안 올린다'다. 예전에는 universal zip 이
  # 없으면 조용히 빠졌는데, 그건 Intel 사용자에게 받을 것이 없는 릴리즈를 —
  # 아무 경고도 없이 — 내보내는 것이다. 공개된 v0.19 도 넷을 다 갖고 있다.
  local -a files=("$ZIP" "$UZIP" "$DMG" "$UDMG")
  # 이름이 업데이터의 표(UPDATE_ASSET_NAMES)와 맞는지 먼저 본다. 두 곳이 각자
  # 이름을 들고 있었고 둘을 맞춰 보는 곳이 없었다 — 한쪽만 바꾸면
  # check_github_update 가 'failed' 를 돌려주고, 그 값은 쿨다운을 태우지 않아
  # 설치된 모든 사본이 조용히 영원히 재시도한다. 아무에게도 신호가 가지 않는다.
  "$PY" verify_release_artifact.py assets "${files[@]}" \
    || { echo "❌ 업로드 목록이 업데이터의 자산 표와 맞지 않습니다 — 올리지 않습니다"; exit 1; }
  # 올라갈 파일 하나하나를 열어서 확인한다(디렉터리가 아니라).
  local f
  for f in "${files[@]}"; do
    verify_upload_artifact "$f" || { echo "❌ 업로드 중단: $f"; exit 1; }
  done
  local NOTES_TMP; NOTES_TMP=$(mktemp)
  gen_release_notes "$NOTES_TMP"
  if gh release view "$TAG" >/dev/null 2>&1; then
    gh release upload "$TAG" "${files[@]}" --clobber
    gh release edit "$TAG" --notes-file "$NOTES_TMP"   # 노트도 고정본으로 갱신(현재 버전만)
    echo "🚀 기존 릴리즈에 업로드: $TAG ← ${files[*]}"
  else
    gh release create "$TAG" "${files[@]}" --title "ClaudePet $TAG" --notes-file "$NOTES_TMP"
    echo "🚀 새 릴리즈 생성: $TAG ← ${files[*]}"
  fi
  rm -f "$NOTES_TMP"
}

# ─── source 방지 가드 ───────────────────────────────────────────────
# 이 파일을 함수만 쓰려고 source 하면 아래 dispatch 가 돌아 버린다. 예전에는
# 인자가 없으면 case "${1:-all}" 이 all 로 떨어져 build → sign → notarize 까지
# 실행됐고, 실제로 그렇게 서명·공증이 나갔다. 지금은 기본값이 사용법이지만,
# 그건 두 번째 문이었을 뿐이다 — source 로 들어오는 문은 이 가드가 닫는다.
# 실행됐을 때만 dispatch 한다.
# (zsh 스크립트다. bash 의 `(return 0 2>/dev/null)` 관용구는 zsh 에서 실행
#  중에도 참이 되어 정반대로 동작한다 — 실제 zsh 로 확인하고 이 형태를 썼다.)
case "${ZSH_EVAL_CONTEXT}" in *:file*) return 0 ;; esac

# 인자가 없으면 사용법을 찍고 끝낸다 — 예전 기본값이던 all 로 떨어지지 않는다.
# `./release.sh` 한 줄이 build → sign → notarize → universal → dmg 를 다 돌려
# 서명·공증이 의도 없이 나간 적이 있다. bare 실행은 어차피 CLAUDE.md 에서
# [NEVER] 라 정상 경로가 이 기본값에 기대는 곳이 없고, 틀려도 안전한 쪽으로
# 틀린다(사용법을 보고 원하던 걸 다시 친다). 다시 all 로 되돌리지 말 것.
case "${1:-}" in
  build)     build ;;
  sign)      sign ;;
  notarize)  notarize ;;
  universal) universal ;;                   # 유니버설(arm64+x86_64) 빌드+서명+공증
  dmg)       make_dmg ;;                    # 설명은 맨 위 사용법 한 곳에만 둔다
  publish)   publish ;;                     # zip/dmg를 GitHub Release에 업로드만
  all)       build; sign; notarize; maybe_universal; make_dmg ;;
  ship)      bump_version "$2"; build; sign; notarize; maybe_universal; make_dmg; publish ;;
  # 인자 없음("")과 모르는 인자를 같은 곳으로 보낸다.
  ""|*) echo "사용법: ./release.sh [build|sign|notarize|universal|dmg|publish|all|ship [새버전]]"
     # 예시로 ship 을 권하지 않는다. 오타를 친 사람에게 가장 먼저 보이는 줄이
     # 하필 이 저장소에서 가장 위험한 명령이었다(커밋·태그·푸시를 빌드보다
     # 먼저 하고, 서명·공증까지 한 번에 간다). all·ship 은 CLAUDE.md 에서
     # [NEVER] 이고, 단계는 하나씩 따로 실행한다.
     echo "  all·ship 은 이 저장소 규칙상 금지입니다(CLAUDE.md). 단계별로 실행하세요."
     echo "  예: ./release.sh build"
     exit 1 ;;
esac
