from openai import OpenAI
from typing import Dict, List, Optional, Any
import json
import os
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FallacyDetector:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        logger.info(f"Initializing FallacyDetector with API key: {api_key[:10]}...")
            
        self.client = OpenAI()
        
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
            "anecdotal": "Using a personal experience or isolated example instead of sound reasoning or evidence"
        }
        
        logger.info("FallacyDetector initialized successfully")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def detect_fallacies(self, text: str) -> List[Dict[str, Any]]:
        """Detect logical fallacies in the given text."""
        logger.info(f"Analyzing text for fallacies: {text}")
        
        prompt = f"""You are an expert at detecting logical fallacies. Analyze this text for logical fallacies:

"{text}"

Example analysis:
Text: "Everyone knows that video games cause violence. My neighbor's kid played violent games and got into a fight at school, so that proves it!"
[
    {{
        "type": "bandwagon",
        "explanation": "Uses 'Everyone knows' to appeal to popular belief rather than evidence",
        "confidence": 0.95
    }},
    {{
        "type": "anecdotal",
        "explanation": "Uses a single case of one child to draw a general conclusion about video games and violence",
        "confidence": 0.9
    }},
    {{
        "type": "hasty_generalization",
        "explanation": "Concludes that video games cause violence based on a single incident",
        "confidence": 0.85
    }}
]

Analyze the text above and list ALL logical fallacies you find. Use these types: {', '.join(self.fallacies.keys())}
Format your response as a JSON array with "type", "explanation", and "confidence" for each fallacy.
Return [] ONLY if you are absolutely certain there are no fallacies.

Your analysis in JSON format:"""

        logger.info("Sending request to OpenAI...")
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert at detecting logical fallacies."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            logger.info(f"Chat API Response received")
            result = response.choices[0].message.content.strip()
            
            logger.info(f"Raw response content: {result}")
            
            try:
                fallacies = json.loads(result)
                if not isinstance(fallacies, list):
                    logger.error(f"Error: Response is not a list: {result}")
                    return []
                    
                logger.info(f"Detected fallacies: {json.dumps(fallacies, indent=2)}")
                return fallacies
                
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON: {e}")
                logger.error(f"Raw response: {result}")
                return []
                
        except Exception as e:
            logger.error(f"Error in OpenAI request: {str(e)}")
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
        
        prompt = f"""Write a witty, educational tweet response (max 280 chars) about these logical fallacies:

Tweet analyzed: "{original_text}"

Fallacies found:
{fallacy_descriptions}

Requirements:
1. Must be ≤ 280 characters
2. Use a friendly, referee-like tone
3. Include a brief explanation
4. Add a constructive suggestion
5. Use emojis sparingly
6. Sign with -🎯 @RhetoricalRef #LogicCheck

Example:
"🎯 Penalty flag! That's a bandwagon play ('everyone knows') + hasty generalization. One case doesn't make a pattern. Try citing specific studies instead! -🎯 @RhetoricalRef #LogicCheck"

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
            return response.choices[0].message.content.strip()
                
        except Exception as e:
            logger.error(f"Error generating Twitter response: {str(e)}")
            return None
