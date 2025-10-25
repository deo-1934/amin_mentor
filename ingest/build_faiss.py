# ingest/build_faiss.py
# ساخت ایندکس FAISS از فایل‌های متنی داخل data/ + تولید meta.json
# اجرا:  python ingest/build_faiss.py

import os
import json
import glob
from pathlib import Path
from typing import List, Dict, Tuple

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# ---------- مسیرها ----------
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
OUT_DIR = BASE_DIR / "faiss_index"
OUT_DIR.mkdir(parents=True, exist_ok=True)

INDEX_PATH = OUT_DIR / "index.faiss"
META_PATH = OUT_DIR / "meta.json"

# ---------- تنظیمات ----------
EMB_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
FILE_EXTS = ["*.txt", "*.md"]
CHUNK_SIZE = 800           # تعداد کاراکتر
CHUNK_OVERLAP = 120        # همپوشانی بین چانک‌ها

# ---------- ابزارک‌ها ----------
def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")

def iter_text_files() -> List[Path]:
    files: List[Path] = []
    for ext in FILE_EXTS:
        files.extend([Path(p) for p in glob.glob(str(DATA_DIR / ext))])
    return sorted(files)

def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    text = text.strip()
    if not text:
        return []
    chunks = []
    i = 0
    n = len(text)
    while i < n:
        j = min(i + size, n)
        chunks.append(text[i:j])
        if j == n:
            break
        i = j - overlap
        if i < 0:
            i = 0
    return chunks

def l2_normalize(mat: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(mat, axis=1, keepdims=True) + 1e-12
    return mat / norms

# ---------- بدنه اصلی ----------
def build_corpus() -> Tuple[List[str], List[Dict]]:
    texts, metas = [], []
    files = iter_text_files()
    if not files:
        print(f"⚠️ هیچ فایل متنی در {DATA_DIR} پیدا نشد. ابتدا فایل‌هایی مثل .txt یا .md اضافه کن.")
        return texts, metas

    for fp in files:
        raw = read_text_file(fp)
        chunks = chunk_text(raw, CHUNK_SIZE, CHUNK_OVERLAP)
        for idx, ch in enumerate(chunks):
            texts.append(ch)
            metas.append({
                "source": fp.name,
                "path": str(fp.relative_to(BASE_DIR)),
                "chunk_idx": idx
            })

    print(f"✅ جمع‌آوری شد: {len(files)} فایل، {len(texts)} چانک")
    return texts, metas

def embed_texts(texts: List[str], model_name: str = EMB_MODEL_NAME) -> np.ndarray:
    if not texts:
        return np.empty((0, 384), dtype="float32")
    model = SentenceTransformer(model_name)
    emb = model.encode(texts, batch_size=64, show_progress_bar=True, convert_to_numpy=True, normalize_embeddings=True)
    # اگر normalize_embeddings=True باشد، IP ≡ cosine خواهد شد.
    return emb.astype("float32")

def build_faiss(embs: np.ndarray) -> faiss.Index:
    if embs.size == 0:
        raise RuntimeError("هیچ برداری برای ایندکس وجود ندارد (corpus خالی است).")
    dim = embs.shape[1]
    index = faiss.IndexFlatIP(dim)  # Inner Product (با نرمال‌سازی = cosine similarity)
    index.add(embs)
    return index

def main():
    print("🚧 شروع ساخت ایندکس...")
    texts, metas = build_corpus()
    if not texts:
        return

    embs = embed_texts(texts, EMB_MODEL_NAME)
    index = build_faiss(embs)

    faiss.write_index(index, str(INDEX_PATH))
    META_PATH.write_text(json.dumps({"texts": texts, "sources": metas}, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"🎯 ایندکس ذخیره شد → {INDEX_PATH}")
    print(f"📝 متادیتا ذخیره شد → {META_PATH}")
    print("✅ تمام.")

if __name__ == "__main__":
    main()
