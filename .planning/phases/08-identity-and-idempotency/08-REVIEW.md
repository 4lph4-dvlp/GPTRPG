---
phase: 08-identity-and-idempotency
reviewed: 2026-08-06T00:00:00Z
depth: standard
files_reviewed: 24
files_reviewed_list:
  - frontend/src/api/types.ts
  - frontend/src/labels.ts
  - frontend/src/panes/ChatPane.tsx
  - src/gptrpg/cli/main.py
  - src/gptrpg/cli/turn_flow.py
  - src/gptrpg/event_log/schema.py
  - src/gptrpg/rules_core/reducer.py
  - src/gptrpg/session_actor/actor.py
  - src/gptrpg/web/app.py
  - src/gptrpg/web/cookie_auth.py
  - src/gptrpg/web/routes_actions.py
  - src/gptrpg/web/routes_characters.py
  - tests/conftest.py
  - tests/test_event_log.py
  - tests/test_identity_tracer.py
  - tests/test_imagery.py
  - tests/test_measurement.py
  - tests/test_prompt_assembly_scenario.py
  - tests/test_report.py
  - tests/test_reverse_verification.py
  - tests/test_session_actor.py
  - tests/test_session_actor_auto_advance.py
  - tests/test_tracer_d100.py
  - tests/test_web_actions.py
  - tests/test_web_characters.py
  - tests/test_web_events.py
findings:
  critical: 0
  warning: 4
  info: 1
  total: 5
status: issues_found
---

# Phase 8: Code Review Report

**Reviewed:** 2026-08-06T00:00:00Z
**Depth:** standard
**Files Reviewed:** 24 (of 26 listed — `test_web_events.py` had no Phase 8 code paths beyond a shared fixture reference already covered, `test_measurement.py`/`test_report.py`/`test_reverse_verification.py`/`test_tracer_d100.py`/`test_prompt_assembly_scenario.py`/`test_session_actor_auto_advance.py`/`test_imagery.py` were spot-checked via grep for Phase 8 identity/occupancy surface area — none contained additional Phase 8 production-code logic beyond the fixture updates already reviewed in `conftest.py`)
**Status:** issues_found

## Summary

This phase adds HMAC-signed browser identity cookies, character occupancy
enforcement, confirm-idempotency short-circuiting, and narration-failure
recovery (502→200). The core cryptographic design is sound: HMAC-SHA256
with `hmac.compare_digest`, `secrets`-backed random IDs, no plaintext JSON
cookie, and secrets are never included in log/response text (verified by the
project's own `QUAL-05` tests, which pass on inspection). The occupancy and
idempotency state machines in `session_actor/actor.py` are carefully
reasoned through (TOCTOU windows for confirm↔resolve races are closed
correctly, concurrent occupy/confirm races are serialized correctly through
the single-consumer queue).

The issues found here are narrower: one place where the module's own
"single verification path" invariant is violated by a duplicate
implementation, one place where the confirm-idempotency short-circuit can
report an incorrect `confirmed` value to the caller in a two-tab race, and
a frontend error-handling gap on the reject path. None of these corrupt the
persisted event log (the source of truth stays correct in all three cases),
so none rise to data-loss/security severity, but they are the kind of bug
that quietly disagrees with the code's own explicit doc comments about
what invariants it upholds.

## Warnings

### WR-01: `my_character()` duplicates `read_identity()` instead of calling it, contradicting the module's own "single verification path" claim

**File:** `src/gptrpg/web/routes_characters.py:228-245`
**Issue:** `cookie_auth.py`'s module docstring states explicitly:

> "이 함수가 이 프로젝트의 유일한 신원 검증 경로다(`routes_characters.my_character`와
> `routes_actions.declare`/`confirm`이 전부 이 함수를 거친다) — 검증 경로가
> 두 벌이면 한쪽만 고쳐질 수 있다."

("This function is the project's one and only identity-verification path
— `my_character` and `declare`/`confirm` all go through it. Two
verification paths means one can be fixed without the other.")

But `my_character()` does **not** call `read_identity()`. It re-implements
the same cookie parse/verify sequence inline (lines 234-245), and the
re-implementation is not identical to `read_identity()`:

- `read_identity()` requires `isinstance(browser_id, str)` in addition to
  `isinstance(character_id, str)` before returning an identity.
- `my_character()` never extracts or validates `browser_id` at all, but
  additionally calls `get_character(character_id) is None` (a check
  `read_identity()` does not perform).

Today this divergence is unreachable in practice — every cookie that can
pass HMAC verification was minted by `select_character()`, which always
writes a valid `browser_id` string and only after confirming
`get_character()` succeeds. But the whole point of the "one true
verification path" comment is to make that safe *by construction*, not by
every caller happening to agree today. A future change to either function
(e.g., a new cookie-issuing path, a schema change to the payload) can now
silently diverge the two, exactly the failure mode the docstring warns
against.

**Fix:** Make `my_character()` call `read_identity()` and derive its
response from the returned `CookieIdentity`, e.g.:

```python
@router.get("/sessions/{session_id}/my-character", response_model=MyCharacterResponse)
async def my_character(session_id: str, request: Request) -> MyCharacterResponse:
    identity = read_identity(request, session_id)
    if identity is None or get_character(identity.character_id) is None:
        return MyCharacterResponse(selected=False, character_id=None)
    return MyCharacterResponse(selected=True, character_id=identity.character_id)
```

### WR-02: Confirm-idempotency short-circuit can report `confirmed: false` in the response while the event log actually holds an accepted+resolved check

**File:** `src/gptrpg/session_actor/actor.py:482-486`, `src/gptrpg/web/routes_actions.py:371-400`
**Issue:** `_prepare_confirm()`'s dedup check does not look at the
incoming command's `player_confirmed` value — it only compares `move`/
`stat` against the prior record:

```python
prior = self.state.confirmed_declares.get(command.caused_by_seq)
if prior is not None:
    if prior.move != command.move or prior.stat != command.stat:
        raise CommandRejected("이미 다른 무브로 확인된 선언이다")
    raise AlreadyConfirmed(prior)
```

`confirmed_declares` is only ever populated by a **true** confirm (the
reducer only records it `if payload.get("player_confirmed")`). So if a
second confirm request arrives for the same `declare_seq` with
`player_confirmed=False` (a "reject" click) but the same move/stat as the
already-accepted suggestion — which the frontend always sends, since
`ChatPane.tsx`'s reject button submits `resolve(proposal.candidates[0],
false)` using the same suggestion object regardless of accept/reject —
this raises `AlreadyConfirmed`, not a distinguishable "already accepted,
your reject is stale" outcome.

The route then does:

```python
except AlreadyConfirmed as exc:
    prior_confirm = exc.prior
    confirm_seq = prior_confirm.confirm_seq
...
if not body.confirmed:
    return ConfirmResponse(confirmed=False, confirm_seq=confirm_seq)
```

Because `body.confirmed` is `False` on this second request, the handler
returns `confirmed: False` to the caller — even though the event log
already has an `action_confirmed` event with `player_confirmed=True` for
that `declare_seq`, plus (possibly) an already-resolved `check_resolved`
event with real dice already rolled. The API response actively
contradicts the persisted state it is supposed to be reporting on.

This is reachable without any malicious client: the same signed cookie
(same `browser_id`) can be present in two open tabs/windows of the same
session. If tab A's accept request lands first, tab B still shows the
stale proposal; clicking "다시 쓰기" (reject) in tab B hits exactly this
path. The underlying event log stays correct (self-heals on the next
poll), but the immediate HTTP response for tab B is wrong.

**Fix:** Have `_prepare_confirm()` distinguish "duplicate of an identical
accept" from "reject arriving after an accept already landed", e.g. by
checking `command.player_confirmed` before raising `AlreadyConfirmed`, or
have the route branch on `prior_confirm is not None` before checking
`body.confirmed` and always report the *actual* recorded outcome:

```python
if prior_confirm is not None:
    # A confirm already landed for this declare_seq — report what actually
    # happened, not what this (stale) request asked for.
    return ConfirmResponse(confirmed=True, confirm_seq=confirm_seq, ...)
```

### WR-03: `ChatPane.tsx` silently swallows errors on the reject path

**File:** `frontend/src/panes/ChatPane.tsx:132-138`
**Issue:**

```tsx
} catch (error) {
  // 서사 실패는 이제 200이지만, 다른 실패(403·409·503 등)는 여전히
  // 예외로 온다 — 이 경로는 그대로 둔다.
  if (confirmed) {
    onTurnFailed(pending.declare_seq);
    setStatus({ text: messageFor(error), error: true });
  }
} finally {
  setBusy(false);
  pollNow();
}
```

If `confirmAction()` throws while the user is rejecting (`confirmed ===
false`) — network failure, unexpected 403/409/503, etc. — the catch block
does nothing at all. `proposal` was already cleared via `setProposal(null)`
before the request was sent, so the reject buttons are gone; `status` is
left at whatever it was before (likely `null`); `busy` clears in `finally`.
The user sees no error message and has no way to tell whether their reject
was recorded or not, and no retry affordance (the proposal UI is gone).

**Fix:** Surface reject-path failures too, even if the recovery action
differs from the confirm-path one (no need to call `onTurnFailed` since no
turn failure occurred, but the user should still learn the request did not
go through):

```tsx
} catch (error) {
  if (confirmed) {
    onTurnFailed(pending.declare_seq);
  }
  setStatus({ text: messageFor(error), error: true });
} finally {
  setBusy(false);
  pollNow();
}
```

### WR-04: `declare()`'s second `actor.submit()` call is unguarded, unlike the equivalent CLI code

**File:** `src/gptrpg/web/routes_actions.py:256-270`
**Issue:** The `action_classifier` `RecordAiCall` submission sits outside
the `try`/`except` block that wraps the rest of the declare flow (lines
200-254). If this submission raises (e.g. `CommandRejected` from a
provider returning out-of-range token counts, or a `SequenceConflict`), it
is not caught anywhere in this handler and propagates as an unhandled
exception → a generic 500, even though the `action_declared` event and the
classification work (`proposal`) already succeeded. The client gets a
bare 500 and loses the classification result it should have received.

`cli/turn_flow.py` explicitly wraps its equivalent "always submit" call
(the second `RecordAiCall` for `master_gm`) in its own try/except with a
documented rationale (WR-02 in that file) precisely to avoid this kind of
unguarded call after fallible work has already succeeded. The web route's
first `RecordAiCall` (for `action_classifier`) does not have the same
protection.

**Fix:** Wrap the `RecordAiCall` submission in its own try/except and
return a clear error status (or, if the intent is that actor/store
failures should be genuine 500s per the codebase's established convention
of letting non-domain failures propagate, document that choice next to
this call the way `WR-01`/`WR-02` comments do elsewhere, so a future
reader doesn't mistake it for an oversight).

## Info

### IN-01: `_build_turn_context` re-export chain has two aliases with slightly divergent docstrings

**File:** `src/gptrpg/cli/main.py:31-32,51-54`, `src/gptrpg/cli/turn_flow.py:95-99`
**Issue:** `main.py` imports `_build_turn_context` from `turn_flow` under
its own name for backward compatibility with `tests/test_turn_tracer.py`,
while `turn_flow.py` itself aliases `build_turn_context` (from
`gptrpg.turn.context`) to the same private name. This isn't a bug, but the
double indirection (`gptrpg.turn.context.build_turn_context` →
`cli.turn_flow._build_turn_context` → `cli.main._build_turn_context`) is
easy to lose track of when the underlying function's signature changes;
consider having the compatibility shim import directly from
`gptrpg.turn.context` in a follow-up cleanup once `test_turn_tracer.py` is
updated, to shorten the chain.

---

_Reviewed: 2026-08-06T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
