import os
import requests
from dotenv import load_dotenv

# This script just asks Anthropic's servers "What AI models do you currently have available?"
# It helps us check if a specific model version (like 'claude-sonnet-3-5') is active.

# Load our secret API keys from the .env configuration file
load_dotenv()
api_key = os.environ.get("ANTHROPIC_API_KEY")

# Set up our authentication headers
headers = {
    "x-api-key": api_key,
    "anthropic-version": "2023-06-01"
}

try:
    print("Fetching available models...")
    # Send a GET request to ask for the list of models
    response = requests.get("https://api.anthropic.com/v1/models", headers=headers)
    
    # If the request was successful (200 OK)
    if response.status_code == 200:
        data = response.json()
        models = data.get("data", [])
        
        # Print each model ID out so we can read the list
        for m in models:
            print(f"- {m.get('id')} (type: {m.get('type')})")
    else:
        # If we didn't get a 200 (like a 401 Unauthorized due to bad API key), print the error
        print(f"Error {response.status_code}: {response.text}")
except Exception as e:
    # If the network connection completely failed
    print(f"Request failed: {e}")
