"""
Run this FIRST to confirm your Groq key works:
    python test_groq.py
"""
import os, sys, requests
from dotenv import load_dotenv
load_dotenv()

key = os.environ.get('GROQ_API_KEY', '')
if not key:
    print("ERROR: GROQ_API_KEY not found in .env file")
    sys.exit(1)

print(f"Key found: {key[:12]}...")

headers = {
    "Authorization": f"Bearer {key}",
    "Content-Type":  "application/json",
}

MODELS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "gemma2-9b-it"]

for model in MODELS:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a UML expert. Reply only with @startuml\nA -> B: hello\n@enduml"},
            {"role": "user",   "content": "Give me a simple sequence diagram."},
        ],
        "max_tokens": 100,
    }
    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers, json=payload, timeout=20
        )
        if resp.ok:
            text = resp.json()["choices"][0]["message"]["content"]
            print(f"\n✓ SUCCESS with model: {model}")
            print(f"  Response: {text[:80]}")
            print(f"\nYour key works! Run: python app.py")
            sys.exit(0)
        else:
            print(f"✗ {model}: HTTP {resp.status_code} — {resp.text[:100]}")
    except Exception as e:
        print(f"✗ {model}: {e}")

print("\nAll models failed. Check your GROQ_API_KEY in .env")
sys.exit(1)
