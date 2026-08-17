"""`turn` 하위 명령의 실제 흐름 — 분류 -> 세 갈래 확인 -> 판정 -> 문장 단위 서사.

`cli/main.py`는 인자 파싱과 저장소·세션 준비만 한다(그 파일의 "게임 규칙이
한 줄도 없다"는 약속). 흐름 자체, 확신도 세 갈래 확인 화면(D-34/D-35/D-36),
5초 진행 표시(D-26), 판정 결과를 서사보다 먼저 내보내는 순서(MEAS-02)는
전부 이 모듈이 진다.
"""

import argparse
import os
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from gptrpg.agents.action_classifier import MoveCandidate, classify
from gptrpg.agents.config import AgentChoice, load_config, resolve_provider
from gptrpg.agents.context import NO_CHECK_SUMMARY
from gptrpg.agents.envelope import AgentResult
from gptrpg.agents.master_gm import narrate
from gptrpg.agents.providers.base import Provider
from gptrpg.event_log.store import EventStore
from gptrpg.rulebooks import get_rulebook
from gptrpg.rulebooks.moves import get_moves
from gptrpg.rules_core.resource_change import ResourceOp, roll_amount
from gptrpg.rules_core.rulebook import (
    GradeBand,
    OutcomeList,
    UnknownGradeName,
    ordered_categories,
    require_band,
)
from gptrpg.session_actor.actor import (
    AlreadyChanged,
    AppendNarration,
    ConfirmAction,
    DeclareAction,
    ProceedEligible,
    RecordActionClassification,
    RecordAiCall,
    RecordResourceChange,
    RecordSafetyFlag,
    ResolveCheck,
    SessionActor,
    SessionRegistry,
    VerifyProceedEligibility,
)
from gptrpg.session_actor.live_roller import LiveRoller
from gptrpg.turn.clock_condition import build_clock_judge_context, run_clock_condition_check
from gptrpg.turn.context import CLOCK_SEGMENT_COUNT, build_turn_context
from gptrpg.turn.judgments import build_narration_facts, empty_turn_judgments, gather_turn_judgments

_T = TypeVar("_T")

_NO_SENTENCE = object()
"""narrate()의 첫 조각을 기다릴 때 쓰는 보초값. `chunk_sentences`는 빈
문자열을 절대 내보내지 않으므로 이 값과의 신원 비교로 "아직 하나도 안
나왔다"를 안전하게 구분할 수 있다."""

_NO_CHECK_GRADE_BAND = GradeBand(
    name="__no_check__", counts_as_failure=False, succeeded=True, costs=False
)
"""`_proceed_without_check`가 `gather_turn_judgments`에 넘기는
자리표시자(12-06) — `web/routes_actions.py`의 같은 이름 상수와 같은
이유·같은 값이다. 판정이 없는 경로에는 태울 결과 목록이 없고,
`costs=False`가 `pick_outcome`의 조기 반환을 걸어 모델을 아예 안 부른다."""


async def _submit_narration_chunk(
    *,
    actor: SessionActor,
    chunk,  # NarrationChunk — 순환 import를 피하려 타입만 값으로 쓴다(agents는 이 모듈을 모른다)
    chunk_index: int,
    resolve_seq: int,
    narration_texts: list[str],
) -> None:
    """`narrate()`가 낸 `NarrationChunk` 하나를 화면·사건으로 옮긴다(10-01, Task 2 ⑦).

    `web/routes_actions.py`의 같은 이름 도우미와 똑같은 모양이다 — 다른
    점은 여기서 `print(chunk.text)`도 그대로 한다는 것뿐이다(명령줄은
    지금도 화면에 직접 찍는다). `disposition != "clean"`이면 이어서
    `RecordSafetyFlag`를 같은 `caused_by_seq`로 제출하고, `"blocked"`인
    조각은 `narration_texts`에 넣지 않는다(배경 시계 조건 검사가 이야기
    텍스트로만 받아야 한다).
    """
    print(chunk.text)
    await actor.submit(
        AppendNarration(text=chunk.text, chunk_index=chunk_index, caused_by_seq=resolve_seq)
    )
    if chunk.disposition != "clean":
        await actor.submit(
            RecordSafetyFlag(
                source="narration",
                reason=chunk.reason,
                disposition=chunk.disposition,
                matched_len=chunk.matched_len,
                subject_len=chunk.subject_len,
                chunk_index=chunk_index,
                caused_by_seq=resolve_seq,
            )
        )
    if chunk.disposition != "blocked":
        narration_texts.append(chunk.text)


def with_progress_dots(
    fn: Callable[[], _T], *, threshold_s: float = 5.0, tick_s: float = 1.0
) -> _T:
    """`fn()`을 부르는 동안 `threshold_s`초를 넘기면 `tick_s`마다 점을 찍는다 (D-26).

    데몬 스레드 하나가 화면 출력만 맡는다 — `fn()` 자체는 이 함수를 부른
    스레드에서 그대로 실행된다(블로킹, 외부 라이브러리를 쓰지 않는다).
    `fn()`이 `threshold_s` 안에 끝나면 점이 하나도 안 찍힌다. 점을 하나라도
    찍었으면 `fn()`이 끝난 뒤 줄바꿈으로 마감해 다음 출력이 점 뒤에 바로
    붙지 않게 한다 — 점이 하나도 없었으면 아무것도 더 찍지 않는다(불필요한
    빈 줄을 만들지 않는다).
    """
    done = threading.Event()
    dot_count = 0
    lock = threading.Lock()

    def _tick() -> None:
        nonlocal dot_count
        if done.wait(threshold_s):
            return
        while not done.is_set():
            print(".", end="", flush=True)
            with lock:
                dot_count += 1
            if done.wait(tick_s):
                return

    ticker = threading.Thread(target=_tick, daemon=True)
    ticker.start()
    try:
        return fn()
    finally:
        done.set()
        ticker.join()
        with lock:
            printed_any = dot_count > 0
        if printed_any:
            print()


# `_build_turn_context`는 이제 `gptrpg.turn.context.build_turn_context`가 소유한다
# (04-05 Task 1 — 명령줄과 웹이 함께 쓰는 층으로 내려감). 이 이름은 그 함수를
# 가리키는 별칭으로만 남는다 — `cli/main.py`가 이 이름을 `tests/test_turn_tracer.py`용으로
# 다시 노출하고 있어 이름이 사라지면 그 시험이 깨진다.
_build_turn_context = build_turn_context


def _resolve_role_choice(args: argparse.Namespace, role: str) -> AgentChoice:
    """그 역할이 쓸 제공자·모델을 정한다.

    `--provider`/`--model`이 둘 다 주어지면 두 역할 모두 그 값을 쓴다(빠른
    수동 시험용, 기존 트레이서 시험과의 호환). 둘 다 없으면 저장된 파일에서
    그 역할의 선택을 읽는다(D-33 — 다시 묻지 않는다). 저장 파일이 없으면
    `ConfigNotFound`가 그대로 위로 올라간다 — `agents select`를 먼저 돌리라는
    안내가 그 예외 메시지에 이미 들어 있다.
    """
    if args.provider and args.model:
        return AgentChoice(provider=args.provider, model=args.model)
    choices = load_config(Path(args.config))
    return choices[role]


def _read_single_confirmation(candidate: MoveCandidate) -> bool:
    """`single` 갈래 — 제안 한 줄 + `[Enter=확인 / n=아니오]` (D-34).

    안내 문구는 `print`로 찍는다(`input`의 prompt 인자가 아니다) — 표준입력을
    가짜로 바꿔치기하는 시험 방식에서는 `input`의 prompt 인자가 표준출력에
    찍히지 않기 때문이다. 번호 목록은 나오지 않는다. 신뢰도 숫자는 어디에도
    없다.
    """
    print(f"제안: {candidate.move} ({candidate.stat}) [Enter=확인 / n=아니오]")
    answer = input().strip().lower()
    return answer not in ("n", "no")


def _prompt_candidate_or_reject(candidates: tuple[MoveCandidate, ...]) -> MoveCandidate | None:
    """`several` 갈래 — 번호가 붙은 후보를 최대 셋까지 보여주고 숫자를 받는다 (D-35).

    잘못된 숫자·범위 밖 숫자는 다시 묻는다. `n`으로도 거부를 받는다.
    반환값이 `None`이면 거부다. 안내 문구는 `_read_single_confirmation`과 같은
    이유로 전부 `print`로 찍는다.
    """
    print("후보가 여럿입니다. 번호를 고르세요:")
    for i, candidate in enumerate(candidates, start=1):
        print(f"  {i}. {candidate.move} ({candidate.stat})")

    while True:
        print(f"[1-{len(candidates)} / n=아니오]")
        raw = input().strip().lower()
        if raw in ("n", "no"):
            return None
        if raw.isdigit():
            index = int(raw)
            if 1 <= index <= len(candidates):
                return candidates[index - 1]
        print(f"1부터 {len(candidates)} 사이의 번호 또는 n을 입력하세요.")


def _last_result_or_failure_envelope(provider: Provider, *, elapsed_ms: int) -> AgentResult:
    """`provider.last_result()`를 시도하고, 예외가 나면 실패 껍데기를 만들어 돌려준다.

    `master_gm.narrate()`의 실패 경로는 `Provider` 프로토콜의 `note_result()`로
    실패 껍데기를 남기는 것이 규약이다(G-03-3, 03-06). 하지만 제공자가 그
    규약을 어기면(예: `note_result()`가 값을 버리거나, 여섯 번째 어댑터가
    이 메서드를 빠뜨리면) `last_result()`가 여전히 `RuntimeError`를 던질 수
    있다 — 이 도우미가 그 경우에도 `None`을 돌려주지 않고 실패 껍데기를
    직접 만들어 채워, `RecordAiCall` 제출부가 성공/실패 갈래 없이 한 모양을
    유지하게 한다. 제공자가 규약을 어겨도 CLI는 죽지 않아야 한다.
    """
    try:
        return provider.last_result()
    except Exception:  # noqa: BLE001 - 제공자가 규약을 어겨도 CLI는 죽지 않아야 한다
        return AgentResult(
            ok=False,
            value=None,
            elapsed_ms=elapsed_ms,
            prompt_tokens=0,
            completion_tokens=0,
            cached_prompt_tokens=0,
        )


async def _proceed_without_check(
    store: EventStore,
    actor: SessionActor,
    args: argparse.Namespace,
    *,
    declare_seq: int,
    rulebook,
) -> int:
    """굴릴 필요가 없다고 분류된 행동(`tier == "no_check"`)을 판정 없이
    서술로 잇는다(D-10 ②갈래, RULE-15, 11-06).

    `web/routes_actions.py`의 `proceed()`와 같은 뜻·같은 구조를 CLI 방식으로
    밟는다 — `confirm`/`roll`에 해당하는 사건을 제출하지 않고,
    `check_summary` 자리에는 `NO_CHECK_SUMMARY` 고정 문장을 쓴다. 이 함수
    전체에서 `caused_by_seq`는 `declare_seq` 하나로 고정된다 — 이 경로에는
    확인·판정 사건이 없다(결정 1, PLAN.md).

    **웹과 같은 서버 쪽 이중 검사를 거친다(T-11-29, 11-06 rework).** CLI가
    직접 계산한 `tier`를 그대로 믿지 않는다 — `_turn_flow`가 이 함수를 부를
    수 있는 경로 자체는 지금 하나뿐이지만, `_prepare_confirm`의 소유권
    검사가 이미 세운 규율(우회 경로가 CLI·시험·다음 단계의 새 호출부로
    남는다, D-11)을 이 함수도 똑같이 따른다 — 액터가 사건에서 접은
    `declare_owners`/`declare_no_check`로 다시 확인한다.
    """
    try:
        await actor.submit(
            VerifyProceedEligibility(declare_seq=declare_seq, character_id=args.player)
        )
    except ProceedEligible:
        pass  # 검증 통과 — 사건은 안 남는다, 그대로 진행한다.

    # 파티 인자(party_state/actor_character_id)를 안 넘긴다(12-05) — 명령줄에는
    # 캐릭터 선택·신원 개념이 없다(person_id=args.player, character_id=args.player
    # 전제와 같은 이유). 기본값이 예시 개체 하나짜리 파티를 채운다.
    ctx = _build_turn_context(store, args.session, args.rulebook)

    # 상황판단·장면 신규 대상 판단·시계 신호 관문을 narrate() 호출 **전**에
    # 병렬로 부른다 — `_turn_flow`의 판정 뒤 구간과 같은 구조·같은 이유
    # (ARCH-04). 실패해도 진행을 막지 않는다(D-05, ARCH-05).
    situation_judge_choice = _resolve_role_choice(args, "situation_judge")
    entity_judge_choice = _resolve_role_choice(args, "scene_entity_judge")
    clock_judge_choice = _resolve_role_choice(args, "clock_judge")
    outcome_judge_choice = _resolve_role_choice(args, "outcome_picker")
    try:
        situation_provider = resolve_provider(
            "situation_judge", {"situation_judge": situation_judge_choice}, os.environ
        )
        entity_provider = resolve_provider(
            "scene_entity_judge", {"scene_entity_judge": entity_judge_choice}, os.environ
        )
        clock_provider = resolve_provider(
            "clock_judge", {"clock_judge": clock_judge_choice}, os.environ
        )
        outcome_provider = resolve_provider(
            "outcome_picker", {"outcome_picker": outcome_judge_choice}, os.environ
        )
        judgments = await gather_turn_judgments(
            situation_provider=situation_provider,
            situation_model=situation_judge_choice.model,
            entity_provider=entity_provider,
            entity_model=entity_judge_choice.model,
            clock_provider=clock_provider,
            clock_model=clock_judge_choice.model,
            outcome_provider=outcome_provider,
            outcome_model=outcome_judge_choice.model,
            ctx=ctx,
            check_summary=NO_CHECK_SUMMARY,
            rulebook_display_name=rulebook.display_name,
            # 판정 자체가 없는 경로다(D-10 ②갈래) — 결과 목록도 재량 판정도
            # 성립하지 않는다(`web/routes_actions.py`의 `proceed()`와 같은 이유).
            outcome_list=OutcomeList(categories=()),
            grade_band=_NO_CHECK_GRADE_BAND,
            resource_axes=rulebook.resource_axes,
        )
    except Exception as exc:  # noqa: BLE001 - D-05, 판단(및 그 제공자 구성)이 실패해도 진행을 막지 않는다
        print(
            f"경고: 상황판단/장면 신규 대상/시계 신호 판단이 실패했다 (declare_seq {declare_seq}) — {exc}",
            file=sys.stderr,
        )
        judgments = empty_turn_judgments()
        clock_provider = None

    await actor.submit(
        RecordAiCall(
            agent_role="situation_judge",
            model=situation_judge_choice.model,
            provider=situation_judge_choice.provider,
            prompt_tokens=judgments.situation.ai.prompt_tokens,
            completion_tokens=judgments.situation.ai.completion_tokens,
            cached_prompt_tokens=judgments.situation.ai.cached_prompt_tokens,
            latency_ms=judgments.situation.ai.elapsed_ms,
            caused_by_seq=declare_seq,
        )
    )
    await actor.submit(
        RecordAiCall(
            agent_role="scene_entity_judge",
            model=entity_judge_choice.model,
            provider=entity_judge_choice.provider,
            prompt_tokens=judgments.entity.ai.prompt_tokens,
            completion_tokens=judgments.entity.ai.completion_tokens,
            cached_prompt_tokens=judgments.entity.ai.cached_prompt_tokens,
            latency_ms=judgments.entity.ai.elapsed_ms,
            caused_by_seq=declare_seq,
        )
    )
    await actor.submit(
        RecordAiCall(
            agent_role="clock_judge",
            model=clock_judge_choice.model,
            provider=clock_judge_choice.provider,
            prompt_tokens=judgments.clock.ai.prompt_tokens,
            completion_tokens=judgments.clock.ai.completion_tokens,
            cached_prompt_tokens=judgments.clock.ai.cached_prompt_tokens,
            latency_ms=judgments.clock.ai.elapsed_ms,
            caused_by_seq=declare_seq,
        )
    )
    await actor.submit(
        RecordAiCall(
            agent_role="outcome_picker",
            model=outcome_judge_choice.model,
            provider=outcome_judge_choice.provider,
            prompt_tokens=judgments.outcome.ai.prompt_tokens,
            completion_tokens=judgments.outcome.ai.completion_tokens,
            cached_prompt_tokens=judgments.outcome.ai.cached_prompt_tokens,
            latency_ms=judgments.outcome.ai.elapsed_ms,
            caused_by_seq=declare_seq,
        )
    )

    facts = build_narration_facts(ctx=ctx, check_summary=NO_CHECK_SUMMARY, judgments=judgments)

    gm_choice = _resolve_role_choice(args, "master_gm")
    gm_provider = resolve_provider("master_gm", {"master_gm": gm_choice}, os.environ)

    # 서사 — `_turn_flow`의 ⑤ 구간과 한 글자도 다르지 않다(예외 포착 범위·
    # 되감지 않음·실패 처리 전부 동일). caused_by_seq만 `declare_seq`로 다르다.
    narration_start = time.monotonic()
    narration_error: Exception | None = None
    chunk_index = 0
    narration_texts: list[str] = []
    try:
        narration_iter = narrate(
            provider=gm_provider,
            model=gm_choice.model,
            facts=facts,
            rulebook_display_name=rulebook.display_name,
            resource_axes=rulebook.resource_axes,
        )
        first_sentence = with_progress_dots(
            lambda: next(narration_iter, _NO_SENTENCE),
            threshold_s=args.progress_after,
            tick_s=args.progress_tick,
        )
    except Exception as exc:  # noqa: BLE001 - 서사 스트림 생성/첫 조각 실패만 여기서 잡는다(G-03-3)
        narration_error = exc
        first_sentence = _NO_SENTENCE

    if first_sentence is not _NO_SENTENCE:
        await _submit_narration_chunk(  # 액터/저장소 결함은 여기서 그대로 터진다(WR-01)
            actor=actor,
            chunk=first_sentence,
            chunk_index=chunk_index,
            resolve_seq=declare_seq,
            narration_texts=narration_texts,
        )
        chunk_index += 1
        while True:
            try:
                sentence = next(narration_iter)
            except StopIteration:
                break
            except Exception as exc:  # noqa: BLE001 - 서사 스트림 이어받기 실패만 여기서 잡는다(G-03-3)
                narration_error = exc
                break
            await _submit_narration_chunk(  # 액터/저장소 결함은 여기서 그대로 터진다(WR-01)
                actor=actor,
                chunk=sentence,
                chunk_index=chunk_index,
                resolve_seq=declare_seq,
                narration_texts=narration_texts,
            )
            chunk_index += 1

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
                cached_prompt_tokens=gm_result.cached_prompt_tokens,
                latency_ms=gm_result.elapsed_ms,
                caused_by_seq=declare_seq,
            )
        )
    except Exception as exc:  # noqa: BLE001 - "항상 제출한다" 기록 제출 실패도 raw traceback으로 새면 안 된다(WR-02)
        print(f"오류: 진행자 AI 호출 기록 제출이 실패했다 — {exc}", file=sys.stderr)
        return 1

    if narration_error is not None or not gm_result.ok:
        reason = (
            str(narration_error)
            if narration_error is not None
            else "제공자가 last_result() 규약을 어겼다"
        )
        print(f"오류: 서사가 끝까지 나오지 못했다 — {reason}", file=sys.stderr)
        return 1

    if judgments.clock.should_check and clock_provider is not None:
        # `_turn_flow`와 같은 CLI/웹 비대칭 이유(Pitfall 1) — 여기서도
        # `await`로 끝까지 기다린다.
        await run_clock_condition_check(
            actor=actor,
            provider=clock_provider,
            model=clock_judge_choice.model,
            judge_ctx=build_clock_judge_context(ctx, NO_CHECK_SUMMARY),
            rulebook_display_name=rulebook.display_name,
            narration_text="\n".join(narration_texts),
            resolve_seq=declare_seq,
            clock_id=ctx.clock_state.clock_id,
            clock_segment_count=CLOCK_SEGMENT_COUNT,
        )

    return 0


async def _turn_flow(store: EventStore, actor: SessionActor, args: argparse.Namespace) -> int:
    """`turn` 하위 명령의 본체 — 분류 -> 세 갈래 확인 -> 판정 -> 문장 단위 서사.

    **판정 결과가 서사보다 항상 먼저 나간다.** 조건 분기가 아니라 흐름
    자체의 순서로 보장한다 — 판정을 제출하고 결과 줄을 화면에 찍은 뒤에야
    진행자(narrate)를 호출한다. 지연이 1초든 15초를 넘기든 이 순서는 코드
    구조상 뒤집힐 수 없다(MEAS-02 성공조건 3).
    """
    # ① 선언 — 플레이어가 친 문장을 다듬지 않고 그대로 기록한다 (MEAS-04)
    declare_seq = await actor.submit(DeclareAction(player_id=args.player, raw_text=args.text))

    rulebook = get_rulebook(args.rulebook)
    moves = get_moves(args.rulebook)
    # 파티 인자를 안 넘긴다(12-05) — 명령줄에는 캐릭터 선택·신원 개념이 없다
    # (아래 person_id=args.player, character_id=args.player 전제와 같은
    # 이유). 기본값이 예시 개체 하나짜리 파티를 채운다.
    ctx = _build_turn_context(store, args.session, args.rulebook)

    classifier_choice = _resolve_role_choice(args, "action_classifier")
    # WR-03 리뷰 발견: 실제 호출 경로가 `resolve_provider`를 쓰지 않고
    # `get_provider`를 직접 불러 로직을 중복시켰었다 — 저장된/CLI로 받은
    # 선택 하나짜리 `choices` 사전을 만들어 `resolve_provider`를 통해
    # provider를 만든다. 이제 `resolve_provider`가 죽은 코드가 아니다.
    classifier_provider = resolve_provider(
        "action_classifier", {"action_classifier": classifier_choice}, os.environ
    )

    # ② 분류 — 문장 입력 -> 행동 확인 표시 사이의 지연을 진행 표시로 덮는다
    proposal = with_progress_dots(
        lambda: classify(
            provider=classifier_provider,
            model=classifier_choice.model,
            ctx=ctx,
            raw_text=args.text,
            moves=moves,
            rulebook_display_name=rulebook.display_name,
            resource_axes=rulebook.resource_axes,
        ),
        threshold_s=args.progress_after,
        tick_s=args.progress_tick,
    )
    ai_result = proposal.ai
    await actor.submit(
        RecordAiCall(
            agent_role="action_classifier",
            model=classifier_choice.model,
            provider=classifier_choice.provider,
            prompt_tokens=ai_result.prompt_tokens,
            completion_tokens=ai_result.completion_tokens,
            cached_prompt_tokens=ai_result.cached_prompt_tokens,
            latency_ms=ai_result.elapsed_ms,
            caused_by_seq=declare_seq,
        )
    )
    # T-11-29(11-06 rework) — 웹(`web/routes_actions.py`)과 똑같은 자리·
    # 똑같은 이유로 분류 결정을 사건에 durable하게 남긴다. CLI가 직접 계산한
    # `tier`를 그대로 믿지 않고, `_proceed_without_check`가 이 표를 다시
    # 접어 확인하게 한다(웹/CLI 어느 쪽도 「직접 찾아야 함」 우회가 없다).
    await actor.submit(
        RecordActionClassification(
            no_check=proposal.tier == "no_check",
            caused_by_seq=declare_seq,
        )
    )
    if proposal.unknown_move is not None:
        # SAFE-07/D-12, 10-05 — 웹(`web/routes_actions.py`)과 똑같은 자리·
        # 똑같은 조건으로 계약 위반을 운영자 기록에 남긴다. 이름 문자열
        # 자체는 사건에 안 들어간다(T-10-03).
        await actor.submit(
            RecordSafetyFlag(
                source="classifier",
                reason="unknown_move",
                disposition="blocked",
                subject_len=len(proposal.unknown_move),
                caused_by_seq=declare_seq,
            )
        )

    tier = proposal.tier

    # ③ 네 갈래 확인 화면 — 어느 갈래에서도 사람 입력 없이 다음으로 못
    # 넘어간다. `unclear`(AI가 못 알아들었음)만 이번 턴을 판정 없이 끝낸다
    # — 되돌리기 전용 화면을 만들지 않는다, ConfirmAction 자체를 제출하지
    # 않는다. 「확인 사건 없는 선언 사건」이 곧 「직접 찾아야 함」 사례의
    # 기록이다 (D-29, D-36, HYP-04의 세 번째 칸).
    if tier == "unclear":
        print("이번 턴은 판정 없이 여기서 끝납니다. 필요하면 다음 턴에 roll 명령을 직접 쓰세요.")
        return 0

    # `no_check`(굴릴 필요 없음)는 11-06부터 판정 없이 서사가 실제로
    # 이어지는 별도 갈래다(D-10 ②갈래, RULE-15) — `unclear`와 더 이상 같은
    # 화면이 아니다. 후보 확인 화면(아래 single/several)으로도 가지 않는다
    # — `_prompt_candidate_or_reject`/`_read_single_confirmation`은 후보가
    # 있을 때만 의미가 있고, 이 갈래는 애초에 후보가 0개다.
    if tier == "no_check":
        print("판정 없이 이야기를 이어갑니다.")
        return await _proceed_without_check(store, actor, args, declare_seq=declare_seq, rulebook=rulebook)

    if tier == "single":
        (candidate,) = proposal.candidates
        confirmed = _read_single_confirmation(candidate)
        suggestion = candidate
        picked = candidate
    else:  # tier == "several" — 후보가 2개 이상인 유일한 남은 갈래
        candidates = proposal.candidates
        suggestion = candidates[0]  # 시스템이 처음 내민 것 — 사람이 뭘 고르든 안 바뀐다
        chosen = _prompt_candidate_or_reject(candidates)
        confirmed = chosen is not None
        # 거부(`n`)해도 picked는 비워두지 않고 suggestion으로 채운다 — `single`
        # 갈래와 같은 이유다: 아래 ConfirmAction은 confirmed=False일 때도
        # move/stat 값이 필요하고, 판정은 어차피 `if not confirmed: return 0`에서
        # 걸러진다(IN-03). "거부됐는데 왜 무브가 채워지나"는 착각을 막기 위한 주석.
        picked = chosen if chosen is not None else suggestion

    confirm_seq = await actor.submit(
        ConfirmAction(
            player_id=args.player,
            move=picked.move,
            stat=picked.stat,
            system_suggestion={"move": suggestion.move, "stat": suggestion.stat},
            player_confirmed=confirmed,
            caused_by_seq=declare_seq,
        )
    )

    if not confirmed:
        return 0

    # ④ 판정 — 결과 줄을 화면에 찍는다. 서사 호출은 아직 시작하지 않았다.
    #
    # person_id/character_id(판 5+, TRUST-04)는 CLI에 브라우저 쿠키 신원
    # 개념이 없으므로 args.player를 그대로 두 칸에 쓴다 — D-42가 이 CLI
    # 경로에서는 여전히 유효한 전제다(신원 분리는 웹 계층의 서명 쿠키에서만
    # 의미가 있다, D-03). D-02 — 바깥에서 자유 수정치/목표값을 안 받는다.
    # `--difficulty`가 유일한 통로이고, 그 이름을 룰북 선언에서 찾는 것은
    # `_prepare_resolve_check`(session_actor)가 한다 — 없는 이름이면
    # `UnknownDifficultyLevel` -> `CommandRejected`가 되어 `_cmd_turn`의
    # except 절이 0이 아닌 종료 코드로 끝맺는다(사건은 하나도 안 쌓인다).
    resolve_seq = await actor.submit(
        ResolveCheck(
            move=picked.move,
            modifiers=(),
            rulebook_id=args.rulebook,
            caused_by_seq=confirm_seq,
            person_id=args.player,
            character_id=args.player,
            difficulty=args.difficulty,
        )
    )
    check_event = store.read_events(args.session, from_seq=resolve_seq)[0]
    print(f"판정: 눈 {check_event.rolls} 등급 {check_event.grade} 목표 {check_event.target}")

    check_summary = f"{picked.move} 판정 결과 {check_event.grade} (목표 {check_event.target})"

    # 이 등급의 밴드(D-13/D-14) — `costs`가 결과 목록을 태울지 정한다.
    # `check_event.grade`는 `_prepare_resolve_check`가 이미 룰북 선언에서
    # 뽑은 이름이므로(`web/routes_actions.py`의 `confirm()`과 같은 근거) 여기서
    # `UnknownGradeName`이 나는 것은 룰북 데이터 자체가 등록 뒤에 바뀐
    # 경우뿐이다 — 조용히 넘기지 않되, 이미 판정 결과 줄은 화면에 찍혔으므로
    # (D-08과 같은 이유) 여기서부터 사람이 읽을 오류로 끝맺는다.
    try:
        grade_band = require_band(rulebook.grade_bands, check_event.grade)
    except UnknownGradeName as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1

    # `TurnContext`를 다시 접는다(CR-02 리뷰 발견) — 웹 경로
    # (`web/routes_actions.py`의 `confirm()`, 455~461줄)와 정확히 같은 이유다:
    # `ResolveCheck` 처리 중 실패 횟수 자동 진행(fail-counter auto-advance)이
    # 시계를 이미 옮겼을 수 있다(`docs/PIPELINE.md` §2 "⑤ build_turn_context()
    # 재호출 ← 시계·최근 대화가 ③에서 바뀌었으므로 다시 접는다"). 판정 전에
    # 만든 `ctx`(192줄)를 그대로 아래 세 판단(`gather_turn_judgments`)·서사
    # (`build_narration_facts`)·배경 시계 조건 검사(`run_clock_condition_check`)에
    # 넘기면 이 판정 자신이 옮긴 시계 위치를 놓친 채로 판단하게 된다 — 웹과
    # 똑같이 여기서도 다시 접어 뒤 구간에 넘긴다. 파티 인자는 여전히 안
    # 넘긴다(12-05) — 명령줄에는 캐릭터 선택 개념이 없다는 전제는 그대로다.
    ctx = _build_turn_context(store, args.session, args.rulebook)

    # 상황판단·장면 신규 대상 판단·시계 신호 관문을 narrate() 호출 **전**에
    # 병렬로 부른다(ARCH-04). 웹과 달리 여기서는 이벤트 루프를 막아도 되는
    # 자리가 아니다(액터의 큐 소비 태스크가 같은 루프에 있다) —
    # `gather_turn_judgments` 내부가 이미 `asyncio.to_thread`로 세 판단을
    # 작업 스레드로 내보낸다. 이 구간 전체를 `try`로 감싸 실패 시 stderr
    # 한 줄만 남기고 빈 판단으로 계속 간다(D-05) — 판단이 실패해도
    # `_turn_flow`의 종료 코드는 영향받지 않는다. **제공자 구성
    # (`resolve_provider` 호출) 자체도 이 `try` 안에 있다(CR-01 리뷰 발견)** —
    # 웹 경로(`routes_actions.py`)의 `master_gm` 제공자 구성과 같은 이유로,
    # 이 세 역할의 구성 실패도 판단 *호출* 실패와 똑같이 처리돼야 한다: 이미
    # 굴린 주사위(`ResolveCheck`)를 버리지 않고 빈 판단으로 계속 간다.
    # `_resolve_role_choice`는 예외를 던지지 않는 저장/CLI 인자 조회이므로
    # `try` 밖에 남긴다 — 아래 `RecordAiCall`이 성공/실패 어느 쪽에서도
    # `*.model`/`*.provider`를 읽어야 하기 때문이다.
    situation_judge_choice = _resolve_role_choice(args, "situation_judge")
    entity_judge_choice = _resolve_role_choice(args, "scene_entity_judge")
    clock_judge_choice = _resolve_role_choice(args, "clock_judge")
    outcome_judge_choice = _resolve_role_choice(args, "outcome_picker")
    try:
        situation_provider = resolve_provider(
            "situation_judge", {"situation_judge": situation_judge_choice}, os.environ
        )
        entity_provider = resolve_provider(
            "scene_entity_judge", {"scene_entity_judge": entity_judge_choice}, os.environ
        )
        clock_provider = resolve_provider(
            "clock_judge", {"clock_judge": clock_judge_choice}, os.environ
        )
        outcome_provider = resolve_provider(
            "outcome_picker", {"outcome_picker": outcome_judge_choice}, os.environ
        )
        judgments = await gather_turn_judgments(
            situation_provider=situation_provider,
            situation_model=situation_judge_choice.model,
            entity_provider=entity_provider,
            entity_model=entity_judge_choice.model,
            clock_provider=clock_provider,
            clock_model=clock_judge_choice.model,
            outcome_provider=outcome_provider,
            outcome_model=outcome_judge_choice.model,
            ctx=ctx,
            check_summary=check_summary,
            rulebook_display_name=rulebook.display_name,
            outcome_list=rulebook.outcome_list,
            grade_band=grade_band,
            resource_axes=rulebook.resource_axes,
        )
    except Exception as exc:  # noqa: BLE001 - D-05, 판단(및 그 제공자 구성)이 실패해도 턴을 막지 않는다
        print(
            f"경고: 상황판단/장면 신규 대상/시계 신호/결과 선택 판단이 실패했다 (seq {resolve_seq}) — {exc}",
            file=sys.stderr,
        )
        judgments = empty_turn_judgments()
        # 제공자 구성이 실패했을 수 있으므로 아래 배경 시계 조건 검사 호출에서
        # 이 변수를 참조하기 전에 안전한 값으로 되돌린다 — `judgments.clock.should_check`는
        # `empty_turn_judgments()`에서 항상 False이므로 실제로 쓰이지는 않지만,
        # unbound 변수를 남겨 두지 않는다(CR-01, `web/routes_actions.py`와 동일).
        clock_provider = None

    # 새 에이전트 호출 셋의 기록 — 성공·실패 어느 쪽에서도 항상 제출한다
    # (MEAS-02, 아래 `master_gm` 호출 기록과 같은 규율).
    await actor.submit(
        RecordAiCall(
            agent_role="situation_judge",
            model=situation_judge_choice.model,
            provider=situation_judge_choice.provider,
            prompt_tokens=judgments.situation.ai.prompt_tokens,
            completion_tokens=judgments.situation.ai.completion_tokens,
            cached_prompt_tokens=judgments.situation.ai.cached_prompt_tokens,
            latency_ms=judgments.situation.ai.elapsed_ms,
            caused_by_seq=confirm_seq,
        )
    )
    await actor.submit(
        RecordAiCall(
            agent_role="scene_entity_judge",
            model=entity_judge_choice.model,
            provider=entity_judge_choice.provider,
            prompt_tokens=judgments.entity.ai.prompt_tokens,
            completion_tokens=judgments.entity.ai.completion_tokens,
            cached_prompt_tokens=judgments.entity.ai.cached_prompt_tokens,
            latency_ms=judgments.entity.ai.elapsed_ms,
            caused_by_seq=confirm_seq,
        )
    )
    await actor.submit(
        RecordAiCall(
            agent_role="clock_judge",
            model=clock_judge_choice.model,
            provider=clock_judge_choice.provider,
            prompt_tokens=judgments.clock.ai.prompt_tokens,
            completion_tokens=judgments.clock.ai.completion_tokens,
            cached_prompt_tokens=judgments.clock.ai.cached_prompt_tokens,
            latency_ms=judgments.clock.ai.elapsed_ms,
            caused_by_seq=confirm_seq,
        )
    )
    await actor.submit(
        RecordAiCall(
            agent_role="outcome_picker",
            model=outcome_judge_choice.model,
            provider=outcome_judge_choice.provider,
            prompt_tokens=judgments.outcome.ai.prompt_tokens,
            completion_tokens=judgments.outcome.ai.completion_tokens,
            cached_prompt_tokens=judgments.outcome.ai.cached_prompt_tokens,
            latency_ms=judgments.outcome.ai.elapsed_ms,
            caused_by_seq=confirm_seq,
        )
    )

    # 자원 변화 확인 관문(12-06, D-09/D-10) — 웹의
    # `POST .../confirm-resource-change`와 같은 뜻을 명령줄 방식으로 밟는다.
    # 새 HTTP 왕복을 만들지 않는다 — CLI는 이미 액터에 직접 접근하는
    # 단일 프로세스이므로, 웹이 하는 「코드가 다시 대조 -> 사람 확인 ->
    # 서버가 다시 굴려 적용」을 이 함수 안에서 그대로 한다. **확인 없이
    # 자원이 깎이는 경로가 CLI에만 열려 있으면 안 된다**(10-05 관례,
    # 이 계획의 웹·CLI 짝 수정 원칙).
    if judgments.outcome.category_ids:
        try:
            picked_categories = ordered_categories(rulebook.outcome_list, judgments.outcome.category_ids)
        except Exception as exc:  # noqa: BLE001 - T-12-27, 목록 밖 결과가 와도 턴을 막지 않는다
            print(
                f"경고: outcome_picker가 닫힌 목록과 어긋난 결과를 냈다 (seq {resolve_seq}) — {exc}",
                file=sys.stderr,
            )
            picked_categories = ()
        pending_changes = [
            change for category in picked_categories for change in category.changes
        ]
        if pending_changes:
            print("자원 변화 제안:")
            for change in pending_changes:
                print(f"  - {change.axis} {change.operation} {change.amount}")
            print("[Enter=확인 / n=아니오]")
            answer = input().strip().lower()
            if answer not in ("n", "no"):
                roller = LiveRoller()
                ops = tuple(
                    ResourceOp(axis=decl.axis, operation=decl.operation, amount=rolled, rolls=rolls)
                    for decl in pending_changes
                    for rolled, rolls in (roll_amount(roller, decl.amount),)
                )
                try:
                    await actor.submit(
                        RecordResourceChange(
                            character_id=args.player,
                            changes=ops,
                            source="outcome_list",
                            caused_by_seq=resolve_seq,
                        )
                    )
                except AlreadyChanged:
                    pass  # 재시도 — 이미 기록된 변화를 다시 깎지 않는다.
            else:
                print("자원 변화를 적용하지 않습니다.")
    elif not rulebook.outcome_list.categories and grade_band.costs:
        # RULE-10 — 결과 목록이 없어도 재량 판정 여지가 있다는 것만
        # 안내한다. 실제 제안(축·동작·양)을 만드는 AI 호출은 이 계획의
        # 파일 범위(agents/*를 안 건드린다) 밖이라 만들지 않는다 — 알려진
        # 갭(차단 아님, SUMMARY.md 참조).
        eligible_axes = [axis.name for axis in rulebook.resource_axes if axis.form != "none"]
        print(
            "안내: 이 룰북은 결과 목록이 없어 재량 판정 여지가 있습니다 "
            f"(가능한 축: {', '.join(eligible_axes) if eligible_axes else '없음'})."
        )

    facts = build_narration_facts(ctx=ctx, check_summary=check_summary, judgments=judgments)

    gm_choice = _resolve_role_choice(args, "master_gm")
    gm_provider = resolve_provider("master_gm", {"master_gm": gm_choice}, os.environ)

    # ⑤ 서사 — 판정 결과를 찍은 **뒤에야** 시작한다. 첫 조각을 기다리는 동안만
    # 진행 표시를 건다(확인 -> 서사 첫 글자, MEAS-02의 두 번째 지점).
    #
    # 예외 포착은 AI 스트림 자체(narrate() 생성/첫 조각/이후 조각 이어받기)만
    # 감싼다 — 어떤 이유로든(90초 정지 워치독의 TimeoutError 포함) 서사가
    # 실패해도 raw traceback으로 죽지 않는다(G-03-3). `Exception`만 잡는다 —
    # `KeyboardInterrupt` 같은 `BaseException`은 그대로 통과시켜 사용자의
    # 중단 의사를 가로채지 않는다. **되감지 않는다** — 이미 나온 문장은
    # 지금처럼 나오는 족족 그 자리에서 `AppendNarration`으로 제출한다.
    #
    # `actor.submit(AppendNarration(...))`는 **이 try 밖**에 둔다(WR-01) —
    # 이 호출이 던지는 예외는 이벤트 스키마·저장소 I/O 같은 액터/저장소
    # 계층의 결함이지 서사 실패가 아니다. 같은 낙하 경로로 모으면 "서사가
    # 끝까지 나오지 못했다"는 문구가 실제로는 다른 종류의 버그를 가리는
    # 결과가 된다 — 그대로 전파시켜 진짜 원인이 드러나게 둔다.
    narration_start = time.monotonic()
    narration_error: Exception | None = None
    chunk_index = 0
    narration_texts: list[str] = []
    """이번 턴에 실제로 화면에 나간 서사 조각을 모아 둔다 — 배경 시계 조건
    검사가 서사가 끝난 뒤의 `narration_text`로 이걸 이어 붙여 받는다(웹과
    같은 방식)."""
    try:
        narration_iter = narrate(
            provider=gm_provider,
            model=gm_choice.model,
            facts=facts,
            rulebook_display_name=rulebook.display_name,
            resource_axes=rulebook.resource_axes,
        )
        first_sentence = with_progress_dots(
            lambda: next(narration_iter, _NO_SENTENCE),
            threshold_s=args.progress_after,
            tick_s=args.progress_tick,
        )
    except Exception as exc:  # noqa: BLE001 - 서사 스트림 생성/첫 조각 실패만 여기서 잡는다(G-03-3)
        narration_error = exc
        first_sentence = _NO_SENTENCE

    if first_sentence is not _NO_SENTENCE:
        await _submit_narration_chunk(  # 액터/저장소 결함은 여기서 그대로 터진다(WR-01)
            actor=actor,
            chunk=first_sentence,
            chunk_index=chunk_index,
            resolve_seq=resolve_seq,
            narration_texts=narration_texts,
        )
        chunk_index += 1
        while True:
            try:
                sentence = next(narration_iter)
            except StopIteration:
                break
            except Exception as exc:  # noqa: BLE001 - 서사 스트림 이어받기 실패만 여기서 잡는다(G-03-3)
                narration_error = exc
                break
            await _submit_narration_chunk(  # 액터/저장소 결함은 여기서 그대로 터진다(WR-01)
                actor=actor,
                chunk=sentence,
                chunk_index=chunk_index,
                resolve_seq=resolve_seq,
                narration_texts=narration_texts,
            )
            chunk_index += 1

    # ⑥ 두 번째 AI 호출 기록 — 성공·실패 어느 쪽에서도 항상 제출한다. 실패한
    # 호출도 걸린 시간이 남아야 MEAS-02의 두 번째 지점(확인 -> 서사 첫 글자)에서
    # 실패한 턴이 통째로 빠지지 않는다(T-03-06-04).
    #
    # 이 제출 자체도 자기만의 try/except로 감싼다(WR-02) — G-03-3의 목표는
    # "이 함수에서 raw traceback이 새어 나가지 않는다"였는데, narrate() 실패
    # 처리부만 감싸고 이 "항상 제출한다" 기록 제출은 감싸지 않으면 같은 종류의
    # 결함(이벤트 스키마·저장소 I/O)이 한 호출 뒤에서 그대로 새 나간다. 서사
    # 실패와는 다른 결함이므로 narration_error 낙하 경로에 섞지 않고, 여기서
    # 바로 그 자리에서 사람이 읽을 오류로 끝맺는다.
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
                cached_prompt_tokens=gm_result.cached_prompt_tokens,
                latency_ms=gm_result.elapsed_ms,
                caused_by_seq=confirm_seq,
            )
        )
    except Exception as exc:  # noqa: BLE001 - "항상 제출한다" 기록 제출 실패도 raw traceback으로 새면 안 된다(WR-02)
        print(f"오류: 진행자 AI 호출 기록 제출이 실패했다 — {exc}", file=sys.stderr)
        return 1

    if narration_error is not None or not gm_result.ok:
        # 「무브 없음」 문구를 재사용하지 않는다 — 여기까지 왔다는 것은 무브가
        # 확인됐고 판정이 실제로 굴러갔고 그 결과 줄이 이미 화면에 찍혔다는
        # 뜻이다. 서사만 실패했다는 것이 드러나는 문구를 쓴다. 예외 객체의
        # 메시지만 붙인다 — 호출 스택이나 제공자 설정을 화면에 쏟지 않는다.
        reason = str(narration_error) if narration_error is not None else "제공자가 last_result() 규약을 어겼다"
        print(f"오류: 서사가 끝까지 나오지 못했다 — {reason}", file=sys.stderr)
        return 1

    if judgments.clock.should_check and clock_provider is not None:
        # `clock_provider is not None`도 함께 확인한다(CR-01) — 위 제공자
        # 구성이 실패했으면 `judgments.clock.should_check`가 항상 False이므로
        # 이 조건은 방어적 이중 확인이지만, `clock_provider`가 unbound인 채로
        # 아래에서 참조되는 경로를 코드로도 남겨 두지 않는다
        # (`web/routes_actions.py`와 동일한 이유).
        #
        # **CLI/웹 비대칭(Pitfall 1)** — 웹은 응답을 보낸 뒤 `BackgroundTasks`로
        # 시계 조건 검사를 던지지만, CLI는 `asyncio.run()`이 반환하는 순간
        # 이벤트 루프가 닫히므로 "응답 후 배경"이 성립하지 않는다. 여기서
        # 반드시 `await`로 끝내야 한다 — `run_turn`의 `finally: await
        # actor.stop()`보다 먼저다. `asyncio.create_task`로 던지고 기다리지
        # 않으면 프로세스가 곧 끝나 배경 산출물이 스케줄되다 말거나 아예
        # 스케줄되지 못한 채 사라지고, ARCH-03이 CLI 경로에서 조용히 깨진다.
        await run_clock_condition_check(
            actor=actor,
            provider=clock_provider,
            model=clock_judge_choice.model,
            judge_ctx=build_clock_judge_context(ctx, check_summary),
            rulebook_display_name=rulebook.display_name,
            narration_text="\n".join(narration_texts),
            resolve_seq=resolve_seq,
            clock_id=ctx.clock_state.clock_id,
            clock_segment_count=CLOCK_SEGMENT_COUNT,
        )

    return 0


async def run_turn(store: EventStore, args: argparse.Namespace) -> int:
    """`turn` 하위 명령의 진입점 — 세션 액터를 준비하고 `_turn_flow`에 맡긴다."""
    registry = SessionRegistry(store)
    actor = registry.get_or_create(args.session)
    try:
        return await _turn_flow(store, actor, args)
    finally:
        await actor.stop()
