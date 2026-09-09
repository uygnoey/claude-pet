# 자유 산책 — 모니터 전체 랜덤 이동, 자동 귀가 제거 (2026-09-09)

> 사용자 원문: *"야 산책 범위가 너무 좁은데? 모니터 전체를 돌아다녀도 되! 랜덤으로"*,
> *"원래 자리도 돌아가지 않아도 되고"*.
>
> 상태: **구현됨. 동작은 Reviewer 승인, 주석/docstring 정정 뒤 소스 freeze — 최종
> `claude_pet.py` SHA256 `f3810b141423ec3a9343b4b6ef76ebe1e29b7658ba9a07be13db2146f922150a`; 전체 스위트·GUI 확인은
> Verifier 기록을 본다.** Verifier 의 red 기록과 Coordinator GO(2026-09-09T07:22:34Z) 뒤에 production 을 고쳤다.
> 이 문서는 Developer 의 설계·구현 설명이고, 이 변경의 승인·검증 결과의 기준은
> `docs-design/free-roaming-verification-20260909.md`(Verifier)와 `docs-design/free-roaming-review-20260909.md`(Reviewer)다.
> (v0.21 의 조용한 동행 자체는 `quiet-companion-verification.md` / `quiet-companion-review.md`.)

## 역할과 산출물

| 역할 | 누구 | 산출물 |
|---|---|---|
| Developer | Claude Fable 5.1 (session 55c3dee4-727f-4a94-b960-66540b129014) | `claude_pet.py`, `README.md`/`README.ko.md`/`README.ja.md`/`README.es.md`, `docs-design/quiet-companion.md`(정합), 이 문서 |
| Coordinator | Codex `/root` | 역할 배정, GO/NO-GO |
| Verifier | `/root/verifier` | `tests/`(assertion·fixture·hash pin 전부), 검증 기록 |
| Reviewer | `/root/reviewer` | 리뷰 기록 |

이번 변경은 v0.21 릴리즈(HEAD `24731b0`, `claude_pet.py` `3a96147a…`) 위의 새 변경이다. 기존 게시물·서명
산출물·다른 역할의 문서·미추적 사용자 파일(`diag.py`, `release/ClaudePet.iconset/`, `release/icon_1024.png`)과
QA/trace/operator 기록은 손대지 않는다. v0.21 릴리즈 승인은 이 변경의 서명·게시로 확대되지 않는다.

## 사양 (사용자 최종 요구 6항)

1. **산책 목적지** = 펫이 지금 있는 모니터의 `visibleFrame` 안에 논리 full 창이 통째로 들어가는 안전 bounds
   전체에서 **균등 랜덤**. 집 기준 반경 160pt 제한은 없앤다. 모니터 원점이 음수여도, 작은 모니터여도 안전해야
   한다(작으면 bounds 가 뒤집혀 아무것도 하지 않는다). 모니터 사이 순간이동은 요구가 아니다.
2. **자동 귀가 없음.** 구경(approach)이든 산책(wander)이든 도착해 잠깐 보고/쉬고 나면 **그 자리에서 rest**.
   hover·메뉴·드래그·끄기·Reduce Motion·커서 진입·긴 틱 공백으로 멈춘 뒤에도 집으로 돌아가지 않고, 다음
   휴식이 끝나면 **현재 자리**에서 새로 계획한다. 수동 집(드래그로 놓은 자리)은 재시작 위치라는 뜻으로만 남고
   자동 phase 가 그리로 되돌리지 않는다.
3. 속도 55pt/s, 휴식 45~90초, 구경 최소 180초·산책 최소 300초 간격, 한 번 정한 목적지 유지, 사용자 조작 우선,
   커서 안전거리는 그대로. 랜덤 후보가 너무 가깝거나 커서·경로와 겹치면 **상한이 있는 재추첨**으로 걸러 출발
   직후 guard 취소를 줄인다. 무한 루프·무조건 즉시 재시도 없음.
4. 걷는 동안 실제 창은 접힌 crop, 구경 도착엔 요약/수동 펼침, 산책 도착은 조용한 잠깐 정지 — 그대로.
   자연 종료 뒤엔 **새 위치에서** 평소 `show_panel` 복원. `away=True` 라도 요약이 영구 래치되지 않는다.
   hover/요약 클릭으로 읽고 펼치기는 유지.
5. 자동 위치는 설정에 저장하지 않는다. 실제 드래그 위치만 저장(변경 없음).
6. 실제 crop·sprite 전역 anchor·수동 드래그·화면 끝 clamp·Reduce Motion 메뉴·사용량 계산에 회귀가 없어야 한다.

## 기존 동작과 달라지는 점 (순수 API)

| 항목 | 지금(v0.21) | 이번 |
|---|---|---|
| `ROAM_DEFAULTS` | `wander_radius: 160.0` (0 이면 산책 없음) | `wander_radius` 삭제 → `wander_enabled: True`, `wander_tries: 6`. 호환: 설정에 예전 키 `wander_radius`를 `0`으로 준 경우는 여전히 '끔'으로 읽는다(반경 값 자체는 무시) |
| phase | `rest / out / look / home` | `rest / out / look` — `home` phase 와 `_begin("home")` 제거 |
| R2 계획 | approach → wander → **집이 아니면 귀가 leg** → 재추첨 | approach → wander → 재추첨 (귀가 없음) |
| R4 산책 목적지 | `home + (cos θ, sin θ)·U(60, 160)` 을 클램프 | 최대 `wander_tries` 회: `x = U(x0, x1)`, `y = U(y0, y1)` (시도당 `rng.uniform` 정확히 2회). 거부: `|target − pos| < min_trip_px`, 커서와 `approach_stop + radius` 안, 선분 `[pos, target]` 이 커서와 `radius + cursor_margin_px` 안. 첫 통과 후보 채택, 없으면 `None` → 휴식 재추첨 |
| R6 look 종료 | 나가 있으면 귀가 leg, 아니면 그 자리 rest | 항상 그 자리 `_stop(settled=True)` |
| `home`, `set_home`, `release` | 수동 배치 갱신 | 그대로 (자동 이동은 `home` 을 바꾸지 않음) |
| `RoamOut.away` | 표시 계층이 참조 | 자동 계획(`_plan`)과 표시 복원(`RoamDisplay`)은 쓰지 않음. 어댑터 `roam_resync` 만 참조(나가 있으면 `pos` 기준으로 `release`, 집이면 `set_home`) |
| `RoamDisplay.note` D3 | `rest and not away and settled` → 복원 | **`rest and settled` → 복원** (away 무관). hover/클릭 정지(`settled=False`)는 래치 유지 |
| `RoamDisplay.mode` | `out/home` → folded | `out` → folded |

바뀌지 않는 것: R3 구경 계획(커서 방향, `stop = 150 + radius`, 최대 360pt, bounds 클램프), R5 걷기와 커서
경로 guard, R7 정지(모든 phase 에서 그 자리), R8 경계 복구, `settled` 의미, 어댑터의 crop/anchor/드래그
저장/clamp/Reduce Motion 메뉴.

## 어댑터에서 달라지는 점

거의 없다. `roam_tick`·`roam_apply_display` 는 phase 이름만 따라가고, `roam_resync` 는 나가 있으면
`release(moved=False)`(자동 위치를 집으로 만들지 않음), 집이면 `set_home` — 그대로다. 레이아웃 고정
(`roam_layout`)은 첫 자동 이동부터 수동 드래그까지 유지된다: 창 전체는 항상 bounds 안이라 화면을 벗어나지
않지만, 자동으로 쉬는 자리에서 필이 화면 중앙선 기준 반대편에 붙어 보일 수 있다. 플립하면 sprite 가 창 안에서
옮겨 앉으므로 하지 않는다 — 알려진 미관상 한계.

## Verifier 에게 — 갈라야 할 경쟁 구현 (산문 제안)

1. 산책 목적지가 집 반경 안(기존) vs 현재 모니터 bounds 전체(정답): `uniform → low` stub 로 bounds 좌하 구석,
   음수 원점 bounds(예 `(-1700, 100, -300, 1100)`)에서 목적지가 bounds 안이고 집 반경 밖.
2. look 종료 뒤 `home` phase 가 생기는가(기존) vs 그 자리 rest·`settled=True`·pos 불변(정답).
3. hold 로 멈춘 뒤 다음 계획의 출발점이 현재 pos 인가(집이 아니라).
4. D3': `away=True` 에서 `rest` + `settled=True` → 요약 해제, `settled=False` → 유지.
5. 재추첨 상한: 모든 후보가 거부되는 stub 에서 `uniform` 호출이 정확히 `2 × wander_tries`, 결과 `None`,
   즉시 재시도 없이 `next_at` 재추첨.
6. 후보 guard: 첫 후보가 커서 경로 위, 둘째가 통과 → 둘째 채택(호출 4회).
7. 회귀: 구경 목적지/guard/hold/gap/R8/드래그 저장/Reduce Motion 메뉴의 기존 게이트 그대로 통과.

## 구현 결과 (Developer)

- `claude_pet.py`: `ROAM_DEFAULTS`(`wander_radius` → `wander_enabled`/`wander_tries`), `Roamer._begin`(home leg 제거),
  `_wander_on`(신규), `_plan_wander`(사각형 균등 샘플 + 거부 + 상한 재추첨), `_plan`(귀가 분기 제거), look 종료
  (`_stop(settled=True)`), 걷기 leg(`out` 만), `RoamDisplay.note`/`mode`(D1·D3·`home` 분기). 어댑터 코드는 변경 없음.
- 주석/docstring 정정(동작 변경 없음): `RoamOut.away` 주석(자동 계획·표시 복원 미사용, `roam_resync` 만 참조), `Roamer`
  docstring(걷는 leg 는 `out` 하나), `RoamDisplay` docstring(도착 자리에서의 구경·자연 완료 휴식). 정정 전(`f61851d0…`)과
  후(`f3810b14…`)를 `compile(..., optimize=2)` 로 비교하면 코드·이름·상수가 같고 class `__firstlineno__` 상수만 한 줄씩
  밀린다(주석 한 줄 추가) — Developer 자체 확인이며 §5 기록은 아니다.
- README 네 언어의 동작 절(한 번 다가와 바라보기 / 화면 아무 데나 랜덤 산책 뒤 도착지에서 휴식, 제자리로 돌아오지 않음),
  `docs-design/quiet-companion.md` §1·§3·§4·§9.1 정합.
- 게이트 결과와 수치는 Developer 가 쓰지 않는 독립 기록이 기준이다: `docs-design/free-roaming-verification-20260909.md`
  (baseline RED, "Focused free-roaming run", "Focused companion regression run", native compact arrival/no-return,
  in-memory rival execution; 각 항목에 command·source SHA·UTC 창이 있다) 와 `docs-design/free-roaming-review-20260909.md`.
  Developer 의 로컬 실행은 위 기록과 같은 명령으로 같은 결과를 봤다는 확인일 뿐 수치 근거로 쓰지 않는다.
  `tests/test_v021_release_contract.py` 의 소스 해시 핀은 Verifier 소유이며 최종 SHA 로 재고정된다.
- 이번 변경의 commit·버전·릴리즈·서명·push·설치는 이 과제 범위가 아니다.
