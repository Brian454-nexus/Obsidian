import os
import requests
from dotenv import load_dotenv

# Resolves available model identifiers from the Anthropic metadata endpoint.
load_dotenv()
api_key = os.environ.get("ANTHROPIC_API_KEY")

headers = {
    "x-api-key": api_key,
    "anthropic-version": "2023-06-01"
}

try:
    print("Fetching active model identifiers...")
    response = requests.get("https://api.anthropic.com/v1/models", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        models = data.get("data", [])
        
        for m in models:
            print(f"- {m.get('id')} (type: {m.get('type')})")
    else:
        print(f"HTTP Error {response.status_code}: {response.text}")
except Exception as e:
    print(f"Transport layer exception: {e}")
