import json
import os

def init_files():
    # Create alert_states directory if it doesn't exist
    if not os.path.exists("alert_states"):
        os.makedirs("alert_states")

    # Initialize users.json if it doesn't exist
    if not os.path.exists("users.json"):
        with open("users.json", "w") as f:
            json.dump({}, f)
        print("Created users.json")

    # Initialize state.json if it doesn't exist
    if not os.path.exists("state.json"):
        with open("state.json", "w") as f:
            json.dump({
                "cookies": [],
                "origins": []
            }, f)
        print("Created state.json")

    # Initialize instagram_session.json if it doesn't exist
    if not os.path.exists("instagram_session.json"):
        with open("instagram_session.json", "w") as f:
            json.dump({
                "last_refresh": "",
                "next_refresh": "",
                "user_agent": ""
            }, f)
        print("Created instagram_session.json")

if __name__ == "__main__":
    init_files() 