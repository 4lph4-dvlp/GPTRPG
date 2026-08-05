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
from gptrpg.agents.envelope import AgentResult
from gptrpg.agents.master_gm import narrate
from gptrpg.agents.providers.base import Provider
from gptrpg.event_log.store import EventStore
from gptrpg.rulebooks import get_rulebook
from gptrpg.rulebooks.moves import get_moves
from gptrpg.rules_core.resolution import Modifier
from gptrpg.session_actor.actor import (
    AppendNarration,
    ConfirmAction,
    DeclareAction,
    RecordAiCall,
    ResolveCheck,
    SessionActor,
    SessionRegistry,
)
from gptrpg.turn.context import build_turn_context

_T = TypeVar("_T")

_NO_SENTENCE = object()
"""narrate()의 첫 조각을 기다릴 때 쓰는 보초값. `chunk_sentences`는 빈
문자열을 절대 내보내지 않으므로 이 값과의 신원 비교로 "아직 하나도 안
나왔다"를 안전하게 구분할 수 있다."""


def _parse_modifier(raw: str) -> Modifier:
    """'유형:값:출처' 형태의 --modifier 문자열 하나를 Modifier로 바꾼다."""
    parts = raw.split(":", 2)
    if len(parts) != 3:
        raise ValueError(f"modifier 형식은 '유형:값:출처'여야 한다: {raw!r}")
    mod_type, value, source = parts
    return Modifier(type=mod_type, value=int(value), source=source)


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

    tier = proposal.tier

    # ③ 세 갈래 확인 화면 — 어느 갈래에서도 사람 입력 없이 다음으로 못 넘어간다
    if tier == "none":
        # 되돌리기 전용 화면을 만들지 않는다 — ConfirmAction 자체를 제출하지
        # 않는다. 「확인 사건 없는 선언 사건」이 곧 「직접 찾아야 함」 사례의
        # 기록이다 (D-29, D-36, HYP-04의 세 번째 칸).
        print("무브 없음 — 판정 없이 진행합니다. 필요하면 다음 턴에 roll 명령을 직접 쓰세요.")
        return 0

    if tier == "single":
        (candidate,) = proposal.candidates
        confirmed = _read_single_confirmation(candidate)
        suggestion = candidate
        picked = candidate
    else:  # tier == "several"
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
    modifiers = tuple(_parse_modifier(raw) for raw in args.modifier)
    resolve_seq = await actor.submit(
        ResolveCheck(
            move=picked.move,
            modifiers=modifiers,
            target=args.target,
            rulebook_id=args.rulebook,
            caused_by_seq=confirm_seq,
        )
    )
    check_event = store.read_events(args.session, from_seq=resolve_seq)[0]
    print(f"판정: 눈 {check_event.rolls} 등급 {check_event.grade} 목표 {check_event.target}")

    check_summary = f"{picked.move} 판정 결과 {check_event.grade} (목표 {check_event.target})"

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
    try:
        narration_iter = narrate(
            provider=gm_provider,
            model=gm_choice.model,
            ctx=ctx,
            check_summary=check_summary,
            rulebook_display_name=rulebook.display_name,
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
        print(first_sentence)
        await actor.submit(  # 액터/저장소 결함은 여기서 그대로 터진다(WR-01)
            AppendNarration(
                text=first_sentence, chunk_index=chunk_index, caused_by_seq=resolve_seq
            )
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
            print(sentence)
            await actor.submit(  # 액터/저장소 결함은 여기서 그대로 터진다(WR-01)
                AppendNarration(
                    text=sentence, chunk_index=chunk_index, caused_by_seq=resolve_seq
                )
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

    return 0


async def run_turn(store: EventStore, args: argparse.Namespace) -> int:
    """`turn` 하위 명령의 진입점 — 세션 액터를 준비하고 `_turn_flow`에 맡긴다."""
    registry = SessionRegistry(store)
    actor = registry.get_or_create(args.session)
    try:
        return await _turn_flow(store, actor, args)
    finally:
        await actor.stop()
