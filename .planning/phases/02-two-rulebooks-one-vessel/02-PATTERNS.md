# Phase 2: 룰북 두 개를 같은 그릇에 - Pattern Map

**Mapped:** 2026-08-01
**Files analyzed:** 10 (new/modified, per RESEARCH.md "Recommended Project Structure" + Integration Points)
**Analogs found:** 9 / 10

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/gptrpg/rules_core/resolution_d100.py` (new) | service (pure calc) | request-response (CRUD-like: compute once) | `src/gptrpg/rules_core/resolution.py` | exact |
| `src/gptrpg/rules_core/grading_d100.py` (new) | utility (pure calc) | transform | `src/gptrpg/rules_core/grading.py` | exact |
| `src/gptrpg/rules_core/dice.py` (extend — add `PercentileRoller` Protocol) | utility/interface | transform | `src/gptrpg/rules_core/dice.py` (`Roller`) | exact (self-extension, additive) |
| `src/gptrpg/session_actor/live_roller.py` (extend — add `roll_tens`/`roll_units`) | service (side-effect provider) | event-driven | `src/gptrpg/session_actor/live_roller.py` (`LiveRoller.roll_d6`) | exact (self-extension, additive) |
| `src/gptrpg/rulebooks/openquest.py` (new) | config/data (rulebook declaration) | CRUD (static data) | none in codebase (new layer) | no analog |
| `src/gptrpg/rulebooks/dungeonworld_like.py` (new, optional per RESEARCH) | config/data (rulebook declaration) | CRUD (static data) | none in codebase (new layer) | no analog |
| `src/gptrpg/rules_core/entities.py` (new — `Entity`/`StatEntry`, D-20/D-21) | model | CRUD | `src/gptrpg/rules_core/resolution.py` (`Modifier` dataclass) | role-match (closest "value + source" shape) |
| `src/gptrpg/event_log/schema.py` (modify — `Grade: Literal[...] → str`) | model/schema | request-response (validation) | itself, current lines 23 & 94 | exact (modification of existing file) |
| `src/gptrpg/rules_core/reducer.py` (modify — replace `grade == "miss"` hardcode) | service (state fold) | event-driven | itself, current lines 60-68 | exact (modification of existing file) |
| `src/gptrpg/session_actor/actor.py` (modify — `ResolveCheck` dispatch to `resolve_2d6`/`resolve_d100`) | controller (command dispatcher) | event-driven | itself, current lines 239-258 (`_prepare_resolve_check`) | exact (modification of existing file) |
| `tests/test_resolution_d100.py` (new) | test | request-response | `tests/test_resolution_edges.py` | exact |
| `tests/test_grading_d100.py` (new) | test | transform | `tests/test_grading.py` | exact |
| `tests/test_entities.py` (new) | test | CRUD | `tests/test_resolution_edges.py` (dataclass-focused test style) | role-match |
| `02-INTERFACE-CHANGES.md` (new) | doc | — | none (new doc artifact) | no analog |

## Pattern Assignments

### `src/gptrpg/rules_core/resolution_d100.py` (service, pure calc)

**Analog:** `src/gptrpg/rules_core/resolution.py` (full file read, 99 lines)

**Imports pattern** (lines 1-7):
```python
"""2d6 판정 계산 — 순수 함수. 무작위는 Roller를 통해서만 얻는다."""

from collections.abc import Sequence
from dataclasses import dataclass

from gptrpg.rules_core.dice import Roller
from gptrpg.rules_core.grading import DEFAULT_TARGET, Grade, grade_for_total
```
For d100: import `PercentileRoller` from `dice.py` and `grade_for_d100` from the new `grading_d100.py` instead. Do NOT modify `Modifier`/`CheckOutcome`/`UnsupportedModifier` — reuse them as-is from `resolution.py` (import, don't redefine — this is the concrete proof of "same request/result shape" required by success criterion 1).

**Core CRUD/compute pattern — the `_flat_total` + "reject unknown modifier type" pattern** (lines 13-27, 50-57):
```python
class UnsupportedModifier(Exception):
    """계산에 반영할 수 없는 수정치 유형이 들어왔을 때 던진다.

    조용히 건너뛰면 합계가 틀린 채로 판정이 끝나고, 그 틀린 값이 기록에
    남아 이후 어디서도 복원되지 않는다 — 그래서 예외로 실패시킨다.
    """

    def __init__(self, modifier_type: str, source: str) -> None:
        super().__init__(
            f"resolve_2d6 does not know how to apply modifier type "
            f"{modifier_type!r} from source {source!r}"
        )
        self.modifier_type = modifier_type
        self.source = source
```
`resolve_d100` must raise `UnsupportedModifier` (reused from `resolution.py`, not redefined) for any `modifier.type` it doesn't recognize among `FLAT`, `BONUS_DICE`, `TARGET_SHIFT`, `PUSH` — same "reject, don't silently skip" discipline. RESEARCH.md Pattern 2 (`rules_core/resolution_d100.py` pseudocode, lines 244-262 of 02-RESEARCH.md) is the concrete starting skeleton — it separates modifiers by *when* they apply (pre-roll target shift, roll-shape bonus dice, post-roll flat) rather than reusing `_flat_total` verbatim (Anti-Pattern warning in RESEARCH.md: don't copy `_flat_total` to fake bonus dice as summation).

**Reroll/push pattern — direct copy target for `push_d100`** (lines 80-98, verbatim from `resolution.py`):
```python
def reroll_2d6(roller: Roller, previous: CheckOutcome) -> CheckOutcome:
    """앞선 판정 결과에 재굴림을 이어 붙인다.

    앞선 눈을 지우지 않는다 — 굴림 도구를 두 번 더 불러 새 눈 두 개를 얻고,
    `rolls`는 앞선 눈 뒤에 새 눈을 이어 붙인 것으로 만든다. `total`과
    `grade`는 새로 굴린 두 눈만으로 다시 계산한다. `modifiers`와 `target`은
    앞선 판정의 것을 그대로 물려받는다.
    """
    new_rolls = (roller.roll_d6(), roller.roll_d6())
    total = sum(new_rolls) + _flat_total(previous.modifiers)
    grade = grade_for_total(total, previous.target)
    return CheckOutcome(
        move=previous.move,
        rolls=previous.rolls + new_rolls,
        modifiers=previous.modifiers,
        total=total,
        target=previous.target,
        grade=grade,
    )
```
`push_d100(roller, previous)` copies this structure exactly per D-23: keep `previous.rolls` prefix, append new percentile roll(s), recompute `total`/`grade` from the new roll only, inherit `modifiers`/`target` unchanged. This is the single strongest "same skeleton, different dice shape" proof point for the phase.

**Error handling pattern:** same as analog — `UnsupportedModifier` propagates up uncaught from `resolve_d100`/`push_d100`; the caller (`session_actor._prepare_resolve_check`) is responsible for catching it and converting to `CommandRejected` (see actor.py pattern below).

---

### `src/gptrpg/rules_core/grading_d100.py` (utility, transform)

**Analog:** `src/gptrpg/rules_core/grading.py` (full file, 22 lines)

**Full pattern to mirror structurally** (lines 1-22):
```python
"""2d6 판정 등급 산출 — 순수 함수."""

from typing import Literal

Grade = Literal["strong_hit", "weak_hit", "miss"]

DEFAULT_TARGET = 10
WEAK_HIT_BAND = 3


def grade_for_total(total: int, target: int) -> Grade:
    """굴림 합계와 목표값에서 등급을 산출한다.

    target 이상이면 strong_hit, target - WEAK_HIT_BAND 이상이면 weak_hit,
    그 아래는 miss.
    """
    if total >= target:
        return "strong_hit"
    if total >= target - WEAK_HIT_BAND:
        return "weak_hit"
    return "miss"
```
`grading_d100.py` mirrors this shape (module docstring, constants, single pure grading function) but must NOT reuse the `Grade = Literal[...]` alias — per RESEARCH.md Pattern 1, `Grade` in both `grading.py` and `event_log/schema.py` widens to `str`. `grade_for_d100(roll, target, tens, units)` takes the decomposed tens/units digits (RESEARCH.md Pattern 3) rather than a scalar total only, because OpenQuest's critical/fumble is a "doubles" digit condition, not a threshold band — `CheckOutcome.rolls` (already a tuple) carries the decomposed digits with no schema change needed.

---

### `src/gptrpg/rules_core/dice.py` (extend, utility/interface)

**Analog:** itself, current content (full file, 16 lines)

```python
"""굴림 도구의 모양(Roller)만 정의한다. 실제 굴림 구현은 규칙 코어 밖에 있다."""

from typing import Protocol


class Roller(Protocol):
    """1~6 사이 눈 하나를 돌려주는 도구가 갖춰야 할 구조.

    구조적 타이핑(PEP 544)이라 이 클래스를 상속할 필요가 없다 — 메서드
    시그니처만 맞으면 실제 굴림 도구든 테스트용 즉석 객체든 그대로 통과한다.
    """

    def roll_d6(self) -> int:
        """1 이상 6 이하의 정수 하나를 돌려준다."""
        ...
```
Add a second, parallel `PercentileRoller(Protocol)` class in the same file with `roll_tens() -> int` and `roll_units() -> int` methods, following the exact same docstring convention. Do NOT modify `Roller` — this is additive, side-by-side (RESEARCH.md Pitfall 3, "확장이지 변경이 아니다").

---

### `src/gptrpg/session_actor/live_roller.py` (extend, service)

**Analog:** itself, current content (11 lines)

```python
"""실제로 굴리는 도구 (암호학적 난수). rules_core 밖 — 여기서만 secrets를 쓴다."""

import secrets


class LiveRoller:
    """secrets 기반 실제 Roller 구현체."""

    def roll_d6(self) -> int:
        # secrets.randbelow(6)의 범위는 [0, 6)이다. +1을 빠뜨리면 눈에 0이 나온다.
        return secrets.randbelow(6) + 1
```
Add `roll_tens()` (0-9) and `roll_units()` (0-9) methods to the same `LiveRoller` class using `secrets.randbelow(10)`, following the same off-by-one comment discipline. `LiveRoller` structurally satisfies both `Roller` and `PercentileRoller` simultaneously (PEP 544 — no explicit inheritance declaration needed). This is an "extension, honestly recorded as extension, not pure non-change" per RESEARCH.md Pitfall 3.

---

### `src/gptrpg/rules_core/entities.py` (model, CRUD) — D-20/D-21

**Analog:** `Modifier` dataclass in `src/gptrpg/rules_core/resolution.py` (lines 29-35)

```python
@dataclass(frozen=True)
class Modifier:
    """판정 총합에 영향을 주는 수정치 하나와 그 출처."""

    type: str
    value: int
    source: str
```
This "value + source/meaning" shape is the direct precedent for `StatEntry`. Follow the same `@dataclass(frozen=True)` convention (matches Phase 1's immutability discipline, consistent with `CheckOutcome` at lines 38-47 also being frozen). RESEARCH.md's proposed shape (lines 276-291 of 02-RESEARCH.md, "미검증 — Claude's Discretion"):
```python
@dataclass(frozen=True)
class StatEntry:
    name: str
    current: int
    max: int | None = None
    depleted_effect_ref: str | None = None

@dataclass(frozen=True)
class Entity:
    entity_id: str
    display_name: str
    rulebook_id: str
    stats: tuple[StatEntry, ...]
```
Note `stats` is a `tuple`, matching `CheckOutcome.modifiers: tuple[Modifier, ...]` (line 44) — the codebase convention is tuples for immutable ordered collections, not lists, inside `rules_core` dataclasses.

---

### `src/gptrpg/event_log/schema.py` (modify — Grade widening)

**Analog:** itself, current lines 22-23 and 86-94

```python
# rules_core.grading.Grade와 값은 같지만 별도로 선언한다 — 두 층은 서로를 모른다.
Grade = Literal["strong_hit", "weak_hit", "miss"]
...
class CheckResolved(EventEnvelope):
    """판정 한 번 = 사건 하나 (D-17). 계산 과정 전체를 담는다 (D-16)."""

    event_type: Literal["check_resolved"]
    move: str
    rolls: list[int]
    modifiers: list[ModifierRecord]
    target: int
    grade: Grade
```
Change `Grade = Literal["strong_hit", "weak_hit", "miss"]` to `Grade = str`. Keep `ModifierRecord` (lines 52-59) unchanged as the direct precedent — its `type: str` field is already the "open string, not fixed literal" pattern this change extends to `Grade`. Per RESEARCH.md Pitfall 4/Pattern 1, this must be explicitly decided as "shape change y/n" for `EVENT_SCHEMA_VERSION` (currently `1`, line 18) and the decision + rationale recorded in `02-INTERFACE-CHANGES.md` — do not silently widen without that record.

**Validation pattern to preserve:** `ConfigDict(extra="forbid", frozen=True)` (line 42, inherited by all event classes including `CheckResolved`) — any new pydantic models (e.g. for rulebook-declared grade sets) should follow this same strict/frozen convention (flagged in RESEARCH.md Security Domain V5).

---

### `src/gptrpg/rules_core/reducer.py` (modify — remove `grade == "miss"` hardcode)

**Analog:** itself, current lines 60-68

```python
if event_type == "check_resolved":
    grade = payload["grade"]
    return replace(
        state,
        last_seq=seq,
        check_count=state.check_count + 1,
        miss_count=state.miss_count + (1 if grade == "miss" else 0),
        last_grade=grade,
    )
```
This is Pitfall 1 (RESEARCH.md) — a new discovery not in CONTEXT.md. Fix must read a rulebook-declared "counts as failure" signal from the payload (e.g. a new `counts_as_failure: bool` field carried on `CheckResolved`/`ModifierRecord`-adjacent data) rather than comparing `grade` to the string `"miss"` — otherwise `miss_count` silently stays 0 for OpenQuest's `"failure"`/`"fumble"` grades. **Also update the `UnknownEventType` exception discipline is unaffected** — keep the "reject unknown, don't silently skip" pattern from lines 36-46 as-is; this is a computation-inside-a-known-branch fix, not a new event type.

**Import to note:** line 11, `from gptrpg.rules_core.grading import Grade` — this import must track whatever `Grade` becomes (`str`) after the schema.py change; `last_grade: Grade | None` (line 28) stays structurally the same field, just wider type.

---

### `src/gptrpg/session_actor/actor.py` (modify — ResolveCheck dispatch)

**Analog:** itself, current lines 54-61 (`ResolveCheck` dataclass) and 239-258 (`_prepare_resolve_check`)

```python
@dataclass(frozen=True)
class ResolveCheck:
    """판정 하나를 요청하는 명령."""

    move: str
    modifiers: tuple[Modifier, ...]
    target: int = DEFAULT_TARGET
    caused_by_seq: int | None = None
```
```python
def _prepare_resolve_check(self, command: ResolveCheck) -> tuple[str, int | None, dict]:
    self._validate_caused_by(command.caused_by_seq)
    try:
        outcome = resolve_2d6(self._roller, command.move, command.modifiers, command.target)
    except UnsupportedModifier as exc:
        raise CommandRejected(str(exc)) from exc
    return (
        "check_resolved",
        command.caused_by_seq,
        {
            "move": outcome.move,
            "rolls": list(outcome.rolls),
            "modifiers": [
                ModifierRecord(type=modifier.type, value=modifier.value, source=modifier.source)
                for modifier in outcome.modifiers
            ],
            "target": outcome.target,
            "grade": outcome.grade,
        },
    )
```
Add a resolution-method identifier field to `ResolveCheck` (a plain `str`, NOT a `Literal` — per D32/RESEARCH.md Pitfall 2), then branch in `_prepare_resolve_check` to call `resolve_2d6` or `resolve_d100` based on that field, both wrapped in the same `try/except UnsupportedModifier: raise CommandRejected(...)` structure already present. The dict-building tail (`ModifierRecord(...)` list comprehension, `outcome.grade` passthrough) is reusable verbatim for both branches since `CheckOutcome` shape is shared. This dispatch point is explicitly flagged by RESEARCH.md as a "limited modification" (not a pure "held back with data") — record it as such in `02-INTERFACE-CHANGES.md`.

**Error handling pattern:** `CommandRejected` (defined line 112-113) is the uniform rejection channel for the whole actor — reuse it for any new validation failures (e.g. unknown resolution method string), following the same `raise CommandRejected(f"...")` string-message convention used throughout `_prepare_*` methods (see lines 209-217, 272-290 for the style).

---

### `tests/test_resolution_d100.py` / `tests/test_grading_d100.py` (test)

**Analog:** `tests/test_resolution_edges.py` (header + `ScriptedRoller`, lines 1-40) and `tests/test_grading.py`

```python
class ScriptedRoller:
    """정해진 눈을 넣은 순서 그대로 돌려주는 가짜 굴림 도구.

    `Roller` 를 상속할 필요가 없다 — 구조적 타이핑(PEP 544)이라
    `roll_d6(self) -> int` 시그니처만 맞으면 통과한다.
    """

    def __init__(self, values):
        self._values = list(values)

    def roll_d6(self) -> int:
        return self._values.pop(0)
```
Mirror this as a `ScriptedPercentileRoller` with `roll_tens()`/`roll_units()` popping from separate pre-seeded lists — same "no inheritance needed, structural typing" docstring convention. Follow `test_resolution_edges.py`'s five-category structure (boundary / adjacency via `hypothesis` / empty-input / order / integer-ness) for `test_resolution_d100.py`, and reuse the `hypothesis`-based adjacency-proof idiom (`test_edge_adjacency_*`, referenced in RESEARCH.md Wave 0 Gaps) for `test_grading_d100.py` to prove d100's grade bands are contiguous/exclusive.

---

## Shared Patterns

### "Reject unknown, never silently skip" (cross-cutting)
**Sources:**
- `UnsupportedModifier` in `src/gptrpg/rules_core/resolution.py:13-27`
- `UnknownEventType` in `src/gptrpg/rules_core/reducer.py:36-46`

**Apply to:** `resolution_d100.py` (unknown modifier types), any new rulebook-data validation (unknown grade names referenced by an entity's `depleted_effect_ref`, etc.). Every new "we don't recognize this input" branch in this phase must raise a named exception, never fall through silently — this is the single most repeated defensive idiom in the codebase (also echoed in RESEARCH.md's Security Domain STRIDE table).

### Frozen dataclass / frozen pydantic model for all data records
**Sources:**
- `@dataclass(frozen=True)` on `Modifier`, `CheckOutcome` (`resolution.py:29,38`)
- `ConfigDict(extra="forbid", frozen=True)` on `EventEnvelope`, `ModifierRecord` (`event_log/schema.py:42,55`)

**Apply to:** `StatEntry`/`Entity` (new `entities.py`), any new rulebook-declaration dataclasses in `rulebooks/openquest.py`. Immutability is a load-bearing convention throughout `rules_core` and `event_log` — new structures should not break it.

### Structural typing (PEP 544 Protocol) for pluggable I/O boundaries
**Source:** `Roller` Protocol, `src/gptrpg/rules_core/dice.py:6-15`

**Apply to:** `PercentileRoller` — add alongside `Roller`, never modify it. Any real or test implementation (`LiveRoller`, `ScriptedRoller`/`ScriptedPercentileRoller`) satisfies the protocol purely by method signature, no explicit subclassing.

### `str`-typed "type"/"grade" fields instead of fixed `Literal`s, for anything a rulebook must be able to extend
**Sources:**
- `Modifier.type: str` (already `str`, not `Literal`) — `resolution.py:33`
- `ModifierRecord.type: str` — `event_log/schema.py:57`

**Apply to:** widening `Grade` in both `grading.py` and `event_log/schema.py` — this is the existing precedent proving the codebase already uses this pattern for modifiers; extending it to grades is consistent, not novel.

### Command→event dispatch always wraps rules_core exceptions into `CommandRejected`
**Source:** `src/gptrpg/session_actor/actor.py:239-244` (`except UnsupportedModifier as exc: raise CommandRejected(str(exc)) from exc`)

**Apply to:** the new `resolve_d100`/`push_d100` call sites inside `_prepare_resolve_check` — same try/except shape, same `from exc` chaining (preserves traceback per existing style).

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `src/gptrpg/rulebooks/openquest.py` | config/data | CRUD (static) | `rulebooks/` is a brand-new layer (RESEARCH.md Recommended Project Structure) — no prior "rulebook declares its own data" module exists in the codebase. Use `Modifier`/`StatEntry` dataclass conventions and pydantic's `ConfigDict(extra="forbid", frozen=True)` style (from `event_log/schema.py`) as the nearest stylistic guide even though no direct analog file exists. |
| `src/gptrpg/rulebooks/dungeonworld_like.py` | config/data | CRUD (static) | Same as above — optional per RESEARCH.md, migrating Phase 1's implicit 2d6 grade names into explicit declared data. |
| `02-INTERFACE-CHANGES.md` | doc | — | New document type for this phase (D-22) — no prior phase produced an equivalent single-purpose "did we touch platform code" ledger. Closest precedent in spirit is `01-04-SUMMARY.md`/`01-06-SUMMARY.md` (Phase 1 SUMMARY docs), but D-22 explicitly requires NOT scattering this across SUMMARYs. |

## Metadata

**Analog search scope:** `src/gptrpg/rules_core/`, `src/gptrpg/event_log/`, `src/gptrpg/session_actor/`, `tests/`
**Files scanned:** `resolution.py`, `grading.py`, `dice.py`, `reducer.py`, `schema.py`, `actor.py`, `live_roller.py`, `test_resolution_edges.py`, `test_grading.py` (9 read directly, full content, ≤150 lines each — no partial reads needed)
**Pattern extraction date:** 2026-08-01
