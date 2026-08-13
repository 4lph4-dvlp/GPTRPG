# Phase 10 — Deferred Items (out of scope for the touching plan)

## 10-04

- **`tests/test_agent_context_caps.py:31` — unused import `gptrpg.rules_core.entities.Entity`**
  (`ruff F401`). Pre-existing before 10-04 (file untouched by this plan's diff, confirmed via
  `git diff --stat -- tests/test_agent_context_caps.py` showing no changes). Not fixed —
  out of scope per SCOPE BOUNDARY (only auto-fix issues directly caused by the current task's
  changes). Leave for a future lint-cleanup task.
