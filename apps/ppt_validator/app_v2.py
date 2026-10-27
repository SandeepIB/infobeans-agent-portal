"""FastAPI v2 application — PPT Review Platform.

Run with:
    uvicorn app_v2:app --host 0.0.0.0 --port 8002 --reload

Legacy app.py is untouched. This is the new v2 entry point.
"""
from __future__ import annotations
import os

from dotenv import load_dotenv
load_dotenv()
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.review import router as review_router
from api.health import router as health_router
from api.prompts import router as prompts_router
from api.rules import router as rules_router
from api.agents import router as agents_router
from api.observability import router as observability_router
from db.migrate import run as run_migrations

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup: running migrations")
    run_migrations()
    logger.info("startup: complete")
    yield
    logger.info("shutdown")


app = FastAPI(
    title="IB PPT Review Platform v2",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(review_router)
app.include_router(health_router)
app.include_router(prompts_router)
app.include_router(rules_router)
app.include_router(agents_router)
app.include_router(observability_router)
