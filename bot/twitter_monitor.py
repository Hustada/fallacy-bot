import asyncio
import logging
import os
import random
from datetime import datetime, timedelta
from typing import List, Optional, Dict

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv

from .fallacy_detector import FallacyDetector

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TwitterMonitor:
    def __init__(self):
        """Initialize the Twitter monitor."""
        self.driver = None
        self.is_logged_in = False
        self.fallacy_detector = FallacyDetector()
        
        # Load environment variables
        load_dotenv()
        self.twitter_username = os.getenv("TWITTER_USERNAME")
        self.twitter_password = os.getenv("TWITTER_PASSWORD")
        
        if not all([self.twitter_username, self.twitter_password]):
            raise ValueError("Twitter credentials not found in environment variables")
        
        # Monitoring settings
        self.monitored_accounts: List[str] = []
        self.last_check: Dict[str, datetime] = {}
        self.cooldown_period = timedelta(hours=1)
        self.confidence_threshold = 0.8
    
    def start(self):
        """Start the browser and log in to Twitter."""
        try:
            # Set up Chrome options
            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument('--headless')  # Run in headless mode
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            
            # Initialize the driver
            self.driver = webdriver.Chrome(
                ChromeDriverManager().install(),
                options=chrome_options
            )
            
            # Log in to Twitter
            self.login()
            logger.info("Twitter monitor started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Twitter monitor: {str(e)}")
            self.cleanup()
            raise
    
    def login(self):
        """Log in to Twitter using credentials."""
        try:
            # Navigate to Twitter login
            self.driver.get("https://twitter.com/login")
            
            # Wait for and enter username
            username_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[autocomplete="username"]'))
            )
            username_input.send_keys(self.twitter_username)
            
            # Click next
            next_button = self.driver.find_element(By.XPATH, '//span[text()="Next"]')
            next_button.click()
            
            # Wait for and enter password
            password_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="password"]'))
            )
            password_input.send_keys(self.twitter_password)
            
            # Click login
            login_button = self.driver.find_element(By.XPATH, '//span[text()="Log in"]')
            login_button.click()
            
            # Wait for login to complete
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'a[aria-label="Profile"]'))
            )
            
            self.is_logged_in = True
            logger.info("Successfully logged in to Twitter")
            
        except Exception as e:
            logger.error(f"Failed to log in to Twitter: {str(e)}")
            raise
    
    def check_notifications(self):
        """Check Twitter notifications for mentions."""
        if not self.is_logged_in:
            self.start()
        
        try:
            # Navigate to notifications
            self.driver.get("https://twitter.com/notifications/mentions")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'article[data-testid="tweet"]'))
            )
            
            # Get recent mentions
            mentions = self.driver.find_elements(By.CSS_SELECTOR, 'article[data-testid="tweet"]')
            
            for mention in mentions[:5]:  # Process last 5 mentions
                try:
                    # Get tweet text
                    tweet_text = mention.find_element(By.CSS_SELECTOR, 'div[data-testid="tweetText"]')
                    if not tweet_text:
                        continue
                    
                    text_content = tweet_text.text
                    
                    # Check if we should analyze this tweet
                    if self._should_analyze_tweet(mention):
                        # Analyze for fallacies
                        fallacies = self.fallacy_detector.detect_fallacies(text_content)
                        
                        if fallacies and max(f['confidence'] for f in fallacies) >= self.confidence_threshold:
                            # Generate and post response
                            response = self.fallacy_detector.generate_twitter_response(fallacies, text_content)
                            if response:
                                self._post_response(mention, response)
                
                except Exception as e:
                    logger.error(f"Error processing mention: {str(e)}")
                    continue
            
        except Exception as e:
            logger.error(f"Error checking notifications: {str(e)}")
    
    def monitor_account(self, username: str):
        """Monitor a specific Twitter account for new tweets."""
        if not self.is_logged_in:
            self.start()
        
        try:
            # Navigate to user's profile
            self.driver.get(f"https://twitter.com/{username}")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'article[data-testid="tweet"]'))
            )
            
            # Get recent tweets
            tweets = self.driver.find_elements(By.CSS_SELECTOR, 'article[data-testid="tweet"]')
            
            for tweet in tweets[:3]:  # Process last 3 tweets
                try:
                    # Get tweet text
                    tweet_text = tweet.find_element(By.CSS_SELECTOR, 'div[data-testid="tweetText"]')
                    if not tweet_text:
                        continue
                    
                    text_content = tweet_text.text
                    
                    # Check if we should analyze this tweet
                    if self._should_analyze_tweet(tweet):
                        # Analyze for fallacies
                        fallacies = self.fallacy_detector.detect_fallacies(text_content)
                        
                        if fallacies and max(f['confidence'] for f in fallacies) >= self.confidence_threshold:
                            # Generate and post response
                            response = self.fallacy_detector.generate_twitter_response(fallacies, text_content)
                            if response:
                                self._post_response(tweet, response)
                
                except Exception as e:
                    logger.error(f"Error processing tweet: {str(e)}")
                    continue
            
        except Exception as e:
            logger.error(f"Error monitoring account {username}: {str(e)}")
    
    def _should_analyze_tweet(self, tweet_element) -> bool:
        """Determine if we should analyze a tweet based on various criteria."""
        try:
            # Get tweet timestamp
            timestamp = tweet_element.find_element(By.CSS_SELECTOR, 'time')
            if not timestamp:
                return False
            
            # Get tweet URL to use as unique identifier
            tweet_link = tweet_element.find_element(By.CSS_SELECTOR, 'a[href*="/status/"]')
            if not tweet_link:
                return False
            
            tweet_url = tweet_link.get_attribute('href')
            
            # Check if we've recently responded to this tweet
            if tweet_url in self.last_check:
                if datetime.now() - self.last_check[tweet_url] < self.cooldown_period:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking tweet criteria: {str(e)}")
            return False
    
    def _post_response(self, tweet_element, response: str):
        """Post a response to a tweet."""
        try:
            # Click reply button
            reply_button = tweet_element.find_element(By.CSS_SELECTOR, 'div[aria-label="Reply"]')
            if not reply_button:
                return
            
            reply_button.click()
            
            # Wait for reply box and enter response
            reply_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="tweetTextarea_0"]'))
            )
            reply_box.send_keys(response)
            
            # Add random delay (2-5 seconds) to seem more human
            import time
            time.sleep(random.uniform(2, 5))
            
            # Click reply
            reply_button = self.driver.find_element(By.CSS_SELECTOR, 'div[data-testid="tweetButton"]')
            reply_button.click()
            
            # Wait for reply to be posted
            WebDriverWait(self.driver, 10).until(
                EC.staleness_of(reply_box)
            )
            
            # Update last check time
            tweet_link = tweet_element.find_element(By.CSS_SELECTOR, 'a[href*="/status/"]')
            if tweet_link:
                tweet_url = tweet_link.get_attribute('href')
                self.last_check[tweet_url] = datetime.now()
            
            logger.info("Successfully posted response")
            
        except Exception as e:
            logger.error(f"Error posting response: {str(e)}")
    
    def cleanup(self):
        """Clean up resources."""
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.is_logged_in = False
