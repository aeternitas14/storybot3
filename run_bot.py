import os
import json
import logging
import re
from typing import Dict, List, Optional, Any
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from instagram_monitor import InstagramMonitor
import asyncio

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize bot and application
bot_token = os.getenv('BOT_TOKEN')
ig_username = os.getenv('IG_USERNAME')
ig_password = os.getenv('IG_PASSWORD')
if not bot_token:
    raise ValueError("BOT_TOKEN environment variable is required")

application = Application.builder().token(bot_token).build()

# Initialize Instagram monitor
monitor = InstagramMonitor(ig_username=ig_username, ig_password=ig_password)


def load_users() -> Dict[str, List[str]]:
    """Load users from the users file."""
    if not os.path.exists("users.json"):
        return {}
    try:
        with open("users.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, PermissionError) as e:
        logger.error(f"Error loading users: {e}")
        return {}


def save_users(users: Dict[str, List[str]]) -> None:
    """Save users to the users file."""
    try:
        with open("users.json", "w") as f:
            json.dump(users, f)
    except (PermissionError, IOError) as e:
        logger.error(f"Error saving users: {e}")


def validate_username(username: str) -> bool:
    """Validate Instagram username format."""
    if not username or not username.strip():
        return False
    username = username.strip().lower()
    # Instagram usernames can only contain letters, numbers, periods, and underscores
    return bool(re.match(r'^[a-zA-Z0-9._]+$', username))


def add_user(chat_id: str, username: str) -> bool:
    """Add a user to the tracking list."""
    if not validate_username(username):
        return False

    users = load_users()
    if str(chat_id) not in users:
        users[str(chat_id)] = []
    if username not in users[str(chat_id)]:
        users[str(chat_id)].append(username)
        save_users(users)
        return True
    return False


def remove_user(chat_id: str, username: str) -> bool:
    """Remove a user from the tracking list."""
    if not validate_username(username):
        return False

    users = load_users()
    if str(chat_id) in users and username in users[str(chat_id)]:
        users[str(chat_id)].remove(username)
        if not users[str(chat_id)]:
            del users[str(chat_id)]
        save_users(users)
        return True
    return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command."""
    chat_id = update.effective_chat.id
    await context.bot.send_message(
        chat_id=chat_id,
        text="🎭 <b>Welcome to the Instagram Story Stalker Bot!</b>\n\n"
        "Oh great, another person who can't resist the urge to know what others are doing 24/7. Don't worry, we won't judge... much. 😏\n\n"
        "Here's what you can do with me (because apparently, you have nothing better to do):\n\n"
        "🔍 <b>Track Stories:</b>\n"
        "/track &lt;username&gt; - Start stalking someone's stories\n"
        "Example: /track instagram\n\n"
        "📥 <b>Download Stories:</b>\n"
        "/download &lt;username&gt; - Download someone's current story\n"
        "Example: /download kimkardashian\n\n"
        "🚫 <b>Stop Stalking:</b>\n"
        "/untrack &lt;username&gt; - Stop being creepy (or at least pretend to)\n\n"
        "📋 <b>Your Stalking List:</b>\n"
        "/list - See who you're currently obsessing over\n\n"
        "📊 <b>Stalking Stats:</b>\n"
        "/stats - Check how much of your life you've wasted here\n\n"
        "🏆 <b>Stalking Level:</b>\n"
        "/level - See how deep into the stalking rabbit hole you are\n\n"
        "🔥 <b>Get Roasted:</b>\n"
        "/roast - Get roasted for your questionable life choices\n\n"
        "🎯 <b>Pro Tips:</b>\n"
        "/tips - Learn how to be a better stalker (we're not proud of this)\n\n"
        "🏅 <b>Stalking Achievements:</b>\n"
        "/achievements - Collect badges for your dedication to being nosy\n\n"
        "❓ <b>Need Help?</b>\n"
        "/help - Get this message again (because you probably forgot already)\n\n"
        "<i>Remember: Just because you can stalk someone's stories doesn't mean you should... but who are we to stop you? 🤷‍♂️</i>",
        parse_mode="HTML")


async def track(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /track command."""
    chat_id = update.effective_chat.id
    if not context.args:
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ Please provide an Instagram username to track.\n"
            "Example: /track instagram",
            parse_mode="HTML")
        return

    username = context.args[0].lower()
    if not validate_username(username):
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ Invalid Instagram username format.\n"
            "Usernames can only contain letters, numbers, periods, and underscores.",
            parse_mode="HTML")
        return

    if add_user(chat_id, username):
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"✅ Now tracking @{username}!\n"
            "You'll be notified when they post new stories. 🎭",
            parse_mode="HTML")
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"ℹ️ You're already tracking @{username}!",
            parse_mode="HTML")


async def untrack(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /untrack command."""
    chat_id = update.effective_chat.id
    if not context.args:
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ Please provide an Instagram username to stop tracking.\n"
            "Example: /untrack instagram",
            parse_mode="HTML")
        return

    username = context.args[0].lower()
    if not validate_username(username):
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ Invalid Instagram username format.\n"
            "Usernames can only contain letters, numbers, periods, and underscores.",
            parse_mode="HTML")
        return

    if remove_user(chat_id, username):
        await context.bot.send_message(chat_id=chat_id,
                                       text=f"✅ Stopped tracking @{username}.",
                                       parse_mode="HTML")
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"ℹ️ You weren't tracking @{username}.",
            parse_mode="HTML")


async def list_tracked(update: Update,
                       context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /list command."""
    chat_id = update.effective_chat.id
    users = load_users()
    tracked = users.get(str(chat_id), [])

    if not tracked:
        await context.bot.send_message(
            chat_id=chat_id,
            text="ℹ️ You're not tracking any Instagram accounts yet.\n"
            "Use /track &lt;username&gt; to start tracking.",
            parse_mode="HTML")
    else:
        message = "📋 <b>You're tracking these Instagram accounts:</b>\n\n"
        message += "\n".join([f"• @{username}" for username in tracked])
        await context.bot.send_message(chat_id=chat_id,
                                       text=message,
                                       parse_mode="HTML")


async def download(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /download command."""
    chat_id = update.effective_chat.id
    if not context.args:
        await context.bot.send_message(
            chat_id=chat_id,
            text=
            "❌ Please provide an Instagram username to download stories from.\n"
            "Example: /download kimkardashian",
            parse_mode="HTML")
        return

    username = context.args[0].lower()
    if not validate_username(username):
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ Invalid Instagram username format.\n"
            "Usernames can only contain letters, numbers, periods, and underscores.",
            parse_mode="HTML")
        return

    # Send initial message
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"🔄 Checking stories for @{username}...\n"
        "This might take a moment while I do my sneaky business. 👀",
        parse_mode="HTML")

    try:
        # Initialize monitor
        monitor = InstagramMonitor()

        # Login to Instagram
        if not await monitor.login_to_instagram():
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Failed to login to Instagram. Please try again later.",
                parse_mode="HTML")
            return

        # Navigate to profile
        await monitor.page.goto(f"https://www.instagram.com/{username}/")
        await monitor.page.wait_for_selector('header', timeout=10000)

        # Check for story ring
        story_ring = await monitor.page.query_selector(
            'div[role="button"] canvas')
        if not story_ring:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"😴 No active stories found for @{username}.\n\n"
                "Your collection of sadness is empty. Maybe they're:\n"
                "• Living their best life offline (unlike you)\n"
                "• Actually being productive (unlike you)\n"
                "• Just not interested in sharing their life with random stalkers (like you)\n\n"
                "Try again later when they're actually doing something interesting. Or maybe... get a life? 🤷‍♂️",
                parse_mode="HTML")
            return

        # Click story ring and wait for story viewer
        await story_ring.click()
        await monitor.page.wait_for_selector('div[role="dialog"]',
                                             timeout=5000)

        # Get story container
        story_element = await monitor.page.query_selector('div[role="dialog"]')
        if not story_element:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ Could not open stories for @{username}.\n"
                "Maybe they're private or blocked you? 🤔",
                parse_mode="HTML")
            return

        # Process story content
        story_content = await monitor.get_story_content(story_element)
        if not story_content:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ Could not download story content for @{username}.\n"
                "Instagram might be onto us... 👮‍♂️",
                parse_mode="HTML")
            return

        # Send the content
        if story_content['type'] == 'video':
            # For videos, send both the video and a screenshot
            await context.bot.send_video(
                chat_id=chat_id,
                video=story_content['media_content'],
                caption=f"🎥 Story from @{username}\n"
                "Here's your stolen content, you sneaky stalker! 😏",
                parse_mode="HTML")
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=story_content['screenshot'],
                caption=
                "📸 Screenshot of the video (in case you're too lazy to watch it)",
                parse_mode="HTML")
        else:
            # For images, just send the image
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=story_content['media_content'],
                caption=f"🖼️ Story from @{username}\n"
                "Here's your stolen content, you sneaky stalker! 😏",
                parse_mode="HTML")

        await context.bot.send_message(
            chat_id=chat_id,
            text="✅ Story downloaded successfully!\n"
            "Don't forget to delete this message if you don't want evidence of your stalking habits. 😉",
            parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error downloading story for @{username}: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ Error downloading story: {str(e)}\n"
            "Maybe try again later? Or maybe you should just... stop stalking? 🤷‍♂️",
            parse_mode="HTML")
    finally:
        await monitor.cleanup_browser()


async def error_handler(update: Optional[Update],
                        context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Update {update} caused error {context.error}")
    import traceback
    traceback.print_exc()  # ← shows the real error in your Replit logs

    if update and update.effective_chat:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ An error occurred. Please try again later.",
            parse_mode="HTML")


# Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("track", track))
application.add_handler(CommandHandler("untrack", untrack))
application.add_handler(CommandHandler("list", list_tracked))
application.add_handler(CommandHandler("download", download))
application.add_handler(
    CommandHandler(
        "stats", lambda u, c: c.bot.send_message(u.effective_chat.id,
                                                 "📊 Stats coming soon!")))
application.add_handler(
    CommandHandler(
        "level", lambda u, c: c.bot.send_message(
            u.effective_chat.id, "🏆 Level system coming soon!")))
application.add_handler(
    CommandHandler(
        "roast", lambda u, c: c.bot.send_message(
            u.effective_chat.id, "🔥 Roasting system coming soon!")))
application.add_handler(
    CommandHandler(
        "tips", lambda u, c: c.bot.send_message(u.effective_chat.id,
                                                "🎯 Tips coming soon!")))
application.add_handler(
    CommandHandler(
        "achievements", lambda u, c: c.bot.send_message(
            u.effective_chat.id, "🏅 Achievements coming soon!")))
application.add_handler(CommandHandler("help",
                                       start))  # Reuse start command for help
application.add_error_handler(error_handler)

import requests


def run_bot():
    print("🤖 StoryBot v1.0 – Polling mode initialized")

    try:
        # Delete webhook to enable polling
        requests.get(f"https://api.telegram.org/bot{bot_token}/deleteWebhook",
                     params={'drop_pending_updates': True})
        application.initialize()
        application.run_polling(drop_pending_updates=True)
    except Exception as e:
        logger.error(f"Polling failed: {e}")
    finally:
        print("Bot stopped.")


if __name__ == '__main__':
    run_bot()
