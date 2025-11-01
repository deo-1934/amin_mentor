#FEYZ
#DEO
# -*- coding: utf-8 -*-
"""
generator.py
نسخه‌ی یکپارچه‌شده:
- خروجی: فقط یک رشته (string) نهایی. نه intro/core/outro
- استفاده از OpenAI Responses API وقتی MODEL_PROVIDER="openai"
- استفاده از HuggingFace وقتی MODEL_PROVIDER="huggingface"
- حالت fallback اگر هیچکدوم در دسترس نباشن
"""

import os, json, time
from pathlib import Path
from typing import Dict, Any, Optional, List
import requests

# در SDK جدید اوپن‌ای‌آی از کلاس OpenAI استفاده می‌شود. :contentReference[oaicite:2]{index=2}
try:
    from openai import OpenAI  # type: ignore
except Exception:
    OpenAI = None  # اگر پکیج نصب نشده باشد، بعداً fallback می‌رویم


def _read_secret_or_env(key: str, default: str = "") -> str:
    """
    اول از st.secrets می‌خوانیم (محیط Streamlit Cloud)
    بعد از os.environ (محیط لوکال .env)
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
    پارامترهای اتصال مدل + مسیر کش
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

        # پارامترهای کنترلی پایه
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
    چند پاراگراف بازیابی‌شده از retriever رو به بلوک زمینه تبدیل می‌کنه
    تا مدل بفهمه چه دانشی باید لحاظ بشه.
    این متن مستقیماً به مدل داده می‌شه ولی به کاربر نمایش داده نمیشه.
    """
    if not context:
        return ""
    cleaned = [c.strip() for c in context if c and c.strip()]
    if not cleaned:
        return ""
    ctx = "\n\n".join(cleaned)
    return (
        "\n\n[دانش مرتبط و مثال‌های داخلی برای کمک به پاسخ دقیق‌تر، فقط برای منِ مدل:]\n"
        f"{ctx}\n"
    )


# قواعد خیلی ارزان (Rule-based) برای وقتی اصلاً مدل در دسترس نیست.
_RULES = {
    "streamlit": (
        "برای استقرار پایدار روی Streamlit Cloud، نسخهٔ پایتون را در runtime.txt "
        "لاک کن (مثل 3.11)، Secrets را جایگزین .env کن و import ها را با یک __init__.py "
        "ماژولار کن تا ModuleNotFoundError نگیری."
    ),
    "faiss": (
        "برای جست‌وجوی دانش محلی سریع: متن‌ خام را تمیز کن، پاراگراف‌بندی کن، "
        "از Sentence-Transformers مثل all-MiniLM-L6-v2 برای embedding استفاده کن "
        "و خروجی را داخل FAISS ایندکس کن تا top_k سریع بیاد."
    ),
    "api": (
        "برای کاهش هزینه API، سؤالات تکراری را کش کن و فقط برای پرسش جدید برو سراغ مدل ابری. "
        "اول یک نسخهٔ rule-based/لوکال داشته باش بعد scale کن."
    ),
    "کسب و کار": (
        "زیرساخت هر کسب‌وکار سالم اینه که یک مسئله واقعی رو حل کنه و ارزش قابل لمس بده. "
        "قبل از بزرگ شدن دنبال تکرارپذیری باش، نه دنبال فانسی بودن."
    ),
    "مذاکره": (
        "در مذاکره اول بفهم چی برای طرف مقابل مهمه و چرا. توی گوش دادن امتیاز می‌بری، "
        "نه توی توضیح دادن خودت."
    ),
}


def _rule_based_answer(query: str) -> Optional[str]:
    """
    اگر کلیدواژه مهمی داخل سوال کاربر بود، یک جواب آماده و قابل استفاده بده.
    """
    q_low = (query or "").lower()
    for key, val in _RULES.items():
        if key.lower() in q_low:
            return val
    return None


def _hf_generate(prompt: str,
                 endpoint: str,
                 token: str,
                 temperature: float,
                 max_new_tokens: int,
                 timeout: float = 40.0) -> str:
    """
    تماس ساده با Inference API هاگینگ‌فیس.
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

    # ساختار خروجی HuggingFace معمولا یه لیست از آبجکت‌هاست که توش generated_text هست. :contentReference[oaicite:3]{index=3}
    if isinstance(data, list) and data and isinstance(data[0], dict) and "generated_text" in data[0]:
        return str(data[0]["generated_text"]).strip()
    if isinstance(data, dict) and "generated_text" in data:
        return str(data["generated_text"]).strip()

    return json.dumps(data, ensure_ascii=False)


#DEO
def _openai_generate(prompt: str,
                     api_key: str,
                     model_name: str,
                     temperature: float,
                     max_new_tokens: int) -> str:
    """
    تماس با OpenAI Responses API.
    طبق مستند رسمی، مدل‌های سری gpt-4o و gpt-4o-mini از طریق client.responses.create فراخوانی می‌شوند. :contentReference[oaicite:4]{index=4}
    """
    if not OpenAI:
        raise RuntimeError("openai package not available in this environment")

    client = OpenAI(api_key=api_key)

    # input: فقط یک رشته. Responses API خروجی رو در blocks برمی‌گردونه.
    # ما متن رو از first output.text استخراج می‌کنیم. :contentReference[oaicite:5]{index=5}
    response = client.responses.create(
        model=model_name,
        input=prompt,
        temperature=float(temperature),
        max_output_tokens=int(max_new_tokens),
    )

    # ساختار response توی Responses API معمولا شامل output(s) هست.
    # در نسخه‌های اخیر پاسخ متنی در اولین بخش text قرار می‌گیره. :contentReference[oaicite:6]{index=6}
    #
    # ما حالت‌های متداول رو هندل می‌کنیم تا چیزی نشکنه.
    text_out = None

    # حالت جدید: response.output و داخلش items با type='output_text'
    try:
        if hasattr(response, "output") and response.output:
            # response.output ممکنه لیست از آبجکت‌هایی باشه که text دارن
            parts = []
            for item in response.output:
                # item ممکنه .content یا .text داشته باشه
                if hasattr(item, "content") and item.content:
                    # content هم می‌تونه لیست segment باشه
                    segs = []
                    for seg in item.content:
                        # هر seg شاید text داشته باشه
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

    # حالت fallback: بعضی نسخه‌ها .output_text ساده هم دارن
    if (not text_out) and hasattr(response, "output_text"):
        try:
            text_out = str(response.output_text).strip()
        except Exception:
            pass

    # حالت خیلی قدیمی‌تر/سازگاری: شبیه chat.completions
    if (not text_out) and hasattr(response, "choices"):
        try:
            if response.choices and hasattr(response.choices[0], "message"):
                msg = response.choices[0].message
                if hasattr(msg, "content"):
                    text_out = str(msg.content).strip()
        except Exception:
            pass

    if not text_out:
        # اگر هیچ‌کدوم نگرفتیم، کل آبجکت رو دامپ می‌کنیم تا حداقل کاربر چیزی ببینه.
        text_out = str(response)

    return text_out


def healthcheck() -> Dict[str, Any]:
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
    برمی‌گردونه: یک متن یکپارچه. بدون مقدمه/هسته/جمع‌بندی جدا.

    ورودی context از ریتریور می‌آید (Top-K نتایج دانش داخلی).
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

    # prompt نهایی که به مدل می‌فرستیم
    ctx_block = _join_context(context)
    prompt = (
        "شما یک دستیار منتور فارسی هستی. پاسخ باید روان، حرفه‌ای و عمل‌محور باشد. "
        "پاسخ را فقط در یک بلوک متنی بده. "
        "هیچ تیتر جداگانه مثل «مقدمه / هسته / جمع‌بندی» استفاده نکن.\n\n"
        f"سؤال کاربر:\n{query.strip()}\n"
        f"{ctx_block}"
    )

    # کش برای صرفه‌جویی در هزینه اگر سوال تکراری باشه
    cache_key = f"{provider}:{hash((query, ctx_block, max_new_tokens, temperature))}"
    if cache_key in cache:
        return str(cache[cache_key])

    # 1. اگر rule-based می‌تونه جواب بده (خیلی ارزون)
    rb = _rule_based_answer(query)
    if rb:
        result_text = rb
        cache[cache_key] = result_text
        _save_cache(cache_path, cache)
        return result_text

    # 2. اگر provider == "openai" و کلید هست → بفرست به OpenAI Responses API
    #    مدل gpt-4o-mini مخصوص جواب‌دهی سریع و کم‌هزینه با کیفیت بالاست. :contentReference[oaicite:7]{index=7}
    if provider == "openai" and api_key:
        try:
            result_text = _openai_generate(
                prompt=prompt,
                api_key=api_key,
                model_name=model_name,
                temperature=temperature,
                max_new_tokens=max_new_tokens,
            )
            cache[cache_key] = result_text
            _save_cache(cache_path, cache)
            return result_text
        except Exception as e:
            # اگر اوپن‌ای‌آی شکست خورد پایین‌تر fallback می‌رویم
            pass

    # 3. اگر provider == "huggingface" و HF_TOKEN هست → بفرست به HF
    if provider == "huggingface" and hf_tok:
        try:
            result_text = _hf_generate(
                prompt=prompt,
                endpoint=endpoint,
                token=hf_tok,
                temperature=temperature,
                max_new_tokens=max_new_tokens,
            )
            cache[cache_key] = result_text
            _save_cache(cache_path, cache)
            return result_text
        except Exception:
            pass

    # 4. آخرین دفاع: fallback لوکال
    fallback_text = (
        "برای رسیدن سریع به نتیجه، مسئله‌ات را به یک گام ۳۰ تا ۶۰ دقیقه‌ای تقسیم کن. "
        "هر تغییر را با معیار «آیا می‌شود همین امروز نشانش داد؟» بسنج. "
        "تا جایی که می‌توانی از کش و پاسخ‌های تکراری استفاده کن و فقط وقتی لازم شد "
        "سراغ مدل ابری برو تا هزینه را پایین نگه داری."
    )
    cache[cache_key] = fallback_text
    _save_cache(cache_path, cache)

    return fallback_text
