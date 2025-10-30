# app/retriever.py
from __future__ import annotations
import os
import glob
from functools import lru_cache
from typing import List, Dict, Any, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer
from numpy.linalg import norm


# ========== ۱. مسیرهای ممکن برای داده‌ها ==========
# ما سعی می‌کنیم داده‌ها رو از این پوشه‌ها بخونیم:
CANDIDATE_DATA_DIRS = [
    # حالت production تمیز
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "ingest", "data"),
    # حالت ساده‌ای که تو الان استفاده می‌کنی (پوشه data کنار ریشه‌ی repo)
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "data"),
]


# ========== ۲. پارامترهای برش متن و انتخاب نتایج ==========
CHUNK_SEPARATOR = "\n\n"  # یعنی پاراگراف‌ها با خط خالی جدا بشن
TOP_K_DEFAULT = 5
EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def _debug(msg: str):
    # اگر لازم شد می‌تونی این رو silent کنی برای Cloud
    print(f"[retriever] {msg}")


# ========== ۳. خواندن همه فایل‌های .txt از مسیرهای معتبر ==========
def _load_raw_chunks_from_dirs() -> List[Tuple[str, str]]:
    """
    خروجی: لیست تاپل‌های (chunk_text, source_info)
    - chunk_text: متن هر تکه
    - source_info: منبع (نام فایل و شماره‌ی چانک)
    """
    chunks: List[Tuple[str, str]] = []

    for candidate_dir in CANDIDATE_DATA_DIRS:
        if not os.path.isdir(candidate_dir):
            continue

        _debug(f"checking data dir: {candidate_dir}")
        txt_files = glob.glob(os.path.join(candidate_dir, "*.txt"))

        for path in txt_files:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    full_text = f.read().strip()
            except Exception as e:
                _debug(f"failed reading {path}: {e}")
                continue

            # بر اساس خط خالی split می‌کنیم تا پاراگراف‌های معنادار بسازیم
            raw_chunks = [c.strip() for c in full_text.split(CHUNK_SEPARATOR) if c.strip()]

            for idx, ch in enumerate(raw_chunks):
                source_info = f"{os.path.basename(path)}[chunk:{idx}]"
                chunks.append((ch, source_info))

    return chunks


# ========== ۴. ساخت امبدینگ‌ها (lazy, cache) ==========
@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    _debug(f"loading embedding model: {EMBED_MODEL_NAME}")
    return SentenceTransformer(EMBED_MODEL_NAME)


@lru_cache(maxsize=1)
def _get_index() -> Dict[str, Any]:
    """
    خروجی این تابع:
    {
        "chunks": [ "متن چانک۱", "متن چانک۲", ...],
        "sources": [ "file.txt[chunk:0]", ...],
        "embeddings": ndarray(float32) با شکل (N, dim)
    }
    """
    data_pairs = _load_raw_chunks_from_dirs()
    if not data_pairs:
        _debug("no data found in either data/ or ingest/data/")
        return {"chunks": [], "sources": [], "embeddings": np.zeros((0, 384), dtype="float32")}

    chunks = [p[0] for p in data_pairs]
    sources = [p[1] for p in data_pairs]

    model = _get_model()
    _debug(f"embedding {len(chunks)} chunks...")
    embs = model.encode(chunks, convert_to_numpy=True, show_progress_bar=False).astype("float32")

    return {
        "chunks": chunks,
        "sources": sources,
        "embeddings": embs,
    }


# ========== ۵. شباهت کسینوسی و رتبه‌بندی ==========
def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    # safe cosine similarity
    denom = (norm(a) * norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _search(query: str, top_k: int = TOP_K_DEFAULT) -> List[Dict[str, Any]]:
    """
    ورودی: query (سوال کاربر)
    خروجی: لیست دیکشنری مثل:
    {
        "text": "...",
        "source": "d.txt[chunk:0]",
        "distance": 0.123  # هر چی کمتر باشه یعنی نزدیک‌تر؟
    }

    نکته: ما از شباهت کسینوسی استفاده می‌کنیم
    ولی برای سازگاری با قبلی "distance" رو 1 - sim می‌ذاریم.
    """

    idx = _get_index()
    chunks = idx["chunks"]
    sources = idx["sources"]
    embs = idx["embeddings"]

    if len(chunks) == 0:
        _debug("empty index, returning fallback msg")
        return []

    model = _get_model()
    q_emb = model.encode([query], convert_to_numpy=True, show_progress_bar=False)[0].astype("float32")

    scored: List[Tuple[int, float]] = []
    for i, emb in enumerate(embs):
        sim = _cosine_sim(q_emb, emb)
        # برای تفسیر قدیمی، distance رو 1 - similarity نگه می‌داریم
        distance = 1.0 - sim
        scored.append((i, distance))

    # sort by distance ASC (کمتر = بهتر)
    scored.sort(key=lambda x: x[1])

    top_hits = scored[: top_k]
    results: List[Dict[str, Any]] = []
    for i, dist in top_hits:
        results.append({
            "text": chunks[i],
            "source": sources[i],
            "distance": float(dist),
        })

    return results


# ========== ۶. API اصلی که ui.py صداش می‌زنه ==========
@lru_cache(maxsize=1)
def _get_singleton() -> "Retriever":
    return Retriever()


class Retriever:
    def retrieve(self, query: str, top_k: int = TOP_K_DEFAULT) -> List[Dict[str, Any]]:
        return _search(query, top_k=top_k)


# این تابعی بود که ui.py داشت ازش استفاده می‌کرد
def retrieve(query: str, top_k: int = TOP_K_DEFAULT) -> List[Dict[str, Any]]:
    return _get_singleton().retrieve(query, top_k=top_k)
