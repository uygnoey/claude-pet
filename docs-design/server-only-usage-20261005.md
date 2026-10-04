# 서버 값만 쓰는 사용량 · 제공자별 설정 · 로그 기반 급증 감지(Claude·Codex)

작성 2026-10-05 · 조정자(Coordinator) 문서 · 브랜치 `claude/server-only-usage` (origin/dev 기준)

## 0. 사용자 결정 (2026-10-05, 대화에서 직접)

- "설정창에 claude만 잇는데 이거 codex도 동일하게!! 설정 가능하게"
  - 고른 항목: **제공자별 표시 켜기/끄기**, **Codex 도 API 비용 모드**, **필에 보일 게이지 고르기**,
    **우클릭 메뉴도 동일하게**.
- "추정 로그치 적는건 이제 없애자!! 기능도 없애고"
- 급증 알림: "**로그로 급증감지만 살려놔 ! 그럼 코덱스도 로그로 급증감지가 되어야겠지!!**"
- 세션 리셋 점프: **서버 값으로 유지**.
- 범위: **macOS + Windows 둘 다, dev 까지**. 릴리즈(버전·서명·배포)는 이 변경에 포함되지 않는다.

## 1. 없앨 것 — 로그 추정을 "표시하는 숫자"와 "설정"에서 완전히

로그는 **급증 감지에만** 쓴다. 사용량 숫자는 언제나 서버 값이고, 서버 값이 없으면 숫자를 보여 주지 않는다.

- 필의 `estimate` 구간(≈, 호박색 값, `_summary_label` 의 추정 전용 번역), `SUMMARY_APPROX`,
  `SUMMARY_COLORS["estimate"]`, auth_error 일 때 붙던 ` ⚠`.
- `compute_usage()` 의 게이지(session/weekly/opus 의 pct·limit·left·reset) — 반환에서 제거.
  `entries`, `last_activity`, `burn_*`, `spikes`, `now` 는 남긴다(아래 3절이 새 계약).
- 보정(% → 한도 역산), 절대 한도 입력, 고급 한도 창(`open_advanced_limits` 와 Windows
  `AdvancedLimitsDialog`), 한도 안내 문구, 주간 리셋 요일·시각, 모델 게이지 키워드 **설정 UI**.
  `prepare_settings_config` 의 한도/보정 부분, `_calibration_percent_error`, `GAUGE_LIMIT_KEYS`,
  `fmt_limit_m`, `LIMIT_M_DECIMALS`, `_weekly_window_start`, `WEEKDAYS_FULL`(다른 곳에서 안 쓰면).
- 관련 TR 키 전부(4개 언어): `s_model_kw, s_auto_detect, s_weekly_reset, s_rolling7, s_hour,
  s_calib*, s_limit_*, s_g_*, s_err_limit, s_err_calib*, s_err_hour`, 그리고 `--report` 만 쓰던 것.
- 설정 키 `session_limit, weekly_limit, opus_limit, model_keyword, weekly_reset_day,
  weekly_reset_hour` 는 더 이상 **읽지도 쓰지도 않는다**. 기존 `~/.claude_pet.json` 에 남아 있어도
  무시하고, 저장할 때 **지우지 않는다**(사용자 파일을 함부로 바꾸지 않는다 — 기존 "blank means keep" 정신).
  환경변수 `CLAUDE_PET_*_LIMIT`, `CLAUDE_PET_MODEL` 도 읽지 않는다.
- `s_mode_sub` 의 "(Claude Code logs)" 같은 로그 언급 문구는 "구독(로그인 계정)" 류로 바꾼다.
- 서버 값이 없을 때의 필: 토큰 거부(401/403) → `token_expired` 상태(로그 유무와 **무관하게**),
  로그인 없음 → 기존 온보딩/로그인 필요 상태, 아직 응답 전 → loading. "scanning" 은 서버 응답을
  기다리는 상태로만 남거나 없앤다. **어떤 경우에도 로그에서 낸 % 를 보여 주지 않는다.**
- 펫 기분(`current_mood`/`worst_pct`/`mood_for`): 서버 행이 없으면 idle(급증이면 failed).
- `--report`: 서버 값(Claude OAuth 행, Codex 행, API 모드면 비용)과 급증 상태만 출력.

## 2. 설정 창 — 제공자별 두 구역 (macOS NSPanel · Windows SettingsDialog 동일 배치)

위에서부터:

1. 펫, 언어 (지금과 같음)
2. **Claude Code** 구역
   - `[✓] 필에 표시` → 설정 키 `show_claude` (기본 true)
   - 데이터 소스 팝업: 구독(로그인 계정) / API 비용(Anthropic Admin API) → 기존 키 `mode` (`"sub"|"api"`) 유지
   - 보일 게이지 체크박스: 세션 · 주간 · 모델별 · 크레딧 → `claude_gauges` (기본 `["session","weekly","model","credit"]`)
   - Admin API 키(보안 입력) → 기존 `admin_key`, 월 예산($) → 기존 `api_budget`
3. **Codex** 구역 (같은 모양)
   - `[✓] 필에 표시` → `show_codex` (기본 true)
   - 데이터 소스: 구독(로그인 계정) / API 비용(OpenAI Admin API) → `codex_mode` (`"sub"|"api"`, 기본 `"sub"`)
   - 보일 게이지: 세션 · 주간 → `codex_gauges` (기본 `["session","weekly"]`). 계정에 없는 창은 원래대로 그냥 안 보인다.
   - OpenAI Admin API 키(보안) → `openai_admin_key`, 월 예산($) → `codex_budget`
4. 공통: 급증 알림 민감도(기존 `spike_mult`), 마우스 인사(기존 `greet`)
5. 저장 버튼, 버전 라벨

규칙:
- 내용 높이 ≤ 656 (1366×768 최소 화면, CLAUDE.md Danger zone). 고급 창은 없어진다.
- 검증 오류: 예산은 각각 0 이상 숫자(`s_err_budget` 재사용, Codex 쪽은 새 키 `s_err_codex_budget`).
  둘 다 꺼짐(`show_claude=false` 이고 `show_codex=false`)은 허용하되 필에 "표시할 제공자가 없어요" 상태.
  게이지를 하나도 고르지 않은 제공자는 표시 꺼짐과 같다.
- `SETTINGS_OWNED_KEYS` 를 새 집합으로: `pet, lang, mode, admin_key, api_budget, spike_mult, greet,
  show_claude, claude_gauges, show_codex, codex_mode, codex_gauges, openai_admin_key, codex_budget`.
  저장은 기존 트랜잭션(`plan_settings_save` → `apply_settings_plan` → `merge_config_updates`)을 그대로 쓴다.
  `merge_config_updates` 는 소유하지 않은 키를 건드리지 않는다(기존 계약 유지 → 옛 한도 키도 남는다).
- 새 TR 키(4개 언어 en/ko/ja/es 모두): 구역 제목, 표시 체크, 게이지 이름, Codex 데이터 소스 두 항목,
  OpenAI 키·예산 라벨, 오류, "표시할 제공자 없음" 상태, Codex 메뉴 항목. Codex 문구는 Claude 와 대칭으로
  ("Claude Code 또는 Codex" 원칙, 메모리 codex-equal-to-claude).

## 3. 급증 감지 — 로그 기반, Claude 와 Codex 모두

### 3.1 Claude (기존 파이프라인 유지)
`parse_usage_entries` / `_weigh_usage` / max-wins dedup / 시각 필터 순서 등 CLAUDE.md JSONL 불변식은 **그대로**.
`is_spike(burn, base, limit, base_pct)` 와 `SPIKE_BASE`, 2.5× 게이트, 활성 버킷 평균도 그대로.
바뀌는 것은 `limit` 의 출처뿐이다(3.3).
모델별 급증의 모델 키워드는 설정이 아니라 **서버 모델별 행의 라벨**에서(있으면) 정하고, 없으면 지금의 자동 감지
(`_detect_model_keyword`, PREMIUM_FAMILIES)를 쓴다.

### 3.2 Codex (새로)
- 파일: `$CODEX_HOME/sessions/**/*.jsonl`, 없으면 홈의 `.codex/sessions/**/*.jsonl` (`codex_auth_path` 와 같은 루트 규칙).
  Windows 도 같은 규칙(`%CODEX_HOME%` 또는 사용자 프로필의 `.codex`).
- 레코드: `{"type":"event_msg","timestamp":ISO,"payload":{"type":"token_count","info":{"last_token_usage":{...},"total_token_usage":{...}}}}`.
  `info` 가 null 인 것은 건너뛴다.
- 가중: `last_token_usage` 로 Claude 와 같은 비율 —
  `input_tokens − cached_input_tokens` ×1(음수면 0), `cached_input_tokens` ×0.1,
  `cache_write_input_tokens` ×1.25, `output_tokens` ×5. `reasoning_output_tokens` 는 **더하지 않는다**
  (output 에 포함된 값일 수 있어 이중 계산을 피한다 — 관측이지 보장이 아니므로 문서에 '보수적 선택'으로 적는다).
  noncache = total − cached×0.1. 숫자가 아닌 값·음수·nan/inf 는 그 행 전체를 버린다(`_weigh_usage` 와 같은 원칙).
- 중복 제거: 같은 파일 안에서 `total_token_usage.total_tokens` 가 같은 이벤트는 **한 번만**(Codex 는 같은
  token_count 를 두 번 쓰는 일이 있다). 시각 필터를 **먼저** 적용하고 그다음 중복 집합을 본다(JSONL 불변식 3과 같은 이유).
- 파일 mtime 은 프리필터일 뿐, 레코드 시각이 진짜 기준(불변식 6과 같다).
- 창: 직전 5분 burn, 그 앞 25분의 활성 5분 버킷 평균(Claude 와 같은 함수 재사용).
- 레인: `codex_session`(서버가 세션 창을 줄 때만), `codex_weekly`. `SPIKE_BASE` 대응 값은 session 2.0, weekly 0.5.
- 개인정보: 메시지 본문·경로·세션 id 를 로그/예외에 남기지 않는다(CLAUDE.md Privacy).

### 3.3 한도는 서버 값에서 자동 학습 (보정 UI 대체)
급증의 바닥값(`limit×base_pct×mult/100`)에 쓰는 `limit` 을 사람이 넣지 않고 서버 % 로부터 역산한다.

- 대상 레인마다(Claude session/weekly/model, Codex session/weekly): 서버가 준 사용률 `p`(0–100)와 리셋 시각 `R`,
  창 길이 `W`(Claude: session 5h, weekly 7d, model 7d / Codex: 서버의 `limit_window_seconds`)로
  창 시작 `R − W` 이후의 로그 가중 합계 `T`(**total**, noncache 아님 — 서버 %는 비용 전체 기준이라 추정)를 구해
  `limit = T / (p/100)`.
- **p < 5 이면 학습하지 않는다**(분모가 작아 폭주). T = 0 이어도 학습하지 않는다. 학습값은 메모리
  (`RUNTIME` 이 아닌 별도 dict)에만 두고, 직전 학습값과의 지수이동평균(α=0.3)으로 흔들림을 줄인다.
- 학습값이 없을 때는 **급증을 판정하지 않는다**(틀린 기본 한도로 오경보를 내느니 알림이 없는 쪽).
  기존 기본값 8M/60M/15M 은 지운다(CLAUDE.md: 공식값 아님).
- API 모드(Claude `mode=api` / Codex `codex_mode=api`)에서는 그 제공자의 급증을 판정하지 않는다(기존 규칙과 대칭).
- 표시: 급증이면 해당 제공자 줄의 세션 라벨에 ▲ + bad 색(기존 `spike_first` 경로를 제공자별로).
  펫 기분/오버레이/인사 억제/roam busy 는 어느 제공자든 급증이면 지금처럼.

## 4. 세션 리셋 점프 — 서버 값으로
직전 새로고침의 서버 세션 행 사용률 > 5 이고 이번 < 1 이면 점프. Claude OAuth 세션 행과 Codex
`codex_session` 행 각각 독립 판정, 하나라도 만족하면 한 번 점프. 로그 % 는 쓰지 않는다. API 모드에도 동작(서버 행이 있으면).

## 5. 필 표시
- `show_claude=false` → Claude 줄 없음. `show_codex=false` → Codex 줄 없음. 둘 다 없음 → 상태 키 하나.
- 게이지 선택: Claude 서버 행을 `_label_order` 로 분류 — session(0), weekly(1), model(2 와 5: 모델군 행), credit(9).
  선택하지 않은 분류의 행은 숨긴다. 순서·최대 개수 규칙(`SUMMARY_GAUGE_ROWS`)은 지금과 같다.
  Codex: `codex_session`↔session, `codex_weekly`↔weekly.
- 리셋 줄도 보이는 게이지에 대해서만.
- Codex API 모드: Claude 의 `cost` 구간과 같은 모양(오늘 $x · 이번 달 $y / $budget), 상태 키도 대칭
  (`codex_need_admin_key`, `codex_api_key_rejected`, `codex_api_unreachable`, loading).

## 6. Codex API 비용 (새로)
- `GET https://api.openai.com/v1/organization/costs?start_time=<unix>&bucket_width=1d&limit=31`,
  헤더 `Authorization: Bearer <openai_admin_key>`. 응답 `data[].results[].amount.value`(USD) 합.
  `has_more`/`next_page` 페이지 처리. 오늘 = 로컬 자정 이후, 이번 달 = 로컬 1일 이후(기존 Anthropic 함수와 같은 정의).
- 캐시·실패 재시도·상태 분류는 `fetch_api_cost` / `API_STATUS` / `api_error_kind` 와 대칭으로(401/403 → key rejected,
  네트워크 → unreachable). 키는 `~/.claude_pet.json` 에 평문(Anthropic Admin 키와 같은 처리 — 문서에 명시).
- 디버그 로그에는 상태 코드·예외 클래스만, 키 바이트는 절대 안 된다.

## 7. 우클릭 메뉴 (양 플랫폼)
- 온보딩 상태에서 Claude 와 대칭으로 **Codex 설치…**, **Codex 로그인…** 항목.
  - Codex 로그인 필요 판단: Codex 표시가 켜져 있고 `read_codex_auth` 가 토큰을 못 낼 때.
  - macOS: Terminal 에서 `npm install -g @openai/codex` / `codex login`(기존 `start_claude_install` 와 같은 방식).
    Windows: 기존 `_install_claude`/`_login_claude` 와 같은 새 PowerShell 콘솔.
- **Codex 토큰 자동 갱신은 넣지 않는다**: Codex CLI 가 스스로 갱신하고, 우리가 `auth.json` 을 쓰면 사용자의
  Codex 로그인을 망가뜨릴 수 있다(읽기 전용 원칙). 메뉴 순서가 바뀌면 `test_autostart`/`test_win_autostart`
  의 AST 고정과 Pets 서브메뉴 삽입 인덱스를 함께 맞춘다.

## 8. Windows 포트 패리티
`windows/claude_pet_win.py`·`win_core.py` 에 1–7 을 **똑같이**(메모리 windows-ui-parity: UI·동작 100% 동일).
코어 함수(파서·학습·필 구간·설정 계획)는 `claude_pet.py` 에 두고 Windows 는 그것을 호출한다(지금 구조 유지).

## 9. 문서
CLAUDE.md(추정·보정·Danger zone·필 표 절 갱신, Codex 로그 급증 추가, 개인정보에 Codex 로그 읽기 명시),
README 4개 언어, `docs/llms*.txt`, `docs/index.html`(FAQ·데모의 추정 토글·"Codex 는 로컬 로그를 쓰지 않아요"),
`docs/privacy.html`(앱 항목: Codex 세션 로그를 급증 감지용으로 이 컴퓨터에서만 읽음, 숫자만). RELEASE_NOTES 는
릴리즈 때 쓴다(이번 범위 아님). **사이트 문구 변경은 dev 에만**, main 반영은 릴리즈 때.

## 10. 역할과 순서 (AGENTS.md)
- 조정자: 이 문서를 쓴 세션. 역할 배정·머지 판단.
- 검증자(Verifier): 1–8 의 게이팅 테스트를 **먼저** 작성·갱신(옛 추정 테스트는 삭제 또는 새 계약으로 재작성),
  미구현 코드에 대해 **빨강을 관측·기록**하고 푸시. 프로덕션 파일은 건드리지 않는다.
- 개발자(Developer): 프로덕션 파일(claude_pet.py, windows/*.py, 문서)만. 게이팅 테스트의 단언·픽스처는 건드리지 않는다.
- 검토자(Reviewer): 둘 다 아닌 에이전트. 범위·정확성·패리티 검토 후 서명.
- CI(macOS + Windows) 초록 → dev 머지. 커밋 트레일러 `Developer:` / `Verifier:` 서로 다르게.
