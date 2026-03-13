import os
import requests
from dotenv import load_dotenv

# This simple script checks whether our API connection to Anthropic's Claude is working correctly.

# Load our secret API keys from the .env configuration file
load_dotenv()
api_key = os.environ.get("ANTHROPIC_API_KEY")
print(f"API Key present: {bool(api_key)}")

# Prepare the "envelope" (Headers) identifying us to the Anthropic server
headers = {
    "x-api-key": api_key,
    "anthropic-version": "2023-06-01",
    "content-type": "application/json"
}

# Prepare a simple payload (a bare-minimum packet of data asking the AI to say Hello)
data = {
    "model": "claude-4-6-sonnet-latest",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "Hello, Claude!"}]
}

try:
    print("Testing direct HTTPS request to https://api.anthropic.com/v1/messages...")
    # Fire off our message to Anthropic over the internet
    response = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=data)
    
    # Print out the results (status code 200 means success)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    # If anything went wrong (like no internet), print the error
    print(f"Error: {e}")
