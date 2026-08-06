"""ChromaDB-backed memory store with per-user collections and dedup."""

import hashlib
import logging
import threading
import uuid
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from embedder import Embedder

logger = logging.getLogger(__name__)

DEFAULT_COLLECTION_PREFIX = "user_mem_"


class MemoryStore:
    """Each user_id owns a dedicated Chroma collection."""

    def __init__(
        self,
        persist_path: str = "./chroma_data",
        model_name: str = "all-MiniLM-L6-v2",
        dedup_threshold: float = 0.85,
        embedder: Optional[Any] = None,
    ) -> None:
        if not 0.0 <= dedup_threshold <= 1.0:
            raise ValueError("dedup_threshold must be between 0.0 and 1.0")

        self.persist_path = persist_path
        self.dedup_threshold = dedup_threshold
        self._embedder = embedder or Embedder(model_name)
        self._write_lock = threading.Lock()
        self._client = chromadb.PersistentClient(
            path=persist_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

    @staticmethod
    def _collection_name(user_id: str) -> str:
        digest = hashlib.sha1(user_id.encode("utf-8")).hexdigest()[:32]
        return f"{DEFAULT_COLLECTION_PREFIX}{digest}"

    def _collection_for(self, user_id: str):
        return self._client.get_or_create_collection(
            name=self._collection_name(user_id),
            metadata={"hnsw:space": "cosine"},
        )

    def add(self, user_id: str, content: str, timestamp: str) -> Dict[str, Any]:
        """Add a memory, skipping writes for semantically duplicate content."""
        embedding = self._embedder.embed(content)

        with self._write_lock:
            collection = self._collection_for(user_id)
            duplicate = self._find_duplicate(collection, embedding)
            if duplicate is not None:
                logger.info(
                    "duplicate memory for user=%s, keeping id=%s, score=%.4f",
                    user_id,
                    duplicate["memory_id"],
                    duplicate["score"],
                )
                return {
                    "status": "success",
                    "memory_id": duplicate["memory_id"],
                    "deduplicated": True,
                    "score": round(duplicate["score"], 4),
                    "message": "duplicate memory discarded; existing memory returned",
                }

            memory_id = str(uuid.uuid4())
            collection.add(
                ids=[memory_id],
                embeddings=[embedding],
                documents=[content],
                metadatas=[{"user_id": user_id, "timestamp": timestamp}],
            )
            logger.info("stored memory id=%s for user=%s", memory_id, user_id)
            return {
                "status": "success",
                "memory_id": memory_id,
                "deduplicated": False,
                "score": 1.0,
            }

    def search(self, user_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search the user's own collection and return top-K results."""
        collection = self._collection_for(user_id)
        embedding = self._embedder.embed(query)
        result = collection.query(
            query_embeddings=[embedding],
            n_results=limit,
            include=["documents", "metadatas", "distances"],
        )

        ids = (result.get("ids") or [[]])[0]
        if not ids:
            return []

        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        memories: List[Dict[str, Any]] = []

        for document, metadata, distance in zip(documents, metadatas, distances):
            score = 1.0 - float(distance)
            score = round(max(0.0, min(1.0, score)), 4)
            memories.append(
                {
                    "content": document,
                    "score": score,
                    "timestamp": metadata.get("timestamp", ""),
                }
            )
        return memories

    def _find_duplicate(self, collection, embedding: List[float]) -> Optional[Dict[str, Any]]:
        result = collection.query(
            query_embeddings=[embedding],
            n_results=1,
            include=["documents", "distances", "metadatas"],
        )
        ids = (result.get("ids") or [[]])[0]
        if not ids:
            return None

        distance = float((result.get("distances") or [[]])[0][0])
        similarity = 1.0 - distance
        if similarity > self.dedup_threshold:
            return {"memory_id": ids[0], "score": similarity}
        return None
