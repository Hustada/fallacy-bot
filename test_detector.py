from bot.fallacy_detector import FallacyDetector
import asyncio
import logging
from dotenv import load_dotenv
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Test tweets
test_tweets = {
    # Clear logical fallacies
    "ad_hominem": "Don't listen to Dr. Smith's climate research. He drives a gas-guzzling SUV, total hypocrite!",
    "false_dichotomy": "Either you support unrestricted gun rights, or you hate freedom. There's no middle ground.",
    "appeal_to_authority": "As a mother of three, I can tell you vaccines are dangerous. Trust me, I've done my research.",
    
    # Inappropriate hyperbole in serious contexts
    "inappropriate_historical": "This new policy is literally worse than the darkest moments in human history. It's like 1984 meets the Holocaust.",
    "exaggerated_stats": "Crime has increased by 5000% since last year! Our city has become a complete war zone with violence on every corner!",
    "diminishing_serious": "Having to wait 2 hours at the DMV is basically torture and a violation of human rights.",
    
    # Acceptable hyperbole (casual/emotional)
    "casual_hyperbole": "This is the BEST sandwich I've ever had in my entire life! I would die for another bite! 😋",
    "emotional_expression": "I'm so hungry I could eat a horse right now! 🐎",
    
    # Mixed fallacies and hyperbole
    "mixed_issues": "This policy will DESTROY AMERICA FOREVER! My neighbor's cousin's friend lost their job because of it, which proves it's destroying millions of lives. Anyone who supports it is clearly a traitor!",
    
    # Control cases (no issues)
    "valid_argument": "Recent studies show a 15% increase in crime rates downtown compared to last year. Here's a link to the police statistics.",
    "casual_opinion": "I prefer taking the train to work. It's more relaxing and better for the environment.",
    "joke_tweet": "Breaking news: My cat has declared herself the supreme ruler of the living room. Opposition parties (the dog) have filed a formal protest 😺"
}

async def test_fallacy_detector():
    detector = FallacyDetector()
    
    print("\n=== Testing Fallacy Detector with Multiple LLMs ===\n")
    
    for category, tweet in test_tweets.items():
        print(f"\n--- Testing {category} ---")
        print(f"Tweet: {tweet}")
        
        # Detect fallacies
        fallacies = await detector.detect_fallacies(tweet)
        
        if fallacies:
            print("\nFallacies detected:")
            for fallacy in fallacies:
                print(f"- Type: {fallacy['type']}")
                print(f"  Subtype: {fallacy['subtype']}")
                print(f"  Explanation: {fallacy['explanation']}")
                print(f"  Confidence: {fallacy['confidence']}")
                print(f"  Source: {fallacy['source']}")
            
            # Generate response
            response = detector.generate_twitter_response(fallacies, tweet)
            if response:
                print(f"\nBot's response: {response}")
        else:
            print("\nNo fallacies detected")
        
        print("\n" + "="*50)

if __name__ == "__main__":
    asyncio.run(test_fallacy_detector())
