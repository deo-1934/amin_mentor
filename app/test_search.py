"""
test_search.py
---------------
تست عملکرد سیستم جست‌وجوی معنایی FAISS.
"""

import pickle
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from pathlib import Path


# مسیر فایل‌های ایندکس و داده‌ها
ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "faiss_index" / "index.faiss"
STORE_PATH = ROOT / "faiss_index" / "store.pkl"

# مدل Embedding مورد استفاده
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def load_index_and_data():
    """بارگذاری ایندکس FAISS و داده‌های متنی."""
    print("📦 در حال بارگذاری ایندکس و داده‌ها...")
    index = faiss.read_index(str(INDEX_PATH))
    with open(STORE_PATH, "rb") as f:
        store = pickle.load(f)
    return index, store


def semantic_search(query: str, top_k: int = 3):
    """جست‌وجوی معنایی پرسش در میان داده‌ها."""
    index, store = load_index_and_data()
    model = SentenceTransformer(MODEL_NAME)

    print("🧠 در حال محاسبه‌ی embedding برای پرسش...")
    q_embed = model.encode([query], normalize_embeddings=True)
    q_embed = np.asarray(q_embed, dtype="float32")

    print("🔎 جست‌وجو در ایندکس...")
    distances, indices = index.search(q_embed, top_k)

    print("\n✅ نتایج نزدیک‌ترین بخش‌ها:\n")
    for rank, (idx, dist) in enumerate(zip(indices[0], distances[0])):
        doc = store["docs"][idx]
        meta = store["meta"][idx]
        print(f"{rank+1}. ({meta['source']} - chunk {meta['chunk_idx']})")
        print(f"فاصله: {dist:.4f}")
        print(f"متن: {doc[:200]}...")
        print("-" * 80)


if __name__ == "__main__":
    q = input("❓ پرسش خود را وارد کنید: ")
    semantic_search(q)
