import os
from google import genai

print("Starting Gemini test...")

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError("GEMINI_API_KEY is missing")

client = genai.Client(api_key=api_key)

response = client.models.generate_content(
    model="gemini-3.5-flash-lite",
    contents="Reply with exactly: Gemini API connected successfully."
)

print("Gemini response:", response.text)

client.close()