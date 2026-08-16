---
phase: 11-rulebook-vocabulary
reviewed: 2026-08-17T00:00:00Z
depth: standard
files_reviewed: 29
files_reviewed_list:
  - src/gptrpg/rules_core/entities.py
  - src/gptrpg/rules_core/rulebook.py
  - src/gptrpg/rulebooks/__init__.py
  - src/gptrpg/rulebooks/cairn.py
  - src/gptrpg/rulebooks/dungeonworld_like.py
  - src/gptrpg/rulebooks/moves.py
  - src/gptrpg/rulebooks/openquest.py
  - src/gptrpg/rulebooks/openquest_creatures.py
  - src/gptrpg/rulebooks/threat_clocks.py
  - src/gptrpg/agents/action_classifier.py
  - src/gptrpg/agents/context.py
  - src/gptrpg/agents/master_gm.py
  - src/gptrpg/agents/prompt_assembly.py
  - src/gptrpg/agents/situation_judge.py
  - src/gptrpg/cli/turn_flow.py
  - src/gptrpg/turn/judgments.py
  - src/gptrpg/web/characters_data.py
  - src/gptrpg/web/routes_actions.py
  - src/gptrpg/web/routes_characters.py
  - frontend/src/api/client.ts
  - frontend/src/api/types.ts
  - frontend/src/components/TurnCard.tsx
  - frontend/src/labels.ts
  - frontend/src/panes/ChatPane.tsx
  - frontend/src/panes/StatusPane.tsx
  - frontend/src/panes/StoryPane.tsx
  - frontend/src/session/groupTurns.ts
  - frontend/src/session/groupTurns.test.ts
  - LICENSES.md
findings:
  critical: 2
  warning: 5
  info: 0
  total: 7
status: issues_found
---

# Phase 11: Code Review Report

**Reviewed:** 2026-08-17T00:00:00Z
**Depth:** standard
**Files Reviewed:** 29
**Status:** issues_found

## Summary

Phase 11 widens `StatEntry`/`ResourceAxisDecl` to a six-form model, adds a third
rulebook (Cairn) as pure data, and splits `ProposalTier` into four values with a
new `POST /sessions/{id}/proceed` no-check narration path. The registration-time
validators (`validate_grade_bands`, `validate_move_stats`, `validate_trigger_mode`,
`validate_entity_axes`) and the `StatEntry._validate_form_payload` six-way
exhaustive switch are well-built and internally consistent. `_format_character_state`
(prompt_assembly.py) is a genuinely exhaustive, well-documented per-form renderer.

Two real gaps stood out under the "does confirm() guard something proceed()
doesn't" and "does the six-form widening reach every consumer" questions the
review was asked to focus on:

1. `POST /sessions/{id}/proceed` skips the ownership/ContractCheck that `confirm()`
   enforces via `ConfirmAction`, and nothing anywhere validates that the
   `declare_seq` it's given was ever actually classified as `no_check` in the
   first place. This is a genuine authorization/game-integrity gap, not just a
   style nit.
2. `_format_scene_entities` (prompt_assembly.py) was left behind when its sibling
   `_format_character_state` was made six-form-aware in this same phase — it still
   assumes every `StatEntry.current` is populated, which is false for three of
   the six forms. It's currently unreachable (scene entities are hardcoded to an
   all-numeric cast) but is a live landmine for the feature this phase built, and
   the same commit's own docstring names it as a "sibling formatter" that should
   have gotten the same treatment.

Five further issues are validator-completeness / silent-fallback gaps that are
lower-impact today but are exactly the class of defect the project's own
"no silent holes" rule exists to prevent.

## Critical Issues

### CR-01: `POST /sessions/{id}/proceed` has no ownership check and no verification that the declared action was actually classified as `no_check`

**File:** `src/gptrpg/web/routes_actions.py:789-1020` (also `src/gptrpg/session_actor/actor.py:458-527`)

**Issue:** `confirm()` enforces two guards before it will run the (expensive,
AI-backed) judgment + narration pipeline for a given `declare_seq`:

1. **Ownership** — `ConfirmAction` is submitted, and `_prepare_confirm`
   (`session_actor/actor.py:485-527`) checks
   `self.state.declare_owners.get(command.caused_by_seq)` against
   `command.character_id` and raises `CommandRejected("이 선언은 다른 캐릭터가
   낸 것이다")` if they don't match (TRUST-03).
2. **Idempotency for the expensive dice-roll step** — `AlreadyConfirmed`/
   `AlreadyResolved` short-circuit repeat confirms of the same declare.

`proceed()` never submits a `ConfirmAction` or `ResolveCheck` — by design
(结정 1, per its own docstring, "확인·판정 사건이 없다"). But that means the
ownership check in `_prepare_confirm` **never runs for this path at all**. The
only validation `proceed()`'s `declare_seq` goes through is
`_validate_caused_by` (`actor.py:458-468`), which merely checks
`0 <= caused_by_seq < next_seq(session_id)` — i.e. "some event with this seq
exists in this session," not "this is an `action_declared` event," and
certainly not "this event belongs to the calling character."

Worse: `ProposalTier`/`tier` (the classifier's `"no_check"` verdict) is **never
persisted anywhere** — `ActionDeclared` (`event_log/schema.py:105-115`) has no
`tier` field, and no other event captures it. So there is no server-side record
to check even if `proceed()` wanted to verify "was this declare_seq actually
classified as no_check?" The entire "does this action need a dice roll"
decision is client-trusted.

Combined, any occupied character (any of the four cookie-holders in the room)
can `POST /proceed` with:
- an arbitrary `declare_seq` that was never classified as `no_check` (or was
  never classified at all) — bypassing the dice-roll/check requirement for any
  action, including ones the classifier explicitly proposed a move for;
- a `declare_seq` belonging to a **different character's** declaration —
  triggering a full narration turn (4 AI calls: situation/entity/clock judges +
  master_gm) attributed via `caused_by_seq` to someone else's action, something
  `confirm()`'s TRUST-03 check exists specifically to prevent.

**Fix:** Before running the judgment/narration pipeline in `proceed()`, check
ownership the same way `_prepare_confirm` does — e.g. expose a read of
`actor.state.declare_owners` (or add a dedicated `SessionActor` query) and
reject with 403/400 if `declare_owners.get(body.declare_seq) != identity.character_id`.
Additionally, verify the referenced event is actually an `action_declared`
event (not just "some seq in range"). Longer-term, consider persisting the
classifier's tier decision against the declare event so `proceed()` can refuse
to run for a `declare_seq` that was never classified `no_check` — mirroring
`confirm()`'s reliance on real classifier output rather than a client-asserted
flag. Apply the identical fix to `cli/turn_flow.py`'s `_proceed_without_check`
if the CLI is ever exposed to untrusted callers (currently a local trust
boundary, per its own comments, so lower priority there).

### CR-02: `_format_scene_entities` was not updated for the six-form `StatEntry` model — it silently embeds Python `None` in the AI prompt for three of the six forms

**File:** `src/gptrpg/agents/prompt_assembly.py:186-193`

**Issue:**

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

This unconditionally reads `stat.current` for every `StatEntry` regardless of
`form`. Per `entities.py`'s `_validate_form_payload`, `current` is `None` for
`named_slots`, `tag_list`, and `none` forms (those forms are *required* to
leave `current` unset). For any entity carrying such a stat, this produces a
literal `"이름 None"` fragment (Python f-string of `None`), injected verbatim
into the **permanently cached** prompt block sent to `action_classifier`,
`master_gm` (`_narration_session_block_text`), `situation_judge`, and
`scene_entity_judge` — all four call this helper via `_session_block_text`,
`_narration_session_block_text`, or directly in `build_scene_entity_prompt`.

This directly contradicts the design this same phase built elsewhere:
`_format_character_state` (same file, same phase, commit `feat(11-07):
character-state string handles all six resource-axis forms`) was given an
explicit per-form switch specifically to prevent this — and that function's
own docstring literally names `_format_scene_entities` as the sibling
formatter whose `"(없음)"` placeholder convention it follows (`_format_moves`'s
docstring: `형제 포매터들(_format_scene_entities 등)의 "(없음)" 자리표시자 관례를
따른다`). The sibling was never actually brought in line.

It also bypasses the `none`-form treatment this phase carefully built
elsewhere: `_format_resource_treatment` exists specifically so a `form="none"`
axis is described by policy line rather than leaking a raw value into context
(D-08/D-09). `_format_scene_entities` has no such exclusion — a `none`-form
stat on a scene entity would show up as `"축이름 None"` regardless.

**Reachability today:** `TurnContext.scene_entities` is currently hardcoded to
`THREAT_CAST` (`turn/context.py:121`), whose entities only carry `numeric`
stats or no stats at all — so this is not triggered by any currently
registered data. But it is squarely in the blast radius of the feature this
phase shipped (Cairn's `named_slots` inventory, in particular), the very next
time any non-numeric-only entity becomes a scene entity (e.g. a future
Cairn/OpenQuest threat-clock cast, or if `THREAT_CAST` is ever built from
player/NPC data with richer stat forms). Per the "no silent holes" project
invariant, this should fail loudly or render a placeholder, not silently emit
`None` into a cached AI prompt.

**Fix:** Give `_format_scene_entities` the same per-form treatment as
`_format_character_state` (or better, factor the per-stat formatting logic out
into one shared helper both call, so the two can't drift again). At minimum,
skip `form == "none"` stats and render a form-appropriate string for
`named_slots`/`tag_list`/`usage_die`/`clock` instead of assuming `current` is
always populated.

## Warnings

### WR-01: Registration-time validators don't reject unrecognized `check_trigger_mode` / `none_kind` values — only recognized-value consistency is checked

**File:** `src/gptrpg/rules_core/rulebook.py:405-418` (`validate_trigger_mode`),
`src/gptrpg/agents/prompt_assembly.py:152-160` (`_format_resource_treatment`)

**Issue:** `CheckTriggerMode` and `NoneKind` are `Literal` type hints, which
Python does not enforce at runtime. Nothing rejects an out-of-set string value
at construction or registration time:

```python
def validate_trigger_mode(mode: CheckTriggerMode, move_count: int) -> None:
    if mode == "declared_list" and move_count == 0:
        raise InvalidTriggerMode(...)
    if mode in ("no_dice", "gm_discretion") and move_count > 0:
        raise InvalidTriggerMode(...)
```

If `mode` is any string other than the three known values (e.g. a typo like
`"declared"`), neither `if` fires and the rulebook registers successfully
regardless of its move-list length — silently defeating the exact purpose this
validator's own docstring states ("빈 목록은 미완성이 아니라 정상값이지만... 조용히
통과하지 않는다"). `Rulebook.__post_init__` doesn't check this field either
(it only checks `resource_axes` name uniqueness).

The same pattern exists for `none_kind`:

```python
if axis.none_kind == "discretionary":
    lines.append(...)
else:  # "absent"
    lines.append(...)
```

Any value other than exactly `"discretionary"` — including a typo, or a value
that was never validated as one of the two literal options at
`ResourceAxisDecl.__post_init__`/`StatEntry.__post_init__` (both only check
"is it `None`" / "is it required," never "is it one of the two allowed
strings") — silently renders as `"absent"` ("이 개념은 이 세계에 없다") instead of
`"discretionary"` ("규칙으로 세지 않지만 존재한다"). This is a real behavior
inversion fed straight into a cached AI prompt, with zero validation anywhere
catching the typo.

Contrast with `StatEntry._validate_form_payload`'s handling of `form`, which
does have an explicit `else: raise InvalidStatEntry(f"알 수 없는 form: {form!r}")`
catch-all — this is exactly the pattern `check_trigger_mode`/`none_kind` are
missing.

**Fix:** Add an explicit `else: raise` (or `if mode not in {...}: raise`) branch
to `validate_trigger_mode` for unrecognized modes, and add the same closed-set
check to `ResourceAxisDecl.__post_init__`/`StatEntry.__post_init__` for
`none_kind` (`if self.none_kind not in ("discretionary", "absent"): raise ...`
when it's not `None`).

### WR-02: `ConfirmRequest.rulebook_id`/`ProceedRequest.rulebook_id` are client-supplied and never checked against the target character's actual `Entity.rulebook_id`

**File:** `src/gptrpg/web/routes_actions.py:353-408, 773-826`;
`src/gptrpg/session_actor/actor.py:569-597` (`_prepare_resolve_check`)

**Issue:** `confirm()`/`proceed()` fetch `character = get_character(body.character_id)`
(which carries its own immutable `rulebook_id`), but then independently do
`rulebook = get_rulebook(body.rulebook_id)` using the **client-supplied**
`rulebook_id` from the request body — with no check that the two agree.
`_prepare_resolve_check` (session_actor/actor.py) does the same:
`get_rulebook(command.rulebook_id)` trusts the request field verbatim to pick
the resolution method (`2d6`/`d100_roll_under`/`d20_roll_under`) and grade
bands used to resolve the check.

A client can therefore resolve a `dungeonworld_like` character's move under
`openquest`'s (or vice versa) resolution mechanic, or fetch a mismatched
`resource_axes` list for the "none-axis treatment" prompt block, producing a
narration/resolution context that doesn't match the character actually being
played. This gap likely predates phase 11 (the field has existed since
`confirm()` first shipped), but phase 11 materially raises its stakes: before
this phase there were two rulebooks with somewhat comparable 2d6/d100
resolution; now there are three, including Cairn's d20-roll-under mechanic (no
resolver registered yet, so that specific combination fails loudly via
`CommandRejected`, but the dungeonworld_like/openquest cross-substitution is
live today).

**Fix:** Derive `rulebook_id` from `character.rulebook_id` server-side instead
of trusting the request body field, or explicitly validate
`body.rulebook_id == character.rulebook_id` and reject with 400 otherwise.

### WR-03: Registration-time entity/axis validation excludes player characters, but a sibling module's docstring asserts it doesn't

**File:** `src/gptrpg/rulebooks/__init__.py:47-56`;
`src/gptrpg/web/routes_characters.py:91-107`

**Issue:** `_REGISTERED_ENTITIES_FOR_AXIS_CHECK` (rulebooks/__init__.py)
deliberately excludes `web/characters_data.py`'s `PLAYER_CHARACTERS`
(explained correctly in its own comment: importing `web` from `rulebooks`
would invert the layering). Player-character axis conformance is instead
checked only by a pytest test (`tests/test_web_characters.py` /
`test_all_player_characters_match_their_rulebook_axes`), not at
import/registration time.

But `routes_characters.py`'s `_visible_stats` docstring states as fact:

> "(등록 시점의 `validate_entity_axes`가 이미 둘이 어긋나면 등록 자체를 거부하므로
> 정상 등록된 개체라면 두 신호는 항상 일치한다.)"

This is only true for the entities in `_REGISTERED_ENTITIES_FOR_AXIS_CHECK`
(scenario cast + creature constants) — it's false for the four player
characters, whose axis conformance is enforced by test suite discipline, not
by anything that runs when the app boots. `_visible_stats` itself is written
defensively (it checks both the entity's own `stat.form` and the rulebook's
declared axis form independently, "이 함수는 그 전제에 기대지 않고 독립적으로 둘 다
본다"), so the actual behavior is safe either way — but the comment overstates
what's structurally guaranteed, and a malformed player-character `StatEntry`
(form mismatch vs. its rulebook's declared axis) can ship to a running server
undetected if `pytest` isn't run as a deploy gate.

**Fix:** Either correct the `_visible_stats` docstring to scope its claim to
non-player entities, or move player-character axis validation into an
import-time call (e.g. a small `validate_player_characters()` invoked from
`web/app.py` startup, avoiding the `rulebooks -> web` layering inversion by
having `web` call `rules_core.validate_entity_axes` directly rather than going
through `rulebooks`).

### WR-04: `StatusPane.tsx`'s `StatRows` silently drops any stat with an unrecognized `form`

**File:** `frontend/src/panes/StatusPane.tsx:78-144`

**Issue:** The per-form `if` chain in `StatRows` ends with:

```tsx
// stat.form === "none": 서버가 이 축을 응답에서 이미 뺐으므로
// 화면은 이 갈래에 도달하지 않는다...
return null;
```

This fallback is documented as being for `form === "none"` only (which the
server already filters out via `_visible_stats`, so it's normally dead code).
But because it's an unconditional final `return null` rather than a check for
`stat.form === "none"` specifically, it also silently swallows any *other*
unrecognized `form` value with zero visual indication — no console warning, no
placeholder text, nothing. Compare with the Python-side sibling
`_format_character_state`, which was explicitly built in this same phase to
render `"(알 수 없는 형태 {form!r})"` for exactly this situation rather than
disappearing the stat.

Given `StatEntryView.form` is typed as plain `str` on the wire (not a closed
union at the wire boundary — `frontend/src/api/types.ts`'s `StatEntry.form`
union is a client-side assumption, not something the server enforces beyond
the Python `Literal`), a future server-added seventh form (or any
server/frontend version skew) would just make that stat vanish from the
character sheet with no error surfaced anywhere.

**Fix:** Match `_format_character_state`'s pattern — render a visible
"(알 수 없는 형태)" fallback for any `stat.form` that isn't one of the five
handled cases, rather than an unconditional `return null`.

### WR-05: `StatEntry`/`ResourceAxisDecl` form-payload validation doesn't restrict `depleted_effect_ref` for `named_slots`/`tag_list`/`usage_die` forms

**File:** `src/gptrpg/rules_core/entities.py:112-146`

**Issue:** `_validate_form_payload`'s `named_slots`, `tag_list`, and
`usage_die` branches each explicitly forbid the other cross-form fields
(`current`/`max`/`slot_values`/`tags`/`none_kind` as appropriate) but none of
them mention `depleted_effect_ref` — so a `StatEntry` with, say,
`form="named_slots"` and a populated `depleted_effect_ref` passes validation
silently, even though "depletion" isn't a concept `named_slots`/`tag_list`
axes have (only `numeric`/`clock`/`usage_die` naturally deplete). This is
lower-severity than the other findings because no current consumer reads
`depleted_effect_ref` (confirmed via repo-wide grep — it's write-only,
reserved for M1), so it can't currently break anything downstream, but it's an
inconsistency in an otherwise carefully closed six-way validation matrix and
will silently accept malformed data once M1 starts reading this field.

**Fix:** Add `self.depleted_effect_ref is not None` to the forbidden-field
checks for `named_slots` and `tag_list` (and decide deliberately, one way or
the other, whether `usage_die` should allow it — currently unspecified either
way).

---

_Reviewed: 2026-08-17T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
