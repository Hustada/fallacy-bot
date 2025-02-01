"""Test tweets for fallacy detection."""
import logging
from typing import List, Dict, Any
from .fallacy_detector import FallacyDetector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_fallacy_detection():
    """Test the fallacy detector with various examples."""
    detector = FallacyDetector()
    
    test_tweets = [
        # Ad Hominem
        "Don't listen to Dr. Smith's climate research. He drives a gas-guzzling SUV, so he's clearly a hypocrite!",
        
        # Strawman
        "Environmentalists want us all to live in caves without electricity. That's why we can't trust their green energy proposals.",
        
        # False Dichotomy
        "Either we completely ban all immigration, or we'll have complete open borders. There's no middle ground!",
        
        # Bandwagon
        "Everyone knows that vaccines are dangerous. Just look at how many people on social media are talking about it!",
        
        # Hasty Generalization
        "My neighbor got robbed by someone from that neighborhood, so clearly that whole area is full of criminals.",
        
        # Appeal to Authority (Misused)
        "My favorite celebrity says this diet cures all diseases. She has millions of followers, so she must be right!",
        
        # Post Hoc
        "I started wearing this crystal necklace and a week later got a promotion. These crystals really work!",
        
        # Sarcasm (should not trigger)
        "Oh sure, because OBVIOUSLY the earth is flat. I mean, just look out your window - it's totally not curved! 🙄",
        
        # Slippery Slope
        "If we allow gay marriage, next people will want to marry their pets, then their cars, then buildings!",
        
        # Red Herring
        "Why are we discussing climate change when there are still people who can't afford healthcare?",
        
        # Whataboutism
        "Sure, our candidate lied, but what about all the lies from the other side? They're much worse!",
        
        # Appeal to Nature
        "This medicine can't be good for you because it's not natural. Only natural remedies can truly heal.",
        
        # Circular Reasoning
        "The Bible is true because it says it's the word of God, and we know God exists because the Bible tells us so.",
        
        # No True Scotsman
        "No real patriot would ever criticize their country. If they do, they're not a true patriot.",
        
        # Intentional Exaggeration (should not trigger)
        "If I have to sit through one more meeting, I'm going to explode into a million pieces! 🤯",
    ]
    
    print("\n=== Testing Fallacy Detection ===\n")
    for tweet in test_tweets:
        print(f"\nTesting tweet: {tweet}")
        fallacies = detector.detect_fallacies(tweet)
        if fallacies:
            print(f"✅ Detected fallacies: {fallacies}")
        else:
            print("❌ No fallacies detected")
        print("-" * 80)

if __name__ == "__main__":
    test_fallacy_detection()
