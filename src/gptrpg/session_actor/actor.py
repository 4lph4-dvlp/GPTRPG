"""명령 큐 + 단일 소비자. 세션당 쓰기 주체 하나 (D-05, D-09①).

여섯 종류 명령(DeclareAction / ConfirmAction / ResolveCheck / AppendNarration /
AdvanceClock / RecordAiCall)을 전부 여기서만 처리한다. 절차는 늘 같은 네 단계다 —
① 명령 값을 검증한다 ② 필요하면 규칙 코어를 부른다(판정 명령만) ③ 순번을 얻고
시각을 찍어 사건 객체를 만든다 ④ 저장소에 append한다. ①·②가 ③보다 먼저 끝나므로,
거부되는 명령은 순번을 소모하지도 기록을 남기지도 않는다 — 반쪽 상태가 생기지
않는다.
"""

import asyncio
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from gptrpg.event_log.schema import (
    EVENT_SCHEMA_VERSION,
    ActionConfirmed,
    ActionDeclared,
    AiInvoked,
    CheckResolved,
    ClockAdvanced,
    ModifierRecord,
    NarrationAppended,
    SceneIllustrated,
    utc_now_iso,
)
from gptrpg.event_log.store import EventStore
from gptrpg.rules_core.dice import Roller
from gptrpg.rules_core.grading import DEFAULT_TARGET
from gptrpg.rules_core.reducer import GameState, apply_event
from gptrpg.rules_core.resolution import Modifier, UnsupportedModifier, resolve_2d6
from gptrpg.rules_core.resolution_d100 import resolve_d100
from gptrpg.rules_core.rulebook import (
    D100_ROLL_UNDER,
    TWO_D6,
    NoMatchingGradeBand,
    Rulebook,
    UnknownGradeName,
    require_band,
)
from gptrpg.rulebooks import UnknownRulebook, get_rulebook
from gptrpg.rulebooks.dungeonworld_like import DUNGEONWORLD_LIKE_ID
from gptrpg.rulebooks.threat_clocks import THREAT_CLOCK_SEGMENT_COUNT
from gptrpg.session_actor.live_roller import LiveRoller
from gptrpg.session_actor.projection import rebuild_state
from gptrpg.session_actor.report import DEFAULT_REPORTS_DIR, UnsafeSessionId, write_report

AUTO_ADVANCE_FAILURE_THRESHOLD = 3
"""D-21이 적은 진행 규칙 기본값("N회 기본 3, 시계별 조절") — 시계별로
문턱값을 다르게 주는 것은 이 마일스톤 범위 밖이다(룰북 데이터의 칸 단위
구체 규격은 전부 M1, `.planning/PROJECT.md`의 M0 범위선).

**D-21의 진행 규칙 세 가지 중 ①(실패 누적)만 이 액터가 만든다.**
②조건 트리거와 ③AI 선택은 M0에 없다 — ③은 `prompt_assembly.build_gm_prompt`가
AI에게 명시적으로 금지하고, ②는 명령줄 `gptrpg submit clock --trigger condition`
으로만 닿는다. 그 결과 `failure_to_clock_ratio`는 이 문턱값에 고정되며
(실패 3회당 정확히 1칸) MEAS-03의 비율 자체로는 봐주기를 판별할 수 없다 —
Phase 6이 H2를 어떻게 읽어야 하는지는
`docs/experiment/hypothesis-scoring-rules.md`가 정한다."""


@dataclass(frozen=True)
class DeclareAction:
    """플레이어가 자유 문장으로 행동을 선언하는 명령."""

    player_id: str
    raw_text: str


@dataclass(frozen=True)
class ConfirmAction:
    """시스템이 제안한 무브·능력치를 플레이어가 확인(또는 거부)하는 명령."""

    player_id: str
    move: str
    stat: str
    system_suggestion: dict[str, str]
    player_confirmed: bool
    caused_by_seq: int | None = None


@dataclass(frozen=True)
class ResolveCheck:
    """판정 하나를 요청하는 명령.

    **판정 방식은 이 명령에 넣지 않는다** — 방식은 룰북 선언(`Rulebook.
    resolution_method`)이 갖고 있고, 이 명령은 어느 룰북인지(`rulebook_id`)만
    말한다.
    """

    move: str
    modifiers: tuple[Modifier, ...]
    target: int = DEFAULT_TARGET
    rulebook_id: str = DUNGEONWORLD_LIKE_ID
    caused_by_seq: int | None = None


@dataclass(frozen=True)
class AppendNarration:
    """서사 문장 조각 하나를 덧붙이는 명령."""

    text: str
    chunk_index: int
    caused_by_seq: int | None = None


@dataclass(frozen=True)
class AdvanceClock:
    """위협 시계를 한 칸 돌리는 명령."""

    clock_id: str
    segment_index: int
    trigger: str
    caused_by_seq: int | None = None


@dataclass(frozen=True)
class RecordAiCall:
    """AI를 한 번 불렀다는 사실을 기록하는 명령.

    `cached_prompt_tokens`는 `prompt_tokens`의 부분집합이며 기본값이 0이다 —
    캐시 정보를 주지 않는 제공자와, 이 칸이 생기기 전에 쓰인 호출부를 위한
    기본값이다(`AgentResult`·`AiInvoked`의 같은 이름 칸과 같은 뜻).
    """

    agent_role: str
    model: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    caused_by_seq: int | None = None
    cached_prompt_tokens: int = 0


@dataclass(frozen=True)
class RecordSceneIllustration:
    """장면 삽화 한 장이 만들어졌다는 사실을 기록하는 명령.

    **그림을 만드는 코드가 이 명령을 만들지 않는다.** `gptrpg.imagery`는
    `session_actor`를 import할 수 없으므로(contract:4) 그림 층에는 사건을 쓸
    수단이 없다. 그림 바이트를 받아 이 명령으로 옮기는 것은 `web`의 일이고,
    그 통로가 유일하다 — `agents`가 서사를 사건으로 바꾸는 방식과 같다.
    """

    image_path: str
    prompt: str
    style: str
    seed: int
    steps: int
    size: int
    latency_ms: int
    caused_by_seq: int | None = None


Command = (
    DeclareAction
    | ConfirmAction
    | ResolveCheck
    | AppendNarration
    | AdvanceClock
    | RecordAiCall
    | RecordSceneIllustration
)

_VALID_CLOCK_TRIGGERS = frozenset({"fail_counter", "condition", "ai_choice"})

_EVENT_CLASSES: dict[str, type] = {
    "action_declared": ActionDeclared,
    "action_confirmed": ActionConfirmed,
    "check_resolved": CheckResolved,
    "narration_appended": NarrationAppended,
    "clock_advanced": ClockAdvanced,
    "ai_invoked": AiInvoked,
    "scene_illustrated": SceneIllustrated,
}


def _resolve_two_d6(roller, command: ResolveCheck, rulebook: Rulebook):
    return resolve_2d6(roller, command.move, command.modifiers, command.target)


def _resolve_d100_roll_under(roller, command: ResolveCheck, rulebook: Rulebook):
    return resolve_d100(
        roller, command.move, command.modifiers, command.target, rulebook.grade_bands
    )


_RESOLVERS: dict[str, Callable] = {
    TWO_D6: _resolve_two_d6,
    D100_ROLL_UNDER: _resolve_d100_roll_under,
}


class CommandRejected(Exception):
    """세션 액터가 명령을 처리할 수 없을 때 던진다. 이 명령에 대해 아무것도 기록되지 않는다."""


class SessionActor:
    """asyncio.Queue 하나 + 그 큐를 소비하는 태스크 하나. 세션당 쓰기 주체는 이거 하나뿐이다."""

    def __init__(
        self,
        store: EventStore,
        session_id: str,
        roller: Roller,
        *,
        clock_id: str = "threat",
        clock_segment_count: int = THREAT_CLOCK_SEGMENT_COUNT,
        report_dir: Path | None = None,
    ) -> None:
        self._store = store
        self._session_id = session_id
        self._roller = roller
        self._queue: asyncio.Queue = asyncio.Queue()
        self._task: asyncio.Task | None = None
        # **저장소에 이미 쌓인 사건을 그대로 다시 접어 시작한다** — `initial_state()`로
        # 시작하면 액터가 새로 만들어질 때마다(서버 재시작, 또는 CLI `submit`처럼
        # 명령 하나당 프로세스 하나가 뜨는 경로) 이 액터의 자기 인식이 빈 세션으로
        # 되돌아간다. 검증(순번 충돌은 예외다 — `EventStore.next_seq`가 프로세스
        # 경계와 무관하게 지킨다)과 `_maybe_auto_advance`의 `fails_since_clock` 문턱
        # 판정이 전부 `self.state`를 본다 — 이 칸이 사건 기록과 어긋나면 "현재
        # 상태는 그 기록에서만 재구성된다"는 이 프로젝트의 되돌릴 수 없는 결정
        # (PROJECT.md)이 액터 내부에서만 조용히 깨진다. `poll_events`가 이미 매
        # 요청마다 같은 `rebuild_state`로 화면 값을 다시 접는 것과 같은 이유,
        # 같은 함수다 — 두 번째 재구성 로직을 새로 만들지 않는다.
        self.state: GameState = rebuild_state(store, session_id)
        # clock_id를 생성 시점에 묶는다 — GameState는 마지막으로 쓴 clock_id를
        # 기억하지 않으므로, 첫 자동 진행이 일어날 때 참고할 값이 아무 데도
        # 없다. 세션당 위협 시계 하나(EXP-01)와 cli/turn_flow.py가 이미 쓰는
        # "threat" 관례에 맞춰 생성 인자로 받는 것이 닭-달걀 조회를 없애는
        # 가장 단순한 길이다.
        self._clock_id = clock_id
        # 자동 진행의 상한. 기본값의 출처는 `rulebooks.threat_clocks`이고
        # 그 값 하나가 프롬프트 분모(`turn.context`)·화면 분모
        # (`web.routes_events`)·이 상한까지 동시에 정한다 — 같은 숫자를
        # 세 자리에 따로 적지 않는다.
        self._clock_segment_count = clock_segment_count
        self._report_dir = report_dir if report_dir is not None else DEFAULT_REPORTS_DIR

    def start(self) -> None:
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        """소비자 루프에 종료 신호를 넣고 끝날 때까지 기다린다."""
        if self._task is not None:
            await self._queue.put(None)
            await self._task
            self._task = None

    async def submit(self, command: Command) -> int:
        """명령을 큐에 넣고 처리가 끝날 때까지 기다린 뒤, 기록된 사건의 순번을 돌려준다.

        검증에 실패하면 `CommandRejected`가, 순번 충돌이 나면 `SequenceConflict`가
        그대로 이 호출자에게 전달된다 — 액터는 어느 쪽도 삼키지 않는다.
        """
        future: asyncio.Future[int] = asyncio.get_running_loop().create_future()
        await self._queue.put((command, future))
        return await future

    async def _run(self) -> None:
        while True:
            item = await self._queue.get()
            if item is None:
                self._queue.task_done()
                break
            command, future = item
            try:
                seq = await self._process(command)
            except Exception as exc:  # noqa: BLE001 - 부르는 쪽에 그대로 전달한다, 삼키지 않는다
                if not future.done():
                    future.set_exception(exc)
            else:
                if not future.done():
                    future.set_result(seq)
            self._queue.task_done()

    async def _process(self, command: Command) -> int:
        event_type, caused_by_seq, fields = self._prepare(command)

        seq = self._store.next_seq(self._session_id)
        event = _EVENT_CLASSES[event_type](
            session_id=self._session_id,
            seq=seq,
            schema_version=EVENT_SCHEMA_VERSION,
            caused_by_seq=caused_by_seq,
            recorded_at=utc_now_iso(),
            event_type=event_type,
            **fields,
        )
        self._store.append(event)
        self.state = apply_event(self.state, event.event_type, event.model_dump())

        await self._maybe_auto_advance(event_type, seq)
        self._write_report_snapshot()
        return seq

    async def _maybe_auto_advance(self, event_type: str, check_seq: int) -> None:
        """실패 판정이 문턱을 넘으면 위협 시계를 스스로 한 칸 돌린다 (RIG-04, D-21).

        `_process`를 큐에 다시 넣지 않고 **직접 재귀 호출**한다 — 큐로 돌리면
        그 사이에 다른 플레이어의 명령이 끼어들어 "3번째 실패와 그 실패가
        부른 시계 진행" 사이가 벌어지고, 최악의 경우 두 플레이어가 동시에
        3번째 실패를 만들어 시계가 두 칸 돈다. `_process`를 직접 부르면
        이미 단일 소비자 안이므로 원자적이다.

        재귀는 최대 한 겹이다 — 시계 진행 사건(`clock_advanced`)은
        `check_resolved`가 아니므로 이 메서드를 다시 부르지 않는다.

        **마지막 칸에 도달하면 더 돌리지 않는다.** 예전에는 상한 없이
        `clock_segment + 1`을 썼기 때문에 파국(4/4) 이후 실패가 3번 더 쌓이면
        `5/4`, `6/4`가 기록되고 화면 머리띠에도 그대로 찍혔다 — 플레이어에게는
        버그로 보이는 값이다. D-47이 "코드로 상한선을 강제하지 않고, 파국
        이후에도 즉흥으로 계속 진행하지도 않는다"고 정한 것의 뒷문장을
        지키는 것이 이 상한이다: 진행자가 파국 서사 직후 세션을 마무리하는
        동안에도 자동 진행이 뒤에서 칸을 더 밀어 올리지 않는다. 실패 자체는
        계속 세어지므로(`failure_count`는 초기화되지 않는다) MEAS-03의 분자는
        잃지 않는다 — `fails_since_clock`만 문턱 위에 머문다.
        """
        if event_type != "check_resolved":
            return
        if self.state.fails_since_clock < AUTO_ADVANCE_FAILURE_THRESHOLD:
            return
        if self.state.clock_segment >= self._clock_segment_count:
            return
        await self._process(
            AdvanceClock(
                clock_id=self._clock_id,
                segment_index=self.state.clock_segment + 1,
                trigger="fail_counter",
                caused_by_seq=check_seq,
            )
        )

    def _write_report_snapshot(self) -> None:
        """`write_report`를 불러 집계 파일을 최신으로 갱신한다 (D-44).

        집계 파일을 못 써서 사건 기록이 막히면 안 된다 — 사건 기록이 이
        프로젝트의 진실이고 집계는 그 파생물이다. `OSError`/`UnsafeSessionId`를
        잡아 경고 한 줄만 찍고 그냥 돌아온다.
        """
        try:
            write_report(self.state, base_dir=self._report_dir)
        except (OSError, UnsafeSessionId) as exc:
            print(f"경고: 집계 파일 저장 실패 — {exc}", file=sys.stderr)

    def _prepare(self, command: Command) -> tuple[str, int | None, dict]:
        if isinstance(command, DeclareAction):
            return self._prepare_declare(command)
        if isinstance(command, ConfirmAction):
            return self._prepare_confirm(command)
        if isinstance(command, ResolveCheck):
            return self._prepare_resolve_check(command)
        if isinstance(command, AppendNarration):
            return self._prepare_narration(command)
        if isinstance(command, AdvanceClock):
            return self._prepare_clock(command)
        if isinstance(command, RecordAiCall):
            return self._prepare_ai_call(command)
        if isinstance(command, RecordSceneIllustration):
            return self._prepare_scene_illustration(command)
        raise CommandRejected(f"알 수 없는 명령: {command!r}")

    def _validate_caused_by(self, caused_by_seq: int | None) -> None:
        """caused_by_seq가 있으면 이 세션에 실제로 존재하는 순번인지 확인한다.

        없는 순번을 가리키면 나중에 응답 시간 계산이 짝을 못 찾는다.
        """
        if caused_by_seq is None:
            return
        if caused_by_seq < 0 or caused_by_seq >= self._store.next_seq(self._session_id):
            raise CommandRejected(
                f"caused_by_seq {caused_by_seq}는 이 세션에 실제로 존재하는 순번이 아니다"
            )

    def _prepare_declare(self, command: DeclareAction) -> tuple[str, int | None, dict]:
        if not command.player_id.strip():
            raise CommandRejected("player_id는 비어 있을 수 없다")
        if not command.raw_text.strip():
            raise CommandRejected("raw_text는 비어 있을 수 없다")
        return (
            "action_declared",
            None,
            {"player_id": command.player_id, "raw_text": command.raw_text},
        )

    def _prepare_confirm(self, command: ConfirmAction) -> tuple[str, int | None, dict]:
        if not command.player_id.strip():
            raise CommandRejected("player_id는 비어 있을 수 없다")
        if not command.move.strip():
            raise CommandRejected("move는 비어 있을 수 없다")
        if not command.stat.strip():
            raise CommandRejected("stat는 비어 있을 수 없다")
        self._validate_caused_by(command.caused_by_seq)
        return (
            "action_confirmed",
            command.caused_by_seq,
            {
                "player_id": command.player_id,
                "move": command.move,
                "stat": command.stat,
                "system_suggestion": command.system_suggestion,
                "player_confirmed": command.player_confirmed,
            },
        )

    def _prepare_resolve_check(self, command: ResolveCheck) -> tuple[str, int | None, dict]:
        self._validate_caused_by(command.caused_by_seq)

        try:
            rulebook = get_rulebook(command.rulebook_id)
        except UnknownRulebook as exc:
            raise CommandRejected(str(exc)) from exc

        resolver = _RESOLVERS.get(rulebook.resolution_method)
        if resolver is None:
            raise CommandRejected(
                f"알 수 없는 판정 방식: {rulebook.resolution_method!r} "
                f"(룰북 {rulebook.rulebook_id!r})"
            )

        try:
            outcome = resolver(self._roller, command, rulebook)
        except UnsupportedModifier as exc:
            raise CommandRejected(str(exc)) from exc
        except AttributeError as exc:
            raise CommandRejected(
                f"굴림 도구가 {rulebook.resolution_method!r} 판정에 필요한 메서드를 "
                f"갖추지 않았다: {exc}"
            ) from exc
        except NoMatchingGradeBand as exc:
            raise CommandRejected(
                f"룰북 {rulebook.rulebook_id!r}의 등급 밴드 선언이 이 판정 결과를 "
                f"덮지 않는다: {exc}"
            ) from exc

        try:
            band = require_band(rulebook.grade_bands, outcome.grade)
        except UnknownGradeName as exc:
            raise CommandRejected(str(exc)) from exc

        return (
            "check_resolved",
            command.caused_by_seq,
            {
                "move": outcome.move,
                "rolls": list(outcome.rolls),
                "modifiers": [
                    ModifierRecord(type=modifier.type, value=modifier.value, source=modifier.source)
                    for modifier in outcome.modifiers
                ],
                "target": outcome.target,
                "grade": outcome.grade,
                "counts_as_failure": band.counts_as_failure,
            },
        )

    def _prepare_narration(self, command: AppendNarration) -> tuple[str, int | None, dict]:
        if not command.text.strip():
            raise CommandRejected("text는 비어 있을 수 없다")
        if command.chunk_index < 0:
            raise CommandRejected("chunk_index는 0 이상이어야 한다")
        self._validate_caused_by(command.caused_by_seq)
        return (
            "narration_appended",
            command.caused_by_seq,
            {"text": command.text, "chunk_index": command.chunk_index},
        )

    def _prepare_clock(self, command: AdvanceClock) -> tuple[str, int | None, dict]:
        if not command.clock_id.strip():
            raise CommandRejected("clock_id는 비어 있을 수 없다")
        if command.segment_index < 0:
            raise CommandRejected("segment_index는 0 이상이어야 한다")
        if command.trigger not in _VALID_CLOCK_TRIGGERS:
            raise CommandRejected(
                f"trigger는 {sorted(_VALID_CLOCK_TRIGGERS)} 중 하나여야 한다: {command.trigger!r}"
            )
        self._validate_caused_by(command.caused_by_seq)
        return (
            "clock_advanced",
            command.caused_by_seq,
            {
                "clock_id": command.clock_id,
                "segment_index": command.segment_index,
                "trigger": command.trigger,
            },
        )

    def _prepare_ai_call(self, command: RecordAiCall) -> tuple[str, int | None, dict]:
        if not command.agent_role.strip():
            raise CommandRejected("agent_role은 비어 있을 수 없다")
        if not command.model.strip():
            raise CommandRejected("model은 비어 있을 수 없다")
        if not command.provider.strip():
            raise CommandRejected("provider는 비어 있을 수 없다")
        if command.prompt_tokens < 0 or command.completion_tokens < 0:
            raise CommandRejected("토큰 수는 0 이상이어야 한다")
        if command.cached_prompt_tokens < 0:
            raise CommandRejected("캐시 적중 토큰 수는 0 이상이어야 한다")
        if command.cached_prompt_tokens > command.prompt_tokens:
            # 이 칸의 정의가 「`prompt_tokens`의 부분집합」이다. 넘으면 어댑터가
            # 캐시 몫을 입력 몫에 포함시키지 않은 것이므로(Anthropic이 실제로
            # 그렇다 — `_input_token_counts`가 그래서 따로 더한다) 조용히
            # 통과시키면 원가가 음수 신규 입력으로 계산된다.
            raise CommandRejected(
                f"캐시 적중 토큰({command.cached_prompt_tokens})이 입력 토큰"
                f"({command.prompt_tokens})보다 많을 수 없다"
            )
        if command.latency_ms < 0:
            raise CommandRejected("소요 시간은 0 이상이어야 한다")
        self._validate_caused_by(command.caused_by_seq)
        return (
            "ai_invoked",
            command.caused_by_seq,
            {
                "agent_role": command.agent_role,
                "model": command.model,
                "provider": command.provider,
                "prompt_tokens": command.prompt_tokens,
                "completion_tokens": command.completion_tokens,
                "latency_ms": command.latency_ms,
                "cached_prompt_tokens": command.cached_prompt_tokens,
            },
        )

    def _prepare_scene_illustration(
        self, command: RecordSceneIllustration
    ) -> tuple[str, int | None, dict]:
        """빈 `image_path`를 거절한다 — 「그림이 있다」가 이 사건의 뜻이다.

        그림을 못 만든 턴은 사건이 없는 턴으로 남아야 한다(`SceneIllustrated`
        도크스트링). 빈 경로를 통과시키면 읽는 쪽마다 빈 값 검사를 다시 해야
        하고, 「삽화 사건이 있다」로 세는 집계가 실제 그림 수와 어긋난다.
        """
        if not command.image_path.strip():
            raise CommandRejected("image_path는 비어 있을 수 없다")
        if not command.prompt.strip():
            raise CommandRejected("prompt는 비어 있을 수 없다")
        if not command.style.strip():
            raise CommandRejected("style은 비어 있을 수 없다")
        if command.steps < 1:
            raise CommandRejected("steps는 1 이상이어야 한다")
        if command.size < 1:
            raise CommandRejected("size는 1 이상이어야 한다")
        if command.latency_ms < 0:
            raise CommandRejected("소요 시간은 0 이상이어야 한다")
        self._validate_caused_by(command.caused_by_seq)
        return (
            "scene_illustrated",
            command.caused_by_seq,
            {
                "image_path": command.image_path,
                "prompt": command.prompt,
                "style": command.style,
                "seed": command.seed,
                "steps": command.steps,
                "size": command.size,
                "latency_ms": command.latency_ms,
            },
        )


class SessionRegistry:
    """세션 식별자당 액터를 하나만 보관한다 (D-09① 첫 겹).

    같은 식별자로 두 번 요청하면 새로 만들지 않고 이미 살아 있는 액터를 돌려준다.
    두 번째 겹(순번 유일성 제약, 프로세스 경계를 넘어서도 유효)은 `EventStore`가 진다.
    """

    def __init__(
        self,
        store: EventStore,
        roller_factory: Callable[[], Roller] | None = None,
        *,
        clock_id: str = "threat",
        clock_segment_count: int = THREAT_CLOCK_SEGMENT_COUNT,
        report_dir: Path | None = None,
    ) -> None:
        self._store = store
        self._roller_factory: Callable[[], Roller] = roller_factory or LiveRoller
        self._actors: dict[str, SessionActor] = {}
        self._clock_id = clock_id
        self._clock_segment_count = clock_segment_count
        self._report_dir = report_dir

    def get_or_create(self, session_id: str) -> SessionActor:
        actor = self._actors.get(session_id)
        if actor is None:
            actor = SessionActor(
                self._store,
                session_id,
                self._roller_factory(),
                clock_id=self._clock_id,
                clock_segment_count=self._clock_segment_count,
                report_dir=self._report_dir,
            )
            actor.start()
            self._actors[session_id] = actor
        return actor
