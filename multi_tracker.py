import requests
import json
import os

USERS_FILE = "users.json"
BOT_TOKEN = "7569840561:AAHnbeez9FcYFM_IpwyxJ1AwaiqKA7r_jiA"

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def is_new_user(chat_id):
    """Check if a user is new to the bot."""
    users = load_users()
    return chat_id not in users

def add_user(chat_id, username):
    """Add a user to track list. Returns True if added, False if already tracking."""
    users = load_users()
    if chat_id not in users:
        users[chat_id] = []
    
    # Clean username
    username = username.strip().lstrip('@')
    
    if username not in users[chat_id]:
        users[chat_id].append(username)
        save_users(users)
        return True
    return False

def remove_user(chat_id, username):
    """Remove a user from track list. Returns True if removed, False if not found."""
    users = load_users()
    if chat_id in users:
        # Clean username
        username = username.strip().lstrip('@')
        
        if username in users[chat_id]:
            users[chat_id].remove(username)
            if not users[chat_id]:  # If no more tracked users, remove the chat_id
                del users[chat_id]
            save_users(users)
            return True
    return False

def get_tracked_users(chat_id):
    """Get list of users being tracked by a chat_id."""
    users = load_users()
    return users.get(chat_id, [])

def update_users():
    """Update users from Telegram updates."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    response = requests.get(url)
    updates = response.json().get("result", [])
    users = load_users()

    for update in updates:
        try:
            chat_id = str(update["message"]["chat"]["id"])
            text = update["message"]["text"]
            if text.lower().startswith("track "):
                username = text.split(" ", 1)[1].strip()
                if add_user(chat_id, username):
                    print(f"Added {username} for {chat_id}")
        except Exception:
            continue

    save_users(users)

