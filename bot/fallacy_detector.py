from openai import OpenAI
from typing import Dict, List, Optional, Any
import json
import os
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FallacyDetector:
    def __init__(self):
        # Try all possible locations
        bot_env_path = Path(__file__).parent / '.env'
        root_env_path = Path(__file__).parent.parent / '.env'
        database_env_path = Path(__file__).parent.parent / 'database' / '.env'
        
        api_key = os.getenv("OPENAI_API_KEY")
        
        # If not in environment, try reading from files
        if not api_key:
            logger.info("API key not found in environment, checking .env files")
            for env_path in [database_env_path, bot_env_path, root_env_path]:  # prioritize database/.env
                if env_path.exists():
                    logger.info(f"Reading from {env_path}")
                    with open(env_path, 'r') as f:
                        for line in f:
                            if line.startswith('OPENAI_API_KEY='):
                                api_key = line.strip().split('=', 1)[1].strip("'").strip('"')
                                os.environ["OPENAI_API_KEY"] = api_key
                                break
        
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        
        logger.info(f"Initializing FallacyDetector with API key: {api_key[:10]}...")
        self.client = OpenAI(api_key=api_key)
        
        # Define fallacy types for reference
        self.fallacies = {
            "ad_hominem": "Attacking the person instead of their argument",
            "false_dichotomy": "Presenting only two options when more exist",
            "appeal_to_authority": "Claiming something is true because an authority said so",
            "strawman": "Misrepresenting an opponent's argument",
            "slippery_slope": "Arguing that a small first step will lead to significant negative consequences",
            "appeal_to_emotion": "Using emotions rather than facts to win an argument",
            "hasty_generalization": "Drawing conclusions from insufficient evidence",
            "circular_reasoning": "Using the conclusion as a premise",
            "bandwagon": "Arguing that something is true because many people believe it",
            "anecdotal": "Using a personal experience or isolated example instead of sound reasoning or evidence",
            "red_herring": "Introducing an irrelevant topic to divert attention",
            "whataboutism": "Deflecting criticism by pointing to someone else's actions",
            "appeal_to_nature": "Arguing that what is natural is inherently good/better",
            "post_hoc": "Assuming that because B followed A, A caused B",
            "no_true_scotsman": "Redefining terms to exclude counter-examples",
            "loaded_question": "Asking a question that contains a controversial assumption",
            "false_cause": "Incorrectly assuming one thing caused another",
            "appeal_to_ignorance": "Arguing something is true because it hasn't been proven false",
            "middle_ground": "Assuming the middle position between two extremes must be correct",
            "genetic": "Dismissing something solely based on its origin or history"
        }
        
        logger.info("FallacyDetector initialized successfully")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def detect_fallacies(self, text: str) -> List[Dict[str, Any]]:
        """Detect logical fallacies in text."""
        prompt = f"""Analyze this tweet for logical fallacies, being careful to distinguish between actual fallacies and rhetorical devices like sarcasm or purposeful exaggeration.

Tweet: "{text}"

Instructions:
1. First, determine if this tweet is:
   - Serious/literal
   - Sarcastic
   - Using purposeful exaggeration for effect
   - Making a joke or being humorous

2. Only identify fallacies if the tweet is being serious/literal. Ignore rhetorical devices used for humor or emphasis.

3. For each ACTUAL fallacy found (not rhetorical devices), provide:
   - Type of fallacy
   - Brief explanation
   - Confidence level (0.0-1.0)

IMPORTANT: Your response must be a valid JSON array. Only include fallacies with confidence > 0.8
If no actual fallacies are found, or if the tweet is clearly sarcastic/humorous, return an empty array: []

Example outputs:
[]  # for sarcastic/humorous tweets
[{{"type": "ad_hominem", "explanation": "Attacks the person instead of their argument", "confidence": 0.95}}]  # for actual fallacies

Your response (must be valid JSON array):"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",  # Using GPT-4 for better context understanding
                messages=[
                    {"role": "system", "content": "You are a logical fallacy detection expert who can distinguish between actual fallacies and rhetorical devices. You MUST respond with a valid JSON array."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1  # Lower temperature for more consistent analysis
            )
            
            result = response.choices[0].message.content.strip()
            
            # Ensure we have valid JSON array brackets
            if not (result.startswith('[') and result.endswith(']')):
                result = '[]'
            
            fallacies = json.loads(result)
            
            # Log the analysis for debugging
            logger.info(f"Fallacy analysis for tweet: {text[:100]}...")
            logger.info(f"Detected fallacies: {fallacies}")
            
            return fallacies
            
        except Exception as e:
            logger.error(f"Error detecting fallacies: {str(e)}")
            return []
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def generate_response(self, fallacies: List[Dict[str, Any]], original_text: str) -> Optional[str]:
        """Generate a response explaining the fallacies found."""
        if not fallacies:
            return None
            
        fallacy_descriptions = "\n".join([
            f"- {fallacy['type'].replace('_', ' ').title()}: {fallacy['explanation']}"
            for fallacy in fallacies
        ])
        
        prompt = f"""Write a friendly response explaining these logical fallacies found in a tweet:

Tweet: "{original_text}"

Fallacies found:
{fallacy_descriptions}

Write a response that:
1. Acknowledges their argument
2. Explains the fallacies found
3. Suggests how to make the argument stronger
4. Maintains a helpful and educational tone

Your response:"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that explains logical fallacies."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            return response.choices[0].message.content.strip()
                
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return None
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def explain_fallacy(self, fallacy_name: str) -> str:
        """Explain a specific fallacy type in detail."""
        if fallacy_name not in self.fallacies:
            return None
            
        prompt = f"""Explain the logical fallacy '{fallacy_name}' in detail. Include:
        1. Definition
        2. Why it's problematic
        3. Common examples
        4. How to avoid it
        Keep the explanation clear and concise."""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert at explaining logical fallacies."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=300
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error in explain_fallacy: {str(e)}")
            return "Sorry, I couldn't generate an explanation at this time."

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def generate_twitter_response(self, fallacies: List[Dict[str, Any]], original_text: str) -> Optional[str]:
        """Generate a concise Twitter response (max 280 chars) explaining the fallacies found."""
        if not fallacies:
            return None
            
        # Get the top 2 most confident fallacies
        sorted_fallacies = sorted(fallacies, key=lambda x: x['confidence'], reverse=True)[:2]
        
        fallacy_descriptions = "\n".join([
            f"- {fallacy['type'].replace('_', ' ').title()}"
            for fallacy in sorted_fallacies
        ])
        
        prompt = f"""Write a witty, educational tweet response (max 250 chars) about these logical fallacies:

Tweet analyzed: "{original_text}"

Fallacies found:
{fallacy_descriptions}

Requirements:
1. Must be ≤ 250 characters (STRICT LIMIT)
2. Use a friendly, referee-like tone
3. Include a brief explanation
4. Add a constructive suggestion
5. Use emojis sparingly
6. End with -🎯 @RhetoricalRef

Example:
"🎯 Penalty flag! That's a bandwagon play + hasty generalization. One case doesn't make a pattern. Try citing specific studies instead! -🎯 @RhetoricalRef"

Your tweet response:"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a witty bot that explains logical fallacies in tweets."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=100  # Keep it concise for Twitter
            )
            
            result = response.choices[0].message.content.strip()
            
            # Ensure we don't exceed Twitter's character limit
            if len(result) > 280:
                # Try to cut at a sentence boundary
                cutoff = result[:250].rfind('.')
                if cutoff == -1:
                    cutoff = 250
                result = result[:cutoff].rstrip() + " -🎯 @RhetoricalRef"
                
            # Remove any hashtags that might have been generated
            result = ' '.join([word for word in result.split() if not word.startswith('#')])
            
            return result
                
        except Exception as e:
            logger.error(f"Error generating Twitter response: {str(e)}")
            return None
