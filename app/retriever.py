# app/retriever.py
from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
import numpy as np

# تلاش برای import streamlit (فقط برای کش). اگر نبود، کش را خنثی می‌کنیم.
try:
    import streamlit as st
    cache_resource = st.cache_resource
except Exception:
    def cache_resource(func=None, **_):
        return func

# مدل کوچک و سریع
DEFAULT_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
INDEX_DIR = Path("faiss_index")
INDEX_PATH = INDEX_DIR / "index.faiss"
META_PATH = INDEX_DIR / "meta.json"

# --- ابزارها ---
def _chunk_text(text: str, max_chars: int = 700) -> List[str]:
    text = " ".join((text or "").split())
    chunks = []
    cursor = 0
    while cursor < len(text):
        end = min(cursor + max_chars, len(text))
        # شکستن روی فاصله برای تمیزی
        if end < len(text):
            sp = text.rfind(" ", cursor, end)
            if sp != -1 and sp > cursor + 200:
                end = sp
        chunks.append(text[cursor:end].strip())
        cursor = end
    return [c for c in chunks if c]

def _load_corpus(data_dir: Path = Path("data")) -> List[Dict[str, Any]]:
    docs = []
    for p in sorted(data_dir.glob("*.txt")):
        content = p.read_text(encoding="utf-8", errors="ignore")
        parts = _chunk_text(content)
        for i, part in enumerate(parts):
            docs.append({"text": part, "source": {"file": p.name, "chunk_idx": i}})
    return docs

@cache_resource(show_spinner=False)
def _get_model(name: str = DEFAULT_EMBED_MODEL):
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(name)

def _embed_texts(texts: List[str]) -> np.ndarray:
    model = _get_model()
    vecs = model.encode(texts)
    return np.array(vecs, dtype="float32")

def _build_index(docs: List[Dict[str, Any]]):
    import faiss
    texts = [d["text"] for d in docs]
    embs = _embed_texts(texts)
    dim = embs.shape[1]
    index = faiss.IndexFlatIP(dim)
    # نرمال‌سازی برای Cosine similarity با Inner Product
    faiss.normalize_L2(embs)
    index.add(embs)
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(INDEX_PATH))
    META_PATH.write_text(json.dumps({"texts": texts, "sources": [d["source"] for d in docs]}, ensure_ascii=False), encoding="utf-8")

def _ensure_index():
    if INDEX_PATH.exists() and META_PATH.exists():
        return
    docs = _load_corpus()
    if not docs:
        INDEX_DIR.mkdir(parents=True, exist_ok=True)
        META_PATH.write_text(json.dumps({"texts": [], "sources": []}, ensure_ascii=False), encoding="utf-8")
        # ایندکس خالی
        import faiss
        index = faiss.IndexFlatIP(384)  # dim مدل MiniLM
        faiss.write_index(index, str(INDEX_PATH))
        return
    _build_index(docs)

@cache_resource(show_spinner=False)
def _load_index_and_meta():
    import faiss
    _ensure_index()
    index = faiss.read_index(str(INDEX_PATH))
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    return index, meta

def retrieve(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    if not query or not query.strip():
        return []
    index, meta = _load_index_and_meta()

    # embed پرسش و search
    q = _embed_texts([query])
    import faiss
    faiss.normalize_L2(q)
    distances, indices = index.search(q, top_k)

    texts = meta.get("texts", [])
    sources = meta.get("sources", [])
    results: List[Dict[str, Any]] = []
    for idx, dist in zip(indices[0], distances[0]):
        idx = int(idx)
        if idx < 0 or idx >= len(texts):
            continue
        results.append({"text": texts[idx], "source": sources[idx], "distance": float(dist)})
    return results
