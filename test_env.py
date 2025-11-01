from dotenv import load_dotenv
import os

load_dotenv()

print("MODEL_PROVIDER =", os.getenv("MODEL_PROVIDER"))
print("OPENAI_MODEL   =", os.getenv("OPENAI_MODEL"))
print("API_KEY exists?", bool(os.getenv("OPENAI_API_KEY")))
