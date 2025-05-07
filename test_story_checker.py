import asyncio
import logging
import os
import json
import requests
from instagram_monitor import InstagramMonitor

# Set the BOT_TOKEN environment variable
os.environ['BOT_TOKEN'] = '7569840561:AAHnbeez9FcYFM_IpwyxJ1AwaiqKA7r_jiA'

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize bot token
bot_token = os.getenv('BOT_TOKEN')
if not bot_token:
    raise ValueError("BOT_TOKEN environment variable is required")

def load_users():
    """Load users from the users file."""
    if not os.path.exists("users.json"):
        return {}
    try:
        with open("users.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, PermissionError) as e:
        logger.error(f"Error loading users: {e}")
        return {}

def send_telegram_message(chat_id: str, message: str) -> bool:
    """Send a message via Telegram bot."""
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
        response = requests.post(url, data=data)
        if response.ok:
            logger.info(f"Sent alert to {chat_id}")
        else:
            logger.error(f"Failed to send alert to {chat_id}: {response.text}")
        return response.ok
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")
        return False

async def check_and_notify():
    """Check stories for all tracked users and send status messages."""
    monitor = InstagramMonitor()
    
    try:
        # Load tracked users
        users = load_users()
        if not users:
            logger.info("No users to check")
            return
            
        # Login to Instagram
        if not await monitor.login_to_instagram():
            logger.error("Failed to login to Instagram")
            return
            
        # Check each subscriber's tracked accounts
        for chat_id, usernames in users.items():
            if not usernames:
                continue
                
            message = "📊 <b>Story Status Report</b>\n\n"
            active_stories = []
            no_stories = []
            
            # Check each username
            for username in usernames:
                try:
                    # Navigate to profile
                    await monitor.page.goto(f"https://www.instagram.com/{username}/")
                    await monitor.page.wait_for_selector('header', timeout=10000)
                    
                    # Check for story ring
                    story_ring = await monitor.page.query_selector('div[role="button"] canvas')
                    if story_ring:
                        active_stories.append(username)
                    else:
                        no_stories.append(username)
                        
                except Exception as e:
                    logger.error(f"Error checking @{username}: {e}")
                    no_stories.append(f"{username} (error)")
                    
            # Build status message
            if active_stories:
                message += "🎭 <b>Active Stories:</b>\n"
                message += "\n".join([f"• @{username}" for username in active_stories])
                message += "\n\n"
                
            if no_stories:
                message += "😴 <b>No Stories:</b>\n"
                message += "\n".join([f"• @{username}" for username in no_stories])
                
            # Send message to subscriber
            if send_telegram_message(chat_id, message):
                logger.info(f"Sent status update to chat {chat_id}")
            else:
                logger.error(f"Failed to send status update to chat {chat_id}")
                
    except Exception as e:
        logger.error(f"Error in check_and_notify: {e}")
    finally:
        await monitor.cleanup_browser()

async def main():
    """Run the story checker."""
    try:
        await check_and_notify()
    except Exception as e:
        logger.error(f"Error in main: {e}")

if __name__ == "__main__":
    asyncio.run(main())