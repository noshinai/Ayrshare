import os
import uuid
import requests
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime

# Load environment variables
load_dotenv()

# --- ENVIRONMENT CONFIG ---
API_KEY = os.getenv("AYRSHARE_API_KEY")
API_URL = os.getenv("AYRSHARE_URL")
PRIVATE_KEY_PATH = os.getenv("PRIVATE_KEY_PATH")
DATABASE_URL = os.getenv("DATABASE_URL")  # e.g. postgresql://user:password@localhost/dbname

if not all([API_KEY, API_URL, PRIVATE_KEY_PATH, DATABASE_URL]):
    raise ValueError("Missing required environment variables")

with open(PRIVATE_KEY_PATH, "r") as f:
    PRIVATE_KEY = f.read()

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

# --- DATABASE CONFIG ---
Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- MODELS ---
class UserAyrshareProfile(Base):
    __tablename__ = "user_ayrshare_profile"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, unique=True, nullable=False)
    profile_key = Column(String, nullable=False)
    ref_id = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SocialPlatformPreference(Base):
    __tablename__ = "social_platform_preference"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    platform = Column(String, nullable=False)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# --- INIT DB ---
Base.metadata.create_all(bind=engine)

# --- FASTAPI SETUP ---
app = FastAPI()


# --- SCHEMAS ---
class PostRequest(BaseModel):
    profileKey: str
    post: str
    platforms: list[str]
    mediaUrls: list[str] = []

class ProfileRequest(BaseModel):
    title: str
    user_id: str

class JWTRequest(BaseModel):
    profileKey: str

class TogglePlatformRequest(BaseModel):
    user_id: str
    platform: str
    enabled: bool


# --- API ROUTES ---
@app.post("/create-profile")
def create_profile(data: ProfileRequest, db: Session = Depends(get_db)):
    # Create profile via Ayrshare
    url = f"{API_URL}/profiles"
    try:
        response = requests.post(url, json={"title": data.title}, headers=HEADERS)
        response.raise_for_status()
        profile_data = response.json()
        profile_key = profile_data.get("profileKey")

        # Save to DB
        db.add(UserAyrshareProfile(user_id=data.user_id, profile_key=profile_key))
        db.commit()
        return profile_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/active-social-accounts/{user_id}")
def get_active_accounts(user_id: str, db: Session = Depends(get_db)):
    user_profile = db.query(UserAyrshareProfile).filter_by(user_id=user_id).first()
    if not user_profile:
        raise HTTPException(status_code=404, detail="Profile not found for user")

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Profile-Key": user_profile.profile_key
    }

    try:
        response = requests.get(f"{API_URL}/user", headers=headers)
        response.raise_for_status()
        user_data = response.json()
        active_platforms = user_data.get("activeSocialAccounts", [])
        ref_id = user_data.get("refId")

        if ref_id and ref_id != user_profile.ref_id:
            user_profile.ref_id = ref_id
            db.commit()

        # Sync platforms
        existing = db.query(SocialPlatformPreference).filter_by(user_id=user_id).all()
        existing_map = {e.platform: e for e in existing}

        result = []
        for platform in active_platforms:
            if platform not in existing_map:
                new_pref = SocialPlatformPreference(user_id=user_id, platform=platform)
                db.add(new_pref)
                result.append({"platform": platform, "enabled": True})
            else:
                result.append({"platform": platform, "enabled": existing_map[platform].enabled})

        db.commit()
        return {"platforms": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/toggle-platform")
def toggle_platform(data: TogglePlatformRequest, db: Session = Depends(get_db)):
    pref = (
        db.query(SocialPlatformPreference)
        .filter_by(user_id=data.user_id, platform=data.platform)
        .first()
    )
    if pref:
        pref.enabled = data.enabled
        db.commit()
    else:
        db.add(SocialPlatformPreference(user_id=data.user_id, platform=data.platform, enabled=data.enabled))
        db.commit()
    return {"message": "Preference updated"}


@app.post("/post-by-profile")
def post_by_profile(data: PostRequest):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "Profile-Key": data.profileKey
    }
    try:
        payload = {
            "post": data.post,
            "platforms": data.platforms,
            "mediaUrls": data.mediaUrls
        }
        response = requests.post(f"{API_URL}/post", json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-jwt")
def generate_jwt(data: JWTRequest):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "domain": "ACME",
        "privateKey": PRIVATE_KEY,
        "profileKey": data.profileKey
    }
    try:
        response = requests.post(f"{API_URL}/profiles/generateJWT", json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
