"""
app/generator.py — مولد پاسخ با fallback خلاصه‌ساز داخلی (بدون نیاز به HF)
"""
from __future__ import annotations
import os, json, logging, re
from typing import List, Optional, Dict, Any

import requests  # فقط وقتی HF_TOKEN داشته باشی استفاده می‌شود

# ---------- لاگ ----------
logger = logging.getLogger("generator")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(h)
logger.setLevel(logging.INFO)

# ---------- تنظیمات ----------
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "huggingface").strip().lower()
MODEL_ENDPOINT = os.getenv("MODEL_ENDPOINT", "https://api-inference.huggingface.co/models/gpt2").strip()
HF_TOKEN = os.getenv("HF_TOKEN", "").strip()
REQUEST_TIMEOUT = float(os.getenv("GENERATOR_TIMEOUT_SECS", "30"))
MAX_NEW_TOKENS_DEFAULT = int(os.getenv("MAX_NEW_TOKENS", "200"))

# ---------- ابزارهای متن ----------
def _normalize_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def _sentences(txt: str) -> List[str]:
    # جداسازی جمله‌ها ساده‌سازی‌شده برای فارسی/انگلیسی
    txt = txt.replace("؟", ".").replace("!", ".")
    parts = re.split(r"[\.。\n]+", txt)
    return [p.strip() for p in parts if p.strip()]

def _keywords(s: str) -> List[str]:
    s = re.sub(r"[^\w\u0600-\u06FF]+", " ", s)  # اجازهٔ فارسی/لاتین/عدد
    toks = [t for t in s.lower().split() if len(t) > 2]
    stop = {"این","آن","است","برای","اما","باشد","نیست","که","اگر","های","را","به","در","از",
            "with","and","the","are","you","your","our"}
    return [t for t in toks if t not in stop]

def _score_sentence(sent: str, q_terms: List[str]) -> float:
    s_terms = _keywords(sent)
    if not s_terms:
        return 0.0
    inter = len(set(s_terms) & set(q_terms))
    return inter / (len(set(s_terms)) ** 0.5)

def _join_context(context: Optional[List[str]]) -> str:
    if not context:
        return ""
    joined = "\n\n".join([c.strip() for c in context if c and c.strip()])
    return joined[:2000] + (" …" if len(joined) > 2000 else "")

def _build_prompt(prompt: str, context: Optional[List[str]]) -> str:
    ctx = _join_context(context)
    if ctx:
        return f"System: Use the provided context.\nContext:\n{ctx}\n\nUser: {prompt}\nAssistant:"
    return prompt

# ---------- HuggingFace ----------
def _hf_headers() -> Dict[str, str]:
    h = {"Content-Type": "application/json"}
    if HF_TOKEN:
        h["Authorization"] = f"Bearer {HF_TOKEN}"
    return h

def _hf_payload(text: str, max_new_tokens: int) -> Dict[str, Any]:
    return {
        "inputs": text,
        "parameters": {"max_new_tokens": max_new_tokens, "temperature": 0.7, "top_p": 0.95},
        "options": {"wait_for_model": True},
    }

def _extract_hf_text(resp_json: Any, _original_prompt: str) -> str:
    try:
        if isinstance(resp_json, list) and resp_json:
            item0 = resp_json[0]
            if isinstance(item0, dict) and "generated_text" in item0:
                return str(item0["generated_text"])
            return json.dumps(item0, ensure_ascii=False)
        if isinstance(resp_json, dict):
            if "generated_text" in resp_json:
                return str(resp_json["generated_text"])
            if "error" in resp_json:
                return f"[HF error] {resp_json['error']}"
            return json.dumps(resp_json, ensure_ascii=False)
    except Exception as e:
        logger.warning("failed to parse HF response: %s", e)
    return f"(no structured generated_text; raw) {json.dumps(resp_json, ensure_ascii=False)[:1000]}"

def _call_huggingface_inference(text: str, max_new_tokens: int) -> str:
    if not MODEL_ENDPOINT:
        raise RuntimeError("MODEL_ENDPOINT تنظیم نشده است.")
    r = requests.post(MODEL_ENDPOINT, headers=_hf_headers(), json=_hf_payload(text, max_new_tokens), timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return _extract_hf_text(r.json(), text)

# ---------- خلاصه‌ساز داخلی (Fallback) ----------
def _summarize_locally(question: str, context: Optional[List[str]]) -> str:
    q = _normalize_text(question)
    q_terms = _keywords(q)
    if not context:
        return "هیچ زمینه‌ای در دسترس نبود. سؤال را مشخص‌تر بپرس یا داده‌های پروژه را به‌روزرسانی کن."

    # ساخت استخر جمله‌ها و امتیازدهی بر اساس کلیدواژه‌های سؤال
    sent_pool: List[str] = []
    for c in context:
        sent_pool.extend(_sentences(c))

    scored = [(s, _score_sentence(s, q_terms)) for s in sent_pool]
    scored = [x for x in scored if x[1] > 0]
    top = sorted(scored, key=lambda x: x[1], reverse=True)[:6] if scored else [(s, 0) for s in sent_pool[:6]]

    bullets: List[str] = []
    for s, _ in top:
        s = _normalize_text(s)
        if s and s not in bullets:
            bullets.append(s)
        if len(bullets) >= 6:
            break

    if not bullets:
        return "متنی برای استخراج نکات کلیدی یافت نشد."

    # خروجی نهایی
    intro = f"خلاصهٔ نکات کلیدی مرتبط با پرسش «{q}»:"
    body = "\n".join([f"• {b}" for b in bullets])
    tips = "\n\nپیشنهاد: برای پاسخ دقیق‌تر، مثال/سناریوی خودت را اضافه کن."
    return f"{intro}\n{body}{tips}"

# ---------- API اصلی ----------
def generate_answer(
    prompt: str,
    context: Optional[List[str]] = None,
    max_new_tokens: int = MAX_NEW_TOKENS_DEFAULT
) -> str:
    prompt = (prompt or "").strip()
    if not prompt:
        return "⚠️ ورودی خالی است."
    built = _build_prompt(prompt, context)

    # مسیر HF در صورت وجود توکن
    if MODEL_PROVIDER == "huggingface" and MODEL_ENDPOINT and HF_TOKEN:
        try:
            text = _call_huggingface_inference(built, max_new_tokens=max_new_tokens)
            if "Assistant:" in text:
                text = text.split("Assistant:", 1)[-1].strip()
            return text.strip()
        except Exception as e:
            logger.error("HF call failed: %s", e)

    # Fallback: خلاصه‌ساز داخلی
    return _summarize_locally(prompt, context)

def healthcheck() -> Dict[str, Any]:
    return {
        "provider": MODEL_PROVIDER,
        "has_token": bool(HF_TOKEN),
        "endpoint_set": bool(MODEL_ENDPOINT),
        "timeout_secs": REQUEST_TIMEOUT,
    }

if __name__ == "__main__":
    demo = generate_answer(
        "سلام! یک پاسخ کوتاه بده.",
        context=["این یک متن زمینهٔ آزمایشی برای چک‌کردن کارکرد خلاصه‌ساز داخلی است."]
    )
    print(demo)
    print("health:", healthcheck())
