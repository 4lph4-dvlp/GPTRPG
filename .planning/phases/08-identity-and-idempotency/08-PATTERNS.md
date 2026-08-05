# Phase 8: 신원 검증과 멱등성 - Pattern Map

**Mapped:** 2026-08-06
**Files analyzed:** 12 (backend 6 modified/new, tests 4, frontend 3 flagged deferred)
**Analogs found:** 10 / 12 (frontend files deferred — no analog needed this phase per FE-03/Phase16 boundary; verify scope before touching)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `src/gptrpg/web/cookie_auth.py` (NEW) | utility (crypto/security) | transform (sign/verify) | `src/gptrpg/web/routes_characters.py` (json cookie read/write, lines 143-190) | role-match (closest wiring analog; no prior signing module exists) |
| `src/gptrpg/web/routes_characters.py` (MODIFIED) | route/controller | request-response | itself (existing `select_character`/`my_character`, lines 143-190) | exact (in-place extension) |
| `src/gptrpg/web/routes_actions.py` (MODIFIED) | route/controller | request-response | itself (existing `declare`/`confirm`, lines 152-473) | exact (in-place extension) |
| `src/gptrpg/session_actor/actor.py` (MODIFIED — new `OccupyCharacter` command + `_prepare_occupy`, extend `_prepare_confirm`) | service (single-writer command processor) | event-driven | itself — `_prepare_declare`/`_prepare_confirm` pattern (lines 349-408), `_validate_caused_by` (366-376) | exact (same file, same dispatch table pattern) |
| `src/gptrpg/event_log/schema.py` (MODIFIED — version 4→5, new `CharacterOccupied`, extend 3 events) | model (event schema) | event-driven | itself — `EVENT_SCHEMA_VERSION` docstring precedent (lines 18-35), existing event classes (82-115) | exact |
| `src/gptrpg/rules_core/reducer.py` (MODIFIED — old-format read path) | transform (event → state fold) | event-driven | itself — `_legacy_v1_counts_as_failure` + version-gated branch in `apply_event` (lines 76-105) | exact |
| `src/gptrpg/web/characters_data.py` (MODIFIED — verify use) | config/data | CRUD (read-only lookup) | itself — `get_character`/`list_characters` (imported by both route files) | exact (likely only consumed, not structurally changed — verify during planning) |
| `frontend/src/screens/SessionScreen.tsx` (flagged) | component | request-response | N/A — out of primary pattern scope; FE-03 real-time refresh deferred to Phase 16, but `player_id===character_id` split (D-03) may still require a minimal response-shape update here | no strong analog needed — verify scope in plan |
| `frontend/src/api/client.ts` (flagged) | service (API client) | request-response | N/A | same as above |
| `frontend/src/api/types.ts` (flagged) | model (TS types) | transform | N/A | same as above |
| `tests/conftest.py` (MODIFIED) | test fixture | batch/event-driven | itself — `_env()` envelope builder + `_t()` fixed-clock helper (lines 40-60), `fake_session_log` construction pattern | exact |
| `tests/test_session_actor.py` (MODIFIED) | test | event-driven | itself — existing `_prepare_*` unit tests + `asyncio.gather` concurrency pattern (line ~186-190) | exact |
| `tests/test_web_actions.py` (MODIFIED) | test | request-response | itself — existing declare/confirm HTTP test patterns | exact |
| `tests/test_web_characters.py` (MODIFIED) | test | request-response | itself — existing cookie read/write test patterns | exact |

## Pattern Assignments

### `src/gptrpg/web/cookie_auth.py` (NEW — utility, transform)

**Analog:** `src/gptrpg/web/routes_characters.py` (module docstring + `select_character`/`my_character`), plus RESEARCH.md's own worked-out stdlib design (already VERIFIED against this repo's conventions).

**Imports pattern** — match the plain-stdlib, no-new-dependency style already used in `web/` (`routes_characters.py:27-36` imports `json`, `dataclasses.asdict`, `pathlib.Path` — no external crypto libs):
```python
import base64
import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path
```

**Secret loading pattern** — mirror `EventStore`'s `db_path` construction and the `.gptrpg/` directory convention (already gitignored, `app.py` uses `.gptrpg/events.db` as default). Place secret at `.gptrpg/cookie_secret`, loaded in `lifespan()` (see `web/app.py:91-96` where `app.state.store` is built), not at import time — same reasoning `app.py`'s own docstring gives for `check_dir=False` on the media mount (avoid import-time filesystem side effects):
```python
def load_or_create_secret(
    path: Path, *, env_var: str = "GPTRPG_COOKIE_SECRET", environ: dict = os.environ
) -> bytes:
    if env_var in environ:
        return environ[env_var].encode("utf-8")
    if path.is_file():
        return path.read_bytes()
    secret = secrets.token_bytes(32)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(secret)
    return secret
```

**Sign/verify core pattern** — `hmac.compare_digest` is mandatory (see Don't Hand-Roll in RESEARCH.md); failure mode must match `my_character()`'s "silently fall back, never raise" convention (`routes_characters.py:172-190`, specifically the `except (json.JSONDecodeError, TypeError, ValueError):` pattern at line 181):
```python
def verify_cookie(raw: str, *, secret: bytes) -> dict | None:
    try:
        body, signature = raw.rsplit(".", 1)
    except ValueError:
        return None
    expected = hmac.new(secret, body.encode("ascii"), digestmod="sha256").hexdigest()
    if not hmac.compare_digest(expected, signature):
        return None
    try:
        padded = body + "=" * (-len(body) % 4)
        return json.loads(base64.urlsafe_b64decode(padded))
    except (ValueError, UnicodeDecodeError):
        return None
```

**Error-message hygiene (QUAL-05):** never interpolate the raw cookie/secret/signature into an exception or log string — this file's docstring precedent is `routes_characters.py:16-24` which already states the M0 trust model explicitly. Follow the same restraint `_prepare_ai_call` uses in `actor.py:508-511` (states the *kind* of mismatch, never the value).

---

### `src/gptrpg/web/routes_characters.py` (MODIFIED — controller, request-response)

**Analog:** itself, extending in place.

**Cookie-write pattern to replace** (lines 156-163, currently unsigned):
```python
response.set_cookie(
    key=COOKIE_NAME,
    value=json.dumps({"session_id": session_id, "character_id": body.character_id}),
    max_age=COOKIE_MAX_AGE_S,
    httponly=True,
    samesite="lax",
    path="/",
)
```
New version signs the payload via `cookie_auth.sign_cookie(...)` using `request.app.state.cookie_secret` and adds `browser_id` per D-03 (person/character split). Keep `httponly=True`, `samesite="lax"`, no `secure=True` (M0-only trust model documented in the module docstring, lines 16-24 — do not silently "fix" this, it's an explicit decision).

**Cookie-read pattern to replace** (lines 171-190, `my_character`): keep the exact "fail silently, never raise" shape — swap `json.loads` for `cookie_auth.verify_cookie(raw, secret=...)`, returning `MyCharacterResponse(selected=False, character_id=None)` on any verification failure (signature mismatch is just another parse failure in this model).

**Length-cap gap (QUAL-04):** `SelectCharacterRequest.character_id: str` (line 83) has no `Field(max_length=...)`. Import and reuse `MAX_ID_LEN` from `routes_actions.py` (line 81-82) rather than declaring a new constant — this repo's stated convention against duplicating the same magic number in two places (see `actor.py:236-239` comment referenced in RESEARCH.md).

**Occupation check integration point:** `select_character` must call `actor.submit(OccupyCharacter(...))` before setting the cookie — analog is exactly how `declare()` in `routes_actions.py:165-167` calls `actor.submit(DeclareAction(...))` first, then proceeds only if it doesn't raise.

---

### `src/gptrpg/web/routes_actions.py` (MODIFIED — controller, request-response)

**Analog:** itself.

**Identity cross-check insertion point (TRUST-02):** at the very top of `declare()` (before `actor.submit`, around line 153) and `confirm()` (around line 264), read+verify the signed cookie the same way `my_character()` does, then compare `body.character_id` (or `body.player_id`) against the cookie's `character_id`. On mismatch, raise `HTTPException` — follow the existing exception-mapping table already present:
```python
except (UnknownMove, CommandRejected, UnknownRulebook) as exc:
    raise HTTPException(status_code=400, detail=str(exc)) from exc
except SequenceConflict as exc:
    raise HTTPException(status_code=409, detail=str(exc)) from exc
```
(lines 203-204, 341-342 area). A new identity-mismatch case should raise via the same `except CommandRejected` path if the check is pushed into `_prepare_declare`/`_prepare_confirm` (preferred per D-11 — two-tier defense), or a direct `HTTPException(status_code=403, ...)` if done as a fast-fail route-layer check before `actor.submit` is even called (open question in RESEARCH.md — confirm status-code choice with 400-only precedent at plan time).

**"No event on request-format rejection" convention (D-04):** exactly the comment block at lines 281-285 — request-format validation happens and raises *before* any `actor.submit` call. Cookie/identity checks that are pure request-shape problems (not game-state problems) must follow the same ordering.

**Idempotent-confirm / cached-roll reuse (D-08/D-09/TRUST-05/06):** replace the current unconditional 502-and-discard block (lines 439-446) with a branch that first checks whether `confirm_seq`'s underlying `declare_seq` was already resolved (`AlreadyConfirmed`, a `CommandRejected` subclass per RESEARCH.md Pattern 2) — catch it *before* the generic `except CommandRejected` (subclass ordering matters, same principle FastAPI/Python exception handling already requires). On `AlreadyConfirmed`, skip straight to narration re-generation using the cached `resolve_seq`, reusing the existing `store.read_events(session_id, from_seq=...)` pattern already used at line ~346.

---

### `src/gptrpg/session_actor/actor.py` (MODIFIED — service, event-driven)

**Analog:** itself — `_prepare_declare`/`_prepare_confirm` dispatch table.

**New command dataclass pattern** (mirror `ConfirmAction`, lines ~77-84):
```python
@dataclass(frozen=True)
class OccupyCharacter:
    """캐릭터 점유를 요청하는 명령 — 먼저 잡은 사람이 임자다(D-05)."""

    character_id: str
    browser_id: str
```

**Dispatch table extension** (`_prepare`, lines 349-364) — add one `isinstance` branch, same style as the existing six:
```python
if isinstance(command, OccupyCharacter):
    return self._prepare_occupy(command)
```

**`_prepare_occupy` pattern** (new method, modeled on `_prepare_declare`'s validate-then-return-tuple shape, lines 379-386):
```python
def _prepare_occupy(self, command: OccupyCharacter) -> tuple[str, int | None, dict]:
    if not command.character_id.strip():
        raise CommandRejected("character_id는 비어 있을 수 없다")
    holder = self.state.occupied_by.get(command.character_id)
    if holder is not None and holder != command.browser_id:
        raise CommandRejected("이미 다른 사람이 점유한 캐릭터다")
    return (
        "character_occupied",
        None,
        {"character_id": command.character_id, "browser_id": command.browser_id},
    )
```

**Ownership + idempotency check extension in `_prepare_confirm`** (extend lines 389-408, keep `_validate_caused_by(command.caused_by_seq)` call at line 397 unchanged, add checks immediately after):
```python
self._validate_caused_by(command.caused_by_seq)

declared_owner = self.state.declare_owners.get(command.caused_by_seq)
if declared_owner is not None and declared_owner != command.character_id:
    raise CommandRejected("이 선언은 다른 캐릭터가 낸 것이다")

prior = self.state.confirmed_declares.get(command.caused_by_seq)
if prior is not None:
    if prior.move != command.move or prior.stat != command.stat:
        raise CommandRejected("이미 다른 무브로 확인된 선언이다")
    raise AlreadyConfirmed(prior)
```

**Exception class pattern:** `AlreadyConfirmed(CommandRejected)` — subclass following the existing single-line docstring-exception style at `actor.py:197-198`:
```python
class AlreadyConfirmed(CommandRejected):
    """이미 확인된 선언에 대한 재확인 — 캐시된 판정 결과를 들고 있다."""

    def __init__(self, prior: "ConfirmedDeclareRecord") -> None:
        super().__init__("이미 확인된 선언이다")
        self.prior = prior
```

---

### `src/gptrpg/event_log/schema.py` (MODIFIED — model, event-driven)

**Analog:** itself — the exact version-bump precedent already in the file.

**Version bump docstring pattern** (extend the `EVENT_SCHEMA_VERSION` docstring, lines 18-35, in the same append-only narrative style — do not rewrite prior paragraphs, only add a new one):
```python
EVENT_SCHEMA_VERSION = 5
"""...(existing paragraphs unchanged)...

판 4 -> 판 5: 점유 사건이 새로 생겼다 — `CharacterOccupied`. `ActionDeclared`/
`ActionConfirmed`에 선택 칸 `character_id: str | None = None`이 늘었다(옛 기록은
소유자를 모른다는 뜻으로 읽는다). `CheckResolved`에는 `person_id`·`character_id`가
필수 칸으로 늘었다(D-12) — 판정 기록에 「누구의 판정인가」가 반드시 남는다.
"""
```

**New event class pattern** (mirror `ActionDeclared`, lines 82-88, same `EventEnvelope` base + `extra="forbid"`/`frozen=True` inherited config):
```python
class CharacterOccupied(EventEnvelope):
    """캐릭터를 처음 점유했다 — 먼저 잡은 사람이 임자다(D-05/D-06). 놓기 사건은 없다(D-07)."""

    event_type: Literal["character_occupied"]
    character_id: str
    browser_id: str
```

**Extending `ActionDeclared`/`ActionConfirmed`** — optional field, default `None`, per D-13's "old records don't know" convention already established for `cached_prompt_tokens` (schema.py:26-35):
```python
class ActionDeclared(EventEnvelope):
    event_type: Literal["action_declared"]
    player_id: str
    raw_text: str
    character_id: str | None = None  # 판 5+, D-03/Pitfall 1
```

**`CheckResolved` extension (required field, D-12)** — mirror how `counts_as_failure` was made required in the 1→2 bump (this is the strict precedent, contrast with the optional-field precedent above):
```python
class CheckResolved(EventEnvelope):
    event_type: Literal["check_resolved"]
    move: str
    rolls: list[int]
    modifiers: list[ModifierRecord]
    target: int
    grade: Grade
    counts_as_failure: bool
    person_id: str      # 판 5+ 필수 (D-12)
    character_id: str   # 판 5+ 필수 (D-12)
```

---

### `src/gptrpg/rules_core/reducer.py` (MODIFIED — transform, event-driven)

**Analog:** itself — `reducer.py:76-105`, exact precedent cited by CONTEXT.md's D-13.

**Version-gated read pattern** (copy the shape of `_legacy_v1_counts_as_failure` + the `schema_version >= 2` branch verbatim, adjust threshold to 5):
```python
def apply_event(state: GameState, event_type: str, payload: Mapping) -> GameState:
    ...
    if event_type == "character_occupied":
        occupied_by = dict(state.occupied_by)
        occupied_by[payload["character_id"]] = payload["browser_id"]
        return replace(state, last_seq=seq, occupied_by=occupied_by)

    if event_type == "action_declared":
        schema_version = payload.get("schema_version", 1)
        character_id = payload.get("character_id") if schema_version >= 5 else None
        declare_owners = dict(state.declare_owners)
        if character_id is not None:
            declare_owners[seq] = character_id
        return replace(
            state, last_seq=seq, turn_count=state.turn_count + 1, declare_owners=declare_owners
        )
```
Must ship in the **same commit** as the `EVENT_SCHEMA_VERSION` bump — CONTEXT.md explicitly calls out this exact risk ("빠뜨리면 세션이 영구히 안 열리는 사고가 재발한다").

**`GameState` new fields** (add alongside existing derived fields like `fails_since_clock`, per RESEARCH.md Pattern 2 — locate the `@dataclass(frozen=True) class GameState` definition and add `declare_owners: dict[int, str] = field(default_factory=dict)`, `confirmed_declares: dict[int, ...] = field(default_factory=dict)`, `occupied_by: dict[str, str] = field(default_factory=dict)`).

---

### `src/gptrpg/web/characters_data.py` (MODIFIED — verify scope)

**Analog:** itself — `get_character`/`list_characters` are pure read functions consumed by both `routes_characters.py` and `routes_actions.py`. RESEARCH.md and CONTEXT.md do not describe a structural change to this file's content (the four hand-written characters); CONTEXT.md's canonical_refs section flags it only as "referenced." **Action for planner:** confirm at plan time whether this file needs any change at all in Phase 8, or whether CONTEXT.md's mention is informational (docstring citation) only — current evidence suggests no code change needed here.

---

### `tests/conftest.py` (MODIFIED — test fixture, event-driven/batch)

**Analog:** itself — `_env()` envelope builder (lines ~60-70) and `_t()` fixed-clock helper (lines 47-53), plus the existing `fake_session_log` fixture pattern that appends real events through `EventStore` and reads them back (module docstring, lines 1-6 — "메모리 안 객체를 그대로 돌려주면 저장·복원 과정에서 값이 상하는지 잡을 수 없다").

**Multi-character fixture pattern (TEST-01):** replace/extend the `"p1"` constant (13 files, 44 occurrences per CONTEXT.md) with real character ids from `characters_data.py`. Follow the same "build through the real store, read back" discipline already used for `fake_session_log` — do not hand-construct `GameEvent` objects and skip the store round-trip, since that's exactly what this fixture module's docstring says it exists to avoid.

**Signed-cookie test helper (new):** add a helper that signs a cookie payload using the same `cookie_auth.sign_cookie` used in production code (not a hand-rolled test-only signer) — mirrors this project's general anti-hand-roll stance (RESEARCH.md's Don't Hand-Roll table).

---

### `tests/test_session_actor.py` / `tests/test_web_actions.py` / `tests/test_web_characters.py` (MODIFIED — test, event-driven / request-response)

**Analog:** existing tests in each of these files (unit tests calling `actor.submit(...)` directly for actor-level; `TestClient`/`httpx.AsyncClient` for HTTP-level).

**Concurrency test pattern (TEST-02, actor-level)** — exact reusable pattern already in the codebase:
```python
seqs = await asyncio.gather(*(actor.submit(command) for command in commands))
```
(cited in RESEARCH.md as `tests/test_session_actor.py:186-190`, already existing — reuse verbatim for two simultaneous `ConfirmAction`s or two simultaneous `OccupyCharacter`s.)

**Concurrency test pattern (TEST-02, HTTP-level, new but stdlib-supported)** — `httpx.AsyncClient` + `ASGITransport` against the real `create_app(...)` instance, two clients firing `asyncio.gather`:
```python
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
    assert len(statuses) == 2
```

## Shared Patterns

### Two-tier defense (route + actor), per D-11
**Source:** `src/gptrpg/web/app.py:49-61` (`validate_session_id` as `Depends()`) for the route-tier shape; `src/gptrpg/session_actor/actor.py:349-408` (`_prepare_*` dispatch) for the actor-tier shape.
**Apply to:** `routes_characters.py`, `routes_actions.py` (fast-fail layer) AND `actor.py` (final defense layer). Every new check (identity mismatch, occupation conflict, idempotency) needs *both* a route-layer fast path and an actor-layer authoritative check — do not implement only one.

### "Request-format failures don't produce events" (D-04)
**Source:** `src/gptrpg/web/routes_actions.py:281-285` (comment + code structure — all format validation happens before any `actor.submit` call).
**Apply to:** all new identity/cookie verification logic in route handlers — verification failures must be raised as `HTTPException` before any `actor.submit(...)` call, never recorded as game events.

### Version-gated schema evolution (D-12/D-13)
**Source:** `src/gptrpg/event_log/schema.py:18-35` (docstring convention) + `src/gptrpg/rules_core/reducer.py:76-105` (`_legacy_v1_counts_as_failure` + `schema_version >= N` branching).
**Apply to:** `schema.py` (bump `EVENT_SCHEMA_VERSION` 4→5, document each field addition in the same docstring paragraph style) and `reducer.py` (add matching version-gated read branches in the same commit — never skip the reducer side).

### Exception hygiene, no secrets in messages (QUAL-05)
**Source:** `src/gptrpg/session_actor/actor.py:197-198` (`CommandRejected` — plain string, no interpolated sensitive values) and `actor.py:508-511`'s restrained AI-call error message style.
**Apply to:** `cookie_auth.py`, all new `CommandRejected` subclasses, all new `HTTPException` detail strings touching identity/cookie logic.

### Sqlite3 thread-affinity discipline
**Source:** `src/gptrpg/web/routes_actions.py` module docstring (lines 1-19) — `asyncio.to_thread` only for blocking AI calls, actor/store access always stays on the event loop.
**Apply to:** any new code path in `routes_actions.py`/`routes_characters.py` — do not move `actor.submit(...)` calls into `asyncio.to_thread`.

### Field-name fidelity across layers
**Source:** `src/gptrpg/web/routes_characters.py:9-14` (module docstring — "칸 이름은 한 글자도 다르게 짓지 않는다").
**Apply to:** any new response view models (e.g. an occupation-conflict response) — keep field names identical to the underlying dataclass/event field names.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `frontend/src/screens/SessionScreen.tsx` | component | request-response | CONTEXT.md explicitly defers screen layout/real-time refresh to Phase 16 (FE-03); only a minimal response-shape consumption change may be needed here (D-03 person/character split affecting `player_id`/`character_id` usage at line 113) — no strong frontend analog surveyed this pass since scope is uncertain. Planner should re-confirm in-scope vs out-of-scope before assigning a plan file here. |
| `frontend/src/api/client.ts` | service (API client) | request-response | Same as above — likely needs the request body shape updated (e.g., `character_id` sent alongside cookie) but full analog search deferred pending scope confirmation. |
| `frontend/src/api/types.ts` | model (TS types) | transform | Same as above. |

## Metadata

**Analog search scope:** `src/gptrpg/web/`, `src/gptrpg/session_actor/`, `src/gptrpg/event_log/`, `src/gptrpg/rules_core/`, `tests/` (backend). Frontend (`frontend/src/`) scanned only for the three files CONTEXT.md flags as "verify if truly in scope," not searched further given Phase 16 boundary.
**Files scanned (Read):** `routes_characters.py` (full), `routes_actions.py` (lines 1-100, 130-330, 420-450), `actor.py` (lines 1-120, 190-420), `schema.py` (lines 1-140), `reducer.py` (lines 70-110), `app.py` (lines 1-135), `tests/conftest.py` (lines 1-90).
**Pattern extraction date:** 2026-08-06

---

*Phase: 8-신원 검증과 멱등성*
