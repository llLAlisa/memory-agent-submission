"""Pydantic request and response models."""

from typing import List, Optional

from pydantic import BaseModel, Field


class AddMemoryRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128)
    content: str = Field(..., min_length=1, max_length=10000)
    timestamp: str = Field(..., min_length=1, max_length=64)


class AddMemoryResponse(BaseModel):
    status: str = "success"
    memory_id: str
    deduplicated: bool = False
    score: Optional[float] = None
    message: Optional[str] = None


class SearchRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128)
    query: str = Field(..., min_length=1, max_length=10000)
    limit: int = Field(5, ge=1, le=100)


class MemoryItem(BaseModel):
    content: str
    score: float
    timestamp: str


class SearchResponse(BaseModel):
    memories: List[MemoryItem]


class HealthResponse(BaseModel):
    status: str
    model: str
