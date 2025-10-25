# app/settings.py
from pathlib import Path
from dataclasses import dataclass
import os

BASE_DIR = Path(__file__).resolve().parents[1]
INDEX_DIR = BASE_DIR / "faiss_index"
DATA_DIR = BASE_DIR / "data"

DEFAULT_EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
DEFAULT_TOP_K = int(os.getenv("TOP_K", "5"))

@dataclass
class UIConfig:
    title: str = "منتور شخصی با حافظه و جست‌وجوی معنایی"
    description: str = "پرسش خود را وارد کنید؛ سیستم از روی داده‌های شما پاسخ تولید می‌کند."
    offline_max_chars: int = 900  # برای حالت آفلاین (خلاصه‌سازی ساده)
