import tweepy
from config import (
    TWITTER_API_KEY,
    TWITTER_API_SECRET,
    TWITTER_ACCESS_TOKEN,
    TWITTER_ACCESS_TOKEN_SECRET,
)

class TwitterClient:
    def __init__(self):
        auth = tweepy.OAuthHandler(TWITTER_API_KEY, TWITTER_API_SECRET)
        auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET)
        self.api = tweepy.API(auth)
        self.client = tweepy.Client(
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_TOKEN_SECRET
        )

    def reply_to_tweet(self, tweet_id: str, text: str) -> bool:
        """Reply to a tweet with the given text"""
        try:
            self.client.create_tweet(
                text=text,
                in_reply_to_tweet_id=tweet_id
            )
            return True
        except Exception as e:
            print(f"Error replying to tweet: {e}")
            return False

    def get_tweet(self, tweet_id: str) -> dict:
        """Get tweet data by ID"""
        try:
            tweet = self.client.get_tweet(tweet_id)
            return tweet.data
        except Exception as e:
            print(f"Error getting tweet: {e}")
            return None
