---
created: 2026-08-15
title: 판정의 기본 능력치를 「그때그때 고른다」로 비워둘 수 있게 한다
area: rulebooks/moves, rules_core/rulebook, agents/prompt_assembly
severity: major
resolves_in: 11-04
files:
  - src/gptrpg/rulebooks/moves.py:MoveDecl.default_stat
  - src/gptrpg/rules_core/rulebook.py:validate_move_stats
  - src/gptrpg/agents/prompt_assembly.py:110
  - src/gptrpg/rulebooks/dungeonworld_like.py
---

## Problem

**어디서 나왔나:** 2026-08-15, 계획 11-02 실행 중 발생한 편차. 실행자가 신고했고
사장님이 「11-04에 접어넣기」로 결정했다.

던전월드류 무브 둘 — `defy_danger`(위험을 무릅쓰다), `aid_or_interfere`(돕거나 훼방
놓다) — 은 원래 `default_stat="상황에 맞는 능력치"`였다. 원문 설계가 **일부러** 단일
능력치를 정하지 않은 자리다: 접근 방식에 따라 어느 능력치든 쓸 수 있다는 뜻이다.

11-02가 추가한 `validate_move_stats`가 「모든 무브의 `default_stat`은 그 룰북이 선언한
자원 축 이름이어야 한다」를 등록 시점에 강제하면서 이 두 값이 등록을 깼다. 실행자는
`DEX` / `CHA`로 근사치를 골라 넣었다(커밋 `ac51d48`~`8e88562` 구간, 코드 주석에 근거
기록됨).

**왜 문제인가:** 방향이 반대다. 이 프로젝트의 목적은 특정 룰북에 치우치지 않는 범용
시스템이고, Phase 11의 주제는 「룰북이 자기 어휘를 말하게 한다」이다. 그런데 여기서는
룰북이 표현하고 싶은 것(「그때그때 고른다」)을 **플랫폼이 표현할 방법을 안 줘서 룰북
데이터를 플랫폼 모양에 맞게 구부렸다.** 플랫폼 제약이 룰북 데이터로 새어나온 사례다.

**실제 피해 범위:** 제한적이다. `default_stat`은 분류기 프롬프트 힌트로만 쓰이고
(`prompt_assembly.py:110` — "기본 능력치 {default_stat}"), 실제 판정 능력치는
`ConfirmRequest.stat`으로 확인 시점에 다시 정해진다. 게임이 틀리게 돌지는 않고,
AI가 받는 설명이 원문보다 좁아진 상태다.

## Fix

`MoveDecl.default_stat`을 비워둘 수 있는 값으로 바꾼다:

1. `MoveDecl.default_stat: str | None` — 비어 있으면 「그때그때 고른다」는 뜻
2. `validate_move_stats`가 비어 있는 값은 검사에서 건너뛴다 (구멍 검사는 유지)
3. `prompt_assembly.py:110`이 비어 있을 때 "상황에 맞게 고른다"로 렌더링한다 —
   AI가 「없다」가 아니라 「자유롭게 고르는 자리」로 이해해야 한다
4. `dungeonworld_like`의 두 무브를 원래 의도대로 되돌린다 (DEX/CHA 근사 제거,
   근사치를 설명하던 코드 주석도 함께 정리)

## Why 11-04

11-04는 이미 `moves.py`·`rulebook.py`·`dungeonworld_like.py`를 고치고, 성격이 정반대인
세 번째 룰북(Cairn)을 넣는 계획이다. Cairn이 같은 벽에 부딪히는지 먼저 확인하면
**플랫폼 변경이 정말 필요한지가 데이터로 증명된다.** 11-04의 원 전제가 「플랫폼 그릇을
안 고치고 데이터로 넣는다」이므로, 이 항목은 그 전제에 대한 정직한 반례 시험이기도 하다.

## Resolved (2026-08-16, 계획 11-04)

**Cairn이 이 벽에 부딪혔는가 — 아니다, 하지만 부딪히지 않은 이유가 중요하다.**
Cairn 자체는 SRD 원문에 고정 무브/행동 목록이 없다(`MOVE_CATALOGS["cairn"] = ()`,
`check_trigger_mode="gm_discretion"`) — 그래서 Cairn에는 애초에 `MoveDecl.default_stat`
자리가 하나도 생기지 않는다. 이 벽에 실제로 부딪힌 것은 여전히 던전월드류의 두 무브뿐이었다
(11-02에서 이미 발견됨). 즉 Cairn의 설계(재량 판정 모드) 자체가 이 벽을 우회한 것이지,
플랫폼 그릇이 이 문제를 미리 해결해 둔 상태였던 것은 아니다 — 두 무브의 부채는 그대로
남아 있었고 이번 항목이 그것을 갚았다.

**적용한 수정 (계획서 Fix 1~4 그대로):**
1. `MoveDecl.default_stat: str | None`로 확장(`moves.py`)
2. `validate_move_stats`가 `None`을 검사에서 건너뛴다 — 구멍 검사(실제 문자열 대조)는 유지
   (`rules_core/rulebook.py`)
3. `prompt_assembly._format_moves`가 `None`일 때 "상황에 맞게 고른다"로 렌더링
   (`agents/prompt_assembly.py`)
4. `defy_danger`/`aid_or_interfere`의 `default_stat`을 `DEX`/`CHA` 근사에서 `None`으로
   되돌리고, 근사치를 설명하던 주석을 이번 결정을 기록하는 주석으로 교체(`dungeonworld_like.py`
   — 실제로는 `moves.py`, 무브 선언이 그 파일에 있다)

`tests/test_action_classifier.py::test_format_moves_renders_none_default_stat_as_situational_choice`
신설로 렌더링 결과를 회귀 시험으로 고정했다. `tests/test_prompt_assembly_scenario.py`는
이 변경으로 깨지지 않았다(default_stat을 다루지 않는 파일 — 11-07도 안전).
`uv run pytest -q` 895 passed, `uv run lint-imports` 4 kept/0 broken.
