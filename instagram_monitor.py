import time
import requests
import os
import json
import sys
import hashlib
from datetime import datetime, timedelta
from playwright.async_api import async_playwright, TimeoutError
import logging
from typing import Dict, List, Optional, Any
import asyncio
from dotenv import load_dotenv
import random

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class InstagramMonitor:

    def __init__(self, instagram_username: str, instagram_password: str):
        self.bot_token = os.getenv(
            'BOT_TOKEN')  # keep this if you still use it here
        self.instagram_username = instagram_username
        self.instagram_password = instagram_password
        self.check_interval_minutes = 5
        self.max_retries = 3
        self.retry_delay = 5

        # Ensure required directories exist
        self.alert_states_dir = "alert_states"
        os.makedirs(self.alert_states_dir, exist_ok=True)

        # Load tracked users
        self.users_file = "users.json"
        self.tracked_users = self.load_users()

        # Initialize browser context
        self.browser = None
        self.context = None
        self.page = None
        self.last_login_time = None
        self.login_interval = timedelta(hours=6)  # Re-login every 6 hours

    def load_users(self) -> Dict[str, List[str]]:
        """Load users from the users file."""
        if not os.path.exists(self.users_file):
            return {}
        try:
            with open(self.users_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading users: {e}")
            return {}

    def save_users(self, users: Dict[str, List[str]]) -> None:
        """Save users to the users file."""
        try:
            with open(self.users_file, "w") as f:
                json.dump(users, f)
        except Exception as e:
            logger.error(f"Error saving users: {e}")

    def get_story_hash(self, content: bytes) -> str:
        """Create a unique hash from story content."""
        return hashlib.sha256(content).hexdigest()

    def get_last_alert_state(self, username: str) -> Dict[str, Any]:
        """Get the last alert state for a user."""
        file_path = os.path.join(self.alert_states_dir, f"{username}.json")
        if not os.path.exists(file_path):
            return {"hashes": {}, "timestamp": "", "last_check": ""}
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading alert state for {username}: {e}")
            return {"hashes": {}, "timestamp": "", "last_check": ""}

    def set_last_alert_state(self, username: str, state: Dict[str,
                                                              Any]) -> None:
        """Set the last alert state for a user."""
        try:
            file_path = os.path.join(self.alert_states_dir, f"{username}.json")
            with open(file_path, "w") as f:
                json.dump(state, f)
        except Exception as e:
            logger.error(f"Error saving alert state for {username}: {e}")

    def send_telegram_message(self, chat_id: str, message: str) -> bool:
        """Send a message via Telegram bot."""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
            response = requests.post(url, data=data)
            if response.ok:
                logger.info(f"Sent alert to {chat_id}")
            else:
                logger.error(
                    f"Failed to send alert to {chat_id}: {response.text}")
            return response.ok
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False

    def should_relogin(self) -> bool:
        """Check if we should re-login to Instagram."""
        if not self.last_login_time:
            return True
        return datetime.now() - self.last_login_time > self.login_interval

    async def login_to_instagram(self) -> bool:
        """Login to Instagram and return success status."""
        try:
            if self.browser is None:
                playwright = await async_playwright().start()
                self.browser = await playwright.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox', '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-accelerated-2d-canvas', '--disable-gpu',
                        '--window-size=1920,1080'
                    ])
                self.context = await self.browser.new_context()
                self.page = await self.context.new_page()

            await self.page.goto('https://www.instagram.com/accounts/login/',
                                 wait_until='domcontentloaded')
            await asyncio.sleep(2)  # Allow page to load

            # Updated selectors for username and password fields
            username_field = await self.page.query_selector(
                'input[name="username"]')
            password_field = await self.page.query_selector(
                'input[name="password"]')

            if not username_field or not password_field:
                logger.error("Could not find username or password field.")
                return False

            # Enter credentials
            await username_field.fill(self.instagram_username)
            await password_field.fill(self.instagram_password)

            # Updated selector for login button
            login_button = await self.page.query_selector(
                'button[type="submit"]')
            if not login_button:
                logger.error("Could not find login button.")
                return False

            await login_button.click()
            await asyncio.sleep(5)  # Wait for login to process

            # Check for successful login
            if await self.page.query_selector('svg[aria-label="Home"]'):
                logger.info("Successfully logged in to Instagram.")
                self.last_login_time = datetime.now()
                return True

            # Check for login error messages
            error_message = await self.page.query_selector(
                'p[data-testid="login-error-message"]')
            if error_message:
                error_text = await error_message.text_content()
                logger.error(f"Login failed: {error_text}")
                return False

            logger.error("Login failed for an unknown reason.")
            return False

        except Exception as e:
            logger.error(f"Error during Instagram login: {e}")
            return False

        finally:
            if self.page:
                content = await self.page.content()
                with open('debug_instagram_login.html', 'w') as f:
                    f.write(content)

    async def handle_route(self, route):
        """Handle request interception."""
        try:
            await route.continue_()
        except Exception as e:
            logger.error(f"Error in route handling: {str(e)}")
            await route.abort()

    async def cleanup_browser(self) -> None:
        """Clean up browser resources."""
        if self.browser:
            try:
                await self.browser.close()
            except Exception as e:
                logger.error(f"Error closing browser: {e}")
            finally:
                self.browser = None
                self.context = None
                self.page = None

    async def download_media_content(self, url: str) -> Optional[bytes]:
        """Download media content from URL."""
        try:
            response = requests.get(url, timeout=10)
            if response.ok:
                return response.content
            logger.error(f"Failed to download media: {response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error downloading media: {e}")
            return None

    async def get_story_content(self, story_element) -> Dict[str, Any]:
        """Extract and process story content including media and screenshot."""
        try:
            # Get media elements with updated selectors
            media = await story_element.query_selector(
                'img[alt*="Story"], video source')
            if not media:
                logger.warning("No media element found in story")
                return None

            # Get content type and URL
            tag_name = await media.get_attribute('tagName')
            content_type = 'video' if tag_name.lower(
            ) == 'video' or tag_name.lower() == 'source' else 'image'
            content_url = await media.get_attribute('src')

            if not content_url:
                logger.warning("Could not get content URL")
                return None

            # Take full screenshot of the story with maximum quality
            screenshot = await story_element.screenshot(
                type='png',
                animations='disabled',  # Capture the current frame for videos
                scale='css',  # Use CSS pixels for consistent sizing
                quality=100  # Maximum quality for PNG
            )

            if not screenshot:
                logger.warning("Could not take screenshot")
                return None

            # Download media content
            media_content = await self.download_media_content(content_url)
            if not media_content:
                logger.warning("Could not download media content")
                return None

            # Generate hashes
            screenshot_hash = self.get_story_hash(screenshot)
            media_hash = self.get_story_hash(media_content)

            return {
                'type': content_type,
                'screenshot': screenshot,
                'screenshot_hash': screenshot_hash,
                'media_content': media_content,
                'media_hash': media_hash
            }

        except Exception as e:
            logger.error(f"Error getting story content: {e}")
            return None

    def generate_hash_key(self, username: str, chat_id: str,
                          story: Dict[str, Any]) -> str:
        """
        Generate a unique hash key for a story that combines:
        - Username
        - Chat ID
        - Date (YYYYMMDD format)
        - First 8 chars of screenshot hash
        - First 8 chars of media hash (if available)
        """
        date_str = datetime.now().strftime("%Y%m%d")
        screenshot_hash_prefix = story['screenshot_hash'][:8]
        media_hash_prefix = story.get(
            'media_hash', '')[:8] if story.get('media_hash') else 'no-media'

        return f"{username}-{chat_id}-{date_str}-{screenshot_hash_prefix}-{media_hash_prefix}"

    def compare_story_content(self, new_content: Dict[str, Any],
                              old_hashes: Dict[str, str]) -> bool:
        """
        Compare story content with previously seen stories using both screenshot and media hashes.
        Returns True if the story is new, False if it's been seen before.
        """
        if not new_content:
            return False

        # Get new content hashes
        screenshot_hash = new_content['screenshot_hash']
        media_hash = new_content.get('media_hash')

        # If we have no previous hashes, it's definitely new
        if not old_hashes:
            return True

        for hash_key, stored_hashes in old_hashes.items():
            try:
                # Split stored combined hash into screenshot and media hashes
                stored_screenshot_hash, stored_media_hash = stored_hashes.split(
                    ':')

                # Story is considered the same if either:
                # 1. Screenshot hashes match
                # 2. Media hashes exist and match
                if screenshot_hash == stored_screenshot_hash:
                    logger.info(
                        f"Found matching screenshot hash in {hash_key}")
                    return False
                if media_hash and stored_media_hash and media_hash == stored_media_hash:
                    logger.info(f"Found matching media hash in {hash_key}")
                    return False

            except ValueError:
                # Handle legacy format or corrupted hash entries
                if screenshot_hash == stored_hashes or (
                        media_hash and media_hash == stored_hashes):
                    logger.info(f"Found matching legacy hash in {hash_key}")
                    return False

        # If we get here, no matches were found - it's a new story
        logger.info("No matching hashes found - this is a new story")
        return True

    async def check_story(self, username: str) -> Dict[str, Any]:
        """Check if a user has posted a new story."""
        try:
            if not await self.login_to_instagram():
                logger.error("Failed to login to Instagram")
                return None

            logger.info(f"Checking stories for @{username}...")
            await self.page.goto(f'https://www.instagram.com/{username}/')
            await self.page.wait_for_load_state('networkidle')

            # Look for story ring
            story_button = await self.page.wait_for_selector(
                'div[role="button"] canvas', timeout=5000)
            if not story_button:
                logger.info(f"No story found for @{username}")
                return None

            # Click on the story
            await story_button.click()
            await self.page.wait_for_selector('div[role="dialog"]',
                                              timeout=5000)

            # Get story content
            story_content = await self.get_story_content(self.page)
            if not story_content:
                logger.warning(f"Could not get story content for @{username}")
                return None

            return story_content

        except Exception as e:
            logger.error(f"Error checking story for @{username}: {str(e)}")
            return None

    async def run(self) -> None:
        """Main monitoring loop."""
        while True:
            try:
                # Reload tracked users
                self.tracked_users = self.load_users()

                if not self.tracked_users:
                    logger.info("No users to track, sleeping...")
                    await asyncio.sleep(60)
                    continue

                # Check each tracked username
                for chat_id, usernames in self.tracked_users.items():
                    for username in usernames:
                        await self.check_story(username)
                        await asyncio.sleep(2)  # Small delay between users

                # Sleep before next check
                await asyncio.sleep(self.check_interval_minutes * 60)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait a minute before retrying

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup_browser()


if __name__ == "__main__":

    async def main():
        try:
            async with InstagramMonitor() as monitor:
                await monitor.run()
        except KeyboardInterrupt:
            print("\nShutting down...")
        except Exception as e:
            print(f"\nFatal error: {e}")

    asyncio.run(main())
