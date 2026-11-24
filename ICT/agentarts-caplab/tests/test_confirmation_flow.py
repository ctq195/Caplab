"""网页所用 invocation 契约：原草稿绑定、拒绝、重试与跨身份隔离。"""
import importlib
from pathlib import Path
import sys
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    monkeypatch.setenv("CAPLAB_OFFLINE", "1")
    monkeypatch.setenv("CAPLAB_LOCAL_DATA", str(tmp_path))
    for key in ("DATABASE_URL", "MAAS_API_KEY", "CAPLAB_USE_WEB_MODEL"):
        monkeypatch.delenv(key, raising=False)
    app = importlib.import_module("app")
    yield app
    app.resources.close()
    sys.modules.pop("app", None)


def test_original_proposal_only(runtime):
    chat = {"_server_user_id": "student-a", "session_id": uuid4().hex}
    def call(**fields):
        return runtime.handle({**chat, **fields})
    first = call(message="了解实习")
    token = first["proposal"]["token"]
    assert first["revision"] == 0 and not first["confirmed_goal"]
    confirm = dict(action="confirm", confirmation_text="确认", decision="confirm", token=token)
    assert runtime.handle({**chat, **confirm, "_server_user_id":"student-b"})["status"] == "error"
    assert call(**{**confirm,"confirmation_text":""})["status"] == "error"
    assert call(**{**confirm,"decision":"reject"})["revision"] == 0
    next_round = call(action="propose_goal", message="比较到岗时长")
    assert next_round["proposal"]["token"] != token
    assert call(**confirm)["status"] == "error"
    confirm["token"] = next_round["proposal"]["token"]
    for _ in range(2):
        result = call(**confirm)
        assert result["status"] == "success" and result["revision"] == 1
    assert call(action="status")["confirmed_goal"] == "比较到岗时长"
    assert runtime.handle({**chat,"action":"status","_server_user_id":"student-b"})["confirmed_goal"] is None
