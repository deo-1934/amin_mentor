import openai
import os

# تنظیم کلید API
openai.api_key = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY")

def generate_response(query, retrieved_data):
    prompt = f"""
    شما یک منتور شخصی هستید. بر اساس داده‌های زیر به سوال کاربر پاسخ دهید.
    اگر داده‌های مرتبط کافی نیستند، پاسخ دهید: "متأسفانه اطلاعات کافی برای پاسخ به این سوال ندارم."

    داده‌های مرتبط:
    {"\n".join(retrieved_data)}

    سوال کاربر:
    {query}

    پاسخ:
    """

    response = openai.Completion.create(
        engine="gpt-3.5-turbo-instruct",
        prompt=prompt,
        max_tokens=200,
        temperature=0.7
    )

    return response.choices[0].text.strip()
