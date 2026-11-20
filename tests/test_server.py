import json
import os
import socket
import subprocess
import sys
import time
from http.client import HTTPConnection

from app import __main__ as launcher
from app import settings


def test_env_file_cannot_override_bind_address(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("APP_PORT=8100\nHOST=0.0.0.0\nUVICORN_HOST=::\n", encoding="utf-8")
    monkeypatch.delenv("APP_PORT", raising=False)
    monkeypatch.setattr(launcher, "load_settings", lambda: settings.load_settings(env_file))
    calls = []

    def capture_run(app, *, host, port, workers):
        calls.append((host, port))

    monkeypatch.setattr(launcher.uvicorn, "run", capture_run)

    assert launcher.main() == 0
    assert calls == [("127.0.0.1", 8100)]


def test_server_runs_on_loopback_and_returns_health(tmp_path):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]

    env = {**os.environ, "APP_PORT": str(port), "HOST": "0.0.0.0", "UVICORN_HOST": "::"}
    log = tmp_path / "server.log"
    command = [sys.executable, "-m", "app"]
    with log.open("wb") as output, subprocess.Popen(
        command, env=env, stdout=output, stderr=subprocess.STDOUT
    ) as server:
        try:
            deadline = time.monotonic() + 15
            address = f"http://127.0.0.1:{port}"
            while time.monotonic() < deadline and server.poll() is None:
                if f"Uvicorn running on {address}" in log.read_text(encoding="utf-8"):
                    break
                time.sleep(0.05)
            else:
                raise AssertionError(log.read_text(encoding="utf-8", errors="replace"))

            connection = HTTPConnection("127.0.0.1", port, timeout=5)
            try:
                connection.request("GET", "/health")
                response = connection.getresponse()
                assert response.status == 200
                assert json.loads(response.read()) == {"status": "ok"}
            finally:
                connection.close()
        finally:
            if server.poll() is None:
                server.terminate()
                try:
                    server.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()


def test_invalid_configuration_fails_without_echoing_value():
    result = subprocess.run(
        [sys.executable, "-m", "app"],
        env={**os.environ, "APP_PORT": "invalid-value"},
        capture_output=True,
        timeout=10,
    )

    assert result.returncode == 2
    assert b"APP_PORT" in result.stderr
    assert b"invalid-value" not in result.stderr
