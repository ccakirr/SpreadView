from fastapi import FastApi

from routers.analysis import router as analysis_router

app = FastApi(
    title="SpreadView API",
    version="0.1.0"
)

app.include_router(
    analysis_router,
    prefix="api/v1",
)
