import streamlit as st
import asyncio

# Must be the first Streamlit command
st.set_page_config(
    page_title="RhetoricalRef Dashboard",
    page_icon="🎯",
    layout="wide"
)

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import json
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import logging
import io
from openai import OpenAI

# Configure logging to capture output
log_stream = io.StringIO()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=log_stream
)

# Add the project root to Python path
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# Load environment variables - handle both local and Streamlit Cloud
env_path = Path(project_root) / 'bot' / '.env'
if env_path.exists():
    load_dotenv(env_path)

# Get OpenAI API key from environment or Streamlit secrets
def get_openai_key():
    # Try Streamlit secrets first (for cloud deployment)
    try:
        st.write("Trying Streamlit secrets...")
        key = st.secrets['openai']['OPENAI_API_KEY']
        st.write("Found key in Streamlit secrets")
        return key
    except Exception as e:
        st.write(f"No Streamlit secrets found: {str(e)}")
        # Fall back to environment variable (for local development)
        st.write("Trying environment variables...")
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            st.error('❌ OpenAI API key not found. Please set OPENAI_API_KEY in environment or Streamlit secrets.')
            st.write("Available environment variables:", [k for k in os.environ.keys() if 'KEY' in k])
            return None
        st.write("Found key in environment variables")
        return api_key

# Initialize OpenAI client with the key
client = OpenAI(api_key=get_openai_key())

# Import after environment setup
from bot.dashboard_detector import DashboardFallacyDetector
from bot.database.models import log_activity, get_recent_activity, save_sandbox_tweet, get_sandbox_tweets

# Initialize fallacy detector
fallacy_detector = DashboardFallacyDetector()

async def main():
    st.title("RhetoricalRef Dashboard")
    
    # Sidebar navigation
    page = st.sidebar.selectbox("Navigation", ["Sandbox", "Activity Log", "Analytics"])
    
    if page == "Activity Log":
        await show_activity_log()
    elif page == "Sandbox":
        await show_sandbox()
    else:
        await show_analytics()

async def show_activity_log():
    st.header("Bot Activity Log")
    
    # Date filter
    date_range = st.date_input(
        "Select Date Range",
        value=(datetime.now() - timedelta(days=7), datetime.now())
    )
    
    # Get activity data
    activities = get_recent_activity()
    
    # Convert to DataFrame
    if activities:
        df = pd.DataFrame(activities)
        st.dataframe(df)
    else:
        st.info("No activity logged yet.")

async def show_sandbox():
    st.header("Test Fallacy Detection")
    st.markdown("""
    ### Try out the fallacy detection!
    
    Enter a tweet below to test the bot's fallacy detection capabilities. Here's an example:
    > "Everyone knows that video games cause violence. My neighbor's kid played violent games and got into a fight at school, so that proves it!"
    """)
    
    # Text input for testing with placeholder
    test_tweet = st.text_area(
        "Enter a tweet to analyze:",
        placeholder="Type or paste a tweet here...",
        help="Enter any text that you want to analyze for logical fallacies."
    )
    
    col1, col2 = st.columns([1, 5])
    analyze_button = col1.button("🔍 Analyze", use_container_width=True)
    
    if analyze_button and test_tweet:
        st.write("### Analysis Process")
        st.write("1️⃣ Analyzing text...")
        st.write(f"Input text: {test_tweet}")
        
        try:
            # Perform fallacy detection
            fallacies = await fallacy_detector.detect_fallacies(test_tweet)
            st.write("2️⃣ Analysis complete")
            st.write("Detected fallacies:", fallacies)
            
            # Display results
            if fallacies:
                st.subheader("🎯 Detected Fallacies")
                for fallacy in fallacies:
                    with st.expander(f"**{fallacy['type'].replace('_', ' ').title()}** (Confidence: {fallacy['confidence']:.2f})", expanded=True):
                        st.markdown(f"**Explanation:** {fallacy['explanation']}")
                
                # Generate response
                try:
                    st.write("4️⃣ Generating responses...")
                    response = fallacy_detector.generate_response(fallacies, test_tweet)
                    if response:
                        st.subheader("🤖 Bot's Response")
                        st.info(response)
                        
                    # Add Twitter response
                    twitter_response = fallacy_detector.generate_twitter_response(fallacies, test_tweet)
                    if twitter_response:
                        st.subheader("🐦 Twitter Response (@RhetoricalRef)")
                        st.success(twitter_response)
                        # Show character count
                        char_count = len(twitter_response)
                        st.caption(f"Character count: {char_count}/280")
                        if char_count > 280:
                            st.warning("⚠️ Response exceeds Twitter's 280 character limit!")
                except Exception as e:
                    st.error(f"Error generating response: {str(e)}")
                    response = None
            else:
                st.warning("⚠️ No logical fallacies were detected. This seems incorrect - there might be an issue with the API call.")
            
            # Calculate confidence
            confidence = max([f['confidence'] for f in fallacies]) if fallacies else 0.0
            
            # Log activity
            try:
                log_activity(
                    tweet_id="sandbox",
                    tweet_text=test_tweet,
                    fallacies=fallacies,
                    response=response if 'response' in locals() else None,
                    confidence=confidence,
                    is_sandbox=1
                )
            except Exception as e:
                st.error(f"Error logging activity: {str(e)}")
                
        except Exception as e:
            st.error(f"❌ Error during analysis: {str(e)}")
            st.write("Full error:", str(e.__class__.__name__), str(e))

async def show_analytics():
    st.header("Analytics")
    
    # Get all activity data
    activities = get_recent_activity()
    
    if activities:
        df = pd.DataFrame(activities)
        
        # Basic statistics
        st.subheader("Summary Statistics")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Tweets Analyzed", len(df))
        
        with col2:
            tweets_with_fallacies = len(df[df['fallacies'].apply(lambda x: len(json.loads(x)) > 0)])
            st.metric("Tweets with Fallacies", tweets_with_fallacies)
        
        with col3:
            avg_confidence = df['confidence'].mean()
            st.metric("Avg. Confidence", f"{avg_confidence:.2f}")
        
        # Fallacy distribution
        st.subheader("Fallacy Distribution")
        fallacy_types = []
        for fallacies in df['fallacies']:
            fallacies_list = json.loads(fallacies)
            fallacy_types.extend([f['type'] for f in fallacies_list])
        
        if fallacy_types:
            fallacy_counts = pd.Series(fallacy_types).value_counts()
            st.bar_chart(fallacy_counts)
    else:
        st.info("No data available for analytics yet.")

if __name__ == "__main__":
    asyncio.run(main())
