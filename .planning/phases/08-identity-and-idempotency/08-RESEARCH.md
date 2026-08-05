# Phase 8: 신원 검증과 멱등성 - Research

**Researched:** 2026-08-06
**Domain:** HMAC 서명 쿠키 · 세션 단일 쓰기 주체 안의 멱등성 검사 · 사건 기록 형식 판 올리기 · 다인원/동시 요청 테스트
**Confidence:** MEDIUM — 표준 스택(HMAC/pytest/httpx)은 CITED 수준, 이 저장소에 맞는 정확한 통합 지점은 코드를 직접 읽어 VERIFIED로 확인했다. 가장 신뢰도가 낮은 부분은 "이 단계의 사건 형식 판 올리기가 CheckResolved 하나에 그치지 않을 수 있다"는 새 발견(§ Pitfall 1)이다 — CONTEXT.md의 D-12/D-13이 명시한 범위보다 넓어질 가능성이 있어 계획 단계에서 사용자 확인이 필요하다.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**신원 증명**
- **D-01:** 서명한 쿠키(HMAC)로 간다. 서버가 비밀 열쇠 하나로 `gptrpg_character` 쿠키에 서명하고, 한 글자라도 변조되면 검증에서 떨어진다. 서버는 상태를 들지 않는다. 지금은 서명 없는 평문 JSON이다(`src/gptrpg/web/routes_characters.py:156-163`). 탈락한 대안: 서버측 세션 저장소 + 불투명 토큰. **알려진 한계(정직하게 기록):** 서명 쿠키는 개별 무효화가 즉시 되지 않는다 — 이 마일스톤에서 필요하지 않다고 판단, M1의 실제 계정 체계에서 재검토. Reversibility: reversible.
- **D-02:** 비밀 열쇠가 없으면 서버가 만들어 파일에 저장하고 다음 실행부터 재사용한다. 준비 없이 그냥 켜도 돌고, 세션 중간에 서버를 껐다 켜도 아무도 쫓겨나지 않는다. 열쇠를 밖에서 주입하는 경로(환경변수 등)도 함께 연다 — 밖에서 준 열쇠가 있으면 그것이 우선이다. 열쇠 파일은 반드시 `.gitignore`에 들어간다.
- **D-03:** 쪽지에 「브라우저 식별자」와 「고른 캐릭터」를 따로 적는다 — 사람과 캐릭터를 분리한다. 지금 코드는 `player_id === character_id`로 둘을 같은 값으로 쓰고 있다(`frontend/src/screens/SessionScreen.tsx:113`, D-42). 지금은 여전히 한 사람이 한 캐릭터다. Reversibility: one-way — 사건 기록에 남는 칸이다.
- **D-04:** 거부는 서버 기록(로그)에만 남긴다. 게임 사건 기록은 「게임에서 실제로 일어난 일」만 담는다. 화면에는 안내를 띄운다. QUAL-05에 따라 안내 문구·로그 어느 쪽에도 쿠키 값·비밀 열쇠·서명이 실려 나가지 않는다.

**캐릭터 점유**
- **D-05:** 먼저 잡은 사람이 임자다. 이미 잡힌 캐릭터를 다른 브라우저가 고르려 하면 거부하고, 그 사람은 다른 캐릭터를 고른다. 본인 재접속은 서명 쿠키로 확인되므로 그대로 통과한다 — 자기 캐릭터에 다시 들어오는 것은 점유 충돌이 아니다.
- **D-06:** 점유를 게임 사건으로 기록한다. 서버를 껐다 켜도 기록을 다시 읽으면 점유가 복원된다. 새 사건 종류가 하나 늘어난다 → `EVENT_SCHEMA_VERSION`을 올린다(D-09와 같은 커밋에서). `reducer.py`의 분기를 같은 커밋에 반드시 동반한다. Reversibility: one-way.
- **D-07:** 한 번 잡으면 놓을 수 없다. 놓기 경로를 만들지 않는다. 사용자가 대가를 알고 선택했다.

**서사 실패와 재시도(멱등성)**
- **D-08:** 주사위 결과를 먼저 보여주고, 그 아래 「이야기를 못 썼다」 안내를 붙인다. 이미 일어난 일을 버리지 않는다. 지금은 `routes_actions.py:439-446`이 502를 던져 이미 기록된 판정 결과를 통째로 버린다. 응답에서 「주사위 굴림 실패」와 「서사 생성 실패」가 구분되어야 한다(TRUST-06).
- **D-09:** 다시 시도를 누르면 이야기만 다시 쓴다. 주사위는 이미 굴렀으니 그대로 두고 AI에게 서사만 다시 부탁한다. AI가 자동으로 한 번 더 써 보는 것(SAFE-04)은 Phase 10의 몫 — 이 단계는 사람이 다시 눌렀을 때의 동작만 정한다.
- **D-10:** 멱등성 열쇠 = 요청에 이미 들어 있는 선언 번호(`declare_seq`). 서버는 사건 기록에서 「이 선언은 이미 확인됐다」를 확인한다. 브라우저가 새로 만들어 보내는 요청 번호를 도입하지 않는다. `ConfirmRequest.declare_seq`가 이미 필드로 있다(`routes_actions.py:246`). 이미 확인된 선언에 대해 **다른 무브·능력치로** 들어온 확인도 거부 대상이다.
- **D-11:** 신원·점유·멱등성 검사는 라우트 계층과 `SessionActor` 양쪽에 둔다. 라우트 검사만으로는 우회 경로가 남는다(TRUST-03이 명시). `SessionActor._validate_caused_by`(`actor.py:366-376`)는 지금 「그 순번이 존재하는가」만 본다. 「그 선언의 주인이 지금 확인하는 사람과 같은가」와 「이미 확인됐는가」가 여기에 붙는다.

**기록 형식과 옛 기록**
- **D-12:** 판정 기록(`CheckResolved`)에 「사람」과 「캐릭터」를 둘 다 필수 칸으로 넣는다. Reversibility: one-way.
- **D-13:** 옛 형식(번호 2)으로 쓰인 기록을 읽는 경로를 낸다. `.gptrpg/events.db`에 세션1 기록 895건이 실제로 살아 있다(판정 38 · 선언 47 · 확인 39 · 서사 682 · 시계 4 · AI 호출 85, 전부 형식 번호 2). 전례: 형식 1→2 때 `counts_as_failure`를 필수 칸으로 올리며 `rules_core/reducer.py:98-99`에 옛 판 해석 경로를 냈다.
- **D-14:** 점유 기록이 없는 옛 세션은 다시보기만 되고 새 행동은 못 보낸다. ⚠️ 구현 시 반드시 구분: 「사건이 아예 없는 세션」(새 세션, 캐릭터를 잡을 수 있어야 함) vs 「사건은 있는데 점유 사건만 없는 세션」(옛 세션, 다시보기 전용). 같게 다루면 아무도 새 세션을 시작하지 못한다.

### Claude's Discretion

- **QUAL-04(입력 길이 상한):** `routes_actions.py`에는 이미 상한이 있다(`MAX_RAW_TEXT_LEN=2000`, `MAX_ID_LEN=64`). `routes_characters.py`의 `SelectCharacterRequest.character_id`에는 상한이 없다 — API 경계 전수 훑기 대상.
- **QUAL-05(예외 관례):** 예외 문구에 쿠키 값·비밀 열쇠·서명·API 키가 실려 나가지 않는다.
- **TEST-01(테스트 픽스처):** `"p1"` 상수가 13개 파일 44군데에 있다. 실제 캐릭터 여러 명으로 도는 픽스처로 바꾸고, 각자의 발화에 각자의 이름이 붙는지 단언한다. 전면 교체 vs 공유 픽스처 점진 교체는 계획 단계 판단.
- **TEST-02(겹치는 요청):** 같은 선언에 대한 확인이 동시에 두 번 들어오는 상황, 두 브라우저가 같은 캐릭터를 동시에 고르는 상황을 재현한다.
- HTTP 상태 코드 선택, 함수·모듈 이름, 서명 알고리즘 세부.

### Deferred Ideas (OUT OF SCOPE)

- **캐릭터 만들기(D22)** — Phase 8 범위 아님, Phase 12.1로 배정됨(2026-08-06 로드맵 변경).
- **서명 쿠키의 개별 무효화** — M1의 실제 계정 체계에서 재검토.
- **한 사람이 여러 캐릭터 조종** — D-03이 자리만 열어 두고, 기능은 만들지 않는다. 솔로 모드는 M2.
- **캐릭터 선택 화면의 실시간 갱신** — Phase 16(FE-03).
- **AI가 서사를 자동으로 다시 생성** — Phase 10(SAFE-04). D-09는 사람이 다시 눌렀을 때만 다룬다.
- **세션1 기록 재생 회귀 픽스처** — Phase 12(TEST-04). 이 단계는 읽는 길만 연다.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TRUST-01 | 브라우저가 실제로 고른 캐릭터가 위조할 수 없는 형태로 보관된다 | § HMAC 서명 쿠키 구현(코드 예시), § Standard Stack |
| TRUST-02 | 선언 시 서버가 요청의 캐릭터를 쿠키의 캐릭터와 대조하고 다르면 거부한다 | § 신원 대조 지점(라우트 1차선), § HTTP 상태 코드 권고 |
| TRUST-03 | 확인 요청의 주인이 그 선언의 주인과 같은지 SessionActor 안에서 검증된다 | § Pitfall 1(핵심 발견), § 멱등성·소유권 검증 설계, § 액터 계층 코드 예시 |
| TRUST-04 | 판정 결과 기록에 「누구의 판정인가」가 필수 항목으로 남는다 | § 사건 형식 판 올리기(D-12/D-13 전례 재현), § CheckResolved 확장안 |
| TRUST-05 | 같은 선언에 대한 확인이 두 번 처리되지 않는다 | § 멱등성·소유권 검증 설계, § GameState 확장안 |
| TRUST-06 | 「주사위 실패」와 「서사 실패」가 응답에서 구분된다 | § 멱등성·소유권 검증 설계(캐시된 판정 재사용 흐름) |
| QUAL-04 | API 경계의 입력 길이 상한이 빠짐없이 걸린다 | § API 경계 전수 훑기 |
| QUAL-05 | 예외가 프로젝트 관례를 따르고 자격 증명이 실려 나가지 않는다 | § 예외 문구 위생, § CommandRejected 확장 패턴 |
| TEST-01 | 실제 캐릭터 여러 명으로 도는 테스트, 각자의 발화에 각자의 이름이 붙는지 단언 | § 다중 캐릭터 픽스처 설계 |
| TEST-02 | 여러 요청이 겹쳐 들어오는 상황이 테스트로 재현된다 | § 동시성 재현 테스트 패턴(actor-level, HTTP-level) |
</phase_requirements>

## Summary

이 단계는 새 게임 기능을 만들지 않고, 이미 있는 세 경계(신원·점유·재시도)에 검사를 채워 넣는다. 코드베이스를 직접 읽어 확인한 결과, 구현에 필요한 재료는 대부분 이미 자리에 있다 — `SessionActor`의 단일 쓰기 직렬화 지점(`actor.py:201-602`), `_prepare_*` 검증 분기 표(`actor.py:349-364`), `EVENT_SCHEMA_VERSION` 판 올리기 전례(`reducer.py:98-99`), `validate_session_id`의 `Depends()` 패턴(`app.py:49-61`)이 전부 그대로 재사용 가능하다. 새로 필요한 것은 (1) HMAC 서명/검증 함수 한 쌍, (2) 점유를 기록하는 새 사건 종류 하나, (3) 선언 소유권을 액터가 재구성 가능한 형태로 지속시키는 스키마 확장, (4) 이미 확인된 선언을 감지해 판정을 재사용하는 상태 필드 하나다.

**가장 중요한 발견(HIGH 확신, 코드 직접 확인):** `DeclareAction`/`ActionDeclared`와 `ConfirmAction`/`ActionConfirmed`는 지금 `character_id`를 전혀 담지 않는다 — 오직 `player_id`(오늘은 `character_id`와 같은 값)만 있다(`actor.py:64-70,72-82`, `schema.py:82-88,90-103`). 라우트가 받는 `character_id`는 AI 문맥 조립에만 쓰이고 `actor.submit(...)`에는 전달되지 않는다(`routes_actions.py:165-167,305-317`로 검증). `SessionActor.state`는 매번 저장된 사건에서 **처음부터 다시 접혀** 만들어진다(`actor.py:219-229` 주석 — "저장소에 이미 쌓인 사건을 그대로 다시 접어 시작한다"). 따라서 TRUST-03("확인의 주인 == 선언의 주인")을 서버 재시작에도 살아남게 검증하려면, 그 소유권 정보가 **사건 자체에 저장**되어야 한다 — 액터 안의 임시 변수로는 재시작 후 사라진다(D-02가 명시한 "서버를 껐다 켜도 아무도 쫓겨나지 않는다"는 전제와 정면으로 충돌). CONTEXT.md의 D-12/D-13은 `CheckResolved`만 명시적으로 언급하지만, 이 발견에 따르면 **`ActionDeclared`/`ActionConfirmed`도 같은 `EVENT_SCHEMA_VERSION` 판 올리기에 `character_id`(및 점유 확인용 `browser_id`) 칸을 함께 받아야** TRUST-02/03이 실제로 성립한다. 자세한 근거와 대안은 § Pitfall 1 참조 — 계획 단계에서 사용자 확인이 필요한 항목이다.

**Primary recommendation:** 쿠키 서명은 `hmac`+`hashlib`(stdlib, 새 의존성 없음)로 직접 구현한다. 점유·소유권·멱등성 검사는 전부 `SessionActor._prepare_*`의 확장으로 넣고(라우트 계층은 빠른 실패용 1차선), `EVENT_SCHEMA_VERSION` 4→5 판 올리기 하나로 「점유 사건 신설 + `ActionDeclared`/`ActionConfirmed`/`CheckResolved`에 `character_id`(및 `CheckResolved`에 `person_id`) 필수/조건부 칸 추가」를 한 커밋에 묶는다.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 쿠키 서명·검증(HMAC) | API / Backend (`web/routes_characters.py` + 새 서명 모듈) | — | 쿠키는 브라우저가 들고 있지만 서명·검증 로직은 서버 비밀에 의존하므로 전적으로 백엔드 책임 |
| 요청 캐릭터 ↔ 쿠키 캐릭터 대조(TRUST-02) | API / Backend (`routes_actions.py` 진입부) | — | 라우트가 신뢰할 수 없는 HTTP 요청을 처음 받는 자리(기존 `MAX_RAW_TEXT_LEN` 관례와 동일 층) |
| 소유권·멱등성 최종 검증(TRUST-03/05) | Database/State 계층에 준하는 세션 단일 쓰기 주체(`session_actor/actor.py`) | API / Backend(1차 빠른 실패) | 이 프로젝트에서 "상태의 유일한 진실"은 사건 기록이고, 액터가 그 기록에 대한 유일한 쓰기 창구다 — 두 계층 방어는 이미 결정(D-11) |
| 점유 상태 지속(D-06) | Database/Storage(`event_log`) | 세션 액터의 `GameState`(파생 캐시) | append-only 사건 기록이 진실이고 `GameState`는 그 파생 재구성일 뿐(D3, 되돌릴 수 없음) |
| 캐릭터 목록 표시 | Browser / Client (`frontend/src/screens/SessionScreen.tsx`) | API(목록 제공) | 화면 배치·안내 문구는 Phase 16 영역 — 이 단계는 응답 모양만 바뀐다 |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `hmac` (Python stdlib) | Python 3.11+ 내장 | 쿠키 서명 생성·검증 | 이미 프로젝트가 요구하는 `requires-python = ">=3.11"`에 포함, 새 의존성 없음. `hmac.compare_digest()`가 타이밍 공격에 안전한 비교를 표준으로 제공한다 [CITED: docs.python.org/3/library/hmac.html] |
| `hashlib.sha256` (Python stdlib) | Python 3.11+ 내장 | HMAC의 digestmod | Python 3.8부터 `digestmod`가 필수 인자이고, 문서가 sha256/sha512 계열을 권장한다 [CITED: docs.python.org/3/library/hmac.html] |
| `secrets` (Python stdlib) | Python 3.11+ 내장 | 서버 비밀 열쇠 생성(`secrets.token_bytes`), 브라우저 식별자 생성(`secrets.token_urlsafe`) | 이미 `pyproject.toml`의 `ruff` 규칙이 `rules_core` 층에서만 `secrets` import를 금지한다(`web` 층은 허용) [VERIFIED: pyproject.toml:64 — `"secrets".msg = "규칙 코어는 무작위성을 직접 가져다 쓸 수 없다..."`, `per-file-ignores`에 `src/gptrpg/web/*` 포함(줄 77)] |
| `pytest-asyncio` | 이미 설치(`>=1.4.0`) | 액터 동시성 재현 테스트(TEST-02) | `asyncio_mode = "auto"`가 이미 `pyproject.toml`에 있다 [VERIFIED: pyproject.toml:51-53] |
| `httpx` | 이미 설치(`0.28.1`, uv.lock 확인) | HTTP 계층 동시 요청 재현 테스트(TEST-02) | `httpx.AsyncClient` + `ASGITransport`가 0.27+부터 정식 지원되어 새 의존성 없이 비동기 동시 POST를 앱에 직접 보낼 수 있다 [VERIFIED: uv.lock:721-723] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `itsdangerous` | 2.2.0(PyPI 최신, 확인함) | `URLSafeTimedSerializer`로 서명+만료+JSON 인코딩을 한 번에 처리 | **이번 단계에는 권장하지 않음** — stdlib만으로 충분하고, 지금 쿠키는 만료를 브라우저 `Max-Age`(14일, `COOKIE_MAX_AGE_S`)에 이미 위임하고 있어 서버측 타임스탬프 만료가 필수는 아니다. 서명 대상이 여러 종류로 늘거나(예: 초대 링크 토큰, M1) 알고리즘 롤오버가 필요해지면 그때 재고려 |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| stdlib `hmac`+`hashlib` 직접 구현 | `itsdangerous.URLSafeTimedSerializer` | itsdangerous는 Flask/Starlette 생태계의 사실상 표준이고 오탐 위험이 적지만(Pallets 프로젝트, 의존성 0개), 이번 프로젝트에 새 의존성을 추가하는 대가가 있다. 서명 대상이 단순 JSON 하나뿐이라 stdlib로 충분 |
| SessionActor 상태(`GameState`)에 소유권/멱등성 캐시 필드 추가 | 매 확인 요청마다 `store.read_events()`로 전체 사건을 다시 스캔 | 스캔 방식은 스키마 변경이 필요 없지만, 세션이 길어질수록(895건 실사례) O(n) 스캔이 매 확인마다 반복된다 — `GameState`는 이미 `rebuild_state`가 매 액터 생성 시 한 번 접어 두므로, 접는 시점에 파생 필드를 추가하는 편이 기존 패턴(`fails_since_clock` 등)과 일치 |

**Installation:** 새 패키지 설치 불필요(stdlib만 사용). `itsdangerous`를 채택하기로 하면: `uv add itsdangerous`

**Version verification:** `pip index versions itsdangerous` → `2.2.0`(2026-08-06 확인, PyPI 공식 registry) [VERIFIED: pypi.org/pypi/itsdangerous/json 조회]. `hmac`/`hashlib`/`secrets`는 stdlib이라 별도 버전 확인 대상이 아니다.

## Package Legitimacy Audit

> 이 단계는 stdlib만으로 구현 가능하므로 **필수 신규 설치 패키지가 없다.** 아래는 대안으로 검토했던 `itsdangerous`에 대한 감사 결과다(채택 시에만 적용).

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| itsdangerous | pypi | 최신판 2024-04-16 릴리스(패키지 자체는 2010년부터 존속하는 Pallets 프로젝트) | 확인 불가(`weeklyDownloads: null`, 조회 도구 한계) | github.com/pallets/itsdangerous/ | SUS(사유: `unknown-downloads`만) | **보류 — 이번 단계에서 미채택.** 채택 시 `checkpoint:human-verify` 필요 |

**패키지 레짐 검사 명령(재현 가능):** `gsd-tools query package-legitimacy check --ecosystem pypi itsdangerous` → `verdict: SUS`, `reasons: ["unknown-downloads"]`. 이 SUS는 실제 신용도 문제가 아니라 조회 도구가 다운로드 수 API에 접근하지 못한 결과로 보인다(GitHub 저장소 존재, Pallets 공식 조직, Flask/Starlette가 내부적으로 쓰는 잘 알려진 패키지) — 그럼에도 프로토콜상 SUS는 미채택 판단과 무관하게 `checkpoint:human-verify`를 요구하므로, 채택하지 않기로 한 이번 권고와 별개로 기록해 둔다.

**Packages removed due to [SLOP] verdict:** 없음
**Packages flagged as suspicious [SUS]:** itsdangerous(대안으로만 검토, 미채택)

## Architecture Patterns

### System Architecture Diagram

```
[Browser A]                              [Browser B]
    |  POST /select-character                 |  POST /select-character
    |  {character_id: "bram"}                  |  {character_id: "bram"}  (동시)
    v                                          v
+-----------------------------------------------------------------+
|  routes_characters.select_character()  (라우트 1차선)            |
|  1) character_id가 알려진 캐릭터인가?  (기존, 400)                |
|  2) 기존 쿠키가 있는가?                                           |
|     - 있고 같은 character_id → 재접속, 그대로 통과 (D-05)         |
|     - 있고 다른 character_id → 거부 (한 브라우저 = 한 캐릭터)     |
|     - 없으면 새 browser_id 발급 후 아래로                         |
+-----------------------------------------------------------------+
    |  actor.submit(OccupyCharacter(character_id, browser_id))
    v
+-----------------------------------------------------------------+
|  SessionActor._prepare_occupy()  (최종 방어선, 단일 소비자)       |
|  self.state.occupied_by 에서 character_id 이미 점유됐는지 확인    |
|  점유됨 + 다른 browser_id → CommandRejected (D-05)                |
|  아니면 → "character_occupied" 사건 append, GameState 갱신        |
+-----------------------------------------------------------------+
    |  성공                                    |  실패(CommandRejected)
    v                                          v
  HMAC 서명 쿠키 발급                        409/403 + 안내 문구만
  {session_id, browser_id, character_id}     (사건 기록에는 안 남음, D-04)
    |
    v
[이후 declare/confirm 요청은 쿠키의 browser_id/character_id를
 요청 본문의 character_id와 대조 → 다르면 거부(TRUST-02, 라우트 계층)]
    |
    v
+-----------------------------------------------------------------+
|  SessionActor._prepare_confirm()  (TRUST-03/05 최종 방어선)       |
|  1) caused_by_seq(declare_seq)가 존재하는가?  (기존)              |
|  2) 그 선언의 소유자(character_id)가 지금 확인하는 쪽과 같은가?    |
|     다르면 → CommandRejected (TRUST-03)                          |
|  3) 이미 확인된 declare_seq인가?  (self.state.confirmed_declares) |
|     같은 move/stat → AlreadyConfirmed(캐시된 resolve_seq 반환)    |
|     다른 move/stat → CommandRejected (D-10)                      |
|     처음이면 → 정상 진행                                          |
+-----------------------------------------------------------------+
```

### Recommended Project Structure

```
src/gptrpg/web/
├── cookie_auth.py          # 신규: sign/verify 함수 + 비밀 열쇠 로딩(load_or_create_secret)
├── routes_characters.py    # select_character/my_character가 cookie_auth를 쓰도록 확장
├── routes_actions.py       # declare/confirm 진입부에 신원 대조(TRUST-02) 추가
src/gptrpg/session_actor/
├── actor.py                 # OccupyCharacter 명령 + _prepare_occupy, _prepare_confirm 확장
src/gptrpg/event_log/
├── schema.py                 # EVENT_SCHEMA_VERSION 4→5, CharacterOccupied 신설, 관련 이벤트 확장
src/gptrpg/rules_core/
├── reducer.py                 # 옛 판 해석 경로 추가(reducer.py:98-99 전례를 따름)
tests/
├── conftest.py                 # 다중 캐릭터 픽스처(TEST-01)
├── test_session_actor.py        # 소유권/멱등성/점유 액터 단위 테스트 + 동시성(TEST-02)
├── test_web_actions.py            # HTTP 계층 신원 대조·멱등성 테스트
├── test_web_characters.py          # 쿠키 서명·점유 테스트
```

### Pattern 1: HMAC 서명 쿠키 (stdlib)

**What:** JSON 페이로드를 `base64url(payload).hex(hmac)` 형태의 단일 문자열로 만들어 쿠키 값으로 쓴다.
**When to use:** TRUST-01(위조 불가능한 보관), D-01/D-02.
**Example:**
```python
# 새 모듈: src/gptrpg/web/cookie_auth.py
# 패턴 근거: docs.python.org/3/library/hmac.html [CITED] — hmac.compare_digest로
# 타이밍 공격에 안전하게 비교한다. 저장소의 다른 secret 사용처
# (ruff per-file-ignores가 src/gptrpg/web/*에서 "secrets" import를 허용함,
# pyproject.toml:64,77 [VERIFIED])와 같은 층에 위치시킨다.
import base64
import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path

_DIGESTMOD = "sha256"


def load_or_create_secret(
    path: Path, *, env_var: str = "GPTRPG_COOKIE_SECRET", environ: dict = os.environ
) -> bytes:
    """환경변수가 있으면 그것을 우선한다(D-02). 없으면 파일에서 읽거나 새로 만든다."""
    if env_var in environ:
        return environ[env_var].encode("utf-8")
    if path.is_file():
        return path.read_bytes()
    secret = secrets.token_bytes(32)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(secret)
    return secret


def sign_cookie(payload: dict, *, secret: bytes) -> str:
    body = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).rstrip(b"=")
    signature = hmac.new(secret, body, digestmod=_DIGESTMOD).hexdigest()
    return f"{body.decode('ascii')}.{signature}"


def verify_cookie(raw: str, *, secret: bytes) -> dict | None:
    """서명이 안 맞거나 형식이 깨지면 조용히 None을 돌려준다 — 기존
    my_character()가 옛 형식 쿠키를 조용히 selected:false로 떨어뜨리는
    관례(routes_characters.py:172-190)와 같은 실패 모드를 유지한다."""
    try:
        body, signature = raw.rsplit(".", 1)
    except ValueError:
        return None
    expected = hmac.new(secret, body.encode("ascii"), digestmod=_DIGESTMOD).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return None
    try:
        padded = body + "=" * (-len(body) % 4)
        return json.loads(base64.urlsafe_b64decode(padded))
    except (ValueError, UnicodeDecodeError):
        return None
```

**비밀 열쇠 파일 배치:** `.gptrpg/` 디렉터리는 이미 `.gitignore:7`에 통째로 들어 있다 [VERIFIED: .gitignore:7 — `.gptrpg/`]. `.gptrpg/events.db`(`app.py:183` 기본값)와 같은 자리인 `.gptrpg/cookie_secret`에 두면 **새 gitignore 항목을 추가할 필요가 없다.**

**비밀 열쇠 로딩 시점:** `app = create_app(...)`이 **import 시점**에 실행되지만(`app.py:182-186`), store/registry는 `lifespan` 안에서 만들어진다(`app.py:91-96` — `app.state.store = store` 패턴) [VERIFIED]. 비밀 열쇠도 같은 이유로 **lifespan 안에서** `app.state.cookie_secret = load_or_create_secret(...)`로 만들어야 한다 — import 시점에 파일을 만들면 "이 모듈을 import하면 디렉터리에 흔적이 남는다"는, `app.py:131-138`이 그림 마운트에서 명시적으로 피한 것과 같은 문제가 재발한다.

### Pattern 2: SessionActor 안의 소유권 + 멱등성 상태 (권고 설계)

**What:** `GameState`에 두 파생 필드를 추가해 `_prepare_confirm`이 즉시 조회할 수 있게 한다. `fails_since_clock`/`clock_segment`가 사건을 접으며 파생되는 것과 같은 패턴이다(`reducer.py:41-56` 참조).
**When to use:** TRUST-03(소유권), TRUST-05(멱등성), TRUST-06(캐시된 판정 재사용).
**Example (설계안, 이 저장소의 기존 코드는 아직 이 필드를 갖지 않음 — ASSUMED 설계):**
```python
# rules_core/reducer.py의 GameState에 추가할 필드(설계안)
@dataclass(frozen=True)
class GameState:
    ...
    # declare_seq -> 그 선언을 낸 character_id (ActionDeclared.character_id, 판 5+)
    declare_owners: dict[int, str] = field(default_factory=dict)
    # declare_seq -> (confirm_seq, resolve_seq, move, stat) — 이미 확인·판정된 선언
    confirmed_declares: dict[int, "ConfirmedDeclareRecord"] = field(default_factory=dict)
    # character_id -> browser_id (점유 사건에서 파생)
    occupied_by: dict[str, str] = field(default_factory=dict)
```

```python
# session_actor/actor.py의 _prepare_confirm 확장(설계안) — 기존 함수(actor.py:389-407)에
# 소유권 대조(TRUST-03)와 멱등성 단락(TRUST-05/06)을 추가한다.
def _prepare_confirm(self, command: ConfirmAction) -> tuple[str, int | None, dict]:
    if not command.player_id.strip():
        raise CommandRejected("player_id는 비어 있을 수 없다")
    ...
    self._validate_caused_by(command.caused_by_seq)

    # TRUST-03: 확인하는 쪽이 그 선언을 낸 쪽과 같은 캐릭터인가.
    declared_owner = self.state.declare_owners.get(command.caused_by_seq)
    if declared_owner is not None and declared_owner != command.character_id:
        raise CommandRejected(
            "이 선언은 다른 캐릭터가 낸 것이다"  # 어떤 캐릭터인지는 문구에 안 싣는다(QUAL-05)
        )

    # TRUST-05/D-10: 이미 확인된 선언이면 재처리하지 않는다.
    prior = self.state.confirmed_declares.get(command.caused_by_seq)
    if prior is not None:
        if prior.move != command.move or prior.stat != command.stat:
            raise CommandRejected("이미 다른 무브로 확인된 선언이다")
        raise AlreadyConfirmed(prior)  # CommandRejected의 서브클래스, 캐시된 결과를 들고 있음
    ...
```

**라우트 층 소비 방식(설계안):** `routes_actions.py:confirm()`이 `AlreadyConfirmed`를 `CommandRejected`보다 먼저 잡아(서브클래스이므로 순서 중요), `store.read_events(session_id, from_seq=prior.resolve_seq)[0]`로 캐시된 `CheckResolved`를 가져온 뒤(기존 `routes_actions.py:346`과 같은 패턴), `ResolveCheck`를 다시 제출하지 않고 곧바로 서사 생성(⑤ 단계, `routes_actions.py:372-419`)으로 건너뛴다. 이렇게 하면 TRUST-06("주사위 실패"와 "서사 실패" 구분)과 D-09("이야기만 다시 쓴다")가 정확히 성사된다.

### Anti-Patterns to Avoid

- **라우트 계층에서만 소유권/멱등성을 검사:** TRUST-03이 명시적으로 우회 경로를 지적한다 — 두 브라우저가 준비된 요청을 정확히 같은 밀리초에 보내면 라우트 계층의 `if` 문 두 개가 둘 다 통과할 수 있다. `SessionActor`의 `asyncio.Queue` 단일 소비자만이 진짜 직렬화 지점이다.
- **액터의 메모리 상태만으로 소유권을 판단:** 서버 재시작 후 `self.state`는 저장소에서 다시 접힌다(`actor.py:219-229`). 소유권 정보가 사건에 없으면 재시작 직후의 확인 요청은 검증할 근거가 사라진다.
- **`itsdangerous`처럼 만료가 내장된 서명기를 도입하면서 브라우저 `Max-Age`와 별도로 서버측 만료를 추가:** 이 프로젝트는 "한 번 잡으면 놓을 수 없다"(D-07)와 "서버가 꺼졌다 켜져도 아무도 안 쫓겨난다"(D-02)를 이미 결정했다 — 서버측 타임스탬프 만료를 넣으면 두 결정과 충돌하는 세 번째 만료 규칙이 생긴다.
- **예외 메시지에 `character_id`/`browser_id` 값을 그대로 삽입:** 신원 불일치 사유를 상세히 적으면 그 자체가 "누가 어떤 캐릭터를 쥐고 있는지"를 추측하게 해주는 정보 노출이 된다(QUAL-05). 기존 코드도 이미 이 규율을 지킨다 — `_prepare_ai_call`의 오류 문구(`actor.py:508-511`)가 숫자 비교 실패를 말하되 실제 토큰 값을 매번 문구에 넣지는 않는 것과 같은 절제.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 서명 비교 | 문자열 `==` 비교 | `hmac.compare_digest()` | `==`는 첫 불일치 지점에서 조기 종료해 타이밍 공격에 노출된다 — Python 공식 문서가 명시적으로 이 함수를 위해 존재한다고 설명한다 [CITED] |
| JSON 파싱 실패 처리 | bare `except:` 또는 `except Exception:` | `except (json.JSONDecodeError, TypeError, ValueError):` | 기존 `my_character()`가 이미 이 정확한 패턴을 쓴다(`routes_characters.py:179-182`) [VERIFIED] — 새 코드도 같은 구체적 예외 목록을 따라야 `BaseException`까지 삼키는 사고를 피한다 |
| 동시 요청 직렬화 | 락(`asyncio.Lock`)이나 뮤텍스를 새로 도입 | 기존 `SessionActor`의 `asyncio.Queue` 단일 소비자 | 이미 세션당 유일한 쓰기 주체가 있다(`actor.py:201-202` 도크스트링) — 두 번째 동기화 장치를 얹으면 두 메커니즘의 상호작용을 새로 추론해야 한다 |

**Key insight:** 이 단계가 필요로 하는 모든 "동시성 안전성"은 이미 `SessionActor`의 큐 하나로 공짜로 따라온다 — 새로 발명할 동시성 도구가 없다는 것이 이 저장소의 강점이다. 위험은 오히려 반대 방향이다: 라우트 계층에서 편의상 먼저 검사를 해버리고 액터 계층 검사를 빠뜨리는 것(TRUST-03이 우려하는 정확히 그 상황).

## Common Pitfalls

### Pitfall 1: `ActionDeclared`/`ActionConfirmed`가 `character_id`를 담지 않는다 — 스키마 범위가 D-12/D-13이 명시한 것보다 넓어질 수 있다

**What goes wrong:** 계획이 D-12/D-13을 문자 그대로만 읽으면 "`CheckResolved`에만 사람·캐릭터 칸을 추가"로 스코프를 좁힐 위험이 있다. 하지만 TRUST-03("확인의 주인이 선언의 주인과 같은가")을 검증하려면, **선언 시점에 누가(어떤 character_id로) 선언했는지가 액터의 재구성 가능한 상태에 남아 있어야** 한다.

**Why it happens:** 지금 `DeclareAction`(`actor.py:64-70`)과 `ConfirmAction`(`actor.py:72-82`)은 `player_id`만 갖고, 이 값이 `character_id`와 같다는 전제(D-42)에 기대고 있다. 라우트가 받는 `character_id`(`routes_actions.py:139-143,249`)는 지금 오직 AI 문맥 조립(`build_turn_context`)에만 쓰이고 `actor.submit(...)` 호출에는 전달되지 않는다 — `declare()`의 실제 호출(`routes_actions.py:165-167`: `DeclareAction(player_id=body.player_id, raw_text=body.raw_text)`)과 `confirm()`의 실제 호출(`routes_actions.py:305-317`, `character_id` 없음)을 직접 읽어 확인했다. D-03이 "사람과 캐릭터를 분리"하기로 결정한 순간, `player_id`가 곧 `character_id`라는 전제가 깨지므로 이 문제가 표면화된다.

**How to avoid:** 계획 단계에서 이 스키마 확장을 명시적으로 포함시킨다 — `EVENT_SCHEMA_VERSION` 4→5 판 올리기에 다음을 함께 넣는 것을 권고한다(전부 D-12/D-13이 이미 확립한 "옛 판 해석 경로" 패턴을 그대로 재사용):
1. `ActionDeclared`에 `character_id: str` 필수 칸 추가(판 5+에서만 필수, 판 4 이하 기록은 옛 판 해석 경로로 읽는다 — 값을 모른다는 뜻으로 처리).
2. `ActionConfirmed`에 `character_id: str` 필수 칸 추가(같은 이유).
3. `CheckResolved`에 `person_id`(브라우저 식별자)·`character_id` 필수 칸 추가 — D-12가 이미 정한 대로.
4. 새 사건 종류(예: `CharacterOccupied`) 신설 — D-06이 이미 정한 대로.

이 발견은 이 연구 세션에서 코드를 직접 읽어 확인한 것이지, CONTEXT.md가 명시적으로 검증한 결정은 아니다 — **계획 단계에서 사용자에게 "스키마 판 올리기 범위가 CheckResolved 하나가 아니라 넷(3개 필드 확장 + 1개 신규 사건)이 될 것"을 확인받는 체크포인트를 넣을 것을 권고한다.**

**Warning signs:** 구현 중 `_prepare_confirm`이 "누가 이 선언을 냈는지" 물어볼 데이터가 없다는 것을 알게 되면 이 갭에 부딪힌 것이다. 서버 재시작 직후 확인 요청이 소유권 검증을 통과시키지 못하거나(과잉 거부) 조용히 통과시키면(검증 무력화) 증상이 나타난다.

### Pitfall 2: 옛 사건(형식 판 2~4)을 판 5 코드로 읽을 때 `character_id`가 없다

**What goes wrong:** `.gptrpg/events.db`의 세션1 기록 895건은 전부 판 2다(`reducer.py`가 이미 판 1→2→3→4 세 번의 판 올리기를 거쳤음이 코드에 남아 있다 — `schema.py:18-35` [VERIFIED, 전문 인용은 아래]). 판 5 리듀서가 이 옛 기록을 접을 때 `character_id`가 없는 `action_declared`/`action_confirmed`/`check_resolved`를 만나게 된다.

**Why it happens:** `EVENT_SCHEMA_VERSION`은 코드에서 이미 **4**다 — CONTEXT.md의 "형식 번호 2"라는 표현은 **`.gptrpg/events.db`에 실제로 저장된 옛 기록의 판 번호**를 가리키는 것이지, 이번에 판을 올릴 시작점이 2라는 뜻이 아니다. 이번 단계의 판 올리기는 **4→5**다. 헷갈리면 리듀서의 옛 판 해석 경로를 잘못된 기준(`schema_version >= 2`가 아니라 실제로는 `schema_version >= 5`가 새 칸의 기준)으로 짤 위험이 있다.

**How to avoid:** `reducer.py:98-99`의 정확한 패턴(`schema_version = payload.get("schema_version", 1)`, `if schema_version >= N:`)을 그대로 복제하되 기준값을 5로 쓴다. `CheckResolved`처럼 새 칸을 **필수로 만들 것인지**(D-12가 명시), 아니면 `cached_prompt_tokens`처럼 **기본값 있는 선택 칸으로 만들 것인지**(판 2→3 전례, `schema.py:26-35`)는 사건 종류마다 다시 판단해야 한다 — `CheckResolved`는 D-12가 필수로 못박았지만, `ActionDeclared`/`ActionConfirmed`에 새로 추가하는 `character_id`는 옛 기록에서 값 자체가 존재한 적이 없으므로 **선택 칸(기본값 `None`)으로 두고, 리듀서가 "판 5 미만이면 소유권을 모른다"로 읽는 경로**를 권고한다(D-14가 이미 "옛 세션은 새 행동을 못 보낸다"고 정했으므로, 옛 기록에 소유권이 없어도 새 확인 요청이 그 옛 declare_seq를 가리킬 일 자체가 없다 — 일관적이다).

**Warning signs:** `pytest`로 `.gptrpg/events.db`를 복제해 판 5 코드로 읽었을 때 `UnknownEventType`이나 pydantic validation error가 나면 이 경로를 놓친 것이다. (Phase 12의 TEST-04가 이 회귀를 전담하지만, 이 단계도 "읽는 길만 연다"는 D-13의 약속을 어기지 않으려면 최소한 판 5 코드가 판 2~4 기록에서 예외 없이 상태를 재구성한다는 것을 스모크 테스트해야 한다.)

### Pitfall 3: `SelectCharacterRequest.character_id`에 길이 상한이 없다 (QUAL-04)

**What goes wrong:** `routes_characters.py:82-83`의 `SelectCharacterRequest.character_id: str`에는 `Field(max_length=...)`가 없다 [VERIFIED: routes_characters.py:82-83 — `class SelectCharacterRequest(BaseModel): character_id: str`]. 임의 길이 문자열이 쿠키 페이로드에 그대로 들어가면, 쿠키 크기 상한(브라우저마다 다르지만 보통 4KB)을 넘겨 쿠키 자체가 저장되지 않는 조용한 실패가 날 수 있다.

**Why it happens:** `routes_actions.py`의 `DeclareRequest`/`ConfirmRequest`는 이미 `Field(min_length=1, max_length=MAX_ID_LEN)` 관례를 캐릭터/식별자 칸마다 적용했지만(`routes_actions.py:139-143,240-250`), `routes_characters.py`는 이 상한 도입 이전에 작성된 파일이라 관례가 전파되지 않았다.

**How to avoid:** `routes_actions.py`가 이미 export하는 `MAX_ID_LEN = 64`(`routes_actions.py:81-82`)를 `routes_characters.py`가 import해 재사용한다(새 상수를 따로 선언하지 않는다 — 같은 숫자를 두 자리에 적지 않는다는 이 프로젝트의 기존 관례, `actor.py:236-239` 주석이 명시).

## Code Examples

### 기존 신원 대조 지점(변경 없이 그대로 재사용)

```python
# src/gptrpg/web/app.py:49-61 — 신원 검증 Depends의 이미 있는 선례.
# 새 쿠키 검증 의존성(예: require_character_cookie)도 같은 방식으로
# app.include_router(..., dependencies=[Depends(...)])에 건다.
def validate_session_id(session_id: str) -> str:
    if not SAFE_SESSION_ID.match(session_id):
        raise HTTPException(
            status_code=400,
            detail="세션 식별자가 허용된 글자 범위를 벗어났다",
        )
    return session_id
```

### 기존 액터 동시성 테스트 패턴(TEST-02 actor-level에 그대로 재사용 가능)

```python
# tests/test_session_actor.py:186-190 — 이미 존재하는 패턴.
# TEST-02가 재현할 "두 확인 요청이 동시에 들어오는 상황"은 바로 이 패턴으로
# ConfirmAction 두 개를 asyncio.gather에 넣으면 된다: 큐가 직렬화하므로
# 실제 경쟁 조건 없이도 "둘 중 하나만 성공, 나머지는 AlreadyConfirmed 또는
# CommandRejected"를 결정적으로(non-flaky) 검증할 수 있다.
seqs = await asyncio.gather(*(actor.submit(command) for command in commands))
```

### HTTP 계층 동시 요청 재현(TEST-02, 신규 패턴 — httpx.AsyncClient)

```python
# 이 저장소에는 아직 없는 패턴이지만 httpx 0.28.1(이미 설치됨)이 지원한다.
# 두 브라우저가 select-character를 동시에 같은 캐릭터로 누르는 상황(D-05)을
# 실제 ASGI 앱을 통해(라우트+액터 전체 경로) 재현한다.
import asyncio
from httpx import ASGITransport, AsyncClient

async def test_two_browsers_selecting_same_character_only_one_wins(web_app):
    transport = ASGITransport(app=web_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c1, \
               AsyncClient(transport=transport, base_url="http://test") as c2:
        r1, r2 = await asyncio.gather(
            c1.post("/api/sessions/s1/select-character", json={"character_id": "bram"}),
            c2.post("/api/sessions/s1/select-character", json={"character_id": "bram"}),
        )
    statuses = {r1.status_code, r2.status_code}
    assert 200 in statuses
    assert len(statuses) == 2  # 나머지 하나는 점유 충돌 상태 코드
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| 서명 없는 평문 JSON 쿠키(`json.dumps({"session_id": ..., "character_id": ...})`) | HMAC 서명 쿠키 | 이번 단계(D-01) | 브라우저 콘솔에서 쿠키 값을 편집해 남의 캐릭터를 사칭하는 경로가 막힌다 |
| `player_id === character_id`(D-42) | 「브라우저 식별자」와 「고른 캐릭터」 분리(D-03) | 이번 단계 | 사건 기록에 사람·캐릭터가 각각 남아, 나중에 한 사람이 여러 캐릭터를 조종해도 기록 형식을 다시 안 고쳐도 됨(M2 대비) |
| 확인 재시도 시 서사 실패면 502로 판정 결과까지 통째로 버림 | 판정은 그대로 두고 서사만 재시도(D-08/D-09) | 이번 단계 | 세션1에서 재시도가 이중 굴림을 유발한 근본 원인이 제거됨 |

**Deprecated/outdated:** 없음 — 이 단계는 새 라이브러리를 도입하지 않으므로 "구식이 된 접근"이 발생하지 않는다.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `GameState`에 `declare_owners`/`confirmed_declares`/`occupied_by` 파생 필드를 추가하는 설계(Pattern 2)가 최선의 구현 방식이다 | Architecture Patterns § Pattern 2 | 대안(매 요청마다 `store.read_events()` 스캔)도 정확성은 동일하다 — 이것은 성능/코드 위치 선호일 뿐 필수 결정은 아니다. 계획 단계에서 재고할 수 있다 |
| A2 | `ActionDeclared`/`ActionConfirmed`에 `character_id`를 추가하는 스키마 확장(Pitfall 1)이 D-12/D-13의 의도된 범위 안에 있다 | Common Pitfalls § Pitfall 1 | 만약 사용자가 다른 방식(예: 신원 검증을 오직 라우트 계층 쿠키 대조로만 하고 액터 계층은 "존재하는 declare_seq인가"만 계속 본다)을 의도했다면, TRUST-03("SessionActor 안에서 검증")의 실질적 보장 수준이 이 연구가 가정한 것보다 약해진다 — **계획 전 사용자 확인 필수** |
| A3 | HTTP 상태 코드: 신원 불일치(TRUST-02/03) → 403, 점유 충돌(D-05) → 409, 이미 확인됨의 무브 불일치(D-10) → 400 | HTTP 상태 코드 언급(§ Architecture Patterns, § Pitfall) | 이 저장소의 기존 관례는 `CommandRejected`를 전부 400으로 뭉뚱그린다(`routes_actions.py:203-204,318-319,341-342`) — 403/409를 새로 도입하면 기존 테스트의 상태 코드 단언과 어긋날 수 있어, 계획 단계에서 "기존 400 통일 방식을 유지할지, 세분화할지"를 명시적으로 정해야 한다 |
| A4 | `.gptrpg/cookie_secret` 파일 경로가 적절한 이름/위치다 | Pattern 1 | 이름 자체는 순전히 Claude's Discretion 항목("함수·모듈 이름")이므로 계획 단계에서 자유롭게 바꿀 수 있다 — 리스크 낮음 |

**참고:** 이 표의 항목들은 모두 코드 직접 확인(VERIFIED)에 기반한 설계 추론이며, "설계가 틀렸다"는 뜻이 아니라 "CONTEXT.md가 명시적으로 잠그지 않은 결정"이라는 뜻이다.

## Open Questions

1. **`ActionDeclared`/`ActionConfirmed`에 `character_id`를 추가하는 스키마 확장 범위를 사용자가 승인하는가?**
   - What we know: 코드를 읽어 확인한 결과 이 확장 없이는 TRUST-03이 재시작 후에도 성립하지 않는다(Pitfall 1).
   - What's unclear: CONTEXT.md의 D-12/D-13이 이 확장까지 의도했는지, 아니면 계획 단계에서 처음 제기되는 결정인지.
   - Recommendation: 계획 단계 시작 시 `checkpoint:human-verify`로 이 발견을 사용자에게 제시하고 승인받는다.

2. **점유 충돌·신원 불일치의 정확한 HTTP 상태 코드는?**
   - What we know: 기존 코드는 `CommandRejected`를 예외 없이 400으로 매핑한다.
   - What's unclear: 이번 단계에서 403/409로 세분화할지, 기존 400 통일을 유지할지는 CONTEXT.md가 "Claude's Discretion"으로 명시적으로 위임했다.
   - Recommendation: 403(신원/권한) · 409(점유 충돌, 기존 `SequenceConflict`와 같은 계열) · 400(입력 형식) 세 갈래로 나누는 것을 권고하되, 계획 단계에서 최종 확정한다.

3. **브라우저 식별자(`browser_id`)를 어디서·언제 발급하는가?**
   - What we know: `select-character`가 처음 성공할 때 발급하는 것이 D-01/D-03/D-05와 가장 잘 맞는다(Architecture Patterns 다이어그램 참조).
   - What's unclear: 세션 진입 시점(캐릭터 선택 전)에 이미 `browser_id`가 필요한 화면 동작이 있는지(예: "누가 지금 보고 있는지"를 캐릭터 선택 전에도 구분해야 하는 요구가 있는지) — CONTEXT.md에 명시가 없다.
   - Recommendation: 이 단계 범위(캐릭터 선택 이후의 신원·점유·멱등성)로 한정하면 select-character 시점 발급으로 충분하다.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python `hmac`/`hashlib`/`secrets`(stdlib) | 쿠키 서명(D-01) | ✓ | Python 3.11+ 내장(`requires-python>=3.11`, VERIFIED: pyproject.toml:9) | — |
| `httpx` | HTTP 계층 동시성 테스트(TEST-02) | ✓ | 0.28.1(VERIFIED: uv.lock:721-723) | — |
| `pytest-asyncio` | 액터 동시성 테스트(TEST-02) | ✓ | `>=1.4.0`, `asyncio_mode="auto"`(VERIFIED: pyproject.toml:47,53) | — |
| `itsdangerous`(대안, 미채택) | — | ✗ | 미설치 확인(`pip show itsdangerous` 실패) | stdlib `hmac` 사용(권고안) |

**Missing dependencies with no fallback:** 없음.
**Missing dependencies with fallback:** `itsdangerous`(대안 검토 후 stdlib로 대체 — 원래부터 필수 의존성이 아님).

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest `>=9.1.1` + pytest-asyncio `>=1.4.0`(VERIFIED: pyproject.toml:46-49) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]`(줄 51-53) — `testpaths=["tests"]`, `asyncio_mode="auto"` |
| Quick run command | `uv run pytest tests/test_session_actor.py tests/test_web_actions.py tests/test_web_characters.py -q` |
| Full suite command | `uv run pytest -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TRUST-01 | 서명 없이 조작한 쿠키가 거부된다 | unit(web) | `pytest tests/test_web_characters.py -k signed_cookie -x` | ❌ Wave 0 |
| TRUST-02 | 요청 character_id ≠ 쿠키 character_id면 declare/confirm이 거부된다 | unit(web) | `pytest tests/test_web_actions.py -k identity_mismatch -x` | ❌ Wave 0 |
| TRUST-03 | 액터 계층에서 소유권 불일치가 거부된다(라우트를 우회해 직접 `actor.submit`) | unit(actor) | `pytest tests/test_session_actor.py -k owner_mismatch -x` | ❌ Wave 0 |
| TRUST-04 | `CheckResolved`에 person_id/character_id가 필수로 남는다 | unit(schema) | `pytest tests/test_session_actor.py -k check_resolved_has_actor -x` | ❌ Wave 0 |
| TRUST-05 | 같은 declare_seq 두 번 확인해도 판정 사건이 하나만 남는다 | unit(actor) | `pytest tests/test_session_actor.py -k idempotent_confirm -x` | ❌ Wave 0 |
| TRUST-06 | 서사 실패 시 응답에 판정 결과가 남고, 재시도 시 굴림이 재사용된다 | integration(web) | `pytest tests/test_web_actions.py -k narration_retry_reuses_roll -x` | ❌ Wave 0 |
| QUAL-04 | `SelectCharacterRequest.character_id` 길이 초과가 422다 | unit(web) | `pytest tests/test_web_characters.py -k max_length -x` | ❌ Wave 0 |
| QUAL-05 | 예외 문구에 쿠키 값/비밀 열쇠가 없다 | unit(web) | `pytest tests/test_web_characters.py -k no_secret_leak -x` | ❌ Wave 0 |
| TEST-01 | 실제 캐릭터 여러 명의 발화에 각자 이름이 붙는다 | integration | `pytest tests/test_web_actions.py -k multi_character_names -x` | ❌ Wave 0(픽스처 자체가 이번 단계 산출물) |
| TEST-02 | 겹치는 확인/점유 요청이 재현된다 | integration(actor+http) | `pytest tests/test_session_actor.py tests/test_web_characters.py -k concurrent -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_session_actor.py tests/test_web_actions.py tests/test_web_characters.py -q`
- **Per wave merge:** `uv run pytest -q`(전체 스위트, `.importlinter`까지 포함하려면 `uv run lint-imports` 별도 실행 — 기존 CI 관례를 계획 단계에서 확인)
- **Phase gate:** 전체 스위트 green + `.gptrpg/events.db`(또는 복제본)를 판 5 리듀서로 읽어도 예외가 없는지 스모크 확인(Pitfall 2)

### Wave 0 Gaps

- [ ] `tests/conftest.py` — 다중 캐릭터 픽스처(TEST-01), 서명된 쿠키를 발급하는 헬퍼 함수
- [ ] `tests/test_web_characters.py`에 서명 쿠키·점유 충돌 테스트 신설
- [ ] `tests/test_web_actions.py`에 신원 대조·멱등성 통합 테스트 신설
- [ ] `tests/test_session_actor.py`에 소유권/멱등성/점유 명령 단위 테스트 + `asyncio.gather` 동시성 테스트 신설
- [ ] Framework install: 불필요(기존 pytest/pytest-asyncio/httpx로 충분)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | 부분 적용 | 이 프로젝트는 계정 체계가 없다(M0/v1.1 범위 밖) — 서명 쿠키는 "신원 확인"이 아니라 "브라우저 재식별"에 가깝다. HMAC 서명이 위조를 막는 것이 이 층의 유일한 통제(D-01의 알려진 한계와 일치) |
| V3 Session Management | 예 | `hmac`+`hashlib`(stdlib), `secrets.token_bytes(32)`로 비밀 생성(V6.2.1 수준의 CSPRNG). 쿠키 자체는 `httponly`+`samesite=lax`가 이미 걸려 있다(`routes_characters.py:160-162`, VERIFIED) — 이번 단계가 추가하는 것은 서명뿐, 두 속성은 그대로 유지한다 |
| V4 Access Control | 예 | 캐릭터 소유권 검증(TRUST-02/03)이 이 카테고리의 핵심 — 라우트+액터 이중 검증(D-11)이 ASVS의 "서버측에서, 신뢰할 수 없는 클라이언트 데이터가 아니라 서버가 보유한 상태로 검증" 원칙과 일치 |
| V5 Input Validation | 예 | 기존 pydantic `Field(min_length=..., max_length=...)` 관례(QUAL-04가 이 관례의 빈틈을 메운다) |
| V6 Cryptography | 예 | `hmac.compare_digest()`로 타이밍 공격 방지(hand-roll 금지 — Don't Hand-Roll 표 참조). 자체 서명 알고리즘·자체 비교 로직을 만들지 않는다 |

### Known Threat Patterns for 이 스택(FastAPI + SQLite + 서명 쿠키)

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| 쿠키 값 변조로 남의 캐릭터 사칭 | Spoofing | HMAC 서명 + `hmac.compare_digest` 검증(D-01, 이 단계의 핵심) |
| 남이 선언한 행동을 자기 것인 양 확인 | Spoofing/Elevation of Privilege | 액터 계층 소유권 검증(TRUST-03, Pattern 2) |
| 같은 확인을 반복 전송해 주사위를 여러 번 굴림 | Tampering(게임 상태 무결성) | 멱등성 검사(TRUST-05, `confirmed_declares`) |
| 두 브라우저가 동시에 같은 캐릭터를 점유 시도 | Tampering/Repudiation(누가 진짜 점유자인지 불분명해짐) | `SessionActor` 단일 소비자 직렬화(D-11) + 점유 사건 append-only 기록(D-06) |
| 예외 메시지·로그에 쿠키 값·비밀 열쇠가 노출 | Information Disclosure | QUAL-05 — 커스텀 예외가 원인 유형만 말하고 실제 값은 담지 않는다(기존 `InvalidStatEntry`/`InvalidEntity`처럼 `reason` 문자열은 있어도 비밀은 없는 패턴, `entities.py:20-23,33-36` 참조) |
| 타이밍 공격으로 HMAC 서명 바이트를 하나씩 추측 | Information Disclosure/Spoofing | `hmac.compare_digest`(Don't Hand-Roll 표) |

## Sources

### Primary (HIGH confidence)
- 이 저장소 자체 코드(`src/gptrpg/...`, `tests/...`, `pyproject.toml`, `uv.lock`, `.gitignore`) — 이번 연구 세션에서 `Read`로 직접 열람, 인용된 모든 줄 번호는 검증됨
- `.planning/phases/08-identity-and-idempotency/08-CONTEXT.md` — 사용자 결정(D-01~D-14), 이번 연구 세션에서 직접 열람
- `.planning/REQUIREMENTS.md` — TRUST-01~06, QUAL-04·05, TEST-01·02 원문, 이번 연구 세션에서 직접 열람

### Secondary (MEDIUM confidence)
- [Python `hmac` 공식 문서](https://docs.python.org/3/library/hmac.html) — `hmac.compare_digest`, `hmac.new(digestmod=...)` 사용법 [CITED, WebFetch로 확인]
- [itsdangerous 공식 문서(GitHub, Pallets)](https://github.com/pallets/itsdangerous/blob/main/docs/timed.rst) — `TimestampSigner`/`max_age`/`SignatureExpired` [CITED, WebFetch로 확인, 이번 단계에서는 미채택]
- PyPI registry 조회(`pip index versions itsdangerous` → `2.2.0`) — [VERIFIED: PyPI 공식 registry]

### Tertiary (LOW confidence)
- 이하 WebSearch 결과는 일반적인 업계 패턴 설명이며 이 저장소에 특화된 것이 아니다 — 방향성 참고용, 구체적 구현은 위 코드 확인 기반 설계를 따른다.
- 멱등성 키 원자적 처리 패턴(check-then-act 문제, insert-or-fail) — WebSearch 다건 종합
- pytest 다중 아이덴티티 파라미터화 패턴(`pytest.param(..., id=...)`) — WebSearch, pytest 공식 문서 링크 다수 포함되었으나 개별 페이지는 WebFetch로 재확인하지 않음
- FastAPI 동시성 테스트 일반론(스레드풀, race condition 재현) — WebSearch 종합
- Python 커스텀 예외 클래스의 비밀 누출 방지 일반론 — WebSearch 종합(이 저장소의 구체적 패턴은 `entities.py`/`actor.py` 직접 확인이 더 신뢰도 높은 근거)

## Metadata

**Confidence breakdown:**
- Standard stack(HMAC/pytest/httpx): HIGH — stdlib·기설치 패키지이고 공식 문서로 교차 확인
- 저장소 통합 지점(어디에 무엇을 넣는가): HIGH — 전부 `Read`로 직접 코드 확인, 줄 번호·인용 포함
- Pitfall 1(스키마 확장 범위): MEDIUM — 코드 사실(HIGH)에서 도출한 설계 추론(사용자 미확인)이므로 계획 단계 확인 필요
- 멱등성/소유권 상태 설계(Pattern 2): MEDIUM — 이 저장소에 아직 없는 신규 설계이므로 ASSUMED로 표시, 기존 패턴(`fails_since_clock` 등)과의 정합성으로 근거를 보강함
- 동시성 테스트 패턴: HIGH(actor-level, 기존 코드 재사용) / MEDIUM(HTTP-level, 신규지만 httpx 공식 기능)

**Research date:** 2026-08-06
**Valid until:** 이 저장소 자체가 빠르게 바뀌므로 30일 이내 재검토 권고. stdlib 기반 부분(HMAC)은 사실상 만료되지 않는다.
