import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CareerPath.settings")
django.setup()

from google import genai

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("API key not found")
else:
    try:
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents="Reply with: Gemini connection successful"
        )

        print(response.text)

    except Exception as e:
        print("Error:", e)