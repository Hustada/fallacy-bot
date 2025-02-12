from typing import Dict, List, Optional, Any
import json
import os
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
from pathlib import Path
from dotenv import load_dotenv
from collections import Counter
from .llm_clients import OpenAIClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DashboardFallacyDetector:
    def __init__(self):
        # Initialize only OpenAI client for dashboard
        self.client = OpenAIClient()
        logger.info("Initializing DashboardFallacyDetector with OpenAI client...")
        
        # Define issue types for reference
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
        
        logger.info("DashboardFallacyDetector initialized successfully")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def detect_fallacies(self, text: str) -> List[Dict[str, Any]]:
        """Detect logical fallacies in text using OpenAI."""
        import streamlit as st
        
        example_response = '[{"type": "logical_fallacy", "subtype": "ad_hominem", "explanation": "Attacks the person instead of their argument", "confidence": 0.95}]'
        
        prompt = f"""Analyze this tweet for logical fallacies, distinguishing between actual issues and rhetorical devices.

Tweet: \"{text}\"

Instructions:
1. First, determine if this tweet is:
   - Serious/literal
   - Sarcastic
   - Using purposeful exaggeration for effect
   - Making a joke or being humorous

2. Only identify issues if the tweet is being serious/literal. Ignore rhetorical devices used for humor or emphasis.

3. For each ACTUAL issue found, provide:
   - Type (logical_fallacy)
   - Subtype (specific type)
   - Brief explanation
   - Confidence level (0.0-1.0)

IMPORTANT: Your response must be a valid JSON array. Only include issues with confidence > 0.8
If no actual issues are found, or if the tweet is clearly sarcastic/humorous, return an empty array: []

Example outputs:
[]  # for sarcastic/humorous tweets
{example_response}  # for actual fallacies

Your response (must be valid JSON array):"""

        try:
            st.write("Attempting to analyze with OpenAI...")
            results = await self.client.analyze_text(text, prompt)
            st.write("Analysis successful!")
            return results
        except Exception as e:
            st.error(f"Error analyzing text: {str(e)}")
            st.write("Full error:", str(e.__class__.__name__), str(e))
            return []
    
    def generate_response(self, fallacies: List[Dict[str, Any]], original_text: str) -> str:
        """Generate a response explaining the fallacies found."""
        if not fallacies:
            return None
        
        response = "Here's what I found:\n\n"
        for fallacy in fallacies:
            response += f"• {fallacy['subtype'].replace('_', ' ').title()}: {fallacy['explanation']}\n"
        return response
    
    def generate_twitter_response(self, fallacies: List[Dict[str, Any]], original_text: str) -> str:
        """Generate a concise Twitter response (max 280 chars) explaining the issues found."""
        if not fallacies:
            return None
        
        # Get the most confident fallacy
        main_fallacy = max(fallacies, key=lambda x: x['confidence'])
        
        # Create a concise response
        fallacy_name = main_fallacy['subtype'].replace('_', ' ').title()
        explanation = main_fallacy['explanation']
        
        # Format the response to fit Twitter's limit
        response = f"🎯 Found a {fallacy_name}! {explanation}"
        if len(response) > 280:
            response = response[:277] + "..."
        
        return response
