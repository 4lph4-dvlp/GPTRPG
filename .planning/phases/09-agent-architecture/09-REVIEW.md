---
phase: 09-agent-architecture
reviewed: 2026-08-09T12:31:53Z
depth: standard
files_reviewed: 32
files_reviewed_list:
  - docs/PIPELINE.md
  - README.md
  - src/gptrpg/agents/action_classifier.py
  - src/gptrpg/agents/clock_judge.py
  - src/gptrpg/agents/config.py
  - src/gptrpg/agents/context.py
  - src/gptrpg/agents/invoke.py
  - src/gptrpg/agents/json_parsing.py
  - src/gptrpg/agents/master_gm.py
  - src/gptrpg/agents/prompt_assembly.py
  - src/gptrpg/agents/scene_entity_judge.py
  - src/gptrpg/agents/situation_judge.py
  - src/gptrpg/cli/main.py
  - src/gptrpg/cli/turn_flow.py
  - src/gptrpg/turn/clock_condition.py
  - src/gptrpg/turn/judgments.py
  - src/gptrpg/web/routes_actions.py
  - tests/conftest.py
  - tests/test_agent_config.py
  - tests/test_agent_context_caps.py
  - tests/test_agents_retry.py
  - tests/test_clock_condition_cli.py
  - tests/test_clock_condition_web.py
  - tests/test_clock_judge.py
  - tests/test_master_gm.py
  - tests/test_measurement.py
  - tests/test_narration_isolation.py
  - tests/test_parallel_judgment.py
  - tests/test_prompt_assembly_scenario.py
  - tests/test_scene_entity_judge.py
  - tests/test_situation_judge.py
  - tests/test_turn_flow_failure.py
  - tests/test_turn_tracer.py
  - tests/test_web_actions.py
findings:
  critical: 2
  warning: 2
  info: 2
  total: 6
status: issues_found
---

# Phase 09: Code Review Report

**Reviewed:** 2026-08-09T12:31:53Z
**Depth:** standard
**Files Reviewed:** 32 (30 source/test files touched by Phase 9's three new judgment agents — `situation_judge`, `scene_entity_judge`, `clock_judge` — plus their shared plumbing in `turn/judgments.py`, `turn/clock_condition.py`, `agents/config.py`, `agents/context.py`, `agents/invoke.py`, `agents/json_parsing.py`, and the two call sites in `cli/turn_flow.py` / `web/routes_actions.py`)
**Status:** issues_found

## Summary

Phase 9 adds three new judgment roles that run in parallel with (and sometimes before) narration, and threads them through both the web and CLI turn pipelines while trying hard to preserve two invariants that the docstrings repeat throughout: (1) a judgment-agent failure must never block the turn (D-05/ARCH-05), and (2) the CLI and web paths use "정확히 같은" (exactly the same) actor/store/rules core so they stay behaviorally equivalent. Both invariants are broken in ways the existing test suite does not exercise:

- The exception handling that guarantees "judgment failure doesn't block the turn" was applied to the AI *call* (`gather_turn_judgments`) but not to the *provider construction* step that immediately precedes it, for the three new roles only. A misconfigured `situation_judge`/`scene_entity_judge`/`clock_judge` provider (missing API key, unknown provider name, etc.) now crashes the request/turn **after** the dice roll (`check_resolved`) has already been recorded, unlike every other provider-resolution call site in the same functions, which is wrapped and degrades gracefully.
- The CLI turn flow builds `TurnContext` once, before `ConfirmAction`/`ResolveCheck`, and never rebuilds it — unlike the web `confirm()` handler, which explicitly rebuilds `TurnContext` after the resolve step specifically because the clock/state may have changed (fail-counter auto-advance). The three new judgment agents and `run_clock_condition_check` in the CLI path therefore reason about the threat clock as it stood *before* the roll, not after.

Two additional lower-severity issues (a same-process race on the new "condition" clock-advance background task, and a missing dedupe-within-batch in `scene_entity_judge`) round out the findings, plus two informational nits.

## Critical Issues

### CR-01: New judgment-role provider resolution isn't guarded, so a config error crashes the turn *after* the dice have already been rolled

**Fixed:** commit `334aa05` (2026-08-09) — provider-resolution calls for the three new roles moved inside the existing try/except; falls back to `empty_turn_judgments()` on failure. Verified: `uv run pytest` 629 passed, `lint-imports` 4/4 kept, `ruff check` clean.

**File:** `src/gptrpg/web/routes_actions.py:471-494` and `src/gptrpg/cli/turn_flow.py:300-329`

**Issue:**
Both `confirm()` (web) and `_turn_flow()` (CLI) build providers for `master_gm` inside a `try/except` that turns `ConfigNotFound` / `InvalidAgentConfig` / `UnknownProvider` / `MissingApiKey` / `ProviderNotImplemented` into a controlled response (503 in web, a clean `_cmd_turn` error exit in CLI) — see `routes_actions.py:440-453`. The three *new* Phase 9 roles do not get the same treatment:

```python
# routes_actions.py:470-494 (web) — no try/except around provider_resolver()
situation_judge_choice = choices["situation_judge"]
situation_provider: Provider = request.app.state.provider_resolver(
    "situation_judge", choices, os.environ
)
entity_judge_choice = choices["scene_entity_judge"]
entity_provider: Provider = request.app.state.provider_resolver(
    "scene_entity_judge", choices, os.environ
)
clock_judge_choice = choices["clock_judge"]
clock_provider: Provider = request.app.state.provider_resolver(
    "clock_judge", choices, os.environ
)
try:
    judgments = await gather_turn_judgments(...)
except Exception as exc:  # only guards the *call*, not the construction above
    ...
    judgments = empty_turn_judgments()
```

The same pattern repeats in `cli/turn_flow.py:300-312` (`resolve_provider(...)` calls for `situation_judge`/`scene_entity_judge`/`clock_judge` sit directly above the `try:` that wraps `gather_turn_judgments`).

By the time these lines run, `ResolveCheck` has already been submitted and the dice roll (`check_resolved`) is permanently recorded in the event log (`resolve_seq` is already known). If an operator sets a distinct provider for one of the three new roles and that provider's API key env var is unset (or the provider name is a typo), `provider_resolver`/`resolve_provider` raises `MissingApiKey`/`UnknownProvider` *outside* any try/except in this function:

- **Web:** the exception propagates out of the `async def confirm(...)` handler uncaught → FastAPI returns a generic 500. The client never receives `rolls`/`grade`/`target` for a check that already happened, and there is no narration path left — a retry with the same `declare_seq` re-enters `AlreadyConfirmed`/cached-resolve handling and hits the exact same unguarded provider call again (same misconfiguration ⇒ same crash), so the turn can never complete until an operator fixes the config.
- **CLI:** the exception is eventually caught by `_cmd_turn`'s broad `except (..., MissingApiKey, ...)` in `cli/main.py:466-479`, so the process exits cleanly with `오류: ...`, but the `check_resolved` event (and possibly the fail-counter clock advance triggered by it) is already permanently in the log with no narration ever generated for it.

This directly contradicts the invariant the surrounding code repeatedly documents and tests for — "판단이 실패해도 턴을 막지 않는다" (D-05/ARCH-05) — and is asymmetric with how the exact same function already treats `action_classifier`/`master_gm` provider construction (both wrapped). No test in `test_web_actions.py`, `test_clock_condition_web.py`, `test_turn_tracer.py`, or `test_clock_condition_cli.py` exercises a provider-resolution failure for the three new roles, so this gap is currently invisible to CI.

**Fix:** Wrap the three `provider_resolver(...)`/`resolve_provider(...)` calls in the same try/except used for `master_gm`, and fall back to `empty_turn_judgments()` (or skip that specific judgment) instead of raising — mirroring how `gather_turn_judgments`'s own internal failures are already handled:

```python
# web/routes_actions.py
try:
    situation_judge_choice = choices["situation_judge"]
    situation_provider: Provider = request.app.state.provider_resolver(
        "situation_judge", choices, os.environ
    )
    entity_judge_choice = choices["scene_entity_judge"]
    entity_provider: Provider = request.app.state.provider_resolver(
        "scene_entity_judge", choices, os.environ
    )
    clock_judge_choice = choices["clock_judge"]
    clock_provider: Provider = request.app.state.provider_resolver(
        "clock_judge", choices, os.environ
    )
    judgments = await gather_turn_judgments(...)
except Exception as exc:  # noqa: BLE001 - D-05, provider construction failures are also judgment failures
    print(f"경고: ... — {exc}", file=sys.stderr)
    judgments = empty_turn_judgments()
    situation_judge_choice = entity_judge_choice = clock_judge_choice = None  # or reuse a safe fallback for RecordAiCall/background task guards
```

(The `RecordAiCall` submissions right after already use `judgments.*.ai`, which is safe with `empty_turn_judgments()`; the trickier part is that `clock_provider`/`clock_judge_choice` are also needed later for the background `run_clock_condition_check` call — guard that call with `if judgments.clock.should_check and clock_provider is not None:` or simply skip scheduling the background task when provider construction failed.)

---

### CR-02: CLI turn flow reuses a stale `TurnContext` for the three parallel judgments and the background clock check, unlike the web path

**Fixed:** commit `0ab0605` (2026-08-09) — CLI now rebuilds `ctx` after `ResolveCheck`, mirroring the web handler; rebuilt context confirmed threaded into `gather_turn_judgments`/`build_narration_facts`/`run_clock_condition_check`. Verified: `uv run pytest` 629 passed, `lint-imports` 4/4 kept, `ruff check` clean.

**File:** `src/gptrpg/cli/turn_flow.py:192` (context built) vs. `src/gptrpg/cli/turn_flow.py:312-323, 370, 485-495` (context reused) — contrast with `src/gptrpg/web/routes_actions.py:455-461` (context rebuilt)

**Issue:**
In the web handler, `confirm()` deliberately rebuilds `TurnContext` *after* `ResolveCheck` is submitted, specifically because the clock/state can change during resolution (`_maybe_auto_advance`'s fail-counter trigger):

```python
# routes_actions.py:455-461 — built AFTER resolve_seq is known
ctx = build_turn_context(
    store, session_id, body.rulebook_id,
    character_stats=character.stats, character_names=_CHARACTER_NAMES,
)
```
`docs/PIPELINE.md` §2 documents this explicitly: "⑤ build_turn_context() 재호출 ← 시계·최근 대화가 ③에서 바뀌었으므로 다시 접는다".

The CLI path (`cli/turn_flow.py`) never does this second rebuild. `ctx` is built once, at line 192, *before* `ConfirmAction` (line ~256) and `ResolveCheck` (line ~277):

```python
ctx = _build_turn_context(store, args.session, args.rulebook)   # line 192 — pre-roll snapshot
...
confirm_seq = await actor.submit(ConfirmAction(...))            # ~256
...
resolve_seq = await actor.submit(ResolveCheck(...))             # ~277 — may trigger fail-counter auto-advance here
...
judgments = await gather_turn_judgments(..., ctx=ctx, ...)      # ~312-323 — reuses the PRE-ROLL ctx
facts = build_narration_facts(ctx=ctx, ...)                     # ~370 — same stale ctx
...
await run_clock_condition_check(
    ..., judge_ctx=build_clock_judge_context(ctx, check_summary),  # ~489 — same stale ctx
    clock_id=ctx.clock_state.clock_id, ...
)
```

`ClockJudgeContext`/`TurnContext` both carry `clock_state` (segment index, next-segment description), and `situation_judge`/`clock_judge` both read it (`build_situation_prompt`/`_clock_judge_session_block_text` in `prompt_assembly.py`). When a turn's `ResolveCheck` is the one that pushes `fails_since_clock` over `AUTO_ADVANCE_FAILURE_THRESHOLD` (fail-counter auto-advance fires *inside* the same `actor.submit(ResolveCheck(...))` call), the clock has already moved on by the time `resolve_seq` is returned — but every AI judgment call in this turn (situation, entity, clock-signal gate, and the deep clock-condition check triggered afterward) is still shown the *pre-advance* clock position and the *wrong* "next segment" description. This can produce an incorrect `clock_judge` verdict (reasoning about the segment that just auto-advanced instead of the new "next" one) and an incoherent `situation_judge` summary. It is also silently inconsistent with the tested/documented web behavior for the identical turn shape.

No test in this phase's suite (`test_clock_condition_cli.py`, `test_turn_tracer.py`, `test_turn_flow_failure.py`) combines a fail-counter-triggering `ResolveCheck` with judgment-context assertions, so this divergence isn't caught by CI.

**Fix:** Rebuild `ctx` after `ResolveCheck` in `cli/turn_flow.py`, mirroring the web handler:

```python
resolve_seq = await actor.submit(ResolveCheck(...))
check_event = store.read_events(args.session, from_seq=resolve_seq)[0]
...
ctx = _build_turn_context(store, args.session, args.rulebook)  # rebuild — clock/state may have changed
```
and use this rebuilt `ctx` for `gather_turn_judgments`, `build_narration_facts`, and `run_clock_condition_check`.

## Warnings

### WR-01: Concurrent background `run_clock_condition_check` calls can race on `actor.state.clock_segment` and produce duplicate `clock_advanced` events at the same segment

**File:** `src/gptrpg/turn/clock_condition.py:91-102`, invoked from `src/gptrpg/web/routes_actions.py:637-649`

**Issue:** `run_clock_condition_check` reads `actor.state.clock_segment` (a live, in-memory value on the actor), does an `await asyncio.to_thread(judge_clock_condition, ...)` (which can take seconds), and only *after* that await re-reads `actor.state.clock_segment` to decide the upper bound and to compute `segment_index=actor.state.clock_segment + 1`:

```python
if actor.state.clock_segment >= clock_segment_count:
    return
try:
    await actor.submit(
        AdvanceClock(..., segment_index=actor.state.clock_segment + 1, trigger="condition", ...)
    )
```

The module docstring itself notes `_prepare_clock`은 이 검사를 하지 않으므로 여기서 해야 한다 — i.e., the actor does not itself enforce "don't advance past a segment that was already reached by this trigger." Because `confirm()` schedules this as a FastAPI `BackgroundTasks` job (真正 non-blocking, per the module docstring), two different confirm() requests from two different players acting close together — each of which independently decided `judgments.clock.should_check == True` — can have their background tasks' `await asyncio.to_thread(judge_clock_condition, ...)` calls overlap. If both read `actor.state.clock_segment == N` before either has submitted its `AdvanceClock`, both will submit `AdvanceClock(segment_index=N+1, trigger="condition", ...)`. `actor.submit()` serializes the actual event-log writes, so both will succeed and both will be recorded — producing two `clock_advanced` events with the *same* `segment_index`, which duplicates the "one clock tick" semantics the rest of the system relies on (episode snapshots in `build_report`, the `5/4` display cap, etc., all assume one `clock_advanced` per real advance).

This is a distinct, same-process race from the already-documented cross-process CLI/web caveat in `docs/PIPELINE.md` §9-B item 11 (which is about `ai_choice` from a second CLI process); this one can happen purely from normal multi-player web usage (four browsers acting near-simultaneously is the app's documented normal use case, per `README.md`).

**Fix:** Either (a) make the upper-bound/segment-index decision inside the same serialized command the actor already provides (e.g., have `AdvanceClock`'s handling in the actor itself compute `segment_index = current_segment + 1` and reject/clamp if a concurrent advance already happened, rather than trusting the caller-supplied `segment_index`), or (b) add a lightweight in-process lock/flag on the actor (e.g., "condition-advance in flight") so a second background task started while one is still awaiting `judge_clock_condition` short-circuits instead of re-reading a stale `clock_segment`.

### WR-02: `judge_new_entity` doesn't dedupe within a single model response, so the same "new" entity name can appear twice in one turn

**File:** `src/gptrpg/agents/scene_entity_judge.py:109-114`

**Issue:**
```python
existing_names = frozenset(entity.display_name for entity in ctx.scene_entities)
new_entities = tuple(
    entity for entity in parsed_entities if entity.name not in existing_names
)[:NEW_ENTITY_LIMIT]
```
This filters out names that are already in `ctx.scene_entities`, but does not deduplicate `parsed_entities` against itself. If the model returns the same new name twice in one response (e.g. `[{"name": "부서진 등불", "kind": "thing"}, {"name": "부서진 등불", "kind": "thing"}]`), both survive the filter and both get counted against `NEW_ENTITY_LIMIT`, and `build_narration_facts` will pass a `new_entities` tuple containing the duplicate straight into `build_gm_prompt`'s turn message ("이번 장면에 새로 등장하는 대상: 부서진 등불, 부서진 등불"). This wastes a limit slot and can nudge the narrator into mentioning the same object twice in one turn.

**Fix:**
```python
seen: set[str] = set()
new_entities: list[NewEntity] = []
for entity in parsed_entities:
    if entity.name in existing_names or entity.name in seen:
        continue
    seen.add(entity.name)
    new_entities.append(entity)
new_entities = tuple(new_entities)[:NEW_ENTITY_LIMIT]
```

## Info

### IN-01: Greedy JSON-array regex can mis-parse a valid array followed by trailing bracket-containing prose

**File:** `src/gptrpg/agents/json_parsing.py:14`

**Issue:** `_JSON_ARRAY = re.compile(r"\[.*\]", re.DOTALL)` is greedy, so it matches from the *first* `[` to the *last* `]` in the (think-block-stripped, fence-stripped) text. If a reasoning model emits the correct array followed by trailing prose that itself contains an unmatched `]` (e.g. "...입니다[참고]"), the regex will capture the array plus everything up to that trailing bracket, producing invalid JSON that falls back to an empty list — even though the model's actual JSON answer was well-formed. This is a pre-existing pattern (moved, not introduced, by 09-01) and the fallback path is safe (empty list = "no candidates", same as an intentional empty response), so this is informational rather than a functional break, but it's worth a `re.compile(r"\[.*?\]", re.DOTALL)` first-match attempt before falling back to the greedy one, given how much of Phase 9 depends on this parser for four more agent roles now.

**Fix:** Consider trying a non-greedy match first (`\[.*?\]`) and only falling back to the current greedy match (or `[]`) if the non-greedy parse fails — reduces false negatives on reasoning-model chatter without touching the already-tested happy paths.

### IN-02: Stale CLI help text still says "두 역할 모두" (both roles) for `--provider`/`--model`, but now applies to all five roles

**File:** `src/gptrpg/cli/main.py:588, 593`

**Issue:** `turn_parser.add_argument("--provider", ..., help="두 역할 모두에 쓸 제공자 이름(빠른 수동 시험용)...")` (and the matching `--model` help text) predates Phase 9. Since `_resolve_role_choice` now applies the `--provider`/`--model` override to all five roles (`action_classifier`, `master_gm`, `situation_judge`, `scene_entity_judge`, `clock_judge` — see `cli/turn_flow.py:104-116`), the help text undersells what the flag actually does and could confuse an operator debugging why a "two role" override affected `clock_judge` too.

**Fix:** Update the help strings to "다섯 역할 모두에 쓸..." (or generically "모든 역할에 쓸...") to match current behavior.

---

_Reviewed: 2026-08-09T12:31:53Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
