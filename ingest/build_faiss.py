# ingest/build_faiss.py
# ساخت ایندکس FAISS از فایل‌های متنی داخل پوشه data/
# خروجی: D:/Amin_Mentor/faiss_index/index.faiss  +  meta.json

import os
import json
import glob
from pathlib import Path

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer


# ---------- تنظیم مسیرها ----------
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
OUT_DIR = BASE_DIR / "faiss_index"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------- تنظیمات ----------
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
MAX_CHARS = int(os.getenv("CHUNK_MAX_CHARS", "800"))
OVERLAP = int(os.getenv("CHUNK_OVERLAP", "120"))
BATCH_SIZE = int(os.getenv("EMBED_BATCH", "64"))

# الگوهای فایل‌ ورودی
FILE_EXTS = ("*.txt", "*.md", "*.srt", "*.vtt")


def chunk_text(text: str, max_chars: int = MAX_CHARS, overlap: int = OVERLAP):
    """
    متن را به چانک‌های همپوشان تقسیم می‌کند. از لوپ بی‌نهایت جلوگیری می‌شود.
    """
    text = text.strip().replace("\r", "")
    if max_chars <= 0:
        raise ValueError("max_chars must be > 0")

    if overlap >= max_chars:
        # برای پایداری اگر کسی overlap را بزرگ گذاشته بود، منطقی‌اش می‌کنیم
        overlap = max_chars // 4

    step = max_chars - overlap
    chunks = []
    i = 0
    n = len(text)

    while i < n:
        end = min(i + max_chars, n)
        chunk = text[i:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == n:
            break  # به انتهای متن رسیدیم
        i += step  # با گام ثابت جلو برویم (نه بازگشت به عقب)

    return chunks


def read_text_file(path: Path) -> str:
    """
    خواندن امن فایل‌های متنی با UTF-8 و نادیده‌گرفتن خطاهای کاراکتر.
    """
    return path.read_text(encoding="utf-8", errors="ignore")


def build_corpus():
    texts, sources = [], []
    # جمع‌آوری فایل‌ها
    found_any = False
    for ext in FILE_EXTS:
        for fp in glob.glob(str(DATA_DIR / ext)):
            found_any = True
            p = Path(fp)
            raw = read_text_file(p)
            for ch in chunk_text(raw):
                texts.append(ch)
                sources.append({"source": p.name})
    if not found_any:
        raise SystemExit(f"⚠️ No input files found in {DATA_DIR}. "
                         f"Put .txt/.md/.srt/.vtt files there and rerun.")
    if not texts:
        raise SystemExit("⚠️ Files were found but produced no chunks. "
                         "Check CHUNK_MAX_CHARS/CHUNK_OVERLAP or file encoding.")
    return texts, sources


def main():
    print(f"📂 DATA_DIR: {DATA_DIR}")
    print(f"📦 OUT_DIR : {OUT_DIR}")
    print(f"🔤 MODEL   : {EMBED_MODEL}")
    print(f"🧩 chunk   : max={MAX_CHARS}, overlap={OVERLAP}, batch={BATCH_SIZE}")

    texts, sources = build_corpus()

    # مدل امبدینگ
    model = SentenceTransformer(EMBED_MODEL)

    # امبدینگ‌ها را در بچ‌ها محاسبه کنیم تا حافظه مدیریت شود
    embs_list = []
    total = len(texts)
    for start in range(0, total, BATCH_SIZE):
        end = min(start + BATCH_SIZE, total)
        batch = texts[start:end]
        emb = model.encode(batch, convert_to_numpy=True, show_progress_bar=False)
        embs_list.append(emb)
        print(f"… embedded {end}/{total}")

    embs = np.vstack(embs_list).astype(np.float32)

    # نرمال‌سازی برای cosine (dot-product با IndexFlatIP)
    norms = np.linalg.norm(embs, axis=1, keepdims=True) + 1e-10
    embs = embs / norms

    # ساخت ایندکس و افزودن
    index = faiss.IndexFlatIP(embs.shape[1])
    index.add(embs)

    # ذخیره ایندکس و متا
    index_path = OUT_DIR / "index.faiss"
    meta_path = OUT_DIR / "meta.json"

    faiss.write_index(index, str(index_path))
    meta_path.write_text(
        json.dumps({"texts": texts, "sources": sources}, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"✅ Indexed {len(texts)} chunks → {index_path}")
    print(f"📝 Meta saved → {meta_path}")


if __name__ == "__main__":
    main()
