# Phase 4: 실험 도구 완성 - Research

**Researched:** 2026-08-03
**Domain:** First web layer (FastAPI backend + minimal TypeScript polling frontend) wrapping an existing pure-Python event-sourced CLI engine (Phases 1-3)
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-38:** 여러 브라우저 사이의 동기화는 **짧은 폴링(1~2초 간격)** 으로 한다. WebSocket·SSE는 이번 단계에 넣지 않는다.
  - *이유:* `EventStore.read_events(session_id, from_seq)`가 이미 순번 기반 조회를 완벽히 지원한다 — 폴링은 이 함수를 주기적으로 부르기만 하면 되고 새 재생 로직이 필요 없다. AI 응답 자체가 2~15초 걸리므로 1~2초 폴링 지연은 체감상 의미가 없다. 실험 도구는 두 세션·네 명이 쓰고 끝나므로 WebSocket의 연결 상태 관리·재연결 로직 비용이 회수되지 않는다.
- **D-39:** 폴링 한 번에 여러 문장이 한꺼번에 모여서 보여도 된다 — 문장 단위 스트리밍 체감을 유지하려고 폴링 주기를 더 짧게(0.5초) 하지 않는다.
- **D-40:** 폴링이 **약 10초(폴링 몇 번 연속 실패)** 동안 이어지지 않으면 화면에 "연결이 끊겼음"을 표시한다.
- **D-41:** 브라우저를 새로고침하거나 완전히 닫았다 다시 열면 **세션 전체 역사를 처음부터 다시 불러와(`from_seq=0`) 마지막까지 스크롤**한다. 브라우저에 마지막으로 본 순번을 저장해 그 이후만 불러오는 방식은 쓰지 않는다.
- **D-42:** 네 명이 받는 링크는 **전부 같은 하나의 링크**다. 그 링크로 들어온 사람이 입장 시 자기 캐릭터를 고른다. 사람별로 다른 개인 링크는 만들지 않는다.
- **D-43:** 캐릭터 선택 결과는 **브라우저 쿠키에 저장**한다. 같은 브라우저로 돌아오면 새로고침해도 이름을 다시 묻지 않고 자동으로 같은 캐릭터가 선택된다.
- **D-44:** 집계 결과(MEAS-01·MEAS-03)는 **CLI 조회 명령과 세션 종료 시 파일 자동 저장을 둘 다** 제공한다. 별도 웹 요약 화면은 만들지 않는다.
- **D-45:** 자동 저장 파일 형식은 **JSON**이다. CSV는 쓰지 않는다.
- **D10 (referenced, already locked pre-Phase-4):** 조율은 외부 메신저에서 끝난다 — 발언권 락·순서 강제·짧은 타이머는 만들지 않는다. `session_actor`의 단일 쓰기 주체 + 명령 큐가 동시 입력의 유일한 조율 장치다.

### Claude's Discretion

계획·조사 단계에서 판단하되, 위 결정을 뒤집지 않는 선에서:

- 폴링 API의 정확한 엔드포인트 설계(REST 형태, 응답 스키마)
- 실패 3회 도달 시 시계를 강제로 진행시키는 로직을 어느 층에 둘지 — `session_actor`가 `ResolveCheck` 처리 직후 자동으로 `AdvanceClock(trigger="fail_counter")`를 주입하는 방식이 유력하나 최종 구조는 계획 단계 판단
- 쿠키의 정확한 키 이름·만료 기간·직렬화 형식
- 자동 저장되는 JSON 집계 파일의 정확한 필드 스키마와 저장 경로/파일명 규칙
- 웹 프레임워크 선택(FastAPI 등 Python 백엔드 생태계 내에서) — PROJECT.md의 "Python 백엔드 + TypeScript 프런트엔드" 제약 안에서 리서치 단계가 정한다
- 프런트엔드 기술 스택 세부(빌드 도구, 상태 관리 등) — 화면 배치·컴포넌트 설계는 M0 범위 밖(ROADMAP 원문)이므로 최소한만
- "연결이 끊겼음" 표시의 정확한 문구·위치
- 캐릭터 선택 화면(입장 시 뜨는 것)의 정확한 모양

### Deferred Ideas (OUT OF SCOPE)

- **WebSocket 기반 즉시 반영** — D-38이 이번 단계엔 과하다고 판단. 제품 단계(M1)에서 실시간성이 중요해지면 재검토
- **웹 요약 화면(집계 결과 전용 페이지)** — D-44에서 명시적으로 제외. CLI+파일로 충분하다고 판단됨
- **개인별 링크(사람마다 다른 URL)** — D-42에서 제외. "링크 하나"의 취지와 배치됨
- 캐릭터 만들기 화면, 매칭·로비, 안전 장치 UI, 결제·계정, 코스메틱, 룰북 저작 도구, 리캡 자동 생성 (전체 phase-level Out of Scope, REQUIREMENTS.md/PROJECT.md)

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|--------------------|
| RIG-04 | 위협 시계의 현재 칸과 판정 실패 누적 카운터가 화면에 보이고, 실패 3회 도달 시 시계가 강제로 한 칸 진행된 뒤 카운터가 초기화된다 | New `GameState.fails_since_clock` field (Pitfall 2) + `SessionActor` auto-advance hook (Code Examples); `clock_segment`/`clock_advances` already exist and need no new logic |
| RIG-05 | 플레이어가 자기 캐릭터 시트를 읽기 전용으로 볼 수 있다 | Requires a new `player_id -> Entity` mapping (Pitfall 3, Open Question 1) — `Entity`/`StatEntry` shape is reusable as-is, but the association layer doesn't exist yet; served via a new read-only GET endpoint |
| RIG-07 | 링크 하나로 여러 명이 같은 세션 화면을 동시에 보고, 끊겼다 다시 들어와도 놓친 부분이 이어 붙는다 | `EventStore.read_events(session_id, from_seq)` (verified, already implements both polling and full-reconnect semantics) exposed via one GET endpoint; D-42's single link handled by character-selection-on-entry, not per-user routing |
| MEAS-01 | 세션이 끝나면 실제 토큰 소모량과 실제 턴 수가 자동으로 집계된다 | `GameState.total_tokens`/`turn_count` (already computed by the existing reducer) surfaced via the new `build_report()` function (Code Examples), written by both the CLI `report` subcommand and the auto-save hook |
| MEAS-03 | 판정 실패 횟수 대비 위협 시계 진행 횟수가 기록에서 자동 집계된다 | `GameState.failure_count`/`clock_advances` (both already exist, cumulative — distinct from the new resettable RIG-04 counter, see Pitfall 2) combined into `failure_to_clock_ratio` in `build_report()` |
</phase_requirements>

## Summary

Phase 4 does not build a new engine — it builds a thin HTTP skin around code that already works end-to-end from the CLI (`gptrpg turn`). The two load-bearing primitives the whole phase rests on are `EventStore.read_events(session_id, from_seq)` (polling + reconnect, D-38/D-41 — verified, `src/gptrpg/event_log/store.py:93-103`) and `SessionActor`'s single-writer command queue (concurrent submissions, D-09 — verified, `src/gptrpg/session_actor/actor.py:149-227`). Both already do exactly what D-38/D-41/D-42 need with zero changes.

Three things are **not** already solved and need real design work this phase, verified by reading the actual code rather than assumed from CONTEXT.md's optimistic notes:

1. **The "실패 3회 → 초기화" counter does not exist yet.** `GameState.failure_count` (`rules_core/reducer.py:22`) is monotonic — it never resets — and is exactly the number MEAS-03 needs (cumulative failures vs. cumulative clock advances). RIG-04's on-screen counter, which explicitly "초기화"s after firing, is a *different*, currently-nonexistent quantity. This phase must add one new derived `GameState` field.
2. **There is no player-character data model.** `Entity`/`StatEntry` (`rules_core/entities.py`) is documented and tested as an enemy/NPC container ("적/NPC 그릇") — every existing usage (`EXAMPLE_SINGLE_STAT_FOE`, `OPENQUEST_GOBLIN`, `OPENQUEST_SKELETON`) is an NPC. `TurnContext.character_state` (`agents/context.py:46`) is just a bare `tuple[StatEntry, ...]` with no owning identity, and `turn_flow.py:139` currently hardcodes it to the placeholder foe's stats. RIG-05 needs a `player_id -> character sheet` mapping that doesn't exist in any layer today.
3. **The CLI's turn flow is built around blocking `input()` prompts** (`cli/turn_flow.py:164-197`, the three-branch D-34/D-35/D-36 confirmation screens) and calls the classifier/narrator SDKs synchronously in a plain function body. None of that can be called as-is from an HTTP handler; the phase must split it into a propose/confirm pair of endpoints and be careful about blocking Uvicorn's single event loop while an LLM call is in flight (Common Pitfalls below).

**Primary recommendation:** FastAPI (thin layer, JSON in/out, reuses pydantic `GameEvent` models directly as response types) + a plain Vite `vanilla-ts` frontend (no framework, no state library — polling + DOM updates only, per CONTEXT.md's explicit "kept minimal" discretion). Add one new `gptrpg.web` package as a sibling to `gptrpg.cli` in the import-linter layering, reusing `session_actor`/`event_log`/`rulebooks` directly the same way `cli` does today.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Poll-based sync of session events (D-38) | API / Backend | Browser / Client | `EventStore.read_events` already does the query; backend just exposes it over HTTP. Client tier only holds `from_seq` and calls `setInterval` |
| Reconnect / full-history refetch (D-41) | Browser / Client | API / Backend | Client decides "I just loaded/refreshed" and requests `from_seq=0`; backend has no special-cased "reconnect" endpoint, same GET handles both |
| "Disconnected" indicator (D-40) | Browser / Client | — | Purely a client-side timer on consecutive poll failures; the backend has no concept of connection state (Constraint: "규칙 계산은 시간을 모른다" / "접속 상태 개념 금지" — this must stay true of `rules_core` and `session_actor`, the *client* is where connection-awareness is allowed to live) |
| Character selection + cookie persistence (D-42/D-43) | Browser / Client | API / Backend | Cookie itself is a browser mechanism; backend only validates the `character_id` sent back on each request against the session's known characters |
| Threat clock display + fail-counter + auto-advance (RIG-04) | API / Backend (`session_actor`) | Browser / Client (render only) | The auto-advance rule must be enforced where the single writer lives (`SessionActor`), not the client — otherwise two clients racing to submit "3rd failure" could double-trigger. Client only renders the numbers the backend returns |
| Character sheet, read-only (RIG-05) | API / Backend | Browser / Client (render only) | Data lives in `rules_core.entities.Entity`; backend serves it, client renders it with no game logic |
| End-of-session aggregation (MEAS-01/MEAS-03, D-44/D-45) | API / Backend (`session_actor`) + CLI | — | Both delivery mechanisms (CLI query, auto-save) read the same derived `GameState`; no web screen involved per D-44 |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|---------------|
| `fastapi` | 0.141.1 [VERIFIED: pip index versions fastapi, run this session — `fastapi (0.141.1)`, 260+ prior releases back to 0.1.0] | HTTP layer: polling GET, action POST endpoints, static frontend serving | Only mainstream async Python web framework with first-class pydantic integration — `GameEvent` (already a pydantic discriminated union, `event_log/schema.py:146-158`) can be used directly as a `response_model` with zero extra serialization code |
| `uvicorn` | 0.52.1 [VERIFIED: pip index versions uvicorn, run this session — 190+ prior releases back to 0.0.1] | ASGI server to run the FastAPI app | Reference ASGI server for FastAPI; no `[standard]` extras needed (those add `uvloop`/`httptools` for perf headroom this 4-person experiment doesn't need) |
| `pydantic` | already a project dependency (`pyproject.toml`) | Request/response models | Already used throughout `event_log/schema.py`; no new modeling library needed |

### Supporting (dev/test only)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `httpx` | 0.28.1 [VERIFIED: pip index versions httpx, run this session] | Required by FastAPI's `TestClient` [CITED: fastapi.tiangolo.com/tutorial/testing/ — "To use `TestClient`, first install `httpx`"] | Add to `[dependency-groups] dev`, not main deps — this project already has a `dev` group (`pyproject.toml`) |
| `vite` | 8.2.0 [VERIFIED: npm view vite version, run this session; `npm view vite time.created` → 2020-04-21, 145.8M weekly downloads] | Frontend dev server + build for the TS client | Standard, zero-config TS build tool; no bundler alternative is simpler for a "screens are out of scope" frontend |
| `typescript` | 7.0.2 [VERIFIED: npm view typescript version, run this session; `npm view typescript time.created` → 2012-10-01, 257.6M weekly downloads] | Frontend language (PROJECT.md constraint: "Python 백엔드 + TypeScript 프런트엔드") | Constraint-mandated, not a choice |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Short polling (D-38, locked) | WebSocket / SSE | Explicitly deferred by D-38 — connection lifecycle management cost isn't recovered by a 2-session, 4-person experiment |
| Vite vanilla-ts (no framework) | React + Vite (`react-ts` template) | React buys component reuse patterns Phase 4 doesn't need — CONTEXT.md discretion explicitly says frontend stack should be "최소한만" since screen/component design is M0-out-of-scope. A framework would add a state-management decision (redux/zustand/context) this phase has no need to make |
| FastAPI's `StaticFiles(html=True)` mount for the built frontend | Separate static file server / CDN | Overkill for 4 users on one machine; `StaticFiles` is built into Starlette (FastAPI's base), zero extra dependency |
| Storing character selection in a plain unsigned cookie | Signed cookie (`itsdangerous`) / server-side session | Trust model is 4 known people sharing one room and one link (D-42) — worst case of a forged `character_id` cookie is viewing another player's *read-only* sheet, not a privilege escalation. Signing this is engineering effort the experiment doesn't need; note as a gap if this code is ever reused past M0 (M1 has real accounts) |

**Installation:**
```bash
# backend (uv-managed, per existing pyproject.toml)
uv add fastapi uvicorn
uv add --dev httpx

# frontend (new directory, e.g. frontend/)
npm create vite@latest frontend -- --template vanilla-ts
```

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|--------------|---------|-------------|
| `fastapi` | pypi | 260+ releases since 0.1.0 (verified via `pip index versions`) | unknown via seam (PyPI JSON API doesn't expose download counts here) | github.com/fastapi/fastapi | [SUS] (seam reason: "too-new" / "unknown-downloads" — see note) | Approved — see note |
| `uvicorn` | pypi | 190+ releases since 0.0.1 | unknown via seam | github.com/Kludex/uvicorn | [SUS] ("too-new") | Approved — see note |
| `httpx` | pypi | 70+ releases since 0.6.7 | unknown via seam | github.com/encode/httpx | [SUS] ("unknown-downloads") | Approved — see note |
| `vite` | npm | created 2020-04-21 | 145.8M/week (verified via `npm view`) | github.com/vitejs/vite | [SUS] ("too-new") | Approved — see note |
| `typescript` | npm | created 2012-10-01 | 257.6M/week (verified via `npm view`) | github.com/microsoft/TypeScript | [SUS] ("too-new") | Approved — see note |

**Note on the SUS verdicts:** the legitimacy seam flags "too-new" using each package's *latest release publish date* (all five had a release within the last several weeks, since they ship frequently), not the package's actual inception date. Direct registry queries this session (`pip index versions`, `npm view <pkg> time.created`) show all five are long-established, extremely high-traffic packages (FastAPI: 260+ releases since 2018; Vite: 145M weekly downloads since 2020; TypeScript: 257M weekly downloads since 2012). This is very likely a heuristic false-positive rather than a real slopsquatting risk. **Per protocol, the planner must still insert a lightweight `checkpoint:human-verify` task before the `uv add`/`npm create` install step** — but that checkpoint can reasonably just confirm "yes, this is the `fastapi.tiangolo.com` project, not a lookalike," which the evidence above already supports.

**Packages removed due to `[SLOP]` verdict:** none.
**Packages flagged as suspicious `[SUS]`:** all five above, disposition Approved with human-verify checkpoint per protocol (see note).

## Architecture Patterns

### System Architecture Diagram

```
                     ┌─────────────────────────────────────────────┐
                     │  Browser (×4, one per player)                │
                     │  - character-select screen (cookie check)    │
                     │  - poll loop: GET /events?from_seq=N (1-2s)  │
                     │  - render: narration feed, clock, fail count,│
                     │    read-only character sheet                 │
                     │  - "disconnected" banner after ~10s of        │
                     │    consecutive poll failures (D-40)           │
                     └───────────────┬───────────────────────────────┘
                                     │ HTTP (JSON)
                                     ▼
                     ┌─────────────────────────────────────────────┐
                     │  FastAPI app (new: gptrpg.web)                │
                     │  GET  /sessions/{id}/events?from_seq=N        │
                     │        -> EventStore.read_events + GameState  │
                     │  POST /sessions/{id}/actions/declare           │
                     │        -> DeclareAction, then classify()       │
                     │           (offloaded to thread, see Pitfall 1) │
                     │        -> returns MoveCandidate proposal(s)    │
                     │  POST /sessions/{id}/actions/confirm           │
                     │        -> ConfirmAction, ResolveCheck,          │
                     │           narrate() loop -> AppendNarration     │
                     │           per sentence (also thread-offloaded) │
                     │  GET  /sessions/{id}/characters/{player_id}    │
                     │        -> read-only Entity sheet (RIG-05)      │
                     └───────────────┬───────────────────────────────┘
                                     │ in-process calls (no network)
                                     ▼
     ┌───────────────────────────────────────────────────────────────┐
     │  SessionActor (existing, session_actor/actor.py)                │
     │  single asyncio.Queue consumer — serializes all 4 players'      │
     │  concurrent POSTs automatically (D-09, already true today)      │
     │  + NEW: after ResolveCheck, checks fails_since_clock >= 3 ->    │
     │    auto-submits AdvanceClock(trigger="fail_counter") inline     │
     │  + NEW: after every processed command, overwrites                │
     │    .gptrpg/reports/{session_id}.json (D-44 auto-save)            │
     └───────────────────────┬───────────────────────────────────────┘
                              ▼
     ┌───────────────────────────────────────────────────────────────┐
     │  EventStore (existing, event_log/store.py) — SQLite, WAL mode  │
     └───────────────────────────────────────────────────────────────┘

     Separately: `gptrpg report --db --session` (new CLI subcommand,
     same pattern as declare/confirm/roll/narrate/clock/ai) reads the
     store standalone and prints + writes the same JSON (D-44 CLI leg).
```

### Recommended Project Structure
```
src/gptrpg/
├── web/                      # NEW — sibling to cli/, same layer in import-linter
│   ├── __init__.py
│   ├── app.py                # FastAPI() instance, mounts StaticFiles for built frontend
│   ├── routes_events.py      # GET /sessions/{id}/events (polling endpoint)
│   ├── routes_actions.py     # POST declare / confirm (splits turn_flow's blocking flow)
│   ├── routes_characters.py  # GET /sessions/{id}/characters/{player_id} (RIG-05)
│   └── report.py             # shared aggregation-building function (used by CLI report too)
├── cli/
│   └── main.py                # + new `report` subcommand reusing web/report.py's function
└── session_actor/
    └── actor.py                # + fails_since_clock auto-advance, + auto-save hook

frontend/                       # NEW — separate npm project (Vite vanilla-ts)
├── src/main.ts
├── index.html
└── package.json
```

### Pattern 1: Reuse `GameEvent` pydantic models as FastAPI response types directly
**What:** `event_log/schema.py`'s `GameEvent` is already `Annotated[Union[...], Field(discriminator="event_type")]` wrapped in a `TypeAdapter`. FastAPI/pydantic can serialize a `list[GameEvent]` (or a wrapper model containing one) as a response body with correct per-type field validation, with no hand-written serialization.
**When to use:** the polling endpoint's response body.
**Example (schema shape, not hand-verified against a running FastAPI instance this session — mark MEDIUM):**
```python
from pydantic import BaseModel
from gptrpg.event_log.schema import GameEvent

class PollResponse(BaseModel):
    events: list[GameEvent]
    state: "GameStateView"   # plain field mirror of rules_core.reducer.GameState

@app.get("/sessions/{session_id}/events")
def poll_events(session_id: str, from_seq: int = 0) -> PollResponse:
    events = store.read_events(session_id, from_seq=from_seq)
    state = rebuild_state(store, session_id)   # session_actor/projection.py, already exists
    return PollResponse(events=events, state=GameStateView(**dataclasses.asdict(state)))
```
**Don't hand-roll a second event schema for the wire format** — reuse the one `event_log` already declares (single source of truth for what a "sentence chunk" / "check result" event looks like, matches project convention that `rules_core`/`event_log` are the only place game truth is declared).

### Pattern 2: Split the CLI's blocking turn flow into propose/confirm endpoints
**What:** `cli/turn_flow.py._turn_flow` (lines 219-402) does declare → classify → (blocking `input()` for D-34/D-35/D-36) → resolve → narrate, all in one synchronous function. For the web version this must become two HTTP round trips, because the *player's browser* needs to render candidate moves and wait for a human click, which a single backend call cannot do.
**When to use:** any endpoint that needs the classifier's proposal shown to a human before commit.
**Recommended shape:**
- `POST /sessions/{id}/actions/declare {player_id, raw_text}` → submits `DeclareAction`, runs `classify()`, returns `{tier, candidates: [...]}` (mirrors `Proposal.tier`, `agents/action_classifier.py` — already the exact data the CLI's three branches consume, just returned as JSON instead of printed)
- `POST /sessions/{id}/actions/confirm {player_id, move, stat, confirmed, declare_seq}` → submits `ConfirmAction`; if `confirmed`, submits `ResolveCheck` then runs the `narrate()` loop, submitting `AppendNarration` per sentence exactly as `turn_flow.py:343-385` already does — this part **is** reusable almost verbatim, only the `input()`-driven parts are not.

### Pattern 3: New `gptrpg.web` import-linter layer, sibling to `cli`
**What:** `.importlinter` contract 2 (verified, `.importlinter:12-18`) currently declares:
```
[importlinter:contract:2]
type = layers
layers =
    gptrpg.cli
    gptrpg.agents
    gptrpg.session_actor
    gptrpg.rulebooks
    gptrpg.rules_core | gptrpg.event_log
```
`gptrpg.web` needs to call `session_actor`/`event_log`/`rulebooks` directly, exactly the way `cli` does today — it must not be layered *below* `cli` (no reason for `web` to import `cli`) nor *above* it in a way that lets `cli` import `web`. The correct fix is to make them co-equal:
```
layers =
    gptrpg.cli | gptrpg.web
    gptrpg.agents
    gptrpg.session_actor
    gptrpg.rulebooks
    gptrpg.rules_core | gptrpg.event_log
```
**Also required:** add `"src/gptrpg/web/*" = ["TID251"]` to `pyproject.toml`'s `[tool.ruff.lint.per-file-ignores]` (verified list currently only exempts `event_log/session_actor/cli/agents/tests`, `pyproject.toml:33-38`) — `gptrpg.web` will import `asyncio`/`pathlib` (for static file paths) which the global TID251 ban list forbids everywhere except the exempted directories.

### Anti-Patterns to Avoid
- **Re-implementing the reducer's fold logic in TypeScript:** the frontend must never independently compute `turn_count`/`failure_count`/`clock_segment` from raw events — always render the `GameState` snapshot the backend already computed via `rebuild_state`. Two implementations of the same fold logic in two languages is exactly the kind of duplication D-08 ("중간 저장 없이 매번 재구성") was designed to prevent from ever diverging.
- **A per-player link/token:** explicitly excluded by D-42 — don't build per-URL identity even as a "nice to have," it directly contradicts the locked decision and the Deferred Ideas list.
- **Blocking the FastAPI event loop with `input()`-style interactive prompts carried over from the CLI:** the confirmation UX must be two separate requests (Pattern 2), never a server-side `input()` call (which would hang the whole process waiting for terminal stdin that no browser client can provide).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| Wire-format schema for events | A second hand-written JSON schema/serializer | `event_log.schema.GameEvent` (pydantic, already `extra="forbid"`) used directly as the response type | Single source of truth for event shape; a second schema drifts the moment `EVENT_SCHEMA_VERSION` bumps and nobody remembers to update the web copy |
| Cursor/since-based sync protocol | A custom "delta packet + ack" protocol (the *deferred* v1 design in `design-plan.md` §3.6) | The plain `from_seq` query param against `EventStore.read_events` | [CITED via WebSearch, LOW confidence — general REST polling literature] the standard "cursor" pattern for polling is exactly "client sends last-seen id, server returns strictly-newer items," which `read_events(session_id, from_seq)`'s inclusive-boundary semantics already implement precisely (verified, `event_log/store.py:93-103`, docstring: "경계는 포함이다") |
| SPA static file serving | A hand-rolled catch-all file-reading route | `starlette.staticfiles.StaticFiles(directory=..., html=True)` mounted at `/` [CITED: fastapi.tiangolo.com/tutorial/static-files/] | Built into the dependency you already have (Starlette ships inside FastAPI); `html=True` gives SPA-style fallback to `index.html` for free |
| Character-selection identity | A mini auth/session system (JWT, server sessions, etc.) | A plain unsigned cookie holding `{session_id, character_id}` (D-43) | Explicitly out of scope per Out of Scope ("결제·계정") — the trust model is 4 people in one room with one link, not a multi-tenant system |

**Key insight:** almost everything this phase needs is already implemented one layer down (Phases 1-3). The actual net-new code is small: an HTTP shim, one new `GameState` field (fails_since_clock), one new small character-data association, and splitting one function's control flow across two HTTP calls. Resist the temptation to design a bigger sync/reconnect protocol than `from_seq` — that temptation is exactly what the *deferred* v1 chunk-and-ack design (§3.6, superseded by D-38) fell into.

## Common Pitfalls

### Pitfall 1: Blocking the single asyncio event loop during AI calls
**What goes wrong:** `action_classifier.classify()` and `agents.master_gm.narrate()` call provider SDKs (`openai`, `anthropic`, etc.) synchronously — verified by reading `cli/turn_flow.py:244-255` and `343-358`, which call them as plain blocking functions/generators (`next(narration_iter, ...)`), not `await`ed coroutines. If a FastAPI `async def` endpoint calls these directly, Uvicorn's single-threaded event loop is blocked for the entire 2-15+ second duration of an LLM call (MEAS-02's own documented latency range) — during that window, **all 4 players' polling GET requests stall**, not just the one who submitted the action, because `SessionActor` and the event loop are shared per-process (required by D-09's single-writer invariant, which rules out running multiple worker processes for this session).
**Why it happens:** synchronous SDK calls (or their generator wrappers) don't yield control back to the event loop the way `await`ed I/O does.
**How to avoid:** wrap each blocking call in `await asyncio.to_thread(...)` (e.g. `await asyncio.to_thread(next, narration_iter, _NO_SENTENCE)` per sentence) so the event loop stays free between chunks; keep the actual `await actor.submit(...)` calls on the main event loop as they are today (they're already `async`). Do **not** offload `store.read_events()`/`actor.submit()` themselves to a worker thread — `sqlite3.Connection` objects are thread-affine by default (`check_same_thread=True`, the default `EventStore.initialize()` uses, verified `event_log/store.py:41`), and mixing threads there risks `ProgrammingError`. Keep all `EventStore`/`SessionActor` access on the one thread that created the connection; only the blocking third-party SDK calls should move to a worker thread.
**Warning signs:** during manual QA, one player's turn takes 8 seconds and all 4 browsers' "last updated" timestamps freeze for those 8 seconds even though only one player acted.

### Pitfall 2: Treating `GameState.failure_count` as the RIG-04 display counter
**What goes wrong:** re-using the existing `failure_count` field (cumulative, never resets — verified `rules_core/reducer.py:22`, `85-91` shows `clock_advanced` never touches it) as the on-screen "실패 카운터" that RIG-04 requires to reset to 0 after the clock advances. Doing so makes the UI counter climb forever across the whole session instead of showing "how close are we to the next forced advance right now."
**Why it happens:** CONTEXT.md's code_context section optimistically states the existing fields "이미 리듀서에서 계산되어 나온다" for RIG-04 — true for `clock_segment`/`clock_advances`, **not** true for the resettable fail-streak, which is a distinct quantity from `failure_count` and does not exist yet.
**How to avoid:** add a second `GameState` field (e.g. `fails_since_clock: int`) that increments on `check_resolved` with `counts_as_failure=True` and resets to `0` on any `clock_advanced` event (regardless of trigger). Keep `failure_count` untouched — MEAS-03's ratio (실패 대비 시계 진행) needs the cumulative number, not the resettable one.
**Warning signs:** a `test_reducer_failure_count.py`-style test asserting the display counter resets after 3 failures fails because the field it's checking never goes back to 0.

### Pitfall 3: Assuming `Entity`/`StatEntry` already models player characters
**What goes wrong:** planning RIG-05 as "just render the existing `Entity`" without noticing every current usage and every docstring (`rules_core/entities.py:1-8`: "적/NPC 그릇") is about enemies/NPCs, and `TurnContext.character_state` is a bare stat tuple with no name/id/rulebook association (`agents/context.py:41-48`).
**Why it happens:** the shapes are structurally identical (a name + stats), so it's easy to assume the concept is shared — but there is currently no code path that maps a `player_id` to a character's `Entity`/stats; `turn_flow.py:139` hardcodes the placeholder foe's stats for every player.
**How to avoid:** decide explicitly (flagged as an open question below) whether player characters reuse the `Entity` dataclass (recommended — same four-field shape already fits, per D-20/D-21's "그릇 하나로 열 개든 하나든" philosophy) with a new `player_id -> Entity` lookup the web layer owns (probably a hand-authored JSON/dict loaded at startup, matching EXP-01's "캐릭터 4개... 손으로 준비").
**Warning signs:** RIG-05's success criterion ("자기 캐릭터 시트를 읽기 전용으로 열어 볼 수 있다") can't be satisfied because there's no per-player data to open in the first place — only one shared placeholder foe.

### Pitfall 4: Re-litigating the connection/reconnect protocol as more than a `from_seq` param
**What goes wrong:** over-engineering per-packet acks, sequence-gap detection, or a resume-token scheme — this is exactly the deferred v1 design (`design-plan.md` §3.6) that D-38/D-41 replaced with "just refetch and re-poll."
**Why it happens:** the phrase "이어붙이는 규칙" in the phase's원문 sounds like it wants a merge algorithm; D-41 already answered it (always `from_seq=0`, no incremental resume).
**How to avoid:** the entire "reconnect" feature is: on page load, call the same polling endpoint with `from_seq=0` and render everything returned, then continue polling with the latest seq seen. No special reconnect code path.

## Code Examples

### FastAPI serving the built frontend + polling API side by side
```python
# Source: pattern synthesized from fastapi.tiangolo.com/tutorial/static-files/ (WebSearch, LOW confidence — verify against current docs at plan time)
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()
app.include_router(events_router, prefix="/api")
app.include_router(actions_router, prefix="/api")
app.include_router(characters_router, prefix="/api")
# Mounted LAST so /api/* routes above take precedence over the SPA catch-all
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")
```

### Cookie set/read for character selection (D-43)
```python
# Source: pattern synthesized from fastapi.tiangolo.com/advanced/response-cookies/ (WebSearch, LOW confidence — verify against current docs at plan time)
import json
from fastapi import Response, Request

COOKIE_NAME = "gptrpg_character"

@app.post("/api/sessions/{session_id}/select-character")
def select_character(session_id: str, character_id: str, response: Response):
    response.set_cookie(
        key=COOKIE_NAME,
        value=json.dumps({"session_id": session_id, "character_id": character_id}),
        max_age=60 * 60 * 24 * 14,  # 14 days — covers the 1-week gap between EXP-03's two sessions with margin
        httponly=True,
        samesite="lax",
    )

@app.get("/api/sessions/{session_id}/my-character")
def my_character(session_id: str, request: Request):
    raw = request.cookies.get(COOKIE_NAME)
    if raw is None:
        return {"selected": False}
    saved = json.loads(raw)
    if saved.get("session_id") != session_id:
        return {"selected": False}  # cookie belongs to a different game
    return {"selected": True, "character_id": saved["character_id"]}
```

### Auto-advance clock hook inside `SessionActor` (RIG-04)
```python
# Sketch based on verified session_actor/actor.py:197-213 (_process) structure — not yet implemented, planner's job
AUTO_ADVANCE_FAILURE_THRESHOLD = 3  # D-21 default ("N회 기본 3, 시계별 조절") — per-scenario override is out of scope this phase

async def _process(self, command: Command) -> int:
    event_type, caused_by_seq, fields = self._prepare(command)
    seq = self._store.next_seq(self._session_id)
    event = _EVENT_CLASSES[event_type](
        session_id=self._session_id, seq=seq, schema_version=EVENT_SCHEMA_VERSION,
        caused_by_seq=caused_by_seq, recorded_at=utc_now_iso(), event_type=event_type, **fields,
    )
    self._store.append(event)
    self.state = apply_event(self.state, event.event_type, event.model_dump())

    if event_type == "check_resolved" and self.state.fails_since_clock >= AUTO_ADVANCE_FAILURE_THRESHOLD:
        await self._process(AdvanceClock(
            clock_id=self._clock_id,
            segment_index=self.state.clock_segment + 1,
            trigger="fail_counter",
            caused_by_seq=seq,
        ))
    self._write_report_snapshot()  # D-44 auto-save, see below
    return seq
```

### Report aggregation (shared by CLI `report` subcommand and the auto-save hook, D-44/D-45)
```python
# Sketch — reuses existing GameState fields exclusively, verified rules_core/reducer.py:14-28
import json
from dataclasses import asdict
from pathlib import Path
from gptrpg.event_log.schema import utc_now_iso

def build_report(state: GameState) -> dict:
    ratio = (state.failure_count / state.clock_advances) if state.clock_advances else None
    return {
        "session_id": state.session_id,
        "generated_at": utc_now_iso(),
        "event_count": state.last_seq + 1,
        "turn_count": state.turn_count,
        "check_count": state.check_count,
        "failure_count": state.failure_count,          # MEAS-03 numerator
        "clock_segment": state.clock_segment,
        "clock_advances": state.clock_advances,          # MEAS-03 denominator
        "failure_to_clock_ratio": ratio,                 # MEAS-03
        "narration_count": state.narration_count,
        "ai_calls": state.ai_calls,
        "total_tokens": state.total_tokens,              # MEAS-01
        "last_grade": state.last_grade,
    }

def write_report(state: GameState, base_dir: Path = Path(".gptrpg/reports")) -> Path:
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / f"{state.session_id}.json"
    path.write_text(json.dumps(build_report(state), ensure_ascii=False, indent=2), encoding="utf-8")
    return path
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|-------------------|---------------|--------|
| v1 design's per-packet chunk + sequence-numbered ack + delta-resend on reconnect (`design-plan.md` §3.6) | Plain `from_seq` cursor polling, full refetch on reconnect (D-38/D-41) | This phase's context-gathering session (2026-08-03) | Removes an entire protocol layer; `EventStore.read_events` already does everything needed with the boundary-inclusive semantics it already has |
| v1 design's turn-timer / speaking-lock coordination (`design-plan.md` §3.3) | None — coordination happens in an external messenger (D-10) | Locked before this phase (D-10) | Phase 4 must not build any turn-order enforcement UI at all |

**Deprecated/outdated:** the `design-plan-v1-archive.md` file describes a fuller real-time protocol (chunked delivery + acks) — per PROJECT.md, this file is explicitly archived/superseded and must not be read as a live spec.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|----------------|
| A1 | Player characters should reuse the existing `Entity`/`StatEntry` dataclasses (rather than a new bespoke "PlayerCharacter" type) for RIG-05 | Pitfall 3 / Architecture Patterns | If wrong, RIG-05's read-only sheet either duplicates the `Entity` shape unnecessarily or the planner discovers mid-phase that `Entity`'s NPC-flavored docstrings/tests block reuse, forcing a redesign |
| A2 | Auto-advance clock threshold is a hardcoded constant (3, D-21's stated default) rather than a per-scenario configurable value this phase | Code Examples (auto-advance hook) | Low risk — D-21 explicitly allows "시계별 조절" as a future refinement; hardcoding the default is consistent with M0's "룰북 데이터의 필드 단위 규격... 전부 M0 밖" boundary |
| A3 | No maximum-segment cap exists or is needed on `clock_segment` this phase (nothing in `rules_core` enforces a ceiling today) | Pitfall / Open Questions | If a scenario's clock only has 4 segments and 3+ consecutive failures happen after the last one, `clock_segment` could increment past the scenario's actual segment count with nothing catching it — low probability in one 3-4hr session but not zero |
| A4 | The auto-save aggregation file should be rewritten after every `SessionActor`-processed command (not just at some explicit "session end" signal) | Code Examples (report hook) | There is no `session_ended` event type in the six-event schema (verified `event_log/schema.py:146-155`) — "session end" is not a moment the system can detect precisely. Rewriting after every command is the safest way to guarantee D-44's "누가 조회 명령을 안 쳐도 남게" property; if this assumption is wrong (e.g. too much I/O overhead), the fallback is rewriting only after `clock_advanced`/`ai_invoked` events |
| A5 | Cookie should not be cryptographically signed (plain JSON value) | Code Examples (cookie) / Alternatives Considered | If the experiment is ever run with less-trusted participants, an unsigned cookie lets a player claim another player's character_id and view their (read-only) sheet — low severity since RIG-05 is view-only, but worth flagging before this code is ever reused past M0 |
| A6 | `uvicorn` should be installed without the `[standard]` extra | Standard Stack | If poll latency under concurrent load turns out to matter more than expected at 4 users, `uvloop`/`httptools` could be added later with zero code changes — pure performance headroom, not a correctness risk |

**If this table is empty:** N/A — see items above; all require light confirmation before the planner locks task-level decisions on them.

## Open Questions

1. **Does the character-sheet data (RIG-05) get hand-authored as Python module constants (like `EXAMPLE_SINGLE_STAT_FOE`) or as a loaded JSON/YAML file the web server reads at startup?**
   - What we know: EXP-01 says characters are prepared by hand ("캐릭터 4개 중 절반"); the existing precedent (`rulebooks/dungeonworld_like.py`, `rulebooks/openquest_creatures.py`) hardcodes example `Entity` instances as Python constants.
   - What's unclear: whether the web layer should own a small `player_id -> Entity` dict as Python source (matching existing precedent, fastest to implement) or read an external data file (more flexible, closer to how a real scenario/character file would eventually work in M1).
   - Recommendation: Python module constant for M0 (matches every existing precedent in this codebase, zero new file-parsing code), explicitly flagged as throwaway/M0-only in a comment, same spirit as `_PLACEHOLDER_CLOCK_SEGMENT_COUNT` in `turn_flow.py:38-42`.

2. **Where does the `clock_id` used for auto-advance come from when no `AdvanceClock` has ever been submitted yet in a session?**
   - What we know: `SessionActor` has no persisted `clock_id` field; `ClockAdvanced` events carry `clock_id` but `GameState` doesn't retain the last one used (verified `reducer.py:85-91` only tracks `clock_segment`/`clock_advances`, not `clock_id`).
   - What's unclear: whether to bind `clock_id` at `SessionActor` construction time (single default clock per session, matching EXP-01's "위협 시계 1개") or read it from the first `ClockAdvanced` ever submitted.
   - Recommendation: bind at construction (`SessionRegistry.get_or_create(session_id, clock_id="threat")`, default `"threat"` matching the existing `turn_flow.py:133` convention) — simplest, matches the one-clock-per-session experiment scope (EXP-01), and needs no chicken-and-egg lookup for the very first auto-trigger.

3. **Exact frontend build/serve wiring: does FastAPI serve Vite's `dist/` output directly, or does the plan assume `npm run dev`'s separate dev server (with a proxy) during development?**
   - What we know: for the 4-person experiment, a single deployed FastAPI process serving the built static bundle is simplest operationally (one process, one URL, one link to share per D-42).
   — What's unclear: whether the planner wants a dev-mode Vite proxy setup for iteration speed during implementation (common in modern web dev) in addition to the production single-process serving.
   - Recommendation: plan for both — `StaticFiles` mount for the "real" deployed link (D-42's "링크 하나"), and note that `npm run dev` + a Vite proxy config pointing `/api` at the FastAPI port is a normal dev-time convenience that doesn't change the shipped architecture.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|--------------|-----------|---------|----------|
| Python | Backend (FastAPI/Uvicorn) | ✓ | 3.13.5 (project requires ≥3.11) | — |
| `uv` | Dependency management (existing convention, `pyproject.toml` build-system) | ✓ | 0.11.28 | — |
| Node.js | Frontend build (Vite) | ✓ | v22.23.1 | — |
| npm | Frontend package management | ✓ | 12.0.1 | — |
| `sqlite3` CLI | Manual DB inspection during development (optional) | ✗ | — | Not required — `EventStore` uses Python's stdlib `sqlite3` module exclusively; the CLI binary is a developer-convenience-only nice-to-have |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** `sqlite3` CLI (use `python3 -c "import sqlite3; ..."` or a one-off script if manual DB inspection is ever needed).

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 + pytest-asyncio 1.4.0 (both already project dev dependencies, `pyproject.toml`) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — `testpaths = ["tests"]`, `asyncio_mode = "auto"` (verified) |
| Quick run command | `uv run pytest tests/test_web_*.py -q` (new files this phase) |
| Full suite command | `uv run pytest -q` |

**Note:** FastAPI's `TestClient` (once `httpx` dev dependency is added) is fully synchronous to call — new endpoint tests do **not** need `pytest-asyncio` even though the endpoints themselves are `async def` [CITED: fastapi.tiangolo.com/tutorial/testing/].

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|--------------------|--------------|
| RIG-04 | Failure counter resets to 0 and clock auto-advances after 3rd consecutive failure since last advance | unit (reducer) | `uv run pytest tests/test_reducer_fails_since_clock.py -x` | ❌ Wave 0 |
| RIG-04 | `SessionActor` auto-injects `AdvanceClock` after the 3rd failure | integration (actor) | `uv run pytest tests/test_session_actor_auto_advance.py -x` | ❌ Wave 0 |
| RIG-05 | `GET /sessions/{id}/characters/{player_id}` returns the correct read-only sheet | integration (web, `TestClient`) | `uv run pytest tests/test_web_characters.py -x` | ❌ Wave 0 |
| RIG-07 | Polling endpoint returns events with `seq >= from_seq`, boundary inclusive | integration (web, `TestClient`) | `uv run pytest tests/test_web_events.py -x` | ❌ Wave 0 |
| RIG-07 | `from_seq=0` after a "reconnect" returns full history unchanged | integration (web, `TestClient`) | `uv run pytest tests/test_web_events.py -x` | ❌ Wave 0 (same file) |
| MEAS-01 | Auto-saved JSON report contains `total_tokens`/`turn_count` matching a hand-built fixture session | unit (report builder) | `uv run pytest tests/test_report.py -x` | ❌ Wave 0 |
| MEAS-03 | `failure_to_clock_ratio` computed correctly, including the `clock_advances == 0` (null) edge case | unit (report builder) | `uv run pytest tests/test_report.py -x` | ❌ Wave 0 (same file) |

### Sampling Rate
- **Per task commit:** the relevant `uv run pytest tests/test_web_*.py -q` / `tests/test_reducer_*` subset
- **Per wave merge:** `uv run pytest -q` (full suite)
- **Phase gate:** full suite green before `/gsd-verify-work`; additionally, a manual live QA pass with 2+ real browser tabs against a running `uvicorn` instance is warranted given D-38/D-40's timing behavior (polling cadence, disconnect banner) is not meaningfully unit-testable

### Wave 0 Gaps
- [ ] `tests/test_reducer_fails_since_clock.py` — covers RIG-04's new `GameState` field (mirrors the existing style of `tests/test_reducer_failure_count.py`, verified read this session)
- [ ] `tests/test_session_actor_auto_advance.py` — covers the actor-level auto-injection (mirrors `tests/test_session_actor.py`'s existing `AdvanceClock` test pattern, verified read this session, lines 142-155/397-425)
- [ ] `tests/test_web_events.py`, `tests/test_web_characters.py` — new, need FastAPI `TestClient` fixture
- [ ] `tests/test_report.py` — new, pure-function unit tests against `build_report(state)`
- [ ] Framework install: `uv add --dev httpx` (required for `TestClient`, not yet in `pyproject.toml`'s dev group)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | No | No accounts (Out of Scope: "결제·계정") — the shared link + cookie is identity-lite by design, not authentication |
| V3 Session Management | Partial | The `gptrpg_character` cookie is the only session-like artifact; use `httponly`, `samesite="lax"`; no `Secure` flag possible without HTTPS, which this experiment (LAN/single-room, per CONTEXT.md's "4명이 같은 방에 있을 가능성이 높다") likely won't have — acceptable given the trust model, but flag if this code path is ever exposed over the public internet |
| V4 Access Control | Partial | Any of the 4 players can view any character's sheet if they guess/forge another `character_id` (A5 above) — acceptable for RIG-05 (read-only, no write capability gated by this), not acceptable if this becomes a real product surface |
| V5 Input Validation | Yes | Player free-text (`raw_text`) flows into an LLM prompt exactly as it did in Phase 3 (already covered by Phase 3's Security Domain — D-14 keeps `rules_core` from ever trusting LLM-emitted numbers); the *new* surface this phase adds is that `raw_text` now also arrives over untrusted HTTP instead of a trusted local CLI argument — FastAPI/pydantic request validation (`str` type, length limits) should be applied at the endpoint boundary |
| V6 Cryptography | No | No new cryptographic primitive introduced; the character-selection cookie is deliberately unsigned (A5) |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|-----------------------|
| Reflected XSS via AI-generated or player-submitted narration text rendered into the DOM | Tampering / Information Disclosure | The frontend must render narration/`raw_text` using `textContent` (or a templating approach that escapes by default), never `innerHTML` — this is a *new* risk this phase introduces (Phase 3 only ever printed to a terminal, which has no script-execution context) |
| Cookie/session forgery (A5) | Spoofing | Accepted risk for M0 given the trust model (documented above); do not carry this pattern forward into M1's real-account system |
| Unbounded polling load from a misbehaving client (e.g. a buggy tab polling every 100ms instead of 1-2s) | Denial of Service | Not a concern at 4-user scale this phase; note as a non-issue explicitly so nobody adds unneeded rate-limiting complexity |
| CORS misconfiguration if frontend and backend are ever served from different origins during development | Tampering | If using a Vite dev-server proxy (Open Question 3), configure the proxy so the browser only ever talks to one origin — avoids needing a CORS policy on the FastAPI app at all for this experiment's scope |

## Sources

### Primary (HIGH confidence)
- `/home/alpha-pi/GPTRPG/src/gptrpg/event_log/store.py` — read in full this session, lines cited inline
- `/home/alpha-pi/GPTRPG/src/gptrpg/event_log/schema.py` — read in full this session, lines cited inline
- `/home/alpha-pi/GPTRPG/src/gptrpg/rules_core/reducer.py` — read in full this session, lines cited inline
- `/home/alpha-pi/GPTRPG/src/gptrpg/rules_core/entities.py` — read in full this session, lines cited inline
- `/home/alpha-pi/GPTRPG/src/gptrpg/session_actor/actor.py` — read in full this session, lines cited inline
- `/home/alpha-pi/GPTRPG/src/gptrpg/cli/main.py`, `src/gptrpg/cli/turn_flow.py` — read in full this session, lines cited inline
- `/home/alpha-pi/GPTRPG/src/gptrpg/agents/context.py` — read in full this session, lines cited inline
- `/home/alpha-pi/GPTRPG/.importlinter`, `/home/alpha-pi/GPTRPG/pyproject.toml` — read in full this session, lines cited inline
- `/home/alpha-pi/GPTRPG/tests/test_reducer_failure_count.py`, `tests/test_session_actor.py` — read this session to confirm no existing reset/auto-advance test coverage
- `pip index versions fastapi/uvicorn/httpx`, `npm view vite/typescript version + time.created` — run live this session against PyPI/npm

### Secondary (MEDIUM confidence)
- `docs/GPTRPG-M0-decisions.md` D21 (threat clock structure, 3-rule combination, "초기화" language), D22 (character creation scope boundary), D31 (per-turn context fields) — read this session, quoted inline

### Tertiary (LOW confidence — WebSearch only, no MCP docs provider configured this session; verify against current official docs at plan/implementation time)
- FastAPI `TestClient`/httpx dependency — fastapi.tiangolo.com/tutorial/testing/
- FastAPI static file / SPA serving — fastapi.tiangolo.com/tutorial/static-files/
- FastAPI cookie set/read — fastapi.tiangolo.com/advanced/response-cookies/
- Vite `vanilla-ts` scaffolding command — vite.dev/guide/
- Short-polling cursor/since-id pattern — general REST API design literature (no single authoritative source; matches this project's existing `from_seq` semantics)

## Metadata

**Confidence breakdown:**
- Standard stack (FastAPI/Uvicorn/Vite/TypeScript versions): HIGH — versions verified directly against PyPI/npm this session
- Standard stack (specific FastAPI usage patterns — TestClient, StaticFiles, cookies): MEDIUM — no MCP docs provider (context7/ref/jina) was configured this session (`exa_search`/`brave_search`/`firecrawl` all `false` per `init.phase-op`), so these are WebSearch-sourced summaries pointing at official doc URLs, not directly fetched/verified page content
- Architecture (event/reconnect/auto-advance/character-sheet gaps): HIGH — every specific gap identified (fails_since_clock, character data model, blocking-call risk, layering) is backed by direct reads of the actual source files this session, with line numbers and verbatim quotes
- Pitfalls: HIGH — all four are derived from reading actual existing code (`turn_flow.py`, `reducer.py`, `entities.py`, `store.py`), not speculation

**Research date:** 2026-08-03
**Valid until:** 30 days for the architectural findings (code-grounded, won't go stale); 7-14 days for the exact FastAPI/Vite doc-usage patterns marked LOW/MEDIUM confidence — re-verify against official docs before implementation if this research is more than ~2 weeks old
