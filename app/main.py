import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from dataclasses import asdict
from pathlib import Path
from sqlite3 import Error as SQLiteError
from time import monotonic, time

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.baby import rules
from app.baby.data import NEEDS, BehaviorDataError, load_catalog
from app.baby.engine import BabyEngine
from app.baby.store import BabyStore
from app.settings import Settings, load_settings

STATIC_DIR = Path(__file__).resolve().parent / "static"
logger = logging.getLogger(__name__)


class CareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: rules.Care


async def run_baby(app: FastAPI, engine: BabyEngine, store: BabyStore) -> None:
    next_save = monotonic() + rules.SAVE_SECONDS
    while True:
        await asyncio.sleep(1)
        event = engine.tick()
        if event is not None:
            app.state.last_baby_reaction = event
        now = monotonic()
        if now >= next_save:
            try:
                store.save(engine.state)
            except SQLiteError:
                logger.warning("아기 상태를 저장하지 못했습니다.")
            next_save = now + rules.SAVE_SECONDS


def baby_status(engine: BabyEngine) -> dict:
    signal = engine.current
    return {
        "age_months": engine.state.age_months,
        "emotion": signal.emotion if signal else "평온",
        "action": asdict(signal.action if signal else rules.NEUTRAL),
        "behavior_id": signal.behavior_id if signal else None,
        "signal": engine.catalog.behaviors[signal.behavior_id].label if signal else None,
        "needs": {key: getattr(engine.state, key) for key in sorted(NEEDS)},
        "demo": engine.speed != 1,
    }


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        config = settings or load_settings()
        catalog = load_catalog()
        signals = (*rules.CALM, rules.SLEEP, rules.EARLY_SLEEP,
                   *(signal for group in rules.SIGNALS.values() for signal in group))
        if any(signal.behavior_id not in catalog.behaviors for signal in signals):
            raise BehaviorDataError("아기 행동 규칙에 필요한 행동 ID가 CSV에 없습니다.")
        store = BabyStore(config.data_dir / "app.db")
        engine = BabyEngine(catalog, store.load(now=int(time())), speed=config.baby_speed)
        store.save(engine.state)
        app.state.baby = engine
        app.state.baby_store = store
        app.state.last_baby_reaction = None
        task = asyncio.create_task(run_baby(app, engine, store))
        try:
            yield
        finally:
            task.cancel()
            try:
                with suppress(asyncio.CancelledError):
                    await task
            finally:
                app.state.last_baby_reaction = None
                store.save(engine.state)

    app = FastAPI(title="AI 육아 로봇", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.exception_handler(RequestValidationError)
    async def invalid_input(request: Request, error: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": "돌봄 종류를 확인해 주세요."})

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", response_class=FileResponse)
    async def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/baby")
    async def status(request: Request) -> JSONResponse:
        return JSONResponse(baby_status(request.app.state.baby), headers={"Cache-Control": "no-store"})

    @app.get("/api/baby/sources")
    async def sources(request: Request) -> list[dict[str, str]]:
        return [asdict(source) for source in request.app.state.baby.catalog.sources]

    @app.post("/api/baby/care")
    async def care(body: CareRequest, request: Request) -> JSONResponse:
        origin = request.headers.get("origin")
        local_origin = f"{request.url.scheme}://{request.url.netloc}"
        if request.headers.get("sec-fetch-site") == "cross-site" or (origin is not None and origin != local_origin):
            raise HTTPException(403, "아기 화면에서 다시 시도해 주세요.")
        if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
            raise HTTPException(415, "돌봄 요청 형식을 확인해 주세요.")
        engine = request.app.state.baby
        previous, previous_signal = engine.state, engine.sleep_signal
        engine.apply_care(body.action)
        try:
            request.app.state.baby_store.save(engine.state)
        except SQLiteError:
            engine.state, engine.sleep_signal = previous, previous_signal
            raise HTTPException(503, "아기 상태를 저장하지 못했습니다. 다시 시도해 주세요.") from None
        return JSONResponse(baby_status(engine), headers={"Cache-Control": "no-store"})

    return app


app = create_app()
