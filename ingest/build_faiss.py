"""
build_faiss.py
---------------
ایجاد ایندکس معنایی با FAISS برای فایل‌های متنی پروژه.

شرح عملکرد:
- متن فایل‌های موجود در مسیر ./data را می‌خواند.
- هر متن را به قطعات کوچک‌تر (chunk) تقسیم می‌کند.
- برای هر قطعه، embedding معنایی تولید می‌کند.
- ایندکس FAISS می‌سازد و داده‌ها را در فایل ذخیره می‌کند.

پیش‌نیازها:
    pip install faiss-cpu sentence-transformers numpy

خروجی:
    ./faiss_index/index.faiss
    ./faiss_index/store.pkl
"""

from __future__ import annotations
import os
import uuid
import pickle
import glob
from pathlib import Path
from typing import List, Dict, Tuple
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer


# مسیرهای پروژه
ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
INDEX_DIR = ROOT_DIR / "faiss_index"
INDEX_DIR.mkdir(parents=True, exist_ok=True)

# تنظیمات
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"  # 384 بعد
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """تقسیم متن به قطعات با طول ثابت."""
    text = " ".join(text.split())
    chunks, i = [], 0
    while i < len(text):
        chunks.append(text[i:i + size])
        i += max(1, size - overlap)
    return [c for c in chunks if c.strip()]


def load_text_files() -> Tuple[List[str], List[Dict]]:
    """خواندن تمام فایل‌های متنی از مسیر data و تقسیم آن‌ها به قطعات."""
    files = sorted(glob.glob(str(DATA_DIR / "*.txt")))
    if not files:
        raise FileNotFoundError(f"هیچ فایل متنی در مسیر {DATA_DIR} پیدا نشد.")
    documents, metadata = [], []
    for path in files:
        text = Path(path).read_text(encoding="utf-8", errors="ignore")
        chunks = chunk_text(text)
        for i, ch in enumerate(chunks):
            documents.append(ch)
            metadata.append({"id": str(uuid.uuid4()), "source": os.path.basename(path), "chunk_idx": i})
    return documents, metadata


def build_faiss_index(vectors: np.ndarray) -> faiss.Index:
    """ایجاد ایندکس FAISS بر اساس بردارها."""
    dim = vectors.shape[1]
    index = faiss.IndexHNSWFlat(dim, 32)
    index.hnsw.efConstruction = 200
    index.add(vectors)
    return index


def main() -> None:
    """اجرای کامل فرآیند ساخت ایندکس."""
    print(f"📂 مسیر داده‌ها: {DATA_DIR}")
    documents, metadata = load_text_files()
    print(f"✅ تعداد کل قطعات: {len(documents)}")

    # تولید embedding
    print("🔄 در حال محاسبه‌ی embedding...")
    model = SentenceTransformer(MODEL_NAME)
    embeddings = model.encode(documents, normalize_embeddings=True, batch_size=64, show_progress_bar=True)
    embeddings = np.asarray(embeddings, dtype="float32")

    # ساخت ایندکس
    print("⚙️ در حال ساخت ایندکس FAISS...")
    index = build_faiss_index(embeddings)

    # ذخیره فایل‌ها
    faiss.write_index(index, str(INDEX_DIR / "index.faiss"))
    with open(INDEX_DIR / "store.pkl", "wb") as f:
        pickle.dump({"docs": documents, "meta": metadata, "model": MODEL_NAME}, f)

    print("🎯 ایندکس ساخته و ذخیره شد.")
    print(f"📦 مسیر ایندکس: {INDEX_DIR / 'index.faiss'}")
    print(f"🗂️ مسیر داده‌ها: {INDEX_DIR / 'store.pkl'}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ خطا: {e}")
