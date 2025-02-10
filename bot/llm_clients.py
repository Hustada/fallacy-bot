from typing import Dict, List, Optional, Any
import os
import json
import logging
import re
from pathlib import Path
from openai import OpenAI
from anthropic import Anthropic
import google.generativeai as genai
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_json_response(text: str) -> str:
    """Clean up LLM response to ensure valid JSON array format."""
    # Remove any leading/trailing whitespace
    text = text.strip()
    
    # Remove any newlines and normalize whitespace within the JSON
    text = re.sub(r'\s+', ' ', text)
    
    # If the response is wrapped in ```, remove it
    text = re.sub(r'^```json\s*|^```\s*|\s*```$', '', text)
    
    # Ensure we have array brackets
    if not text.startswith('['):
        text = '[' + text
    if not text.endswith(']'):
        text = text + ']'
    
    return text

class LLMClient:
    """Base class for LLM clients"""
    def __init__(self):
        # Only load environment once
        if not os.getenv('ENV_LOADED'):
            bot_env_path = Path(__file__).parent / '.env'
            if bot_env_path.exists():
                logger.info(f"Loading environment from {bot_env_path}")
                load_dotenv(bot_env_path)
                os.environ['ENV_LOADED'] = 'true'
                logger.info(f"Available API keys: {[k for k in os.environ.keys() if 'KEY' in k]}")
    
    async def analyze_text(self, text: str, prompt: str) -> List[Dict[str, Any]]:
        """Analyze text using the LLM. Must be implemented by subclasses."""
        raise NotImplementedError

class OpenAIClient(LLMClient):
    def __init__(self):
        super().__init__()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")
        self.client = OpenAI(api_key=api_key)
    
    async def analyze_text(self, text: str, prompt: str) -> List[Dict[str, Any]]:
        try:
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are a logical fallacy detection expert who can distinguish between actual fallacies and rhetorical devices. You MUST respond with a valid JSON array."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1
                )
                result = response.choices[0].message.content.strip()
                logger.info(f"Raw OpenAI response: {repr(result)}")
                
                # Ensure we have valid JSON array brackets
                if not (result.startswith('[') and result.endswith(']')):
                    result = '[]'
                    
                try:
                    fallacies = json.loads(result)
                    logger.info(f"OpenAI response parsed: {fallacies}")
                    return fallacies
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON from OpenAI: {repr(result)}")
                    logger.error(f"JSON error: {str(e)}")
                    return []
            except Exception as e:
                logger.error(f"OpenAI API error: {str(e)}")
                return []
        except Exception as e:
            logger.error(f"OpenAI analysis error: {e}")
            return []

class ClaudeClient(LLMClient):
    def __init__(self):
        super().__init__()
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.error(f"Available environment variables: {[k for k in os.environ.keys() if 'KEY' in k]}")
            raise ValueError("ANTHROPIC_API_KEY not found in environment")
        self.client = Anthropic(api_key=api_key)
    
    async def analyze_text(self, text: str, prompt: str) -> List[Dict[str, Any]]:
        try:
            try:
                response = self.client.messages.create(
                    model="claude-3-opus-20240229",
                    max_tokens=1000,
                    system="You are a logical fallacy detection expert who can distinguish between actual fallacies and rhetorical devices. You MUST respond with a valid JSON array.",
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }]
                )
                result = response.content[0].text
                logger.info(f"Raw Claude response: {repr(result)}")
                
                # Ensure we have valid JSON array brackets
                if not (result.startswith('[') and result.endswith(']')):
                    result = '[]'
                    
                try:
                    fallacies = json.loads(result)
                    logger.info(f"Claude response parsed: {fallacies}")
                    return fallacies
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON from Claude: {repr(result)}")
                    logger.error(f"JSON error: {str(e)}")
                    return []
            except Exception as e:
                logger.error(f"Claude API error: {str(e)}")
                return []
        except Exception as e:
            logger.error(f"Claude analysis error: {e}")
            return []

class GeminiClient(LLMClient):
    def __init__(self):
        super().__init__()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
    
    async def analyze_text(self, text: str, prompt: str) -> List[Dict[str, Any]]:
        try:
            system_prompt = """You are a logical fallacy and rhetoric expert. Your task is to analyze text for logical fallacies and inappropriate hyperbole.

For each issue found, you MUST return a valid JSON array containing objects with these fields:
- type: Either 'logical_fallacy' or 'inappropriate_hyperbole'
- subtype: The specific type of fallacy (e.g., 'ad_hominem', 'straw_man', etc.)
- explanation: A brief explanation of why this is a fallacy
- confidence: A float between 0.0 and 1.0 indicating your confidence

Example response for a fallacy:
[{
  "type": "logical_fallacy",
  "subtype": "ad_hominem",
  "explanation": "Attacks the person instead of their argument",
  "confidence": 0.95
}]

If no fallacies are found, return an empty array: []
"""
            full_prompt = f"{system_prompt}\n\n{prompt}"
            try:
                response = self.model.generate_content(full_prompt)
                result = response.text
                logger.info(f"Raw Gemini response: {repr(result)}")
                
                # Ensure we have valid JSON array brackets
                if not (result.startswith('[') and result.endswith(']')):
                    result = '[]'
                    
                try:
                    fallacies = json.loads(result)
                    logger.info(f"Gemini response parsed: {fallacies}")
                    return fallacies
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON from Gemini: {repr(result)}")
                    logger.error(f"JSON error: {str(e)}")
                    return []
            except Exception as e:
                logger.error(f"Gemini API error: {str(e)}")
                return []
        except Exception as e:
            logger.error(f"Gemini analysis error: {e}")
            return []
