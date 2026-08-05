# Phase 5: 실험 실행 — 두 번, 1주 간격 - Pattern Map

**Mapped:** 2026-08-03
**Files analyzed:** 6 (1 new module + 5 modified files)
**Analogs found:** 6 / 6

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `src/gptrpg/rulebooks/threat_clocks.py` (신규) | config/model (data-declaration module) | batch (static content declared once, read every turn) | `src/gptrpg/rulebooks/openquest_creatures.py` | exact — same role (룰북-인접 손 작성 콘텐츠 모듈), same flow (정적 `Entity`/`StatEntry` 상수 선언) |
| `src/gptrpg/agents/context.py` (`ClockState` 확장) | model (frozen dataclass value object) | transform (grows an existing value object, no new flow) | same file, `TurnContext`/`ENTITY_FIELD_NAMES` field-lock convention | exact — literally the file being edited; convention borrowed from `rules_core/entities.py` |
| `src/gptrpg/turn/context.py` (`build_turn_context` 확장) | service (state-assembly / read-then-transform) | CRUD (read `EventStore`/`rebuild_state`) → transform into `TurnContext` | same file — existing `clock_state`/`scene_entities` assembly block | exact — extending the function in place, no external analog needed |
| `src/gptrpg/agents/prompt_assembly.py` (`_format_clock_state` 확장) | transform / formatter | transform (value object → cached prompt text) | same file — sibling formatters `_format_scene_entities`, `_format_character_state` | exact — three formatters share one signature shape `(value) -> str` |
| `src/gptrpg/rulebooks/dungeonworld_like.py` (`EXAMPLE_SINGLE_STAT_FOE` 참고/대체 근거) | config/model | batch | `src/gptrpg/rulebooks/openquest_creatures.py` (Entity 선언 관례) | role-match — placeholder being superseded by scenario cast, not edited directly |
| `src/gptrpg/web/characters_data.py` (`seon`/`hodu` 교체) | model (data-declaration dict of Entities) | CRUD (static lookup table, `get_character`) | same file — `bram`/`nari` entries as the in-file analog for `seon`/`hodu` | exact — literally sibling dict entries in the same file |
| `tests/test_prompt_assembly_scenario.py` (신규) | test | request-response (prompt string assertions) | `tests/test_turn_tracer.py::test_classifier_system_prompt_is_byte_identical_across_calls_with_different_text` (line 160) | exact — same byte-identical-caching assertion pattern, same fixtures (`fake_provider`, `_run_turn`) |

## Pattern Assignments

### `src/gptrpg/rulebooks/threat_clocks.py` (신규 config/model, batch)

**Analog:** `src/gptrpg/rulebooks/openquest_creatures.py` (full file, 79 lines — small enough to read in one pass)

**Module docstring pattern** (lines 1-12): every hand-authored content module opens with a docstring stating (a) where the content came from / that it's self-authored, (b) what fields are deliberately NOT included and why, (c) pointer to the license/authorship doc if relevant.
```python
"""OpenQuest System Resource Document(CC BY 4.0)의 크리처 두 종을 실제 수치
그대로 옮긴다 — 메인 룰북이 아니라 SRD 페이지 원문에서 옮겼다. 여기 적힌
수치는 이 단계가 지어낸 것이 하나도 없다(D-18).
...
무기·주문·이동력·특수능력 등 나머지 항목은 담지 않는다 — 룰북 데이터의
필드 단위 상세 규격은 M0 범위 밖이다.
"""
```
For `threat_clocks.py`, adapt to: "이 시나리오는 Claude가 창작한 것이며 특정 룰북/저작물의 원문이 아니다(D-46)."

**Imports pattern** (lines 14-15):
```python
from gptrpg.rulebooks.openquest import OPENQUEST_ID
from gptrpg.rules_core.entities import Entity, StatEntry
```
For the new module: `from gptrpg.rulebooks.dungeonworld_like import DUNGEONWORLD_LIKE_ID` + `from gptrpg.rules_core.entities import Entity, StatEntry`.

**Core Entity-declaration pattern** (lines 17-47, one creature shown):
```python
OPENQUEST_GOBLIN = Entity(
    entity_id="openquest.goblin",
    display_name="Goblin",
    rulebook_id=OPENQUEST_ID,
    stats=(
        StatEntry(name="STR", current=10),
        ...
        StatEntry(
            name="Hit Points",
            current=9,
            max=9,
            depleted_effect_ref="openquest.hit_points_depleted",
        ),
    ),
)
```
Cast NPCs without combat stats can use `stats=()` per `rules_core/entities.py:64-77` (`stats` defaults to `()`) and `entities.py:79-90` (`InvalidEntity` only fires on empty `entity_id`/`display_name`/`rulebook_id`).

**Tuple-of-all-declared-things pattern** (line 79):
```python
OPENQUEST_CREATURES: tuple[Entity, ...] = (OPENQUEST_GOBLIN, OPENQUEST_SKELETON)
```
For the new module: `THREAT_CAST: tuple[Entity, ...] = (...)` — this tuple is what gets assigned directly to `scene_entities` in `build_turn_context` (D-48, fixed cast every turn, no per-scene filtering).

**Non-Entity scenario content (name/identity/wants/segments/catastrophe):** no existing analog is an exact dataclass match (this is genuinely new shape) — declare as plain module-level `str`/`tuple[str, ...]` constants or a small `@dataclass(frozen=True)`, following the `@dataclass(frozen=True)` convention used everywhere else in `agents/context.py` and `rules_core/entities.py`. Recommended minimal field set per RESEARCH.md Open Questions §1: name, threat identity, threat wants, 4 segment descriptions, catastrophe text — omit "진행 조건"/"상태" since `segment_index` already tracks progression.

---

### `src/gptrpg/agents/context.py` — `ClockState` field extension (model, transform)

**Analog:** same file, the `TURN_CONTEXT_FIELD_NAMES` lock convention (lines 55-57) and `ClockState` itself (lines 32-38).

**Current state** (lines 32-38):
```python
@dataclass(frozen=True)
class ClockState:
    """위협 시계 상태 한 조각 — 몇 번째 칸인지와 전체 칸 수."""

    clock_id: str
    segment_index: int
    segment_count: int
```

**Extension pattern** — add fields with safe defaults so `tests/test_turn_tracer.py`'s existing `ClockState(...)` call sites don't break:
```python
@dataclass(frozen=True)
class ClockState:
    clock_id: str
    segment_index: int
    segment_count: int
    threat_name: str = ""
    threat_identity: str = ""
    threat_wants: str = ""
    segment_descriptions: tuple[str, ...] = ()
    catastrophe_text: str = ""
```
**Do not** add a 5th field to `TurnContext` — the file's own lock comment (lines 55-57) forbids it:
```python
# 칸이 정확히 넷임을 코드로도 고정한다 — `entities.py`의 `ENTITY_FIELD_NAMES`
# 관례를 그대로 따른다.
TURN_CONTEXT_FIELD_NAMES = frozenset(f.name for f in fields(TurnContext))
```

---

### `src/gptrpg/turn/context.py` — `build_turn_context` extension (service, CRUD→transform)

**Analog:** same file, existing assembly block (lines 73-89).

**Imports pattern** (lines 11-15) — add the new scenario module import alongside the existing rulebook import:
```python
from gptrpg.agents.context import ClockState, RECENT_TURNS_LIMIT, TurnContext
from gptrpg.event_log.store import EventStore
from gptrpg.rules_core.entities import StatEntry
from gptrpg.rulebooks.dungeonworld_like import EXAMPLE_SINGLE_STAT_FOE  # replaced by scenario import
from gptrpg.session_actor.projection import rebuild_state
```

**Current assembly to modify** (lines 73-82):
```python
clock_state = ClockState(
    clock_id="threat",
    segment_index=state.clock_segment,
    segment_count=PLACEHOLDER_CLOCK_SEGMENT_COUNT,   # 6 → 4
)

scene_entities = (EXAMPLE_SINGLE_STAT_FOE,)          # → THREAT_CAST from threat_clocks.py
character_state = (
    character_stats if character_stats is not None else EXAMPLE_SINGLE_STAT_FOE.stats
)
```
`PLACEHOLDER_CLOCK_SEGMENT_COUNT = 6` is declared at line 17 in this same file — changing it to `4` also fixes `web/routes_events.py:88`'s `clock_segment_count=PLACEHOLDER_CLOCK_SEGMENT_COUNT` display automatically (single source of truth, confirmed via `web/routes_events.py:25,88`).

**Docstring-as-contract pattern** (lines 57-61) — must be preserved when editing, it documents the "no observability metrics leak into the prompt" boundary:
```python
"""시계 정보는 「지금 몇 번째 칸인가」까지만 넣는다. `clock_advances`
(그동안 몇 번 돌았나)도 `fails_since_clock`(실패가 몇 번 쌓였나)도
`TurnContext`에 넣지 않는다 ..."""
```

---

### `src/gptrpg/agents/prompt_assembly.py` — `_format_clock_state` extension (transform/formatter)

**Analog:** same file, sibling formatters `_format_scene_entities` (lines 35-42) and `_format_character_state` (lines 45-48) — both follow `def _format_x(value) -> str: ...` with an explicit "(없음)" fallback for empty/falsy input.

```python
def _format_scene_entities(entities: tuple) -> str:
    if not entities:
        return "(장면에 등장한 대상 없음)"
    lines = []
    for entity in entities:
        stats = ", ".join(f"{stat.name} {stat.current}" for stat in entity.stats)
        lines.append(f"- {entity.display_name} ({entity.entity_id}): {stats}")
    return "\n".join(lines)
```

**Current implementation to extend** (lines 51-52):
```python
def _format_clock_state(clock) -> str:
    return f"{clock.clock_id}: {clock.segment_index}/{clock.segment_count}"
```
Extend to fold in `threat_name`/`threat_identity`/`threat_wants`/`segment_descriptions`/`catastrophe_text`. Follow the ASVS V5 caveat from RESEARCH.md: guard against empty string defaults producing malformed text like `"위협 시계: : 1/4"` — use the same "(없음)" fallback idiom as the sibling formatters when a field is empty.

**Caching-boundary constraint** (file docstring, lines 1-10 — must not be violated):
```python
"""... 시각·플레이어 표시 이름·세션 식별자·추적 번호처럼 호출마다 달라지는
값은 `system` 안에 한 글자도 넣지 않는다 — 넣는 순간 그 뒤로는 캐시가
매번 깨진다."""
```
`_session_block_text` (lines 61-66) is the caller that must remain byte-identical across calls within the same clock segment:
```python
def _session_block_text(ctx: TurnContext) -> str:
    return (
        f"장면 대상:\n{_format_scene_entities(ctx.scene_entities)}\n\n"
        f"캐릭터 상태: {_format_character_state(ctx.character_state)}\n\n"
        f"위협 시계: {_format_clock_state(ctx.clock_state)}"
    )
```

---

### `src/gptrpg/web/characters_data.py` — `seon`/`hodu` value replacement (model, CRUD)

**Analog:** same file — `bram`/`nari` entries (lines 23-64) are the in-file analog for editing `seon`/`hodu` (lines 65-102). Same `Entity`/`StatEntry` structure, only the values change (D-49 — no shape change, `ENTITY_FIELD_NAMES` lock must not be touched per the file's own docstring lines 10-14).

```python
"seon": Entity(
    entity_id="player.seon",
    display_name="선",
    rulebook_id=DUNGEONWORLD_LIKE_ID,
    stats=(
        StatEntry(name="체력", current=14, max=14, depleted_effect_ref="dungeonworld_like.hp_depleted"),
        StatEntry(name="STR", current=-1),
        StatEntry(name="DEX", current=0),
        StatEntry(name="CON", current=0),
        StatEntry(name="INT", current=2),
        StatEntry(name="WIS", current=1),
        StatEntry(name="CHA", current=1),
    ),
),
```
Also update `CHARACTER_ARCHETYPES` (lines 107-112) sibling dict entry for `seon`/`hodu` to match whatever the two non-experienced participants create verbally (D-49/discretion — exact values decided at session-prep time, not by planning).

---

### `tests/test_prompt_assembly_scenario.py` (신규 test, request-response)

**Analog:** `tests/test_turn_tracer.py:160` — `test_classifier_system_prompt_is_byte_identical_across_calls_with_different_text`.

```python
def test_classifier_system_prompt_is_byte_identical_across_calls_with_different_text(
    tmp_db_path, monkeypatch, fake_provider
):
    db = str(tmp_db_path)
    _install_fake_provider(monkeypatch, fake_provider)

    assert _run_turn(db, "s1", "문을 두드린다", monkeypatch=monkeypatch) == 0
    assert _run_turn(db, "s1", "창문으로 넘어간다", monkeypatch=monkeypatch) == 0

    turn1_classifier_system, _turn1_messages = fake_provider.calls[0]
    turn2_classifier_system, _turn2_messages = fake_provider.calls[2]

    assert turn1_classifier_system == turn2_classifier_system
```
Reuse this fixture set (`tmp_db_path`, `monkeypatch`, `fake_provider`, `_install_fake_provider`, `_run_turn`) directly — new test asserts two things: (1) `_session_block_text`/`_format_clock_state` output contains the scenario's `threat_name`/`threat_identity` substrings, (2) the byte-identical assertion still holds across two calls within the same clock segment (same pattern as above, applied post-scenario-injection).

## Shared Patterns

### Frozen dataclass + field-lock convention
**Source:** `src/gptrpg/agents/context.py:55-57` (`TURN_CONTEXT_FIELD_NAMES`), mirrored by `src/gptrpg/rules_core/entities.py:93-96` (`ENTITY_FIELD_NAMES`/`STAT_ENTRY_FIELD_NAMES`)
**Apply to:** Any edit to `ClockState`, `TurnContext`, `Entity`, `StatEntry` — always check for a `frozenset(f.name for f in fields(X))` sentinel nearby before adding/removing fields; extend the sentinel-adjacent container (`ClockState`) rather than the locked one (`TurnContext`/`Entity`).

### Hand-authored data module docstring convention
**Source:** `src/gptrpg/rulebooks/openquest_creatures.py:1-12`, `src/gptrpg/web/characters_data.py:1-15`
**Apply to:** `threat_clocks.py` — state provenance (Claude-authored, D-46), state what's intentionally omitted, cross-reference the relevant decision ID.

### Formatter fallback-for-empty idiom
**Source:** `src/gptrpg/agents/prompt_assembly.py:35-48` (`_format_scene_entities`, `_format_character_state`)
**Apply to:** `_format_clock_state` extension — every formatter in this file returns a Korean "(없음)" placeholder string rather than emitting empty/malformed text when input is falsy.

### Prompt caching stability rule
**Source:** `src/gptrpg/agents/prompt_assembly.py:1-10` (module docstring)
**Apply to:** Any value flowing into `_session_block_text`/`_format_clock_state` — must change only when the clock segment changes, never per-call (no timestamps, no per-request IDs).

## No Analog Found

None — all 6 target files have a strong same-file or same-role/same-flow in-codebase analog. The only genuinely novel shape is the scenario content dataclass (name/identity/wants/segment descriptions/catastrophe) inside `threat_clocks.py`, which has no direct dataclass analog in the codebase but follows the universal `@dataclass(frozen=True)` convention used by every other value object in `agents/context.py` and `rules_core/entities.py`.

## Metadata

**Analog search scope:** `src/gptrpg/rulebooks/`, `src/gptrpg/agents/`, `src/gptrpg/turn/`, `src/gptrpg/web/characters_data.py`, `tests/test_turn_tracer.py`
**Files scanned:** 8 (6 target files + `openquest_creatures.py` + `test_turn_tracer.py`, all read in full — none exceeded 2,000 lines)
**Pattern extraction date:** 2026-08-03
