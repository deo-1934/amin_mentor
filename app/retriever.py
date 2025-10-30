# app/retriever.py
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import List, Dict, Any, Optional

import numpy as np
from sentence_transformers import SentenceTransformer

try:
    import faiss  # faiss-cpu در requirements.txt هست
except Exception as e:
    faiss = None

from .settings import INDEX_PATH, META_PATH, DEFAULT_EMBED_MODEL


class Retriever:
    """
    بازیاب مبتنی بر FAISS + SentenceTransformers.
    - ایندکس: faiss_index/index.faiss
    - متادیتا: faiss_index/meta.json (یا فایل اشتباهی metajson)
    """

    def __init__(
        self,
        index_path: Optional[Path] = None,
        meta_path: Optional[Path] = None,
        model_name: str = DEFAULT_EMBED_MODEL,
    ) -> None:
        self.index_path = Path(index_path or INDEX_PATH)
        self.meta_path = Path(meta_path or META_PATH)
        self.model_name = model_name

        # مدل امبدینگ
        self.model = SentenceTransformer(self.model_name)

        # بارگذاری ایندکس FAISS
        self.index = self._load_index()
        # بارگذاری متادیتا
        self.meta = self._load_meta()

    def _load_index(self):
        if faiss is None:
            raise RuntimeError("faiss در دسترس نیست. لطفاً faiss-cpu را نصب کنید (در requirements.txt موجود است).")
        if not self.index_path.exists():
            raise FileNotFoundError(
                f"ایندکس FAISS پیدا نشد: {self.index_path} — ابتدا ایندکس را بساز: python ingest/build_faiss.py"
            )
        return faiss.read_index(str(self.index_path))

    def _load_meta(self) -> Dict[str, Any]:
        # حالت استاندارد
        if self.meta_path.exists():
            with open(self.meta_path, "r", encoding="utf-8") as f:
                return json.load(f)
        # اگر اشتباهی با نام metajson ذخیره شده باشد، همان را بخوان
        alt = self.meta_path.with_name("metajson")
        if alt.exists():
            with open(alt, "r", encoding="utf-8") as f:
                return json.load(f)
        raise FileNotFoundError(
            f"فایل متادیتا پیدا نشد: {self.meta_path} (یا metajson). لطفاً ingest/build_faiss.py را اجرا کن."
        )

    def _embed(self, texts: List[str]) -> np.ndarray:
        vecs = self.model.encode(texts)
        vecs = np.array(vecs, dtype="float32")
        return vecs

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if not query or not query.strip():
            return []

        q = self._embed([query])
        distances, indices = self.index.search(q, top_k)

        texts = self.meta.get("texts") or []
        sources = self.meta.get("sources") or []

        results: List[Dict[str, Any]] = []
        for idx, dist in zip(indices[0], distances[0]):
            idx = int(idx)
            if idx < 0:
                continue
            text = texts[idx] if idx < len(texts) else ""
            src = sources[idx] if idx < len(sources) else {}
            results.append({"text": text, "source": src, "distance": float(dist)})
        return results


# ——— سازگاری با import در UI ———
@lru_cache(maxsize=1)
def _get_singleton() -> Retriever:
    return Retriever()

def retrieve(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    return _get_singleton().retrieve(query, top_k)
