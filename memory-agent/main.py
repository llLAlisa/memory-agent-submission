"""FastAPI entrypoint for the Agent Memory Service."""

import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request

from memory_store import MemoryStore
from models import (
    AddMemoryRequest,
    AddMemoryResponse,
    HealthResponse,
    SearchRequest,
    SearchResponse,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = "./chroma_data"
DEFAULT_MODEL = "all-MiniLM-L6-v2"


def create_app(memory_store: Optional[MemoryStore] = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.memory_store = memory_store or MemoryStore(
            persist_path=os.getenv("MEMORY_DB_PATH", DEFAULT_DB_PATH),
            model_name=os.getenv("EMBEDDING_MODEL", DEFAULT_MODEL),
            dedup_threshold=float(os.getenv("DEDUP_THRESHOLD", "0.85")),
        )
        logger.info(
            "memory service ready (db=%s, threshold=%.2f)",
            app.state.memory_store.persist_path,
            app.state.memory_store.dedup_threshold,
        )
        yield

    app = FastAPI(
        title="Agent Memory Service",
        description="Local vector memory service for the Agent Memory Challenge text track.",
        version="1.0.0",
        lifespan=lifespan,
    )

    @app.get("/", tags=["meta"])
    def root() -> dict:
        return {"service": "agent-memory-service", "docs": "/docs"}

    @app.get("/health", response_model=HealthResponse, tags=["meta"])
    def health() -> dict:
        return {
            "status": "ok",
            "model": os.getenv("EMBEDDING_MODEL", DEFAULT_MODEL),
        }

    @app.post(
        "/add",
        response_model=AddMemoryResponse,
        response_model_exclude_none=True,
        tags=["memory"],
    )
    def add_memory(payload: AddMemoryRequest, request: Request) -> dict:
        return request.app.state.memory_store.add(
            user_id=payload.user_id,
            content=payload.content,
            timestamp=payload.timestamp,
        )

    @app.post("/search", response_model=SearchResponse, tags=["memory"])
    def search_memory(payload: SearchRequest, request: Request) -> dict:
        results = request.app.state.memory_store.search(
            user_id=payload.user_id,
            query=payload.query,
            limit=payload.limit,
        )
        return {"memories": results}

    return app


app = create_app()
