"""그림 층 시험 — **torch/diffusers 없이 전부 돈다.**

그림 꾸러미는 선택 의존성이다(`pyproject.toml`의 `[project.optional-dependencies]`).
이 파일의 시험 하나라도 실제 모델을 요구하면 시험 묶음이 2.5GB 설치와 6.9GB
내려받기를 전제하게 되고, 그 순간 「1.8초에 끝나는 399개」라는 성질이 깨진다.
그래서 `FakeRenderer`를 끼워 넣는다 — `create_app`의 `renderer_factory` 이음매가
있는 이유가 이것이다(`provider_resolver`가 네트워크를 걷어낸 것과 같은 방식).

여기서 확인하는 성질:

- 프롬프트가 **결정적**이고 모르는 값에 안 터진다 (AI 없이 조립하는 근거)
- 삽화 사건이 **상태를 바꾸지 않지만 폴링을 깨뜨리지도 않는다** (reducer 분기)
- 그림 실패가 **턴을 실패시키지 않는다**
- 기본값이 **꺼짐**이다 (실험 측정에 끼어들지 않는다)
"""

import json
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from conftest import FakeProvider
from gptrpg.imagery import (
    ImageryConfig,
    RenderedImage,
    RendererUnavailable,
    imagery_config_from_env,
    portrait_prompt,
    scene_prompt,
    seed_for,
)
from gptrpg.imagery.scene_prompt import (
    GENERIC_SETTING,
    MAX_PROMPT_CHARS,
    WELL_SCENARIO_SETTING,
)
from gptrpg.imagery.styles import DEFAULT_STYLE, STYLES, unknown_style_fallback
from gptrpg.rulebooks import RULEBOOKS
from gptrpg.rulebooks.moves import get_moves
from gptrpg.rules_core.reducer import fold
from gptrpg.turn.context import CLOCK_SEGMENT_COUNT
from gptrpg.web.app import create_app
from gptrpg.web.characters_data import PLAYER_CHARACTERS
from gptrpg.web.portraits import (
    CHARACTER_APPEARANCES,
    generate_portraits,
    portrait_relative_path,
    portrait_seed,
)

SESSION_ID = "s1"
_NARRATION_TEXT = "문이 요란하게 부서진다. 안에서 서늘한 바람이 흘러나온다."

_ONE_PIXEL_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)
"""1픽셀 PNG. 시험은 **바이트가 파일로 그대로 갔는지**만 보므로 진짜 그림이
필요 없다. 그림의 내용은 이 층의 책임이 아니다(모델의 책임이다)."""


class FakeRenderer:
    """`Renderer` 프로토콜을 torch 없이 구현하는 대역.

    받은 인자를 전부 `self.calls`에 쌓는다 — 프롬프트·씨앗이 실제로 무엇으로
    불렸는지 시험이 확인해야 한다. `fail_with`를 주면 그 예외를 던진다.
    """

    def __init__(self, *, fail_with: Exception | None = None) -> None:
        self.calls: list[tuple[str, str, int]] = []
        self.fail_with = fail_with
        self.warm_up_count = 0

    def warm_up(self) -> None:
        self.warm_up_count += 1

    def render(self, prompt: str, *, style: str, seed: int) -> RenderedImage:
        self.calls.append((prompt, style, seed))
        if self.fail_with is not None:
            raise self.fail_with
        return RenderedImage(
            png=_ONE_PIXEL_PNG,
            prompt=prompt,
            style=style,
            seed=seed,
            steps=4,
            size=512,
            latency_ms=1234,
        )


# ---------------------------------------------------------------------------
# 프롬프트 조립 — 결정적이고, 모르는 값에 안 터진다
# ---------------------------------------------------------------------------


def test_scene_prompt_is_deterministic() -> None:
    """같은 판정은 같은 프롬프트. 이 성질이 없으면 사건 기록으로 그림을 다시 만들 수 없다."""
    kwargs = {
        "move": "hack_and_slash",
        "grade": "strong_hit",
        "clock_segment": 1,
        "style": DEFAULT_STYLE,
        "setting": WELL_SCENARIO_SETTING,
    }
    assert scene_prompt(**kwargs) == scene_prompt(**kwargs)


def test_scene_prompt_contains_move_grade_and_setting() -> None:
    prompt = scene_prompt(
        move="volley",
        grade="miss",
        clock_segment=0,
        style=DEFAULT_STYLE,
        setting=WELL_SCENARIO_SETTING,
    )
    assert "archer" in prompt  # volley
    assert "goes wrong" in prompt  # miss
    assert "village well" in prompt  # 시나리오 배경

    # 그림체 프리셋 — **문구를 여기 다시 적지 않는다.** `STYLES`가 유일한
    # 출처다. 예전에는 프리셋의 첫 몇 단어를 문자열로 박아 두었는데,
    # CLIP의 77토큰 상한에 맞춰 프리셋을 짧게 고치자(`styles.py` 도크스트링)
    # 이 시험이 **그림체가 빠졌기 때문이 아니라 단어가 바뀌었기 때문에**
    # 깨졌다. 템플릿의 `{subject}` 앞뒤 조각이 둘 다 들어 있는지를 보면
    # 프리셋 문구를 자유롭게 고치면서도 "프리셋이 실제로 붙는다"는 성질만
    # 지킬 수 있다.
    head, tail = STYLES[DEFAULT_STYLE].split("{subject}")
    assert head.strip() in prompt
    assert tail.strip(", ") in prompt


def test_scene_prompt_unknown_move_and_grade_fall_back_without_raising() -> None:
    """세 번째 룰북의 모르는 무브·등급이 턴을 깨뜨리지 않는다.

    플랫폼이 특정 룰북의 어휘를 안다고 가정하지 않는다는 원칙(`labels.ts`와
    같은 태도)을 그림 쪽에서도 지킨다.
    """
    prompt = scene_prompt(
        move="완전히_새로운_무브",
        grade="완전히_새로운_등급",
        clock_segment=0,
        style=DEFAULT_STYLE,
    )
    assert "an adventurer facing danger" in prompt
    assert "tense uncertain moment" in prompt
    assert GENERIC_SETTING in prompt


@pytest.mark.parametrize("segment", [-5, 0, 4, 99])
def test_scene_prompt_clamps_clock_segment(segment: int) -> None:
    """시계 칸 수가 나중에 바뀌어도 IndexError가 나지 않는다."""
    assert scene_prompt(
        move="defend", grade="weak_hit", clock_segment=segment, style=DEFAULT_STYLE
    )


def test_unknown_style_falls_back_to_default() -> None:
    assert unknown_style_fallback("없는그림체") == DEFAULT_STYLE
    assert unknown_style_fallback("dungeon-ink") == "dungeon-ink"


def test_portrait_prompt_uses_portrait_style() -> None:
    assert "head and shoulders" in portrait_prompt("a wandering swordsman")


# ---------------------------------------------------------------------------
# 씨앗 — 실행 사이에 값이 같아야 한다
# ---------------------------------------------------------------------------


def test_seed_for_is_stable_across_calls_and_bounded_to_32_bits() -> None:
    """`hash()`를 쓰지 않았음을 값으로 고정한다 — `hash()`는 실행마다 달라진다."""
    assert seed_for("s1", 7) == seed_for("s1", 7)
    assert seed_for("s1", 7) != seed_for("s1", 8)
    assert 0 <= seed_for("s1", 7) < 2**32


def test_portrait_seed_differs_per_character() -> None:
    seeds = {portrait_seed(cid) for cid in CHARACTER_APPEARANCES}
    assert len(seeds) == len(CHARACTER_APPEARANCES)


# ---------------------------------------------------------------------------
# 설정 — 기본값이 꺼짐이고, 오타에 안 터진다
# ---------------------------------------------------------------------------


def test_imagery_is_disabled_by_default() -> None:
    """실험 측정(H1/H5)에 그림이 끼어들지 않는 것이 기본이다."""
    assert imagery_config_from_env({}).enabled is False


@pytest.mark.parametrize("raw", ["1", "true", "TRUE", "yes", "on"])
def test_imagery_enable_accepts_common_true_spellings(raw: str) -> None:
    assert imagery_config_from_env({"GPTRPG_IMAGERY": raw}).enabled is True


@pytest.mark.parametrize("raw", ["", "0", "false", "no", "아니오", "켜짐"])
def test_imagery_enable_treats_anything_else_as_off(raw: str) -> None:
    """오타가 조용히 「켜짐」이 되지 않는다 — 켜는 것은 명시적 선택이어야 한다."""
    assert imagery_config_from_env({"GPTRPG_IMAGERY": raw}).enabled is False


def test_imagery_config_bad_numbers_and_styles_fall_back() -> None:
    """설정 오타 하나로 서버가 뜨지 못하는 것보다 기본값으로 도는 편이 낫다."""
    config = imagery_config_from_env(
        {
            "GPTRPG_IMAGERY_STEPS": "헛소리",
            "GPTRPG_IMAGERY_SIZE": "-3",
            "GPTRPG_IMAGERY_STYLE": "없는그림체",
        }
    )
    assert config.steps == 4
    assert config.size == 512
    assert config.style == DEFAULT_STYLE


# ---------------------------------------------------------------------------
# 초상화 — 캐릭터 넷과 열쇠가 같아야 한다
# ---------------------------------------------------------------------------


def test_every_player_character_has_an_appearance() -> None:
    """캐릭터를 추가하고 겉모습을 잊으면 그 캐릭터만 초상화 없이 남는다.

    `CHARACTER_ARCHETYPES`(한국어 화면 캡션)와 달리 이쪽은 영어 그림 지시라
    두 사전이 갈라져 있다 — 그래서 잊기 쉽고, 그래서 고정한다.
    """
    assert set(CHARACTER_APPEARANCES) == set(PLAYER_CHARACTERS)


def test_generate_portraits_writes_files_and_skips_existing(tmp_path: Path) -> None:
    renderer = FakeRenderer()
    written = generate_portraits(
        renderer, media_dir=tmp_path, character_ids=["bram", "nari"]
    )
    assert [path.name for path in written] == ["bram.png", "nari.png"]
    assert (tmp_path / portrait_relative_path("bram")).read_bytes() == _ONE_PIXEL_PNG

    # 두 번째 호출은 이미 있는 파일을 건너뛴다 — 세션 당일 선·호두만 다시
    # 뽑을 때 브람·나리를 헛되게 다시 만들지 않아야 한다.
    again = generate_portraits(renderer, media_dir=tmp_path, character_ids=["bram", "nari"])
    assert again == []
    assert len(renderer.calls) == 2


def test_generate_portraits_force_overwrites(tmp_path: Path) -> None:
    renderer = FakeRenderer()
    generate_portraits(renderer, media_dir=tmp_path, character_ids=["bram"])
    generate_portraits(renderer, media_dir=tmp_path, character_ids=["bram"], force=True)
    assert len(renderer.calls) == 2


def test_generate_portraits_seed_offset_changes_the_seed(tmp_path: Path) -> None:
    """마음에 드는 얼굴이 나올 때까지 돌릴 손잡이가 실제로 씨앗을 바꾼다."""
    renderer = FakeRenderer()
    generate_portraits(renderer, media_dir=tmp_path, character_ids=["bram"])
    generate_portraits(
        renderer, media_dir=tmp_path, character_ids=["bram"], force=True, seed_offset=1
    )
    assert renderer.calls[0][2] != renderer.calls[1][2]


# ---------------------------------------------------------------------------
# 웹 계층 — 대역 렌더러를 끼운 앱
# ---------------------------------------------------------------------------


def _imagery_client(
    tmp_db_path: Path,
    tmp_path: Path,
    *,
    renderer: FakeRenderer,
    enabled: bool = True,
) -> TestClient:
    """그림 설정과 대역 렌더러를 끼운 `TestClient`.

    `conftest.web_client_with_fake_provider`와 같은 구조지만 그림 이음매 두
    자리(`imagery_config`/`renderer_factory`)를 추가로 넘긴다.
    """
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
    providers = {
        "action_classifier": FakeProvider(
            complete_value=json.dumps([{"move": "parley", "stat": "CHA"}])
        ),
        "master_gm": FakeProvider(stream_text=_NARRATION_TEXT),
    }
    app = create_app(
        db_path=tmp_db_path,
        provider_resolver=lambda role, choices, env: providers[role],
        agent_config_path=config_path,
        imagery_config=ImageryConfig(
            enabled=enabled,
            media_dir=tmp_path / "media",
            style=DEFAULT_STYLE,
            steps=4,
            size=512,
            model="fake-model",
        ),
        renderer_factory=lambda config: renderer,
    )
    return TestClient(app)


def _run_one_turn(client: TestClient) -> dict:
    declare = client.post(
        f"/api/sessions/{SESSION_ID}/actions/declare",
        json={
            "player_id": "p1",
            "character_id": "bram",
            "raw_text": "경비병을 설득해 통로를 열어 보려 한다",
            "rulebook_id": "dungeonworld_like",
        },
    )
    assert declare.status_code == 200
    confirm = client.post(
        f"/api/sessions/{SESSION_ID}/actions/confirm",
        json={
            "player_id": "p1",
            "move": "parley",
            "stat": "CHA",
            "suggestion_move": "parley",
            "suggestion_stat": "CHA",
            "confirmed": True,
            "declare_seq": declare.json()["declare_seq"],
            "target": 10,
            "rulebook_id": "dungeonworld_like",
            "character_id": "bram",
            "modifiers": [],
        },
    )
    assert confirm.status_code == 200
    return confirm.json()


def _events_of_type(client: TestClient, event_type: str) -> list[dict]:
    response = client.get(f"/api/sessions/{SESSION_ID}/events")
    assert response.status_code == 200
    return [e for e in response.json()["events"] if e["event_type"] == event_type]


def test_enabled_turn_records_scene_illustrated_and_writes_the_file(
    tmp_db_path: Path, tmp_path: Path
) -> None:
    renderer = FakeRenderer()
    with _imagery_client(tmp_db_path, tmp_path, renderer=renderer) as client:
        body = _run_one_turn(client)
        illustrations = _events_of_type(client, "scene_illustrated")

    assert len(illustrations) == 1
    event = illustrations[0]
    # 삽화는 판정 사건에 매달린다 — 화면이 어느 판정의 그림인지 알아야 한다.
    assert event["caused_by_seq"] == body["resolve_seq"]
    assert event["style"] == DEFAULT_STYLE
    assert event["image_path"] == f"/media/scenes/{SESSION_ID}/{body['resolve_seq']:06d}.png"
    # 응답에 실린 주소가 실제 파일과 같은 자리를 가리켜야 한다.
    written = tmp_path / "media" / f"scenes/{SESSION_ID}/{body['resolve_seq']:06d}.png"
    assert written.read_bytes() == _ONE_PIXEL_PNG


def test_scene_illustration_does_not_change_game_state(tmp_db_path: Path, tmp_path: Path) -> None:
    """그림은 판정·실패 누적·시계 어디에도 닿지 않는다 — `last_seq` 하나만 따라 올린다.

    **판정 결과를 단정하지 않는다.** 이 턴은 실제 주사위를 굴리므로
    `failure_count`가 0인지 1인지는 굴림에 따라 달라진다(그걸 단정했다가
    전체 실행에서만 깨졌다). 대신 같은 사건 목록을 **삽화만 빼고** 한 번 더
    접어 두 상태를 비교한다 — 굴림이 무엇이든 성립하고, 주장하려는 성질
    자체를 직접 재는 방식이다.

    동시에 **폴링이 살아 있어야 한다** — `reducer`에 `scene_illustrated` 분기가
    없으면 이 요청이 `UnknownEventType`으로 500이 되고, 삽화가 한 장 남은
    세션은 그 뒤로 영영 열리지 않는다(사건은 지워지지 않으므로 기능을 다시
    꺼도 낫지 않는다).
    """
    renderer = FakeRenderer()
    with _imagery_client(tmp_db_path, tmp_path, renderer=renderer) as client:
        _run_one_turn(client)
        response = client.get(f"/api/sessions/{SESSION_ID}/events")
        assert response.status_code == 200
        payload = response.json()

    events = payload["events"]
    illustrations = [e for e in events if e["event_type"] == "scene_illustrated"]
    assert len(illustrations) == 1

    with_illustration = fold(SESSION_ID, [(e["event_type"], e) for e in events])
    without_illustration = fold(
        SESSION_ID,
        [(e["event_type"], e) for e in events if e["event_type"] != "scene_illustrated"],
    )
    # 삽화를 빼도 상태 숫자가 전부 같다. 다른 것은 마지막 순번뿐이다.
    assert replace(with_illustration, last_seq=without_illustration.last_seq) == (
        without_illustration
    )
    assert with_illustration.last_seq == illustrations[0]["seq"]

    # 굴림과 무관하게 고정된 두 숫자만 따로 확인한다.
    assert payload["state"]["check_count"] == 1
    assert payload["state"]["narration_count"] == 2


def test_disabled_by_default_records_nothing(tmp_db_path: Path, tmp_path: Path) -> None:
    renderer = FakeRenderer()
    with _imagery_client(tmp_db_path, tmp_path, renderer=renderer, enabled=False) as client:
        _run_one_turn(client)
        illustrations = _events_of_type(client, "scene_illustrated")

    assert illustrations == []
    assert renderer.calls == []


def test_renderer_failure_leaves_the_turn_successful(tmp_db_path: Path, tmp_path: Path) -> None:
    """그림 꾸러미가 없거나 모델을 못 올려도 턴은 200으로 끝난다.

    그림은 있으면 좋은 것이다 — 실험 세션 도중 GPU가 말썽이라고 게임이
    멈추면 재미(H1) 측정 자체가 불가능해진다.
    """
    renderer = FakeRenderer(fail_with=RendererUnavailable("꾸러미 없음"))
    with _imagery_client(tmp_db_path, tmp_path, renderer=renderer) as client:
        body = _run_one_turn(client)
        illustrations = _events_of_type(client, "scene_illustrated")
        narrations = _events_of_type(client, "narration_appended")

    assert body["confirmed"] is True
    assert len(narrations) == 2
    assert illustrations == []
    assert len(renderer.calls) == 1


def test_renderer_unexpected_exception_also_leaves_the_turn_successful(
    tmp_db_path: Path, tmp_path: Path
) -> None:
    """`RendererUnavailable` 말고 무엇이 터져도 마찬가지다(배경 작업이므로)."""
    renderer = FakeRenderer(fail_with=RuntimeError("예상 못한 실패"))
    with _imagery_client(tmp_db_path, tmp_path, renderer=renderer) as client:
        body = _run_one_turn(client)
        illustrations = _events_of_type(client, "scene_illustrated")

    assert body["confirmed"] is True
    assert illustrations == []


def test_rejected_confirm_makes_no_illustration(tmp_db_path: Path, tmp_path: Path) -> None:
    """거부된 확인은 판정이 없으므로 그릴 장면도 없다."""
    renderer = FakeRenderer()
    with _imagery_client(tmp_db_path, tmp_path, renderer=renderer) as client:
        declare = client.post(
            f"/api/sessions/{SESSION_ID}/actions/declare",
            json={
                "player_id": "p1",
                "character_id": "bram",
                "raw_text": "경비병을 설득해 통로를 열어 보려 한다",
                "rulebook_id": "dungeonworld_like",
            },
        )
        client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm",
            json={
                "player_id": "p1",
                "move": "parley",
                "stat": "CHA",
                "suggestion_move": "parley",
                "suggestion_stat": "CHA",
                "confirmed": False,
                "declare_seq": declare.json()["declare_seq"],
                "target": 10,
                "rulebook_id": "dungeonworld_like",
                "character_id": "bram",
                "modifiers": [],
            },
        )
        illustrations = _events_of_type(client, "scene_illustrated")

    assert illustrations == []
    assert renderer.calls == []


def test_scene_prompt_reaches_the_renderer_with_the_actual_move_and_grade(
    tmp_db_path: Path, tmp_path: Path
) -> None:
    """렌더러가 받은 프롬프트가 그 턴의 무브·시나리오를 반영해야 한다."""
    renderer = FakeRenderer()
    with _imagery_client(tmp_db_path, tmp_path, renderer=renderer) as client:
        _run_one_turn(client)

    prompt, style, _seed = renderer.calls[0]
    assert "bargaining" in prompt  # parley
    assert "village well" in prompt  # M0 시나리오 배경
    assert style == DEFAULT_STYLE


def test_media_is_mounted_before_the_frontend_catch_all(
    tmp_db_path: Path, tmp_path: Path
) -> None:
    """`/media/...`가 프론트엔드 포괄 경로에 삼켜지지 않는지 확인한다.

    순서가 뒤집히면 그림 자리마다 index.html이 내려가고, 화면에는 깨진
    이미지만 보인다 — 서버 로그에는 200만 남으므로 눈으로는 원인을 못 찾는다.
    """
    static_dir = tmp_path / "dist"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<html>프론트엔드</html>", encoding="utf-8")
    media_dir = tmp_path / "media"
    (media_dir / "scenes").mkdir(parents=True)
    (media_dir / "scenes" / "x.png").write_bytes(_ONE_PIXEL_PNG)

    app = create_app(
        db_path=tmp_db_path,
        static_dir=static_dir,
        imagery_config=ImageryConfig(
            enabled=False,
            media_dir=media_dir,
            style=DEFAULT_STYLE,
            steps=4,
            size=512,
            model="fake-model",
        ),
        renderer_factory=lambda config: FakeRenderer(),
    )
    with TestClient(app) as client:
        response = client.get("/media/scenes/x.png")
        assert response.status_code == 200
        assert response.content == _ONE_PIXEL_PNG
        # 포괄 경로 자체는 살아 있어야 한다.
        assert client.get("/").status_code == 200


# ---------------------------------------------------------------------------
# 초상화 주소 — 파일이 있을 때만 채운다
# ---------------------------------------------------------------------------


def test_character_list_portrait_url_is_null_without_files(
    tmp_db_path: Path, tmp_path: Path
) -> None:
    """초상화를 아직 안 뽑았다고 입장 화면이 깨지지 않는다."""
    with _imagery_client(tmp_db_path, tmp_path, renderer=FakeRenderer()) as client:
        summaries = client.get(f"/api/sessions/{SESSION_ID}/characters").json()

    assert summaries
    assert all(summary["portrait_url"] is None for summary in summaries)


def test_character_list_portrait_url_points_at_the_written_file(
    tmp_db_path: Path, tmp_path: Path
) -> None:
    media_dir = tmp_path / "media"
    generate_portraits(FakeRenderer(), media_dir=media_dir, character_ids=["bram"])

    with _imagery_client(tmp_db_path, tmp_path, renderer=FakeRenderer()) as client:
        summaries = client.get(f"/api/sessions/{SESSION_ID}/characters").json()
        by_id = {summary["character_id"]: summary for summary in summaries}
        assert by_id["bram"]["portrait_url"] == "/media/portraits/bram.png"
        assert by_id["nari"]["portrait_url"] is None
        # 그 주소가 실제로 내려와야 한다.
        assert client.get(by_id["bram"]["portrait_url"]).content == _ONE_PIXEL_PNG


# ---------------------------------------------------------------------------
# 그림체 이름은 사건에 남는 값이다
# ---------------------------------------------------------------------------


def test_default_style_exists_in_the_style_table() -> None:
    """기본 그림체 이름이 사전에서 사라지면 매 턴 `KeyError`가 난다."""
    assert DEFAULT_STYLE in STYLES


# ---------------------------------------------------------------------------
# 프롬프트 길이 — CLIP 77토큰 상한을 넘기지 않는다
# ---------------------------------------------------------------------------


def test_every_real_move_and_grade_combination_fits_the_prompt_budget() -> None:
    """**등록된 룰북의 모든 무브 × 등급 × 시계칸 조합**이 길이 예산 안에 있어야 한다.

    CLIP은 77토큰을 넘는 입력의 뒤쪽을 조용히 버린다(경고 한 줄만 남는다).
    프리셋이 프롬프트 뒤쪽에 오므로, 예산을 넘기면 **그림체 지시가 먼저
    잘려 나간다** — 실제로 처음 쓴 판이 그랬다(조합 5,600개 중 2,617개에서
    프리셋 꼬리가 잘렸고, 화면에는 아무 오류도 보이지 않았다).

    여기서 토큰이 아니라 글자를 재는 이유는 `MAX_PROMPT_CHARS` 도크스트링에
    있다 — 토크나이저는 선택 의존성이라 이 시험이 쓸 수 없다.

    새 룰북·새 무브가 등록되면 이 시험이 그 조합까지 자동으로 덮는다.
    """
    too_long: list[tuple[int, str, str, str]] = []
    for rulebook_id, rulebook in RULEBOOKS.items():
        grades = [band.name for band in rulebook.grade_bands]
        for move in get_moves(rulebook_id):
            for grade in grades:
                for segment in range(CLOCK_SEGMENT_COUNT + 1):
                    for style in STYLES:
                        prompt = scene_prompt(
                            move=move.move_id,
                            grade=grade,
                            clock_segment=segment,
                            style=style,
                            setting=WELL_SCENARIO_SETTING,
                        )
                        if len(prompt) > MAX_PROMPT_CHARS:
                            too_long.append((len(prompt), style, move.move_id, grade))

    assert too_long == [], f"길이 예산({MAX_PROMPT_CHARS}자) 초과 {len(too_long)}건: {too_long[:3]}"


def test_every_character_portrait_prompt_fits_the_prompt_budget() -> None:
    """초상화 프롬프트도 같은 예산을 지킨다 — 겉모습 문장을 늘리다 넘기기 쉽다."""
    too_long = {
        character_id: len(portrait_prompt(appearance))
        for character_id, appearance in CHARACTER_APPEARANCES.items()
        if len(portrait_prompt(appearance)) > MAX_PROMPT_CHARS
    }
    assert too_long == {}


def test_style_templates_all_take_a_subject_slot() -> None:
    """`{subject}` 자리가 빠진 프리셋은 프롬프트를 조용히 버린다."""
    for name, template in STYLES.items():
        assert "{subject}" in template, name
