"""submit / replay 두 하위 명령. 이 파일에는 게임 규칙이 한 줄도 없다.

인자를 명령 객체로 바꾸고, 세션 액터를 부르고, 상태를 글자로 바꾸는 일만 한다.
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

from gptrpg.agents.action_classifier import UnknownMove
from gptrpg.agents.config import (
    AGENT_ROLES,
    DEFAULT_CONFIG_PATH,
    AgentChoice,
    ConfigNotFound,
    InvalidAgentConfig,
    load_config,
    load_partial_config,
    save_config,
)
from gptrpg.agents.providers import (
    PROVIDER_ENV_VARS,
    MissingApiKey,
    ProviderNotImplemented,
    UnknownProvider,
    available_providers,
    get_provider,
)
from gptrpg.cli.turn_flow import _parse_modifier, run_turn
from gptrpg.cli.turn_flow import _build_turn_context as _build_turn_context
from gptrpg.event_log.store import EventStore, SequenceConflict
from gptrpg.rules_core.grading import DEFAULT_TARGET
from gptrpg.rulebooks import UnknownRulebook
from gptrpg.rulebooks.dungeonworld_like import DUNGEONWORLD_LIKE_ID
from gptrpg.session_actor.actor import (
    AdvanceClock,
    AppendNarration,
    Command,
    CommandRejected,
    ConfirmAction,
    DeclareAction,
    RecordAiCall,
    ResolveCheck,
    SessionRegistry,
)
from gptrpg.session_actor.projection import rebuild_state, rebuild_state_from_events
from gptrpg.session_actor.report import DEFAULT_REPORTS_DIR, UnsafeSessionId, build_report, write_report

# `_build_turn_context`는 이제 `turn_flow`가 소유하지만, `tests/test_turn_tracer.py`가
# `from gptrpg.cli.main import _build_turn_context`로 이 이름을 계속 찾는다 — 위
# import가 그 이름을 이 모듈의 네임스페이스로 다시 노출한다 (단방향 재노출,
# 순환 import 없음: `turn_flow`는 `main`을 전혀 모른다).


def _build_command(args: argparse.Namespace) -> Command:
    """submit 하위 명령(선택된 갈래)의 인자를 대응하는 Command 객체로 바꾼다."""
    kind = args.submit_command
    if kind == "declare":
        return DeclareAction(player_id=args.player, raw_text=args.text)
    if kind == "confirm":
        return ConfirmAction(
            player_id=args.player,
            move=args.move,
            stat=args.stat,
            system_suggestion={"move": args.suggestion, "stat": args.stat},
            player_confirmed=args.confirmed,
            caused_by_seq=args.caused_by,
        )
    if kind == "roll":
        modifiers = tuple(_parse_modifier(raw) for raw in args.modifier)
        return ResolveCheck(
            move=args.move,
            modifiers=modifiers,
            target=args.target,
            rulebook_id=args.rulebook,
            caused_by_seq=args.caused_by,
        )
    if kind == "narrate":
        return AppendNarration(
            text=args.text, chunk_index=args.chunk, caused_by_seq=args.caused_by
        )
    if kind == "clock":
        return AdvanceClock(
            clock_id=args.clock_id,
            segment_index=args.segment,
            trigger=args.trigger,
            caused_by_seq=args.caused_by,
        )
    if kind == "ai":
        return RecordAiCall(
            agent_role=args.role,
            model=args.model,
            provider=args.provider,
            prompt_tokens=args.prompt_tokens,
            completion_tokens=args.completion_tokens,
            cached_prompt_tokens=args.cached_prompt_tokens,
            latency_ms=args.latency_ms,
            caused_by_seq=args.caused_by,
        )
    raise ValueError(f"알 수 없는 submit 하위 명령: {kind!r}")


async def _run_submit(store: EventStore, session_id: str, command: Command) -> int:
    registry = SessionRegistry(store)
    actor = registry.get_or_create(session_id)
    try:
        return await actor.submit(command)
    finally:
        await actor.stop()


def _cmd_submit(args: argparse.Namespace) -> int:
    try:
        command = _build_command(args)
    except ValueError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1

    store = EventStore(args.db)
    store.initialize()
    try:
        seq = asyncio.run(_run_submit(store, args.session, command))
    except (CommandRejected, SequenceConflict) as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1
    finally:
        store.close()

    print(seq)
    return 0


def _cmd_replay(args: argparse.Namespace) -> int:
    store = EventStore(args.db)
    store.initialize()
    try:
        state = rebuild_state(store, args.session)
    finally:
        store.close()

    # 실행할 때마다 달라지는 값(실행 시각·소요 시간)은 넣지 않는다 —
    # 같은 기록을 두 번 재생하면 항상 같은 글자가 나와야 한다.
    print(f"세션: {args.session}")
    print(f"기록 파일: {args.db}")
    print(f"사건 수: {state.last_seq + 1}")
    print(f"턴 수: {state.turn_count}")
    print(f"판정 수: {state.check_count}")
    print(f"판정 실패 수: {state.failure_count}")
    print(f"위협 시계 현재 칸: {state.clock_segment}")
    print(f"시계 진행 횟수: {state.clock_advances}")
    print(f"서사 조각 수: {state.narration_count}")
    print(f"AI 호출 수: {state.ai_calls}")
    print(f"토큰 합계: {state.total_tokens}")
    print(f"마지막 판정 등급: {state.last_grade}")
    return 0


def _print_latency_section(latency: dict) -> None:
    """MEAS-02 두 지점을 사람이 읽을 줄로 찍는다.

    문턱 초과 횟수를 함께 찍는 이유: D-33이 정한 것은 목표값 두 개(0.5초·2초)와
    **초과 시 행동** 두 개(5초 진행 표시·15초 판정 우선)이므로, 실제로 그
    행동이 몇 번 발동했는지가 판정에 쓰이는 숫자다.
    """
    print("\n[응답 속도 — MEAS-02]")
    confirm_to_narration = latency["confirm_to_first_narration"]
    if confirm_to_narration["sample_count"] == 0:
        print("  확인 -> 서사 첫 글자: 표본 없음")
    else:
        print(
            f"  확인 -> 서사 첫 글자 (목표 2초): "
            f"중앙값 {confirm_to_narration['median_ms']}ms · "
            f"최대 {confirm_to_narration['max_ms']}ms · "
            f"표본 {confirm_to_narration['sample_count']}개 · "
            f"5초 초과 {confirm_to_narration['over_5s']}회 · "
            f"15초 초과 {confirm_to_narration['over_15s']}회"
        )
    for role, summary in latency["by_agent_role"].items():
        print(
            f"  {role} 호출: 중앙값 {summary['median_ms']}ms · "
            f"최대 {summary['max_ms']}ms · 표본 {summary['sample_count']}개 · "
            f"5초 초과 {summary['over_5s']}회 · 15초 초과 {summary['over_15s']}회"
        )


def _print_friction_section(friction: dict) -> None:
    """HYP-04 마찰 3분류를 사람이 읽을 줄로 찍는다.

    **판정하지 않고 숫자만 찍는다.** HYP-04의 문턱(95% / 30%)은 사람이 라벨을
    다시 붙인 뒤 Phase 6이 판정한다 — 여기서 「통과」라고 찍으면 자동 계산한
    값이 최종 판정으로 읽힌다.
    """
    print("\n[자유 텍스트 마찰 — HYP-04 원자료]")
    total = friction["declared_total"]
    if total == 0:
        print("  선언된 행동 없음")
        return
    print(f"  선언된 행동: {total}개")
    print(f"  첫 제안이 맞음 (엔터 한 번): {friction['accepted_as_is']}개")
    print(f"  후보에 있었음 (클릭 한 번): {friction['picked_other']}개")
    print(f"  어디에도 없음 (직접 찾아야 함): {friction['no_candidate']}개")
    print(f"  앞 둘 합계 비율: {friction['frictionless_ratio']:.3f} (HYP-04 문턱 0.95)")
    print(f"  세 번째 비율: {friction['unmatched_ratio']:.3f} (HYP-04 문턱 0.30 미만)")
    print("  * 사람이 라벨을 다시 붙인 뒤 Phase 6이 판정한다 — 이 숫자는 원자료다")


def _print_episodes_section(episodes: list[dict]) -> None:
    """시계 칸별 누적 스냅샷 — 「무료로 주는 1~2칸이 얼마짜리인가」의 입력값.

    세션 합계만으로는 이 값이 안 나온다. D20·D21이 확정한 상품 단위가
    「첫 에피소드(1~2칸)」이고 무료로 나눠 주는 몫도 그것이라, 세션이 3칸까지
    갔으면 합계에는 무료 구간 밖의 몫이 섞여 있다.
    """
    print("\n[시계 칸별 누적 — D20·D21의 상품 단위]")
    if not episodes:
        print("  시계가 한 번도 진행되지 않음 (무료 구간 원가를 아직 가를 수 없다)")
        return
    for milestone in episodes:
        elapsed = milestone["elapsed_ms"]
        elapsed_text = "시각 불명" if elapsed is None else f"{elapsed / 60000:.1f}분"
        print(
            f"  {milestone['segment_index']}칸 도달 ({milestone['trigger']}): "
            f"{elapsed_text} · 행동 {milestone['turn_count']} · 판정 {milestone['check_count']} · "
            f"실패 {milestone['failure_count']} · "
            f"입력 {milestone['prompt_tokens']}(캐시 {milestone['cached_prompt_tokens']}) · "
            f"출력 {milestone['completion_tokens']}"
        )
    print("  * 1~2칸 줄의 값이 「첫 에피소드 무료」의 원가 입력이다 (채점 규칙 §5)")


def _cmd_report(args: argparse.Namespace) -> int:
    store = EventStore(args.db)
    store.initialize()
    try:
        # 사건 목록을 한 번 읽어 상태와 집계 둘 다에 쓴다. 이 명령은 어차피
        # 전체를 읽으므로 `latency`/`friction`까지 계산해 넘긴다 — 액터의
        # 자동 저장 훅은 이 두 칸을 채우지 않는다(사건마다 전체를 다시 읽으면
        # 비용이 세션 길이의 제곱이 된다, `build_report` 도크스트링 참조).
        events = store.read_events(args.session)
        state = rebuild_state_from_events(args.session, events)
    finally:
        store.close()

    try:
        report = build_report(state, events=events)

        # 라벨은 `_cmd_replay`가 이미 쓰는 이름을 그대로 재사용한다 —
        # 같은 숫자에 두 개의 이름을 만들지 않는다.
        print(f"세션: {args.session}")
        print(f"집계 생성 시각: {report['generated_at']}")
        print(f"사건 수: {report['event_count']}")
        print(f"턴 수: {report['turn_count']}")
        print(f"판정 수: {report['check_count']}")
        print(f"판정 실패 수: {report['failure_count']}")
        print(f"위협 시계 현재 칸: {report['clock_segment']}")
        print(f"시계 진행 횟수: {report['clock_advances']}")
        ratio = report["failure_to_clock_ratio"]
        if ratio is None:
            print("실패 대비 시계 진행 비율: 시계가 한 번도 진행되지 않음")
        else:
            print(f"실패 대비 시계 진행 비율: {ratio}")
        print(f"서사 조각 수: {report['narration_count']}")
        print(f"AI 호출 수: {report['ai_calls']}")
        print(f"토큰 합계: {report['total_tokens']}")

        # **입력·출력을 나눠 찍는다.** 합계 하나로는 원가를 계산할 수 없다 —
        # 두 단가가 보통 4~5배 다르다. 캐시 적중 몫은 입력의 부분집합이며,
        # 0이면 「적중 없음」과 「제공자가 보고하지 않음」이 구분되지 않으므로
        # 그때의 원가는 상한선으로 읽어야 한다(H5 판정 규칙).
        print(f"  입력 토큰: {report['prompt_tokens']}")
        print(f"  출력 토큰: {report['completion_tokens']}")
        cached = report["cached_prompt_tokens"]
        prompt_total = report["prompt_tokens"]
        if prompt_total:
            print(f"  그중 캐시 적중 입력 토큰: {cached} ({cached / prompt_total:.1%})")
        else:
            print(f"  그중 캐시 적중 입력 토큰: {cached}")
        if cached == 0:
            print("  * 캐시 적중이 0이다 — 「적중 없음」과 「제공자 미보고」가 구분되지 않으므로")
            print("    이 세션의 원가는 캐시 0% 가정의 상한선으로 읽어야 한다")
        print(f"마지막 판정 등급: {report['last_grade']}")

        _print_latency_section(report["latency"])
        _print_friction_section(report["friction"])
        _print_episodes_section(report["episodes"])

        # 조회와 저장을 한 번에 한다(D-44) — 운영자가 조회할 때마다 파일도
        # 최신으로 갱신되므로, 조회 명령을 한 번이라도 친 세션은 Phase 5·6이
        # 쓸 파일이 반드시 남는다.
        path = write_report(
            state,
            base_dir=Path(args.out_dir),
            generated_at=report["generated_at"],
            events=events,
        )
        print(f"\n집계 파일: {path}")
    except UnsafeSessionId as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1
    return 0


def _prompt_numbered_choice(options: list[str], label: str) -> str:
    """번호 목록에서 하나를 고르게 한다. 범위를 벗어난 입력은 다시 묻는다."""
    while True:
        raw = input(f"{label} (번호): ").strip()
        if raw.isdigit():
            index = int(raw)
            if 1 <= index <= len(options):
                return options[index - 1]
        print(f"1에서 {len(options)} 사이의 번호를 입력하세요.")


def _select_one_role(role: str, env: dict[str, str]) -> AgentChoice | None:
    """한 역할의 제공자·모델 두 단계 선택 화면. 실패하면 None(호출한 쪽이 종료 코드를 낸다)."""
    available = available_providers(env)
    if not available:
        env_names = ", ".join(sorted(PROVIDER_ENV_VARS.values()))
        print(
            f"오류: 사용 가능한 제공자가 없다. 다음 환경 변수 중 하나를 채우세요: {env_names}",
            file=sys.stderr,
        )
        return None

    print(f"\n[{role}] 제공자를 고르세요:")
    for i, name in enumerate(available, start=1):
        print(f"  {i}. {name}")
    provider_name = _prompt_numbered_choice(available, "제공자")

    provider = get_provider(provider_name, env)
    try:
        models = provider.list_models()
    except Exception as exc:  # noqa: BLE001 - 사람이 읽을 한 줄 메시지로 바꿔 그대로 종료한다
        print(f"오류: {provider_name!r} 모델 목록 조회 실패 — {exc}", file=sys.stderr)
        return None
    if not models:
        print(f"오류: {provider_name!r}가 모델을 하나도 돌려주지 않았다", file=sys.stderr)
        return None

    print(f"[{role}] 모델을 고르세요:")
    for i, model_id in enumerate(models, start=1):
        print(f"  {i}. {model_id}")
    model_id = _prompt_numbered_choice(models, "모델")

    return AgentChoice(provider=provider_name, model=model_id)


def _cmd_agents_select(args: argparse.Namespace) -> int:
    """D-31의 두 단계 선택 화면. `--role` 없으면 두 역할을 각각 한 번씩 돈다(D-32)."""
    # `--role`로 한 역할만 다시 고를 때, 나머지 역할의 기존 선택을 잃지
    # 않아야 한다. `load_config`는 두 역할이 다 있어야 성공하므로 아직
    # 완성되지 않은 파일에서는 예외가 나고, 그 예외를 빈 사전으로 받으면
    # 방금까지 저장돼 있던 다른 역할이 지워진다(`_cmd_agents_set`과 같은 함정).
    config_path = Path(args.config)
    choices = load_partial_config(config_path)

    roles = (args.role,) if args.role else AGENT_ROLES
    for role in roles:
        choice = _select_one_role(role, os.environ)
        if choice is None:
            return 1
        choices[role] = choice

    save_config(config_path, choices)
    print(f"\n저장됨: {config_path}")
    return 0


def _cmd_agents_set(args: argparse.Namespace) -> int:
    """제공자·모델을 대화 없이 바로 저장한다 — 실행 절차가 재현 가능해야 한다.

    **`select`만으로는 런북을 쓸 수 없다는 것이 이 명령이 생긴 이유다.**
    `select`는 번호를 골라 넣는 대화형 화면이고, 모델 목록을 띄우려면
    `provider.list_models()`로 실제 네트워크 왕복을 한다. 그래서 ① 세션 당일
    절차서에 "이렇게 치면 이 상태가 된다"를 적을 수 없고 ② 저장 파일이
    `.gitignore`의 `.gptrpg/`에 들어가 저장소에 남지 않으므로, 새로 받은
    작업 사본이나 다른 기기에서는 설정이 **없는 상태에서 시작**한다.
    설정이 없으면 `load_config`가 `ConfigNotFound`를 던지고 웹의 행동 선언이
    503으로 떨어진다 — 실험 당일 서버는 뜨는데 아무도 행동을 못 하는 모양이다.

    `select`를 대체하지 않는다(모델 이름을 모를 때 목록을 보고 고르는 일은
    여전히 `select`가 한다). 이 명령은 **이미 정해진 값을 그대로 적는** 자리다.
    제공자 이름은 `PROVIDER_ENV_VARS`에 있는지 검사하지만 **API 키가 있는지는
    검사하지 않는다** — 키가 없는 환경(예: 프런트엔드만 빌드하는 기기)에서도
    설정 파일을 미리 만들어 둘 수 있어야 하고, 키가 없다는 사실은 실제 호출
    시점에 `MissingApiKey`가 조용한 대체 없이 알려 준다.
    """
    if args.provider not in PROVIDER_ENV_VARS:
        known = ", ".join(sorted(PROVIDER_ENV_VARS))
        print(
            f"오류: 등록되지 않은 제공자: {args.provider!r} (알려진 이름: {known})",
            file=sys.stderr,
        )
        return 1

    # `load_config`가 아니라 `load_partial_config`를 쓴다 — 역할 하나만 저장된
    # 파일은 `load_config` 기준으로 「올바르지 않은」 파일이라 예외가 나고,
    # 그것을 빈 사전으로 받아 넘기면 두 번째 `set`이 첫 번째 역할을 지운다.
    config_path = Path(args.config)
    choices = load_partial_config(config_path)
    choices[args.role] = AgentChoice(provider=args.provider, model=args.model)
    save_config(config_path, choices)

    missing = [role for role in AGENT_ROLES if role not in choices]
    print(f"저장됨: {config_path} — {args.role}: {args.provider}/{args.model}")
    if missing:
        # 두 역할이 다 차기 전까지 `load_config`는 여전히 InvalidAgentConfig를
        # 던진다. 그 사실을 지금 알려 주지 않으면 운영자는 "저장됨"만 보고
        # 끝났다고 믿는다.
        print(f"아직 안 정해진 역할: {', '.join(missing)} — 이 역할까지 정해야 서버가 행동을 받는다")
    return 0


def _cmd_agents_show(args: argparse.Namespace) -> int:
    config_path = Path(args.config)
    try:
        choices = load_config(config_path)
    except (ConfigNotFound, InvalidAgentConfig) as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1

    for role in AGENT_ROLES:
        choice = choices[role]
        print(f"{role}: {choice.provider}/{choice.model}")
    return 0


def _cmd_turn(args: argparse.Namespace) -> int:
    if bool(args.provider) != bool(args.model):
        print("오류: --provider와 --model은 항상 함께 줘야 한다", file=sys.stderr)
        return 1

    store = EventStore(args.db)
    store.initialize()
    try:
        return asyncio.run(run_turn(store, args))
    except (
        CommandRejected,
        SequenceConflict,
        UnknownRulebook,
        UnknownMove,
        UnknownProvider,
        MissingApiKey,
        ProviderNotImplemented,
        ConfigNotFound,
        InvalidAgentConfig,
    ) as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1
    finally:
        store.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gptrpg")
    subparsers = parser.add_subparsers(dest="command", required=True)

    submit_parser = subparsers.add_parser("submit")
    submit_parser.add_argument("--db", required=True)
    submit_parser.add_argument("--session", required=True)
    submit_parser.set_defaults(func=_cmd_submit)
    submit_subparsers = submit_parser.add_subparsers(dest="submit_command", required=True)

    declare_parser = submit_subparsers.add_parser("declare")
    declare_parser.add_argument("--player", required=True)
    declare_parser.add_argument("--text", required=True)

    confirm_parser = submit_subparsers.add_parser("confirm")
    confirm_parser.add_argument("--player", required=True)
    confirm_parser.add_argument("--move", required=True)
    confirm_parser.add_argument("--stat", required=True)
    confirm_parser.add_argument("--suggestion", required=True)
    confirm_group = confirm_parser.add_mutually_exclusive_group(required=True)
    confirm_group.add_argument("--confirmed", dest="confirmed", action="store_true")
    confirm_group.add_argument("--rejected", dest="confirmed", action="store_false")
    confirm_parser.add_argument("--caused-by", type=int, default=None)

    roll_parser = submit_subparsers.add_parser("roll")
    roll_parser.add_argument("--move", required=True)
    roll_parser.add_argument(
        "--target",
        type=int,
        default=DEFAULT_TARGET,
        help=(
            "2d6 등급식 룰북에서는 판정 총합과 비교할 고정 기준값이고, "
            "d100 롤언더 룰북에서는 굴림이 밑돌아야 하는 기술값(백분율)이다"
        ),
    )
    roll_parser.add_argument(
        "--rulebook",
        default=DUNGEONWORLD_LIKE_ID,
        help="이 판정에 쓸 룰북 식별자 (기본값: Phase 1과 같은 던전월드 계열)",
    )
    roll_parser.add_argument("--modifier", action="append", default=[])
    roll_parser.add_argument("--caused-by", type=int, default=None)

    narrate_parser = submit_subparsers.add_parser("narrate")
    narrate_parser.add_argument("--text", required=True)
    narrate_parser.add_argument("--chunk", type=int, required=True)
    narrate_parser.add_argument("--caused-by", type=int, default=None)

    clock_parser = submit_subparsers.add_parser("clock")
    clock_parser.add_argument("--clock-id", required=True)
    clock_parser.add_argument("--segment", type=int, required=True)
    clock_parser.add_argument(
        "--trigger", required=True, choices=["fail_counter", "condition", "ai_choice"]
    )
    clock_parser.add_argument("--caused-by", type=int, default=None)

    ai_parser = submit_subparsers.add_parser("ai")
    ai_parser.add_argument("--role", required=True)
    ai_parser.add_argument("--model", required=True)
    ai_parser.add_argument("--provider", required=True)
    ai_parser.add_argument("--prompt-tokens", type=int, required=True)
    ai_parser.add_argument("--completion-tokens", type=int, required=True)
    ai_parser.add_argument(
        "--cached-prompt-tokens",
        dest="cached_prompt_tokens",
        type=int,
        default=0,
        help=(
            "입력 토큰 중 캐시에서 읽어 온 몫(--prompt-tokens의 부분집합). "
            "제공자가 보고하지 않으면 0"
        ),
    )
    ai_parser.add_argument("--latency-ms", type=int, required=True)
    ai_parser.add_argument("--caused-by", type=int, default=None)

    replay_parser = subparsers.add_parser("replay")
    replay_parser.add_argument("--db", required=True)
    replay_parser.add_argument("--session", required=True)
    replay_parser.set_defaults(func=_cmd_replay)

    report_parser = subparsers.add_parser("report")
    report_parser.add_argument("--db", required=True)
    report_parser.add_argument("--session", required=True)
    report_parser.add_argument(
        "--out-dir",
        dest="out_dir",
        default=str(DEFAULT_REPORTS_DIR),
        help="집계 JSON을 저장할 디렉터리",
    )
    report_parser.set_defaults(func=_cmd_report)

    turn_parser = subparsers.add_parser("turn")
    turn_parser.add_argument("--db", required=True)
    turn_parser.add_argument("--session", required=True)
    turn_parser.add_argument("--player", required=True)
    turn_parser.add_argument("--text", required=True)
    turn_parser.add_argument(
        "--rulebook",
        default=DUNGEONWORLD_LIKE_ID,
        help="이 턴에 쓸 룰북 식별자 (기본값: 던전월드 계열)",
    )
    turn_parser.add_argument(
        "--provider",
        default=None,
        help="두 역할 모두에 쓸 제공자 이름(빠른 수동 시험용). 없으면 --config의 저장된 선택을 쓴다",
    )
    turn_parser.add_argument(
        "--model",
        default=None,
        help="두 역할 모두에 쓸 모델 식별자(빠른 수동 시험용). 없으면 --config의 저장된 선택을 쓴다",
    )
    turn_parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="역할별 제공자·모델 선택이 저장된 파일 (기본값: .gptrpg/agents.json)",
    )
    turn_parser.add_argument("--target", type=int, default=DEFAULT_TARGET)
    turn_parser.add_argument("--modifier", action="append", default=[])
    turn_parser.add_argument(
        "--progress-after",
        type=float,
        default=5.0,
        dest="progress_after",
        help="이 초를 넘기면 점(.) 진행 표시를 시작한다 (기본값: 5.0, D-26)",
    )
    turn_parser.add_argument(
        "--progress-tick",
        type=float,
        default=1.0,
        dest="progress_tick",
        help="진행 표시가 시작된 뒤 점을 찍는 간격(초) (기본값: 1.0)",
    )
    turn_parser.set_defaults(func=_cmd_turn)

    agents_parser = subparsers.add_parser("agents")
    agents_subparsers = agents_parser.add_subparsers(dest="agents_command", required=True)

    agents_select_parser = agents_subparsers.add_parser("select")
    agents_select_parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    agents_select_parser.add_argument("--role", choices=AGENT_ROLES, default=None)
    agents_select_parser.set_defaults(func=_cmd_agents_select)

    agents_set_parser = agents_subparsers.add_parser(
        "set",
        help="제공자·모델을 대화 없이 바로 저장한다 (실행 절차서에 그대로 적을 수 있는 형태)",
    )
    agents_set_parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    agents_set_parser.add_argument("--role", choices=AGENT_ROLES, required=True)
    agents_set_parser.add_argument("--provider", required=True)
    agents_set_parser.add_argument("--model", required=True)
    agents_set_parser.set_defaults(func=_cmd_agents_set)

    agents_show_parser = agents_subparsers.add_parser("show")
    agents_show_parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    agents_show_parser.set_defaults(func=_cmd_agents_show)

    args = parser.parse_args(argv)
    return args.func(args)
