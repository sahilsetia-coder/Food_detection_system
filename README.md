# FreshCheck AI — Food Spoilage Image Scanner

A small full-stack prototype that lets a user upload a food image and calls Nyckel's food-spoilage-indicators classifier.

## Important credential safety
The client secret was pasted into a chat. Treat it as exposed: rotate/revoke it in Nyckel before using this project. Do not paste the replacement secret into chat or browser code. The app reads credentials from a local `.env` file and makes Nyckel calls on the server.

## Prerequisites
- Python 3.10+
- A Nyckel account
- A Nyckel function ID for your cloned food-spoilage-indicators classifier

## Setup

1. Extract the project ZIP and open a terminal in the project folder.
2. Create and activate a virtual environment (optional but recommended):
   - Windows: `python -m venv .venv` then `.venv\\Scripts\\activate`
   - macOS/Linux: `python3 -m venv .venv` then `source .venv/bin/activate`
3. Install dependencies:
   `pip install -r requirements.txt`
4. Copy `.env.example` to `.env`.
5. Add your rotated Nyckel client ID, client secret, and function ID to `.env`.
6. Start the server:
   `uvicorn app:app --reload`
7. Open `http://127.0.0.1:8000` in your browser.

## Find the function ID
Open the Nyckel food-spoilage-indicators pretrained classifier page, clone it to your account if needed, then open its Integrate/API section. Copy the function ID from the invoke endpoint:
`https://www.nyckel.com/v1/functions/FUNCTION_ID/invoke`

## How it works
- Browser uploads an image to `/api/analyze`.
- FastAPI validates file type and size.
- Server obtains and caches a short-lived access token using client credentials.
- Server sends the image to Nyckel's function invoke endpoint.
- The UI displays the predicted label and confidence score.

## Troubleshooting
- `Missing NYCKEL_FUNCTION_ID`: fill in `NYCKEL_FUNCTION_ID` in `.env`.
- Authentication failed: check the rotated credentials and ensure the account has access to the function.
- Prediction failed / 404: confirm the function ID and endpoint in Nyckel's Integrate tab.
- If the API rejects the image payload, check the exact image input format shown in the Integrate tab for your function; Nyckel accepts image URLs or base64-encoded images, but the expected encoding convention can vary by integration.

## Safety limitation
This is a visual indicator classifier, not a microbiological safety test. A prediction such as “no obvious indicator” does not prove food is safe to eat. Never taste food to test it; follow food-safety guidance and discard food when appropriate.
