"""G-11-2 — 웹 서버 기동 시 실측 미달 모델이면 stderr에 경고, 기동은 막지 않는다.

`create_app()`의 `lifespan`이 실제로 도는 지점(`with TestClient(app) as
client`)에서 경고가 찍히는지 확인한다 — 요청을 하나도 안 보내도(연결만
열어도) 뜬다는 것이 기동 시점 검사라는 뜻이다.
"""

import json

from fastapi.testclient import TestClient

from gptrpg.imagery import imagery_config_from_env
from gptrpg.web.app import create_app


def _make_app(tmp_path, config_payload: dict):
    config_path = tmp_path / "agents.json"
    config_path.write_text(json.dumps(config_payload), encoding="utf-8")
    return create_app(
        db_path=tmp_path / "events.db",
        agent_config_path=config_path,
        imagery_config=imagery_config_from_env({"GPTRPG_IMAGERY_DIR": str(tmp_path / "media")}),
    )


def test_server_startup_warns_when_action_classifier_is_known_undersized(tmp_path, capsys):
    app = _make_app(
        tmp_path,
        {
            "action_classifier": {"provider": "nim", "model": "meta/llama-3.1-8b-instruct"},
            "master_gm": {"provider": "nim", "model": "nvidia/nemotron-3-ultra-550b-a55b"},
        },
    )

    with TestClient(app):
        pass  # lifespan startup만으로 충분하다 — 요청을 보내지 않는다

    err = capsys.readouterr().err
    assert "경고" in err
    assert "action_classifier" in err
    assert "meta/llama-3.1-8b-instruct" in err
    assert "막지 않는다" in err


def test_server_startup_has_no_warning_for_recommended_models(tmp_path, capsys):
    app = _make_app(
        tmp_path,
        {
            "action_classifier": {
                "provider": "nim",
                "model": "nvidia/nemotron-3-super-120b-a12b",
            },
            "master_gm": {"provider": "nim", "model": "nvidia/nemotron-3-ultra-550b-a55b"},
        },
    )

    with TestClient(app):
        pass

    assert "경고" not in capsys.readouterr().err


def test_server_startup_does_not_fail_when_config_file_is_missing(tmp_path, capsys):
    """설정 파일이 아예 없어도(새 환경) 기동 자체는 막히지 않는다 — 이 검사
    때문에 서버가 안 뜨면 그 자체가 새로운 조용한 실패가 된다."""
    app = create_app(
        db_path=tmp_path / "events.db",
        agent_config_path=tmp_path / "does-not-exist.json",
        imagery_config=imagery_config_from_env({"GPTRPG_IMAGERY_DIR": str(tmp_path / "media")}),
    )

    with TestClient(app) as client:
        response = client.get("/api/sessions/s1/events")
        assert response.status_code == 200

    assert "경고" not in capsys.readouterr().err
