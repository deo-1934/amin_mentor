import os
import json
import faiss
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer

# مسیر اصلی پروژه
BASE_DIR = Path(__file__).resolve().parents[1]
INDEX_DIR = BASE_DIR / "faiss_index"   # مسیر صحیح بر اساس ساختار پوشه‌های تو

class Retriever:
    def __init__(self, embed_model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(embed_model)
        index_path = INDEX_DIR / "index.faiss"

        if not index_path.exists():
            raise FileNotFoundError(f"فايل ایندکس پیدا نشد: {index_path}")

        self.index = faiss.read_index(str(index_path))

        # اگه meta.json هم داری می‌تونی منبع و متن‌ها رو نگه داری
        meta_path = INDEX_DIR / "meta.json"
        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            self.texts = meta.get("texts", [])
            self.sources = meta.get("sources", [])
        else:
            self.texts = []
            self.sources = []

    def search(self, query: str, k: int = 5):
        """بر اساس جمله کاربر، k تا نزدیک‌ترین بخش متن رو برمی‌گردونه"""
        q_emb = self.model.encode([query], convert_to_numpy=True)
        q_emb = q_emb / (np.linalg.norm(q_emb, axis=1, keepdims=True) + 1e-10)

        scores, idxs = self.index.search(q_emb.astype(np.float32), k)
        results = []

        for score, idx in zip(scores[0], idxs[0]):
            if idx == -1:
                continue
            text = self.texts[idx] if self.texts else f"متن شماره {idx}"
            source = self.sources[idx]["source"] if self.sources else "نامشخص"
            results.append({
                "score": float(score),
                "text": text,
                "source": source
            })

        return results
