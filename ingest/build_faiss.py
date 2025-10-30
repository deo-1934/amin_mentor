# ingest/build_faiss.py
import os
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from pathlib import Path
from typing import List, Dict

def load_documents(data_dir: str = "data/") -> List[Dict[str, str]]:
    """
    بارگذاری فایل‌های متنی از پوشه `data/` و تقسیم آن‌ها به چانک‌ها.

    Args:
        data_dir (str): مسیر پوشه حاوی فایل‌های متنی.

    Returns:
        List[Dict[str, str]]: لیست چانک‌ها با متن و منبع.
    """
    documents = []
    for filename in os.listdir(data_dir):
        if filename.endswith(".txt"):
            filepath = os.path.join(data_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                documents.append({
                    "text": content,
                    "source": filename
                })
    return documents

def build_index(documents: List[Dict[str, str]], output_dir: str = "faiss_index") -> None:
    """
    ساخت ایندکس FAISS و ذخیره متادیتا.

    Args:
        documents (List[Dict[str, str]]): لیست چانک‌ها با متن و منبع.
        output_dir (str): مسیر خروجی برای ذخیره ایندکس و متادیتا.
    """
    # ایجاد پوشه خروجی اگر وجود ندارد
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # بارگذاری مدل امبدینگ
    model = SentenceTransformer("all-MiniLM-L6-v2")

    # استخراج متن‌ها و منابع
    texts = [doc["text"] for doc in documents]
    sources = [{"source": doc["source"], "chunk_idx": i} for i, doc in enumerate(documents)]

    # امبدینگ متن‌ها
    embeddings = model.encode(texts)

    # ساخت ایندکس FAISS
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)

    # ذخیره ایندکس FAISS
    faiss.write_index(index, os.path.join(output_dir, "index.faiss"))

    # ذخیره متادیتا
    meta = {
        "texts": texts,
        "sources": sources
    }
    with open(os.path.join(output_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    # بارگذاری و پردازش فایل‌ها
    documents = load_documents()

    # ساخت ایندکس
    build_index(documents)

    print("ایندکس FAISS و متادیتا با موفقیت ساخته شدند!")
