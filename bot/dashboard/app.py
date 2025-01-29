import streamlit as st
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

# Load environment variables
env_path = Path(project_root) / 'bot' / '.env'
load_dotenv(env_path)

from bot.fallacy_detector import FallacyDetector
from bot.database.models import log_activity, get_recent_activity, save_sandbox_tweet, get_sandbox_tweets

# Initialize OpenAI client
client = OpenAI()

# Initialize fallacy detector
fallacy_detector = FallacyDetector()

def main():
    st.title("Twitter Fallacy Bot Dashboard")
    
    # Sidebar navigation
    page = st.sidebar.selectbox("Navigation", ["Sandbox", "Activity Log", "Analytics"])
    
    if page == "Activity Log":
        show_activity_log()
    elif page == "Sandbox":
        show_sandbox()
    else:
        show_analytics()

def show_activity_log():
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

def show_sandbox():
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
    
    # Debug information
    st.write("### Debug Information")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("❌ OpenAI API key not found!")
    else:
        st.success(f"✅ OpenAI API key found (starts with: {api_key[:10]}...)")
    
    col1, col2 = st.columns([1, 5])
    analyze_button = col1.button("🔍 Analyze", use_container_width=True)
    
    if analyze_button and test_tweet:
        st.write("### Analysis Process")
        st.write("1️⃣ Starting analysis...")
        st.write(f"Input text: {test_tweet}")
        
        try:
            st.write("2️⃣ Testing OpenAI API connection...")
            
            # Try a simple API test first
            try:
                test_response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": "Say hello"}],
                    max_tokens=5
                )
                st.success("✅ OpenAI API test successful!")
            except Exception as e:
                st.error(f"❌ OpenAI API test failed: {str(e)}")
                st.warning("Attempting fallacy detection anyway...")
            
            # Now try fallacy detection
            fallacies = fallacy_detector.detect_fallacies(test_tweet)
            st.write("3️⃣ OpenAI API call complete")
            st.write("Response received:", fallacies)
            
            # Display results
            if fallacies:
                st.subheader("🎯 Detected Fallacies")
                for fallacy in fallacies:
                    with st.expander(f"**{fallacy['type'].replace('_', ' ').title()}** (Confidence: {fallacy['confidence']:.2f})", expanded=True):
                        st.markdown(f"**Explanation:** {fallacy['explanation']}")
                
                # Generate response
                try:
                    st.write("4️⃣ Generating response...")
                    response = fallacy_detector.generate_response(fallacies, test_tweet)
                    if response:
                        st.subheader("🤖 Bot's Response")
                        st.info(response)
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

def show_analytics():
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
    main()
