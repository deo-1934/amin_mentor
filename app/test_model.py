from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

model_name = "google/flan-t5-small"

try:
    print("بارگذاری مدل...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    print("مدل با موفقیت بارگذاری شد!")
except Exception as e:
    print(f"خطا در بارگذاری مدل: {e}")
