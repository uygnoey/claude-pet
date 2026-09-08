# 조용한 동행(quiet companion): 펫의 자율 이동

> 목표: 펫이 화면을 **스스로** 돌아다니되 정신 사납지 않게 — 평소엔 제자리에서 쉬고,
> 사용자가 뭔가 하고 있으면 **한 번** 다가와 멈춰서 바라보고, 천천히 제자리로 돌아온다.
>
> 상태: **구현됨 (미배포, 미커밋)**. 순수 상태기계 `Roamer` 와 `run_gui()` 안의 어댑터.
> 게이트: `tests/test_companion_motion.py` (독립 Verifier 소유). **승인·검증 결과의 단일 기준은
> 이 문서가 아니라** `docs-design/quiet-companion-verification.md`(Verifier) 와
> `docs-design/quiet-companion-review.md`(Reviewer) 다 — 무엇이 어디까지 확인·승인됐는지는 거기서
> 읽는다. 이 문서는 Developer 의 설계·구현 설명이다. 실제 도착 화면: `quiet-companion-arrival.png`.
> 줄 번호는 모두 근사치다 — `grep -n` 으로 심볼을 찾을 것 (CLAUDE.md 의 원칙).
>
> 사용자 원문: *"claude pet이 화면을 자유 분방하게 움직일 수 있게 ... 너무 정신 사납게는
> 말고 내가 뭐 하면 와서 좀 처다보는 듯이"*.

---

## 1. 세 가지 성질로 옮기면

| 원문 | 성질 | 어떻게 |
|---|---|---|
| 너무 정신 사납게는 말고 | **오래 쉰다** | 집(사용자가 놓은 자리)에서 45~90초 쉬고, 구경은 180초에 한 번 이하, 산책은 300초에 한 번 이하(`ROAM_DEFAULTS`). 구경 목적지는 출발점에서 최대 360pt, 산책 목적지는 집 반경 160pt 안 |
| 내가 뭐 하면 와서 좀 쳐다보는 듯이 | **활동이 있으면 한 번 다가와 멈춰 본다** | 최근 20초 안에 커서가 움직였으면 그 순간의 커서 위치를 **한 번만** 읽어 그쪽으로 걷다가 창이 커서에 닿기 한참 전에 멈추고 6초 바라본다(review) |
| 화면을 자유 분방하게 | **가끔 짧게 산책한다** | 집 반경 160pt 안의 임의 지점까지 갔다가 돌아온다 (Coordinator 지침: 구경 중심, 산책은 보수적으로) |

그리고 **사용자가 언제나 우선이다.** 잡거나, 마우스를 올리거나, 메뉴·설정 창을 열거나,
사용량이 급증하거나, 시스템의 '동작 줄이기'가 켜져 있거나, 틱이 오래 멈췄다 돌아오면
펫은 **그 자리에 즉시 선다** — 집으로 순간이동하지도, 하던 이동을 이어 가지도 않는다.
쉬고 나서 새로 계획한다. 걷는 동안 커서가 경로에 들어와도 가로지르지 않고 선다.

**하지 않는 것**

- 커서를 **쫓아다니지 않는다.** 목적지는 출발 순간 한 번 정하고 이동 중 다시 계산하지 않는다.
  매 틱 커서를 보는 유일한 이유는 "경로가 커서에 닿는가" 라는 **정지 조건**이다.
- 키 입력·창 내용·앱 이름을 **읽지 않는다.** 쓰는 입력은 커서 좌표(인사 기능이 이미 20 Hz 로
  읽는 `NSEvent.mouseLocation()`)와 화면 크기뿐이다. 추가 권한은 요청하지 않는다.
- 자동 이동으로 바뀐 좌표를 **저장하지 않는다.** `~/.claude_pet.json` 의 `x`/`y` 는 사용자가
  드래그해 놓은 자리만 담는다. 자동으로 나가 있는 동안의 단순 클릭도 저장하지 않는다.
- 1차에서는 사용량 필을 숨기거나 창 모양을 바꾸지 않았다. 2차 요구(§9)에서 걷는 동안 접고
  도착 시 요약을 보이도록 바뀌었다 — 그때도 펫의 전역 좌표와 Roamer 의 논리 창은 그대로다.

---

## 2. 기존 코드가 움직이는 방식 (소스에서 읽은 사실)

`claude_pet.py` 의 `run_gui()` 안이다.

- **창.** 테두리 없는 `NSWindow`, 투명 배경, `setLevel_(25)`, 모든 Space 에 표시. 시작 위치는
  `cfg["x"]`/`cfg["y"]`(없으면 주 화면 우하단), 그 뒤 `clamp_to_screen()` 이 가장 가까운 화면의
  `visibleFrame` 안으로 되돌린다.
- **드래그.** `mouseDragged_` 가 창 origin 을 델타만큼 옮기며 `running-left/right` 를 sticky
  override 로 켠다. `mouseUp_` 이 sticky 해제 → 클램프 → (이제는 **움직였을 때만**) `x`/`y` 저장.
  더블클릭은 `jumping` + 즉시 새로고침.
- **틱.** `Ticker.tick_` 20 Hz(`TICK = 0.05`): 애니메이션 프레임 진행(`STATE_CFG`), hover
  판정, 근접 인사(`RUNTIME["greet"]`, `NEAR_PX`, `GREET_COOLDOWN`, 조건
  `override is None and not dragging and not spike`), 그리고 이제 `roam_tick()`. `refresh_`
  30 초는 별도 스레드다. 두 타이머 모두 기본 run loop 모드라 우클릭 메뉴의 추적 루프 동안은
  멈춘다.
- **레이아웃 플립.** `PetView.petOnRight()`/`petOnBottom()` 이 창 중심이 화면의 어느 반쪽에
  있는지로 결정하고 `petOrigin()`/`pillTop()`/`pillLeft()` 가 펫과 필의 창 내 위치를 바꾼다.
  펫의 x 는 `6` 또는 `W − PW − 6`, y 는 `2` 또는 `pill_h() + GAP` 이라, 창이 중앙선을 넘는
  순간 펫이 창 안에서 좌우 `W − PW − 12`, 상하 `pill_h() + GAP − 2` 만큼 뛴다(소스에서 유도한
  값, 실측 아님). 자동 이동은 이 판정을 **고정**한다(§5).
- **설정.** `RUNTIME` 이 런타임 값, `apply_config()` 가 설정 파일의 키를 얹고, 설정 창은
  `SETTINGS_OWNED_KEYS` 만 저장한다. `x`/`y`/`scale`/`pet` 은 각자 경로가
  `merge_config_updates()` 로 자기 키만 쓴다. 설정 창의 내용 높이 612 는 y 사슬의 마지막
  행이 테스트 하한(46)에 정확히 놓여 있어 **행을 더 넣을 여유가 0** 이다 — 그래서 토글은
  우클릭 메뉴에 있다(§6).

---

## 3. 행동

```
   rest(집 또는 멈춰 선 자리) ─휴식 끝─┬─ 활동 있고 cooldown 지남 ─▶ out ─도착─▶ look(6s, review) ─▶ home ─도착─▶ rest
                                      ├─ 산책 허용 ────────────▶ out ─도착─▶ look(2s, idle)   ─▶ home ─도착─▶ rest
                                      ├─ 집이 아니면 ────────────────────────────────────────▶ home ─도착─▶ rest
                                      └─ 아니면 휴식 재추첨
   out/look/home 어디서든: enabled=False · dragging · blocked · busy · 틱 공백>5s · 경로가 커서에 닿음
                          ─▶ 그 자리에 즉시 정지, rest, 휴식 재추첨 (순간이동·재개 없음)
```

**좌표는 창 중심**이다(전역 스크린 포인트, y 위). `radius` 는 창 전체의 외접원 반지름
`hypot(W/2, H/2)` 라서, "커서까지 `radius` + 여백" 이면 창의 어느 픽셀도 커서에 닿지 않는다.
허용 rect(`bounds`)는 창 전체가 `visibleFrame` 안에 남는 중심의 범위다 — 창이 화면에 들어갈
크기일 때, 정상 이동은 창을 화면 안에 유지한다. 창이 화면보다 크거나 화면 구성이 바뀐 뒤의
복구는 R8 이 다룬다.

**활동(activity)** 은 "최근 20초 안에 커서가 1 Hz 샘플 사이 12pt 이상 움직였다" 이다.
30초 새로고침 워커가 `activity=True` 힌트를 넘길 수도 있지만 지금은 쓰지 않는다.

**구경(approach)** 은 커서와 창 외접원 사이 150pt 를 남기고 멈춘다(중심 기준 `150 + radius`).
커서가 그보다 360pt 넘게 멀면 360pt 만 가서 **멀리서 본다.** 이미 그 거리 안이면 걷지 않고
제자리에서 바라본다.

**산책(wander)** 은 집 기준 반경 160pt 의 임의 지점. 커서 근처(`150 + radius`)에 떨어지는
지점은 버린다.

**빈도.** 휴식 45~90초(균등 난수) 뒤에 출발을 "고려" 한다. 구경은 직전 구경 뒤 180초, 산책은
직전 산책 뒤 300초가 지나야 한다. 거리 상수: 구경 목적지는 출발점에서 최대 360pt
(`approach_max`), 산책 목적지는 집 반경 160pt 안(`wander_radius`), 이동 속도 55pt/s
(`walk_speed`). 걸리는 벽시계 시간은 틱 간격과 `max_dt_s` 에 달려 있어 여기서 보장하지
않는다. 실제 사용에서의 빈도는 측정하지 않았다.

**정지 규칙이 "집으로" 가 아니라 "그 자리" 인 이유.** 메뉴를 열었는데 펫이 집으로 걸어가면
사용자 조작보다 펫의 사정이 앞선다. 동작 줄이기가 켜졌는데 집으로 뛰면 "움직이지 말라" 는
설정에서 한 번 더 뛰는 셈이다. 그래서 어느 경우든 그 자리에 서고, 쉰 뒤 새로 계획한다 —
계획에는 "집이 아니면 귀가" 가 들어 있으므로 결국 천천히 돌아온다.

---

## 4. 순수 상태기계 API — 모듈 레벨, AppKit 없음

`run_gui()` 바깥의 모듈 레벨. `math`/`random`/`namedtuple` 과 이 절의 정의만 참조하므로
게이트 테스트가 AST 로 이 절만 뽑아 AppKit 없이 실행한다 — **다른 모듈 레벨 이름을 여기서
끌어오면 그 시험이 깨진다.**

```python
ROAM_DEFAULTS = {
    "rest_min_s": 45.0, "rest_max_s": 90.0,   # 쉬는 시간: rng.uniform(min, max)
    "approach_cooldown_s": 180.0,             # 구경 최소 간격
    "wander_cooldown_s": 300.0,               # 산책 최소 간격
    "walk_speed": 55.0,                       # pt/s
    "approach_stop": 150.0,                   # 커서와 창 외접원 사이 최소 거리 (+ radius = 중심 기준)
    "approach_max": 360.0,                    # 한 번 이동 상한
    "look_s": 6.0,                            # 바라보기 지속
    "wander_radius": 160.0,                   # 집 기준 산책 반경, 0 이면 산책 없음
    "wander_pause_s": 2.0,
    "activity_window_s": 20.0,
    "cursor_move_px": 12.0, "cursor_sample_s": 1.0,
    "cursor_margin_px": 24.0,                 # 이동 중 외접원과 커서 사이 안전 여백
    "max_dt_s": 0.25,                         # step 당 이동 시간 상한
    "gap_s": 5.0,                             # 이보다 긴 틱 공백이면 그 자리 정지
    "min_trip_px": 60.0, "arrive_px": 2.0,
}
RoamOut = namedtuple("RoamOut", "pos anim moved away phase")
#   pos=(x, y) 창 중심 / anim=None|"running-left"|"running-right"|"review" /
#   moved=이 step 에 pos 변함 / away=|pos−home|>arrive_px / phase="rest"|"out"|"look"|"home"

class Roamer:
    def __init__(self, home, now, rng=None, cfg=None, radius=0.0)   # cfg 는 ROAM_DEFAULTS 위에 얹는 부분 dict
    # 읽기: pos, home, phase, kind ∈ {None, "approach", "wander"}, radius(갱신 가능), cfg, away
    def step(self, now, cursor, bounds, *, enabled=True, dragging=False,
             blocked=False, busy=False, activity=False) -> RoamOut
    def set_home(self, pos, now)          # 수동 배치: pos = home = pos, 그 자리 정지, 휴식 재추첨
    def release(self, now, pos, moved)    # 드래그/클릭 끝: moved → set_home / 아니면 pos 만 맞추고 정지·휴식
    # settled (읽기): 마지막 rest 가 자연 완료였는가 — §9.1 D4 참조 (2차 요구에서 추가)
```

### 규칙

- **R1 rest.** 생성·정지·귀가 시 `next_at = now + rng.uniform(rest_min_s, rest_max_s)`.
  `next_at` 전에는 어떤 step 도 `moved=True` 를 내지 않는다 — 단 하나의 예외는 R8 의 화면
  복구(창이 정상 `bounds` 밖에 남았을 때 안으로 들이는 것)다. 쉬는 중 `gap_s` 보다 긴 공백이
  오면 다시 추첨한다(깨어나자마자 출발하지 않게).
- **R2 출발.** rest 에서 `now >= next_at` 이고 `enabled and not dragging and not blocked and
  not busy` 일 때, 순서대로: (a) `active(now)` 이고 `cursor` 가 있고 `now >= approach_ok_at` →
  구경 계획(R3), 성공 시 `approach_ok_at = now + approach_cooldown_s`; (b) `wander_radius > 0`
  이고 `now >= wander_ok_at` → 산책 계획(R4), 성공 시 `wander_ok_at = now + wander_cooldown_s`;
  (c) `away` 면 집으로 가는 leg; (d) 아니면 휴식 재추첨. **쉬는 동안 플래그가 하나라도
  참이면 매 step 휴식을 다시 추첨한다** — 조작이 이어지는 동안 마감이 계속 뒤로 밀리므로,
  조작이 *끝난* 시점부터 온전한 휴식이 확보되고 지나간 마감을 따라잡아 곧바로 출발하는
  일이 없다. **계획한 step 에는 움직이지 않는다.**
- **R3 구경 계획.** `stop = approach_stop + radius`, `d = |cursor − pos|`. `d <= stop` →
  제자리 구경. 아니면 `travel = min(d − stop, approach_max)`, 그 방향으로 `travel` 간 점을
  `bounds` 로 클램프. 클램프 뒤 `|target − cursor| < stop/2` 면 실패, `|target − pos| < min_trip_px`
  면 제자리 구경. **커서는 이 순간 한 번만 읽는다.**
- **R4 산책 계획.** `ang = rng.uniform(0, 2π)`, `dist = rng.uniform(min_trip_px, wander_radius)`,
  `target = home + (cos, sin)·dist` 를 클램프. `|target − pos| < min_trip_px` 이거나 커서와
  `stop` 안이면 실패. 반경은 **집** 기준이다.
- **R5 걷기 (out/home 공통).** `dt = min(now − last_now, max_dt_s)`. leg 목표(`target` 또는
  `home`)를 `bounds` 로 클램프한 뒤, **현재 커서와 [pos, 목표] 선분의 거리가 `radius +
  cursor_margin_px` 보다 작으면 그 자리 정지(R7).** 아니면 `walk_speed · dt` 만큼 넘치지 않게
  옮긴다. `anim` 은 leg 시작 때 한 번: 목표가 오른쪽이면 `"running-right"`, 아니면
  `"running-left"`. 남은 거리가 이번 걸음(또는 `arrive_px`) 이하면 목표에 놓고: out 이면 look,
  home 이면 rest.
- **R6 look.** 구경은 `anim="review"` 로 `look_s`, 산책은 `anim=None` 으로 `wander_pause_s`.
  끝나면 `away` 면 집 leg, 아니면 rest.
- **R7 정지 (모든 phase).** out/look/home 에서 `enabled=False`·`dragging`·`blocked`·`busy`
  중 하나라도 참이거나, `now − last_now > gap_s` 이거나, `bounds` 가 뒤집혀 있으면
  **그 자리에 즉시 선다**: `phase="rest"`, 목표·종류·애니메이션 폐기, 휴식 재추첨.
  순간이동도 재개도 없다. 이 판정은 경계 검사보다 **먼저** 온다 — 뒤집힌 경계에서 목표를
  남겨 두면 화면이 돌아왔을 때 오래된 경로를 이어 걷게 된다.
- **R8 경계.** 뒤집힌 `bounds`(`x0 > x1` 또는 `y0 > y1`)에서 쉬는 중이면 아무것도 하지
  않는다. 정상 `bounds` 인데 `pos` 가 그 밖에 있으면 — 화면 구성이 바뀐 경우다 — `pos` 와
  `home` 을 안으로 들이고(`moved=True`; 자동 이동이 하는 **유일한 점프**, 창 전체가 다시
  보이게 하는 것이 목적이다) 하던 이동은 접는다. 걷는 leg 의 목표는 매 step 클램프한다.
- **R9 활동.** `cursor` 는 `cursor_sample_s` 마다 한 번만 직전 샘플과 비교하고, 거리가
  `cursor_move_px` 이상이면 `last_active = now`. `activity=True` 도 같다.
  `active(now) = now − last_active <= activity_window_s`. 초기 `last_active = −inf`.
- **R10 release.** `moved=True` → `set_home(pos)`. `moved=False` → `pos` 만 넘겨받은 값으로
  맞추고 집은 그대로, 그 자리 정지, 휴식 재추첨.
- **R11 저장 금지.** 상태기계는 파일을 모른다. 어댑터는 자동 이동으로 바뀐 좌표를 설정에
  쓰지 않는다.

### 왜 이 모양인가

- **모든 입력이 `step()` 의 인자다.** 시계·커서·경계·플래그가 인자라 시험이 시계를 돌리고
  화면을 지어내고 플래그를 켜고 끄며 결과를 단언한다. 상태기계는 `time`, `NSEvent`,
  `NSScreen`, `RUNTIME` 어느 것도 읽지 않는다.
- **난수는 `rng.uniform` 하나.** 시험은 `uniform(a, b)` 가 `a` 를 돌려주는 stub 을 넣는다.
- **출력은 값이다.** 창을 옮기고 override 를 켜는 것은 어댑터의 일이다.
- **`radius` 하나로 "창이 커서에 닿는가" 를 판정한다.** 창의 실제 사각형 대신 외접원을 쓰는
  보수적 근사라, 상태기계가 창 모양이나 레이아웃을 알 필요가 없다.

---

## 5. 어댑터 — `run_gui()` 안

| 이름 | 역할 |
|---|---|
| `window_center()` / `place_window_center(pos)` | **논리 full 창** 중심 ↔ 실제 창 원점 변환. 현재 어댑터는 §9.3 의 논리↔crop 변환을 쓴다: `center = (origin.x − cx + W/2, origin.y − (H − cy − ch) + H/2)`, 실제 원점 `= (center.x − W/2 + cx, center.y + H/2 − cy − ch)` (crop 크기가 실제 창과 다르면 크기까지 바꾼다). `center = origin + size/2` 는 crop 이 없을 때(시작 시, 창 없는 시험)의 특수한 경우다. 네이티브 frame 이 좌표를 반올림할 수 있으므로 정확한 역함수라고 기대하지 않는다 — 그래서 나가 있는 동안의 기준은 상태기계의 `pos` 이고, 창은 매번 그 값에서 다시 놓는다. |
| `roam_bounds()` | 창이 놓인 화면(`win.screen()`, 없으면 주 화면)의 `visibleFrame` 을 창 크기의 절반만큼 안쪽으로 — 창 전체가 화면 안에 남는 중심 rect. |
| `_reduce_motion()` | `NSWorkspace.sharedWorkspace().accessibilityDisplayShouldReduceMotion()`. 1 Hz 로만 읽어 `state["reduce_motion"]` 에 둔다. |
| `roam_resync()` | `set_scale`/`apply_pill_rows`/`set_pet` 뒤. 크기 변경도 조작이다: `radius = hypot(W/2, H/2)` 갱신 → 나가 있으면 `release(now, 클램프된 pos, False)` 로 그 자리 정지, 집이면 `set_home(클램프된 창 중심)` → 창 전체가 화면 안에 남도록 그 중심에 창을 놓는다. |
| `roam_tick()` | 매 틱(인사 판정 뒤): 플래그를 모아 `roamer.step(...)`, 결과를 창과 override 에 반영. |

`roam_tick()` 이 넘기는 플래그:

- `enabled = RUNTIME["roam"] and not state["reduce_motion"]`
- `dragging = state["dragging"]`
- `blocked = state["hover"] or (override 가 있는데 우리가 켠 것(state["roam_anim"])이 아님)` —
  인사·점프·드래그 달리기가 재생 중이면 출발하지 않고, 이동 중이면 선다.
- `busy = 설정 창 열림(ui["panel"]) or state["menu_open"] or state["roam_hold"] or spike`.
  `roam_hold` 는 `rightMouseDown_` 의 `finally` 가 세우는 한 번짜리 표시다: 메뉴 추적 루프
  동안 틱이 멈추므로 `menu_open` 만으로는 "메뉴가 열렸었다" 를 틱이 못 본다. 5초 안에 닫혀도
  다음 틱이 반드시 정지로 처리하게 한다.

결과 반영:

- `out.moved` 면 **창을 옮기기 전에** `state["roam_layout"] = (petOnRight(), petOnBottom())` 을
  한 번 잡아 둔다. `petOnRight()`/`petOnBottom()` 은 이 값이 있으면 그대로 돌려준다 → 이동
  중·구경 중·정지 후 어디서도 펫이 창 안에서 튀지 않는다. 이 고정은 **수동 드래그가 끝날 때만**
  (`mouseUp_`, `_moved` 참) 풀린다.
- `out.anim` 이 바뀌면 `set_override(anim, sticky_flag=True)`, `None` 이 되면 **우리가 켠
  override 일 때만** `clear_sticky()`. `state["roam_anim"]` 이 그 구분이다.

`mouseUp_` 의 변경: `_moved` 일 때만 `roam_layout` 해제 + `x`/`y` 저장. 그 뒤
`state.get("roam_release")` 훅이 있으면 `hook(moved)` → `roamer.release(monotonic, 창 중심,
moved)`. 훅을 `state` 로 우회하는 이유: 게이트가 `mouseUp_` 본문을 AST 로 떼어 창 없는 scope
에서 실행하며, 그 scope 에는 `roamer` 가 없다.

`rightMouseDown_`: 항목 표에 `(t("menu_roam"), "toggleRoam:")` 을 "접기/펴기" 다음에 넣고
체크 상태(`RUNTIME["roam"]`)와 동작 줄이기 때의 비활성을 준다. 펫 서브메뉴 삽입 인덱스는
3 → 4. `popUpContextMenu` 를 `state["menu_open"] = True … finally: False, roam_hold = True`
로 감싼다.

시작: `clamp_to_screen()` 뒤에 `roamer = Roamer(window_center(), time.monotonic(),
radius=hypot(W/2, H/2))`. 시계는 `time.monotonic()` — 인사가 쓰는 `time.time()` 은 벽시계라
점프할 수 있다.

---

## 6. 설정·UI

**우클릭 메뉴의 체크 항목 하나** — 설정 창이 아니라.

| 항목 | 내용 |
|---|---|
| 런타임 키 | `RUNTIME["roam"]`, 기본 `CLAUDE_PET_ROAM` 환경변수("1"). `apply_config()` 키 목록에 포함. |
| 저장 | `Handler.toggleRoam_` 이 `merge_config_updates({"roam": v})` 로 **자기 키만** 쓴다 — `x`/`y`/`scale`/`pet` 과 같은 방식. `SETTINGS_OWNED_KEYS` 와 설정 창 계약은 그대로다. |
| 문자열 | `menu_roam` — en "Roam the screen", ko "화면 돌아다니기", ja "画面を歩き回る", es "Pasear por la pantalla". |
| 끄면 | 다음 틱에 그 자리에서 선다. 켜면 휴식부터 다시. |
| 동작 줄이기 | 켜져 있으면 `enabled=False` 와 같고, 메뉴 항목은 비활성으로 보인다. 그러려면 메뉴에 `setAutoenablesItems_(False)` 가 필요하다 — `NSMenu` 기본값은 표시 직전 항목을 다시 검증해 target 이 action 에 응답하면 enabled 를 YES 로 되돌리므로, 항목의 `setEnabled_(False)` 만으로는 덮인다. 실제 OS 에서 AXEnabled=True 로 발견·재현된 기록: `docs-design/quiet-companion-verification.md`(Verifier native RED), Reviewer 독립 재현. |
| README.ko.md | "행동" 한 줄, "조작 › 우클릭", "설정" 문단에 끄는 법·동작 줄이기·저장 안 함. |

설정 창 체크박스를 쓰지 않는 이유는 §2 의 높이 예산이다. 설정 창을 택한다면 612 → 644,
테스트의 고정값, CLAUDE.md 문장을 함께 바꿔야 한다.

---

## 7. 고려한 경우들

| 상황 | 동작 | 근거 |
|---|---|---|
| hover(접기 버튼 표시 중) | 출발 안 함, 이동 중이면 그 자리 정지. 커서가 떠난 뒤 온전한 휴식부터 | R2, R7 `blocked` |
| 드래그 | 어느 phase 든 정지. 놓으면 `_moved` 일 때만 새 집·저장 | R7, R10, `mouseUp_` |
| 클릭(안 움직임) | 정지·휴식, 집과 저장값은 그대로 | R10, 게이트 `test_click_during_auto_away…` |
| 더블클릭(점프) 재생 중 | 출발 안 함 / 이동 중 정지 | `blocked` |
| 우클릭 메뉴 | `menu_open` + `roam_hold` 로 busy → 정지. 틱이 멈춘 공백이 5초를 넘어도 같은 결과 | R7 |
| 설정 창 열림 | busy → 정지, 닫힌 뒤 휴식하고 새 계획 | R7 |
| spike | busy — 패닉 중엔 돌아다니지 않는다 | R7 |
| 크기 조절 / 필 행 수 변경 / 펫 교체 | 하던 이동 정지, `radius` 갱신, 창 전체가 화면 안에 남게 재배치 | `roam_resync`, R10 |
| 동작 줄이기 | `enabled=False` → 그 자리 정지, 이후 정지. 메뉴 항목 비활성 | R7 |
| 커서가 경로에 들어옴 | out/home 어느 leg 든 그 자리 정지, 우회 없음 | R5 |
| 화면 밖 | 목표는 항상 창 전체가 화면 안에 남는 rect 안 | R3, R4, `roam_bounds` |
| 화면 구성 변경 (축소·모니터 탈착) | `bounds` 는 매 틱 새로 읽는다. 창이 밖에 남으면 안으로 들이고 하던 이동은 접는다 | R8 |
| 다중 모니터, 커서가 다른 화면 | 목표가 집 화면 가장자리로 클램프 → 가장자리에서 본다 | R3 |
| 음수 좌표 화면 | rect 산술뿐, 부호 가정 없음 | 게이트 `test_nonzero_negative_monitor…` |
| 창보다 작은 화면 | `bounds` 가 뒤집힘 → 아무것도 안 함 | R8 |
| 잠자기 → 깨어남 | 공백이면 그 자리 정지·휴식 재추첨; 이동량은 어차피 `max_dt_s` 상한 | R1, R5, R7 |
| 인사(waving) | 걷기·구경 중엔 override 가 차서 안 켜짐; 산책 멈춤 중엔 켜질 수 있음 | 인사 조건 `override is None` |
| 자동 좌표 저장 | 없음 | R11 |
| 개인정보 | 커서 좌표는 메모리에서만 쓰고 로그·설정·오류 메시지에 쓰지 않는다 | CLAUDE.md Privacy |

**검증 체크리스트 — 실제 앱에서 확인해야 하는 항목.** 이것은 Developer 가 Verifier 에게 넘긴
확인 목록이지 "아직 안 했다" 는 뜻이 아니다. 각 항목의 실제 수행 여부와 결과는
`docs-design/quiet-companion-verification.md`(native smoke·CGEvent 조작·프레임 추적) 와
`docs-design/quiet-companion-review.md` 에 기록돼 있고, 그 기록이 기준이다.

1. 화면 중앙선을 걸어서 넘을 때 펫이 **연속**인가(레이아웃 고정이 맞게 걸렸는가).
2. 메뉴를 열었다 닫으면 펫이 **그 자리에 서는가**(집으로 걷거나 튀지 않는가).
3. 시스템 설정 › 손쉬운 사용 › 동작 줄이기를 켜면, 다음 설정 확인 틱에서 이를 감지했을 때 그
   자리에 서고 메뉴 항목이 흐려지는가.
4. 구경하러 갔을 때 창(필 포함)이 커서와 작업 영역을 가리지 않는가 — 안 그렇다면
   `approach_stop` 이나 `cursor_margin_px` 를 키운다.

---

## 8. 산출물과 범위

| 파일 | 변경 |
|---|---|
| `claude_pet.py` | 상단 `import math`/`random`/`namedtuple`. `RUNTIME["roam"]`, `apply_config` 키. `TR` 네 언어에 `menu_roam`. 모듈 레벨 `ROAM_DEFAULTS`/`RoamOut`/`_roam_*` 헬퍼/`Roamer`. `run_gui()`: `NSWorkspace` import, `state` 키 6개, `petOnRight`/`petOnBottom` 고정 분기, `mouseUp_`(moved 일 때만 저장 + 훅), `rightMouseDown_`(항목·인덱스·try/finally), 어댑터 함수 6개(`window_center`, `place_window_center`, `roam_bounds`, `_reduce_motion`, `roam_resync`, `roam_tick`), `set_scale`/`apply_pill_rows`/`set_pet` 의 `roam_resync()`, `Handler.toggleRoam_`, `tick_` 의 `roam_tick()`, 시작 시 `roamer` 생성과 훅. |
| `README.ko.md` | §6 의 세 곳. |
| `docs-design/quiet-companion.md` | 이 문서. |

**하지 않은 것.** `tests/` 는 Verifier 의 것이다. `README.md`/`README.ja.md`/`README.es.md` 는
이 과제의 산출물 목록에 없다(필요하면 별도 배정). 버전 bump·릴리즈 노트·커밋·푸시·빌드·
서명·설치·배포는 하지 않았다. 사용자 소유 untracked 파일(`diag.py`,
`release/ClaudePet.iconset/`, `release/icon_1024.png`)은 건드리지 않았다. 추정기·가중치·
윈도우는 손대지 않았으므로 보정된 한도가 흔들리는 일도 없다.

**Developer 의 범위에서는 앱을 실행하지 않았다.** GUI 실행·조작·계측은 독립 Verifier 의
단독 소유다. §7 과 §9.4 의 체크리스트는 Developer 가 Verifier 에게 넘긴 확인 항목이고, 실제
수행과 결과는 Developer 가 쓰지 않는 별도 기록에 있다: `docs-design/quiet-companion-verification.md`
(Verifier — native smoke, CGEvent 조작, 프레임 추적, 실제 OS 설정 확인),
`docs-design/quiet-companion-review.md`(Reviewer), 실제 도착 화면 `quiet-companion-arrival.png`,
그리고 그 옆의 `quiet-companion-smoke.*`, `quiet-companion-live-*` 산출물. 무엇이 확인·승인됐고
무엇이 아직 진행 중인지는 그 두 기록이 단일 기준이다.

---

## 9. 이동 중 접기, 도착 요약 (2차 요구)

> 사용자 원문: *"이동중엔 게이지는 접어서 넣어두고 이동하자 그리고 와서 펼쳐주거나 요약으로 작게
> 표시해주거나"*. Coordinator 기본 선택: 구경 도착 시 세션·주간 % 중심의 작은 요약, 원하면 전체
> 펼치기. 데이터가 없을 때 0% 를 꾸며 내지 않는다. 산책 도착은 조용히.
>
> 상태: **구현됨 (미배포, 미커밋).** 순수 상태·요약(`RoamDisplay`, `roam_summary`,
> `roam_summary_line`, `roam_fit_text`), 기하(`roam_pill_rect`, `roam_frame`,
> `roam_logical_center`), `run_gui()` 어댑터. 게이트는 `tests/test_companion_motion.py` 의
> Presentation/CropGeometry/CompactRegression 절(Verifier 소유). 실행 증거와 승인·검증 결과의
> 단일 기준은 `docs-design/quiet-companion-verification.md` 와 `docs-design/quiet-companion-review.md`
> 다. 실제 도착 화면(요약 필이 붙은 모습): `quiet-companion-arrival.png`.

### 9.1 세 가지 표시 모드와 그 유도

`state["show_panel"]` 은 여전히 **사용자의** 접기 선택이고 자동 표시는 이 값을 절대 덮어쓰지 않는다.
화면에 그릴 모드는 매 틱 `RoamDisplay.mode(phase, show_panel)` 로 유도한다.

| 모드 | 언제 | 그리는 것 |
|---|---|---|
| `folded` | 걷는 동안(out/home), 산책 멈춤(look·wander), 사용자가 접어 둔 채 쉴 때 | 펫만 (hover 면 ⌄ 버튼) |
| `summary` | 구경 도착(look·approach) 뒤, 래치가 살아 있는 동안 | 펫 + 한 줄 요약 필 |
| `full` | 요약에서 사용자가 펼쳤을 때, 또는 사용자가 펼쳐 둔 채 쉴 때 | 기존 게이지 필 전체 |

`RoamDisplay` 의 상태는 둘뿐이다 — `summary`(래치), `expanded`(요약 중 펼침). 규칙, 우선순위 순:

- **D0 명시적 중단·비활성이 먼저.** `interrupted`(설정 창·메뉴·spike·틱 공백) 또는 `enabled=False`
  → 둘 다 끈다. 같은 호출에 도착이 실려 있어도 중단이 이긴다.
- **D1 걷기.** phase 가 out/home → 둘 다 끈다(걷는 동안엔 접는다).
- **D2 도착.** phase 가 look 이고 kind 가 approach → `summary=True`. 집에서의 제자리 구경도 같다.
- **D3 귀환.** phase 가 rest 이고 집에 있으면 → 둘 다 끈다(평소 선택 복원).
- **D4 hover 정지는 중단이 아니다.** rest 인데 나가 있으면(hover 로 멈춘 것) 래치를 **유지**한다 —
  요약을 펼치려면 커서를 올려야 하고, 그 순간 요약이 사라지면 펼칠 수 없다. 집에서의
  제자리 구경은 hover 정지도 6초 만료도 rest/집이라 구별이 필요하다: `Roamer.settled`
  (자연 완료=True: 생성·구경 만료·귀가 도착·휴식 끝 재추첨·`set_home`; 정지=False: hold·
  공백·guard·경계·단순 클릭 `release(moved=False)`)를 `note(..., settled=)` 로 넘기고, D3 는
  `settled` 일 때만 복원한다. 정지로 남은 요약은 다음 휴식 끝에 Roamer 가 할 일 없이 재추첨
  하면(settled=True) 평소 선택으로 돌아간다.
- **`dragging` 은 `interrupted` 에 넣지 않는다.** 클릭의 mouseDown 도 한 틱 `dragging` 을 세우므로,
  넣으면 ⌄ 버튼 클릭 자체가 요약을 지운다. 진짜 드래그는 `release(moved=True)` 훅이 `reset()` 한다.
- **toggle.** 기존 펼치기 조작(⌄ 버튼, 메뉴 '접기/펴기')은 `RoamDisplay.toggle(show_panel)` 을
  거친다: 래치 중이면 `expanded` 만 뒤집고 `show_panel` 을 그대로 돌려준다(평소 선택 불변); 아니면
  기존처럼 반전한다.
- **메뉴는 시작 시 복원.** `rightMouseDown_` 이 메뉴를 띄우기 *전에* `reset()` 한다. 그래서 메뉴의
  '접기/펴기' 는 래치 없이 평소 선택을 바꾸는 일반 토글이고, 메뉴 뒤에 오는 `roam_hold` 중단은
  멱등이라 의도한 펼치기가 되돌려지는 일이 없다. ⌄ 버튼 경로만 요약을 유지한 채 펼친다.

흐름 하나를 끝까지, 두 갈래로:

- **손대지 않으면**: 집에서 전체 게이지를 보던 사용자 → 출발하면 접힘 → 도착하면 요약(6초 구경)
  → 6초 뒤 접힌 채 귀가 → 집에서 전체. 접어 두던 사용자는 마지막이 접힘으로 끝난다.
- **⌄ 를 누르면**: 커서를 올리는 순간 hover 가 Roamer 를 **그 자리에 세운다**(`blocked` → rest,
  `settled=False`) — 6초 구경은 더 진행되지 않고, 요약 래치는 남는다. ⌄ → 전체, 다시 ⌄ → 요약.
  커서가 떠나면 Roamer 는 조작이 끝난 시점부터 휴식(45~90초)을 다시 재고, 휴식 끝에 집이 아니면
  귀가 leg 를 시작하며 그때(D1) 접힌다 → 집에서 평소 선택. 즉 클릭 뒤 "6초 뒤 귀가" 가 아니라
  "커서가 떠난 뒤 휴식 한 번 지나고 귀가" 다.

### 9.2 요약 내용 — `roam_summary(mode, oauth, stats, onboard, cost_today, has_admin_key)`

반환은 `(kind, payload)` 이고, 데이터가 없으면 상태 키를 돌려준다. 어떤 경우에도 0% 를 지어내지
않는다: 값은 실수형(bool 제외)·유한·0 이상일 때만 쓰고, 아니면 그 행을 버린다.

| 조건(위에서부터) | 반환 |
|---|---|
| API 모드, Admin 키 없음 | `("status", "need_admin_key")` |
| API 모드, 오늘 비용이 유효 수치가 아님 | `("status", "loading")` |
| API 모드 | `("cost", float)` |
| 정확 모드 행이 있음 | 앞 2행 중 유효 행 `("exact", [(라벨 원문, pct), …])`, 유효 행이 없으면 `("status", "scanning")` — 추정으로 내려가지 않는다 |
| 온보딩(install/login) | `("status", "onb_install" / "onb_login")` |
| 로그 추정 stats | `("estimate", [("session", pct), ("weekly", pct)])` 중 유효 행, 없으면 `scanning` |
| 그 외 | `("status", "scanning")` |

라벨의 두 종류는 **kind 로 구분**한다. 한 줄 문자열은 순수 `roam_summary_line(kind, payload, tr)` 가
만든다: `exact` 의 라벨은 서버 행의 원문이고 `tr` 에 넣지 않고 그대로 — 원문이 우연히 `"session"`
같은 번역 키와 같아도 보존된다 — 값에 표식이 없다(`Session 42% · Weekly 17%`). `estimate` 의 라벨은
키 `"session"`/`"weekly"` 라 `tr(label)` 로 옮기고, **값 앞에 `SUMMARY_APPROX`(≈)** 를 붙여 추정치임을
보인다(`세션 ≈42% · 주간 ≈17%`). `cost` 는 `tr("today") $1.23`, `status` 는 `tr(key)`. 상태 키 다섯
개는 `TR` 네 언어에 이미 있다. 어댑터 `roam_summary_text()` 는 이 줄과 그 폭(`F_SUMMARY`)을 돌려주고,
`draw_summary_pill()` 이 실제 필의 안쪽 폭(`w − 2·PILL_PAD`)에 맞춰 **같은 폰트로 재면서** 순수
`roam_fit_text(text, max_w, measure)` 로 말줄임한다 — 폰트를 줄이지 않는다(11pt 가독성). 들어가면 원문,
아니면 실제 측정으로 고른 가장 긴 prefix + `…`, `…` 하나도 안 들어가면 빈 문자열. 세부는 기존 ⌄ 로 전체
게이지를 열어 본다.

### 9.3 기하 — 실제 창은 논리 창의 부분 사각형

`Roamer` 는 그대로 **논리 full 창**(크기 `geom()` 의 W×H, 중심 `roamer.pos`, 배치 right/bottom)을
다룬다. 중심·radius·bounds·집 전부 불변. 실제 `NSWindow` 는 그 논리 창의 **부분 사각형(crop)** 이다:

| 모드 | crop |
|---|---|
| `full` | 논리 창 전체 `(0, 0, W, H)` |
| `folded` | 펫 rect ∪ ⌄ 버튼 rect 를 2pt 넓힌 것 |
| `summary` | 펫 ∪ 버튼 ∪ 요약 필 을 2pt 넓힌 것 |

crop 은 모드에서만 유도되므로 **순수 좌표 계산상** 펫의 전역 좌표 `논리원점 + (px, py)` 는 모드와
무관하게 같다 — 접기·요약·펼침 전환에서 바뀌는 것은 창의 origin/size 뿐이다(게이트의
`CropGeometryTests` 가 세 모드에서 anchor 가 같음을 고정한다). 실제 AppKit 창은 frame 을 정수
포인트/픽셀로 양자화할 수 있어 화면에서도 정말 움직이지 않는지는 이 계산이 아니라 **Verifier 의
실행 증거**(프레임 추적·스프라이트 step 계측)로 확인한다. 접힌 큰
투명 창이 작업 영역을 가리는 문제는 이렇게 창 자체가 작아져서 사라지고, hover 판정(`win.frame()`
기준)도 자연히 그린 영역으로 줄어든다. 집에서 사용자가 접어 둔 경우도 같은 규칙으로 작아진다.

순수 함수 `roam_frame(center, mode, right, bottom, W, H, PW, PH, pill_h, scale, text_w)` 가 crop,
실제 origin/size, 그리고 실제 창 좌표의 펫/버튼/필 rect 를 돌려주고, `roam_logical_center(origin,
size, crop, env)` 가 실제 창에서 논리 중심을 되찾는다(crop 이 없으면 창 중심 — 기존 어댑터 시험과
같은 뜻). 요약 필 rect 는 `roam_pill_rect` 가 펫 쪽에 정렬해 펫에 붙인다(폭은 글자 폭에 맞춰
`SUMMARY_MIN_W`~`PILL_W`, 높이 `SUMMARY_H`).

표시용 크기 변경은 `roam_resync()` 를 부르지 않는다 — 경로도 집도 그대로다. **전환의 기준점은
`roamer.pos` 가 아니라 변경 직전 실제 창의 논리 중심(`window_center()`, 옛 crop 으로 역산)** 이다:
트립 중엔 둘이 같지만, 드래그·clamp·필 행 수 변경처럼 창이 밖에서 움직인 뒤 `roamer.pos` 로 놓으면
사용자의 이동이 지워진다(잡은 순간 걷던 펫이 펼쳐지며 되돌아가는 결함이 이것이었다). 사용자가 직접
크기를 바꾸거나 펫을 바꿀 때(`set_scale`/`apply_pill_rows`/`set_pet`)만 기존 resync(정지·재배치)가 돈다.
`clamp_to_screen()` 도 **논리 full 창** 을 화면 안에 두는 것으로 바뀌었다: 접힌 창만 화면 안에 두면
논리 원점이 화면 밖에 저장되고 집도 그리로 잡혀, 다음에 펼쳐질 때 펫이 화면 밖에 놓인다. 그래서
가장자리에 접힌 채 놓으면 놓는 순간 crop 오프셋(≤ W − cw)만큼 안쪽으로 밀릴 수 있다 — full 창을 화면
안에 두는 대가다. 놓은 뒤 배치 고정이 풀려 live 배치가 바뀌면 다음 틱에 crop 이 바뀌며 펫이 논리 창
안에서 옮겨 앉는데, 이는 기존 중앙선 플립과 같은 크기·같은 계기다.
그 세 경로는 실제 창이 접혀 있어도 **논리 원점**(`roam_logical_origin()`)을 기준으로 새 full 창을
놓고, `roam_env_update()` 로 논리 크기를 갱신하며 crop 을 비운다(다음 틱에 다시 잘린다).
`mouseUp_` 이 저장하는 `x`/`y` 도 논리 원점이라, 접힌 채 옮겨 놓아도 다음 실행에서 같은 자리에
뜬다. `petOnRight()`/`petOnBottom()` 은 실제 origin 과 논리 W/H 를 섞지 않고 논리 중심
(`window_center()`)으로 판정하고, 인사의 pet_center 는 실제 창 높이를 쓴다 — `petOrigin()` 등
네 위치는 `roam_rects` 가 있으면 실제 창 좌표를 돌려주므로 그리기·버튼 판정·인사가 자동으로 맞는다.
어댑터 시험(창 없는 scope)에서는 `roam_env`/`roam_crop`/`roam_display` 가 없어 실제 창 = 논리 창으로
동작한다.

### 9.4 검증 체크리스트 (실제 앱에서)

Developer 가 Verifier 에게 넘긴 확인 항목이다 — "미수행" 목록이 아니다. 각 항목의 실제 수행과
결과는 `docs-design/quiet-companion-verification.md` 와 `docs-design/quiet-companion-review.md` 에
있고, 도착 장면은 `quiet-companion-arrival.png` 에 있다. 아직 진행 중인 항목이 무엇인지도 그
두 기록이 말한다.

1. 접힘 ↔ 요약 ↔ 전체 전환에서 펫의 화면 위치가 실제로 유지되는가(계산상 보존은 게이트가 잡고,
   AppKit 양자화까지 포함한 실측은 Verifier 기록).
2. 접힌 채 걷는 동안 창(hover 영역)이 펫 크기인가 — 옆의 다른 창을 그대로 클릭할 수 있는가.
3. 요약 위에 커서를 올려도 요약이 남고, ⌄ 로 전체가 펼쳐지며, 다시 누르면 요약으로 돌아가는가.
4. 요약 중 우클릭 메뉴를 열면 평소 선택으로 돌아가고, 메뉴의 '접기/펴기' 가 평소 선택을 바꾸는가.
5. 데이터가 없을 때(스캔 전, 로그인 전, Admin 키 없음) 요약이 0% 가 아니라 상태 문구인가.
6. 추정 모드 요약엔 ≈ 가 붙고 정확 모드엔 없는가. 긴 라벨·상태 문구가 필 안에서 `…` 로 끝나는가.
7. 걷는 펫을 잡아 끌었을 때 창이 펼쳐지더라도 잡은 자리에서 이어지는가(되돌아가지 않는가). 접힌 채
   화면 가장자리에 놓았을 때 펼친 창 전체가 화면 안에 있는가.
