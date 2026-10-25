import os
import time
import base64
from typing import Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

NYCKEL_CLIENT_ID = os.getenv("NYCKEL_CLIENT_ID", "").strip()
NYCKEL_CLIENT_SECRET = os.getenv("NYCKEL_CLIENT_SECRET", "").strip()
NYCKEL_FUNCTION_ID = os.getenv("NYCKEL_FUNCTION_ID", "").strip()

TOKEN_URL = "https://www.nyckel.com/connect/token"
NYCKEL_INVOKE_URL = "https://www.nyckel.com/v1/functions/{}/invoke"

app = FastAPI(title="Food Spoilage AI", version="1.0.0")
app.mount("/static", StaticFiles(directory="static"), name="static")

_token: Optional[str] = None
_token_expires_at = 0


@app.get("/")
async def home():
    return FileResponse("static/index.html")


async def get_access_token() -> str:
    global _token, _token_expires_at

    if _token and time.time() < _token_expires_at - 60:
        return _token

    if not NYCKEL_CLIENT_ID or not NYCKEL_CLIENT_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Nyckel credentials are not configured. Add them to your .env file."
        )

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "client_credentials",
                "client_id": NYCKEL_CLIENT_ID,
                "client_secret": NYCKEL_CLIENT_SECRET,
            },
        )

    if response.is_error:
        raise HTTPException(
            status_code=502,
            detail="Nyckel authentication failed. Check your credentials and rotate any exposed secret."
        )

    token_data = response.json()
    _token = token_data.get("access_token")
    if not _token:
        raise HTTPException(status_code=502, detail="Nyckel did not return an access token.")

    _token_expires_at = time.time() + int(token_data.get("expires_in", 3600))
    return _token


@app.post("/api/analyze")
async def analyze_food(file: UploadFile = File(...)):
    allowed = {"image/jpeg", "image/png", "image/webp", "image/bmp"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=415, detail="Upload a JPG, PNG, WEBP, or BMP image.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(content) > 8 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image must be 8 MB or smaller.")

    if not NYCKEL_FUNCTION_ID:
        raise HTTPException(
            status_code=503,
            detail="Missing NYCKEL_FUNCTION_ID. Clone the food-spoilage classifier in Nyckel and add its function ID to .env."
        )

    token = await get_access_token()
    encoded = base64.b64encode(content).decode("ascii")

    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.post(
            NYCKEL_INVOKE_URL.format(NYCKEL_FUNCTION_ID),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={"data": encoded},
        )

    if response.status_code == 401:
        # Force a fresh token on the next request.
        global _token, _token_expires_at
        _token, _token_expires_at = None, 0
        raise HTTPException(status_code=502, detail="Nyckel rejected the access token. Try again.")
    if response.is_error:
        raise HTTPException(
            status_code=502,
            detail=f"Nyckel prediction failed (HTTP {response.status_code}). Verify your function ID and API access."
        )

    prediction = response.json()
    label = prediction.get("labelName", "Unknown")
    confidence = prediction.get("confidence")
    confidence_percent = round(float(confidence) * 100, 1) if confidence is not None else None

    # This is only a cautious UI hint, not a food-safety verdict.
    label_lower = label.lower()
    if any(word in label_lower for word in ["mold", "rotten", "spoiled", "discolor", "foul odor", "liquefaction"]):
        guidance = "A visible spoilage-related indicator may be present. Do not taste the food to check it; discard it if spoilage is apparent."
        category = "attention"
    else:
        guidance = "This prediction did not identify an obvious spoilage-related label. It cannot confirm that the food is safe to eat."
        category = "neutral"

    return {
        "labelName": label,
        "confidence": confidence,
        "confidencePercent": confidence_percent,
        "guidance": guidance,
        "category": category,
        "safetyNote": "Image classification cannot detect all harmful microorganisms or toxins. Follow food-safety storage guidance; when in doubt, discard the food.",
    }
