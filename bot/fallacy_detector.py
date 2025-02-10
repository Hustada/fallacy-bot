from typing import Dict, List, Optional, Any
import json
import os
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
from pathlib import Path
from dotenv import load_dotenv
from collections import Counter
from .llm_clients import OpenAIClient, ClaudeClient, GeminiClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FallacyDetector:
    def __init__(self):
        # Initialize LLM clients
        self.clients = {
            'openai': OpenAIClient(),
            'claude': ClaudeClient(),
            'gemini': GeminiClient()
        }
        
        logger.info("Initializing FallacyDetector with multiple LLM clients...")
        
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
        
        self.hyperbole_types = {
            "historical_comparison": "Inappropriate comparison to historical events or atrocities",
            "statistical_exaggeration": "Grossly exaggerating numbers or statistics",
            "catastrophizing": "Presenting minor issues as catastrophic events",
            "diminishing_serious": "Using hyperbole that diminishes serious issues",
            "absolute_language": "Using absolute terms inappropriately (always, never, everyone, no one)"
        }
        
        logger.info("FallacyDetector initialized successfully")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def detect_fallacies(self, text: str) -> List[Dict[str, Any]]:
        """Detect logical fallacies and inappropriate hyperbole in text."""
        example_response = '[{"type": "logical_fallacy", "subtype": "ad_hominem", "explanation": "Attacks the person instead of their argument", "confidence": 0.95}]'
        
        prompt = f"""Analyze this tweet for logical fallacies and inappropriate hyperbole, distinguishing between actual issues and rhetorical devices.

Tweet: \"{text}\"

Instructions:
1. First, determine if this tweet is:
   - Serious/literal
   - Sarcastic
   - Using purposeful exaggeration for effect
   - Making a joke or being humorous

2. Only identify issues if the tweet is being serious/literal. Ignore rhetorical devices used for humor or emphasis.

3. For each ACTUAL issue found, provide:
   - Type (logical_fallacy or inappropriate_hyperbole)
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
            all_results = []
            
            # Get analysis from each LLM
            for name, client in self.clients.items():
                try:
                    results = await client.analyze_text(text, prompt)
                    for result in results:
                        result['source'] = name
                    all_results.extend(results)
                except Exception as e:
                    logger.error(f"Error with {name}: {e}")
            
            # Find consensus (issues reported by multiple LLMs)
            consensus_results = []
            issue_counter = Counter()
            
            for result in all_results:
                key = (result['type'], result['subtype'])
                issue_counter[key] += 1
            
            # Include issues found by at least 2 LLMs
            for (issue_type, subtype), count in issue_counter.items():
                if count >= 2:
                    matching_results = [r for r in all_results 
                                      if r['type'] == issue_type and 
                                      r['subtype'] == subtype]
                    best_result = max(matching_results, key=lambda x: x['confidence'])
                    consensus_results.append(best_result)
            
            # Log the analysis for debugging
            logger.info(f"Analysis for tweet: {text[:100]}...")
            logger.info(f"All results: {all_results}")
            logger.info(f"Consensus results: {consensus_results}")
            
            return consensus_results
            
        except Exception as e:
            logger.error(f"Error detecting issues: {str(e)}")
            return []
    
    async def generate_twitter_response(self, issues: List[Dict[str, Any]], original_text: str) -> Optional[str]:
        """Generate a concise Twitter response (max 280 chars) explaining the issues found using multiple LLMs."""
        if not issues:
            return None
            
        # Get the top 2 most confident issues
        sorted_issues = sorted(issues, key=lambda x: x['confidence'], reverse=True)[:2]
        
        # Create detailed issue descriptions
        issue_details = []
        for issue in sorted_issues:
            issue_type = issue['type'].replace('_', ' ').title()
            subtype = issue['subtype'].replace('_', ' ').title()
            explanation = issue['explanation']
            issue_details.append(f"- {issue_type}: {subtype}\n  Explanation: {explanation}")
        
        issues_desc = "\n".join(issue_details)
        
        prompt = f"""Generate a witty but educational tweet response about these rhetorical issues.

Original tweet: "{original_text}"

Issues detected:
{issues_desc}

Response requirements:
1. MUST be under 250 characters (STRICT LIMIT)
2. Use a friendly, referee-like tone (like a debate moderator)
3. Briefly explain why these are issues
4. Add a constructive suggestion for improvement
5. Use at most 2 emojis
6. End with -🎯 @RhetoricalRef

Example good responses:
"🎯 Heads up! Ad hominem alert - attacking someone's character doesn't address their argument. Let's focus on the evidence instead! -🎯 @RhetoricalRef"

"Time out! That's a hasty generalization. One example doesn't prove a pattern. Got any broader evidence to share? -🎯 @RhetoricalRef"

Your response (remember: 250 char max!):"""
        
        try:
            all_responses = []
            
            # Get responses from all LLMs
            for name, client in self.clients.items():
                try:
                    results = await client.analyze_text(original_text, prompt)
                    if results and len(results) > 0:
                        response = results[0].get('explanation', '')
                        if response and len(response) <= 280:
                            all_responses.append(response)
                except Exception as e:
                    logger.error(f"Error getting response from {name}: {e}")
            
            if not all_responses:
                # Fallback response if all LLMs fail
                fallback = (
                    f"🎯 Found {len(sorted_issues)} rhetorical issues! "
                    f"Let's aim for clearer arguments backed by evidence. "
                    f"-🎯 @RhetoricalRef"
                )
                return fallback
            
            # Choose the response that best fits our criteria
            best_response = min(all_responses, key=len)  # Prefer shorter responses
            
            # Ensure it ends with our signature
            if not best_response.endswith("-🎯 @RhetoricalRef"):
                best_response = best_response.rstrip() + " -🎯 @RhetoricalRef"
            
            # Final length check
            if len(best_response) > 280:
                cutoff = best_response[:250].rfind('.')
                if cutoff == -1:
                    cutoff = 250
                best_response = best_response[:cutoff].rstrip() + " -🎯 @RhetoricalRef"
            
            return best_response
                
        except Exception as e:
            logger.error(f"Error generating Twitter response: {str(e)}")
            return None
