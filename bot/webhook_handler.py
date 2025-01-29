from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
import hmac
import hashlib
import json
from config import WEBHOOK_SECRET
from .twitter_client import TwitterClient
from .fallacy_detector import FallacyDetector

app = FastAPI()
twitter_client = TwitterClient()
fallacy_detector = FallacyDetector()

def verify_signature(request_body: bytes, signature: str) -> bool:
    """Verify the webhook signature from Twitter"""
    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode('utf-8'),
        msg=request_body,
        digestmod=hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected_signature)

@app.post("/webhook")
async def twitter_webhook(request: Request):
    """Handle incoming webhook events from Twitter"""
    body = await request.body()
    signature = request.headers.get("x-twitter-webhooks-signature")
    
    if not verify_signature(body, signature):
        return JSONResponse(status_code=403, content={"error": "Invalid signature"})
    
    data = json.loads(body)
    
    # Handle tweet_create_events
    if "tweet_create_events" in data:
        for tweet in data["tweet_create_events"]:
            # Don't respond to our own tweets
            if tweet["user"]["id_str"] == twitter_client.api.verify_credentials().id_str:
                continue
            
            # Analyze tweet for fallacies
            fallacies = fallacy_detector.detect_fallacies(tweet["text"])
            if fallacies:
                response = fallacy_detector.generate_response(fallacies, tweet["text"])
                if response:
                    twitter_client.reply_to_tweet(tweet["id"], response)
    
    return Response(status_code=200)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
