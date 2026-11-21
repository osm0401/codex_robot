import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

DEFAULT_PORT = 8000
PROJECT_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_DIR / ".env"
PORT_ERROR = "APP_PORT는 1~65535 사이의 정수여야 합니다."
SPEED_ERROR = "BABY_SPEED는 1~30 사이의 정수여야 합니다."


@dataclass(frozen=True)
class Settings:
    port: int
    baby_speed: int
    data_dir: Path


def load_settings(env_file: Path = ENV_FILE) -> Settings:
    file_values = dotenv_values(env_file, encoding="utf-8-sig", interpolate=False)

    port = positive_setting(os.environ.get("APP_PORT", file_values.get("APP_PORT", str(DEFAULT_PORT))),
                            maximum=65535, error=PORT_ERROR)
    speed = positive_setting(os.environ.get("BABY_SPEED", file_values.get("BABY_SPEED", "1")),
                             maximum=30, error=SPEED_ERROR)
    data_dir = os.environ.get("DATA_DIR", file_values.get("DATA_DIR")) or "data"
    return Settings(port, speed, (PROJECT_DIR / data_dir).resolve())


def positive_setting(value: str | None, *, maximum: int, error: str) -> int:
    if value is None or not value.isascii() or not value.isdecimal():
        raise ValueError(error)

    # Strip leading zeroes before conversion so very long values fail cleanly.
    digits = value.lstrip("0")
    if not digits or len(digits) > len(str(maximum)) or int(digits) > maximum:
        raise ValueError(error)
    return int(digits)
