import asyncio
import logging
import random
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from playwright.async_api import async_playwright, Page, TimeoutError, ElementHandle
from .fallacy_detector import FallacyDetector
from dotenv import load_dotenv
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TwitterMonitorPlaywright:
    def __init__(self):
        load_dotenv()
        self.last_check_times = {}
        self.fallacy_detector = FallacyDetector()
        self.browser = None
        self.context = None
        self.page = None

    async def setup(self):
        """Initialize the browser and context."""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']  # Hide automation
        )
        self.context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        self.page = await self.context.new_page()
        
        # Login to X
        await self._login()

    async def _wait_for_element(self, selector: str, timeout: int = 10000, state: str = 'visible') -> Optional[ElementHandle]:
        """Wait for an element with retry logic and multiple selector attempts."""
        try:
            element = await self.page.wait_for_selector(selector, timeout=timeout, state=state)
            if element:
                return element
        except TimeoutError:
            logger.warning(f"Timeout waiting for {selector}, trying alternative methods...")
            
        # Try alternative selectors if the main one fails
        alt_selectors = {
            'input[autocomplete="username"]': ['input[name="text"]', 'input[type="text"]'],
            'input[type="password"]': ['input[name="password"]'],
            'div[role="button"]:has-text("Next")': ['div[data-testid="Button"]', 'div[role="button"]'],
            'div[role="button"]:has-text("Log in")': ['div[data-testid="LoginButton"]']
        }
        
        if selector in alt_selectors:
            for alt_selector in alt_selectors[selector]:
                try:
                    logger.info(f"Trying alternative selector: {alt_selector}")
                    element = await self.page.wait_for_selector(alt_selector, timeout=5000, state=state)
                    if element:
                        return element
                except TimeoutError:
                    continue
        
        return None

    async def _login(self):
        """Login to X (formerly Twitter) using environment credentials with enhanced error handling."""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Start at login page
                await self.page.goto('https://x.com/login', wait_until='networkidle')
                await asyncio.sleep(2)  # Give extra time for JS to load
                
                # Wait for and fill username with retry logic
                username_input = await self._wait_for_element('input[autocomplete="username"]', timeout=15000)
                if not username_input:
                    raise Exception("Could not find username input field")
                
                await username_input.fill(os.getenv('TWITTER_USERNAME'))
                await asyncio.sleep(1)
                
                # Try multiple methods to click next
                next_button = await self._wait_for_element('div[role="button"]:has-text("Next")', timeout=10000)
                if next_button:
                    await next_button.click()
                else:
                    # Try pressing Enter if button not found
                    await username_input.press('Enter')
                
                await asyncio.sleep(2)
                
                # Wait for and fill password
                password_input = await self._wait_for_element('input[type="password"]', timeout=15000)
                if not password_input:
                    raise Exception("Could not find password input field")
                
                await password_input.fill(os.getenv('TWITTER_PASSWORD'))
                await asyncio.sleep(1)
                
                # Try multiple methods to click login
                login_button = await self._wait_for_element('div[role="button"]:has-text("Log in")', timeout=10000)
                if login_button:
                    await login_button.click()
                else:
                    # Try pressing Enter if button not found
                    await password_input.press('Enter')
                
                # Wait for successful login
                try:
                    await self.page.wait_for_url('https://x.com/home', timeout=30000)
                    timeline = await self._wait_for_element('div[data-testid="primaryColumn"]', timeout=15000)
                    if timeline:
                        logger.info("Successfully logged into X")
                        return
                except TimeoutError:
                    logger.warning("Timeline not found after login, may need to handle additional screens")
                
                # Check for additional verification screens
                if await self._handle_verification_screens():
                    logger.info("Successfully handled verification screens")
                    return
                
                raise Exception("Login flow did not complete successfully")
                
            except Exception as e:
                logger.error(f"Login attempt {retry_count + 1} failed: {str(e)}")
                await self.page.screenshot(path=f"login_error_{retry_count}.png")
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(f"Retrying login... (attempt {retry_count + 1}/{max_retries})")
                    await asyncio.sleep(5)  # Wait before retrying
                else:
                    raise Exception(f"Failed to login after {max_retries} attempts: {str(e)}")

    async def _handle_verification_screens(self) -> bool:
        """Handle any additional verification screens that may appear during login."""
        try:
            # Check for common verification elements
            verification_selectors = [
                'input[name="verfication_code"]',
                'input[name="challenge_response"]',
                'div[role="button"]:has-text("Skip for now")',
                'div[role="button"]:has-text("Not now")'
            ]
            
            for selector in verification_selectors:
                element = await self._wait_for_element(selector, timeout=5000)
                if element:
                    if 'Skip' in selector or 'Not now' in selector:
                        await element.click()
                        await asyncio.sleep(2)
                    logger.info(f"Handled verification element: {selector}")
                    return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Error handling verification screens: {e}")
            return False

    async def monitor_account(self, username: str) -> bool:
        """Monitor a specific account's timeline."""
        try:
            # Navigate to user's profile with retry logic
            profile_url = f"https://x.com/{username}"
            logger.info(f"Navigating to {profile_url}")
            
            # Try navigation with retry
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Navigate and wait for initial load
                    await self.page.goto(profile_url, wait_until='domcontentloaded', timeout=15000)
                    logger.info("Initial page load complete")
                    
                    # Check if we hit a "Something went wrong" page
                    error_text = await self.page.query_selector('text="Something went wrong"')
                    if error_text:
                        logger.warning("Hit error page, refreshing...")
                        await self.page.reload()
                        await asyncio.sleep(2)
                        continue
                    
                    # Wait a bit for dynamic content to load
                    await asyncio.sleep(3)
                    
                    # Try to find any tweets
                    tweets = await self.page.query_selector_all('article[data-testid="tweet"]')
                    if tweets:
                        logger.info(f"Found {len(tweets)} tweets")
                        first_tweet = tweets[0]
                        
                        tweet_text_elem = await first_tweet.query_selector('[data-testid="tweetText"]')
                        if tweet_text_elem:
                            tweet_text = await tweet_text_elem.inner_text()
                            logger.info(f"First tweet text: {tweet_text[:100]}...")
                            
                            # Force check this tweet
                            logger.info("Checking tweet for fallacies...")
                            try:
                                fallacies = self.fallacy_detector.detect_fallacies(tweet_text)
                                logger.info(f"Fallacy detection result: {fallacies}")
                                
                                if fallacies and len(fallacies) > 0:
                                    logger.info(f"Found {len(fallacies)} fallacies: {fallacies}")
                                    
                                    # Take screenshot before clicking reply
                                    await self.page.screenshot(path=f"found_fallacy_{username}.png")
                                    
                                    # Multiple possible selectors for reply button
                                    reply_selectors = [
                                        'div[aria-label="Reply"]',
                                        'div[data-testid="replyButton"]',
                                        'button[data-testid="replyButton"]',
                                        'div[role="button"][aria-label*="Reply"]',
                                        'a[href*="/compose/tweet"][role="button"]',
                                        '[data-testid="reply"]'
                                    ]
                                    
                                    reply_button = None
                                    for selector in reply_selectors:
                                        try:
                                            # Try to find reply button within tweet first
                                            button = await first_tweet.query_selector(selector)
                                            if button:
                                                reply_button = button
                                                logger.info(f"Found reply button using selector: {selector}")
                                                break
                                        except Exception as e:
                                            logger.debug(f"Selector {selector} failed: {e}")
                                    
                                    if not reply_button:
                                        logger.error("Could not find reply button")
                                        continue
                                        
                                    # Make sure reply button is visible
                                    await reply_button.scroll_into_view_if_needed()
                                    await asyncio.sleep(1)
                                    
                                    # Click methods to try
                                    click_methods = [
                                        lambda: reply_button.click(),
                                        lambda: reply_button.click(delay=100),
                                        lambda: reply_button.click(button="left"),
                                        lambda: reply_button.click(force=True),
                                        # JavaScript click events as fallback
                                        lambda: self.page.evaluate("(element) => element.click()", reply_button),
                                        lambda: self.page.evaluate("""(element) => {
                                            const event = new MouseEvent('click', {
                                                view: window,
                                                bubbles: true,
                                                cancelable: true
                                            });
                                            element.dispatchEvent(event);
                                        }""", reply_button)
                                    ]
                                    
                                    clicked = False
                                    for click_method in click_methods:
                                        try:
                                            await click_method()
                                            await asyncio.sleep(2)
                                            
                                            # Check if reply box appeared
                                            reply_box = await self.page.query_selector('[data-testid="tweetTextarea_0"]')
                                            if reply_box:
                                                clicked = True
                                                logger.info("Successfully clicked reply button")
                                                
                                                # Generate and type our response
                                                response = self.fallacy_detector.generate_twitter_response(fallacies, tweet_text)
                                                if response:
                                                    logger.info(f"Generated response: {response}")
                                                    
                                                    # Click and type with retry
                                                    max_retries = 3
                                                    for attempt in range(max_retries):
                                                        try:
                                                            await reply_box.click()
                                                            await asyncio.sleep(1)
                                                            await reply_box.type(response, delay=100)
                                                            
                                                            # Verify text was entered
                                                            entered_text = await reply_box.text_content()
                                                            if response in entered_text:
                                                                logger.info("Successfully entered response text")
                                                                
                                                                # Try multiple selectors for the tweet button
                                                                tweet_button_selectors = [
                                                                    '[data-testid="tweetButton"]',
                                                                    '[data-testid="tweetButtonInline"]',
                                                                    'div[data-testid="tweetButtonInline"]',
                                                                    'div[role="button"]:has-text("Reply")',
                                                                    'div[role="button"]:has-text("Tweet")'
                                                                ]
                                                                
                                                                tweet_button = None
                                                                for selector in tweet_button_selectors:
                                                                    try:
                                                                        button = await self.page.wait_for_selector(selector, timeout=2000)
                                                                        if button:
                                                                            tweet_button = button
                                                                            logger.info(f"Found tweet button with selector: {selector}")
                                                                            break
                                                                    except Exception:
                                                                        continue
                                                                
                                                                if tweet_button:
                                                                    try:
                                                                        await tweet_button.click()
                                                                        logger.info("Clicked tweet button to submit reply")
                                                                        # Wait for the tweet to be posted
                                                                        await self.page.wait_for_load_state('networkidle')
                                                                        await asyncio.sleep(2)
                                                                    except Exception as e:
                                                                        logger.error(f"Error clicking tweet button: {e}")
                                                                        # Try JavaScript click as fallback
                                                                        try:
                                                                            await self.page.evaluate("(element) => element.click()", tweet_button)
                                                                            logger.info("Clicked tweet button using JavaScript")
                                                                            await self.page.wait_for_load_state('networkidle')
                                                                            await asyncio.sleep(2)
                                                                        except Exception as js_e:
                                                                            logger.error(f"JavaScript click also failed: {js_e}")
                                                                else:
                                                                    logger.error("Could not find tweet button with any selector")
                                                                break
                                                        except Exception as e:
                                                            logger.warning(f"Text entry attempt {attempt + 1} failed: {e}")
                                                            if attempt == max_retries - 1:
                                                                logger.error("Failed to enter response text")
                                                                continue
                                                else:
                                                    logger.error("Failed to generate response")
                                                break
                                        except Exception as e:
                                            logger.debug(f"Click method failed: {e}")
                                            continue
                                    
                                    if not clicked:
                                        logger.error("All click methods failed")
                                else:
                                    logger.info("No fallacies found in this tweet")
                            except Exception as e:
                                logger.error(f"Error in fallacy detection/response: {str(e)}")
                                await self.page.screenshot(path=f"fallacy_error_{username}.png")
                        else:
                            logger.warning("Could not find text in tweet")
                    else:
                        logger.warning("No tweets found immediately after load")
                        
                    break  # Successfully loaded profile
                    
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"Error loading profile: {e}, attempt {attempt + 1}/{max_retries}")
                        await asyncio.sleep(2)
                        continue
                    raise
            
            # Continue with scrolling and checking more tweets...
            tweet_selector = 'article[data-testid="tweet"]'
            last_height = await self.page.evaluate('document.body.scrollHeight')
            tweets_seen = set()
            scroll_attempts = 0
            max_scrolls = 3
            
            while scroll_attempts < max_scrolls:
                tweets = await self.page.query_selector_all(tweet_selector)
                logger.info(f"Found {len(tweets)} tweets after scroll")
                
                for tweet in tweets:
                    try:
                        tweet_id = await tweet.get_attribute('data-testid')
                        if tweet_id in tweets_seen:
                            continue
                        tweets_seen.add(tweet_id)
                        
                        tweet_text_elem = await tweet.query_selector('[data-testid="tweetText"]')
                        if tweet_text_elem:
                            tweet_text = await tweet_text_elem.inner_text()
                            logger.info(f"Checking tweet: {tweet_text[:100]}...")
                            
                            # Force check this tweet
                            logger.info("Checking tweet for fallacies...")
                            try:
                                fallacies = self.fallacy_detector.detect_fallacies(tweet_text)
                                logger.info(f"Fallacy detection result: {fallacies}")
                                
                                if fallacies and len(fallacies) > 0:
                                    logger.info(f"Found {len(fallacies)} fallacies: {fallacies}")
                                    
                                    # Take screenshot before clicking reply
                                    await self.page.screenshot(path=f"found_fallacy_{username}.png")
                                    
                                    # Multiple possible selectors for reply button
                                    reply_selectors = [
                                        'div[aria-label="Reply"]',
                                        'div[data-testid="replyButton"]',
                                        'button[data-testid="replyButton"]',
                                        'div[role="button"][aria-label*="Reply"]',
                                        'a[href*="/compose/tweet"][role="button"]',
                                        '[data-testid="reply"]'
                                    ]
                                    
                                    reply_button = None
                                    for selector in reply_selectors:
                                        try:
                                            # Try to find reply button within tweet first
                                            button = await tweet.query_selector(selector)
                                            if button:
                                                reply_button = button
                                                logger.info(f"Found reply button using selector: {selector}")
                                                break
                                        except Exception as e:
                                            logger.debug(f"Selector {selector} failed: {e}")
                                    
                                    if not reply_button:
                                        logger.error("Could not find reply button")
                                        continue
                                        
                                    # Make sure reply button is visible
                                    await reply_button.scroll_into_view_if_needed()
                                    await asyncio.sleep(1)
                                    
                                    # Click methods to try
                                    click_methods = [
                                        lambda: reply_button.click(),
                                        lambda: reply_button.click(delay=100),
                                        lambda: reply_button.click(button="left"),
                                        lambda: reply_button.click(force=True),
                                        # JavaScript click events as fallback
                                        lambda: self.page.evaluate("(element) => element.click()", reply_button),
                                        lambda: self.page.evaluate("""(element) => {
                                            const event = new MouseEvent('click', {
                                                view: window,
                                                bubbles: true,
                                                cancelable: true
                                            });
                                            element.dispatchEvent(event);
                                        }""", reply_button)
                                    ]
                                    
                                    clicked = False
                                    for click_method in click_methods:
                                        try:
                                            await click_method()
                                            await asyncio.sleep(2)
                                            
                                            # Check if reply box appeared
                                            reply_box = await self.page.query_selector('[data-testid="tweetTextarea_0"]')
                                            if reply_box:
                                                clicked = True
                                                logger.info("Successfully clicked reply button")
                                                
                                                # Generate and type our response
                                                response = self.fallacy_detector.generate_twitter_response(fallacies, tweet_text)
                                                if response:
                                                    logger.info(f"Generated response: {response}")
                                                    
                                                    # Click and type with retry
                                                    max_retries = 3
                                                    for attempt in range(max_retries):
                                                        try:
                                                            await reply_box.click()
                                                            await asyncio.sleep(1)
                                                            await reply_box.type(response, delay=100)
                                                            
                                                            # Verify text was entered
                                                            entered_text = await reply_box.text_content()
                                                            if response in entered_text:
                                                                logger.info("Successfully entered response text")
                                                                
                                                                # Try multiple selectors for the tweet button
                                                                tweet_button_selectors = [
                                                                    '[data-testid="tweetButton"]',
                                                                    '[data-testid="tweetButtonInline"]',
                                                                    'div[data-testid="tweetButtonInline"]',
                                                                    'div[role="button"]:has-text("Reply")',
                                                                    'div[role="button"]:has-text("Tweet")'
                                                                ]
                                                                
                                                                tweet_button = None
                                                                for selector in tweet_button_selectors:
                                                                    try:
                                                                        button = await self.page.wait_for_selector(selector, timeout=2000)
                                                                        if button:
                                                                            tweet_button = button
                                                                            logger.info(f"Found tweet button with selector: {selector}")
                                                                            break
                                                                    except Exception:
                                                                        continue
                                                                
                                                                if tweet_button:
                                                                    try:
                                                                        await tweet_button.click()
                                                                        logger.info("Clicked tweet button to submit reply")
                                                                        # Wait for the tweet to be posted
                                                                        await self.page.wait_for_load_state('networkidle')
                                                                        await asyncio.sleep(2)
                                                                    except Exception as e:
                                                                        logger.error(f"Error clicking tweet button: {e}")
                                                                        # Try JavaScript click as fallback
                                                                        try:
                                                                            await self.page.evaluate("(element) => element.click()", tweet_button)
                                                                            logger.info("Clicked tweet button using JavaScript")
                                                                            await self.page.wait_for_load_state('networkidle')
                                                                            await asyncio.sleep(2)
                                                                        except Exception as js_e:
                                                                            logger.error(f"JavaScript click also failed: {js_e}")
                                                                else:
                                                                    logger.error("Could not find tweet button with any selector")
                                                                break
                                                        except Exception as e:
                                                            logger.warning(f"Text entry attempt {attempt + 1} failed: {e}")
                                                            if attempt == max_retries - 1:
                                                                logger.error("Failed to enter response text")
                                                                continue
                                                else:
                                                    logger.error("Failed to generate response")
                                                break
                                        except Exception as e:
                                            logger.debug(f"Click method failed: {e}")
                                            continue
                                    
                                    if not clicked:
                                        logger.error("All click methods failed")
                                else:
                                    logger.info("No fallacies found in this tweet")
                            except Exception as e:
                                logger.error(f"Error in fallacy detection/response: {str(e)}")
                                await self.page.screenshot(path=f"fallacy_error_{username}.png")
                    except Exception as e:
                        logger.error(f"Error processing tweet: {e}")
                        continue
                
                await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await asyncio.sleep(2)
                
                new_height = await self.page.evaluate('document.body.scrollHeight')
                if new_height == last_height:
                    logger.info("Reached end of timeline or no new tweets loading")
                    break
                
                last_height = new_height
                scroll_attempts += 1
            
            return True
            
        except Exception as e:
            logger.error(f"Error monitoring account {username}: {e}")
            await self.page.screenshot(path=f"monitor_error_{username}.png")
            return False

    async def cleanup(self):
        """Clean up browser resources."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
