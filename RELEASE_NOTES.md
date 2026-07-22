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
