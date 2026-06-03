from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.workflow_routes import ApiResponse, router as workflow_router
from app.config import SCREEN_RPA_STATIC_DIST
from app.db.database import db, init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    if db.is_closed():
        db.connect(reuse_if_open=True)
    yield


app = FastAPI(title="Screen RPA Workflow API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(workflow_router, prefix="/api")


@app.exception_handler(Exception)
async def unhandled(_, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"success": False, "code": 5000, "message": str(exc), "data": None},
    )


@app.get("/health")
def health() -> ApiResponse:
    return ApiResponse(data={"status": "ok"})


if SCREEN_RPA_STATIC_DIST is not None:
    app.mount(
        "/",
        StaticFiles(directory=str(SCREEN_RPA_STATIC_DIST), html=True),
        name="spa",
    )
