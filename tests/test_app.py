"""Smoke-test the Streamlit UI end to end with streamlit's AppTest."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "dashboard.py")


def make(tmp_path, monkeypatch, **env):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    return AppTest.from_file(APP, default_timeout=30)


def test_renders_without_exception(tmp_path, monkeypatch):
    at = make(tmp_path, monkeypatch).run()
    assert not at.exception


def test_production_requires_password(tmp_path, monkeypatch):
    at = make(tmp_path, monkeypatch, APP_ENV="production").run()
    assert any("APP_PASSWORD" in e.value for e in at.error)
    assert len(at.tabs) == 0


def test_password_gate(tmp_path, monkeypatch):
    at = make(tmp_path, monkeypatch, APP_PASSWORD="s3cret").run()
    assert len(at.tabs) == 0
    at.text_input[0].set_value("wrong"); at.button[0].click(); at.run()
    assert len(at.tabs) == 0 and at.error
    at.text_input[0].set_value("s3cret"); at.button[0].click(); at.run()
    assert len(at.tabs) > 0 and not at.exception


def test_add_platform_and_save(tmp_path, monkeypatch):
    at = make(tmp_path, monkeypatch).run()
    at.text_input(key="add_plat_name").set_value("DoorDash")
    at.button(key="add_plat_btn").click(); at.run()
    assert not at.exception
    assert any(p.name == "DoorDash" for p in at.session_state.manager.platforms)
