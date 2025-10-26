import os
from app.settings import INDEX_DIR, DEFAULT_EMBED_MODEL

def retrieve(query: str):
    """
    تابع اصلی برای بازیابی پاسخ بر اساس کوئری کاربر.
    در این نسخه‌ی اولیه فقط یک پاسخ تستی برمی‌گرداند تا ارتباط بین ماژول‌ها بررسی شود.
    """

    # ✅ بررسی اینکه مسیر ایندکس وجود دارد
    if not os.path.exists(INDEX_DIR):
        return f"❌ مسیر ایندکس '{INDEX_DIR}' یافت نشد. لطفاً ایندکس را بسازید."

    # ✅ فعلاً پاسخ تستی برمی‌گردانیم (در نسخه بعدی با FAISS جایگزین می‌شود)
    response = f"🔍 در پاسخ به '{query}': این فقط یک پاسخ آزمایشی از تابع retrieve است.\n"
    response += f"(مدل فعلی: {DEFAULT_EMBED_MODEL})"
    return response
