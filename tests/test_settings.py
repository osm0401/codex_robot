import pytest

from app.settings import PROJECT_DIR, load_settings


def test_default_port_without_env_file(tmp_path, monkeypatch):
    monkeypatch.delenv("APP_PORT", raising=False)

    assert load_settings(tmp_path / ".env").port == 8000


def test_process_environment_overrides_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("APP_PORT=8100\n", encoding="utf-8")
    monkeypatch.delenv("APP_PORT", raising=False)

    assert load_settings(env_file).port == 8100

    monkeypatch.setenv("APP_PORT", "65535")

    assert load_settings(env_file).port == 65535


@pytest.mark.parametrize("value", ["", "0", "65536", "-1", "abc", "８０００", "1" * 5000])
def test_invalid_ports_are_rejected(tmp_path, monkeypatch, value):
    monkeypatch.setenv("APP_PORT", value)

    with pytest.raises(ValueError, match="APP_PORT는 1~65535"):
        load_settings(tmp_path / ".env")


def test_baby_settings_resolve_relative_to_project(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("BABY_SPEED=30\nDATA_DIR=data/test\n", encoding="utf-8")
    monkeypatch.delenv("BABY_SPEED", raising=False)
    monkeypatch.delenv("DATA_DIR", raising=False)
    monkeypatch.chdir(tmp_path)
    settings = load_settings(env_file)
    assert settings.baby_speed == 30
    assert settings.data_dir == PROJECT_DIR / "data" / "test"

    monkeypatch.setenv("BABY_SPEED", "31")
    with pytest.raises(ValueError, match="BABY_SPEED는 1~30"):
        load_settings(env_file)
