# convert_abzaar_to_jsonl.py
import json
from pathlib import Path

source_path = Path("data/abzaar.txt")
output_path = Path("data/abzaar_full_clean.jsonl")

# تقسیم متن به تکه‌های کوچک‌تر
def chunk_text(text, max_chars=600):
    sentences = text.split(" ")
    chunks, current = [], ""
    for s in sentences:
        if len(current) + len(s) < max_chars:
            current += s + " "
        else:
            chunks.append(current.strip())
            current = s + " "
    if current:
        chunks.append(current.strip())
    return chunks

# خواندن متن
with open(source_path, "r", encoding="utf-8") as f:
    full_text = f.read()

# تشخیص فصل‌ها با کلیدواژه‌ها
chapters = {
    "هدف": ("هدف‌گذاری و مدیریت زمان", "پایه"),
    "مذاکره": ("مذاکره و تصمیم‌گیری", "پیشرفته"),
    "فروش": ("فروش و بازاریابی", "متوسط"),
    "رهبری": ("رهبری و تیم‌سازی", "پیشرفته"),
}

records = []
for key, (skill, level) in chapters.items():
    if key in full_text:
        part = full_text.split(key, 1)[1]
        chunks = chunk_text(part)
        for c in chunks:
            records.append({
                "text": c,
                "metadata": {
                    "domain": "business",
                    "skill": skill,
                    "level": level,
                    "language": "fa",
                    "chapter": f"فصل مرتبط با {skill}"
                }
            })

# جمع‌بندی
summary = [
    {"skill": s, "level": l, "paragraphs": sum(1 for r in records if r["metadata"]["skill"] == s)}
    for _, (s, l) in chapters.items()
]
records.append({"summary": summary})

# ذخیره فایل JSONL
with open(output_path, "w", encoding="utf-8") as f:
    for rec in records:
        json.dump(rec, f, ensure_ascii=False)
        f.write("\n")

print(f"✅ فایل JSONL با موفقیت ساخته شد: {output_path}")
