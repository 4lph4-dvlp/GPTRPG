"""공용 테스트 픽스처: 프로젝트 루트 상수와 임시 사건 기록 경로.

그 위에 01-05의 `fake_session_log` — 두 플레이어가 번갈아 입력하는 완결된 한 세션을
덧붙인다. 이 픽스처는 사건을 실제 `EventStore` 에 append 한 뒤 `read_events` 로 다시
읽어 돌려준다 (메모리 안 객체를 그대로 돌려주면 저장·복원 과정에서 값이 상하는지
잡을 수 없다 — T-1-03).
"""

import json
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from gptrpg.agents.envelope import AgentResult
from gptrpg.event_log.schema import (
    EVENT_SCHEMA_VERSION,
    ActionConfirmed,
    ActionDeclared,
    AiInvoked,
    CheckResolved,
    ClockAdvanced,
    GameEvent,
    NarrationAppended,
)
from gptrpg.event_log.store import EventStore
from gptrpg.imagery import imagery_config_from_env
from gptrpg.web.app import create_app

# 테스트가 어느 작업 디렉터리에서 실행되든 저장소 최상위를 가리키도록 고정한다.
# import-linter처럼 현재 작업 디렉터리에 의존하는 도구를 테스트 안에서 호출할 때 필요하다.
PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# 01-05: 역방향 검증을 위한 가짜 세션 기록.
#
# 실제 시각 함수를 부르지 않는다 — 고정 기준 시각에서 밀리초를 더해 만든다.
# 그래야 테스트가 실행 시각과 무관하게 항상 같은 recorded_at 을 낸다.
# ---------------------------------------------------------------------------

_BASE_TIME = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)


def _t(ms_offset: int) -> str:
    """고정 기준 시각에서 `ms_offset` 밀리초만큼 더한 ISO8601 문자열.

    `schema.utc_now_iso` 와 같은 형식(%Y-%m-%dT%H:%M:%S.{ms:03d}Z)을 쓴다 —
    저장 왕복에서 형식이 달라 깨지는 일이 없도록.
    """
    dt = _BASE_TIME + timedelta(milliseconds=ms_offset)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def _env(session_id: str, seq: int, caused_by_seq: int | None, ms: int) -> dict:
    """여섯 종류가 공유하는 봉투 칸을 한 자리에서 만든다."""
    return {
        "session_id": session_id,
        "seq": seq,
        "schema_version": EVENT_SCHEMA_VERSION,
        "recorded_at": _t(ms),
        "caused_by_seq": caused_by_seq,
    }


def _make_fake_events(session_id: str) -> list[GameEvent]:
    """순번 순서대로 만든 14개 사건. 인과 칸은 01-02 option-a 로 이어져 있다.

    시각은 seq 와 단조 증가하도록 배치했다 (0→3500ms). 다만 seq 0~3 은 두 플레이어의
    선언·확인이 번갈아 섞이게 배치한다 — 순번 인접으로 짝을 맞추면 인과 칸과 다른
    (틀린) 값이 나온다 (T-1-13).
    """
    return [
        # --- 턴 1·2 의 선언·확정이 번갈아 섞인 구간 (seq 0~3) ---
        ActionDeclared(
            event_type="action_declared",
            player_id="p1",
            raw_text="경비병을 설득해 통로를 열어 보려 한다",
            **_env(session_id, 0, None, 0),
        ),
        ActionDeclared(
            event_type="action_declared",
            player_id="p2",
            raw_text="그림자 속에 숨어 상황을 지켜본다",
            **_env(session_id, 1, None, 50),
        ),
        ActionConfirmed(
            event_type="action_confirmed",
            player_id="p1",
            move="persuade",
            stat="CHA",
            system_suggestion={"move": "persuade", "stat": "CHA"},
            player_confirmed=True,
            **_env(session_id, 2, 0, 250),
        ),
        ActionConfirmed(
            event_type="action_confirmed",
            player_id="p2",
            move="shadow",
            stat="DEX",
            system_suggestion={"move": "hide", "stat": "DEX"},
            player_confirmed=False,
            **_env(session_id, 3, 1, 300),
        ),
        # --- 턴 1 (p1): 판정 실패 → 서사 2조각 ---
        CheckResolved(
            event_type="check_resolved",
            move="persuade",
            rolls=[2, 3],
            modifiers=[],
            target=10,
            grade="miss",
            counts_as_failure=True,
            **_env(session_id, 4, 2, 450),
        ),
        AiInvoked(
            event_type="ai_invoked",
            agent_role="narrator",
            model="gpt-4o",
            provider="openai",
            prompt_tokens=120,
            completion_tokens=80,
            latency_ms=1500,
            **_env(session_id, 5, 2, 1900),
        ),
        NarrationAppended(
            event_type="narration_appended",
            text="경비병이 미심쩍은 눈으로 너를 쳐다본다.",
            chunk_index=0,
            **_env(session_id, 6, 2, 1950),
        ),
        NarrationAppended(
            event_type="narration_appended",
            text="손을 칼자루에 가져가며 한 발 물러선다.",
            chunk_index=1,
            **_env(session_id, 7, 2, 2050),
        ),
        # --- 턴 2 (p2): 판정 성공 (위 제안 거절·대안 선택 = player_confirmed False) ---
        CheckResolved(
            event_type="check_resolved",
            move="shadow",
            rolls=[6, 5],
            modifiers=[],
            target=7,
            grade="strong_hit",
            counts_as_failure=False,
            **_env(session_id, 8, 3, 2200),
        ),
        # --- 턴 3 (p1 재선언): 재굴림 한 번 → 여전히 실패 → 위협 시계 1칸 ---
        ActionDeclared(
            event_type="action_declared",
            player_id="p1",
            raw_text="자물쇠를 강제로 따 들어간다",
            **_env(session_id, 9, None, 3000),
        ),
        AiInvoked(
            event_type="ai_invoked",
            agent_role="move_classifier",
            model="claude-3.5-sonnet",
            provider="anthropic",
            prompt_tokens=90,
            completion_tokens=40,
            latency_ms=200,
            **_env(session_id, 10, 9, 3050),
        ),
        ActionConfirmed(
            event_type="action_confirmed",
            player_id="p1",
            move="pick_lock",
            stat="DEX",
            system_suggestion={"move": "force_lock", "stat": "STR"},
            player_confirmed=True,
            **_env(session_id, 11, 9, 3250),
        ),
        CheckResolved(
            event_type="check_resolved",
            move="pick_lock",
            rolls=[4, 1, 2, 3],
            modifiers=[],
            target=10,
            grade="miss",
            counts_as_failure=True,
            **_env(session_id, 12, 11, 3400),
        ),
        ClockAdvanced(
            event_type="clock_advanced",
            clock_id="threat-1",
            segment_index=1,
            trigger="fail_counter",
            **_env(session_id, 13, 12, 3500),
        ),
    ]


@dataclass(frozen=True)
class FakeSession:
    """`fake_session_log` 픽스처가 돌려주는 값.

    `events` 는 실제 저장소를 한 번 거쳐 다시 읽은 사건 목록이고, 나머지 칸은
    이 기록에서 여섯 숫자가 나와야 하는 값(기대치)이다 — 역산 테스트가 계산한
    값과 이 기대치를 이름으로 비교한다.
    """

    session_id: str
    events: list[GameEvent]
    # 2① 실제 토큰 소모량
    token_spend: int
    # 2② 실제 턴 수
    turn_count: int
    # 2⑤ 판정 실패 횟수 / 시계 진행 횟수
    failure_count: int
    clock_advance_count: int
    # 2③ 문장 입력 → 행동 확인 표시 시간 (인과 칸 기준, ms)
    declare_confirm_ms: list[int]
    # 2④ 확인 → 서사 첫 글자 시간 (인과 칸 기준, chunk_index==0 만, ms)
    confirm_narration_ms: list[int]


@pytest.fixture
def fake_session_log(tmp_db_path: Path) -> FakeSession:
    """두 플레이어가 번갈아 입력하는 완결된 한 세션을 실제 저장소에 넣고 다시 읽는다.

    순번 0~3: p1 선언·p2 선언·p1 확인·p2 확인 — 인접 짝짓기가 틀리게 섞였다.
    턴1 p1 판정 miss → 서사 2조각(chunk 0·1). 턴2 p2 판정 strong_hit.
    턴3 p1 재굴림(눈 4개) → miss → 위협 시계 1칸(실패 누적).
    사건을 append 한 뒤 read_events 로 다시 읽어 돌려준다 (T-1-03).
    """
    session_id = "fake-session-01"
    store = EventStore(tmp_db_path)
    store.initialize()
    for event in _make_fake_events(session_id):
        store.append(event)
    events = store.read_events(session_id)
    store.close()
    return FakeSession(
        session_id=session_id,
        events=events,
        token_spend=120 + 80 + 90 + 40,
        turn_count=3,
        failure_count=2,
        clock_advance_count=1,
        declare_confirm_ms=[250, 250, 250],
        confirm_narration_ms=[1700],
    )


@pytest.fixture
def tmp_db_path(tmp_path: Path) -> Path:
    """임시 디렉터리 안의 사건 기록 파일 경로를 돌려준다.

    파일 자체는 만들지 않는다 — 사건 기록 계층이 첫 append에서 만들어야 한다.
    """
    return tmp_path / "events.db"


# ---------------------------------------------------------------------------
# 03-01: 트레이서 시험을 위한 가짜 제공자 — 네트워크를 전혀 타지 않는다.
# ---------------------------------------------------------------------------


class FakeProvider:
    """`Provider` 프로토콜을 네트워크 없이 구현하는 테스트 픽스처.

    생성자에서 받은 고정 문자열을 그대로 돌려준다. 받은 `(system, messages)`
    짝을 전부 `self.calls`에 쌓아 둔다 — 프롬프트 접두가 호출 사이에 바이트
    단위로 같은지를 시험이 확인할 수 있어야 한다. `last_result()`는 결정적인
    토큰 수와 시간을 돌려준다.
    """

    name = "fake"

    def __init__(
        self,
        *,
        complete_value: str = "[]",
        stream_text: str = "",
        prompt_tokens: int = 12,
        completion_tokens: int = 8,
        elapsed_ms: int = 42,
    ) -> None:
        self.complete_value = complete_value
        self.stream_text = stream_text
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.elapsed_ms = elapsed_ms
        self.calls: list[tuple[list[dict], list[dict]]] = []
        self._last_result: AgentResult | None = None

    def list_models(self) -> list[str]:
        return ["fake-model"]

    def complete(self, *, model, system, messages, max_tokens, timeout_s) -> AgentResult:
        self.calls.append((system, messages))
        result = AgentResult(
            ok=True,
            value=self.complete_value,
            elapsed_ms=self.elapsed_ms,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
        )
        self._last_result = result
        return result

    def stream(self, *, model, system, messages, max_tokens, timeout_s):
        self.calls.append((system, messages))
        for word in self.stream_text.split(" "):
            if word:
                yield word + " "
        self._last_result = AgentResult(
            ok=True,
            value=self.stream_text,
            elapsed_ms=self.elapsed_ms,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
        )

    def last_result(self) -> AgentResult:
        if self._last_result is None:
            raise RuntimeError("complete() 또는 stream()을 먼저 불러야 last_result()를 부를 수 있다")
        return self._last_result

    def note_result(self, result: AgentResult) -> None:
        self._last_result = result


@pytest.fixture
def fake_provider() -> FakeProvider:
    """분류기 후보 하나 + 두 문장짜리 서사를 결정적으로 돌려주는 가짜 제공자."""
    return FakeProvider(
        complete_value=json.dumps([{"move": "hack_and_slash", "stat": "STR"}]),
        stream_text="문이 요란하게 부서진다. 안에서 서늘한 바람이 흘러나온다.",
    )


# ---------------------------------------------------------------------------
# 04-01: 웹 계층 시험을 위한 FastAPI 앱 픽스처.
# ---------------------------------------------------------------------------


@pytest.fixture
def web_app(tmp_db_path: Path, tmp_path: Path) -> FastAPI:
    """정적 파일 마운트 없이 `EventStore`만 임시 경로에 붙인 앱.

    그림 설정도 임시 경로로 돌려 놓는다 — 기본값(`.gptrpg/media`)을 그대로
    두면 시험이 저장소 안에 디렉터리를 만든다. 시험은 작업 디렉터리에 흔적을
    남기지 않아야 한다.
    """
    return create_app(
        db_path=tmp_db_path,
        imagery_config=imagery_config_from_env({"GPTRPG_IMAGERY_DIR": str(tmp_path / "media")}),
    )


@pytest.fixture
def web_client(web_app: FastAPI) -> Iterator[TestClient]:
    """`lifespan`이 돌아야 `app.state.store`가 채워지므로 `with` 문맥으로 연다."""
    with TestClient(web_app) as client:
        yield client


# ---------------------------------------------------------------------------
# 04-05: 선언·확인 경로 시험을 위한 대역 제공자 주입 픽스처.
# ---------------------------------------------------------------------------


@pytest.fixture
def web_client_with_fake_provider(
    tmp_db_path: Path, tmp_path: Path
) -> Callable[..., TestClient]:
    """`web_app`의 `provider_resolver`를 대역 제공자로 갈아 끼운 `TestClient`를 만드는 공장.

    역할별(`action_classifier`/`master_gm`) `FakeProvider` 인스턴스를 넘기면,
    그 인스턴스를 그대로 돌려주는 `provider_resolver`로 `create_app`을 만든다.
    `agent_config_path`는 임시 설정 파일을 가리킨다(역할별 provider/model 두
    칸만 있으면 되고 실제 API 키는 필요 없다 — `resolve_provider` 자체를
    갈아 끼웠으므로 이 파일의 `provider` 이름은 읽히기만 하고 실제로 제공자를
    만드는 데 쓰이지 않는다).

    반환값은 `with` 문맥으로 여는 `TestClient`다(`web_client`와 같은 이유 —
    `lifespan`이 돌아야 `app.state.store`가 채워진다).
    """

    def _make(
        *, action_classifier: FakeProvider, master_gm: FakeProvider | None = None
    ) -> TestClient:
        config_path = tmp_path / "agents.json"
        config_path.write_text(
            json.dumps(
                {
                    "action_classifier": {"provider": "nim", "model": "fake-model"},
                    "master_gm": {"provider": "nim", "model": "fake-model"},
                }
            ),
            encoding="utf-8",
        )
        providers: dict[str, FakeProvider] = {"action_classifier": action_classifier}
        if master_gm is not None:
            providers["master_gm"] = master_gm

        def _resolver(role: str, choices, env):
            return providers[role]

        app = create_app(
            db_path=tmp_db_path,
            provider_resolver=_resolver,
            agent_config_path=config_path,
            imagery_config=imagery_config_from_env(
                {"GPTRPG_IMAGERY_DIR": str(tmp_path / "media")}
            ),
        )
        return TestClient(app)

    return _make
