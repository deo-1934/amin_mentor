#FEYZ
#DEO
# -*- coding: utf-8 -*-
"""
generator.py - Cost-Tiered LLM Routing

هدف:
- همیشه از مدل هوش مصنوعی استفاده کن (دیگه جواب بدون مدل نمی‌دیم)
- ولی بسته به سختی سؤال، مدل ارزون‌تر یا مدل قوی‌تر رو صدا بزن
- برای سوال‌های ساده توکن کمتر خرج کن
- برای سوال‌های جدی از مدل قوی با توکن بیشتر استفاده کن

ورودی اصلی از ui/web می‌آد:
    generate_answer(query=user_text, context=full_context, ...)

context ترکیبیه از:
- تکه‌های دانش داخلی (retriever)
- خلاصه ۶ پیام آخر مکالمه ("گفتگو تا اینجا: ...")

خروجی باید یک متن محاوره‌ای و یک‌تکه باشه.
"""

import os, json, re
from pathlib import Path
from typing import Dict, Any, Optional, List

try:
    # OpenAI SDK جدید
    from openai import OpenAI  # type: ignore
except Exception:
    OpenAI = None


# -------------------------------------------------
# خواندن تنظیمات و سکرت‌ها
# -------------------------------------------------
def _read_secret_or_env(key: str, default: str = "") -> str:
    """
    اول تلاش می‌کنیم از st.secrets بخونیم (Streamlit Cloud)
    بعد میریم سراغ os.environ (لوکال .env)
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
    برمی‌گردونه تنظیمات runtime شامل مدل‌ها، api key و مسیر کش.
    """
    base_dir = Path(__file__).resolve().parents[1]
    data_dir = base_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    cache_path = data_dir / "cache.json"

    return {
        "MODEL_PROVIDER": _read_secret_or_env("MODEL_PROVIDER", "openai").strip().lower(),

        # مدل ارزون برای سوال‌های کوتاه/روتین/ساده
        "OPENAI_MODEL_CHEAP": _read_secret_or_env("OPENAI_MODEL_CHEAP", "gpt-4o-mini"),

        # مدل قوی‌تر برای سوال‌های جدی بیزنس/استراتژی
        "OPENAI_MODEL_DEEP": _read_secret_or_env("OPENAI_MODEL_DEEP", "gpt-4o-mini"),

        "OPENAI_API_KEY": _read_secret_or_env("OPENAI_API_KEY", ""),

        # برای سازگاری با نسخه‌های قبلی (HuggingFace و ...)، اینجا فقط نگه داشته شده:
        "HF_TOKEN": _read_secret_or_env("HF_TOKEN", ""),

        # مسیر کش برای کاهش هزینه سؤالات تکراری
        "CACHE_PATH": str(cache_path),
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


# -------------------------------------------------
# تشخیص نوع سوال (ارزون یا گرون؟)
# -------------------------------------------------
def _is_smalltalk_or_simple(query: str) -> bool:
    """
    اگر سؤال خیلی کوتاهه یا صرفاً احوال‌پرسی/خواسته ساده است،
    می‌تونیم از مدل ارزون‌تر و توکن کم استفاده کنیم.
    """
    q = (query or "").strip().lower()

    greetings = [
        "سلام", "سلام.", "سلام!",
        "hi", "hello", "hey",
        "خوبی", "چطوری", "چه خبر", "خسته نباشی",
        "صبح بخیر", "شب بخیر",
    ]

    # اگر جمله خیلی کوتاه و شبیه احوال‌پرسی بود
    if len(q) <= 25:
        for g in greetings:
            if g in q:
                return True

    # سوال‌های خیلی فرمولی و مستقیم و کوتاه:
    # "اصول مذاکره رو نام ببر"
    # "تعریف تمرکز چیه؟"
    # "چند تا نکته بگو"
    patterns_simple = [
        r"^اصول",          # اصول مذاکره رو بگو
        r"^تعریف",         # تعریف تمرکز چیه؟
        r"^یعنی چی",       # بهره‌وری یعنی چی
        r"^چند تا نکته",   # چند تا نکته بگو
    ]
    for pat in patterns_simple:
        if re.search(pat, q):
            return True

    # اگر خیلی کوتاهه و فقط یه دستور کوچیکه:
    # "یه نکته در مورد مذاکره بگو"
    if len(q.split()) <= 6:
        return True

    # در غیر این صورت می‌تونه پیچیده‌تر باشه
    return False


def _clean_context_blocks(context_list: Optional[List[str]]) -> str:
    """
    ورودی context (لیست تکه‌های دانش/گفتگو) رو تمیز و یکی می‌کنیم
    تا مدل راحت‌تر ازش استفاده کنه.
    """
    if not context_list:
        return ""

    cleaned_blocks: List[str] = []
    for block in context_list:
        if not block:
            continue
        # پاک کردن چیزهایی که نباید مستقیماً کاربر ببیند
        txt = re.sub(r"\(منبع:[^)]+\)", "", block)
        txt = re.sub(r"\[[^\]]+\]", "", txt)
        txt = txt.strip()
        if txt:
            cleaned_blocks.append(txt)

    if not cleaned_blocks:
        return ""

    merged = "\n\n---\n\n".join(cleaned_blocks)
    final = (
        "یادداشت کمکی (سابقه گفتگو و دانش داخلی):\n"
        "از این اطلاعات فقط برای اینکه بهتر و دقیق‌تر جواب بدی استفاده کن. "
        "این متن رو مستقیم تکرار نکن مگر لازم باشد.\n\n"
        f"{merged}\n"
    )
    return final


#DEO
# -------------------------------------------------
# تماس با OpenAI
# -------------------------------------------------
def _call_openai(
    *,
    api_key: str,
    model_name: str,
    prompt: str,
    max_tokens: int,
    temperature: float,
) -> str:
    """
    صدا زدن OpenAI Responses API.
    ما انتظار داریم مدل‌هایی مثل gpt-4o / gpt-4o-mini این را ساپورت کنند.
    خروجی را به یک متن تمیز تبدیل می‌کنیم.
    """
    if not OpenAI:
        raise RuntimeError("openai package not available in this environment")

    client = OpenAI(api_key=api_key)

    response = client.responses.create(
        model=model_name,
        input=prompt,
        max_output_tokens=max_tokens,
        temperature=temperature,
    )

    # استخراج متن از ساختار response
    text_out = None

    try:
        if hasattr(response, "output") and response.output:
            parts = []
            for item in response.output:
                # item ممکنه .content (لیست segmentها) یا .text داشته باشه
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

    # fallbackهای احتمالی
    if text_out is None and hasattr(response, "output_text"):
        try:
            text_out = str(response.output_text).strip()
        except Exception:
            pass

    if text_out is None and hasattr(response, "choices"):
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


# -------------------------------------------------
# تابع اصلی پاسخ‌دهی
# -------------------------------------------------
def generate_answer(
    query: str,
    *,
    context: Optional[List[str]] = None,
    temperature_simple: float = 0.2,
    temperature_deep: float = 0.3,
    max_tokens_simple: int = 128,
    max_tokens_deep: int = 512,
    force_new: bool = False,   # 👈 جدید: اگر True باشد، کش را نادیده می‌گیریم
) -> str:
    """
    همیشه مدل رو صدا می‌زنیم.
    ولی:
      - اگر سوال ساده‌ست → مدل ارزون‌تر، توکن کم
      - اگر سوال جدی‌تره → مدل قوی‌تر، توکن بیشتر
      - اگر force_new == True → کش را نادیده می‌گیریم و حتی اگر این سؤال تکراری است، جواب جدید می‌گیریم

    خروجی: یک متن محاوره‌ای، یک‌تکه، بدون سرفصل‌های خشک.
    """

    s = load_settings()

    provider = s["MODEL_PROVIDER"]
    api_key = s["OPENAI_API_KEY"]
    model_cheap = s["OPENAI_MODEL_CHEAP"]
    model_deep = s["OPENAI_MODEL_DEEP"]

    cache_path = s["CACHE_PATH"]
    cache = _load_cache(cache_path)

    # context رو تمیز کنیم
    ctx_block = _clean_context_blocks(context)

    # کلید کش: سؤال کاربر + کانتکست
    cache_key = f"{query.strip()}##{ctx_block.strip()}"

    # اگر force_new=False و این سؤال قبلا جواب داده شده، همان پاسخ را بده
    if (not force_new) and cache_key in cache:
        return cache[cache_key]

    # تصمیم بگیریم که این سوال "ساده/کوتاه" است یا "جدی/عمیق"
    simple = _is_smalltalk_or_simple(query)

    if simple:
        chosen_model = model_cheap
        chosen_temp = temperature_simple
        chosen_max_tokens = max_tokens_simple
        style_instruction = (
            "خیلی خلاصه و خودمانی جواب بده. "
            "یک پاراگراف یا چند جمله کوتاه کافیه. "
            "زیادی تئوریک و دانشگاهی نباش. "
            "واضح و مستقیم باش."
        )
    else:
        chosen_model = model_deep
        chosen_temp = temperature_deep
        chosen_max_tokens = max_tokens_deep
        style_instruction = (
            "مثل یک منتور کسب‌وکار فارسی رفتار کن. "
            "جواب رو کاربردی، مشخص و مرحله‌ای بده، ولی خشک و رسمی نباش. "
            "خروجی فقط یک متن یک‌تکه باشه؛ سرفصلِ رسمی و تیتر نذار."
        )

    # پرامپت نهایی که مدل باید بگیره
    prompt = (
        f"{style_instruction}\n\n"
        f"سوال کاربر:\n{query.strip()}\n\n"
        f"{ctx_block}"
    )

    # enforce اینکه فعلاً فقط openai ساپورت می‌شه
    if provider != "openai":
        provider = "openai"

    # درخواست به LLM
    if provider == "openai" and api_key:
        try:
            answer_text = _call_openai(
                api_key=api_key,
                model_name=chosen_model,
                prompt=prompt,
                max_tokens=chosen_max_tokens,
                temperature=chosen_temp,
            )
        except Exception:
            answer_text = (
                "الان نتونستم جواب هوشمند رو از مدل بگیرم. "
                "یه بار دیگه بپرس یا واضح‌تر بگو دقیقا دنبال چی هستی."
            )
    else:
        answer_text = (
            "در حال حاضر به مدل متصل نیستم. کلید API یا سطح دسترسی موجود نیست."
        )

    # پاسخ جدید رو در کش ذخیره کن
    cache[cache_key] = answer_text
    _save_cache(cache_path, cache)

    return answer_text

#FEYZ
#DEO
