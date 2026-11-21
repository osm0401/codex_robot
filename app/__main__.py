import sys

import uvicorn

from app.main import app
from app.settings import load_settings


def main() -> int:
    try:
        settings = load_settings()
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2

    uvicorn.run(app, host="127.0.0.1", port=settings.port, workers=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
