---
phase: 04-experiment-tool
reviewed: 2026-08-03T00:00:00Z
depth: standard
files_reviewed: 26
files_reviewed_list:
  - .importlinter
  - README.md
  - frontend/.gitignore
  - frontend/index.html
  - frontend/package-lock.json
  - frontend/package.json
  - frontend/public/favicon.svg
  - frontend/src/action.ts
  - frontend/src/character.ts
  - frontend/src/main.ts
  - frontend/src/session_view.ts
  - frontend/src/style.css
  - frontend/tsconfig.json
  - pyproject.toml
  - src/gptrpg/cli/main.py
  - src/gptrpg/cli/turn_flow.py
  - src/gptrpg/rules_core/reducer.py
  - src/gptrpg/session_actor/actor.py
  - src/gptrpg/session_actor/report.py
  - src/gptrpg/turn/__init__.py
  - src/gptrpg/turn/context.py
  - src/gptrpg/web/__init__.py
  - src/gptrpg/web/app.py
  - src/gptrpg/web/characters_data.py
  - src/gptrpg/web/routes_actions.py
  - src/gptrpg/web/routes_characters.py
  - src/gptrpg/web/routes_events.py
  - tests/conftest.py
  - tests/test_reducer_fails_since_clock.py
  - tests/test_report.py
  - tests/test_session_actor_auto_advance.py
  - tests/test_web_actions.py
  - tests/test_web_characters.py
  - tests/test_web_events.py
  - uv.lock
findings:
  critical: 1
  warning: 5
  info: 1
  total: 7
status: issues_found
---

# Phase 04: Code Review Report

**Reviewed:** 2026-08-03T00:00:00Z
**Depth:** standard
**Files Reviewed:** 26 (source); `uv.lock`/`frontend/package-lock.json` spot-checked for secrets only
**Status:** issues_found (CR-01 fixed post-review — see Resolution note below)

## Resolution

**CR-01 fixed** in `62f1093` (`fix(04): validate confirm request before committing ConfirmAction event`): moved `character_id`/`rulebook_id`/`modifiers` validation ahead of the `ConfirmAction` submit in `confirm()`, so a malformed confirm request now returns 400 with no event written. Added a regression test (`test_confirm_unknown_character_id_leaves_no_orphaned_confirm_event`). Full suite (388 tests) and `lint-imports` (3 kept, 0 broken) pass.

The five WARNING items and one INFO item below were not addressed — they are quality/robustness improvements, not data-integrity blockers, and are left for a future gap-closure or polish pass.

## Summary

Reviewed the M0 experiment tool's web layer (FastAPI polling/actions/characters routes), the shared `turn` context layer, the session actor/reducer/report modules, the CLI, and the hand-rolled vanilla-TS frontend. The codebase is generally careful — extensive docstrings tie code back to explicit decisions (D-xx/T-xx/MEAS-xx), the frontend consistently uses `textContent` (no innerHTML/XSS surface), session-id path segments are validated against directory traversal in two independent places, and the "confirm rejected" data-integrity story is well thought out.

However, I found one genuine data-integrity BLOCKER: the `POST /actions/confirm` handler commits the `ConfirmAction` event (`player_confirmed=True`) to the permanent event log *before* validating `character_id`, `rulebook_id`, and `modifiers`, and before attempting `ResolveCheck`. Any of those later validations failing produces an HTTP 4xx response — which a normal API client would read as "nothing happened" — while an orphaned, permanently unexplained `action_confirmed(player_confirmed=True)` event with no matching `check_resolved` remains in the log. I reproduced this concretely (see CR-01) against the live `create_app`. This directly undermines the project's stated goal of a complete, unfiltered event log as ground truth for later hypothesis testing (see `session_actor/report.py`'s own docstring on why nothing is filtered).

The remaining issues are quality/robustness warnings: a CLI subcommand that cannot represent a system suggestion with a different stat than the confirmed one, duplicated session-id validation regex, missing bounds validation on numeric/list fields in `ConfirmRequest`, a frontend UX gap that lets a player submit a new action while a confirm/narration cycle is still in flight, and an unguarded tuple-unpack in the CLI turn flow.

## Critical Issues

### CR-01: `/actions/confirm` commits a `ConfirmAction` event before validating inputs that gate the rest of the turn, leaving orphaned "confirmed" events in the permanent log when validation later fails

**File:** `src/gptrpg/web/routes_actions.py:241-278`

**Issue:** In `confirm()`, the handler submits `ConfirmAction(..., player_confirmed=body.confirmed, ...)` and gets back `confirm_seq` (lines 241-253) *before* it validates `body.modifiers` (line 267), looks up `body.character_id` (line 271), or looks up `body.rulebook_id` (line 276). If any of those three checks fails — e.g. an unknown `character_id`, an unknown `rulebook_id`, or a malformed modifier string — the handler raises an `HTTPException(400, ...)` and returns, but the `action_confirmed` event with `player_confirmed=True` has *already been permanently appended to the event log*, with no corresponding `check_resolved` event and no failure event of any kind recorded. The same is true for a `CommandRejected` raised later inside `ResolveCheck` (line 282-294, e.g. `NoMatchingGradeBand`/`UnsupportedModifier`/unknown resolution method) — the confirm event is already committed by that point.

A client that receives an HTTP 4xx from a `POST` reasonably assumes no server-side state changed. Here it did: the append-only event log — the single source of truth this entire tool exists to produce for Phase 5/6 hypothesis testing (per `session_actor/report.py`'s docstring: *"이 숫자는 Phase 6의 가설 판정에 그대로 들어가는 입력값이므로, 결과가 유리해 보이게 만드는 어떤 필터링도 넣지 않는다"*) — now contains an unexplained "confirmed" action that never resolved. Nothing else in the system records *why* it didn't resolve (contrast with the narration-failure path, which always submits a `RecordAiCall` even on failure specifically so the failure is visible in the log).

This is reachable by any client that talks to the public, unauthenticated API directly (not just through the bundled frontend, which happens to always send valid values today). I reproduced it directly against `create_app`:

```
declare: 200 {'declare_seq': 0, 'tier': 'single', 'candidates': [...]}
confirm: 400 {"detail":"그런 캐릭터가 없다"}   # character_id="no_such_character"
0 action_declared None
1 ai_invoked None
2 action_confirmed True   # <-- permanently recorded, player_confirmed=True, no check_resolved ever follows
```

**Fix:** Validate everything the rest of the turn depends on (`modifiers`, `character_id`, `rulebook_id`) *before* submitting `ConfirmAction`, so a 400 truly means nothing was recorded — mirroring the ordering already used for `declare()`'s classification step (which is validated after commit, but is explicitly documented as intentional for MEAS-04 raw-text fidelity; `ConfirmAction` has no equivalent rationale for post-commit validation of these three fields):

```python
# before: confirm_seq = await actor.submit(ConfirmAction(...))
try:
    modifiers = tuple(_parse_modifier(raw) for raw in body.modifiers)
except ValueError as exc:
    raise HTTPException(status_code=400, detail=str(exc)) from exc

character = get_character(body.character_id)
if character is None:
    raise HTTPException(status_code=400, detail="그런 캐릭터가 없다")

if body.confirmed:
    try:
        rulebook = get_rulebook(body.rulebook_id)
    except UnknownRulebook as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

try:
    confirm_seq = await actor.submit(ConfirmAction(...))
except CommandRejected as exc:
    raise HTTPException(status_code=400, detail=str(exc)) from exc
except SequenceConflict as exc:
    raise HTTPException(status_code=409, detail=str(exc)) from exc
```

If some validation must stay downstream of the commit (e.g. `ResolveCheck`'s own `CommandRejected`), at minimum submit a compensating event (or a dedicated failure event type) so the orphaned confirm is explainable from the log alone, the same way narration failures are always paired with a `RecordAiCall`.

## Warnings

### WR-01: `gptrpg submit confirm` cannot record a system suggestion whose stat differs from the confirmed stat

**File:** `src/gptrpg/cli/main.py:61-69` (command building), `319-327` (argparse)

**Issue:** The `confirm` subcommand only exposes `--stat` (the chosen stat) and `--suggestion` (the suggested move) — there is no `--suggestion-stat`. `_build_command` hardcodes `system_suggestion={"move": args.suggestion, "stat": args.stat}`, i.e. the recorded "system suggested this stat" is always forced equal to whatever stat the player is confirming. Contrast with `cli/turn_flow.py`, which correctly keeps `suggestion` and `picked` as independent objects (`suggestion = candidates[0]`, `picked = chosen or suggestion`), so `system_suggestion.stat` can legitimately differ from `move`'s stat when a `several`-tier candidate with a different stat is chosen. Anyone using the low-level `submit confirm` subcommand directly (e.g. scripting/replay tooling, or manually correcting a recorded session) cannot represent that scenario faithfully — the resulting `action_confirmed` event will misreport what the system actually suggested.

**Fix:** Add a `--suggestion-stat` argument (default to `--stat`'s value only if explicitly desired) and thread it through:

```python
confirm_parser.add_argument("--suggestion-stat", required=True)
...
system_suggestion={"move": args.suggestion, "stat": args.suggestion_stat},
```

### WR-02: `SAFE_SESSION_ID` regex duplicated in two modules with no shared source of truth

**File:** `src/gptrpg/web/app.py:36`, `src/gptrpg/session_actor/report.py:33`

**Issue:** Both `web/app.py` and `session_actor/report.py` independently define `SAFE_SESSION_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")`. Both docstrings explain *why* the check exists (path-traversal prevention for the report file name) but neither references the other. If one is ever tightened or loosened (e.g. to allow a new character), the other can silently drift, re-opening the exact path-traversal risk both comments warn about.

**Fix:** Move the pattern to one shared location (e.g. `session_actor/report.py`, since that's the actual write site per its own docstring) and import it from `web/app.py`, or extract it to a small shared constants module both layers can depend on without violating the `.importlinter` layering contract.

### WR-03: `ConfirmRequest.target` and `.modifiers` accept unbounded/unvalidated values from an untrusted HTTP body

**File:** `src/gptrpg/web/routes_actions.py:203-214`

**Issue:** Every other user-controlled string field on `ConfirmRequest` (`player_id`, `move`, `stat`, `suggestion_move`, `suggestion_stat`, `character_id`) is constrained with `Field(min_length=1, max_length=MAX_ID_LEN)`. `target: int = DEFAULT_TARGET` has no range constraint at all, and `modifiers: list[str] = Field(default_factory=list)` has neither a max item count nor a max string length per item. A crafted request can submit an arbitrarily large/negative `target` (feeding directly into the grading math) or an arbitrarily long list of modifier strings, each independently parsed by `_parse_modifier` with its own unbounded `int(raw_value)`.

**Fix:** Add explicit bounds, matching the care already given to the string fields, e.g. `target: int = Field(default=DEFAULT_TARGET, ge=1, le=100)` and `modifiers: list[str] = Field(default_factory=list, max_length=20)`.

### WR-04: Frontend submit control stays enabled while a confirm/narration round-trip is in flight, allowing a new action to be declared mid-turn

**File:** `frontend/src/action.ts:227-284` (`handleConfirm`)

**Issue:** `handleSubmit()` calls `setSubmitBusy(true/false, ...)` around the `declare` request, but `handleConfirm()` never calls `setSubmitBusy` at all — the text input and submit button remain fully enabled for the entire confirm → resolve → narrate round trip (which, per the module's own comments, can take up to ~15s). A player can type and submit a brand-new action while their previous action's confirm/narration is still processing. The session actor's single-consumer queue keeps the *event log* consistent regardless, but the UI can end up interleaving the "AI가 생각하는 중…" notice from the first turn with a fresh proposal card from the second, which is confusing given the module's own stated goal of a single, unambiguous "confirm button is the only path to a judgment" flow (see file header comment).

**Fix:** Call `setSubmitBusy(true, ...)` at the start of `handleConfirm` and clear it in the same places the function already handles success/error, mirroring `handleSubmit`'s pattern.

### WR-05: Unguarded tuple-unpack assumes classifier invariant instead of failing gracefully

**File:** `src/gptrpg/cli/turn_flow.py:233`

**Issue:** `if tier == "single": (candidate,) = proposal.candidates` assumes exactly one candidate whenever `tier == "single"`. Every other place in this file that depends on classifier output funnels failures through `CommandRejected`/friendly stderr messages (see the `except` clauses on `_cmd_turn`). If the classifier ever returns a `single` tier with zero or multiple candidates (a contract violation in `agents.action_classifier`, not reviewed here), this line raises a raw, unhandled `ValueError: not enough values to unpack`/`too many values to unpack`, breaking the "CLI doesn't die with a traceback" discipline the surrounding code otherwise follows carefully (e.g. `_last_result_or_failure_envelope`'s explicit defense against provider contract violations).

**Fix:** Guard defensively, e.g. `if tier == "single" and len(proposal.candidates) == 1:` with a clear error message in the `else` branch, consistent with how the rest of the module treats provider/classifier contract violations as recoverable rather than fatal.

## Info

### IN-01: Docstring understates what a stolen/guessed `character_id` actually allows

**File:** `src/gptrpg/web/routes_characters.py:16-24`

**Issue:** The module docstring states the trust model's worst case is *"이 쿠키로 할 수 있는 최악의 일은 남의 읽기 전용 시트를 보는 것뿐이다"* (worst case: viewing someone else's read-only sheet). In practice, `POST /actions/declare` and `POST /actions/confirm` (`routes_actions.py`) take `character_id` directly from the client-supplied JSON body, not from the cookie, and never cross-check it against the caller's selected character. So any of the four link-holders can also *act* as any other character (submit declares/confirms with `character_id` set to someone else's), not just view their sheet. Given the explicitly documented M0 trust model (four people in one room sharing one link), this is very likely an acceptable, even irrelevant, risk — but the comment's stated "worst case" is inaccurate and could mislead a future reader (e.g. when this code is reused for M1, which the same docstring explicitly warns against doing without revisiting the trust model).

**Fix:** Update the docstring to note that `character_id` is caller-supplied per-request and not bound to the selection cookie, so the actual worst case within the M0 room-trust model is "acting as any of the four characters," not just reading their sheets.

---

_Reviewed: 2026-08-03T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
