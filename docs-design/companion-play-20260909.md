# 동행 놀이(companion play): 마우스 따라다니기 에피소드 + 모니터 사이 점프 (2026-09-09)

> 사용자 원문: *"랜덤하게 마우스를 몇 초동안(10초 이상) 따라다니는 기능도 넣어주고 모니터 간 스스로
> 건너 다니는것도 해줘 점프해서 이동하면 괜찮을듯"*.
>
> 상태: **구현됨 (source freeze, 독립 검사 진행 중, 미커밋).** Verifier 의 baseline RED(2026-09-09T08:24:49Z 기록)와
> Coordinator GO 뒤에 production 을 고쳤다. 최종 `claude_pet.py` SHA256
> `150f57757483436e9aa74b85a4a517b3d490941a059a0dc5f9a2288282752351`. 이 문서는 Developer 의 설계·구현 설명이고, 이 변경의 승인·검증 결과의 기준은
> `docs-design/companion-play-verification-20260909.md`(Verifier) 와 `docs-design/companion-play-review-20260909.md`(Reviewer) 다.

## 역할과 소유 파일

| 역할 | 누구 | 소유 |
|---|---|---|
| Developer | Claude (session 55c3dee4-727f-4a94-b960-66540b129014) | `claude_pet.py`(production), `README.md`/`README.ko.md`/`README.ja.md`/`README.es.md`, `docs-design/quiet-companion.md`(정합), 이 문서(신규 deliverable — 착수 시 부재 확인) |
| Coordinator | Codex `/root` | 역할 배정, RED/GO, commit GO |
| Verifier | Mendel `/root/verifier` | 신규 `tests/test_companion_play.py`, 이전 대상 `tests/test_companion_motion.py`·`tests/test_free_roaming.py`, 소스 핀 `tests/test_manual_update_transaction.py`·`tests/test_upload_artifact_gate.py`(최종 리뷰 뒤), GUI 입력(CGEvent), 검증 기록과 QA 산출물(`companion-play-live-20260909.jsonl`/`.png` 등) |
| Reviewer | Curie `/root/reviewer` | 리뷰 기록 |

baseline: HEAD `dba49ef`, `claude_pet.py` SHA256 `f3810b141423ec3a9343b4b6ef76ebe1e29b7658ba9a07be13db2146f922150a`, tracked clean.
착수 시 다른 터미널의 release/install 진행 없음(서명·공증 프로세스 없음, 태그 최신 v0.21, `APP_VERSION` 0.21).
이번은 구현·실제 검증 협업이며 version/release/sign/push/install 은 범위 밖. 과거 QA 기록·사용자 untracked·
`frames/`·`build/`·`release/`·설치 앱 무접촉. **새 production 파일은 필요 없다** — 점프 효과는 기존 `jumping`
스프라이트 + 창 alpha 로 만든다.

## 사양 (사용자 요구를 규칙으로)

1. **따라다니기 에피소드(follow).** 가끔, 랜덤하게 시작해 **10~20 초**(10 초 미만 없음) 동안 **움직이는 커서의 최신
   좌표**를 쫓는다 — 기존 구경(approach)처럼 출발 때 목표를 고정하지 않는다. 커서에서 `approach_stop + radius`
   만큼 여백을 두고 그보다 가까우면 서서 바라본다(`review`), 멀면 천천히(`follow_speed`, 걷기보다 느림) 다가간다.
   도착해도 에피소드가 끝날 때까지 따라가기/바라보기를 반복한다. 마감(`_follow_until`)은 시작 때 고정된다. 끝나면 구경
   도착과 같은 `look`(요약 표시) 뒤 **그 자리에서** 쉰다. 길이 상한·쿨다운(실제 시작 뒤 420 s)·시작 확률로 과도하지 않게.
   첫 정상 휴식부터 자격이 있다(초기 제외 기간 없음).
2. **모니터 사이 점프(jump).** 산책(wander) 계획 때 다른 화면이 있으면 가끔 그 화면의 **안전한 착지 후보**를 랜덤으로
   골라 건너간다. 건너감은 **출발 효과(제자리 `jumping` 스프라이트 + 창이 서서히 사라짐, `jump_prep_s`) → 전송 직전
   재검사 → 한 step 에 원자적 위치 교체 → 착지 효과(anim 없음, 창이 서서히 나타남, `jump_land_s`) → 산책 멈춤 → 그
   자리에서 휴식**이다. 단순 순간이동을 점프라 부르지 않는다. **한 화면 안에서는 점프하지 않는다.** 점프를 시작한 뒤
   대상 화면 ID 와 착지점은 고정이다.
3. **화면 레코드와 좌표계.** 어댑터는 매 tick **현재 화면을 포함한 모든 화면**을 `RoamScreen(id, frame, bounds)` 로
   준다: `id` 는 안정 식별자(`NSScreen` 의 `NSScreenNumber`), `frame` 은 실제 화면 rect(x0,y0,x1,y1; 커서 소속 판정용),
   `bounds` 는 그 화면 `visibleFrame` 안에 논리 full 창이 통째로 들어가는 **중심 허용 rect**(착지·pos 제약용). 두 rect
   는 분리해 쓴다 — safe rect 를 radius 로 넓혀 frame 을 추정하지 않는다(화면 사이 빈틈의 커서가 이웃 화면으로 오인되는
   반례). 크기가 다른 화면·음수 origin·위아래 배치는 전역 좌표라 자연히 처리되고, 창보다 작은 화면(bounds 뒤집힘)은
   어댑터가 빼며 모델도 `step` 입구에서 다시 걸러 낸다(계획·착지 후보·화면 해석 전). 전체 화면 union 의 빈 공간은 목적지도 정지 자리도 아니다(후보는 항상 어떤 화면의
   bounds 안).
4. **현재 화면은 모델이 확정한다.** `Roamer.screen` = 현재 화면 ID. 해석은 pos 로 한다(pos 를 `frame` 에 담는 화면 →
   없으면 bounds 거리가 가장 가까운 화면). 처음 `screens` 를 받을 때, `set_home`/`release`(수동 드래그·resync) 뒤, 그리고
   현재 ID 가 목록에서 사라졌을 때(연결 해제) 다시 해석한다. 착지 뒤 현재 화면 = 착지 화면 ID 이고 **다음 R8 은 그 화면의
   bounds** 를 쓴다 — 어댑터의 `win.screen()` 이 바로 바뀌는지에 의존하지 않는다. 자동 점프는 수동 `home` 을 착지 화면으로
   클램프하거나 바꾸지 않는다(home 은 원래 화면 좌표로 남고 `away=True`). 화면 연결 해제·크기 변경 시 최신 id/frame/bounds
   로 재검증한다.
5. **사용자 우선(기존 R7 그대로).** hover·드래그·메뉴·설정 창·spike·Reduce Motion·off·틱 공백은 follow/jump 어느 단계에서든
   **그 자리 즉시 정지**(`settled=False`). 출발 효과 중 정지하면 원래 화면에 남고, 전송 뒤면 착지 화면에 남는다 — 중간 상태는
   없다. **커서 안전 문구(정정):** 커서는 언제든 펫 위로 들어올 수 있으므로 '거리 항상 보장'은 불가능하다. 보장하는 것은 (a) 펫이
   **자기 이동으로** 커서의 배제 영역(`radius + cursor_margin_px`, 목표 기준 `approach_stop + radius`)에 들어가지 않는다,
   (b) 커서가 경로/자리에 침범하면 **그 tick 은 움직이지 않는다**(정지·바라보기), 두 가지다.
6. **follow 중 커서가 다른 모니터로 가면.** 커서 소속 화면 `cs` 는 `frame` 으로 판정한다. `cs == screen` 이면 보통 follow.
   `cs` 가 없으면(화면 사이 빈틈) 그 tick 은 안전 대기(서서 바라봄)하고 체류 시계를 푼다. `cs` 가 다른 화면이면 현재 bounds 로
   클램프한 자리까지만 가서 가장자리에서 바라보며 **대상 화면 ID 에 묶인** 체류 시계를 잰다(B→C 로 바뀌면 3 초 리셋). 체류
   `follow_cross_s` 이상 ∧ 남은 에피소드 ≥ `follow_min_left_s` ∧ 에피소드 점프 횟수 < `follow_max_jumps`(1) ∧ 점프 쿨다운
   경과 ∧ `jump_enabled` 이면 **같은 jump 경로**로 그 화면의 커서 여백 자리(bounds 클램프, 배제 영역 밖)로 건너가 follow 를
   이어 간다. 에피소드당 1 회·쿨다운 소비이므로 빠른 왕복이 없다.
7. **마감과 취소.** follow 마감은 jump 의 출발/착지 효과 중에도 검사한다: 전송 **전** 만료 → 점프 취소, 원래 화면에서 자연
   완료(`look`); 전송 **후** 만료 → 새 화면에서 follow 를 재개하지 않고 자연 완료. follow 중 `cursor=None` 은 명시적 취소
   (`_stop`, `settled=False`). 전송 직전 재검사: 대상 화면 ID 가 아직 있고 착지점이 그 화면의 **최신** bounds 안이며, 최신 커서가
   착지점의 배제 영역 밖이어야 한다 — 하나라도 어긋나면 점프 취소, 현재 자리 안전 정지(침범 금지). 어댑터는 정상 완료와
   모든 취소 tick 에 창 alpha 를 1 로 복원한다.
8. **표시.** 걷기·점프·follow 동안 게이지는 접힌다(D1). follow 완료는 구경 도착처럼 요약 래치(D2), 자연 완료 뒤 새 위치에서
   평소 선택 복원(D3). 산책 점프 착지는 조용한 멈춤 뒤 복원. 자동 위치는 저장하지 않고 수동 home/config 정책은 그대로.
9. **RNG·이벤트.** 새 행동 선택(follow 확률·길이, 점프 확률·화면·착지)의 난수는 rest 가 끝나는 계획 step 과 점프/에피소드
   시작 때만 뽑는다 — follow/jump 진행 중 매 tick 난수 없음(기존 rest 재추첨 `_arm` 은 그대로라 hold 중엔 tick 마다
   `uniform(rest_min_s, rest_max_s)` 를 소비할 수 있다). override 는 값이
   바뀔 때만 갱신(기존 `roam_anim` 규칙) — 이벤트 폭주 없음. 제품 스케줄링은 기존 fixture 를 위해 제한하지 않는다; Verifier 가
   `follow_p=0` / `jump_enabled=False` 로 기존 case 를 격리한다.

## 최종 API 계약 (순수 상태기계, `claude_pet.py`)

`Roamer` 는 여전히 AppKit 을 모른다(`pure_api` 규칙: math/random/namedtuple 과 자기 정의만).

```python
ROAM_DEFAULTS 추가:
  "follow_p": 0.35,            # 자격이 될 때 follow 를 고를 확률 (rest 끝 계획 step 에서 uniform(0,1) 1회)
  "follow_min_s": 10.0, "follow_max_s": 20.0,   # 에피소드 길이 rng.uniform(min, max) — 10 초 미만 없음
  "follow_cooldown_s": 420.0,  # follow 최소 간격 (실제 시작 뒤). 초기 _follow_ok_at = now
  "follow_speed": 45.0,        # pt/s, 걷기(55)보다 느리게
  "follow_slack_px": 20.0,     # 여백(approach_stop + radius) 안쪽 이 폭에서는 서서 바라본다 (떨림 방지)
  "follow_turn_px": 8.0,       # 좌우 방향 전환 히스테리시스
  "follow_cross_s": 3.0,       # 커서가 같은 다른 화면에 이만큼 머물러야 건너간다 (대상 ID 에 묶임)
  "follow_min_left_s": 5.0,    # 남은 에피소드가 이보다 짧으면 건너가지 않는다
  "follow_max_jumps": 1,       # 에피소드당 점프 상한 (왕복 금지)
  "jump_enabled": True,
  "jump_p": 0.5,               # 다른 화면이 있고 쿨다운이 지났을 때 산책이 점프가 될 확률
  "jump_cooldown_s": 600.0,    # 점프 최소 간격 (실제 시작 뒤). 초기 _jump_ok_at = now
  "jump_tries": 6,             # 착지 후보 재추첨 상한
  "jump_prep_s": 0.75,         # 출발 효과: jumping 스프라이트 한 바퀴(5 프레임 × 150 ms) + fade-out
  "jump_land_s": 0.5,          # 착지 효과: anim 없음 + fade-in

RoamScreen = namedtuple("RoamScreen", "id frame bounds")
  # id     = 안정 식별자 (어댑터: NSScreenNumber; 시험: 임의 해시 가능 값)
  # frame  = (x0, y0, x1, y1) 실제 화면 rect — 커서 소속 판정
  # bounds = (x0, y0, x1, y1) 논리 full 창 중심 허용 rect — 착지·pos 제약. 뒤집힌 것은 무시
RoamOut = namedtuple("RoamOut", "pos anim moved away phase effect", defaults=(None,))
  # effect = None | "takeoff" | "landing" — 어댑터가 창 alpha 로 그린다. 5 인자 생성 호환
phase = "rest" | "out" | "look" | "follow" | "jump"
kind  = None | "approach" | "wander" | "follow"

Roamer.screen   # 현재 화면 ID (screens 를 받기 전엔 None)
Roamer.step(now, cursor, bounds, *, enabled=True, dragging=False, blocked=False,
            busy=False, activity=False, screens=())
  # screens = RoamScreen 목록(현재 화면 포함). 비어 있으면 bounds 단일 화면(기존 호출과 동일, 점프 없음).
  # 비어 있지 않으면 현재 bounds = screens[screen].bounds (bounds 인자는 호환용으로만 받고 무시).
```

### 전이

- **rest → 계획(`_plan`)**, 우선순위: (1) follow 자격 = 활동 중 ∧ 커서 있음 ∧ `now ≥ _follow_ok_at` → `u=uniform(0,1)`;
  `u < follow_p` 면 `dur=uniform(follow_min_s, follow_max_s)`, `_follow_until = now + dur`(고정), `_follow_ok_at = now +
  follow_cooldown_s`, `_follow_jumps = 0`, phase `follow`, kind `follow`. (2) 아니면 기존 approach. (3) 아니면 wander:
  점프 자격 = `jump_enabled` ∧ 다른 유효 화면 ≥ 1 ∧ `now ≥ _jump_ok_at` → `u=uniform(0,1)`; `u < jump_p` 면 다른 화면 중
  `i=int(uniform(0, n))`(상한 클램프) 와 착지 후보(시도당 uniform 2 회, `jump_tries` 상한: 그 화면 bounds 안, 커서와
  `approach_stop + radius` 이상) → phase `jump`(단계 `off`), kind `wander`, `_jump_next="look"`, `_jump_screen=id`,
  `_jump_to=착지`, `_jump_ok_at = now + jump_cooldown_s`, `_wander_ok_at` 도 갱신. 착지 후보가 없으면 같은 화면 산책(기존
  `_plan_wander`)으로 넘어간다. (4) 없으면 휴식 재추첨. 자격이 안 되면 그 선택의 난수(follow 의 `uniform(0, 1)`, 점프의
  `uniform(0, 1)`·화면 index·착지)는 뽑지 않는다: `follow_p=0` 이면 follow 선택 난수가 없고 `jump_enabled=False`(또는 다른
  화면 없음)면 점프 선택 난수가 없다. `jump_p=0` 은 자격이 있으면 `uniform(0, 1)` 을 한 번 소비하고 거절된다. 기존 휴식
  재추첨(`_arm`)의 난수는 그대로다.
- **follow (매 step)**: `now ≥ _follow_until` → `_watch(now)` = `look`(anim `review`, `look_s`) → 만료 시 rest
  `settled=True`. `cursor is None` → `_stop(now)`(취소, `settled=False`). `cs` = 커서를 `frame` 에 담는 화면 ID(없으면 None).
  `cs is None` → 그 tick 정지·`review`·체류 시계 해제. `cs != screen` → 체류 시계(대상 ID 바뀌면 리셋); 사양 6 의 조건이 다
  맞으면 `screens[cs].bounds` 로 클램프한 커서 여백 자리로 jump 시작(`_jump_next="follow"`), 아니면 현재 bounds 로 클램프한
  목표. 그 외: `stop = approach_stop + radius`, `d = |cursor − pos|`, 목표 `= cursor + (pos − cursor)/d · stop` 을 현재
  bounds 로 클램프. `d ≤ stop + follow_slack_px` 면 서서 `review`. 아니면 `follow_speed · dt` 만큼 목표로; anim 은 목표 x 차이가
  `follow_turn_px` 를 넘을 때만 `running-left/right` 전환. 커서가 [pos, 목표] 선분에 `radius + cursor_margin_px` 안이면 그
  step 은 서서 바라본다(중단 아님).
- **jump**: 단계 `off`(anim `jumping`, effect `takeoff`, `_jump_at = now + jump_prep_s`, pos 불변). follow 점프면 매 step 마감
  검사(만료 → 취소 후 `_watch`). `_jump_at` 에 재검사(대상 ID 존재 ∧ 착지가 최신 bounds 안 ∧ 커서가 착지의 배제 영역 밖) →
  통과면 `pos = 착지`, `screen = 대상 ID`, 단계 `land`(moved=True, effect `landing`, anim None, `_land_until = now +
  jump_land_s`); 실패면 `_stop(now)`(원래 자리). `_land_until` 뒤: `_jump_next == "follow"` 이고 마감 전이면 phase `follow`
  (`_follow_jumps += 1`), 마감 지났으면 `_watch`(자연 완료), wander 면 `_watch`(멈춤 `wander_pause_s`) → rest `settled=True`.
- **R7/R8 은 모든 phase 에 그대로**: hold·gap·현재 bounds 뒤집힘 → `_stop(now)`; 현재 ID 가 목록에 없으면 pos 로 재해석;
  pos 가 현재 bounds 밖 → 클램프 + 정지(기존 R8, home 클램프도 기존대로 — 화면 구성 변경 때만).

### RoamDisplay

- D1: phase ∈ {`out`, `jump`, `follow`} → 둘 다 끈다. `mode()` 도 이 셋에서 `folded`.
- D2: phase `look` ∧ kind ∈ {`approach`, `follow`} → `summary=True`.
- D0/D3/D4 그대로.

### 어댑터 (`run_gui`)

- `roam_screens()`: `NSScreen.screens()` 마다 `RoamScreen(id=NSScreenNumber, frame=frame(), bounds=visibleFrame 기준 중심
  rect)`; 뒤집힌 bounds 는 제외 → `step(..., screens=...)`. `bounds` 인자는 기존 `roam_bounds()` 를 그대로 넘긴다(호환).
- `roam_tick`: `out.effect` 가 `takeoff` 면 `win.setAlphaValue_` 를 1 → 0.15(어댑터 시계, `jump_prep_s` 기준), `landing` 이면
  0.15 → 1(`jump_land_s`), effect 가 None 이고 마지막 적용값이 1 이 아니면 1.0 복원(정상 완료·모든 취소 tick) — 값이 바뀔 때만
  호출. 위치 교체는 기존 `place_window_center`. 창 없는 시험에서 alpha 호출은 effect 가 있었던 뒤에만 일어난다.
- `roam_resync` 는 클램프 기준을 `roam_current_bounds()`(모델이 확정한 현재 화면의 bounds; 점프로 다른 화면에 있으면 그 화면)로
  바꿨고, 나머지 동작(나가 있으면 `release`, 집이면 `set_home`, 창 재배치)은 그대로다. `roam_release`·수동 드래그 저장(`x`/`y` 는
  드래그 끝에만)·crop/anchor·Reduce Motion 메뉴·`RUNTIME["roam"]` 단일 토글: 변경 없음.
  follow/jump 는 '화면 돌아다니기' 토글에 함께 묶인다(새 설정 키·메뉴 없음). 수동 드래그/resync 뒤 모델은 새 pos 로 화면을
  다시 고른다(`set_home`/`release` 가 `screen=None` 으로 되돌림).

### 테스트 환경에 대해 (정직한 구분)

현재 OS 에는 화면이 하나(id 18, 화면 공유 가상 1353×761)뿐이라 **실제 다중 모니터 점프는 이 기기에서 측정할 수 없다.**
순수 상태기계는 `screens` 인자로 다중 화면을 완전히 합성할 수 있고, 어댑터는 `NSScreen.screens` 를 두 개 이상 돌려주는
stub 로 `roam_screens`/`roam_tick` 을 창 없는 시험에서 확인할 수 있다. 실제 창의 다중 화면 착지는 Verifier 가 합성 native 로
기록하되 실측이 아님을 명시한다. follow 는 단일 화면에서 실측 가능하다(CGEvent 커서 이동은 Verifier 소유).

## Verifier 에게 — 갈라야 할 경쟁 구현 (산문 제안)

1. `follow_p=0`/`jump_enabled=False` 면 난수 호출 수와 계획 결과가 기존과 같다(기존 case 격리).
2. `MinimumRng` 로 follow 가 시작되면 길이가 정확히 10 초이고, 10 초 전엔 `look` 이 되지 않는다; 마감은 시작 때 고정.
3. 커서를 매 step 옮겨도 최신 좌표를 쫓고, 자기 이동으로 배제 영역에 들어가지 않으며(목표 고정 구현은 갈라짐), 커서가 경로에
   들면 그 tick 은 움직이지 않는다. 속도는 `follow_speed·dt` 를 넘지 않는다.
4. follow 중 hold/gap/off → 그 자리 정지 `settled=False`; `cursor=None` → 취소 `settled=False`; D4 래치 규칙 그대로.
5. 완료 → `look`(kind follow, anim review) → 요약 래치 → `look_s` 뒤 rest `settled=True`, 위치 불변(귀가 없음).
6. 커서가 다른 화면(frame 기준): `follow_cross_s` 전엔 점프 없음(가장자리에서 바라봄); B→C 전환 시 리셋; 빈틈 커서는 대기 +
   리셋; 조건 충족 시 정확히 한 번, 되돌아가도 두 번째 점프 없음; 남은 시간 < 5 s 면 없음.
7. wander 점프: 다른 화면이 없으면 절대 없음; 있으면 `off` 동안 pos 불변·anim `jumping`·effect `takeoff`, `jump_prep_s` 뒤 한
   step 에 `moved=True`·pos 가 고른 화면 bounds 안·`screen` 이 그 ID·이어 `landing`·멈춤·rest `settled=True`. `off` 중 hold →
   원래 자리 정지; 전송 직전 대상 ID 소실/bounds 밖/커서 침범 → 취소·현재 자리 정지; 음수 origin·위아래·다른 크기 rect.
8. 착지 뒤 다음 step 의 R8 이 착지 화면 bounds 를 쓰고(원래 화면 bounds 로 되돌리지 않음), home 은 바뀌지 않는다;
   `set_home`/`release` 뒤 새 pos 로 화면을 다시 고른다; 현재 ID 가 사라지면 pos 로 재해석 + 클램프.
9. 어댑터: `roam_screens` 의 id/frame/bounds 분리와 뒤집힌 rect 제외; alpha 가 완료·중단 뒤 1.0; `win.screen()` 변화에
   의존하지 않음(stub 이 옛 화면을 돌려줘도 착지 화면 bounds 사용).
10. 회귀: free-roaming·companion 기존 게이트 전부 그대로.

## 구현 결과 (Developer)

- `claude_pet.py` SHA256 `150f57757483436e9aa74b85a4a517b3d490941a059a0dc5f9a2288282752351` (baseline `f3810b14…` 위의
  변경, 새 파일 없음). 순수: `ROAM_DEFAULTS`(follow_*/jump_*), `RoamOut`(effect, 5인자 호환), `RoamScreen`(신규),
  `_roam_inside`/`_roam_valid_rect`/`_roam_rect_dist`/`_roam_screen_at`/`_roam_find_screen`, `Roamer`(step 이 뒤집힌 bounds 화면을 먼저 걸러 냄, screen 속성, `_plan` 의 follow→approach→
  wander[jump] 순서, `_step_follow`/`_step_jump`/`_start_jump`/`_plan_landing`/`_standoff`/`_resolve_screen`/`_clamp_home`,
  `step(..., screens=())`, `set_home`/`release` 가 화면 재해석), `RoamDisplay`(out·jump·follow 접기, look kind∈{approach,follow}
  요약). 어댑터: `roam_screen_bounds`/`roam_screen_id`/`roam_screens`/`roam_current_bounds`/`roam_apply_effect`(창 alpha),
  `roam_tick`(screens 전달·효과), `roam_resync`(현재 화면 bounds). 새 설정 키·메뉴 없음 — '화면 돌아다니기' 토글에 묶인다.
- 문서: `docs-design/quiet-companion.md` §1·§3·§4(R2·R12·R13)·§5·§6 정합, README 네 언어(동작 절 한 불릿, 토글 절).
- 게이트 결과와 수치는 Developer 가 쓰지 않는 독립 기록이 기준이다: `docs-design/companion-play-verification-20260909.md`
  (baseline RED, 최종 SHA 의 focused/full suite, native/합성 다중 화면 기록) 와 `docs-design/companion-play-review-20260909.md`.
  Developer 의 로컬 실행(`tests/test_companion_play.py`·`test_free_roaming.py`·`test_settings_and_install.py` 통과)은 같은 명령을
  같은 결과로 봤다는 확인일 뿐 수치 근거로 쓰지 않는다. `tests/test_companion_motion.py` 의 어댑터 fixture 두 곳(실행 scope 의
  `RoamScreen`, 화면 stub 의 `frame()`)은 Verifier 의 이전 대상이다.
- 이번 변경의 commit 은 최종 독립 게이트 뒤 별도 GO 로, 버전·릴리즈·서명·push·설치는 범위 밖이다.
