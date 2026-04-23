import os
import numpy as np
from sentence_transformers import SentenceTransformer
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

THRESHOLD = float(os.getenv("CACHE_THRESHOLD", "0.80"))

_model = None
_client = None
_cache = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _get_client():
    global _client
    if _client is None:
        _client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    return _client


def _get_cache() -> list:
    global _cache
    if _cache is None:
        rows = _get_client().table("cache").select("question,answer,embedding").execute()
        _cache = rows.data or []
    return _cache


def _cosine_similarity(a: list, b: list) -> float:
    a, b = np.array(a), np.array(b)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def find_cached_answer(question: str, threshold: float = THRESHOLD):
    cache = _get_cache()
    if not cache:
        return None

    embedding = _get_model().encode(question).tolist()

    best_score, best_answer = 0.0, None
    for entry in cache:
        score = _cosine_similarity(embedding, entry["embedding"])
        if score > best_score:
            best_score = score
            best_answer = entry["answer"]

    return best_answer if best_score >= threshold else None


def add_to_cache(question: str, answer: str):
    embedding = _get_model().encode(question).tolist()
    entry = {"question": question, "answer": answer, "embedding": embedding}
    _get_client().table("cache").insert(entry).execute()
    cache = _get_cache()
    cache.append(entry)
