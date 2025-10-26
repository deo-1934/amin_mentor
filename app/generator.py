from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# بارگذاری مدل و توکن‌ایزر
model_name = "google/flan-t5-small"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

def generate_response(query, retrieved_data):
    """
    تولید پاسخ با استفاده از مدل flan-t5-small از Hugging Face.

    Args:
        query (str): سوال کاربر
        retrieved_data (list): لیست داده‌های بازیابی‌شده

    Returns:
        str: پاسخ تولیدشده توسط مدل
    """
    prompt = f"""
    شما یک منتور شخصی هستید. بر اساس داده‌های زیر به سوال کاربر پاسخ دهید.
    اگر داده‌های مرتبط کافی نیستند، پاسخ دهید: "متأسفانه اطلاعات کافی برای پاسخ به این سوال ندارم."

    داده‌های مرتبط:
    {"\\n".join(retrieved_data)}

    سوال کاربر:
    {query}

    پاسخ:
    """

    # توکنایز کردن ورودی
    inputs = tokenizer(prompt, return_tensors="pt")

    # تولید پاسخ
    outputs = model.generate(**inputs, max_length=200)

    # دیکد کردن پاسخ
    answer = tokenizer.decode(outputs[0], skip_special_tokens=True)

    return answer

def generate_answer(message, k=5, temperature=0.3):
    """
    تابع اصلی برای تولید پاسخ به سوال کاربر.

    Args:
        message (str): سوال کاربر
        k (int): تعداد داده‌های بازیابی‌شده
        temperature (float): پارامتر temperature برای مدل

    Returns:
        dict: پاسخ و منابع مرتبط
    """
    # اینجا باید منطق بازیابی داده‌ها از ایندکس FAISS یا ChromaDB اضافه شود
    # مثال: retrieved_data = retriever.retrieve(message, k=k)
    retrieved_data = []  # جایگزین با داده‌های واقعی

    answer = generate_response(message, retrieved_data)

    return {
        "answer": answer,
        "sources": [],
        "retrieved": [],
        "model": model_name
    }
