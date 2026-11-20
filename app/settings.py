import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

DEFAULT_PORT = 8000
ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
PORT_ERROR = "APP_PORT는 1~65535 사이의 정수여야 합니다."


@dataclass(frozen=True)
class Settings:
    port: int


def load_settings(env_file: Path = ENV_FILE) -> Settings:
    value = os.environ.get("APP_PORT")
    if value is None:
        file_values = dotenv_values(env_file, encoding="utf-8-sig", interpolate=False)
        value = file_values.get("APP_PORT", str(DEFAULT_PORT))

    if value is None or not value.isascii() or not value.isdecimal():
        raise ValueError(PORT_ERROR)

    # Strip leading zeroes before conversion so very long values fail cleanly.
    digits = value.lstrip("0")
    if not digits or len(digits) > 5 or int(digits) > 65535:
        raise ValueError(PORT_ERROR)

    return Settings(port=int(digits))
