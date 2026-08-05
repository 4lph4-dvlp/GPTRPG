---
phase: 03-ai
reviewed: 2026-08-02T15:48:09Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - src/gptrpg/agents/master_gm.py
  - src/gptrpg/agents/providers/anthropic_provider.py
  - src/gptrpg/agents/providers/base.py
  - src/gptrpg/agents/providers/gemini_provider.py
  - src/gptrpg/agents/providers/nim_provider.py
  - src/gptrpg/agents/providers/openai_provider.py
  - src/gptrpg/agents/providers/openrouter_provider.py
  - src/gptrpg/cli/turn_flow.py
  - tests/conftest.py
  - tests/test_agents_retry.py
  - tests/test_master_gm.py
  - tests/test_providers.py
  - tests/test_turn_flow_failure.py
findings:
  critical: 0
  warning: 2
  info: 1
  total: 3
status: issues_found
---

# Phase 03-ai: Code Review Report (Gap-Closure Re-Review)

**Reviewed:** 2026-08-02T15:48:09Z
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

This is a focused re-review of two UAT gap-closure fixes: G-03-1 (OpenRouter's
`X-Title` attribution header switched from Korean to ASCII, plus a regression
sweep across all 5 adapters) and G-03-3 (`note_result()` promoted to a formal
`Provider` protocol method to fix the delegation-swallowing bug that crashed
NIM/OpenRouter turns, plus `turn_flow.py`'s narration section wrapped in
exception handling).

**G-03-1 (ASCII headers):** Verified correct. `_ATTRIBUTION_HEADERS` in
`openrouter_provider.py` is now pure ASCII (`"GPTRPG M0 Experiment Tool"`,
`"https://github.com/gptrpg-m0/gptrpg"`). The regression tests
(`test_openrouter_attribution_header_constant_is_ascii`,
`test_openrouter_delegate_client_headers_are_ascii`,
`test_all_five_adapters_header_dicts_are_ascii_when_present`) correctly
inspect the headers actually handed to the constructed SDK client (not just
the module constant), so a future re-introduction of non-ASCII text — even
routed through a different code path — would still be caught. No issues found
in this fix.

**G-03-3 (`note_result()` protocol + turn_flow exception handling):** The
`note_result()` method is implemented consistently and correctly across all
5 adapters (confirmed by direct read of all 5 provider files and a
codebase-wide grep for stray `_last_result =` assignments outside the
provider modules — none found). `NimProvider`/`OpenRouterProvider` both
delegate `note_result()`/`last_result()` to `self._delegate` rather than
holding their own `_last_result`, which is exactly the fix G-03-3 needed.
The new tests in `test_master_gm.py` (`_DelegateShapedStallsForeverProvider`
and friends) specifically exercise a hand-built delegation shape driven
through `narrate()`, which is precisely the blind spot that let G-03-3 slip
through the original review — this gap is now closed.

Two structural issues remain in `turn_flow.py`'s new exception-handling
block, both concerning the *boundary* of what the `try/except` around the
narration section actually covers — see Warnings below. Neither is a defect
in the core G-03-3 fix; both are edge-case gaps in how far the "never let a
raw exception escape to the CLI" goal was carried through the function.

## Warnings

### WR-01: Narration exception handler also swallows unrelated actor/store failures, mislabeling them as AI narration failures

**File:** `src/gptrpg/cli/turn_flow.py:340-370`
**Issue:** The `try` block wrapping the narration section covers not just
`narrate()`/`next()` (the actual LLM stream) but also every
`await actor.submit(AppendNarration(...))` call inside the same block (lines
355-359 and 363-367). If an `AppendNarration` submission itself raises for a
reason that has nothing to do with the AI provider — e.g. an event-schema
validation bug, an `EventStore` write failure, or any other actor-level
defect — that exception is caught by the same `except Exception as exc:
narration_error = exc` handler that was designed to catch LLM streaming
failures. The user then sees:

```
오류: 서사가 끝까지 나오지 못했다 — <actor/store exception message>
```

which is textually accurate (it does print the underlying exception message)
but semantically misleading: "서사가 끝까지 나오지 못했다" ("the narration
didn't finish") implies an AI/provider problem, when the actual defect is in
the event-recording layer. This is exactly the failure mode the review was
asked to check for — over-broad exception handling masking a genuinely
different class of bug. It also creates a possible screen/log divergence: if
`print(first_sentence)` (line 354) has already run and the *subsequent*
`actor.submit(AppendNarration(...))` (line 355-359) is what raises, the
sentence is visible on the user's terminal but was never persisted to the
event log — the exact kind of split-brain state phase 03 event sourcing is
supposed to prevent.

**Fix:** Narrow the `try` to cover only the AI-facing calls (`narrate()`
construction, `next(narration_iter, ...)`, and iterating `narration_iter`),
and let `actor.submit(AppendNarration(...))` failures propagate on their own
(or be caught separately with a distinct, honestly-labeled error message).
For example:

```python
try:
    narration_iter = narrate(...)
    first_sentence = with_progress_dots(...)
except Exception as exc:  # only the AI stream failed
    narration_error = exc
    first_sentence = _NO_SENTENCE

if first_sentence is not _NO_SENTENCE:
    print(first_sentence)
    await actor.submit(AppendNarration(...))  # let a genuine actor bug crash loudly
    chunk_index += 1
    try:
        for sentence in narration_iter:
            print(sentence)
            await actor.submit(AppendNarration(...))
            chunk_index += 1
    except Exception as exc:
        narration_error = exc
```

If the intent really is "never crash under any circumstance during this
whole block," at minimum log/print a differently-worded message when the
exception's origin is an `actor.submit()` call rather than the narration
generator, so operators can tell the two failure modes apart.

### WR-02: The mandatory closing `RecordAiCall` submission is not covered by the "never let a raw exception escape" handler, so G-03-3's own stated goal can still be defeated one step later

**File:** `src/gptrpg/cli/turn_flow.py:372-387`
**Issue:** The docstring/comment at line 372-374 says step ⑥ "성공·실패
어느 쪽에서도 항상 제출한다" (always submits, success or failure) — and the
task framing for this review states the fix's purpose was so that a failure
"never lets a raw exception escape to the CLI." But the `await
actor.submit(RecordAiCall(...))` call at lines 377-387 sits *after* the
`try/except` block ends (line 369) and is not itself guarded. If this
submission raises — same failure classes as WR-01 (event-schema bug, store
I/O failure, actor crash) — the exception propagates unhandled out of
`_turn_flow`, through `run_turn`'s `finally: await actor.stop()` (which does
not catch it), and becomes exactly the raw traceback G-03-3 was written to
eliminate. The fix protects the narration-generation/emission path but not
the "always submit" bookkeeping call that follows it, so the crash mode it
was designed to close is still reachable — just one call later in the same
function.

**Fix:** Wrap the closing `RecordAiCall` submission too, or fold it into the
same outer `try/except` so a failure there degrades to the same "print to
stderr, exit 1" behavior instead of an unhandled exception:

```python
elapsed_ms = int((time.monotonic() - narration_start) * 1000)
gm_result = _last_result_or_failure_envelope(gm_provider, elapsed_ms=elapsed_ms)
try:
    await actor.submit(
        RecordAiCall(
            agent_role="master_gm",
            model=gm_choice.model,
            provider=gm_choice.provider,
            prompt_tokens=gm_result.prompt_tokens,
            completion_tokens=gm_result.completion_tokens,
            latency_ms=gm_result.elapsed_ms,
            caused_by_seq=confirm_seq,
        )
    )
except Exception as exc:  # noqa: BLE001 - bookkeeping submission must not crash the CLI either
    narration_error = narration_error or exc
```

## Info

### IN-01: No test drives a real production delegating adapter end-to-end through `narrate()`

**Files:** `tests/test_providers.py`, `tests/test_master_gm.py`
**Issue:** Coverage for the G-03-3 fix currently comes from two disjoint
angles: (1) `test_providers.py` verifies `note_result()`/`last_result()`
round-trip correctly on the *real* `NimProvider`/`OpenRouterProvider`
classes, but never through `narrate()`; and (2) `test_master_gm.py` verifies
`narrate()`'s failure path correctly reaches through a delegation shape, but
only via a hand-built `_DelegateShapedStallsForeverProvider` test double, not
the real `NimProvider`/`OpenRouterProvider` classes. No single test composes
a real `NimProvider` (wrapping a real `OpenAIProvider` whose SDK client is
faked at the network boundary, as `test_providers.py`'s `_no_network`
fixture already does) and drives it through `narrate()` to confirm the full
two-layer production stack behaves the same way the shaped-double tests
predict. This is a reasonable unit-testing split (and both angles are
individually solid), but it is precisely the kind of "double is close in
shape but not identical to the real thing" gap that let G-03-3's original
private-attribute bug hide behind 307 passing tests. Not blocking, but worth
closing before the next UAT round touches NIM/OpenRouter narration paths
directly.
**Fix:** Add one test in `test_master_gm.py` or `test_providers.py` that
constructs `NimProvider(_FAKE_KEY)` with the `_no_network`-style client fake,
monkeypatches its inner `OpenAIProvider._client.chat.completions.create` to
raise mid-stream, and asserts `narrate()` still returns emitted chunks and
leaves `provider.last_result().ok is False` afterward — using the real
class, not a shaped double.

---

_Reviewed: 2026-08-02T15:48:09Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
