import os
from dotenv import load_dotenv
import requests

# Load variables from .env file
load_dotenv()

# Get the API key from environment
api_key = os.getenv("AYRSHARE_API_KEY")

# Make sure it's loaded
if not api_key:
    raise ValueError("AYRSHARE_API_KEY is not set in the .env file")

url = "https://api.ayrshare.com/api/post"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}
payload = {
    "post": "Good Night everyone, What are you doing?",  # Mandatory
    "platforms": ["facebook"],
    "mediaUrls": ["https://img.ayrshare.com/012/gb.jpg"]
}

response = requests.post(url, json=payload, headers=headers)
print(response.json())
