# check_models.py
import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load the .env file to get your API key
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("API Key not found. Make sure your .env file is set up correctly.")
else:
    genai.configure(api_key=api_key)
    print("Successfully configured API key. Checking for available models...")

    try:
        # List all models that support the 'generateContent' method
        for model in genai.list_models():
            if 'generateContent' in model.supported_generation_methods:
                print(f"- {model.name}")
    except Exception as e:
        print(f"An error occurred while trying to list models: {e}")