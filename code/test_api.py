import os
import requests
from dotenv import load_dotenv

# Validates HTTP/REST connectivity configuration for Anthropic integrations.
load_dotenv()
api_key = os.environ.get("ANTHROPIC_API_KEY")
print(f"API Key present: {bool(api_key)}")

# Construct standard API transport envelope
headers = {
    "x-api-key": api_key,
    "anthropic-version": "2023-06-01",
    "content-type": "application/json"
}

# Minimal message payload
data = {
    "model": "claude-sonnet-4-6",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "Hello, Claude!"}]
}

try:
    print("Testing external POST endpoint https://api.anthropic.com/v1/messages...")
    response = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=data)
    
    # 200 OK signals successful handshake
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"I/O Exception: {e}")
