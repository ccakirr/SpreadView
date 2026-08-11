from fastapi import FastAPI

from routers.analysis import router as analysis_router

app = FastAPI(
    title="SpreadView API",
    version="0.1.0"
)

app.include_router(
    analysis_router,
    prefix="/api/v1",
)


@app.get("/")
def health():
    return {
        "status": "ok"
    }
