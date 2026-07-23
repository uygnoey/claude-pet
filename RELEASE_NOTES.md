🐱 A desktop pet that watches your Claude token usage on macOS.

📖 Full README: [English](https://github.com/uygnoey/claude-pet/blob/main/README.md) · [한국어](https://github.com/uygnoey/claude-pet/blob/main/README.ko.md) · [日本語](https://github.com/uygnoey/claude-pet/blob/main/README.ja.md) · [Español](https://github.com/uygnoey/claude-pet/blob/main/README.es.md)

---

### 🇺🇸 English

**Install**
1. Download **ClaudePet.zip** below (**Intel Mac**: download **ClaudePet-universal.zip**) → unzip
2. Move `ClaudePet.app` to your Applications folder → double-click
3. No Python needed — bundled inside & **Apple-notarized** (no Gatekeeper warning)

First launch only asks for the **Keychain** ("Always Allow") and **`~/.claude`** ("Allow"). No Photos/Downloads/other folder prompts.

macOS 12+ (Apple Silicon · Intel via universal zip) · self-contained

<details>
<summary>🇰🇷 한국어</summary>

**설치**
1. 아래 **ClaudePet.zip** 다운로드 (**Intel Mac**은 **ClaudePet-universal.zip**) → 압축 해제
2. `ClaudePet.app`을 응용 프로그램 폴더로 이동 → 더블클릭
3. Python 불필요 — 앱에 내장 + **Apple 공증**(Gatekeeper 경고 없음)

첫 실행 시 **키체인**("항상 허용")과 **`~/.claude`**("허용")만 요청합니다. 사진/다운로드 등 폴더 팝업은 없습니다.

macOS 12+ (Apple Silicon · Intel은 universal zip) · 자체포함
</details>

<details>
<summary>🇯🇵 日本語</summary>

**インストール**
1. 下の **ClaudePet.zip** をダウンロード（**Intel Mac** は **ClaudePet-universal.zip**）→ 展開
2. `ClaudePet.app` をアプリケーションフォルダへ移動 → ダブルクリック
3. Python 不要 — アプリに同梱 + **Apple 公証済み**（Gatekeeper の警告なし）

初回起動時に **キーチェーン**（「常に許可」）と **`~/.claude`**（「許可」）だけを求めます。写真/ダウンロード等のフォルダダイアログは出ません。

macOS 12+（Apple Silicon · Intel は universal zip）· 自己完結
</details>

<details>
<summary>🇪🇸 Español</summary>

**Instalación**
1. Descarga **ClaudePet.zip** abajo (**Mac Intel**: descarga **ClaudePet-universal.zip**) → descomprime
2. Mueve `ClaudePet.app` a tu carpeta de Aplicaciones → doble clic
3. No necesitas Python — incluido y **certificado por Apple** (sin aviso de Gatekeeper)

En el primer arranque solo pide el **Llavero** ("Permitir siempre") y **`~/.claude`** ("Permitir"). Sin avisos de Fotos/Descargas ni otras carpetas.

macOS 12+ (Apple Silicon · Intel con el zip universal) · autocontenido
</details>

---

### 📝 변경 내역 / Changelog

**v0.17**
- **Claude Code가 없을 때 앱에서 설치·로그인 안내** — 이 펫은 Claude Code 사용량을 보여주는 도구라 데이터가 Claude Code에서 나옵니다. 이제 Claude Code가 없으면 빈 게이지 대신 **"Claude Code 미설치"** 안내가 뜨고, **우클릭 → "⬇︎ Claude Code 설치…"** 로 공식 설치 → 로그인까지 터미널에서 진행합니다. 설치돼 있는데 로그인만 필요하면 **"🔑 Claude Code 로그인…"**. 끝나면 재시작 없이 자동으로 사용량이 표시됩니다. (API 모드는 종전대로 Claude Code 없이 동작)
- Finder로 실행된 앱은 PATH가 최소라 `~/.local/bin/claude`(네이티브 설치 위치)를 못 찾던 것 수정.

**v0.16**
- **키체인 허용 프롬프트가 아예 안 뜨고 정확 모드가 안 되던 문제** 수정 — 원인은 토큰을 읽는 **순서**였습니다. 이 키체인 항목은 Claude Code가 `security` 도구로 만들기 때문에 그 도구는 어느 컴퓨터에서든 **프롬프트 없이** 읽을 수 있는 반면, 앱이 직접 읽는 방식은 키체인 암호를 요구받고 창을 띄우지 못하면 조용히 실패합니다. 그런데 v0.14부터 **프롬프트가 필요한 쪽을 먼저** 시도하고 있었습니다. 이제 프롬프트가 필요 없는 경로를 먼저 쓰고, 그게 막힌 환경에서만 프롬프트를 띄웁니다. 조용히 실패하는 상태(`-25308`/`-25315`)에서 폴백이 아예 없던 것도 함께 수정.
- **키체인 프롬프트에 응답하지 않으면 정확 모드가 영영 복구되지 않던 문제** 수정 — 이 앱은 메뉴바 없는 백그라운드 앱이라 macOS 키체인 창이 다른 창 뒤에 가려 못 보고 지나칠 수 있는데, 그러면 내부 잠금이 영구히 물려 재시도 로직 자체가 죽었습니다. 이제 기다리는 시간에 한도를 둬서, **나중에 "항상 허용"을 눌러도 그 응답을 주워가** 재시작 없이 정확 모드로 전환됩니다.
- 새로 설치/업데이트 후 **정확 모드로 복구되지 않고 계속 "로그 추정"으로만 뜨던 문제** 수정 — 키체인 토큰을 처음 몇 번 못 읽으면 그 실행 동안 영구 포기해 키체인 허용 프롬프트도 다시 안 뜨던 버그. 이제 아직 Claude Code 인증 전/키체인 허용 전이어도 주기적으로 재시도해, 나중에 인증하거나 "항상 허용"을 누르면 **재시작 없이 자동으로 정확 모드로 전환**됩니다.
- **로그 추정 모드에서 사용량 %를 입력해도 화면이 안 바뀌던 문제** 수정 — 값은 제대로 저장됐지만 다시 그리라는 요청이 없어, 펫이 쉬는 동안 최대 25초까지 옛 화면이 그대로 남아 있었습니다. 같은 원인으로 30초 주기 자동 갱신도 늦게 반영되던 것이 함께 고쳐집니다. 100을 넘는 값을 넣어 게이지가 100%에 박히던 것과, 설정창을 X로 닫았을 때 이전에 입력한 %가 다시 적용되던 것도 수정.
- **완전 삭제 기능 추가** — 우클릭 메뉴 → "완전 삭제…". 앱과 ClaudePet이 만든 설정·캐시를 한 번에 지웁니다. Claude Code 로그인과 `~/.claude` 데이터는 건드리지 않습니다.
- 문제 진단용: `CLAUDE_PET_DEBUG=1`로 실행하면 `~/claudepet_debug.log`에 토큰 읽기 경로가 기록됩니다.

**v0.15**
- 키체인 허용 프롬프트에 'Python' 대신 'ClaudePet'이 표시되도록 수정

**v0.14**
- 새 컴퓨터에서 정확 모드용 키체인 허용 프롬프트가 아예 안 뜨던 문제 수정 — 앱이 직접 네이티브 API로 키체인을 읽어 "ClaudePet이 키체인에 접근하려 합니다" 프롬프트가 확실히 뜨도록 개선 (첫 실행 시 한 번 "항상 허용"을 누르면 이후 자동)

**v0.13**
- 정확 모드 키체인 허용 프롬프트를 사용자가 응답할 때까지 기다리도록 개선 (타임아웃 제거)

**v0.12**
- 새로 설치했을 때 정확 모드용 키체인 허용 프롬프트가 응답하기도 전에 사라지던 문제 수정 (타임아웃 연장 + 승인 전까지 재시도)

**v0.11**
- 정확 모드(사용량) 인증서 검증 오류 수정 — 유니버설/Intel 빌드에서 정확 모드가 동작하지 않던 문제
- Apple Silicon 전용 DMG 추가 (Intel용 `ClaudePet-universal.dmg`와 별도)

**v0.10**
- Intel Mac 지원 (유니버설 빌드, `ClaudePet-universal.zip`)
- DMG 설치 파일 추가 (드래그 설치)

**v0.9**
- 최상위 모델 게이지 라벨을 서버 표기(예: Fable, Opus) 그대로 표시

**v0.8**
- 정확 모드에서 안 뜨던 **최상위 모델 게이지 복구** (모델별 주간 한도 표시 + 리셋 시각 보정)
- 크레딧 미설정 계정에 뜨던 **"크레딧 0%" 유령 행 제거**

**v0.7**
- **세션 사용률이 가끔 100%로 잘못 표시되던 문제** 수정
- 정상 사용 중에도 뜨던 **토큰 급증(▲급증) 오탐** 수정
