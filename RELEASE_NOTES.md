🐱 A desktop pet that watches your Claude token usage on macOS.

📖 Full README: [English](https://github.com/uygnoey/claude-pet/blob/main/README.md) · [한국어](https://github.com/uygnoey/claude-pet/blob/main/README.ko.md) · [日本語](https://github.com/uygnoey/claude-pet/blob/main/README.ja.md) · [Español](https://github.com/uygnoey/claude-pet/blob/main/README.es.md)

---

### 🇺🇸 English

**Install**
1. Download **ClaudePet.zip** below → unzip
2. Move `ClaudePet.app` to your Applications folder → double-click
3. No Python needed — bundled inside & **Apple-notarized** (no Gatekeeper warning)

First launch only asks for the **Keychain** ("Always Allow") and **`~/.claude`** ("Allow"). No Photos/Downloads/other folder prompts.

macOS 12+ (Apple Silicon) · self-contained

<details>
<summary>🇰🇷 한국어</summary>

**설치**
1. 아래 **ClaudePet.zip** 다운로드 → 압축 해제
2. `ClaudePet.app`을 응용 프로그램 폴더로 이동 → 더블클릭
3. Python 불필요 — 앱에 내장 + **Apple 공증**(Gatekeeper 경고 없음)

첫 실행 시 **키체인**("항상 허용")과 **`~/.claude`**("허용")만 요청합니다. 사진/다운로드 등 폴더 팝업은 없습니다.

macOS 12+ (Apple Silicon) · 자체포함
</details>

<details>
<summary>🇯🇵 日本語</summary>

**インストール**
1. 下の **ClaudePet.zip** をダウンロード → 展開
2. `ClaudePet.app` をアプリケーションフォルダへ移動 → ダブルクリック
3. Python 不要 — アプリに同梱 + **Apple 公証済み**（Gatekeeper の警告なし）

初回起動時に **キーチェーン**（「常に許可」）と **`~/.claude`**（「許可」）だけを求めます。写真/ダウンロード等のフォルダダイアログは出ません。

macOS 12+（Apple Silicon）· 自己完結
</details>

<details>
<summary>🇪🇸 Español</summary>

**Instalación**
1. Descarga **ClaudePet.zip** abajo → descomprime
2. Mueve `ClaudePet.app` a tu carpeta de Aplicaciones → doble clic
3. No necesitas Python — incluido y **certificado por Apple** (sin aviso de Gatekeeper)

En el primer arranque solo pide el **Llavero** ("Permitir siempre") y **`~/.claude`** ("Permitir"). Sin avisos de Fotos/Descargas ni otras carpetas.

macOS 12+ (Apple Silicon) · autocontenido
</details>

---

### 📝 변경 내역 / Changelog

**v0.9**
- 최상위 모델 게이지 라벨을 서버 표기(예: Fable, Opus) 그대로 표시

**v0.8**
- 정확 모드에서 안 뜨던 **최상위 모델 게이지 복구** (모델별 주간 한도 표시 + 리셋 시각 보정)
- 크레딧 미설정 계정에 뜨던 **"크레딧 0%" 유령 행 제거**

**v0.7**
- **세션 사용률이 가끔 100%로 잘못 표시되던 문제** 수정
- 정상 사용 중에도 뜨던 **토큰 급증(▲급증) 오탐** 수정
