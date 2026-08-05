# Phase 3: AI 진행자 한 턴 - Pattern Map

**Mapped:** 2026-08-02
**Files analyzed:** 13 (new) + 3 (modified)
**Analogs found:** 13 / 13 (all have at least a role-match; the `agents/` package itself is greenfield so its closest analogs are cross-layer, not same-package)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|-----------------|----------------|
| `src/gptrpg/agents/providers/base.py` | interface/protocol | request-response | `src/gptrpg/rules_core/rulebook.py` (`Rulebook` declaration shape — value object describing a capability, no I/O) | role-match |
| `src/gptrpg/agents/providers/anthropic_provider.py` | service (external I/O adapter) | request-response + streaming | `src/gptrpg/session_actor/live_roller.py` (the one existing "impure, wraps a non-deterministic real-world call behind a small interface" file) | role-match |
| `src/gptrpg/agents/providers/openai_provider.py` | service | request-response | same as above (`live_roller.py`) | role-match |
| `src/gptrpg/agents/providers/nim_provider.py` | service (thin subclass) | request-response | `agents/providers/openai_provider.py` (sibling, once written this phase) | exact (new-file-to-new-file) |
| `src/gptrpg/agents/providers/openrouter_provider.py` | service (thin subclass) | request-response | `agents/providers/openai_provider.py` | exact (new-file-to-new-file) |
| `src/gptrpg/agents/providers/gemini_provider.py` | service | request-response | `agents/providers/anthropic_provider.py` | role-match |
| `src/gptrpg/agents/envelope.py` | model (value object) | transform | `src/gptrpg/event_log/schema.py` (`AiInvoked`, `EventEnvelope` — pydantic value objects, `extra="forbid"`/`frozen=True` discipline) | exact |
| `src/gptrpg/agents/config.py` | config (persistence) | file-I/O | `src/gptrpg/event_log/store.py` (nearest existing "read/write a small persisted store" file — see note below; not fully read this pass, referenced via `EventStore` usage in `actor.py`/`main.py`) | role-match |
| `src/gptrpg/agents/prompt_assembly.py` | utility (pure transform) | transform | `src/gptrpg/rules_core/resolution.py` (pure function building a structured result from ordered inputs, `Modifier`/`CheckOutcome` dataclasses) | role-match |
| `src/gptrpg/agents/action_classifier.py` | service | request-response | `src/gptrpg/session_actor/actor.py` `_prepare_confirm`/`_process` (validates input → calls out → returns a structured proposal) | role-match |
| `src/gptrpg/agents/master_gm.py` | service | streaming | `src/gptrpg/session_actor/actor.py` `AppendNarration`/`_prepare_narration` (repeated-chunk emission target this streams into) | role-match |
| `tests/test_agents.py` / `test_action_classifier.py` / `test_master_gm.py` / `test_agents_retry.py` | test | request-response / streaming | `tests/test_session_actor.py` (async command-dispatch test style) + `tests/conftest.py` (fixture style) | exact |
| `src/gptrpg/cli/main.py` (MODIFIED) | controller/CLI | request-response | itself — extend existing `_build_command`/subparser pattern | exact |
| `src/gptrpg/session_actor/actor.py` (UNCHANGED — call site only) | — | — | n/a — `RecordAiCall`/`AppendNarration`/`ConfirmAction` already accept the shapes the new agent code will fill | n/a |
| `.importlinter` (MODIFIED) | config | n/a | itself — extend `layers` list | exact |

## Pattern Assignments

### `src/gptrpg/agents/envelope.py` (model, transform)

**Analog:** `src/gptrpg/event_log/schema.py`

**Imports pattern** (lines 13-17):
```python
from datetime import UTC, datetime
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter
```

**Value-object shape pattern** (lines 41-56, `EventEnvelope`):
```python
class EventEnvelope(BaseModel):
    """모든 사건이 공유하는 봉투 칸.

    extra="forbid"가 오타로 생긴 여분 칸을 거부하고, frozen=True가 만들어진
    사건 객체를 못 고치게 한다 (append-only 정신, D-12).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: str
    seq: int
    schema_version: int
    ...
```

**Field-set to copy for D-30's minimum shape** (lines 131-144, `AiInvoked` — do NOT redesign this, it already IS the envelope's persisted shape):
```python
class AiInvoked(EventEnvelope):
    event_type: Literal["ai_invoked"]
    agent_role: str
    model: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
```
**Apply:** `agents/envelope.py`'s `AgentResult` dataclass should be a *plain* (non-pydantic, non-persisted) in-memory carrier — success/failure + value + elapsed_ms + prompt_tokens/completion_tokens — that callers unpack into a `RecordAiCall` command. Do not give it its own pydantic schema; it never touches the event log directly. Mirror the *field names* (`prompt_tokens`, `completion_tokens`, `latency_ms`) exactly so the mapping to `RecordAiCall` is a 1:1 attribute copy with no renaming.

---

### `src/gptrpg/agents/providers/base.py` + adapters (service, request-response/streaming)

**Analog:** `src/gptrpg/session_actor/live_roller.py` (closest existing "small interface wrapping an impure/external primitive")

Read via Bash grep — not fully loaded this pass since RESEARCH.md already supplies a verified, in-session-checked reference implementation for the provider protocol (Anthropic SDK usage was verified against the bundled `claude-api` skill this same research session). Use RESEARCH.md's Pattern 1 code block directly — it is more authoritative than reverse-engineering `live_roller.py`'s shape, since `live_roller.py` wraps `random`, not an LLM SDK. The structural lesson to take from `live_roller.py` is: **the impure adapter lives in its own single-purpose module, is the only file allowed to import the impure primitive (`random`/`anthropic`/`openai`), and exposes a narrow protocol-shaped interface** — same discipline RESEARCH.md's `Provider` protocol already follows.

**Core pattern (from RESEARCH.md, verified this session):**
```python
from typing import Protocol, Iterator

class Provider(Protocol):
    def list_models(self) -> list[str]: ...
    def complete(self, *, system: str, messages: list[dict], max_tokens: int) -> "AgentResult": ...
    def stream(self, *, system: str, messages: list[dict], max_tokens: int) -> Iterator[str]: ...
```

**Error handling pattern to copy from `session_actor/actor.py`** (lines 187-195, the `_run` consumer loop — mirror "never silently swallow, always propagate a typed exception to the caller"):
```python
try:
    seq = await self._process(command)
except Exception as exc:  # noqa: BLE001 - 부르는 쪽에 그대로 전달한다, 삼키지 않는다
    if not future.done():
        future.set_exception(exc)
```
**Apply:** the D-27/D-28 timeout+retry wrapper in `agents/action_classifier.py` should follow this same "one place, one try/except, propagate or convert to the no-move fallback — never swallow silently" discipline. Do not add exception-type branching (`MODEL_ERROR` vs `VALIDATION_FAILED`) — D-28 explicitly forbids it.

---

### `src/gptrpg/agents/config.py` (config, file-I/O)

**No strong same-role analog exists in the codebase** — `EventStore` (`src/gptrpg/event_log/store.py`) is the only existing "persist something to a file/db" code, but it persists append-only game events with sequence numbers, which is a materially different shape than a small overwritable JSON preference file. Follow RESEARCH.md's Open Question 3 recommendation directly: a simple JSON file, one dict with `action_classifier`/`master_gm` keys each holding `{"provider": ..., "model": ...}`, written with plain `json.dump`/`json.load` — no ORM, no schema versioning machinery needed for a single-operator local file. Do **not** copy `EventStore`'s SQLite/sequence-conflict machinery; that solves a concurrency problem this file does not have.

**Security constraint (carry over from RESEARCH.md Security Domain table):** this file must persist only `{provider_name, model_id}`, never the API key itself — keys are re-read from `os.environ` at each startup.

---

### `src/gptrpg/agents/prompt_assembly.py` (utility, transform)

**Analog:** `src/gptrpg/rules_core/resolution.py`

**Pure-function-with-frozen-dataclass-inputs pattern** (lines 1-9, 32-38):
```python
"""2d6 판정 계산 — 순수 함수. 무작위는 Roller를 통해서만 얻는다."""
...
@dataclass(frozen=True)
class Modifier:
    """판정 총합에 영향을 주는 수정치 하나와 그 출처."""

    type: str
    value: int
    source: str
```
**Apply:** `prompt_assembly.py`'s `build_prompt(permanent, session_ctx, turn_ctx)` should follow the same discipline as `resolve_2d6` — pure function, explicit ordered parameters (mirroring `Modifier`'s "value + source" shape called out in CONTEXT.md's Established Patterns), no hidden global state, no I/O. This is also where RESEARCH.md's Pattern 2 code block applies directly (`cache_control` breakpoint placement) — treat that block as the canonical implementation reference, not `resolution.py`, since `resolution.py` has no analog for cache breakpoints; only the "pure function, explicit stable ordering" *discipline* is copied from it.

---

### `src/gptrpg/agents/action_classifier.py` / `master_gm.py` (service, request-response / streaming)

**Analog:** `src/gptrpg/session_actor/actor.py` — specifically the `_prepare_confirm`/`_prepare_narration` validate-then-shape pattern, and the `RecordAiCall`/`AppendNarration` commands these two new files must ultimately produce.

**Imports pattern** (lines 15-26, actor.py):
```python
from gptrpg.event_log.schema import (
    EVENT_SCHEMA_VERSION,
    ActionConfirmed,
    ActionDeclared,
    AiInvoked,
    ...
)
```
**Apply:** `agents/action_classifier.py` and `agents/master_gm.py` do not import `event_log` directly (per `.importlinter`'s layer contract — `agents` sits above `cli`, calls into `session_actor` to submit commands, never touches `event_log` itself). Instead they import `session_actor.actor.RecordAiCall` / `AppendNarration` / `ConfirmAction` dataclasses and return/yield values the CLI layer wraps into those commands — mirroring how `cli/main.py`'s `_build_command` already converts argparse args into `Command` objects (see next section).

**Command-construction pattern to copy** (`cli/main.py` lines 71-80, the `ai` branch of `_build_command`):
```python
if kind == "ai":
    return RecordAiCall(
        agent_role=args.role,
        model=args.model,
        provider=args.provider,
        prompt_tokens=args.prompt_tokens,
        completion_tokens=args.completion_tokens,
        latency_ms=args.latency_ms,
        caused_by_seq=args.caused_by,
    )
```
**Apply:** this is the exact shape `action_classifier.classify()`'s returned `AgentResult` must be unpacked into once the CLI calls the classifier for real instead of taking these six values from argparse flags. Preserve `caused_by_seq` threading (RESEARCH.md Pitfall 4) — every new AI-driven CLI subcommand must pass `caused_by_seq` through the same way `confirm`/`roll`/`narrate`/`clock`/`ai` already do (`cli/main.py:161,180,185,193,202`).

**Streaming-to-chunk-commands pattern:** no existing analog for streaming exists in the codebase (`NarrationAppended`/`AppendNarration` were built in Phase 1 for manual single-chunk CLI submission, not automated streaming). Use RESEARCH.md's Pattern 3 code block (`chunk_sentences`) as the canonical reference — it was derived directly from `NarrationAppended`'s own docstring (`event_log/schema.py:104-115`) this session, so treat it as equivalent-confidence to a codebase analog.

---

### `src/gptrpg/cli/main.py` (MODIFIED — controller, request-response)

**Analog:** itself (extend the existing pattern in place)

**Subparser + `_build_command` extension pattern** (lines 37-81 for command construction, 139-210 for subparser wiring) — every new CLI behavior (provider/model selection prompt, confidence-tiered confirm UX) should be added as either:
1. A new top-level subcommand (mirroring `submit_parser`/`replay_parser` at lines 143/204), or
2. A new branch inside `_build_command`'s existing `if kind == ...` chain (lines 40-80), if it still reduces to producing one of the six existing `Command` objects.

**Existing `--caused-by` wiring to copy exactly** (lines 161, 180, 185, 193, 202 — every existing subcommand already has this argument):
```python
confirm_parser.add_argument("--caused-by", type=int, default=None)
```

**Test harness pattern to copy for new CLI tests** (`tests/test_cli.py` lines 1-36):
```python
def _submit(db: str, session: str, *args: str) -> int:
    return main(["submit", "--db", db, "--session", session, *args])

def _read_events(db: str, session: str):
    store = EventStore(db)
    store.initialize()
    try:
        return store.read_events(session)
    finally:
        store.close()
```
No subprocess is spawned — `main(argv)` is called in-process and stdout is captured via `capsys` (pytest fixture, already in use at line 56 in that file).

---

### `.importlinter` (MODIFIED — config)

**Analog:** itself

**Current layers block to extend** (verified this session, lines 16-21):
```ini
[importlinter:contract:2]
name = cli -> session_actor -> rulebooks -> (rules_core | event_log)
type = layers
layers =
    gptrpg.cli
    gptrpg.session_actor
    gptrpg.rulebooks
    gptrpg.rules_core | gptrpg.event_log
```
**Apply:** insert `gptrpg.agents` as a new line **above** `gptrpg.cli` (per RESEARCH.md's Recommended Project Structure and Assumption A5):
```ini
layers =
    gptrpg.cli
    gptrpg.agents
    gptrpg.session_actor
    gptrpg.rulebooks
    gptrpg.rules_core | gptrpg.event_log
```
Note: in import-linter's `layers` contract, modules listed *earlier* may import modules listed *later*, not the reverse. Confirm at plan/execute time which direction `agents` needs (CLI calls into `agents`, so `agents` must be importable *by* `cli`, meaning `agents` sits below `cli` in the list — this matches the block above). Also add a rule to Contract 1 (`rules_core`'s forbidden-imports list, lines 4-16) is unaffected — no change needed there, since `rules_core` already forbids `asyncio`/network-adjacent modules broadly and has no reason to ever import `gptrpg.agents` under the layers contract anyway.

---

### `tests/test_agents.py`, `test_action_classifier.py`, `test_master_gm.py`, `test_agents_retry.py` (test)

**Analog:** `tests/test_session_actor.py` (async command round-trip style) + `tests/test_cli.py` (in-process `main(argv)` + `capsys` style)

**Async test + fixture pattern to copy** (`tests/test_session_actor.py` line 149 area — `test_record_ai_call_appends_one_ai_invoked_event`, and `tmp_db_path`/`capsys` fixtures used throughout `test_cli.py`):
```python
async def test_record_ai_call_appends_one_ai_invoked_event(tmp_db_path):
    ...
    RecordAiCall(...)
    ...
    assert state.ai_calls == 1
```
**Apply:** new tests need a `FakeProvider` fixture (per RESEARCH.md's Wave 0 Gaps) added to `tests/conftest.py`, implementing the `Provider` protocol deterministically — no real network calls, following the same "fixture lives in `conftest.py`, is reused across multiple test files" convention `tmp_db_path` already demonstrates.

## Shared Patterns

### Pydantic frozen/extra-forbid discipline
**Source:** `src/gptrpg/event_log/schema.py` lines 41-48 (`EventEnvelope`)
**Apply to:** any new pydantic model in `agents/` (if `envelope.py` ends up pydantic rather than a plain dataclass) — `model_config = ConfigDict(extra="forbid", frozen=True)`.

### Frozen dataclass command objects
**Source:** `src/gptrpg/session_actor/actor.py` lines 45-111 (`DeclareAction`, `ConfirmAction`, `RecordAiCall`, etc. — all `@dataclass(frozen=True)`)
**Apply to:** any new value object in `agents/` that isn't persisted (e.g. `AgentResult`, `Proposal`) should follow the same `@dataclass(frozen=True)` convention already used project-wide for command/value objects.

### `caused_by_seq` threading
**Source:** `src/gptrpg/session_actor/actor.py` lines 229-239 (`_validate_caused_by`) + `src/gptrpg/cli/main.py` lines 161/180/185/193/202
**Apply to:** every new CLI subcommand or agent-driven flow that submits a command in reaction to a prior event (RESEARCH.md Pitfall 4 — MEAS-02 depends on this).

### Never swallow exceptions silently
**Source:** `src/gptrpg/session_actor/actor.py` lines 187-195 (the `_run` consumer loop's `except Exception as exc: ... future.set_exception(exc)`)
**Apply to:** the D-27/D-28 timeout+retry wrapper — on final failure, either propagate a typed exception or explicitly convert to the "no-move" fallback path (D-29); never `except: pass`.

### CommandRejected as the one rejection channel
**Source:** `src/gptrpg/session_actor/actor.py` line 145 (`class CommandRejected(Exception)`) and its use throughout `_prepare_*` methods
**Apply to:** if `agents/` code needs to reject malformed input before it ever reaches `session_actor`, prefer raising a similarly narrow, purpose-built exception type rather than a bare `ValueError`/`Exception` — keeps the "reject early, don't half-commit" discipline consistent.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `src/gptrpg/agents/providers/*.py` (all 5) | service | streaming + request-response | No prior LLM-SDK-wrapping code exists in this codebase at all — RESEARCH.md's Architecture Patterns §1-3 code blocks (verified this session against the bundled `claude-api` skill and cross-checked docs) are the correct reference, not a codebase analog. |
| `src/gptrpg/agents/config.py` | config | file-I/O | No existing "small overwritable JSON preference file" pattern in the codebase; `EventStore`'s append-only SQLite model is a poor fit — follow RESEARCH.md's Open Question 3 recommendation instead. |

## Metadata

**Analog search scope:** `src/gptrpg/` (all five existing packages: `cli`, `event_log`, `rules_core`, `rulebooks`, `session_actor`), `tests/`, `.importlinter`, `pyproject.toml`
**Files scanned:** `src/gptrpg/cli/main.py`, `src/gptrpg/session_actor/actor.py`, `src/gptrpg/event_log/schema.py`, `src/gptrpg/rules_core/resolution.py`, `src/gptrpg/rulebooks/dungeonworld_like.py`, `.importlinter`, `pyproject.toml`, `tests/test_cli.py`, `tests/test_session_actor.py` (grep only)
**Pattern extraction date:** 2026-08-02
