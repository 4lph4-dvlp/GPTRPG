---
phase: 02-two-rulebooks-one-vessel
reviewed: 2026-08-02T00:00:00Z
depth: standard
files_reviewed: 22
files_reviewed_list:
  - .importlinter
  - LICENSES.md
  - src/gptrpg/cli/main.py
  - src/gptrpg/event_log/replay_roller.py
  - src/gptrpg/event_log/schema.py
  - src/gptrpg/rulebooks/__init__.py
  - src/gptrpg/rulebooks/dungeonworld_like.py
  - src/gptrpg/rulebooks/openquest.py
  - src/gptrpg/rulebooks/openquest_creatures.py
  - src/gptrpg/rules_core/dice.py
  - src/gptrpg/rules_core/entities.py
  - src/gptrpg/rules_core/grading.py
  - src/gptrpg/rules_core/reducer.py
  - src/gptrpg/rules_core/resolution.py
  - src/gptrpg/rules_core/resolution_d100.py
  - src/gptrpg/rules_core/rulebook.py
  - src/gptrpg/session_actor/actor.py
  - src/gptrpg/session_actor/live_roller.py
  - tests/conftest.py
  - tests/test_cli.py
  - tests/test_entities.py
  - tests/test_event_log.py
  - tests/test_grading_d100.py
  - tests/test_reducer_failure_count.py
  - tests/test_resolution_d100.py
  - tests/test_session_actor.py
  - tests/test_tracer_d100.py
findings:
  critical: 1
  warning: 6
  info: 2
  total: 9
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-08-02T00:00:00Z
**Depth:** standard
**Files Reviewed:** 22 (source: 16, tests: 10, docs: 2 — counted once each; `.importlinter`/`LICENSES.md` are non-code but were reviewed for contract/attribution correctness)
**Status:** issues_found

## Summary

Reviewed the Phase 2 "two rulebooks, one vessel" deliverable: the OpenQuest d100 roll-under
resolver (`resolution_d100.py`), the generalized `GradeBand`/`Rulebook` declaration model
(`rulebook.py`), the two shipped rulebook declarations (`dungeonworld_like.py`,
`openquest.py`, `openquest_creatures.py`), the session actor's new rulebook-dispatch path
(`actor.py`), the CLI's `--rulebook` plumbing (`main.py`), and the full test suite covering
these paths. `pytest` (212 tests), `ruff check`, and `lint-imports` all pass clean on this
tree — the code is well-tested and the layering contracts hold.

The core d100 math (percentile decomposition, bonus/penalty dice, push rolls, grade-band
matching) is correct and thoroughly verified by both example-based and property-based
(Hypothesis) tests. However, adversarial review of the **new rulebook-dispatch path** in
`session_actor/actor.py` found a real gap in the "commands are rejected cleanly, never crash
with a raw traceback" contract that the rest of the CLI enforces and tests for: one of the
exceptions `resolve_d100` can raise (`NoMatchingGradeBand`) is not caught by
`_prepare_resolve_check`, so a rulebook whose declared grade bands don't fully cover the
margin/doubles space crashes the whole process with an unhandled Python traceback instead of
a one-line `CommandRejected` message. I reproduced this concretely (see CR-01). It is not
reachable through the two rulebooks shipped in this phase (both declare an unconditional
catch-all band), but it is directly reachable through the exact extension point
("register a `Rulebook` in `RULEBOOKS`") this phase introduces, and the surrounding code
(`resolution_d100.py`'s own docstrings) explicitly anticipates future rulebook uploads as a
trust boundary. Several smaller robustness/quality issues around the same code path are
listed as warnings below.

## Critical Issues

### CR-01: `NoMatchingGradeBand` from a d100 check is not caught — crashes the CLI with a raw traceback

**File:** `src/gptrpg/session_actor/actor.py:271-299` (`_prepare_resolve_check`), root cause in `src/gptrpg/rules_core/rulebook.py:69-84` (`grade_for_margin`)

**Issue:** `_prepare_resolve_check` wraps the call to `resolver(self._roller, command, rulebook)`
in a `try/except` that only catches `UnsupportedModifier` and `AttributeError`:

```python
try:
    outcome = resolver(self._roller, command, rulebook)
except UnsupportedModifier as exc:
    raise CommandRejected(str(exc)) from exc
except AttributeError as exc:
    raise CommandRejected(...) from exc
```

For the `D100_ROLL_UNDER` resolution method, `resolver` is `_resolve_d100_roll_under` →
`resolve_d100`, which calls `grade_for_margin(margin, is_doubles, bands)`
(`resolution_d100.py:142`). `grade_for_margin` raises `rulebook.NoMatchingGradeBand` when no
declared `GradeBand` matches the computed margin/doubles combination
(`rulebook.py:69-84`) — this is *not* one of the two exception types caught above, so it
propagates uncaught through `_process` → `SessionActor._run`'s catch-all
(`except Exception as exc: future.set_exception(exc)`) → the CLI's `_cmd_submit`, whose
`except (CommandRejected, SequenceConflict)` clause (`cli/main.py:104`) does not match either.
The result is an unhandled exception at the top of `main()`, printed as a full Python
traceback with a non-zero exit code — exactly the failure mode the project's own tests
(`test_submit_with_invalid_argument_exits_nonzero_with_readable_message`,
`test_submit_roll_with_unknown_rulebook_exits_nonzero_without_traceback`,
`test_submit_sequence_conflict_becomes_one_line_message_not_traceback`) explicitly assert
must never happen for a rejected command.

This is unreachable via `dungeonworld_like` (uses `grade_for_total`, not
`grade_for_margin` at all) and unreachable via the shipped `openquest` bands (the `failure`
band has no constraints at all, so it always matches as a catch-all). It **is** reachable the
moment any rulebook is registered whose `grade_bands` don't cover the full margin/doubles
space — precisely the extension mechanism this phase built, and precisely the scenario
`resolution_d100.py`'s own `MAX_BONUS_DICE_MAGNITUDE` docstring calls out ("M1의 룰북
업로드가 이 자리를 신뢰 경계로 바꾼다" — a future user-uploaded-rulebook trust boundary).

Reproduced directly:

```python
# Register a rulebook with an incomplete grade-band declaration (no catch-all band)
HOLED = Rulebook(rulebook_id="holed", display_name="holed",
                  resolution_method=D100_ROLL_UNDER,
                  grade_bands=(GradeBand(name="only-high", counts_as_failure=False,
                                         margin_at_least=1000),))
RULEBOOKS["holed"] = HOLED
main(["submit", "--db", db, "--session", "s1", "roll",
      "--rulebook", "holed", "--target", "50", "--move", "x"])
```

Output:

```text
Traceback (most recent call last):
  ...
  File ".../rules_core/rulebook.py", line 84, in grade_for_margin
    raise NoMatchingGradeBand(margin, is_doubles)
gptrpg.rules_core.rulebook.NoMatchingGradeBand: margin=33, is_doubles=False에 맞는 등급 밴드가 없다
```

**Fix:** Catch `NoMatchingGradeBand` alongside `UnsupportedModifier`/`AttributeError` in
`_prepare_resolve_check` and turn it into a `CommandRejected`, matching the pattern already
used for `UnknownGradeName` two lines below it:

```python
from gptrpg.rules_core.rulebook import NoMatchingGradeBand  # add to existing import

try:
    outcome = resolver(self._roller, command, rulebook)
except UnsupportedModifier as exc:
    raise CommandRejected(str(exc)) from exc
except NoMatchingGradeBand as exc:
    raise CommandRejected(
        f"룰북 {rulebook.rulebook_id!r}의 등급 밴드 선언에 빈틈이 있다: {exc}"
    ) from exc
except AttributeError as exc:
    raise CommandRejected(...) from exc
```

## Warnings

### WR-01: `except AttributeError` in `_prepare_resolve_check` is overly broad and untested

**File:** `src/gptrpg/session_actor/actor.py:290-294`

**Issue:** The `except AttributeError` clause is intended to catch the case where the roller
object doesn't implement `roll_tens`/`roll_units` for a d100 check. But it will catch *any*
`AttributeError` raised anywhere inside `resolver(...)`'s call chain — including a genuine
internal bug (e.g. a typo'd attribute access inside `resolve_d100` or a future rulebook
helper). Such a bug would be silently re-labeled as "굴림 도구가 ... 필요한 메서드를 갖추지
않았다" (the roller is missing a required method), which is misleading and would send anyone
debugging a real defect down the wrong path. There is also no test in the suite that exercises
this branch at all (confirmed via `grep` for the message text — it only appears in the source,
never referenced by a test), so a regression here would go unnoticed.

**Fix:** Narrow the catch to only the roller-shape mismatch it's meant to guard, e.g. by
checking `hasattr` on the roller before calling the resolver, or by wrapping only the specific
`roller.roll_tens()`/`roll_units()` calls inside `resolve_d100` with a more targeted exception.
At minimum, add a regression test that passes a `Roller` (2d6-only) into an `openquest` check
and asserts the resulting `CommandRejected` message, so the branch is actually covered.

### WR-02: `UnsupportedModifier` is reused with a misleading message for the bonus-dice magnitude cap

**File:** `src/gptrpg/rules_core/resolution_d100.py:125-128`

**Issue:** When the combined `BONUS_DICE` value exceeds `MAX_BONUS_DICE_MAGNITUDE`, the code
raises:

```python
raise UnsupportedModifier(BONUS_DICE, "combined bonus_dice sum", resolver="resolve_d100")
```

`UnsupportedModifier.__str__` always renders as `"{resolver} does not know how to apply
modifier type {modifier_type!r} from source {source!r}"`, so the resulting message is:

```
resolve_d100 does not know how to apply modifier type 'bonus_dice' from source 'combined bonus_dice sum'
```

(confirmed by direct reproduction). This is factually wrong — `resolve_d100` understands
`bonus_dice` perfectly well; the real problem is that the *magnitude* is out of the sane
range (T-02-06 guard against runaway roller calls). A player or integrator hitting this will
be told the modifier type is unsupported, which is misleading and will send them looking in
the wrong place (e.g. rechecking the modifier's `type` string) instead of the actual issue
(the summed value is too large).

**Fix:** Raise a distinct, purpose-built exception (or at least a clearer message) for the
magnitude cap, e.g.:

```python
class BonusDiceMagnitudeExceeded(Exception):
    def __init__(self, dice_delta: int) -> None:
        super().__init__(
            f"bonus_dice 합계 {dice_delta}의 절대값이 상한 "
            f"{MAX_BONUS_DICE_MAGNITUDE}을 넘었다"
        )
```
and catch it alongside `UnsupportedModifier` in `_prepare_resolve_check`.

### WR-03: `difficulty_modifier` raises a bare `KeyError` for unknown difficulty names

**File:** `src/gptrpg/rulebooks/openquest.py:41-53`

**Issue:** `OPENQUEST_DIFFICULTY[name]` (line 51, inside `difficulty_modifier`) raises a plain
`KeyError` with no descriptive message if `name` isn't one of the five declared difficulty
levels. Every other user-facing lookup failure in this codebase gets a purpose-built,
descriptive exception (`UnknownRulebook`, `UnknownGradeName`, `NoMatchingGradeBand`,
`InvalidStatEntry`, `InvalidEntity`) that clearly states what was looked up and why it
failed. `difficulty_modifier` breaks that convention. It isn't currently wired to the CLI
(no `--difficulty` flag exists in `main.py`), so the blast radius today is limited to direct
callers/tests, but the inconsistency will surface as soon as this helper is exposed through
a command.

**Fix:** Validate and raise a descriptive exception, e.g.:

```python
def difficulty_modifier(name: str) -> Modifier:
    if name not in OPENQUEST_DIFFICULTY:
        raise ValueError(
            f"알 수 없는 OpenQuest 난이도: {name!r} "
            f"(가능한 값: {sorted(OPENQUEST_DIFFICULTY)})"
        )
    return Modifier(type=TARGET_SHIFT, value=OPENQUEST_DIFFICULTY[name],
                     source=f"openquest:difficulty:{name}")
```

### WR-04: `SessionActor.state` is computed on every event but never read anywhere

**File:** `src/gptrpg/session_actor/actor.py:157`, `:210`

**Issue:** `SessionActor.__init__` sets `self.state: GameState = initial_state(session_id)`
and `_process` updates it after every successfully appended event:
`self.state = apply_event(self.state, event.event_type, event.model_dump())`. A repo-wide
search shows this attribute is never read by any other module, test, or the CLI — the actual
"what is the current game state" question is always answered by
`session_actor.projection.rebuild_state(store, session_id)`, which replays the store from
scratch (per `test_full_six_command_session_reconstructs_to_expected_state`,
`test_rebuild_state_does_not_write_and_is_repeatable`). This leaves two independent code
paths computing "the session state" — one incremental and unused, one authoritative and
tested — with no test asserting they agree. If `apply_event` is ever changed and
`self.state`'s incremental accumulation silently drifts from a fresh `rebuild_state()` replay,
nothing would catch it, because nothing consumes `self.state`.

**Fix:** Either remove the dead `self.state` tracking from `SessionActor` (simplifying
`_process` and the constructor), or, if it's meant to be used as a caching optimization
later, add a test that asserts `actor.state == rebuild_state(store, session_id)` after each
command so drift is caught immediately.

### WR-05: `push_d100`/`reroll_2d6` are fully implemented and tested but unreachable from the actual product surface

**File:** `src/gptrpg/rules_core/resolution.py:81` (`reroll_2d6`), `src/gptrpg/rules_core/resolution_d100.py:154` (`push_d100`)

**Issue:** Both functions are exercised thoroughly by unit tests
(`tests/test_resolution_d100.py`'s push-roll section), but neither is called from
`session_actor/actor.py` or `cli/main.py`. There is no CLI subcommand or `ResolveCheck`
variant that lets a real session actually perform a re-roll or push roll — the only way to
invoke this logic today is a direct unit test import. This may be intentional (deferred to a
later phase), but as written it means the "push roll" feature described at length in the
module docstrings and `LICENSES.md`-adjacent design notes does not exist for an end user of
the CLI. Worth flagging explicitly so it isn't mistaken for delivered, reachable
functionality in phase sign-off.

**Fix:** Either wire a `push`/`reroll` CLI subcommand (and corresponding `SessionActor`
command) before considering this feature "done," or note in the phase's scope/summary
documentation that push/reroll is rules-core-only in this phase and CLI wiring is deferred.

### WR-06: `ScriptedPercentileRoller` is copy-pasted verbatim across three test files

**File:** `tests/test_grading_d100.py:26-37`, `tests/test_resolution_d100.py:24-45`, `tests/test_tracer_d100.py:18-33`

**Issue:** The same helper class (a fake `PercentileRoller` that pops pre-scripted
tens/units values) is defined independently in three test modules. The docstrings even
cross-reference each other ("동일한 관례" / "같은 이름 클래스와 동일한 관례") acknowledging
the duplication as a deliberate convention rather than an oversight. `test_resolution_d100.py`'s
copy additionally tracks call counts (`tens_call_count`/`units_call_count`) that the other two
don't — a subtle behavioral drift between "identical" copies. Any future fix to the shared
behavior (e.g. a clearer `IndexError` message when the scripted list runs out) has to be
applied in three places, and it's easy to update one copy and miss the others.

**Fix:** Factor this into `tests/conftest.py` (or a small `tests/_helpers.py`) as a single
shared class with call-count tracking included, and import it from all three test modules.

## Info

### IN-01: `Rulebook`/`GradeBand` have no structural validation against grade-band gaps

**File:** `src/gptrpg/rules_core/rulebook.py:19-41`

**Issue:** Nothing in the `GradeBand`/`Rulebook` dataclasses (both plain `@dataclass(frozen=True)`
with no `__post_init__`) checks that a rulebook's declared `grade_bands` actually cover the
full margin/doubles space, or that band names are unique. This is what allows the scenario in
CR-01 to be constructed in the first place. `rules_core/entities.py`'s `Entity`/`StatEntry`
show the project's own convention for this kind of guard (`__post_init__` raising a
descriptive `Invalid*` exception) — `Rulebook`/`GradeBand` don't follow it.

**Fix:** Consider adding a lightweight sanity check at registration time (`get_rulebook`) or
declaration time that a rulebook's bands contain at least one fully-unconstrained catch-all
band (no `margin_at_least`/`margin_at_most`/`requires_doubles`), so a misconfigured rulebook
fails fast and loudly at registration instead of lazily inside a live check resolution.

### IN-02: `--target`'s CLI default (`DEFAULT_TARGET = 10`) is a 2d6-tuned constant reused as the d100 "skill" default

**File:** `src/gptrpg/cli/main.py:164-173`, `src/gptrpg/rules_core/grading.py:8`

**Issue:** `roll_parser`'s `--target` defaults to `grading.DEFAULT_TARGET` (10), which was
defined for the 2d6 dungeonworld-like resolution ("total needed to hit"). The same default is
reused verbatim when `--rulebook openquest` is selected, where `--target` means "skill
percentage." A user who runs `roll --rulebook openquest --move x` without remembering to pass
`--target` silently gets a skill of 10% (a near-guaranteed failure) with no warning that the
default doesn't make sense for the selected rulebook. The help text does explain the dual
meaning, but there's no guard against an obviously-wrong default slipping through.

**Fix:** Consider making `--target` required when `--rulebook` isn't the default
(`dungeonworld_like`), or picking a resolution-method-aware default (e.g. via
`rulebook.resolution_method`) rather than one constant shared across semantically different
scales.

---

_Reviewed: 2026-08-02T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
