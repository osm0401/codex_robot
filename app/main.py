from fastapi import FastAPI

app = FastAPI(title="AI 육아 로봇", docs_url=None, redoc_url=None)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
