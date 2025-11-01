#FEYZ
#DEO
# -*- coding: utf-8 -*-
"""
generator.py (نسخه Human+SmartCost Routing)

منطق پاسخ‌دهی:
1) احوال‌پرسی/پیام ساده → جواب کوتاه، گرم، انسانی. بدون مدل، بدون هزینه.
2) Rule-based → اگر سؤال تکراری/واضح باشه از جواب‌های ازپیش‌آماده استفاده می‌شه. بدون هزینه.
3) Retrieval → اگر توی دانش داخلی ما (کتاب/یادداشت‌ها) جواب روشن باشه، از همون استفاده می‌شه. بدون هزینه API.
4) OpenAI / HuggingFace → فقط اگر هنوز جواب خوب نداریم می‌ریم سراغ مدل ابری.
5) fallback → اگر همه چیز قطع شد، یک توصیه‌ی اجرایی کوتاه و انسانی می‌ده.

خروجی همیشه یک متن یک‌تکه است.
"""

import os, json, random, requests
from pathlib import Path
from typing import Dict, Any, Optional, List

# تلاش برای ایمپورت OpenAI SDK جدید
try:
    from openai import OpenAI  # type: ignore
except Exception:
    OpenAI = None


def _read_secret_or_env(key: str, default: str = "") -> str:
    """
    اول از st.secrets (روی Streamlit Cloud)
    بعد از os.environ (لوکال .env)
    """
    try:
        import streamlit as st  # type: ignore
        if key in getattr(st, "secrets", {}):
            return str(st.secrets.get(key, default))
    except Exception:
        pass
    return os.getenv(key, default)


def load_settings() -> Dict[str, Any]:
    """
    مقادیر اتصال به مدل‌ها + مسیر کش
    """
    base_dir = Path(__file__).resolve().parents[1]
    data_dir = base_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    cache_path = data_dir / "cache.json"

    return {
        "MODEL_PROVIDER": _read_secret_or_env("MODEL_PROVIDER", "openai").strip().lower(),
        "OPENAI_API_KEY": _read_secret_or_env("OPENAI_API_KEY", ""),
        "OPENAI_MODEL": _read_secret_or_env("OPENAI_MODEL", "gpt-4o-mini"),
        "MODEL_ENDPOINT": _read_secret_or_env(
            "MODEL_ENDPOINT",
            "https://api-inference.huggingface.co/models/gpt2"
        ),
        "HF_TOKEN": _read_secret_or_env("HF_TOKEN", ""),
        "CACHE_PATH": str(cache_path),
        "DEFAULT_MAX_NEW_TOKENS": int(_read_secret_or_env("MAX_NEW_TOKENS", "256")),
        "DEFAULT_TEMPERATURE": float(_read_secret_or_env("TEMPERATURE", "0.2")),
    }


def _load_cache(path: str) -> Dict[str, Any]:
    try:
        p = Path(path)
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_cache(path: str, data: Dict[str, Any]) -> None:
    try:
        Path(path).write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception:
        pass


def _join_context(context: Optional[List[str]]) -> str:
    """
    context = تکه‌هایی که retriever برگردونده (دانش لوکال ما)
    ما اینو فقط به مدل ابری می‌دیم تا کمکش کنه دقیق‌تر باشه.
    مستقیم به کاربر نشون داده نمی‌شه.
    """
    if not context:
        return ""
    cleaned = [c.strip() for c in context if c and c.strip()]
    if not cleaned:
        return ""
    ctx = "\n\n".join(cleaned)
    return (
        "\n\n[یادداشت داخلی برای مدل: از این دیتا به‌عنوان مرجع استفاده کن. این متن مستقیم به کاربر نمایش داده نمی‌شود]\n"
        f"{ctx}\n"
    )

#DEO
# جواب‌های آماده برای سوال‌های پرتکرار (رایگان، بدون API)
_RULES = {
    "streamlit": (
        "برای اینکه پروژه‌ت روی Streamlit Cloud بدون خطا بالا بیاد، نسخهٔ پایتون رو در runtime.txt قفل کن "
        "مثلاً 3.11، متغیرهای حساس رو بذار توی Secrets نه .env، و داخل پوشه app یک فایل خالی __init__.py "
        "بساز تا import خراب نشه."
    ),
    "faiss": (
        "برای بازیابی سریع دانش محلی: متن‌هارو تمیز و پاراگراف‌بندی کن، "
        "با مدل all-MiniLM-L6-v2 امبدینگ بگیر و همهٔ向بردارها رو داخل FAISS ذخیره کن. "
        "اینطوری top_k خیلی سریع و ارزان برمی‌گرده."
    ),
    "api": (
        "برای کم کردن هزینهٔ API، سوال‌های تکراری رو کش کن و فقط وقتی سوال پیچیده یا جدید شد برو سراغ مدل ابری. "
        "قبل از هزینه کردن، مسئله رو به یک قدم قابل‌اجرا در همین امروز تبدیل کن."
    ),
    "مذاکره": (
        "تو مذاکره اول گوش بده و دقیق بفهم طرف مقابل چی می‌خواد. "
        "هدفت متقاعد کردن زورکی نیست؛ هدفت پیدا کردن نقطه‌ایه که هردو طرف حس نکنن بازنده‌ان."
    ),
    "کسب و کار": (
        "هستهٔ هر کسب‌وکار موفق اینه که یک درد واقعی رو حل کنه، نه اینکه فقط یه ایده قشنگ داشته باشه. "
        "ارزش واقعی یعنی چیزی که طرف مقابل حاضر باشه براش پول یا زمان بده."
    ),
}


def _rule_based_answer(query: str) -> Optional[str]:
    """
    اگر سوال شامل یکی از کلیدواژه‌های _RULES باشه همون‌جا جواب می‌دیم.
    هیچ هزینه‌ای هم نداره.
    """
    q_low = (query or "").lower()
    for key, val in _RULES.items():
        if key.lower() in q_low:
            return val
    return None


def _is_smalltalk(query: str) -> bool:
    """
    تشخیص احوال‌پرسی / سوال ساده.
    اگر بله: جواب دوستانه و خیلی کوتاه بدیم (نه لحن معلم، نه لحن مقاله)
    """
    low_q = (query or "").strip().lower()
    greetings = [
        "سلام", "سلام.", "سلام!", "سلاممم", "salam",
        "hi", "hello", "hey", "heyy", "helo",
        "خوبی", "چطوری", "چه خبر", "خسته نباشی",
        "صبح بخیر", "شب بخیر", "درود"
    ]

    # خیلی کوتاه + یکی از واژه‌های سلام/احوال‌پرسی
    if len(low_q) <= 20:
        for g in greetings:
            if g in low_q:
                return True
    return False


def _smalltalk_answer() -> str:
    """
    جواب انسانی کوتاه برای پیام‌های خیلی ساده
    بدون هیچ اطلاعات سنگین بیزنسی
    """
    candidates = [
        "سلام 👋 من اینجام. چی تو ذهنت هست؟",
        "سلام 😊 بگو ببینم امروز درگیر چی هستی؟",
        "درود 🌱 آماده‌ام هرچی تو فکرت هست بشنو‌م.",
        "سلام خوش اومدی 🙌 شروع کنیم؟",
    ]
    return random.choice(candidates)


def _hf_generate(
    prompt: str,
    endpoint: str,
    token: str,
    temperature: float,
    max_new_tokens: int,
    timeout: float = 40.0
) -> str:
    """
    تماس با HuggingFace (مدل ابری ارزون‌تر یا رایگان‌تر).
    """
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    payload = {
        "inputs": prompt,
        "parameters": {
            "temperature": float(temperature),
            "max_new_tokens": int(max_new_tokens),
            "return_full_text": False,
        },
    }
    r = requests.post(endpoint, headers=headers, json=payload, timeout=timeout)
    r.raise_for_status()
    data = r.json()

    # حالت‌های رایج پاسخ‌های HF
    if isinstance(data, list) and data and isinstance(data[0], dict) and "generated_text" in data[0]:
        return str(data[0]["generated_text"]).strip()
    if isinstance(data, dict) and "generated_text" in data:
        return str(data["generated_text"]).strip()

    return json.dumps(data, ensure_ascii=False)


def _openai_generate(
    prompt: str,
    api_key: str,
    model_name: str,
    temperature: float,
    max_new_tokens: int
) -> str:
    """
    تماس با OpenAI (گران‌ترین مرحله).
    از SDK جدید OpenAI استفاده می‌کنیم (client.responses.create).
    """
    if not OpenAI:
        raise RuntimeError("openai package not available in this environment")

    client = OpenAI(api_key=api_key)

    response = client.responses.create(
        model=model_name,
        input=prompt,
        temperature=float(temperature),
        max_output_tokens=int(max_new_tokens),
    )

    text_out = None

    # مدل جدید ممکن است پاسخ را در response.output برگرداند
    try:
        if hasattr(response, "output") and response.output:
            parts = []
            for item in response.output:
                # item ممکنه .content (لیست قطعه‌ها) یا .text داشته باشه
                if hasattr(item, "content") and item.content:
                    segs = []
                    for seg in item.content:
                        if hasattr(seg, "text") and seg.text:
                            segs.append(seg.text)
                    if segs:
                        parts.append("\n".join(segs))
                elif hasattr(item, "text") and item.text:
                    parts.append(item.text)
            if parts:
                text_out = "\n".join(parts).strip()
    except Exception:
        pass

    # مسیر fallback
    if (text_out is None) and hasattr(response, "output_text"):
        try:
            text_out = str(response.output_text).strip()
        except Exception:
            pass

    if (text_out is None) and hasattr(response, "choices"):
        try:
            if response.choices and hasattr(response.choices[0], "message"):
                msg = response.choices[0].message
                if hasattr(msg, "content"):
                    text_out = str(msg.content).strip()
        except Exception:
            pass

    if text_out is None:
        text_out = str(response)

    return text_out


def healthcheck() -> Dict[str, Any]:
    """
    برای استفاده داخلی (لاگ، دیباگ محلی).
    در UI نهایی نمایش داده نمی‌شه.
    """
    s = load_settings()
    return {
        "provider": s["MODEL_PROVIDER"],
        "has_openai_key": bool(s["OPENAI_API_KEY"]),
        "openai_model": s["OPENAI_MODEL"],
        "has_hf_token": bool(s["HF_TOKEN"]),
    }


def generate_answer(
    query: str,
    *,
    model_provider: Optional[str] = None,
    openai_model: Optional[str] = None,
    openai_api_key: Optional[str] = None,
    model_endpoint: Optional[str] = None,
    hf_token: Optional[str] = None,
    temperature: Optional[float] = None,
    max_new_tokens: Optional[int] = None,
    top_k: int = 5,
    context: Optional[List[str]] = None,
) -> str:
    """
    این تابع همونیه که ui.py صدا می‌زنه.
    خروجی: همیشه یک متن یک‌تکه انسانی.
    """

    s = load_settings()

    provider = (model_provider or s["MODEL_PROVIDER"]).lower()
    temperature = float(temperature if temperature is not None else s["DEFAULT_TEMPERATURE"])
    max_new_tokens = int(max_new_tokens if max_new_tokens is not None else s["DEFAULT_MAX_NEW_TOKENS"])

    api_key = openai_api_key or s["OPENAI_API_KEY"]
    model_name = openai_model or s["OPENAI_MODEL"]
    endpoint = model_endpoint or s["MODEL_ENDPOINT"]
    hf_tok = hf_token or s["HF_TOKEN"]

    cache_path = s["CACHE_PATH"]
    cache = _load_cache(cache_path)

    ctx_list = context or []
    ctx_joined = "\n\n".join(ctx_list)

    # کش برای سوال‌های تکراری
    cache_key = f"{provider}:{hash((query, ctx_joined, max_new_tokens, temperature))}"
    if cache_key in cache:
        return str(cache[cache_key])

    # 0) اگر فقط سلام/احوال‌پرسی بود → جواب کوتاه ریلکس، بدون هزینه
    if _is_smalltalk(query):
        final_text = _smalltalk_answer()
        cache[cache_key] = final_text
        _save_cache(cache_path, cache)
        return final_text

    # 1) Rule-based (سوال‌های واضح و پرتکرار)
    rb = _rule_based_answer(query)
    if rb:
        final_text = rb
        cache[cache_key] = final_text
        _save_cache(cache_path, cache)
        return final_text

    # 2) Retrieval محلی (سوال مفهومی اما جوابش تو دیتای خودمونه)
    # اگر retriever بهمون تیکه متن داده و اون تیکه معنی‌داره، از همون جواب می‌سازیم → بدون هزینه API
    if ctx_list:
        best_snippet = ctx_list[0].strip()
        if len(best_snippet) > 40:
            local_answer = (
                f"{best_snippet}\n\n"
                "اگر می‌خوای اینو تبدیل کنیم به یک قدم عملی برای همین امروز، بگو دقیقا الان کجایی و چی می‌خوای انجام بشه."
            )
            final_text = local_answer
            cache[cache_key] = final_text
            _save_cache(cache_path, cache)
            return final_text

    # 3) مدل ابری (OpenAI → گرونتر / HuggingFace → ارزونتر)
    # فقط وقتی مراحل بالا جواب کافی نداد

    # 3a) OpenAI
    if provider == "openai" and api_key:
        try:
            prompt = (
                "تو نقش یک منتور فارسی رو داری. پاسخ باید دوستانه، قابل‌اجرا و بدون بخش‌بندی رسمی باشه. "
                "جواب رو کوتاه و شفاف بده، انگار مستقیم با طرف حرف می‌زنی.\n\n"
                f"سؤال کاربر:\n{query.strip()}\n\n"
                "اگر لازم شد از این دانش داخلی استفاده کن ولی از حالت خشک و دانشگاهی دوری کن:\n"
                f"{ctx_joined}\n"
            )
            final_text = _openai_generate(
                prompt=prompt,
                api_key=api_key,
                model_name=model_name,
                temperature=temperature,
                max_new_tokens=max_new_tokens,
            )
            cache[cache_key] = final_text
            _save_cache(cache_path, cache)
            return final_text
        except Exception:
            # اگر OpenAI شکست خورد، می‌ریم سراغ HuggingFace یا fallback
            pass

    # 3b) HuggingFace
    if provider == "huggingface" and hf_tok:
        try:
            prompt = (
                "یک پاسخ کوتاه، صمیمی و کاربردی به زبان فارسی بده. رسمی نباش.\n\n"
                f"سؤال:\n{query.strip()}\n\n"
                f"دانش کمکی:\n{ctx_joined}\n"
            )
            final_text = _hf_generate(
                prompt=prompt,
                endpoint=endpoint,
                token=hf_tok,
                temperature=temperature,
                max_new_tokens=max_new_tokens,
            )
            cache[cache_key] = final_text
            _save_cache(cache_path, cache)
            return final_text
        except Exception:
            pass

    # 4) fallback نهایی (اگه همه‌چی از کار افتاد)
    final_text = (
        "بیا مسئله‌ات رو تبدیل کنیم به یه قدم خیلی کوچیک که همین امروز انجامش بدی. "
        "الان دقیقاً کجا گیر کردی؟ همونو بگو تا با هم همون‌جا رو باز کنیم."
    )
    cache[cache_key] = final_text
    _save_cache(cache_path, cache)
    return final_text
