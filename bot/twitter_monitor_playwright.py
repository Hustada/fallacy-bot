import asyncio
import logging
import random
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from playwright.async_api import async_playwright, Page, TimeoutError, ElementHandle
from .fallacy_detector import FallacyDetector
from .db_manager import DBManager
from dotenv import load_dotenv
import os
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TwitterMonitorPlaywright:
    def __init__(self):
        load_dotenv()
        self.last_check_times = {}
        self.fallacy_detector = FallacyDetector()
        self.db_manager = DBManager()
        self.browser = None
        self.context = None
        self.page = None
        
        # Load Twitter credentials from .env files
        bot_env_path = Path(__file__).parent / '.env'
        root_env_path = Path(__file__).parent.parent / '.env'
        
        self.twitter_username = os.getenv('TWITTER_USERNAME')
        self.twitter_password = os.getenv('TWITTER_PASSWORD')
        
        # If not in environment, try reading from files
        if not self.twitter_username or not self.twitter_password:
            logger.info("Twitter credentials not found in environment, checking .env files")
            for env_path in [bot_env_path, root_env_path]:
                if env_path.exists():
                    logger.info(f"Reading from {env_path}")
                    with open(env_path, 'r') as f:
                        for line in f:
                            if line.startswith('TWITTER_USERNAME='):
                                self.twitter_username = line.strip().split('=', 1)[1].strip("'").strip('"')
                                os.environ["TWITTER_USERNAME"] = self.twitter_username
                            elif line.startswith('TWITTER_PASSWORD='):
                                self.twitter_password = line.strip().split('=', 1)[1].strip("'").strip('"')
                                os.environ["TWITTER_PASSWORD"] = self.twitter_password

    def _get_random_viewport(self) -> Dict[str, int]:
        """Generate random but realistic viewport dimensions."""
        common_resolutions = [
            (1920, 1080), (1366, 768), (1536, 864),
            (1440, 900), (1280, 720), (1600, 900)
        ]
        width, height = random.choice(common_resolutions)
        # Add slight variations
        width += random.randint(-50, 50)
        height += random.randint(-30, 30)
        return {"width": width, "height": height}

    def _get_random_user_agent(self) -> str:
        """Generate a random but realistic user agent."""
        os_versions = ['10_15_7', '11_0_1', '12_0_1', '13_0']
        chrome_versions = ['120.0.0.0', '119.0.0.0', '118.0.0.0']
        return f'Mozilla/5.0 (Macintosh; Intel Mac OS X {random.choice(os_versions)}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.choice(chrome_versions)} Safari/537.36'

    async def _natural_scroll(self, start_pos: int, end_pos: int):
        """Scroll in a natural, human-like way."""
        steps = random.randint(5, 10)
        for i in range(steps):
            progress = (i + 1) / steps
            current_pos = start_pos + (end_pos - start_pos) * progress
            # Add some randomness to the scroll position
            jitter = random.randint(-10, 10)
            await self.page.evaluate(f'window.scrollTo(0, {current_pos + jitter})')
            await asyncio.sleep(random.uniform(0.1, 0.3))

    async def _move_mouse_naturally(self, element: ElementHandle):
        """Move mouse in a natural, curved path to the element."""
        # Get element position
        box = await element.bounding_box()
        if not box:
            return

        # Current mouse position or viewport center if not set
        current = await self.page.evaluate('({ x: window.mouseX || window.innerWidth/2, y: window.mouseY || window.innerHeight/2 })')
        start_x, start_y = current['x'], current['y']
        end_x, end_y = box['x'] + box['width'] / 2, box['y'] + box['height'] / 2

        # Generate a bezier curve path
        control_x = (start_x + end_x) / 2 + random.randint(-100, 100)
        control_y = (start_y + end_y) / 2 + random.randint(-100, 100)
        steps = random.randint(10, 20)

        for i in range(steps):
            t = i / steps
            # Quadratic bezier curve
            x = (1 - t) ** 2 * start_x + 2 * (1 - t) * t * control_x + t ** 2 * end_x
            y = (1 - t) ** 2 * start_y + 2 * (1 - t) * t * control_y + t ** 2 * end_y
            await self.page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.01, 0.03))

    async def setup(self):
        """Initialize the browser and context with anti-detection measures."""
        playwright = await async_playwright().start()
        
        # Launch with multiple anti-detection arguments
        self.browser = await playwright.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-site-isolation-trials',
                '--disable-web-security',
                '--disable-features=ScriptStreaming',
                f'--window-size={random.randint(1200,1920)},{random.randint(800,1080)}',
                '--no-sandbox'
            ]
        )
        
        # Create context with randomized viewport and user agent
        viewport = self._get_random_viewport()
        self.context = await self.browser.new_context(
            viewport=viewport,
            user_agent=self._get_random_user_agent(),
            java_script_enabled=True,
            has_touch=random.choice([True, False]),
            is_mobile=False,
            color_scheme=random.choice(['dark', 'light']),
            locale=random.choice(['en-US', 'en-GB', 'en-CA']),
            timezone_id=random.choice(['America/New_York', 'America/Chicago', 'America/Los_Angeles'])
        )
        
        # Additional context configuration
        await self.context.add_init_script("""
            // Override automation-related properties
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            
            // Add random fingerprint noise
            const originalGetContext = HTMLCanvasElement.prototype.getContext;
            HTMLCanvasElement.prototype.getContext = function(type) {
                const context = originalGetContext.apply(this, arguments);
                if (context && type === '2d') {
                    const originalFillText = context.fillText;
                    context.fillText = function() {
                        const args = Array.from(arguments);
                        args[1] += Math.random() * 0.001;
                        args[2] += Math.random() * 0.001;
                        return originalFillText.apply(this, args);
                    }
                }
                return context;
            };
        """)
        
        self.page = await self.context.new_page()
        
        # Add page-level anti-detection measures
        await self.page.add_init_script("""
            // Track mouse position
            window.mouseX = 0;
            window.mouseY = 0;
            document.addEventListener('mousemove', (e) => {
                window.mouseX = e.clientX;
                window.mouseY = e.clientY;
            });
        """)
        
        # Login to X
        await self._login()

    async def _human_type(self, element: ElementHandle, text: str):
        """Type text into an element with human-like timing and mistakes."""
        # Move mouse to element naturally
        await self._move_mouse_naturally(element)
        await element.click()
        
        # Clear any existing text with random backspaces
        current_value = await element.evaluate('el => el.value')
        if current_value:
            for _ in range(len(current_value)):
                await element.press('Backspace')
                await asyncio.sleep(random.uniform(0.05, 0.15))
        
        # Type with human-like timing and occasional mistakes
        for i, char in enumerate(text):
            # Randomly make and correct a typo (5% chance)
            if random.random() < 0.05:
                typo = random.choice('qwertyuiopasdfghjklzxcvbnm')
                await element.type(typo)
                await asyncio.sleep(random.uniform(0.1, 0.3))
                await element.press('Backspace')
                await asyncio.sleep(random.uniform(0.1, 0.3))
            
            # Type the correct character with variable timing
            await element.type(char)
            
            # Longer pauses for space and punctuation
            if char in ' .,!?':
                await asyncio.sleep(random.uniform(0.1, 0.4))
            else:
                # Variable typing speed
                await asyncio.sleep(random.uniform(0.05, 0.2))
            
            # Occasional longer pause (2% chance)
            if random.random() < 0.02:
                await asyncio.sleep(random.uniform(0.5, 1.0))

    async def _human_click(self, element: ElementHandle):
        """Click an element with human-like behavior."""
        # Move mouse naturally to element
        await self._move_mouse_naturally(element)
        
        # Random small delay before clicking (like human reaction time)
        await asyncio.sleep(random.uniform(0.1, 0.3))
        
        # 10% chance to slightly miss the first click
        if random.random() < 0.1:
            box = await element.bounding_box()
            if box:
                miss_x = box['x'] + box['width'] + random.randint(5, 10)
                miss_y = box['y'] + box['height'] + random.randint(5, 10)
                await self.page.mouse.click(miss_x, miss_y)
                await asyncio.sleep(random.uniform(0.1, 0.3))
                await self._move_mouse_naturally(element)
                await asyncio.sleep(random.uniform(0.1, 0.2))
        
        # Click with random delay
        await element.click(delay=random.randint(10, 50))
        
        # Random pause after clicking
        await asyncio.sleep(random.uniform(0.2, 0.5))

    async def _handle_tweet_response(self, tweet: ElementHandle, tweet_text: str, tweet_id: str, username: str) -> bool:
        """Handle responding to a tweet with human-like behavior."""
        try:
            # Random delay like reading and analyzing the tweet
            await asyncio.sleep(random.uniform(2.0, 4.0))
            
            # Check for fallacies
            fallacies = self.fallacy_detector.detect_fallacies(tweet_text)
            logger.info(f"Fallacy detection result: {fallacies}")
            
            if not fallacies or len(fallacies) == 0:
                return False
                
            logger.info(f"Found {len(fallacies)} fallacies: {fallacies}")
            
            # Take screenshot before interaction
            await self.page.screenshot(path=f"found_fallacy_{username}.png")
            
            # Find reply button with human-like scanning
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
                # Random delay like looking for the button
                await asyncio.sleep(random.uniform(0.2, 0.5))
                try:
                    button = await tweet.query_selector(selector)
                    if button:
                        reply_button = button
                        logger.info(f"Found reply button using selector: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
            
            if not reply_button:
                logger.error("Could not find reply button")
                return False
            
            # Make sure reply button is visible with natural scrolling
            await reply_button.scroll_into_view_if_needed()
            await asyncio.sleep(random.uniform(0.5, 1.2))
            
            # Click reply button naturally
            await self._human_click(reply_button)
            
            # Wait for reply box with human-like patience
            await asyncio.sleep(random.uniform(1.0, 2.0))
            reply_box = await self._wait_for_element('div[data-testid="tweetTextarea_0"]')
            
            if not reply_box:
                logger.error("Could not find reply box")
                return False
            
            # Generate response with human-like timing
            await asyncio.sleep(random.uniform(2.0, 4.0))  # Think about response
            response = self.fallacy_detector.generate_twitter_response(fallacies, tweet_text)
            
            if not response:
                logger.error("Failed to generate response")
                return False
                
            logger.info(f"Generated response: {response}")
            
            # Type response with human-like behavior
            await self._human_type(reply_box, response)
            
            # Random delay like reviewing what we typed
            await asyncio.sleep(random.uniform(1.5, 3.0))
            
            # Verify text was entered
            entered_text = await reply_box.text_content()
            if response not in entered_text:
                logger.error("Failed to enter response text")
                return False
            
            logger.info("Successfully entered response text")
            
            # Look for tweet button with human-like scanning
            tweet_button_selectors = [
                '[data-testid="tweetButton"]',
                '[data-testid="tweetButtonInline"]',
                'div[data-testid="tweetButtonInline"]',
                'div[role="button"]:has-text("Reply")',
                'div[role="button"]:has-text("Tweet")'
            ]
            
            for selector in tweet_button_selectors:
                # Random delay like looking for the button
                await asyncio.sleep(random.uniform(0.2, 0.5))
                
                tweet_button = await self._wait_for_element(selector, timeout=5000)
                if tweet_button:
                    # Move to tweet button naturally
                    await self._move_mouse_naturally(tweet_button)
                    
                    # Sometimes hesitate before final submission
                    if random.random() < 0.4:  # 40% chance
                        await self.page.mouse.move(
                            random.randint(-15, 15),
                            random.randint(-15, 15),
                            steps=random.randint(3, 7)
                        )
                        await asyncio.sleep(random.uniform(0.5, 1.2))
                    
                    # Click tweet button naturally
                    await self._human_click(tweet_button)
                    
                    # Wait for tweet to send
                    await asyncio.sleep(random.uniform(2.0, 4.0))
                    
                    # Store interaction in database
                    await self.db_manager.store_interaction({
                        'tweet_url': f'https://twitter.com/{username}/status/{tweet_id}',
                        'tweet_text': tweet_text,
                        'response': response,
                        'fallacies': fallacies
                    })
                    
                    # Mark as processed
                    self.db_manager.mark_tweet_processed(tweet_id, username)
                    logger.info(f"Marked tweet {tweet_id} as processed")
                    
                    # Random longer delay before next interaction to avoid spam detection
                    await asyncio.sleep(random.uniform(30.0, 60.0))
                    
                    return True
            
            logger.error("Could not find tweet button")
            return False
            
        except Exception as e:
            logger.error(f"Error handling tweet response: {e}")
            return False

    async def _wait_for_element(self, selector: str, timeout: int = 10000, state: str = 'visible') -> Optional[ElementHandle]:
        """Wait for an element with human-like behavior and retry logic."""
        try:
            # Random initial delay like a human looking for the element
            await asyncio.sleep(random.uniform(0.5, 2.0))
            
            # Scroll around naturally while looking for the element
            current_scroll = await self.page.evaluate('window.scrollY')
            scroll_attempts = random.randint(2, 4)
            
            for _ in range(scroll_attempts):
                # Random scroll distance
                scroll_to = current_scroll + random.randint(-300, 300)
                await self._natural_scroll(current_scroll, scroll_to)
                current_scroll = scroll_to
                
                # Try to find the element
                element = await self.page.wait_for_selector(selector, timeout=timeout // scroll_attempts, state=state)
                if element:
                    # Move mouse naturally to the element
                    await self._move_mouse_naturally(element)
                    return element
                
                # Random pause between scroll attempts
                await asyncio.sleep(random.uniform(0.5, 1.5))
                
        except TimeoutError:
            logger.warning(f"Timeout waiting for {selector}, trying alternative methods...")
            
        # Try alternative selectors with human-like behavior
        alt_selectors = {
            'input[autocomplete="username"]': [
                'input[name="text"]', 
                'input[type="text"]',
                'input[placeholder*="username" i]',
                'input[placeholder*="email" i]'
            ],
            'input[type="password"]': [
                'input[name="password"]',
                'input[placeholder*="password" i]'
            ],
            'div[role="button"]:has-text("Next")': [
                'div[data-testid="Button"]',
                'div[role="button"]',
                'button:has-text("Next")',
                '[aria-label*="Next" i]'
            ],
            'div[role="button"]:has-text("Log in")': [
                'div[data-testid="LoginButton"]',
                'button:has-text("Log in")',
                '[aria-label*="Log in" i]',
                '[aria-label*="Sign in" i]'
            ]
        }
        
        if selector in alt_selectors:
            for alt_selector in alt_selectors[selector]:
                try:
                    logger.info(f"Looking for alternative: {alt_selector}")
                    # Random delay between attempts
                    await asyncio.sleep(random.uniform(0.3, 1.0))
                    element = await self.page.wait_for_selector(alt_selector, timeout=5000, state=state)
                    if element:
                        await self._move_mouse_naturally(element)
                        return element
                except TimeoutError:
                    continue
        
        return None

    async def _login(self):
        """Login to X (formerly Twitter) using environment credentials with human-like behavior."""
        if not self.twitter_username or not self.twitter_password:
            raise ValueError("Twitter credentials not found in .env file")
            
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Start at login page with human-like initial delay
                await asyncio.sleep(random.uniform(1.0, 3.0))
                await self.page.goto('https://x.com/login', wait_until='networkidle')
                
                # Random delay like a human reading the page
                await asyncio.sleep(random.uniform(2.0, 4.0))
                
                # Wait for and fill username with human-like behavior
                username_input = await self._wait_for_element('input[autocomplete="username"]', timeout=15000)
                if not username_input:
                    raise Exception("Could not find username input field")
                
                # Type username with human-like timing and potential mistakes
                await self._human_type(username_input, self.twitter_username)
                
                # Random delay before clicking next (like reading/checking input)
                await asyncio.sleep(random.uniform(0.5, 1.5))
                
                # Try multiple methods to click next with human-like behavior
                next_button = await self._wait_for_element('div[role="button"]:has-text("Next")', timeout=10000)
                if next_button:
                    await self._human_click(next_button)
                else:
                    # Try pressing Enter if button not found, with human-like delay
                    await asyncio.sleep(random.uniform(0.2, 0.5))
                    await username_input.press('Enter')
                
                # Random delay before looking for password field (like page load)
                await asyncio.sleep(random.uniform(1.5, 3.0))
                
                # Wait for and fill password with human-like behavior
                password_input = await self._wait_for_element('input[type="password"]', timeout=15000)
                if not password_input:
                    raise Exception("Could not find password input field")
                
                # Type password with human-like timing
                await self._human_type(password_input, self.twitter_password)
                
                # Random delay before clicking login (like double-checking password)
                await asyncio.sleep(random.uniform(0.8, 2.0))
                
                # Try multiple methods to click login with human-like behavior
                login_button = await self._wait_for_element('div[role="button"]:has-text("Log in")', timeout=10000)
                if login_button:
                    await self._human_click(login_button)
                else:
                    # Try pressing Enter if button not found, with human-like delay
                    await asyncio.sleep(random.uniform(0.2, 0.5))
                    await password_input.press('Enter')
                
                # Wait for successful login with human-like page processing delay
                try:
                    await asyncio.sleep(random.uniform(2.0, 4.0))
                    await self.page.wait_for_url('https://x.com/home', timeout=30000)
                    
                    # Sometimes humans scroll a bit after logging in
                    if random.random() < 0.7:  # 70% chance
                        await self._natural_scroll(0, random.randint(100, 300))
                    
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
                    # Add random delay between retries like a human would
                    retry_delay = random.uniform(3.0, 8.0)
                    logger.info(f"Retrying login in {retry_delay:.1f} seconds... (attempt {retry_count + 1}/{max_retries})")
                    await asyncio.sleep(retry_delay)
                else:
                    raise Exception(f"Failed to login after {max_retries} attempts: {str(e)}")

    async def _handle_verification_screens(self) -> bool:
        """Handle any additional verification screens that may appear during login with human-like behavior."""
        try:
            # Random initial delay like a human processing the new screen
            await asyncio.sleep(random.uniform(1.0, 3.0))
            
            # Check for common verification elements with human-like scanning
            verification_selectors = [
                'input[name="verfication_code"]',
                'input[name="challenge_response"]',
                'div[role="button"]:has-text("Skip for now")',
                'div[role="button"]:has-text("Not now")',
                'div[role="button"]:has-text("Maybe later")',
                'div[role="button"]:has-text("Close")',
                'div[role="button"]:has-text("Cancel")'
            ]
            
            # Randomize the order to simulate human visual scanning
            random.shuffle(verification_selectors)
            
            for selector in verification_selectors:
                # Random delay between checking different elements
                await asyncio.sleep(random.uniform(0.3, 1.0))
                
                element = await self._wait_for_element(selector, timeout=5000)
                if element:
                    if any(text in selector for text in ['Skip', 'Not now', 'Maybe later', 'Close', 'Cancel']):
                        # Sometimes move mouse around before clicking, like a hesitant human
                        if random.random() < 0.3:  # 30% chance
                            nearby_offset = random.randint(50, 150)
                            await self.page.mouse.move(
                                random.randint(-nearby_offset, nearby_offset),
                                random.randint(-nearby_offset, nearby_offset)
                            )
                            await asyncio.sleep(random.uniform(0.2, 0.8))
                        
                        # Click the button naturally
                        await self._human_click(element)
                        
                        # Random delay after clicking like a human waiting for response
                        await asyncio.sleep(random.uniform(1.5, 3.0))
                    else:
                        # For input fields, type with human-like behavior
                        verification_code = input("Please enter the verification code: ")
                        await self._human_type(element, verification_code)
                        
                        # Look for and click submit button
                        submit_button = await self._wait_for_element('div[role="button"]:has-text("Submit")', timeout=5000)
                        if submit_button:
                            await self._human_click(submit_button)
                            
                            # Longer wait after submitting verification
                            await asyncio.sleep(random.uniform(2.0, 4.0))
                    
                    logger.info(f"Handled verification element: {selector}")
                    return True
            
            # Sometimes scroll a bit while looking for elements
            if random.random() < 0.4:  # 40% chance
                await self._natural_scroll(0, random.randint(100, 300))
            
            return False
            
        except Exception as e:
            logger.warning(f"Error handling verification screens: {e}")
            return False

    async def monitor_account(self, username: str) -> bool:
        """Monitor a specific account's timeline with human-like behavior."""
        try:
            # Navigate to user's profile with human-like initial delay
            profile_url = f"https://x.com/{username}"
            logger.info(f"Navigating to {profile_url}")
            
            # Random delay before starting like a human would have
            await asyncio.sleep(random.uniform(1.0, 3.0))
            
            # Try navigation with retry and human-like behavior
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Navigate and wait for initial load with human-like patience
                    await self.page.goto(profile_url, wait_until='domcontentloaded', timeout=15000)
                    logger.info("Initial page load complete")
                    
                    # Random delay like a human reading the page header
                    await asyncio.sleep(random.uniform(2.0, 4.0))
                    
                    # Check if we hit a "Something went wrong" page
                    error_text = await self.page.query_selector('text="Something went wrong"')
                    if error_text:
                        logger.warning("Hit error page, refreshing...")
                        # Move mouse around randomly before refresh like a frustrated user
                        await self.page.mouse.move(
                            random.randint(100, 500),
                            random.randint(100, 300)
                        )
                        await asyncio.sleep(random.uniform(0.5, 1.5))
                        await self.page.reload()
                        await asyncio.sleep(random.uniform(2.0, 4.0))
                        continue
                    
                    # Wait for dynamic content with human-like scrolling and patience
                    max_load_attempts = 3
                    for load_attempt in range(max_load_attempts):
                        # Scroll around naturally while waiting for content
                        await self._natural_scroll(0, random.randint(200, 500))
                        await asyncio.sleep(random.uniform(3.0, 5.0))
                        
                        tweets = await self.page.query_selector_all('article[data-testid="tweet"]')
                        if tweets:
                            break
                            
                        logger.info(f"No tweets found on attempt {load_attempt + 1}, retrying...")
                        # Sometimes scroll back up before refresh
                        if random.random() < 0.4:  # 40% chance
                            current_scroll = await self.page.evaluate('window.scrollY')
                            await self._natural_scroll(current_scroll, 0)
                            
                        await self.page.reload()
                        # Random delay after refresh
                        await asyncio.sleep(random.uniform(2.0, 4.0))
                    
                    # Process tweets with human-like behavior
                    tweets = await self.page.query_selector_all('article[data-testid="tweet"]')
                    if tweets:
                        logger.info(f"Found {len(tweets)} tweets")
                        
                        # Random delay like reading the timeline
                        await asyncio.sleep(random.uniform(1.5, 3.0))
                        
                        # Process first tweet with human-like interaction
                        first_tweet = tweets[0]
                        
                        # Move mouse around tweet area naturally
                        await self._move_mouse_naturally(first_tweet)
                        
                        # Random delay like reading tweet content
                        await asyncio.sleep(random.uniform(2.0, 4.0))
                        
                        tweet_text_elem = await first_tweet.query_selector('[data-testid="tweetText"]')
                        if tweet_text_elem:
                            # Sometimes highlight text while reading
                            if random.random() < 0.3:  # 30% chance
                                await tweet_text_elem.hover()
                                await asyncio.sleep(random.uniform(0.5, 1.5))
                            
                            tweet_text = await tweet_text_elem.inner_text()
                            logger.info(f"First tweet FULL text:\n{tweet_text}")
                            
                            # Get tweet ID with human-like mouse movement
                            tweet_id = None
                            try:
                                tweet_link = await first_tweet.query_selector('a[href*="/status/"]')
                                if tweet_link:
                                    # Move mouse over timestamp sometimes
                                    if random.random() < 0.2:  # 20% chance
                                        await self._move_mouse_naturally(tweet_link)
                                        await asyncio.sleep(random.uniform(0.3, 0.8))
                                    
                                    href = await tweet_link.get_attribute('href')
                                    tweet_id = href.split('/status/')[-1].split('?')[0]
                            except Exception as e:
                                logger.error(f"Error getting tweet ID: {e}")
                                continue

                            # Skip if we've already processed this tweet
                            if tweet_id and self.db_manager.is_tweet_processed(tweet_id):
                                logger.info(f"Skipping already processed tweet {tweet_id}")
                                # Scroll past it naturally
                                current_scroll = await self.page.evaluate('window.scrollY')
                                await self._natural_scroll(current_scroll, current_scroll + random.randint(100, 200))
                                continue
                            
                            # Process tweet with our helper method
                            success = await self._handle_tweet_response(first_tweet, tweet_text, tweet_id, username)
                            if success:
                                return True
                            elif tweet_id:
                                # Mark as processed even if we didn't respond (no fallacies found)
                                self.db_manager.mark_tweet_processed(tweet_id, username)
                                logger.info(f"Marked tweet {tweet_id} as processed (no response needed)")
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
                            
                            # Get tweet ID
                            tweet_id = None
                            try:
                                tweet_link = await tweet.query_selector('a[href*="/status/"]')
                                if tweet_link:
                                    href = await tweet_link.get_attribute('href')
                                    tweet_id = href.split('/status/')[-1].split('?')[0]
                            except Exception as e:
                                logger.error(f"Error getting tweet ID: {e}")
                                continue

                            # Skip if we've already processed this tweet
                            if tweet_id and self.db_manager.is_tweet_processed(tweet_id):
                                logger.info(f"Skipping already processed tweet {tweet_id}")
                                continue
                            
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
                                        lambda: reply_button.click(force=True),
                                        lambda: self.page.evaluate("(element) => element.click()", reply_button)
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
                                                                
                                                                for selector in tweet_button_selectors:
                                                                    try:
                                                                        tweet_button = await self.page.wait_for_selector(selector, timeout=5000)
                                                                        if tweet_button:
                                                                            # Make sure button is visible and clickable
                                                                            await tweet_button.scroll_into_view_if_needed()
                                                                            await asyncio.sleep(1)
                                                                            
                                                                            # Try multiple click methods
                                                                            click_methods = [
                                                                                lambda: tweet_button.click(),
                                                                                lambda: tweet_button.click(delay=100),
                                                                                lambda: tweet_button.click(force=True),
                                                                                lambda: self.page.evaluate("(element) => element.click()", tweet_button)
                                                                            ]
                                                                            
                                                                            for click_method in click_methods:
                                                                                try:
                                                                                    await click_method()
                                                                                    await asyncio.sleep(2)
                                                                                    
                                                                                    # Check if the reply was successful
                                                                                    # Look for elements that indicate success
                                                                                    success_indicators = [
                                                                                        'div[data-testid="toast"]',  # Success toast
                                                                                        'div[aria-label*="Your tweet was sent"]',  # Success message
                                                                                        'div[data-testid="tweetButtonInline"][aria-disabled="true"]'  # Disabled tweet button
                                                                                    ]
                                                                                    
                                                                                    for indicator in success_indicators:
                                                                                        try:
                                                                                            await self.page.wait_for_selector(indicator, timeout=3000)
                                                                                            logger.info(f"Found success indicator: {indicator}")
                                                                                            
                                                                                            # Mark tweet as processed after successful reply
                                                                                            if tweet_id:
                                                                                                self.db_manager.mark_tweet_processed(tweet_id, username)
                                                                                                logger.info(f"Marked tweet {tweet_id} as processed")
                                                                                            
                                                                                            return True
                                                                                        except Exception:
                                                                                            continue
                                                                                    
                                                                                    # If we didn't find success indicators, try next click method
                                                                                    logger.warning("Click seemed successful but no success indicators found")
                                                                                    continue
                                                                                    
                                                                                except Exception as e:
                                                                                    logger.error(f"Click method failed: {e}")
                                                                                    continue
                                                                            
                                                                            logger.error("All click methods failed")
                                                                            break
                                                                            
                                                                    except Exception as e:
                                                                        logger.debug(f"Tweet button selector {selector} failed: {e}")
                                                                        continue
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
                                    if tweet_id:
                                        self.db_manager.mark_tweet_processed(tweet_id, username)
                                        logger.info(f"Marked tweet {tweet_id} as processed (no fallacies)")
                            except Exception as e:
                                logger.error(f"Error in fallacy detection/response: {str(e)}")
                                await self.page.screenshot(path=f"fallacy_error_{username}.png")
                        else:
                            logger.warning("Could not find text in tweet")
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