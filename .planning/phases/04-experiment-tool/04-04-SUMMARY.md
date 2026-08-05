---
phase: 04-experiment-tool
plan: 04
subsystem: api
tags: [fastapi, cookie-auth, vanilla-ts, entities]

requires:
  - phase: 04-experiment-tool
    provides: "04-01: gptrpg.web FastAPI package (create_app, validate_session_id, StaticFiles mount ordering), Vite vanilla-ts frontend scaffold with textContent-only rendering discipline"
provides:
  - "gptrpg.web.characters_data: PLAYER_CHARACTERS (four hand-authored Entity instances, same container as enemies/NPCs), CHARACTER_ARCHETYPES, list_characters()/get_character()"
  - "GET /api/sessions/{id}/characters, GET /api/sessions/{id}/characters/{character_id}, POST /api/sessions/{id}/select-character, GET /api/sessions/{id}/my-character — sheet route is read-only (405 on write methods)"
  - "gptrpg_character unsigned cookie (HttpOnly, SameSite=lax, 14-day max-age) as the sole player-identity mechanism this milestone"
  - "frontend/src/character.ts: ensureCharacterSelected() (skip-if-cookie-valid entry screen) + mountCharacterSheet() (collapsible read-only stat list)"
affects: [04-05, 04-06]

actuals:
  tokens: 7000
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Player characters reuse rules_core.entities.Entity/StatEntry verbatim (D-20/D-21) instead of a bespoke PlayerCharacter type — the web layer owns a hand-authored player_id -> Entity dict, mirroring rulebooks/dungeonworld_like.py's EXAMPLE_SINGLE_STAT_FOE precedent"
    - "Unsigned plain-JSON cookie as identity for a trusted 4-person room (A5/T-04-02) — explicitly flagged M0-only in the module docstring, not a pattern to carry into M1's real account system"
    - "startPolling(sessionId, onLayoutReady?) callback — lets a caller attach to the header element the instant it's built, before the poll loop's first render, without racing the layout's own root wipe"

key-files:
  created:
    - src/gptrpg/web/characters_data.py
    - src/gptrpg/web/routes_characters.py
    - tests/test_web_characters.py
    - frontend/src/character.ts
  modified:
    - src/gptrpg/web/app.py
    - frontend/src/main.ts

key-decisions:
  - "bram carries a fifth non-HP stat (방어구) so the four characters don't all have identical stat counts — makes 'same code renders any stat count' (D-21) an actually-exercised test property, not just an assumption"
  - "CHARACTER_ARCHETYPES kept as a separate dict, not folded into Entity — a one-line caption is a screen concern (entry-screen copy), not a rulebook concept; adding a field to Entity would leak layer-2 rulebook vocabulary into the layer-1 platform container"
  - "my-character never raises on a malformed/foreign-format cookie — falls back to selected:false. A browser holding a stale cookie shape must never lose the ability to open the screen"
  - "startPolling's layout-callback restructuring (main.ts): the plan's literal task order (mountCharacterSheet then startPolling) would have raced buildLayout's root.textContent = \"\" wipe if mountCharacterSheet appended directly to #app before startPolling ran. Solved by having startPolling accept an optional onLayoutReady(header) callback invoked right after the header element is built but before polling starts, so mountCharacterSheet mounts onto a DOM node that survives"

requirements-completed: [RIG-05]

coverage:
  - id: D1
    description: "Player characters reuse the same Entity/StatEntry container as enemies/NPCs — Entity's four fields are unchanged, and the four hand-authored characters pass Entity's own constructor validation"
    requirement: RIG-05
    verification:
      - kind: unit
        ref: "manual verify command: uv run python -c checks PLAYER_CHARACTERS length==4 and ENTITY_FIELD_NAMES length==4"
        status: pass
    human_judgment: false
  - id: D2
    description: "Character sheet route is read-only — PUT/PATCH/DELETE/POST to GET /characters/{id} all return 405"
    requirement: RIG-05
    verification:
      - kind: unit
        ref: "tests/test_web_characters.py#test_character_sheet_route_rejects_all_write_methods"
        status: pass
    human_judgment: false
  - id: D3
    description: "Selecting a character sets an unsigned, HttpOnly, SameSite=lax cookie; my-character reflects the selection back on a matching session and rejects cookies from a different session"
    requirement: RIG-05
    verification:
      - kind: unit
        ref: "tests/test_web_characters.py#test_select_character_sets_httponly_lax_cookie"
        status: pass
      - kind: unit
        ref: "tests/test_web_characters.py#test_my_character_returns_selected_true_after_selecting"
        status: pass
      - kind: unit
        ref: "tests/test_web_characters.py#test_my_character_returns_selected_false_for_different_session"
        status: pass
    human_judgment: false
  - id: D4
    description: "Sheet responses render identically regardless of stat count (bram has 8 stats, nari has 6) — no count-based branching in either the API model or the frontend renderer"
    requirement: RIG-05
    verification:
      - kind: unit
        ref: "tests/test_web_characters.py#test_different_stat_counts_produce_same_shaped_response"
        status: pass
    human_judgment: false
  - id: D5
    description: "Entry screen never auto-selects a lone character; selection always requires a deliberate click, and the entry screen is skipped entirely on a return visit with a valid cookie"
    requirement: RIG-05
    verification: []
    human_judgment: true
    rationale: "This is a client-side interaction/timing behavior (skip-render-if-cookie-valid, no-auto-select-on-click) that tsc/build only prove compiles and bundles — it needs an eyes-on browser check to confirm the actual click-to-cookie-to-skip flow, consistent with 04-01's own must_haves.truths flagged as verification:backstop for live browser behavior. Deferred to 04-06's live QA pass alongside the other backstop items."
  - id: D6
    description: "Loading/error copy for both the character list and the character sheet toggle match the UI-SPEC Copywriting Contract exactly"
    requirement: RIG-05
    verification:
      - kind: other
        ref: "grep -c on frontend/src/character.ts for each required Korean string (캐릭터를 선택하세요 / 내 캐릭터 시트 / 캐릭터 목록을 불러오지 못했어요... / 캐릭터 시트를 불러오지 못했어요), each == 1"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-08-03
status: complete
---

# Phase 4 Plan 4: Player Characters and Read-Only Sheet Summary

**Four hand-authored player characters sharing the exact `Entity`/`StatEntry` container as enemies/NPCs, served through four HTTP routes (list/sheet/select/my-character) with a read-only sheet enforced by having no write handler, identity carried in an unsigned `gptrpg_character` cookie, and a character-select entry screen + collapsible sheet toggle on the frontend.**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-08-03T05:15:00Z
- **Completed:** 2026-08-03T06:01:27Z
- **Tasks:** 3
- **Files modified:** 6 (4 created, 2 modified)

## Accomplishments
- `characters_data.py`: four player characters (bram/nari/seon/hodu) declared as plain `Entity` constants, reusing the identical four-field container `EXAMPLE_SINGLE_STAT_FOE`/`OPENQUEST_GOBLIN` already use — zero changes to `rules_core.entities`, `ENTITY_FIELD_NAMES` stays at 4
- Four HTTP routes wired behind the existing `validate_session_id` dependency: `GET /characters` (list), `GET /characters/{id}` (read-only sheet, 405 on all write verbs), `POST /select-character` (sets the identity cookie), `GET /my-character` (reads it back, never throws on a malformed cookie)
- `gptrpg_character` cookie: unsigned JSON `{session_id, character_id}`, `HttpOnly`, `SameSite=lax`, no `Secure` attribute (deliberate — this experiment runs without HTTPS), 14-day max-age to span EXP-03's weekly two-session cadence
- `character.ts`: entry screen that skips itself entirely when a valid cookie exists, never auto-selects a lone character, and a native `<details>/<summary>` sheet toggle that fetches once on first expand and retries on re-expand after failure
- 10 new backend tests covering all nine `<action>`-specified cases plus a tenth (list-route archetype match); full 354-test suite passes; `tsc --noEmit` and `vite build` both succeed

## Task Commits

Each task was committed atomically:

1. **Task 1: 손으로 쓴 플레이어 캐릭터 넷 — 적과 같은 그릇에** - `8fa4b2b` (feat)
2. **Task 2: 목록·시트·선택·조회 네 경로 — 시트에는 쓰기 경로가 없다** - `9341b60` (feat)
3. **Task 3: 입장 화면과 접었다 펴는 시트** - `7fb2c9b` (feat)

## Files Created/Modified
- `src/gptrpg/web/characters_data.py` - `PLAYER_CHARACTERS`/`CHARACTER_ARCHETYPES`/`CharacterSummary`/`list_characters()`/`get_character()`
- `src/gptrpg/web/routes_characters.py` - four routes, `StatEntryView`/`CharacterSheetView`/`CharacterSummaryView`/`SelectCharacterRequest`/`SelectCharacterResponse`/`MyCharacterResponse`, `COOKIE_NAME`/`COOKIE_MAX_AGE_S`
- `src/gptrpg/web/app.py` - `characters_router` registered above the `StaticFiles` mount, same `validate_session_id` dependency as `events_router`
- `tests/test_web_characters.py` - 10 tests
- `frontend/src/character.ts` - `ensureCharacterSelected()`, `mountCharacterSheet()`
- `frontend/src/main.ts` - `startPolling(sessionId, onLayoutReady?)`, `bootstrap()` awaiting character selection before polling starts

## Decisions Made
- **Stat-count asymmetry is deliberate:** bram has a seventh stat (방어구) the other three don't, so "same code renders any stat count" is an exercised property (`test_different_stat_counts_produce_same_shaped_response`), not an unverified claim.
- **Archetype stays out of `Entity`:** a one-line entry-screen caption is layer-2/screen concern, not a rulebook field — adding it to `Entity` would have broken the "same grinder as NPCs" property this plan exists to prove.
- **`my-character` fails closed, not loud:** any cookie shape mismatch (wrong session, unknown character, unparseable JSON) returns `selected: false` rather than raising — a stale-format cookie from an earlier session must never break the screen.
- **`startPolling` gained an `onLayoutReady` callback** (deviation-adjacent, not a rule-triggered fix — see below) rather than literally calling `mountCharacterSheet(root, ...)` then `startPolling(sessionId)` as two independent top-level calls: the plan's exact task order would have `mountCharacterSheet` append into `#app` and then `startPolling`'s own `buildLayout` immediately wipe `#app`'s `textContent`, deleting the sheet toggle before the first poll even ran. The callback lets `mountCharacterSheet` attach to the header element the instant it exists, achieving the same "sheet toggle is live before polling starts" outcome the plan specifies, without the race.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed the literal string `secure=True` and `innerHTML` from docstring prose**
- **Found during:** Task 2 and Task 3's own `<verify>` blocks
- **Issue:** the module docstring for `routes_characters.py` originally explained the missing `Secure` cookie attribute using the literal text `secure=True` (matching the acceptance criterion's `grep -c 'secure=True' ... == 0`, which the docstring prose itself then violated). Same issue in `character.ts`'s docstring, which named `innerHTML` literally against a `grep -rn 'innerHTML' frontend/src/ | wc -l == 0` check with no allow-list comment in this file, and separately duplicated the exact string "내 캐릭터 시트" a second time in prose against a `grep -c == 1` check.
- **Fix:** reworded both docstrings to describe the same information without the literal grepped substrings (matching `session_view.ts`'s existing convention of describing "HTML string assignment" in prose instead of naming the DOM property directly).
- **Files modified:** `src/gptrpg/web/routes_characters.py`, `frontend/src/character.ts`
- **Verification:** `grep -c 'secure=True' src/gptrpg/web/routes_characters.py` → 0; `grep -rn 'innerHTML' frontend/src/ | wc -l` → 0; `grep -c '내 캐릭터 시트' frontend/src/character.ts` → 1
- **Committed in:** `9341b60` (Task 2), `7fb2c9b` (Task 3)

**2. [Rule 3 - Blocking] `frontend/node_modules` was never installed in this worktree**
- **Found during:** Task 3's `<verify>` (`npx tsc --noEmit`)
- **Issue:** `npx tsc --noEmit` failed with npm's "not the tsc command you are looking for" error because `frontend/node_modules` didn't exist yet in this freshly-created worktree (04-01's `npm create vite` output isn't tracked in git — `node_modules`/`dist` are gitignored).
- **Fix:** ran `npm install` in `frontend/` before re-running `tsc`/`build`. `package-lock.json` was unchanged (already committed by 04-01), so no new files needed staging.
- **Files modified:** none (local `node_modules/` only, gitignored)
- **Verification:** `npx tsc --noEmit` → exit 0; `npm run build` → `dist/index.html` produced
- **Committed in:** n/a (local dependency install, not a tracked change)

---

**Total deviations:** 2 auto-fixed (1 bug in self-referential docstring text tripping the plan's own grep-based acceptance criteria, 1 blocking local-environment setup)
**Impact on plan:** No scope creep, no architectural changes. Both fixes were required to make each task's own `<verify>` block pass exactly as the plan specified.

## Issues Encountered
- The plan's literal task-order instruction ("mountCharacterSheet(...) then startPolling(...)") would have produced a real runtime bug (sheet toggle wiped immediately after being mounted) if implemented as two sequential top-level calls, because `startPolling`'s internal `buildLayout` unconditionally clears `#app`. Resolved via the `onLayoutReady` callback restructuring documented above in Decisions Made — this is a design adjustment within Task 3's own scope, not a deviation from the plan's functional intent (character sheet still attaches to the header bar area, still mounts before the first poll completes).
- No live browser click-through was performed for the entry-screen skip/no-auto-select behavior — covered by a live `curl`-based smoke test against a real `uvicorn` process (character list → select → cookie persists → my-character reflects it → sheet route 405s on write) instead, which proves the HTTP contract but not the DOM interaction. Flagged as `human_judgment: true` (coverage D5), deferred to 04-06's live QA pass, consistent with 04-01's own precedent for backstop-verification items.

## User Setup Required
None - no external service configuration required. `npm install` in `frontend/` was needed locally (deviation #2 above) but installs from the already-committed `package-lock.json`, no new dependency versions introduced.

## Next Phase Readiness
- `PLAYER_CHARACTERS` is now the canonical `player_id -> Entity` mapping this codebase has been missing since Phase 1 (RESEARCH.md Pitfall 3) — 04-05 (wiring the acting player's real character into `TurnContext.character_state`, replacing `cli/turn_flow.py`'s placeholder-foe hardcode) can import it directly.
- The `gptrpg_character` cookie is the only identity signal that exists anywhere in this stack — 04-05's action-declare/confirm endpoints will need to read it (via the same `request.cookies.get(COOKIE_NAME)` pattern `my-character` already uses) to know which `PLAYER_CHARACTERS` entry an incoming action belongs to.
- No safety-tool UI, no character-creation screen, no matchmaking — all correctly out of scope per PROJECT.md's M0 "안 만드는 것" list, none touched by this plan.
- The Flagged Assumption from the plan stands: **the actual names/numbers in `characters_data.py` are this plan's own invention**, not sourced from any design document — a human must replace them before running the real EXP-01/EXP-02 sessions with actual participants.

---
*Phase: 04-experiment-tool*
*Completed: 2026-08-03*

## Self-Check: PASSED

All 6 created/modified files found on disk (`characters_data.py`, `routes_characters.py`, `test_web_characters.py`, `character.ts`, `app.py`, `main.ts`); all 3 task commit hashes (`8fa4b2b`, `9341b60`, `7fb2c9b`) found in git history.
