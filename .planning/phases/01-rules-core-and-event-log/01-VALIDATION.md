---
phase: 1
slug: rules-core-and-event-log
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-31
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Seeded by `/gsd-plan-phase 1` from `01-RESEARCH.md` § Validation Architecture.
> Task-level rows are filled by `/gsd-validate-phase` once PLAN.md task IDs exist.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 [VERIFIED in research] |
| **Config file** | none — Wave 0 creates `[tool.pytest.ini_options]` in `pyproject.toml` + `tests/conftest.py` |
| **Quick run command** | `uv run pytest -q` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~10 seconds (pure-Python unit tests + in-process SQLite; no network, no server startup) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest -q`
- **After every plan wave:** Run `uv run pytest` (full suite, includes the import-linter boundary contracts)
- **Before `/gsd-verify-work`:** Full suite green AND `uv run pytest tests/test_reverse_verification.py` passes all six assertions (D-11 gate)
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

Task IDs are assigned during planning; this table is seeded at the requirement level and
re-keyed to `{N}-{plan}-{task}` by `/gsd-validate-phase`.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | 0 | RIG-02 | — | N/A | unit | `uv run pytest tests/test_boundaries.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | RIG-02 | T-1-CSPRNG | `rules_core` cannot import `random`; dice come from an injected roller backed by `secrets` | unit | `uv run pytest tests/test_dice_replay.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | RIG-06 | — | N/A | integration | `uv run pytest tests/test_event_log.py -k fold -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | RIG-06 | T-1-SEQ | Concurrent writes to the same `(session_id, seq)` — exactly one commits, the loser raises `SequenceConflict` | integration | `uv run pytest tests/test_event_log.py -k concurrency -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | RIG-06 / D-11 | T-1-PAYLOAD | Event payloads round-trip through `model_validate_json` only — never `pickle`/`eval` | integration | `uv run pytest tests/test_reverse_verification.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**D-11 is the phase's load-bearing check.** `tests/test_reverse_verification.py` builds a synthetic
complete session log and asserts that all six MEAS numbers (token spend, turn count, input→confirm
latency, confirm→first-narration latency, failure-count vs threat-clock advances, player utterance +
system suggestion + player confirmation) are derivable from the log alone. A missing event field must
fail here — loudly, naming which measurement broke — not in Phase 6 when the two sessions are already
spent and unrepeatable.

---

## Wave 0 Requirements

- [ ] `pyproject.toml` — `uv init --lib gptrpg` + `[tool.pytest.ini_options]`
- [ ] `.importlinter` — `layers` contract (`session_actor` → `rules_core | event_log`) + `forbidden` contract (no `time`/`random`/`os`/`socket` inside `rules_core`)
- [ ] `tests/conftest.py` — temp-SQLite-path fixture + `fake_session_log` fixture (one complete session mixing all event types)
- [ ] `tests/test_boundaries.py` — new
- [ ] `tests/test_event_log.py` — new
- [ ] `tests/test_dice_replay.py` — new
- [ ] `tests/test_reverse_verification.py` — new
- [ ] Framework install: `uv add --dev pytest hypothesis import-linter ruff pytest-asyncio`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| CLI replay tool output is readable by a human who did not write it | RIG-06 (success criterion 1, "실물로 증명") | Output legibility is a judgment call, not an assertable string | Run the replay tool against a recorded session file; confirm the reconstructed state is understandable without reading source |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
