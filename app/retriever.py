# app/retriever.py
import json
from pathlib import Path
from typing import List, Dict

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from app.settings import INDEX_DIR, DEFAULT_EMBED_MODEL

class Retriever:
    def __init__(self, embed_model: str = DEFAULT_EMBED_MODEL):
        self.model_name = embed_model
        self.model = SentenceTransformer(embed_model)

        index_path = INDEX_DIR / "index.faiss"
        if not index_path.exists():
            raise FileNotFoundError(
                f"فايل ایندکس یافت نشد: {index_path}. ابتدا `python ingest/build_faiss.py` را اجرا کن."
            )
        self.index = faiss.read_index(str(index_path))

        # متادیتا اختیاری
        self.texts: List[str] = []
        self.sources: List[Dict] = []
        meta_path = INDEX_DIR / "meta.json"
        if meta_path.exists():
            with meta_path.open("r", encoding="utf-8") as f:
                meta = json.load(f)
            self.texts = meta.get("texts", [])
            self.sources = meta.get("sources", [])

    def _embed(self, text: str) -> np.ndarray:
        vec = self.model.encode([text], convert_to_numpy=True, normalize_embeddings=True).astype("float32")
        return vec

    def search(self, query: str, k: int = 5) -> List[Dict]:
        q = self._embed(query)  # (1, d)
        scores, idxs = self.index.search(q, k)  # (1, k)
        results: List[Dict] = []
        for score, idx in zip(scores[0], idxs[0]):
            if idx == -1:
                continue
            text = self.texts[idx] if idx < len(self.texts) else f"[chunk #{idx}]"
            source_meta = self.sources[idx] if idx < len(self.sources) else {}
            source = source_meta.get("source", "نامشخص")
            path = source_meta.get("path", "")
            chunk_idx = source_meta.get("chunk_idx", idx)
            results.append({
                "score": float(score),
                "text": text,
                "source": source,
                "path": path,
                "chunk_idx": int(chunk_idx)
            })
        return results
