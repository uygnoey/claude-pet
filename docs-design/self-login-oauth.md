# 장기 과제: ClaudePet 자체 OAuth 로그인

> 목표: Claude Code 설치 없이도 ClaudePet이 **정확 모드**(서버 계산 사용량)를
> 동작시킬 수 있도록, 앱이 스스로 Anthropic OAuth 로그인을 수행해 토큰을
> 발급·갱신·저장한다.
>
> 상태: **설계 단계 (미구현)**. 별도 세션에서 구현 권장.
> 관련 메모리: `self-login-oauth`, `claude-pet-oauth-usage-schema`.

---

## 1. 배경 — 왜 필요한가

ClaudePet은 "Claude Code 사용량 HUD"라서 데이터가 전적으로 Claude Code에서 나온다:

| 모드 | 데이터 출처 | Claude Code 필요? |
|---|---|---|
| 로그 추정 | `~/.claude/projects/**/*.jsonl` | ✅ |
| 정확 모드 | 키체인 `Claude Code-credentials` OAuth 토큰 → `/api/oauth/usage` | ✅ |
| API 모드 | Admin API 키 → `/v1/organizations/cost_report` | ❌ (조직 Admin 키만) |

v0.17에서 "Claude Code가 없으면 설치·로그인 안내"를 붙였지만, 여전히 **Claude
Code 설치가 전제**다. 이 과제는 그 전제를 없애는 것 — 앱이 직접 로그인해 토큰을
얻으면, 개인 구독자는 Claude Code 없이도 **정확 모드**를 쓸 수 있다.

**한계(반드시 명시):** 로그 추정 모드는 `~/.claude/projects` 로그가 있어야 하므로,
Claude Code를 아예 안 쓰는 사용자에게는 **정확 모드만** 제공된다(세션·주간·모델
게이지는 서버 값으로 채워지므로 실사용엔 충분).

---

## 2. 실제 OAuth 파라미터 (Claude Code 2.1.218에서 확인)

> 아래 값은 설치된 `claude` 바이너리 문자열과 공개 클라이언트 메타데이터
> 엔드포인트에서 **직접 확인**한 것이다. 추측 아님. 다만 Anthropic이 언제든
> 바꿀 수 있으므로, 구현 전 재확인할 것.

### 2.1 클라이언트 메타데이터 (공개)
`GET https://claude.ai/oauth/claude-code-client-metadata` →
```json
{
  "client_id": "https://claude.ai/oauth/claude-code-client-metadata",
  "client_name": "Claude Code",
  "client_uri": "https://claude.ai",
  "redirect_uris": ["http://localhost/callback", "http://127.0.0.1/callback"],
  "grant_types": ["authorization_code", "refresh_token"],
  "response_types": ["code"],
  "token_endpoint_auth_method": "none"
}
```
- **`client_id` 자체가 URL**이다(RFC 7591 스타일 URL-기반 클라이언트 식별). 이
  URL 문자열을 그대로 `client_id` 파라미터로 쓴다.
- **`token_endpoint_auth_method: none`** → 퍼블릭 클라이언트 → **PKCE 필수**
  (클라이언트 시크릿 없음).
- **redirect_uri는 루프백**(`http://localhost/callback` / `http://127.0.0.1/callback`).
  포트는 명시되지 않았으므로 루프백 임의 포트 방식(RFC 8252 §7.3)으로 본다 —
  앱이 로컬에 임시 HTTP 서버를 띄우고 그 포트로 콜백을 받는다.

### 2.2 엔드포인트
| 용도 | URL | 비고 |
|---|---|---|
| Authorize | `https://platform.claude.com/oauth/authorize` | 브라우저로 연다 |
| Token | `https://platform.claude.com/v1/oauth/token` | code→token, refresh 둘 다 |
| Usage(정확 모드) | `https://api.anthropic.com/api/oauth/usage` | 기존 코드가 이미 사용 |

> 참고: `claude.ai/oauth/authorize` 는 403을 반환한다. 현재 플로우의 authorize
> 호스트는 `platform.claude.com` 로 보인다. **구현 시 authorize 응답을 실제로
> 받아 최종 확인**할 것.

### 2.3 스코프 (현재 토큰이 보유)
```
user:profile
user:inference
user:sessions:claude_code
user:file_upload
user:mcp_servers
```
정확 모드(사용량 조회)에 최소로 무엇이 필요한지는 미확인. 최소권한 원칙상
`user:profile` + 사용량 관련 스코프만 요청해보고, 거부되면 Claude Code와 동일한
전체 세트로 맞춘다. `user:sessions:claude_code` 가 `/oauth/usage` 게이트일 가능성 높음.

### 2.4 사용량 요청 헤더 (기존 `fetch_exact_usage` 참고)
```
Authorization: Bearer <accessToken>
anthropic-beta: oauth-2025-04-20
User-Agent: claude-code/<ver>
Accept: application/json
```

---

## 3. 토큰 저장 스키마 (키체인/파일 공통)

Claude Code가 키체인 `Claude Code-credentials` 에 넣는 JSON (키만, 비밀값 제외):
```
claudeAiOauth:
  accessToken:            <str ~108자>
  refreshToken:           <str ~108자>
  expiresAt:              <ms epoch>       예 1784803295679
  refreshTokenExpiresAt:  <ms epoch>
  scopes:                 [5개, §2.3]
  subscriptionType:       "max" | "pro" | ...
  rateLimitTier:          "default_claude_max_20x" | ...
```

**저장 위치 결정 (택1):**

- **A. 앱 전용 키체인 항목** `ClaudePet-credentials` (권장)
  - 장점: Claude Code 항목을 건드리지 않음(오염/충돌 없음). 완전 삭제 시 우리
    것만 지우면 됨.
  - 단점: 사용자가 Claude Code로도 로그인하면 토큰이 두 벌. 무방.
- **B. Claude Code 항목 재사용** `Claude Code-credentials`
  - 장점: Claude Code와 상호운용.
  - 단점: 우리가 남의 항목에 쓰기 → 위험(파티션 ACL 문제, Claude Code가 덮어씀).
    **비권장.**

→ **A 채택.** 읽기 우선순위: `ClaudePet-credentials`(자체 로그인) → 기존 파일
(`~/.claude/.credentials.json`) → `Claude Code-credentials`(있으면 재사용).
이러면 Claude Code가 있으면 그걸 쓰고, 없으면 자체 로그인 토큰을 쓴다.

---

## 4. 로그인 플로우 (Authorization Code + PKCE + 루프백)

RFC 8252(Native App) 표준 흐름:

```
1. code_verifier = base64url(random 32~64 bytes)
   code_challenge = base64url(sha256(code_verifier))
   state          = base64url(random 16 bytes)     # CSRF 방지

2. 루프백 서버 기동: 127.0.0.1 의 임의 빈 포트에 최소 HTTP 서버.
   redirect_uri = http://127.0.0.1:<port>/callback
   (메타데이터가 포트 미지정 루프백을 허용한다는 전제 — 실제로 확인 필요.
    만약 고정 포트만 허용하면 그 포트를 점유하고, 사용 중이면 안내.)

3. 브라우저 오픈:
   https://platform.claude.com/oauth/authorize
     ?response_type=code
     &client_id=https://claude.ai/oauth/claude-code-client-metadata   (URL-encode)
     &redirect_uri=http://127.0.0.1:<port>/callback
     &scope=<공백구분 스코프>
     &state=<state>
     &code_challenge=<challenge>
     &code_challenge_method=S256

4. 사용자가 브라우저에서 로그인/동의 → 콜백:
   GET http://127.0.0.1:<port>/callback?code=<code>&state=<state>
   - state 일치 검증(불일치 시 중단). 사용자에게 "로그인 완료, 창을 닫아도 됩니다" HTML 응답.

5. 토큰 교환 (PKCE):
   POST https://platform.claude.com/v1/oauth/token
   Content-Type: application/x-www-form-urlencoded
     grant_type=authorization_code
     code=<code>
     redirect_uri=http://127.0.0.1:<port>/callback
     client_id=https://claude.ai/oauth/claude-code-client-metadata
     code_verifier=<verifier>
   → { access_token, refresh_token, expires_in, scope, ... }
     (응답 필드명이 snake_case일 수 있음 — 저장 시 §3 스키마로 매핑)

6. §3 스키마로 키체인(ClaudePet-credentials)에 저장. expiresAt = now + expires_in.
```

### 4.1 토큰 갱신 (자동, 무인)
`accessToken` 만료(≈ expiresAt) 임박 시:
```
POST https://platform.claude.com/v1/oauth/token
  grant_type=refresh_token
  refresh_token=<refreshToken>
  client_id=https://claude.ai/oauth/claude-code-client-metadata
→ 새 access(+가끔 새 refresh) 저장.
```
- `refreshTokenExpiresAt` 지나면 refresh도 만료 → 재로그인 안내(온보딩 'login'과 동일 UI).
- 현재 `_read_oauth_token(force=True)` 는 401 시 재조회만 한다. 여기에 **refresh
  시도**를 먼저 끼워야 한다: 401 → refresh 성공하면 새 토큰, 실패하면 로그인 필요.

---

## 5. 앱 통합 지점 (현재 코드 기준)

| 무엇 | 어디 | 변경 |
|---|---|---|
| 토큰 읽기 | `_read_oauth_token()` | 우선순위에 `ClaudePet-credentials` 추가, 만료 시 refresh 로직 |
| 토큰 갱신 | 신규 `_oauth_refresh(refresh_token)` | §4.1 |
| 로그인 개시 | 신규 `start_oauth_login()` | §4, 루프백 서버 + 브라우저 |
| 루프백 서버 | 신규, `http.server` 최소 구현 | 데몬 스레드, 1회 콜백 후 종료, 타임아웃(예 3분) |
| 온보딩 분기 | `compute_onboard_state()` | 'login' 액션을 **자체 로그인**으로 전환(설치 유도 대신) |
| 메뉴/UX | `Handler.loginClaude_` 옆에 `Handler.oauthLogin_` | "🔑 로그인" 을 자체 로그인으로 |
| 저장 | 신규 `_write_credentials()` | 네이티브 Security API로 키체인 add/update |

**중요:** 정확 모드 표시/계산 로직(`fetch_exact_usage`, `/oauth/usage` 파싱,
게이지 렌더)은 **그대로 재사용**된다. 이 과제는 "토큰을 어디서 얻느냐"만 바꾼다.

---

## 6. UX 설계

- Claude Code 없음 + 자체 로그인도 안 됨 →
  온보딩 필에 **두 선택지**: "🔑 ClaudePet으로 로그인" (자체) / "⬇︎ Claude Code 설치"
  (기존). 대부분은 자체 로그인이 빠름.
- 로그인 클릭 → 기본 브라우저 열림 → 완료 시 자동으로 정확 모드 전환(재시작 불필요,
  기존 refresh 주기가 새 토큰을 주워감).
- refresh 만료 → 조용히 재로그인 안내(스팸 없이 1회).
- 완전 삭제(우클릭 → 완전 삭제)에 `ClaudePet-credentials` 키체인 항목 제거 추가.

---

## 7. 보안 고려사항

- **PKCE 필수**(퍼블릭 클라이언트). code_verifier는 메모리에만, 로그 금지.
- **state** 로 CSRF 방지, 루프백 콜백에서 검증.
- 루프백 서버는 `127.0.0.1` 에만 바인드(외부 노출 금지), 콜백 1회 처리 후 즉시 종료,
  타임아웃. 받은 code는 URL 쿼리로 오므로 접근 로그에 남지 않게 주의.
- 토큰은 키체인에 저장(파일 평문 저장 지양). 네이티브 Security API 사용
  (기존 `_keychain_token_native` 패턴 확장 — add/update).
- `accessToken`/`refreshToken` 을 디버그 로그(`CLAUDE_PET_DEBUG`)에 절대 남기지 말 것.
  현재 `_dbg` 는 `bool(tok)` 만 남기므로 그 원칙 유지.

---

## 8. 리스크 / 미확인 항목 (구현 전 반드시 검증)

1. **루프백 포트 정책** — 메타데이터가 `http://localhost/callback`(포트 없음)만
   명시. 임의 포트 허용인지, 고정 포트 요구인지 authorize 실서버 응답으로 확인.
   고정이면 그 포트 점유 전략 필요.
2. **authorize 호스트** — `platform.claude.com` vs `claude.ai`. 실제 302/폼 응답 확인.
3. **토큰 응답 필드명/구조** — snake_case 여부, `subscriptionType`/`rateLimitTier`
   포함 여부(정확 모드 라벨에 쓰임).
4. **약관** — 이 client_id/엔드포인트는 Claude Code 전용이다. 3자 앱이 같은
   client_id로 로그인하는 것이 Anthropic 정책상 허용되는지 **확인 필요**. 안 되면
   자체 클라이언트 등록 경로를 찾거나, 이 과제를 보류.
5. **엔드포인트 변경** — Anthropic이 URL/스킴을 바꾸면 깨진다. 하드코딩 최소화,
   실패 시 명확한 안내.

> **8-4가 이 과제의 최대 관문이다.** 기술적으로는 가능하지만, 정책적으로 허용되지
> 않으면 진행하면 안 된다. 구현 착수 전에 이 항목부터 확인할 것.

---

## 9. 마일스톤

1. **탐색/검증**: §8 항목 전부 실측(로컬 스파이크). 특히 8-4 정책 확인.
2. **PKCE + 루프백 로그인** 프로토타입: 토큰 획득까지 CLI 스크립트로.
3. **키체인 저장/읽기** (`ClaudePet-credentials`) + `_read_oauth_token` 통합.
4. **자동 refresh** + 401 처리.
5. **UX**: 온보딩 분기·메뉴·완전 삭제 연동.
6. **검증**: 새 머신 시뮬레이션, 토큰 만료/갱신/재로그인, 스코프 최소화.
