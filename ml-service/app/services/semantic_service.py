import numpy as np
from typing import List, Tuple, Optional
from sentence_transformers import SentenceTransformer
from ..config import EMBEDDING_MODEL_NAME

_MODEL_INSTANCE: Optional[SentenceTransformer] = None


def get_semantic_model() -> SentenceTransformer:
    global _MODEL_INSTANCE
    if _MODEL_INSTANCE is None:
        try:
            _MODEL_INSTANCE = SentenceTransformer(EMBEDDING_MODEL_NAME)
        except Exception:
            _MODEL_INSTANCE = SentenceTransformer("all-MiniLM-L6-v2")
    return _MODEL_INSTANCE


class SemanticService:
    """Calculates semantic embeddings and cosine similarity scores between prompts."""

    @classmethod
    def cosine_similarity(cls, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))

    @classmethod
    def calculate_similarity(cls, text_a: str, text_b: str) -> float:
        if not text_a or not text_b:
            return 0.0
        if text_a.strip() == text_b.strip():
            return 1.0

        model = get_semantic_model()
        embeddings = model.encode([text_a, text_b], convert_to_numpy=True, normalize_embeddings=True)
        similarity = float(np.dot(embeddings[0], embeddings[1]))
        return max(0.0, min(1.0, round(similarity, 4)))

    @classmethod
    def calculate_batch_similarities(cls, pairs: List[Tuple[str, str]]) -> List[float]:
        if not pairs:
            return []
        model = get_semantic_model()
        texts_a = [p[0] for p in pairs]
        texts_b = [p[1] for p in pairs]
        
        emb_a = model.encode(texts_a, convert_to_numpy=True, normalize_embeddings=True)
        emb_b = model.encode(texts_b, convert_to_numpy=True, normalize_embeddings=True)

        scores = [
            max(0.0, min(1.0, round(float(np.dot(emb_a[i], emb_b[i])), 4)))
            for i in range(len(pairs))
        ]
        return scores
