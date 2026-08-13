#!/bin/zsh
# Claude Pet 빌드/설치 스크립트
#
#   ./build_app.sh build      # 레포 안에 ClaudePet.app 빌드만
#   ./build_app.sh install    # 빌드 → /Applications 설치 → 재시작 (추천)
#   ./build_app.sh update     # 설치본의 코드·펫자산·버전·서명 갱신 후 재시작 (가장 빠름)
#                             #   갱신하는 넷은 claude_pet.py, .claude_pet, Info.plist,
#                             #   서명뿐이다. frames/ 는 건드리지 않는다 — 스프라이트를
#                             #   바꿨다면 update 가 아니라 install 이다. ('자산'을 넓게
#                             #   읽으면 frames 도 갱신된다고 오해하게 되어 이름을 좁힌다.
#                             #   v0.20 에서 update 의 범위를 넓히지는 않는다.)
#   (인자 없이 실행하면 사용법만 찍는다 — 예전에는 빌드+서명이 돌았다)
#
set -e
# CDPATH 가 켜져 있으면 아래 cd 가 조용히 엉뚱한 폴더로 간다 — 그 뒤의 모든
# 상대경로(claude_pet.py, .claude_pet, verify_pet_payload.py)가 남의 파일이 된다.
CDPATH=""
cd "$(dirname "$0")"
APP=ClaudePet.app
DEST="/Applications/$APP"
# 이 스크립트 자신의 절대경로. 아래 잠금 래퍼가 자기 자신을 자식으로 다시 부르는데,
# $0 이 상대경로면 위의 cd 뒤에는 다른 곳(또는 아무 곳도)을 가리킨다.
SELF="$PWD/${0:t}"

# 번들 버전은 claude_pet.py 의 APP_VERSION 하나에서만 나온다. 여기에 1.0 을
# 박아 두면 인앱 업데이터가 설치본을 1.0 으로 보고 매번 업데이트를 권한다.
APP_VERSION=$(sed -n 's/^APP_VERSION = "\([^"]*\)".*/\1/p' claude_pet.py | head -1)
[ -n "$APP_VERSION" ] || { echo "❌ claude_pet.py 에서 APP_VERSION 을 못 읽었습니다"; exit 1; }

# Info.plist 를 APP_VERSION 으로 생성 (빌드/갱신 양쪽에서 같은 걸 쓴다)
write_plist() {
  cat > "$1/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key><string>ClaudePet</string>
    <key>CFBundleDisplayName</key><string>Claude Pet</string>
    <key>CFBundleIdentifier</key><string>me.yeongyu.claudepet</string>
    <key>CFBundleVersion</key><string>${APP_VERSION}</string>
    <key>CFBundleShortVersionString</key><string>${APP_VERSION}</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>CFBundleExecutable</key><string>ClaudePet</string>
    <key>LSUIElement</key><true/>
    <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
PLIST
}

# 동봉 펫 자산(.claude_pet)을 번들 안에 통째로 새로 넣는다. 앱은 시작할 때
# 여기서 ~/.claude_pet 로 '없는 것만' 채우므로, 번들 것이 낡으면 새 펫이
# 영영 안 깔린다. 코드만 바꾸는 update 에서도 반드시 같이 갱신해야 한다.
copy_pet_assets() {
  # 옆에 완성본을 먼저 만들고, 검사까지 통과한 뒤에야 제자리로 바꾼다.
  # 예전에는 rm -rf 로 먼저 지우고 cp -R 했는데, 복사가 중간에 실패하면 번들에
  # 자산이 아예 없거나 반쯤 든 채로 남았다 — 목적지를 '내용이 완성되기 전에'
  # 부수는 것으로, 시더에서 계속 거절해 온 mkdir-후-채우기와 같은 모양이다.
  local res="$1/Contents/Resources"
  local final="$res/.claude_pet"
  local stage="$res/.claude_pet.new.$$"
  # 고정 이름: 크래시로 남더라도 어디 있는지 알 수 있어야 한다($$ 를 붙이면
  # 매번 이름이 달라져 '남은 것'을 찾을 수 없다). 동시 빌드는 상정하지 않는다.
  local backup="$res/.claude_pet.previous"
  local final_id backup_id stage_id
  mkdir -p "$res"

  # ── 0. 잎이 링크면 아무것도 하지 않는다 ───────────────────────────────
  # update_installed 가 stage·backup 에 하는 것과 같은 검사다. 두 자리 모두
  # rename 의 대상이고, 링크면 mv 는 링크 '너머'에 쓴다 — 백업은 분명히
  # 만들어졌는데 되돌릴 때 우리가 보는 자리에는 없다. 파괴하기 전에 거절한다.
  # (이 검사가 여기 없고 update_installed 에만 있던 것이 문제였다: 같은 계약을
  #  두 곳에서 지키는데 한쪽만 검사하면, 검사 없는 쪽이 계약의 실제 강도다.)
  local p
  for p in "$stage" "$backup" "$final"; do
    if [ -L "$p" ]; then
      echo "❌ 자산 작업 경로가 심볼릭 링크입니다 — 갱신하지 않습니다: $p"; return 1
    fi
  done
  if [ -e "$backup" ] && [ ! -d "$backup" ]; then
    echo "❌ 자산 백업 자리에 우리가 만들지 않은 것이 있습니다 — 지우지도 옮기지도 않습니다: $backup"
    return 1
  fi
  # ── 1. 복구를 '어떤 파괴적 정리보다도' 먼저 한다 ──────────────────────
  # 교체 계약: 백업은 $$ 없는 고정 이름 .claude_pet.previous 하나뿐이라, 두
  # rename 사이에서 죽어도 예전 자산이 그 이름으로 남는다. 그런데 정리를 먼저
  # 하면 바로 그 유일한 사본을 지운다 — 계약이 지키려던 것을 정리 코드가
  # 없애는 것이다. 그래서 복구가 맨 앞이다. (순서 실수는 이 저장소에서만
  # 네 번째다: 스테이지 생성 뒤 쓸기, 변환 뒤 검사, 스테이징 뒤 검증, 그리고 이것.)
  if [ -d "$backup" ] && [ ! -e "$final" ]; then
    # 되돌리기의 '결과'를 본다 — 요청한 경로가 아니라 실제로 열리는 것을.
    # (update_installed 의 복구와 같은 강도로 맞춘다. 이름만 보고 "되돌렸습니다"
    #  라고 찍으면, 그 사이에 그 이름으로 생긴 남의 것을 되돌렸다고 말하게 된다.)
    backup_id=$(path_ident "$backup" || true)
    if [ -z "$backup_id" ]; then
      echo "❌ 이전 실행이 남긴 자산의 신원을 읽지 못했습니다 — 손대지 않습니다: $backup"; return 1
    fi
    if ! mv "$backup" "$final"; then
      echo "❌ 이전 실행이 남긴 자산을 되돌리지 못했습니다: $backup"; return 1
    fi
    if [ "$(path_ident "$final" || true)" != "$backup_id" ]; then
      echo "❌ 되돌린 자산이 요청한 자리에 있지 않습니다: $final"; return 1
    fi
    echo "↩️  이전 실행이 중단된 흔적을 발견해 예전 자산을 되돌렸습니다"
  fi

  # ── 2. 복구가 끝난 뒤에야 정리한다 ────────────────────────────────────
  # 중단된 이전 실행이 남긴 스테이징 폴더를 '이번 스테이지를 만들기 전에' 쓸어낸다.
  # 이름에 $$ 가 붙어 매번 달라지므로 그냥 두면 번들 Resources 안에 쌓이고,
  # 서명 때 "unsealed contents" 로 거부되거나 잡동사니가 그대로 배포된다.
  # (이번 스테이지를 만든 뒤에 쓸면 방금 만든 것까지 지운다 — 실제로 그랬다.)
  # 폴더가 아닌 것은 우리가 만든 스테이지가 아니다 — 지우지 않고 둔다.
  # (update_installed 의 .new.* 쓸기는 이미 이렇게 하고 있었고 여기만 무조건
  #  rm -rf 였다. 같은 결정을 두 곳에서 다르게 내리면, 느슨한 쪽이 실제 강도다.)
  local -a stale
  stale=("$res"/.claude_pet.new.*(N))       # (N) = 없으면 빈 목록
  # 빈 목록을 rm -rf 에 그대로 넘기면 인자 없는 rm 이 되어 실패하고, set -e 가
  # 함수를 통째로 중단시킨다 — 자산이 아예 안 깔린다. 하나씩 돈다.
  local s
  for s in "${stale[@]}"; do
    if [ -L "$s" ] || [ ! -d "$s" ]; then
      echo "⚠️  폴더가 아니라 치우지 않고 둡니다: $s"; continue
    fi
    rm -rf "$s"
  done
  # 우리 스테이지 자리가 그래도 비지 않았으면 — 위에서 '남의 것'이라 두고 온
  # 무언가가 하필 그 이름이라는 뜻이다 — 덮지 않고 멈춘다.
  if [ -e "$stage" ] || [ -L "$stage" ]; then
    echo "❌ 자산 작업 경로를 비우지 못했습니다 — 갱신하지 않습니다: $stage"; return 1
  fi
  # backup 은 final 이 제자리에 있을 때만 버린다. final 이 없는데 backup 을
  # 지우면 그게 유일한 사본이다. (여기서 지우는 것은 '지난 실행'이 남긴 것이라
  #  이번 실행이 붙잡아 둔 신원이 없다. 위의 -d/-L 검사가 우리가 가진 전부다.)
  if [ -e "$final" ]; then rm -rf "$backup"; fi
  if ! cp -R .claude_pet "$stage"; then
    rm -rf "$stage"; echo "❌ 펫 자산 복사 실패 — 기존 자산은 그대로 둡니다"; return 1
  fi
  find "$stage" -name ".DS_Store" -delete 2>/dev/null || true
  if ! "${PYCHECK:-python3}" verify_pet_payload.py "$stage" --quiet; then
    rm -rf "$stage"; echo "❌ 복사본 검사 실패 — 기존 자산은 그대로 둡니다"; return 1
  fi
  # ── 3. 교체 ───────────────────────────────────────────────────────────
  # 신원을 '손대기 전에' 붙잡는다. 이름만 들고 옮기면 옮긴 결과가 우리가 옮긴
  # 그것인지 확인할 방법이 없다 — rename 은 그 자리에 폴더가 생겨 있으면 덮지
  # 않고 그 '안으로' 들어간다. update_installed 가 번들 단위로 하는 검사와 같은
  # 것을, 그 검사가 본떠 온 이 함수도 이제 한다.
  stage_id=$(path_ident "$stage" || true)
  if [ -z "$stage_id" ]; then
    echo "❌ 새 자산의 신원을 읽지 못해 교체를 멈춥니다 — 기존 자산은 그대로 둡니다: $stage"
    return 1
  fi
  final_id=""
  if [ -e "$final" ]; then
    final_id=$(path_ident "$final" || true)
    if [ -z "$final_id" ]; then
      echo "❌ 기존 자산의 신원을 읽지 못해 교체를 멈춥니다 — 그대로 둡니다: $final"; return 1
    fi
    if ! mv "$final" "$backup"; then
      echo "❌ 기존 자산을 옮기지 못했습니다 — 그대로 둡니다"; return 1
    fi
    if [ "$(path_ident "$backup" || true)" != "$final_id" ]; then
      if [ "$(path_ident "$backup/.claude_pet" || true)" = "$final_id" ] \
         && mv "$backup/.claude_pet" "$final"; then
        echo "↩️  백업 자리에 다른 것이 있어 기존 자산이 그 안으로 들어갔습니다 — 도로 꺼냈습니다"
      fi
      echo "❌ 자산 백업이 요청한 자리에 생기지 않았습니다: $backup"
      echo "   예전 자산을 잃지 않기 위해 여기서 멈춥니다 — 손으로 확인하세요."
      return 1
    fi
  fi
  if ! mv "$stage" "$final"; then
    if [ -n "$final_id" ]; then
      # 되돌리기의 '결과'를 반드시 본다. 예전에는 결과를 안 보고 무조건
      # "되돌렸습니다"라고 찍어, 실패했는데 성공했다고 말할 수 있었다.
      if [ ! -e "$final" ] && mv "$backup" "$final" \
         && [ "$(path_ident "$final" || true)" = "$final_id" ]; then
        echo "❌ 자산 교체 실패 — 기존 자산을 되돌렸습니다"
        echo "   새로 만들던 자산은 지우지 않았습니다 — 여기 있습니다: $stage"
        return 1
      fi
      echo "❌ 자산 교체 실패, 되돌리기도 실패했습니다."
      echo "   예전 자산은 지우지 않았습니다 — 여기 있습니다: $backup"
      echo "   새로 만들던 자산도 지우지 않았습니다 — 여기 있습니다: $stage"
      return 1
    fi
    # 되돌릴 것이 애초에 없었던 갈래. 예전에는 여기서도 "기존 자산을
    # 되돌렸습니다"라고 찍었다 — 백업이 만들어진 적조차 없는데. 게다가 이 갈래는
    # 예외가 아니라 '모든 build()' 가 지나가는 길이다: build() 는 rm -rf "$APP"
    # 로 시작하므로 $final 은 늘 없고, 그래서 백업도 늘 만들어지지 않는다.
    # (예전에는 이 문장을 찍기 '전에' rm -rf "$stage" 로 방금 만든 것까지
    #  지워서, 거짓말과 함께 볼 것도 남기지 않았다.)
    echo "❌ 자산 교체 실패 — 되돌릴 예전 자산이 없었습니다(번들에 자산이 없습니다): $final"
    echo "   새로 만들던 자산은 지우지 않았습니다 — 여기 있습니다: $stage"
    return 1
  fi
  if [ "$(path_ident "$final" || true)" != "$stage_id" ]; then
    echo "❌ 새 자산이 요청한 자리에 들어가지 않았습니다: $final"
    if [ -n "$final_id" ]; then
      echo "   예전 자산은 지우지 않았습니다 — 여기 있습니다: $backup"
    fi
    return 1
  fi
  # 마지막 정리도 신원에 묶는다. 지우려는 것이 '우리가 방금 옮겨 둔 그것'이
  # 아니면 지우지 않는다 — 이름만 보고 지우면 그 사이에 그 이름으로 생긴 남의
  # 것을 지우게 된다.
  if [ -n "$final_id" ]; then
    if [ "$(path_ident "$backup" || true)" = "$final_id" ]; then
      rm -rf "$backup"
    else
      echo "⚠️  자산 백업 자리의 것이 우리가 옮겨 둔 그것이 아닙니다 — 지우지 않고 둡니다: $backup"
    fi
  fi
}

# ─── 레포 빌드 잠금 (설치 트랜잭션 잠금과 '다른' 잠금) ────────────────────
# build() 는 레포의 ClaudePet.app 을 rm -rf 하고 다시 세운다. 그 트리는 이
# 체크아웃에서 도는 모든 build/install 이 공유하는 하나다 — 잠그지 않으면 두
# 번째 실행의 rm -rf 가 첫 번째가 서명하려던 번들을 발밑에서 걷어낸다.
# install 은 목적지 잠금(txn)을 쥐고 들어오지만 맨 `./build_app.sh build` 는
# 아무것도 쥐지 않아서, build/build 와 build/install 이 그대로 레이스였다.
#
# **잠금 순서는 하나뿐이다: txn → build.** install 이 txn 을 쥔 채 build 를
# 부르므로 이 방향만 존재하고, 그래서 사이클이 없다. **빌드 잠금을 쥔 채 txn
# 잠금을 잡는 코드는 절대 쓰지 말 것** — 그 줄이 생기는 순간 교착이 가능해진다.
# 이름도 일부러 다르게 둔다: txn 잠금은 '설치 목적지'의 이름을 따고, 이 잠금은
# '레포 트리'의 이름을 딴다. 같은 이름을 쓰면 서로 다른 두 자원을 하나로 착각한다.
#
# 잠금 자리는 레포 '밖'이다. 레포 안에 만들면 크래시로 남은 폴더가 추적되지 않는
# 채 루트에 남고, 릴리즈 게이트는 그것을 더러운 트리로 읽는다(.gitignore 는 이
# 변경의 소유가 아니다). 키는 체크아웃 경로라, 다른 체크아웃끼리는 막지 않는다.
build_lock_path() {
  local key
  key=$(printf '%s' "$PWD" | shasum -a 256 | cut -c1-16)
  echo "${TMPDIR:-/tmp}/claudepet-build-$key.lock"
}

acquire_build_lock() {
  # 재진입은 막지 않는다 — 막으면 자기 자신과 교착한다. 지금 그런 경로는 없지만
  # (install 은 txn 만 쥐고 들어온다), 생기더라도 죽지 않도록 깊이를 센다.
  if [ -n "$CLAUDEPET_BUILD_LOCK" ]; then
    CLAUDEPET_BUILD_REENTRY=$((${CLAUDEPET_BUILD_REENTRY:-0} + 1)); return 0
  fi
  local lock holder waited=0
  lock=$(build_lock_path)
  while ! mkdir "$lock" 2>/dev/null; do
    holder=""
    if [ -f "$lock/pid" ]; then holder=$(cat "$lock/pid" 2>/dev/null || true); fi
    if [ -n "$holder" ] && ! kill -0 "$holder" 2>/dev/null; then
      echo "· 죽은 프로세스($holder)가 남긴 빌드 잠금을 회수합니다: $lock"
      rm -rf "$lock"; continue
    fi
    if [ $waited -ge 600 ]; then
      echo "❌ 다른 빌드가 같은 레포 트리를 쓰고 있습니다 — 기다리다 멈춥니다: $lock"
      return 1
    fi
    sleep 0.2; waited=$((waited + 1))
  done
  CLAUDEPET_BUILD_LOCK="$lock"
  echo $$ > "$lock/pid"
}

release_build_lock() {
  if [ ${CLAUDEPET_BUILD_REENTRY:-0} -gt 0 ]; then
    CLAUDEPET_BUILD_REENTRY=$((CLAUDEPET_BUILD_REENTRY - 1)); return 0
  fi
  if [ -n "$CLAUDEPET_BUILD_LOCK" ]; then
    rm -rf "$CLAUDEPET_BUILD_LOCK"; CLAUDEPET_BUILD_LOCK=""
  fi
}

# 잠금은 build() 가 잡고, 실제 작업은 build_body() 가 한다. 나누는 이유는 하나다:
# **EXIT 트랩으로 잠금을 놓지 않기 위해서다.** zsh 에서 함수 안에 건 EXIT 트랩은
# 사람들이 믿는 것처럼 '함수가 끝날 때'가 아니라 프로세스가 끝날 때 돈다. 그래서
# 예전 모양(build() 안의 `trap 'release_build_lock' EXIT`)은 install arm 이 아직
# 레포 번들을 읽고·해시하고·복사하고·서명하는 동안 잠금을 이미 놓았거나, 반대로
# 트랩보다 먼저 죽어 영영 놓지 않았다. 지금은 명시적으로 잡고 명시적으로 놓는다.
#
# 그리고 build_body() 의 모든 단계는 온전한 `if` 로 감싼다. 여기서 `a && b` 를
# 쓰면 안 된다 — zsh 의 ERR_EXIT 는 AND-OR 리스트에서 아예 발동하지 않아,
# 실패가 중단도 안 되고 잡히지도 않는다.
build() {
  # 공유 트리(레포의 ClaudePet.app)를 만지기 전에 잠근다.
  if ! acquire_build_lock; then
    echo "❌ 레포 빌드 잠금을 잡지 못했습니다 — 빌드하지 않습니다"
    return 1
  fi
  # 조건 자리에서 부르므로 build_body 안에서는 ERR_EXIT 가 돌지 않는다. 그래서
  # 그 안의 단계는 전부 스스로 상태를 본다(아래).
  if build_body; then
    release_build_lock
    return 0
  fi
  # 실패 정리 경로. 성공 경로와 같은 해제를 '명시적으로' 한 번 더 적는다 —
  # 두 출구가 하나의 트랩을 공유하는 모양이 바로 앞의 버그였다.
  release_build_lock
  return 1
}

build_body() {
  if ! rm -rf "$APP"; then
    echo "❌ 예전 빌드본을 치우지 못했습니다: $APP"; return 1
  fi
  if ! mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"; then
    echo "❌ 번들 뼈대를 만들지 못했습니다: $APP"; return 1
  fi
  if ! cp claude_pet.py "$APP/Contents/Resources/"; then
    echo "❌ 코드를 번들에 넣지 못했습니다"; return 1
  fi
  if ! cp -R frames "$APP/Contents/Resources/frames"; then
    echo "❌ frames 를 번들에 넣지 못했습니다"; return 1
  fi
  # 동봉 펫 자산(.claude_pet: README 4개 + pets/<4종>) — 앱이 시작할 때
  # ~/.claude_pet 에 없는 것만 채워 넣는다. 빠지면 새 사용자에게 펫이 안 생긴다.
  if ! copy_pet_assets "$APP"; then
    echo "❌ 펫 자산을 번들에 넣지 못했습니다"; return 1
  fi
  find "$APP" -name ".DS_Store" -delete 2>/dev/null || true

  if ! write_plist "$APP"; then
    echo "❌ Info.plist 를 쓰지 못했습니다"; return 1
  fi

  # 런처는 컴파일된 Mach-O (코드서명하려면 실행파일이 Mach-O여야 함)
  if ! clang -O2 -arch arm64 -arch x86_64 -o "$APP/Contents/MacOS/ClaudePet" launcher.c 2>/dev/null; then
    if ! clang -O2 -o "$APP/Contents/MacOS/ClaudePet" launcher.c; then
      echo "❌ 런처를 컴파일하지 못했습니다: launcher.c"; return 1
    fi
  fi
  if ! chmod +x "$APP/Contents/MacOS/ClaudePet"; then
    echo "❌ 런처에 실행 권한을 주지 못했습니다"; return 1
  fi

  # 번들 안에 python 실행파일 복사 → 실행 시 [NSBundle mainBundle]이 ClaudePet.app으로
  # 잡혀 macOS가 문서앱(org.python.python)으로 오인하지 않음 → 보호폴더 프롬프트 제거.
  local PY PYPREFIX PYBIN
  # 명령 치환의 '상태'가 그대로 대입문의 상태가 된다. find_py 의 꼬리는 for 루프고
  # 그 루프의 마지막 명령이 AND-리스트라, AppKit 되는 python 이 하나도 없으면
  # find_py 는 비영으로 끝난다 — 그러면 `PY=$(find_py)` 한 줄에서 set -e 가
  # 스크립트를 죽인다. 아래 else 분기(경고하고 번들 python 없이 계속)는 바로 그
  # 경우를 위해 있는 것이므로, 그 상태로는 영영 닿을 수 없었다: pyobjc 없는
  # 기기의 `./build_app.sh build` 는 경고 대신 아무 말 없이 죽었다.
  # 그래서 상태를 여기서 명시적으로 받아 낸다 — 이 분기가 '도달 가능하도록'.
  if ! PY=$(find_py); then
    PY=""
  fi
  if [ -n "$PY" ]; then
    PYPREFIX=$("$PY" -c 'import sys;print(sys.prefix)' 2>/dev/null)
    PYBIN="$PYPREFIX/Resources/Python.app/Contents/MacOS/Python"
    if [ ! -x "$PYBIN" ]; then PYBIN="$PY"; fi
    if ! cp "$PYBIN" "$APP/Contents/MacOS/ClaudePet_py"; then
      echo "❌ 번들 python 을 복사하지 못했습니다: $PYBIN"; return 1
    fi
    if ! chmod +x "$APP/Contents/MacOS/ClaudePet_py"; then
      echo "❌ 번들 python 에 실행 권한을 주지 못했습니다"; return 1
    fi
    echo "🐍 번들 python: $PYBIN"
  else
    echo "⚠️  AppKit 가능한 python을 못 찾음 — 번들 python 없이 빌드(폴백 실행)"
  fi

  # 서명 실패는 빌드 실패다. 예전에는 상태를 보지 않아, 서명이 실패해도 바로
  # 아래 "✅ 빌드 완료" 가 찍혔다.
  if ! sign_app; then
    echo "❌ 서명 실패 — 빌드를 실패로 봅니다: $APP"; return 1
  fi
  echo "✅ 빌드 완료: $(pwd)/$APP"
}

# AppKit 임포트 되는 framework python 하나 찾기
find_py() {
  local c
  for c in "$HOME/.pyenv/shims/python3" /opt/homebrew/bin/python3 \
           /usr/local/bin/python3 \
           /Library/Frameworks/Python.framework/Versions/Current/bin/python3 \
           /usr/bin/python3; do
    [ -x "$c" ] && "$c" -c "import AppKit" >/dev/null 2>&1 && { echo "$c"; return 0; }
  done
  # 못 찾은 것은 실패다 — 그리고 그 상태는 부르는 쪽에서 명시적으로 받아야 한다.
  # 예전에는 여기서 루프의 AND-리스트 상태가 그대로 새어 나갔고, 부르는 쪽의
  # 명령 치환 대입이 그것을 set -e 에 넘겼다. 상태를 분명히 적어 두되, 이 줄
  # 하나로는 아무것도 고쳐지지 않는다: 고치는 것은 build() 쪽의 `if !` 다.
  return 1
}

# 앱 서명: 정식 Apple 인증서 > 로컬 자체서명(ClaudePet Local) > ad-hoc
# TCC/키체인 권한이 안정적으로 기억되려면 서명이 필요하다.
#
# 이 함수의 성질: **"서명했다"고 찍히면, 찍힌 그대로 서명된 것이다.** 예전에는
# 세 자리가 그 성질을 깨고 있었다 — 엔타이틀먼트가 없으면 조용히 빼고 서명했고,
# 중첩 python 서명 실패는 2>/dev/null 로 삼킨 뒤 그 위에 번들을 서명했고,
# 마지막 ad-hoc 도 실패하면 ✅ 가 안 찍히는 것이 유일한 신호였다. 실패를 알리는
# 유일한 방법이 '아무 말도 안 하는 것'이면, 그건 실패를 알리지 않는 것이다.
# 그래서 여기서는 codesign 의 말을 그대로 흘려보내고(2>/dev/null 없음), 실패한
# 자리마다 ❌ 를 찍고 즉시 멈춘다.
sign_app() {
  local id; local -a opts
  local ENT="$(cd "$(dirname "$0")" && pwd)/entitlements.plist"
  local pybin="$APP/Contents/MacOS/ClaudePet_py"
  local devid=0
  id=$(security find-identity -v -p codesigning 2>/dev/null \
        | grep -Eo '"(Developer ID Application|Apple Development)[^"]*"' | head -1 | tr -d '"')
  if [ -n "$id" ]; then
    devid=1
    # 공증 요건: 하드닝 런타임 + 보안 타임스탬프 + python용 엔타이틀먼트
    opts=(--options runtime --timestamp)
    # 엔타이틀먼트 파일이 없는 것은 '빼고 서명'이 아니라 거절이다. 예전에는
    # `[ -f "$ENT" ] && opts+=(...)` 라, 파일이 없으면 엔타이틀먼트 없는 번들을
    # 정식 인증서로 서명하고 "🔏 서명: Developer ID …" 까지 찍었다 — 서명은
    # 성공했고 산출물은 틀렸으며, 둘을 구별할 방법이 출력에 없었다.
    if [ ! -f "$ENT" ]; then
      echo "❌ 엔타이틀먼트 파일이 없습니다 — 정식 인증서로 서명하지 않습니다: $ENT"
      return 1
    fi
    opts+=(--entitlements "$ENT")
  else
    id="ClaudePet Local"; opts=()          # 로컬 자체서명 (없으면 codesign 실패 → ad-hoc)
  fi
  # 중첩 실행파일(번들 python) 먼저 서명 → 그다음 번들
  #
  # 중첩 서명이 실패했는데 바깥만 성공해서 0 을 돌려주는 길이 있으면 안 된다.
  # 그 번들은 '바깥은 $id, 안은 서명되지 않았거나 예전 신원'인 섞인 산출물인데,
  # 출력에는 "🔏 서명: $id" 만 찍히고 함수는 성공을 돌려준다 — 릴리즈 운영자가
  # "서명 성공"이라고 적는 근거가 바로 그 0 이다. 실패할 수 없는 단계는
  # 아무것도 기록하지 않는 단계다. 그래서 두 갈래만 남긴다: 중첩과 바깥이 같은
  # 신원으로 '둘 다' 서명되거나, 비영으로 끝나거나.
  local nested_failed=0
  if [ -f "$pybin" ]; then
    if ! codesign --force "${opts[@]}" --sign "$id" "$pybin"; then
      if [ $devid -eq 1 ]; then
        echo "❌ 번들 python 서명 실패 — 그 위에 번들을 서명하지 않고 멈춥니다: $pybin"
        return 1
      fi
      # 인증서가 아예 없는 흔한 경우다. 여기서 멈추지 않고 아래 ad-hoc 갈래로
      # 내려가되, 조용히 내려가지도 않고 '반쯤' 내려가지도 않는다 — 바깥을
      # $id 로 서명하는 것을 건너뛰고, 중첩과 바깥을 함께 ad-hoc 으로 맞춘다.
      nested_failed=1
      echo "⚠️  번들 python 서명 실패($id) — 바깥만 그 신원으로 서명하지 않고,"
      echo "    중첩과 바깥을 함께 ad-hoc 으로 내립니다: $pybin"
    fi
  fi
  if [ $nested_failed -eq 0 ]; then
    if codesign --force --identifier me.yeongyu.claudepet "${opts[@]}" --sign "$id" "$APP"; then
      echo "🔏 서명: $id"
      return 0
    fi
    # 정식 인증서로 실패했는데 ad-hoc 으로 내려가는 것은 '강등'이다. 서명은 성공한
    # 것처럼 보이고 산출물은 배포할 수 없는 것이 된다 — 정식 인증서 경로에서는
    # 강등하지 않고 멈춘다.
    if [ $devid -eq 1 ]; then
      echo "❌ 정식 인증서($id) 서명 실패 — ad-hoc 으로 내려가지 않고 멈춥니다: $APP"
      return 1
    fi
  fi
  if [ -f "$pybin" ]; then
    if ! codesign --force --sign - "$pybin"; then
      echo "❌ ad-hoc 서명 실패: $pybin"; return 1
    fi
  fi
  if ! codesign --force --sign - "$APP"; then
    echo "❌ ad-hoc 서명 실패: $APP"; return 1
  fi
  echo "🔏 서명: ad-hoc (인증서 없음)"
}

stop_pet() {
  pkill -f "Resources/claude_pet.py" 2>/dev/null && echo "· 실행 중이던 펫 종료" || true
  sleep 0.3
}

# 경로의 '신원'(장치+아이노드). 요청한 경로 문자열이 아니라 실제로 열린 것이
# 무엇인지 말해 준다. stat 은 기본이 lstat 이라 링크는 링크 자신으로 보고한다.
path_ident() { /usr/bin/stat -f '%d:%i' "$1" 2>/dev/null; }

# 설치본 갱신을 '번들 통째로' 하나의 트랜잭션으로 한다.
#
# 예전에는 설치된 번들 '위에서' 코드 복사 → 자산 교체 → plist → 재서명을 차례로
# 했다. 조각마다 나름의 안전장치는 있었지만 번들 '전체'에는 트랜잭션이 없었다:
# 자산 교체가 실패하면 코드는 새것·자산은 옛것으로, plist 에서 멈추면 코드와
# 자산은 새것·버전은 옛것으로 남는다. 어느 조각의 롤백도 이 상태를 되돌리지
# 못한다 — 조각이 각자 제자리로 돌아가도 번들은 이미 섞여 있기 때문이다.
# 그래서 옆에 완성본을 세우고, 검사까지 끝난 뒤에 한 번에 바꾼다. 되돌리기도
# 한 번이다. (copy_pet_assets 가 자산 트리에 쓰는 계약과 같은 모양이고, 여기서는
# 그 계약을 번들 전체로 한 단계 올린 것이다.)
update_installed() {
  local dest="${1:-$DEST}"
  case "$dest" in
    /*) ;;
    *) echo "❌ 설치 경로가 절대경로가 아닙니다: $dest"; return 1 ;;
  esac
  local parent="${dest:h}" name="${dest:t}"
  local stage="$parent/.$name.new.$$"
  # 고정 이름: 두 rename 사이에서 죽어도 예전 설치본이 '어디 있는지 아는' 이름으로
  # 남아야 한다. $$ 를 붙이면 매번 달라져 남은 것을 찾을 수 없다.
  local backup="$parent/.$name.previous"
  local lock="$parent/.$name.txn.lock"
  if [ ! -d "$parent" ]; then
    echo "❌ 설치 폴더가 없습니다: $parent"; return 1
  fi

  # ── 0. 트랜잭션 전체를 하나씩만 돌린다 ──────────────────────────────
  # 잠금이 '정리보다도 앞'인 이유가 핵심이다. 아래 정리는 .new.* 를 지우는데,
  # 두 번째 실행이 첫 번째가 준비 중인 스테이지를 지우면 첫 번째는 발밑이
  # 사라진 채로 계속 간다. 반대로 잠금을 먼저 잡으면 '남아 있는 .new.* 는
  # 잠금을 쥔 채 죽은 실행의 잔해'가 되어 — 살아 있는 남의 것일 수 없어서 —
  # 지워도 되는 이유가 비로소 생긴다. 잠금은 신원을 확실하게 만드는 장치다.
  # 해제는 함수가 끝날 때다(zsh 에서 함수 안 EXIT 트랩은 함수 종료 시 돈다).
  # 마지막 백업 정리까지 잠금 안에서 끝나야, 그 틈에 들어온 두 번째 실행이
  # 우리 백업을 '남이 남긴 것'으로 보고 멈추는 일이 없다.
  local holder waited=0
  while ! mkdir "$lock" 2>/dev/null; do
    holder=""
    if [ -f "$lock/pid" ]; then holder=$(cat "$lock/pid" 2>/dev/null || true); fi
    if [ -n "$holder" ] && ! kill -0 "$holder" 2>/dev/null; then
      echo "· 죽은 프로세스($holder)가 남긴 잠금을 회수합니다: $lock"
      rm -rf "$lock"; continue
    fi
    if [ $waited -ge 600 ]; then
      echo "❌ 다른 설치/갱신이 아직 돌고 있습니다 — 기다리다 멈춥니다: $lock"; return 1
    fi
    sleep 0.2; waited=$((waited + 1))
  done
  CLAUDEPET_TXN_LOCK="$lock"
  trap 'if [ -n "$CLAUDEPET_TXN_LOCK" ]; then rm -rf "$CLAUDEPET_TXN_LOCK"; fi' EXIT
  echo $$ > "$lock/pid"

  # ── 1. 백업 자리의 신원부터 정한다 ──────────────────────────────────
  # 조상이 링크인 것 자체는 막지 않는다 — /var → /private/var 처럼 시스템이
  # 만든 링크가 흔하고, dest·stage·backup 이 모두 같은 조상을 지나므로 rename 은
  # 여전히 같은 진짜 폴더 안에서 일어난다. 문제가 되는 건 '잎'이다: backup 이
  # 링크면 mv 는 링크 '너머'에 쓰고, 백업은 분명히 만들어졌는데 되돌릴 때
  # 우리가 보는 자리에는 없다. 파괴하기 전에 거절하는 게 낫다.
  local p
  for p in "$stage" "$backup"; do
    if [ -L "$p" ]; then
      echo "❌ 작업 경로가 심볼릭 링크입니다 — 갱신하지 않습니다: $p"; return 1
    fi
  done
  # 우리가 만드는 백업은 언제나 '번들 폴더'다. 그 자리에 폴더가 아닌 것이
  # 있으면 우리가 둔 것이 아니고, 우리가 둔 것이 아니면 지우지도 옮기지도
  # 않는다 — 남의 것을 지우는 실수는 되돌릴 수 없고, 남겨 두는 실수는 되돌릴
  # 수 있다. 예전에는 여기서 무조건 rm -rf "$backup" 했다.
  if [ -e "$backup" ] && [ ! -d "$backup" ]; then
    echo "❌ 백업 자리에 우리가 만들지 않은 것이 있습니다 — 지우지도 옮기지도 않습니다: $backup"
    echo "   내용을 확인하고 손으로 치운 뒤 다시 실행하세요."
    return 1
  fi

  # 복구를 '어떤 파괴적 정리보다도' 먼저 한다. 정리를 먼저 하면 유일하게 남은
  # 사본을 그 정리가 지운다.
  if [ -d "$backup" ] && [ ! -e "$dest" ] && [ ! -L "$dest" ]; then
    local backup_id
    backup_id=$(path_ident "$backup" || true)
    if ! mv "$backup" "$dest"; then
      echo "❌ 이전 실행이 남긴 설치본을 되돌리지 못했습니다: $backup"; return 1
    fi
    if [ -z "$backup_id" ] || [ "$(path_ident "$dest" || true)" != "$backup_id" ]; then
      echo "❌ 되돌린 설치본이 요청한 자리에 있지 않습니다: $dest"; return 1
    fi
    echo "↩️  이전 실행이 중단된 흔적을 발견해 예전 설치본을 되돌렸습니다"
  fi

  if [ ! -d "$dest" ] || [ -L "$dest" ]; then
    echo "⚠️  $dest 가 없어요. 먼저 ./build_app.sh install"; return 1
  fi
  # 설치본이 제자리에 있는데 백업까지 남아 있다면, 교체 뒤 정리 직전에 죽은
  # 흔적이다. 어느 쪽이 최신인지 우리가 알 수 없으므로 지우지 않고 멈춘다.
  if [ -e "$backup" ]; then
    echo "❌ 이전 실행이 남긴 백업이 있습니다 — 지우지 않고 멈춥니다: $backup"
    echo "   설치본은 제자리에 있으니, 백업을 확인해 치운 뒤 다시 실행하세요."
    return 1
  fi

  # ── 2. 원본 번들의 '잎'을 손대기 전에 본다 ──────────────────────────
  # 링크를 통해 쓰면 번들 바깥의 남의 파일이 바뀐다. ditto 는 링크를 링크로
  # 옮기므로 스테이지에도 그대로 남고, 그 뒤의 cp·자산 교체·plist 쓰기가
  # 전부 링크 너머로 나간다. 그래서 스테이지를 만들기 전에 — 아무것도 쓰기
  # 전에 — 거절한다.
  local leaf
  for leaf in Contents Contents/Resources Contents/MacOS; do
    if [ -L "$dest/$leaf" ] || [ ! -d "$dest/$leaf" ]; then
      echo "❌ 설치본의 $leaf 가 실제 폴더가 아닙니다 — 갱신하지 않습니다"; return 1
    fi
  done
  for leaf in Contents/Info.plist Contents/Resources/claude_pet.py Contents/MacOS/ClaudePet; do
    if [ -L "$dest/$leaf" ] || [ ! -f "$dest/$leaf" ]; then
      echo "❌ 설치본의 $leaf 가 일반 파일이 아닙니다 — 갱신하지 않습니다"; return 1
    fi
  done

  # ── 3. 잠금을 잡은 뒤에야 정리한다 ──────────────────────────────────
  local -a stale
  stale=("$parent"/.$name.new.*(N))        # (N) = 없으면 빈 목록
  local s
  for s in "${stale[@]}"; do
    if [ -L "$s" ] || [ ! -d "$s" ]; then
      echo "⚠️  폴더가 아니라 치우지 않고 둡니다: $s"; continue
    fi
    rm -rf "$s"
  done
  if [ -e "$stage" ] || [ -L "$stage" ]; then
    echo "❌ 작업 경로를 비우지 못했습니다 — 갱신하지 않습니다: $stage"; return 1
  fi

  # ── 4. 옆에 완성본을 세운다 ────────────────────────────────────────
  # ditto: 심볼릭 링크·확장속성·리소스포크를 그대로 옮긴다. cp -R 은 확장속성을
  # 흘려서 서명 봉인이 깨진다.
  if ! /usr/bin/ditto "$dest" "$stage"; then
    rm -rf "$stage"
    echo "❌ 설치본 복사 실패 — 기존 설치본은 그대로 둡니다"; return 1
  fi
  if ! cp claude_pet.py "$stage/Contents/Resources/claude_pet.py" \
     || ! copy_pet_assets "$stage" \
     || ! write_plist "$stage" \
     || ! APP="$stage" sign_app; then
    rm -rf "$stage"
    echo "❌ 갱신 준비 실패 — 기존 설치본은 그대로 둡니다"; return 1
  fi

  # ── 5. 바꾸기 '전에' 완성본을 확인한다 ──────────────────────────────
  # '만들었다'와 '쓸 수 있다'는 다른 말이다. 여기서 안 보면 확인은 옛 설치본을
  # 치운 뒤에나 할 수 있고, 그때는 이미 늦다.
  if ! "${PYCHECK:-python3}" verify_pet_payload.py \
         "$stage/Contents/Resources/.claude_pet" --quiet; then
    rm -rf "$stage"
    echo "❌ 완성본 자산 검사 실패 — 기존 설치본은 그대로 둡니다"; return 1
  fi
  # 코드는 '있다'가 아니라 '체크아웃의 그 바이트'여야 한다. 이름만 맞고 내용이
  # 낡은 번들은 서명까지 통과하면서 옛 코드를 그대로 배달한다 — 사용자에게는
  # '업데이트했는데 아무것도 안 바뀌었다'로만 보인다.
  local code="$stage/Contents/Resources/claude_pet.py"
  if [ -L "$code" ] || [ ! -f "$code" ]; then
    rm -rf "$stage"
    echo "❌ 완성본의 코드가 일반 파일이 아닙니다 — 기존 설치본은 그대로 둡니다"; return 1
  fi
  local want got
  want=$(shasum -a 256 claude_pet.py 2>/dev/null | cut -d' ' -f1)
  got=$(shasum -a 256 "$code" 2>/dev/null | cut -d' ' -f1)
  if [ -z "$want" ] || [ "$got" != "$want" ]; then
    rm -rf "$stage"
    echo "❌ 완성본의 코드가 체크아웃과 다릅니다 — 기존 설치본은 그대로 둡니다"; return 1
  fi
  # 두 키를 다 본다. 업데이터가 비교하는 것은 CFBundleShortVersionString 이지만
  # LaunchServices 가 보는 것은 CFBundleVersion 이라, 한쪽만 맞은 번들은 '맞는
  # 버전'과 '틀린 버전'을 동시에 주장한다.
  local key
  for key in CFBundleShortVersionString CFBundleVersion; do
    got=$(/usr/libexec/PlistBuddy -c "Print :$key" \
            "$stage/Contents/Info.plist" 2>/dev/null || true)
    if [ "$got" != "$APP_VERSION" ]; then
      rm -rf "$stage"
      echo "❌ 완성본의 $key 가 $APP_VERSION 이 아님 (${got:-읽지 못함}) — 기존 설치본은 그대로 둡니다"
      return 1
    fi
  done
  # -x 만 보면 안 된다. 심볼릭 링크도, 0700 짜리 폴더도 -x 를 통과한다.
  local exe="$stage/Contents/MacOS/ClaudePet"
  if [ -L "$exe" ] || [ ! -f "$exe" ] || [ ! -x "$exe" ]; then
    rm -rf "$stage"
    echo "❌ 완성본의 실행파일이 일반 실행파일이 아닙니다 — 기존 설치본은 그대로 둡니다"; return 1
  fi

  # ── 6. 한 번에 바꾼다 ───────────────────────────────────────────────
  # 순서의 성질: **거절할 수 있는 것은 무엇도 stop_pet 뒤에 오지 않는다.**
  # 이미 사용자를 방해한 뒤에 하는 거절은 '아무것도 안 했다'가 아니라 '펫만
  # 죽이고 아무것도 안 했다'이다. 신원 읽기는 여기서 유일하게 남아 있던 그런
  # 자리였다 — 실패하면 교체를 멈추면서 이미 펫은 멈춘 뒤였고, 그래서 open 으로
  # 도로 띄우는 보상 코드가 필요했다. 읽기를 stop_pet 앞으로 옮기면 그 보상은
  # 필요 없어진다. 보상이 사라지는 것이 이 순서가 맞다는 표시다.
  local dest_id stage_id
  dest_id=$(path_ident "$dest" || true); stage_id=$(path_ident "$stage" || true)
  if [ -z "$dest_id" ] || [ -z "$stage_id" ]; then
    rm -rf "$stage"
    echo "❌ 신원을 읽지 못해 교체를 멈춥니다 — 기존 설치본은 그대로 둡니다"
    return 1
  fi
  # 펫은 여기서 처음 멈춘다. 위에서 실패하면 펫은 멈춘 적조차 없다.
  stop_pet
  if ! mv "$dest" "$backup"; then
    rm -rf "$stage"
    echo "❌ 기존 설치본을 옮기지 못했습니다 — 그대로 둡니다"
    open "$dest"
    return 1
  fi
  # 옮긴 '결과'를 본다 — 요청한 경로가 아니라 실제로 열리는 것을. 위에서 자리가
  # 비어 있는 것을 봤더라도 그건 '봤을 때'의 이야기고, 그 사이에 다른 것이
  # 생겼으면 rename 은 그것을 덮지 않고 그 '안으로' 들어간다. 이름만 확인하면
  # 그 차이가 안 보인다.
  if [ "$(path_ident "$backup" || true)" != "$dest_id" ]; then
    if [ "$(path_ident "$backup/$name" || true)" = "$dest_id" ] && mv "$backup/$name" "$dest"; then
      echo "↩️  백업 자리에 다른 것이 있어 설치본이 그 안으로 들어갔습니다 — 도로 꺼냈습니다"
      open "$dest"
    fi
    rm -rf "$stage"
    echo "❌ 백업이 요청한 자리에 생기지 않았습니다: $backup"
    echo "   예전 설치본을 잃지 않기 위해 여기서 멈춥니다 — 손으로 확인하세요."
    return 1
  fi
  if ! mv "$stage" "$dest"; then
    # 되돌리기의 '결과'를 반드시 본다. 결과를 안 보고 되돌렸다고 찍으면,
    # 실패했는데 성공했다고 말하게 된다.
    if [ ! -e "$dest" ] && mv "$backup" "$dest" \
       && [ "$(path_ident "$dest" || true)" = "$dest_id" ]; then
      rm -rf "$stage"
      echo "❌ 설치본 교체 실패 — 기존 설치본을 되돌렸습니다"
      # 바이트만 제자리에 돌려놓고 앱은 멈춘 채로 두면, 되돌린 것이 아니다 —
      # 사용자에게는 '갱신했더니 펫이 사라졌다'로 보인다. 멈춘 것은 우리이니
      # 다시 띄우는 것까지가 롤백이다.
      open "$dest"
      return 1
    fi
    rm -rf "$stage"
    echo "❌ 설치본 교체 실패, 되돌리기도 실패했습니다."
    echo "   예전 설치본은 지우지 않았습니다 — 여기 있습니다: $backup"
    return 1
  fi
  if [ "$(path_ident "$dest" || true)" != "$stage_id" ]; then
    echo "❌ 갱신본이 요청한 자리에 들어가지 않았습니다: $dest"
    echo "   예전 설치본은 여기 있습니다: $backup"
    return 1
  fi
  # 마지막 정리도 신원에 묶는다. 지우려는 것이 '우리가 방금 옮겨 둔 그것'이
  # 아니면 지우지 않는다. 이름만 보고 지우면, 그 사이에 그 이름으로 생긴
  # 남의 것을 지우게 된다.
  if [ "$(path_ident "$backup" || true)" != "$dest_id" ]; then
    echo "⚠️  백업 자리의 것이 우리가 옮겨 둔 그것이 아닙니다 — 지우지 않고 둡니다: $backup"
    return 0
  fi
  rm -rf "$backup"
}

# ─── 인앱 업데이터와 '같은 객체'로 직렬화하기 ──────────────────────────
# 여기까지의 잠금(설치 목적지의 .txn.lock, 레포 트리의 build lock)은 둘 다 이
# 스크립트끼리만 아는 자리다. 인앱 업데이터는 그중 어느 것도 보지 않는다 —
# 그쪽이 잠그는 것은 claude_pet.py 의 _acquire_update_lock() 이 flock 으로 잡는
# ~/Library/Caches/me.yeongyu.claudepet/update-<번들이름>.lock 하나뿐이다.
# 그래서 손으로 도는 트랜잭션과 인앱 업데이트가 같은 번들을 동시에 맞바꿀 수
# 있었다: 각자 잠금은 잘 잡았고, 서로 다른 것을 잠갔을 뿐이다.
#
# 셸은 그 객체를 직접 잠글 수 없다(macOS 에 flock(1) 이 없고, 이름으로 다시 여는
# 것은 그쪽이 하지 않기로 한 열기다). 그래서 파이썬이 잠금을 들고 이 스크립트가
# 그 안에서 자식으로 돈다 — claude_pet.py --with-update-lock <APP> -- <명령>.
#
# **잠금 순서는 하나뿐이다: update-lock → txn → build.** 바깥에서 안으로만 잡고,
# 어디서도 반대로 잡지 않는다. 이 래퍼가 가장 바깥이라 그 순서가 지켜진다.
#
# 재진입 위험이 이 구조의 핵심이다: 이 파일은 로드되면 dispatch 가 돈다. 래퍼가
# 자기 자신을 다시 부르므로, 표시가 없으면 안쪽 실행이 또 자기를 감싸 무한히
# 내려간다. 그래서 안쪽은 '내부 전용 서브커맨드'(__install_txn/__update_txn)로
# 부르고, 그 arm 은 잠금을 다시 잡지 않고 트랜잭션 본문만 돈다.
# CLAUDEPET_UPDATE_LOCK_HELD 는 그 arm 이 잠금 밖에서 직접 실행되는 것을 막는
# 두 번째 표시다.
run_under_update_lock() {
  # $1 = 잠글 번들 경로(인앱 업데이터가 쓰는 그 경로여야 한다), $2 = 내부 서브커맨드
  local target="$1" sub="$2"
  if [ "$CLAUDEPET_UPDATE_LOCK_HELD" = "1" ]; then
    # 이미 이 잠금 안이다. flock 은 재진입이 아니라 같은 프로세스가 다시 잡아도
    # 되는 대신 여기서 새 프로세스를 띄우면 자기 자신과 교착한다 — 감싸지 않고
    # 바로 본문으로 간다.
    "$SELF" "$sub"
    return
  fi
  # 자식의 종료 상태는 그대로 올라온다. 100(다른 업데이터가 들고 있음)과
  # 101(잠금 자리를 믿을 수 없음)은 래퍼가 쓰는 값이라, 아래 내부 arm 은
  # 그 둘을 자기 뜻으로 쓰지 않는다(0 또는 1 로만 끝난다).
  CLAUDEPET_UPDATE_LOCK_HELD=1 "${PYCHECK:-python3}" claude_pet.py \
      --with-update-lock "$target" -- "$SELF" "$sub"
}

# 래퍼가 돌려준 상태를 사람 말로 옮긴다. 조용히 1 로 끝나면 '무엇이 막았는지'가
# 사라진다.
lock_rc_note() {
  case "$1" in
    100) echo "❌ 다른 업데이트가 이미 진행 중입니다(인앱 업데이터 포함) — 아무것도 하지 않았습니다" ;;
    101) echo "❌ 업데이트 잠금 자리를 믿을 수 없어 멈춥니다 — 아무것도 하지 않았습니다" ;;
    127) echo "❌ 잠금 안에서 트랜잭션을 실행하지 못했습니다: $SELF" ;;
    2)   echo "❌ 잠금 래퍼 사용법이 틀렸습니다 — 아무것도 하지 않았습니다" ;;
  esac
}

# 내부 arm 이 잠금 밖에서 도는 것을 막는다. 이 검사가 없으면 손으로
# `./build_app.sh __install_txn` 을 쳐서 직렬화 없이 트랜잭션을 돌릴 수 있다.
require_update_lock() {
  if [ "$CLAUDEPET_UPDATE_LOCK_HELD" != "1" ]; then
    echo "❌ 내부 전용 서브커맨드입니다 — 업데이트 잠금 밖에서는 돌지 않습니다: $1"
    echo "   ./build_app.sh install 또는 ./build_app.sh update 를 쓰세요."
    return 1
  fi
  return 0
}

# ─── source 방지 가드 ───────────────────────────────────────────────
# 이 파일을 함수만 쓰려고 source 하면 아래 dispatch 가 돌아 버린다. 인자가
# 없으면 `*)` 로 떨어져 build 가 돌고, build() 끝에서 sign_app 이 Developer ID
# 로 서명한다 — 테스트가 함수 하나 쓰려다 실제로 서명한 적이 있다.
# 실행됐을 때만 dispatch 한다.
# (zsh 스크립트다. bash 의 `(return 0 2>/dev/null)` 관용구는 zsh 에서 실행
#  중에도 참이 되어 정반대로 동작한다 — 실제 zsh 로 확인하고 이 형태를 썼다.)
case "${ZSH_EVAL_CONTEXT}" in *:file*) return 0 ;; esac

case "$1" in
  install)
    # 트랜잭션 '전체'를 인앱 업데이터와 같은 잠금 안에서 돌린다 — 목적지 검사,
    # stop_pet, 복사, 교체, 되돌리기, 마지막 백업 정리까지. 앞부분만 덮으면
    # 덮이지 않은 뒤쪽이 정확히 인앱 업데이트와 부딪히는 자리다.
    if run_under_update_lock "$DEST" __install_txn; then
      PET_RC=0
    else
      PET_RC=$?
    fi
    if [ $PET_RC -ne 0 ]; then
      lock_rc_note $PET_RC
      exit $PET_RC
    fi
    ;;
  update)
    # install 과 같은 이유로 update 도 통째로 잠금 안이다.
    if run_under_update_lock "$DEST" __update_txn; then
      PET_RC=0
    else
      PET_RC=$?
    fi
    if [ $PET_RC -ne 0 ]; then
      lock_rc_note $PET_RC
      exit $PET_RC
    fi
    ;;
  __install_txn)
    if ! require_update_lock "$1"; then exit 1; fi
    # 설치도 갱신과 같은 트랜잭션이다. 예전에는 stop → rm -rf "$DEST" → cp -R 였고,
    # 복사나 서명이 중간에 실패하면 설치본이 '지워진 채로' 남았다 — 목적지를
    # 내용이 완성되기 전에 부수는, 이 저장소가 계속 거절해 온 그 모양이다.
    # 이제는 예전 것을 옆으로 '옮겨' 두고 복사하며, 실패하면 도로 제자리에 놓고
    # 멈춰 둔 펫까지 다시 띄운다.
    #
    # (update_installed 와 같은 절차를 여기 그대로 적은 이유: 이 arm 은 함수를
    #  거치지 않고 검증되는 자리라, 잠금·백업·되돌리기를 함수 뒤로 숨기면
    #  이 arm 을 확인하는 쪽에서는 아무것도 안 보인다.)
    INST_PARENT="${DEST:h}"; INST_NAME="${DEST:t}"
    INST_BACKUP="$INST_PARENT/.$INST_NAME.previous"
    INST_LOCK="$INST_PARENT/.$INST_NAME.txn.lock"
    INST_FAILED="$INST_PARENT/.$INST_NAME.failed.$$"
    if [ ! -d "$INST_PARENT" ]; then
      echo "❌ 설치 폴더가 없습니다: $INST_PARENT"; exit 1
    fi
    # 설치와 갱신은 같은 잠금을 쓴다 — 둘이 동시에 같은 번들을 만지면 어느
    # 쪽의 롤백도 상대가 만든 상태를 되돌리지 못한다.
    #
    # **잠금이 build 보다 앞이다.** 예전에는 build 가 맨 위에 있었다. build() 는
    # 레포의 ClaudePet.app 을 rm -rf 하고 다시 세우는데, 그건 두 설치가 공유하는
    # 하나의 트리다 — 잠금 밖에서 만지면 두 번째 설치의 rm -rf 가 첫 번째가
    # 서명하려던 번들을 걷어낸다. 트랜잭션이 지켜야 할 것은 목적지만이 아니라
    # '이번 트랜잭션이 쓰는 모든 것'이다.
    #
    # (더 강한 모양은 트랜잭션마다 자기만의 빌드 자리를 갖는 것이다 — 공유
    #  객체를 직렬화하는 대신 없애는 쪽. 여기서 그걸 고르지 않은 이유는 자리가
    #  없어서다: 레포 안에 두면 크래시가 추적되지 않는 폴더를 레포 루트에 남기고
    #  (.gitignore 는 이 변경의 소유가 아니다), 릴리즈 게이트는 그걸 '더러운
    #  트리'로 읽는다. /Applications 옆에 두면 남은 스테이지를 누가 언제 쓸어야
    #  하는가라는 문제가 새로 생기고, 그 답이 결국 이 잠금이다.)
    #
    # 그래서 build() 자신도 레포 트리 잠금을 따로 잡는다 — 이 arm 을 거치지 않는
    # 맨 `./build_app.sh build` 는 여기 txn 잠금을 지나가지 않기 때문이다.
    # **순서는 txn → build 하나뿐이다**(이 arm 이 그 순서를 만든다). 반대 방향,
    # 즉 빌드 잠금을 쥔 채 이 txn 잠금을 잡는 코드를 추가하면 교착이 생긴다.
    INST_WAITED=0
    while ! mkdir "$INST_LOCK" 2>/dev/null; do
      INST_HOLDER=""
      if [ -f "$INST_LOCK/pid" ]; then
        INST_HOLDER=$(cat "$INST_LOCK/pid" 2>/dev/null || true)
      fi
      if [ -n "$INST_HOLDER" ] && ! kill -0 "$INST_HOLDER" 2>/dev/null; then
        echo "· 죽은 프로세스($INST_HOLDER)가 남긴 잠금을 회수합니다: $INST_LOCK"
        rm -rf "$INST_LOCK"; continue
      fi
      if [ $INST_WAITED -ge 600 ]; then
        echo "❌ 다른 설치/갱신이 아직 돌고 있습니다 — 기다리다 멈춥니다: $INST_LOCK"; exit 1
      fi
      sleep 0.2; INST_WAITED=$((INST_WAITED + 1))
    done
    CLAUDEPET_TXN_LOCK="$INST_LOCK"
    # EXIT 트랩은 두 잠금을 다 놓는다. 빌드 잠금 쪽에서 깊이를 0 으로 되돌린 뒤
    # 놓는 이유: build() 안에서 죽으면 깊이가 1 이라 release_build_lock 이 감소만
    # 하고 실제 자리는 남는다 — 그러면 이후의 모든 빌드가 영영 막힌다. 여기서는
    # 프로세스가 끝나는 자리이므로 '진짜 해제'가 정확히 한 번 일어나야 한다.
    # release_build_lock 은 CLAUDEPET_BUILD_LOCK 을 비우므로 두 번 돌아도 안전하다.
    trap 'if [ -n "$CLAUDEPET_TXN_LOCK" ]; then rm -rf "$CLAUDEPET_TXN_LOCK"; fi
          CLAUDEPET_BUILD_REENTRY=0; release_build_lock' EXIT
    echo $$ > "$INST_LOCK/pid"

    # 레포 트리 잠금은 build() 안이 아니라 '여기'서 잡는다. build() 가 자기 안에서
    # 잡고 돌려주면, build 가 끝난 뒤에도 이 arm 이 계속 만지는 공유 트리($APP)가
    # — 해시하고, 복사하고, 서명하는 그 내내 — 잠금 밖에 놓인다. 그 창으로 맨
    # `./build_app.sh build` 가 걸어 들어와 rm -rf 로 트리를 걷어낸다.
    # 바깥에서 먼저 잡아 두면 build() 안의 acquire 는 깊이 증가일 뿐이라, build 가
    # 돌아와도 진짜 잠금은 이 arm 이 계속 쥔다. 순서는 txn → build 그대로다.
    if ! acquire_build_lock; then
      echo "❌ 레포 빌드 잠금을 잡지 못했습니다 — 설치하지 않습니다"; exit 1
    fi

    # 잠금을 쥔 뒤에 빌드한다. 여기서 실패하면 EXIT 트랩이 잠금을 놓아 주고,
    # 목적지는 아직 아무도 건드리지 않았다.
    build

    # 올릴 것부터 본다 — 목적지를 건드리기 전에. (버전 키는 여기서 보지 않는다:
    #  방금 위의 build 가 같은 프로세스에서 같은 APP_VERSION 으로 write_plist 한
    #  것이라, 여기서 다시 보는 것은 스스로가 방금 쓴 값을 자기에게 되묻는 것이다.
    #  '설치본'의 버전은 갱신 경로에서 실제로 검사한다.)
    if [ -L "$APP/Contents/Resources/claude_pet.py" ] \
       || [ ! -f "$APP/Contents/Resources/claude_pet.py" ]; then
      echo "❌ 빌드본의 코드가 일반 파일이 아닙니다 — 설치하지 않습니다"; exit 1
    fi
    INST_WANT=$(shasum -a 256 claude_pet.py 2>/dev/null | cut -d' ' -f1)
    INST_GOT=$(shasum -a 256 "$APP/Contents/Resources/claude_pet.py" 2>/dev/null | cut -d' ' -f1)
    if [ -z "$INST_WANT" ] || [ "$INST_GOT" != "$INST_WANT" ]; then
      echo "❌ 빌드본의 코드가 체크아웃과 다릅니다 — 설치하지 않습니다"; exit 1
    fi
    if [ -L "$APP/Contents/MacOS/ClaudePet" ] || [ ! -f "$APP/Contents/MacOS/ClaudePet" ] \
       || [ ! -x "$APP/Contents/MacOS/ClaudePet" ]; then
      echo "❌ 빌드본의 실행파일이 일반 실행파일이 아닙니다 — 설치하지 않습니다"; exit 1
    fi

    # ── 거절과 복구는 전부 stop_pet '앞'에서 끝낸다 ──────────────────────
    # 순서의 성질: **이미 사용자를 방해한 것 뒤에는, 거절할 수 있는 것을 두지
    # 않는다.** 예전에는 stop_pet 이 이 검사들보다 앞에 있었다. 그래서 실패
    # 모드가 '펫을 죽이고, 거절하고, 아무것도 나아진 것 없이 끝난다'였다 —
    # 거절 자체는 옳았지만 그 대가를 사용자가 이미 치른 뒤였다. 거절이 무해하려면
    # 아무것도 방해하기 전에 나와야 한다. (목적지 검사를 build 앞이 아니라
    #  여기 두는 것은 일부러다: 잠금은 인앱 업데이터와만 직렬화할 뿐, 그 잠금을
    #  잡지 않는 바깥의 변경(사용자, Finder, 다른 도구)은 막지 못하므로,
    #  목적지 상태는 '빌드 시작 시점'이 아니라 '손대기 직전'에 봐야 한다.)
    INST_OLD_ID=""
    if [ -L "$INST_BACKUP" ]; then
      echo "❌ 백업 자리가 심볼릭 링크입니다 — 손대지 않습니다: $INST_BACKUP"; exit 1
    fi
    if [ -e "$INST_BACKUP" ] && [ ! -d "$INST_BACKUP" ]; then
      echo "❌ 백업 자리에 우리가 만들지 않은 것이 있습니다 — 지우지도 옮기지도 않습니다: $INST_BACKUP"
      echo "   내용을 확인하고 손으로 치운 뒤 다시 실행하세요."
      exit 1
    fi
    # 크래시 복구: 설치본이 사라졌는데 백업이 남아 있으면, 교체 도중에 죽은
    # 흔적이다. 그대로 새 설치를 하면 그 백업은 아무도 읽지 않는 사본으로 영영
    # 남고, 이번 설치가 실패하면 "설치된 것은 없습니다"라고 말하게 된다 —
    # 되돌릴 사본이 바로 옆에 있는데도. 새 설치를 시작하기 전에 되돌린다.
    # (update_installed 에는 이 복구가 있었고 여기에는 없었다. 같은 계약을 두
    #  곳에서 지키는데 한쪽에만 복구가 있으면, 없는 쪽이 실제 강도다.)
    if [ -d "$INST_BACKUP" ] && [ ! -e "$DEST" ] && [ ! -L "$DEST" ]; then
      INST_BACKUP_ID=$(path_ident "$INST_BACKUP" || true)
      if [ -z "$INST_BACKUP_ID" ]; then
        echo "❌ 이전 실행이 남긴 설치본의 신원을 읽지 못했습니다 — 손대지 않습니다: $INST_BACKUP"
        exit 1
      fi
      if ! mv "$INST_BACKUP" "$DEST"; then
        echo "❌ 이전 실행이 남긴 설치본을 되돌리지 못했습니다: $INST_BACKUP"; exit 1
      fi
      if [ "$(path_ident "$DEST" || true)" != "$INST_BACKUP_ID" ]; then
        echo "❌ 되돌린 설치본이 요청한 자리에 있지 않습니다: $DEST"; exit 1
      fi
      echo "↩️  이전 실행이 중단된 흔적을 발견해 예전 설치본을 되돌렸습니다"
    fi
    if [ -e "$DEST" ] || [ -L "$DEST" ]; then
      if [ -L "$DEST" ] || [ ! -d "$DEST" ]; then
        echo "❌ 설치 자리가 실제 폴더가 아닙니다 — 손대지 않습니다: $DEST"; exit 1
      fi
      # 설치본이 제자리에 있는데 백업까지 남아 있다면, 교체 뒤 정리 직전에 죽은
      # 흔적이다. 어느 쪽이 최신인지 우리가 알 수 없으므로 지우지 않고 멈춘다.
      if [ -e "$INST_BACKUP" ] || [ -L "$INST_BACKUP" ]; then
        echo "❌ 이전 실행이 남긴 백업이 있습니다 — 지우지 않고 멈춥니다: $INST_BACKUP"
        echo "   설치본은 제자리에 있으니, 백업을 확인해 치운 뒤 다시 실행하세요."
        exit 1
      fi
      # 예전 설치본은 '지우지' 않고 옆으로 옮긴다. 옮겨 둔 것의 신원을 붙잡아
      # 두고, 되돌릴 때도 그 신원으로 확인한다. 신원 읽기도 stop_pet 앞이다 —
      # 못 읽어서 거절하는 것 역시 거절이다.
      INST_OLD_ID=$(path_ident "$DEST" || true)
      if [ -z "$INST_OLD_ID" ]; then
        echo "❌ 기존 설치본의 신원을 읽지 못했습니다 — 손대지 않습니다: $DEST"; exit 1
      fi
    fi

    # 펫은 여기서 처음 멈춘다. 위에서 실패하면 펫은 멈춘 적조차 없다.
    stop_pet
    if [ -n "$INST_OLD_ID" ]; then
      if ! mv "$DEST" "$INST_BACKUP"; then
        echo "❌ 기존 설치본을 옮기지 못했습니다 — 그대로 둡니다: $DEST"
        # 멈춘 것은 우리이니 다시 띄우는 것까지가 원상복구다.
        open "$DEST"
        exit 1
      fi
      # 옮긴 '결과'를 본다 — 요청한 경로가 아니라 실제로 열리는 것을. 그 사이에
      # 백업 이름으로 폴더가 생겼으면 rename 은 덮지 않고 그 '안으로' 들어간다.
      if [ "$(path_ident "$INST_BACKUP" || true)" != "$INST_OLD_ID" ]; then
        if [ "$(path_ident "$INST_BACKUP/$INST_NAME" || true)" = "$INST_OLD_ID" ] \
           && mv "$INST_BACKUP/$INST_NAME" "$DEST"; then
          echo "↩️  백업 자리에 다른 것이 있어 설치본이 그 안으로 들어갔습니다 — 도로 꺼냈습니다"
          open "$DEST"
        fi
        echo "❌ 백업이 요청한 자리에 생기지 않았습니다: $INST_BACKUP"
        echo "   예전 설치본을 잃지 않기 위해 여기서 멈춥니다 — 손으로 확인하세요."
        exit 1
      fi
    fi
    INST_RC=0; INST_WHY=""
    if ! cp -R "$APP" "$DEST"; then INST_RC=1; INST_WHY="복사"; fi
    if [ $INST_RC -eq 0 ]; then
      xattr -dr com.apple.quarantine "$DEST" 2>/dev/null || true
      # 설치본 재서명 (복사 후 봉인 보장)
      if ! APP="$DEST" sign_app; then INST_RC=1; INST_WHY="서명"; fi
    fi
    if [ $INST_RC -ne 0 ]; then
      # 만들다 만 것도 '지우지' 않는다 — 옆으로 치워 두고 예전 것을 되돌린다.
      INST_LEFT=""
      if [ -e "$DEST" ] || [ -L "$DEST" ]; then
        if mv "$DEST" "$INST_FAILED"; then INST_LEFT="$INST_FAILED"; fi
      fi
      if [ -n "$INST_OLD_ID" ] && [ ! -e "$DEST" ] && [ ! -L "$DEST" ] \
         && mv "$INST_BACKUP" "$DEST" \
         && [ "$(path_ident "$DEST" || true)" = "$INST_OLD_ID" ]; then
        echo "❌ 설치 $INST_WHY 실패 — 기존 설치본을 되돌렸습니다: $DEST"
        open "$DEST"
      elif [ -n "$INST_OLD_ID" ]; then
        echo "❌ 설치 $INST_WHY 실패, 되돌리기도 실패했습니다."
        echo "   예전 설치본은 지우지 않았습니다 — 여기 있습니다: $INST_BACKUP"
      else
        echo "❌ 설치 $INST_WHY 실패 — 설치된 것은 없습니다"
      fi
      # 치워 둔 것이 있으면 어디 있는지 말한다. 말하지 않으면 그건 '보존'이
      # 아니라 사용자가 모르는 쓰레기다 — /Applications 에 조용히 쌓인다.
      if [ -n "$INST_LEFT" ]; then
        echo "   만들다 만 설치본은 지우지 않고 여기 두었습니다: $INST_LEFT"
      fi
      exit 1
    fi
    if [ -n "$INST_OLD_ID" ]; then
      if [ "$(path_ident "$INST_BACKUP" || true)" = "$INST_OLD_ID" ]; then
        rm -rf "$INST_BACKUP"
      else
        echo "⚠️  백업 자리의 것이 우리가 옮겨 둔 그것이 아닙니다 — 지우지 않고 둡니다: $INST_BACKUP"
      fi
    fi
    echo "✅ 설치: $DEST"
    open "$DEST"
    echo "🐱 실행!"
    ;;
  __update_txn)
    if ! require_update_lock "$1"; then exit 1; fi
    # 코드·펫자산·plist·서명을 하나의 트랜잭션으로 갈아 끼운다. 실패하면 설치본은
    # 손대기 전 그대로다 — 반쯤 갱신된 번들은 남지 않는다.
    # (코드만 갈면 번들 안의 .claude_pet 이 낡은 채로 남아 새 펫이 사용자 홈에
    #  영영 안 깔리고, 버전이 안 맞으면 업데이터가 잘못된 값을 비교한다. 그래서
    #  넷은 같이 움직여야 하고, 같이 움직인다는 건 같이 되돌아온다는 뜻이다.)
    #
    # 갱신하는 것은 그 넷뿐이다. frames/ 는 설치본에 있던 것을 그대로 물려받는다
    # (ditto 로 복사한 뒤 덮어쓰지 않는다). 스프라이트를 바꿨다면 install 을
    # 쓴다 — 여기서 범위를 넓히지 않고, 대신 이름을 좁혀 적는다.
    update_installed "$DEST" || exit 1
    echo "✅ 코드·펫자산·버전·서명 갱신: $DEST (v$APP_VERSION) — frames/ 는 그대로"
    open "$DEST"
    echo "🐱 재시작!"
    ;;
  build)
    build
    echo "설치까지 하려면: ./build_app.sh install"
    ;;
  # 모르는 인자와 '인자 없음'은 같은 곳으로 — 오타가 빌드로 이어지면 안 된다.
  # 예전에는 여기서 build 가 돌았고, build() 끝의 sign_app 이 Developer ID 로
  # 서명까지 했다. 오타 하나가 서명을 부르는 경로였다. 되돌리지 말 것.
  ""|*)
    echo "사용법: ./build_app.sh [build|install|update]"
    echo "  build    레포 안에 ClaudePet.app 빌드만"
    echo "  install  빌드 → /Applications 설치 → 재시작 (추천)"
    echo "  update   설치본의 코드·펫자산·버전·서명 갱신 후 재시작 (frames/ 는 제외, 가장 빠름)"
    exit 1
    ;;
esac
