from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import requests

# Load environment variables
load_dotenv()

# Get Ayrshare API key
API_KEY = os.getenv("AYRSHARE_API_KEY")
API_URL = os.getenv("AYRSHARE_URL")
PRIVATE_KEY_PATH = os.getenv("PRIVATE_KEY_PATH")

if not API_KEY:
    raise ValueError("AYRSHARE_API_KEY is not set in the .env file")
elif not API_URL:
    raise ValueError("AYRSHARE_API_URL is not set in the .env file")
elif not PRIVATE_KEY_PATH:
    raise ValueError("PRIVATE_KEY_PATH is not set in the .env file")

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

with open(PRIVATE_KEY_PATH, "r") as f:
    PRIVATE_KEY = f.read()

# FastAPI app instance
app = FastAPI()


# Define request body schema
class PostRequest(BaseModel):
    profileKey: str
    post: str
    platforms: list[str]
    mediaUrls: list[str] = []  # Optional media


class ProfileRequest(BaseModel):
    title: str

class JWTRequest(BaseModel):
    profileKey: str  # dynamic input per user


@app.post("/post-to-social")
def post_to_social(data: PostRequest):
    url = f"{API_URL}/post"
    payload = {
        "post": data.post,
        "platforms": data.platforms,
        "mediaUrls": data.mediaUrls
    }
    try:
        response = requests.post(url, json=payload, headers=HEADERS)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@app.post("/create-profile")
def create_profile(data: ProfileRequest):
    url = f"{API_URL}/profiles"
    payload = {"title": data.title}
    try:
        response = requests.post(url, json=payload, headers=HEADERS)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Request failed: {e}")

    
@app.post("/generate-jwt")
def generate_jwt(data: JWTRequest):
    url = f"{API_URL}/profiles/generateJWT"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "domain": "ACME",  # Change to your custom domain if needed
        "privateKey": PRIVATE_KEY, #paid
        "profileKey": data.profileKey,
        # "redirect":
        # "allowedSocial":["facebook", "x", "linkedin", "tiktok"]
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")
    

@app.post("/post-by-profile")
def post_by_profile(data: PostRequest):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
        "Profile-Key": data.profileKey
    }
    url = f"{API_URL}/post"
    payload = {
        "post": data.post,
        "platforms": data.platforms,
        "mediaUrls": data.mediaUrls
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@app.get("/active-social-accounts")
def get_active_social_accounts(): #data:JWTRequest
    headers = {
        "Authorization": f"Bearer {API_KEY}"
        # "Profile-Key": data.profileKey
    }
    url = f"{API_URL}/user"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        user_data = response.json()
        # return user_data
        
        # Only return the active social accounts
        return {
            "activeSocialAccounts": user_data.get("activeSocialAccounts", [])
        }
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")
    

# uvicorn server2:app --reload 