import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

_client = None


def _get_supabase():
    global _client
    if _client is None:
        _client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    return _client


def log_interaction(question: str, answer: str, cache_hit: bool, response_time_ms: int):
    try:
        _get_supabase().table("logs").insert({
            "question": question,
            "answer": answer,
            "cache_hit": cache_hit,
            "response_time_ms": response_time_ms,
        }).execute()
    except Exception as e:
        print(f"[logger] Failed to log: {e}")
