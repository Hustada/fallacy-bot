from typing import Dict, List, Optional, Any
import os
import json
import logging
import re
from pathlib import Path
from openai import OpenAI
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
        import streamlit as st
        
        # Try Streamlit secrets first, then environment variable
        try:
            api_key = st.secrets['openai']['OPENAI_API_KEY']
        except Exception:
            api_key = os.getenv("OPENAI_API_KEY")
            
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in Streamlit secrets or environment")
            
        self.client = OpenAI(api_key=api_key)
    
    async def analyze_text(self, text: str, prompt: str) -> List[Dict[str, Any]]:
        try:
            import streamlit as st
            from openai import AsyncOpenAI
            
            async_client = AsyncOpenAI(api_key=self.client.api_key)
            response = await async_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a logical fallacy detection expert who can distinguish between actual fallacies and rhetorical devices. You MUST respond with a valid JSON array. If no issues are found, return an empty array: []."},
                    {"role": "user", "content": text},
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
            logger.error(f"OpenAI analysis error: {e}")
            return []

