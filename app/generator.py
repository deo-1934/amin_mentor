#FEYZ
#DEO
import os
import json
import hashlib
import requests
from datetime import datetime

# --------------------------------------------
# 📍 مسیر فایل کش محلی (برای ذخیره پاسخ‌های قبلی)
# --------------------------------------------
CACHE_PATH = os.path.join("data", "cache.json")
os.makedirs("data", exist_ok=True)
if not os.path.exists(CACHE_PATH):
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump({}, f, ensure_ascii=False, indent=2)


# --------------------------------------------
# 🧠 Rule-Based پاسخ‌های ساده و تکراری
# --------------------------------------------
def rule_based_answer(question: str):
    q = question.strip().lower()
    rules = {
        "سلام": "سلام خوش اومدی 🌸",
        "خداحافظ": "فعلاً، مراقب خودت باش 😊",
        "کی هستی": "من منتور شخصی امینم 🧠، همیشه کنارتم.",
        "اسم": "من منتور شخصی امینم 🌱",
        "ساعت": f"الان ساعت {datetime.now().strftime('%H:%M')} هست ⏰",
        "تاریخ": f"امروز {datetime.now().strftime('%Y-%m-%d')} هست 📅",
    }
    for k, v in rules.items():
        if k in q:
            return v
    return None


# --------------------------------------------
# 💾 سیستم کش (Cache)
# --------------------------------------------
def load_cache():
    with open(CACHE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_cache(cache):
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def get_cached_answer(question: str):
    cache = load_cache()
    key = hashlib.md5(question.encode()).hexdigest()
    return cache.get(key)

def set_cached_answer(question: str, answer: str):
    cache = load_cache()
    key = hashlib.md5(question.encode()).hexdigest()
    cache[key] = answer
    save_cache(cache)


# --------------------------------------------
# 🤖 تماس با API فقط درصورت نیاز
# --------------------------------------------
def call_openai_api(prompt: str):
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY') or os.getenv('HF_TOKEN')}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 400,
        "temperature": 0.7,
    }

    response = requests.post(
        "https://api.openai.com/v1/chat/completions", headers=headers, json=payload
    )
    if response.status_code == 200:
        data = response.json()
        return data["choices"][0]["message"]["content"]
    else:
        return f"⚠️ خطا در ارتباط با مدل: {response.text}"


# --------------------------------------------
# 🔷 تابع اصلی تولید پاسخ (Hybrid)
# --------------------------------------------
def generate_answer(user_question: str, context: list):
    """
    منطق سه‌مرحله‌ای:
      1. rule-based پاسخ ساده
      2. cache برای سوالات تکراری
      3. تماس با API در صورت نیاز
    """

    # مرحله 1: Rule-based
    rb_answer = rule_based_answer(user_question)
    if rb_answer:
        return rb_answer

    # مرحله 2: Cache
    cached = get_cached_answer(user_question)
    if cached:
        return cached

    # مرحله 3: ساخت prompt برای مدل
    context_text = "\n".join(context[-3:]) if context else ""
    prompt = f"""
    [سابقه گفتگو تا اینجا]
    {context_text}

    [پرسش کاربر]
    {user_question}

    لطفاً مثل یک منتور باهوش و مهربون پاسخ بده،
    مختصر، واضح و با لحن طبیعی.
    """

    answer = call_openai_api(prompt)

    # ذخیره در cache
    set_cached_answer(user_question, answer)

    return answer

#FEYZ
#DEO
