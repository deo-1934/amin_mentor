#FEYZ
#DEO
# -*- coding: utf-8 -*-
"""
generator.py
لایه‌ی هوشمند برای کم‌کردن هزینه:
1) Rule-based → اگر سوال ساده/تکراری بود همین‌جا جواب می‌ده (بدون هزینه)
2) Retrieval داخلی → اگر تو دیتای خودمون جواب هست، از همون می‌ده (بدون هزینه)
3) OpenAI/HF → فقط وقتی لازم شد می‌ره سراغ مدل ابری
4) fallback → اگر هیچی کار نکرد، یه جواب امن می‌ده

خروجی همیشه فقط یک متن یک‌تکه است (نه مقدمه/بدنه/جمع‌بندی).
"""

import os, json
from pathlib import Path
from typing import Dict, Any, Optional, List
import requests

# تلاش برای ایمپورت OpenAI SDK جدید
try:
    from openai import OpenAI  # type: ignore
except Exception:
    OpenAI = None


def _read_secret_or_env(key: str, default: str = "") -> str:
    """
    اول از st.secrets (روی Streamlit Cloud)
    بعد از os.environ (روی لوکال .env)
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
    مقادیر تنظیمات مدل و مسیر کش رو برمی‌گردونه
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
    context یعنی تیکه‌های برگردونده از retriever.retrieve()
    ما این تیکه‌ها رو به مدل خارجی می‌دیم تا بهتر بفهمه، ولی مستقیم به کاربر نشونش نمی‌دیم.
    """
    if not context:
        return ""
    cleaned = [c.strip() for c in context if c and c.strip()]
    if not cleaned:
        return ""
    ctx = "\n\n".join(cleaned)
    return (
        "\n\n[یادداشت کمکی برای مدل (دانش داخلی ما):]\n"
        f"{ctx}\n"
    )


# یک بانک جواب‌های آماده و ارزان برای سوال‌های پرتکرار / ساده
_RULES = {
    "streamlit": (
        "برای استقرار در Streamlit Cloud: نسخهٔ پایتون رو در runtime.txt قفل کن (مثلاً 3.11)، "
        "Secrets رو جایگزین .env کن، و یک فایل __init__.py داخل پوشه app بذار تا import خراب نشه."
    ),
    "faiss": (
        "برای جست‌وجوی محلی سریع باید متن رو تمیز و تکه‌بندی کنی، با all-MiniLM-L6-v2 امبدینگ بگیری "
        "و بعدش این امبدینگ‌ها رو داخل FAISS ذخیره کنی تا top_k خیلی سریع بیاد."
    ),
    "api": (
        "برای کم‌کردن هزینهٔ API، سوالات تکراری رو کش کن و فقط برای سوال‌های واقعاً جدید یا پیچیده برو سراغ مدل ابری. "
        "قبل از خرج‌کردن، مسئله رو به یک قدم کوچک و قابل‌اجرا در امروز تبدیل کن."
    ),
    "کسب و کار": (
        "هستهٔ هر کسب‌وکار سالم اینه که یک درد واقعی مشتری رو حل کنه با یه ارزشی که قابل لمس باشه. "
        "تا وقتی به تکرارپذیری نرسیدی، دنبال بزرگ‌شدن نباش."
    ),
    "مذاکره": (
        "در مذاکره اول گوش بده و بفهم طرف مقابل چی می‌خواد و چرا. "
        "بجای جنگیدن برای قانع کردن، دنبال نقطهٔ برد-برد باش."
    ),
}


def _rule_based_answer(query: str) -> Optional[str]:
    """
    اگر سوال کاربر شامل یک کلیدواژه از RULES باشه،
    بدون هیچ هزینه‌ای همون لحظه جواب می‌دیم.
    این یعنی مرحله‌ی ۱ (ارزون‌ترین حالت).
    """
    q_low = (query or "").lower()
    for key, val in _RULES.items():
        if key.lower() in q_low:
            return val
    return None


def _hf_generate(
    prompt: str,
    endpoint: str,
    token: str,
    temperature: float,
    max_new_tokens: int,
    timeout: float = 40.0
) -> str:
    """
    تماس با HuggingFace Inference API (مرحله مدل ابری اقتصادی‌تر).
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

    # ساختار متداول خروجی HF
    if isinstance(data, list) and data and isinstance(data[0], dict) and "generated_text" in data[0]:
        return str(data[0]["generated_text"]).strip()
    if isinstance(data, dict) and "generated_text" in data:
        return str(data["generated_text"]).strip()

    return json.dumps(data, ensure_ascii=False)


#DEO
def _openai_generate(
    prompt: str,
    api_key: str,
    model_name: str,
    temperature: float,
    max_new_tokens: int
) -> str:
    """
    تماس با OpenAI (گرون‌ترین مرحله).
    از SDK جدید OpenAI استفاده می‌کنیم که با client.responses.create کار می‌کنه.
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

    # چند حالت مختلف خروجی رو پوشش می‌دیم تا متن رو دربیاریم
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

    if (not text_out) and hasattr(response, "output_text"):
        try:
            text_out = str(response.output_text).strip()
        except Exception:
            pass

    if (not text_out) and hasattr(response, "choices"):
        try:
            if response.choices and hasattr(response.choices[0], "message"):
                msg = response.choices[0].message
                if hasattr(msg, "content"):
                    text_out = str(msg.content).strip()
        except Exception:
            pass

    if not text_out:
        text_out = str(response)

    return text_out


def healthcheck() -> Dict[str, Any]:
    """
    فقط برای دیباگ محلی / لوکال. در UI نهایی ما دیگه نشونش نمی‌دیم.
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
    این همون تابعی‌ه که ui.py صداش می‌زنه.
    استراتژی:
    - مرحله 1: Rule-based (هیچ تماس گرونی نداره)
    - مرحله 2: جواب بر اساس context بازیابی‌شده (بازم بدون تماس گرون)
    - مرحله 3: مدل ابری (OpenAI یا HuggingFace)
    - مرحله 4: fallback امن
    خروجی همیشه یک متن یک‌تکه است.
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

    # context از ریتریور میاد. این یعنی قطعه‌های دانش داخلی ما.
    ctx_list = context or []
    ctx_joined = "\n\n".join(ctx_list)

    # کش: اگر قبلاً همین سؤال با همین context پرسیده شده، مستقیم بده
    cache_key = f"{provider}:{hash((query, ctx_joined, max_new_tokens, temperature))}"
    if cache_key in cache:
        return str(cache[cache_key])

    # --- مرحله ۱: Rule-based (ارزون‌ترین) ---
    rb = _rule_based_answer(query)
    if rb:
        final_text = rb
        cache[cache_key] = final_text
        _save_cache(cache_path, cache)
        return final_text

    # --- مرحله ۲: جواب از context داخلی بدون مدل ابری ---
    # اگه retriever تونسته پاراگراف مرتبط پیدا کنه، از همون جواب بساز
    if ctx_list:
        best_snippet = ctx_list[0]
        if len(best_snippet.strip()) > 40:
            local_answer = (
                f"بر اساس محتوای داخلی ما:\n\n{best_snippet}\n\n"
                "اگر لازم داری این رو به یک برنامه عملی و مرحله‌به‌مرحله تبدیل کنیم بگو."
            )
            final_text = local_answer
            cache[cache_key] = final_text
            _save_cache(cache_path, cache)
            return final_text

    # --- مرحله ۳: مدل ابری (فقط اگر هنوز جواب ندادیم) ---
    # اینجاست که هزینه می‌دی. اگر کلید هست و provider مناسب هست، می‌ریم سراغش.

    # ۳.a: OpenAI (گرون ولی باکیفیت)
    if provider == "openai" and api_key:
        try:
            prompt = (
                "شما یک منتور و مشاور فارسی هستی. پاسخت باید روان، محترمانه و عملی باشد. "
                "پاسخ را در یک متن یک‌تکه بده، بدون تیتر یا بخش‌بندی رسمی.\n\n"
                f"سؤال کاربر:\n{query.strip()}\n\n"
                "اگر لازم شد از این دانش داخلی کمک بگیر:\n"
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
            # اگر تماس OpenAI خطا داد، ادامه می‌دیم به HuggingFace یا fallback
            pass

    # ۳.b: HuggingFace (در صورت تنظیم)
    if provider == "huggingface" and hf_tok:
        try:
            prompt = (
                "تو یک دستیار فارسی هستی. پاسخ را شفاف و یک‌تکه بده.\n\n"
                f"سؤال کاربر:\n{query.strip()}\n\n"
                "دانش داخلی:\n"
                f"{ctx_joined}\n"
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

    # --- مرحله ۴: fallback نهایی ---
    final_text = (
        "مسئله‌ات را تبدیل کن به یک قدم مشخص که در ۳۰ تا ۶۰ دقیقه می‌توانی همین امروز انجامش بدهی. "
        "هر ایده‌ای را فقط با یک معیار بسنج: آیا خروجی قابل نشان‌دادن تولید می‌کند یا فقط حس شلوغ‌کاری می‌دهد؟ "
        "اگر بخواهی، می‌توانم همین الان با هم آن یک قدم را تعریف کنیم."
    )
    cache[cache_key] = final_text
    _save_cache(cache_path, cache)
    return final_text
