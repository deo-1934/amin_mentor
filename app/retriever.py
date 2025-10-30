# app/retriever.py
import faiss
import json
import numpy as np
from sentence_transformers import SentenceTransformer
from pathlib import Path
from typing import List, Dict, Optional

class Retriever:
    """
    کلاس برای جست‌وجوی اطلاعات با استفاده از FAISS و SentenceTransformers.
    """

    def __init__(
        self,
        index_path: str = "faiss_index/index.faiss",
        meta_path: str = "faiss_index/meta.json",
        model_name: str = "all-MiniLM-L6-v2"
    ):
        """
        مقداردهی اولیه مدل و بارگذاری ایندکس FAISS و متادیتا.

        Args:
            index_path (str): مسیر فایل ایندکس FAISS.
            meta_path (str): مسیر فایل متادیتا (متن‌ها و منابع).
            model_name (str): نام مدل SentenceTransformers برای امبدینگ.
        """
        self.model = SentenceTransformer(model_name)
        self.index = faiss.read_index(index_path)

        with open(meta_path, "r", encoding="utf-8") as f:
            self.meta = json.load(f)

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, str]]:
        """
        جست‌وجوی متن‌های مرتبط با کوئری در ایندکس FAISS.

        Args:
            query (str): متن کوئری برای جست‌وجو.
            top_k (int): تعداد نتایج برتر برای برگرداندن.

        Returns:
            List[Dict[str, str]]: لیست نتایج شامل متن، منبع، و فاصله.
        """
        query_embedding = self.model.encode([query])
        distances, indices = self.index.search(query_embedding, top_k)

        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx != -1:  # FAISS ممکن است -1 برگرداند اگر نتایج کافی نباشد
                results.append({
                    "text": self.meta["texts"][idx],
                    "source": self.meta["sources"][idx],
                    "distance": float(distance)
                })

        return results
