"""Local sentence embedding wrapper."""

from typing import List

from sentence_transformers import SentenceTransformer


class Embedder:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        self._model = SentenceTransformer(model_name)

    def embed(self, text: str) -> List[float]:
        vector = self._model.encode(text, normalize_embeddings=True)
        return vector.tolist()
