---
phase: 12
slug: stats-resources-inventory
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-17
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `12-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest — already used repo-wide (`tests/` holds 60+ `test_*.py` files) |
| **Config file** | `pyproject.toml` — the exact `[tool.pytest.ini_options]` section was NOT opened during research; the first plan must confirm it |
| **Quick run command** | `uv run pytest tests/test_reducer_*.py tests/test_entities.py tests/test_rulebook.py -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | unmeasured — the first plan must record an actual number |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_reducer_*.py tests/test_entities.py tests/test_rulebook.py -q`
- **After every plan wave:** Run `uv run pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** target < 60 seconds for the quick run (to be confirmed against the measured runtime above)

---

## Per-Task Verification Map

*Seeded as draft — the planner fills Task IDs and the executor fills Status. Requirement → command mapping below is from `12-RESEARCH.md` § Phase Requirements → Test Map.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | RULE-02, RULE-03 | T-12-01 (client-supplied modifier tampering) | server derives the modifier from `StatEntry` + rulebook declaration; no free-form number is accepted from web or CLI | unit | `uv run pytest tests/test_resolution_stat_modifier.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | RULE-04, RULE-05 | T-12-03 (retry double-spends a resource) | resource writes ride on the Phase 8 idempotency window (`AlreadyConfirmed` / `AlreadyResolved`) | unit+integration | `uv run pytest tests/test_reducer_resource_change.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | RULE-13, RULE-14 | — | N/A | unit | `uv run pytest tests/test_rulebook.py -k grade_band_costs -x` | ⚠️ partial (file exists, cases new) | ⬜ pending |
| TBD | TBD | TBD | QUAL-01 | T-12-04 (event reordering changes replayed state) | `fold()` validates ordering itself and raises rather than silently continuing | unit | `uv run pytest tests/test_reducer_*.py -k out_of_order -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | QUAL-02 | — | a missing schema marker is distinguishable from a genuinely old record; neither is silently defaulted | unit | `uv run pytest tests/test_event_schema_migration.py -k marker -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | QUAL-06 | — | N/A | unit | `uv run pytest tests/test_entities.py -k clamp -x` | ⚠️ partial | ⬜ pending |
| TBD | TBD | TBD | RULE-09 (D-06 dice amounts) | — | randomness routes only through `Roller` / `ReplayRoller`; no new random path | unit | `uv run pytest tests/test_dice_amount.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | TEST-04 | T-12-04 | committed fixture replays to identical state | regression | `uv run pytest tests/test_event_schema_migration.py -k fixture -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_resolution_stat_modifier.py` — stubs for RULE-02, RULE-03 (stat → modifier assembly)
- [ ] `tests/test_reducer_resource_change.py` — stubs for RULE-04, RULE-05, QUAL-01, QUAL-06
- [ ] `tests/test_dice_amount.py` — stubs for D-06 dice-expression parsing and the `roll_die(sides)` extension
- [ ] `tests/fixtures/session1_events.jsonl` (or equivalent) — a **committed** fixture so TEST-04 actually runs in CI. Research Pitfall 5: `.gptrpg/events.db` (895 events, schema v2) is gitignored, so the existing `test_event_schema_migration.py` `skipif` guard means that test never runs on CI today.
- [ ] Test fixtures covering `clock` / `tag_list` / `usage_die` — the three representation forms `11-VERIFICATION.md` left unproven (RULE-11 is 3/6). No repo rulebook declares them, but resource change must work for all six forms.
- [ ] Framework install: **not needed** — pytest is already installed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| "dice 7 + STR 2 = 9 vs target 10" is legible on screen (D-04) | RULE-06 | Visual legibility of the arithmetic breakdown is the point; an assertion that the numbers exist does not prove a person can check the math | Open a session, take an action that rolls, confirm the confirmation panel shows each addend, its source, the total, and the target |
| A large resource drop is noticeable without hunting for it (D-19) | RULE-07 | D-19 deliberately refuses to define a "large" threshold, so there is no numeric assertion to make — the requirement is that a person notices | Trigger a small change and a large change in the same session; confirm both are announced and the large one reads as more emphatic |
| The AI narrator perceives four distinct party members (D-18) | RULE-16 | The session-1 failure was the model collapsing four characters into one; catching a regression needs a human reading the prose | Run a scene with all four characters at differing resource levels; confirm the narration addresses them as separate people with the right states |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
