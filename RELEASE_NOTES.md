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

**v0.19**
- **로그 추정 모드의 사용량 계산 오차 수정** — 게이지에 표시되는 **%는 정확 모드(게이지 패널 맨 아랫줄에 "정확 모드"라고 표시될 때)에서는 달라지지 않습니다.** 서버가 계산한 값을 그대로 쓰기 때문입니다. 게이지 %가 바뀌는 것은 로그 추정 모드입니다.
  다만 **토큰 급증 감지와 그때의 펫 급증 반응은 정확 모드에서도 달라집니다.** 게이지 %와 달리 급증은 로그 추정 계산으로 판단하기 때문입니다. 화면에 보이는 모습은 모드마다 다릅니다 — 로그 추정 모드에서는 게이지 줄에 **`▲급증` 글자**가 붙고, 정확 모드에서는 글자 대신 **세션 게이지 막대가 빨갛게 변하면서 펫이 반응**합니다. API 모드에서는 급증 표시가 아예 없습니다. 세션이 리셋됐을 때 펫이 점프하는 인사는 **구독·API 모드 모두** 로그 추정 값으로 판단합니다. 그래서 아래 수정은 로그인해서 쓰는 분들에게도 급증 감지와 펫의 급증 반응을 통해 영향을 줍니다. 급증 판정은 최근 5분 사용량과 직전 25분 기준선을 함께 보는데 아래 수정은 이 둘을 모두 바꾸므로, 급증이 더 뜨는 쪽인지 덜 뜨는 쪽인지는 정해져 있지 않습니다.
  - **캐시 쓰기 비용을 TTL별로 반영** — 캐시 저장은 유지 시간에 따라 단가가 다른데(**5분 1.25배 / 1시간 2.0배**) 그동안 전부 1.25배로 계산했습니다. 1시간 캐시를 많이 쓰는 작업일수록 실제보다 적게 잡히던 것이 맞춰집니다. TTL 구분이 없는 예전 로그는 종전대로 전체를 1.25배로 계산합니다.
  - **스트리밍 중복 기록에서 가중 합계가 가장 큰 줄만 채택하도록 수정** — Claude Code는 답변 한 건을 여러 줄로 나눠 기록하고 각 줄에 그 시점까지의 누적 사용량이 들어갑니다. 종전에는 그중 **먼저 나온 줄**을 쓰고 나머지를 버렸는데, 먼저 나온 줄은 응답이 끝나기 전의 중간값이라 사용량이 실제보다 적게 잡혔습니다. 이제 같은 요청의 줄들 중 **가중 합계가 가장 큰 하나만** 채택합니다. 이번에 살펴본 기록에서는 응답 도중의 중간값이 서브에이전트(`subagents`) 기록 쪽에서 눈에 띄었고, 일반 대화 기록만 봤다면 이 차이를 놓칠 수 있었습니다.
  - **시간창 검사를 중복 제거보다 먼저 수행** — 집계 구간 밖의 오래된 줄이 먼저 처리되면 같은 요청의 구간 안 줄이 "중복"으로 버려져 사용량이 통째로 빠지던 문제를 고쳤습니다.
  - **롤링 7일 모드에서 주간 리셋 시각을 표시하지 않음** — 주간 리셋 요일을 지정하지 않으면 최근 7일 구간이 매 순간 밀리는 방식이라 "언제 재설정"이라는 시각 자체가 없습니다. 그동안 첫 기록 시각 + 7일을 리셋 시각처럼 보여줘 실제와 맞지 않았습니다. 이제 이 모드에서는 **주간 게이지와 모델별 게이지 모두 리셋 칸에 `-`** 로 표시됩니다. 리셋 시각을 보고 싶으면 설정에서 주간 리셋 요일을 지정하세요.
- ⚠️ 위 수정으로 추정 사용량 값이 달라지므로, **설정에서 %를 입력해 한도를 보정해 두셨다면 다시 보정해 주세요.** (보정은 추정값에서 한도를 역산하는 방식이라 계산이 바뀌면 이전 값이 어긋납니다.)
- 위 네 가지 수정은 **회귀 테스트로 확인했습니다** — 실제 사용 기록이 아니라 합성 데이터로 계산 결과를 검증해, 같은 문제가 다시 생기면 바로 드러나도록 했습니다.
- 앱 동작과는 별개로, 개발·릴리즈 작업 절차를 정리한 **내부 문서 규칙을 새로 정했습니다.**

**v0.18**
- **펫을 여러 개 두고 골라 쓰기** — 우클릭 → **"펫"** 또는 설정 창 맨 위의 **"펫"** 항목에서 원하는 펫으로 즉시(재시작 없이) 전환됩니다.
- **원하는 펫을 직접 추가** — `~/.claude_pet/pets/` 아래에 펫 폴더(`pet.json` + `spritesheet.webp`)를 넣으면 메뉴에 자동으로 나타납니다. 우클릭 → **"➕ 펫 추가…"** 를 누르면 그 폴더가 열리고 형식 안내(README)도 함께 만들어집니다.

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
