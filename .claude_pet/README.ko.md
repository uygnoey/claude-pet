# `.claude_pet/pets` — 예시 펫 세트

[English](README.md) · **한국어** · [日本語](README.ja.md) · [Español](README.es.md)

**claude-pet(v0.18)** 에서 바로 쓸 수 있는 완성된 커스텀 펫 모음입니다.
현재 4종이 들어 있습니다: **Dog · Fox · Scorpion · Elephant**.

> ⚠️ **중요 — 앱은 이 폴더를 직접 읽지 않습니다.**
> claude-pet은 커스텀 펫을 홈 디렉토리 `~/.claude_pet/pets/` 에서 로드합니다.
> 리포지토리 안의 이 `.claude_pet/pets/` 는 그 홈 폴더로 **복사해서 쓰는 배포용 예시**일 뿐이며,
> 앱이 이 경로를 자동으로 복사·참조하지 않습니다.
>
> 설정 파일 `~/.claude_pet.json`(폴더가 아닌 JSON 파일)과도 다른 경로이니 혼동하지 마세요.

---

## 바로 써보기 (설치)

```bash
mkdir -p ~/.claude_pet/pets
cp -R dog fox scorpion elephant ~/.claude_pet/pets/
```

복사 후 메뉴바 아이콘을 **우클릭 → 펫 선택**에서 새 펫이 나타납니다.
메뉴는 열 때마다 폴더를 다시 스캔하므로 **앱 재시작이 필요 없습니다**(메뉴만 다시 열면 됨).

앱의 "펫 폴더 열기" 메뉴를 누르면 `~/.claude_pet/pets/` 가 없을 경우 자동 생성되고
사용법 안내(`README.txt`)와 함께 Finder로 열립니다.

---

## 폴더 구조

```
<펫이름>/
├── pet.json          # 메타데이터 + 스프라이트 규약 (필수)
├── spritesheet.webp  # 스프라이트시트 (필수, 실제로 로드되는 유일한 이미지)
└── preview.png       # 미리보기 이미지 (선택, 런타임 미사용 — 문서/갤러리용)
```

- **펫의 내부 ID는 폴더 이름**으로 정해집니다. `pet.json` 의 `id` 값이 아니라 폴더명이 기준입니다.
- 런타임에 실제로 읽히는 파일은 `pet.json` 과 `spritesheet.webp` **두 개뿐**입니다.
  `preview.png` 는 코드에서 참조하지 않습니다(리포지토리 미리보기용).

---

## `pet.json` 스키마

```json
{
  "id": "dog",
  "displayName": "Dog",
  "description": "친구 같은 강아지 …",
  "spriteVersionNumber": 2,
  "spritesheetPath": "spritesheet.webp"
}
```

| 필드 | 필수 | 의미 |
|---|---|---|
| `id` | 권장 | 식별용. 단, 앱은 실제로 **폴더 이름**을 ID로 사용합니다. |
| `displayName` | 권장 | 우클릭 메뉴에 표시될 이름. 없으면 폴더명이 표시됩니다. |
| `description` | 선택 | 문서용 설명. 런타임에는 사용되지 않습니다. |
| `spriteVersionNumber` | 권장 | 스프라이트시트 격자 규약 버전. 현재 **2** 만 정의돼 있으며, 알 수 없는 값은 v2로 폴백합니다. |
| `spritesheetPath` | 선택 | 시트 파일 상대 경로. 기본값 `"spritesheet.webp"`. |

---

## 스프라이트시트 규약 (spriteVersionNumber 2)

스프라이트시트는 **고정 8열 × 11행 격자**로 슬라이스됩니다.

- 셀 크기 = `시트 너비 / 8` × `시트 높이 / 11`
- 예시 펫은 모두 **1536 × 2288** → 셀 **192 × 208**
- 각 애니메이션 상태는 지정된 **행(row)** 의 0번 칸부터 왼쪽 → 오른쪽으로 정해진 프레임 수만큼 채웁니다.

| 행 (row) | 상태 | 프레임 수 |
|---|---|---|
| 0 | `idle` | 7 |
| 1 | `running-right` | 8 |
| 2 | `running-left` | 8 |
| 3 | `waving` | 4 |
| 4 | `jumping` | 5 |
| 5 | `failed` | 8 |
| 6 | `waiting` | 6 |
| 7 | `running` | 6 |
| 8 | `review` | 6 |
| 9–10 | (예약, 미사용) | — |

- **`idle` 상태는 필수**입니다. `idle` 프레임을 얻지 못하면 그 펫은 무효로 처리됩니다.
- 각 셀의 여백/배경은 투명(알파)으로 두는 것을 권장합니다.

### 애니메이션 타이밍

고정 fps 대신, 상태별로 **프레임당 지속시간(ms)** 이 정해져 있습니다(대략적 값):

| 상태 | 프레임당 지속 | 재생 |
|---|---|---|
| `idle` | 430ms | 반복 (약 25초 간격 휴지) |
| `waiting` | 340ms | 반복 |
| `review` | 360ms | 반복 |
| `failed` | 260ms | 반복 |
| `waving` | 200ms | 1회 재생 |
| `jumping` | 150ms | 1회 재생 |
| `running` / `running-left` / `running-right` | 90ms | 반복 (≈ 11fps) |

명시되지 않은 상태는 기본값 400ms·반복이 적용됩니다.

---

## 나만의 펫 만들기

1. `~/.claude_pet/pets/<이름>/` 폴더를 만듭니다.
2. 위 8×11 격자 규약에 맞춰 `spritesheet.webp` 를 배치합니다(최소 `idle` 행 필요).
3. `pet.json` 을 작성합니다(`spriteVersionNumber: 2`).
4. 우클릭 메뉴를 다시 열면 새 펫이 나타납니다.

> 참고: 구형 포맷도 지원됩니다 — `pet.json` 없이 `idle/`, `running/` 등 **상태별 하위 폴더 안의 PNG
> 시퀀스**로도 펫을 만들 수 있습니다(앱 내장 고양이가 이 방식). 신규 펫은 위 시트 방식을 권장합니다.

---

## 폴더가 없을 때

`~/.claude_pet/pets/` 가 없어도 앱은 정상 동작하며, **기본값은 앱에 내장된 고양이(Cat 🐱)** 입니다.
저장해 둔 펫이 사라지거나 손상되면 자동으로 이 내장 펫으로 폴백합니다.

---

> 🛍️ **곧 공개:** 클릭 한 번으로 새 펫을 둘러보고 추가하는 펫 마켓플레이스가 준비 중입니다.
