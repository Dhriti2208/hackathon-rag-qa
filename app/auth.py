"""
SIMPLE LOGIN SYSTEM + FEEDBACK TRACKING

Stores usernames and (hashed) passwords in data/users.json.
Stores each user's chat history in data/chat_history/{username}.json
Stores feedback (thumbs up/down) in data/feedback.json

NOTE: This is a simple, hackathon-appropriate login system - passwords
are hashed with SHA-256 but there's no rate-limiting, email verification,
etc. That's fine for a demo/MVP, not for production.
"""

import json
import os
import hashlib

USERS_FILE = "data/users.json"
HISTORY_FOLDER = "data/chat_history"
FEEDBACK_FILE = "data/feedback.json"


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_users(users_dict):
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users_dict, f, ensure_ascii=False, indent=2)


def register_user(username, password):
    users = load_users()

    if username in users:
        return False, "Username already exists. Please log in instead."

    users[username] = hash_password(password)
    save_users(users)
    return True, "Account created successfully!"


def login_user(username, password):
    users = load_users()

    if username not in users:
        return False, "No account found with this username. Please register first."

    if users[username] != hash_password(password):
        return False, "Incorrect password."

    return True, "Login successful!"


def save_history(username, messages):
    os.makedirs(HISTORY_FOLDER, exist_ok=True)
    filepath = os.path.join(HISTORY_FOLDER, f"{username}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)


def load_history(username):
    filepath = os.path.join(HISTORY_FOLDER, f"{username}.json")
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_feedback(username, question, answer, feedback_type):
    """feedback_type should be 'up' or 'down'"""
    os.makedirs(os.path.dirname(FEEDBACK_FILE), exist_ok=True)

    records = []
    if os.path.exists(FEEDBACK_FILE):
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            records = json.load(f)

    records.append({
        "username": username,
        "question": question,
        "answer": answer,
        "feedback": feedback_type
    })

    with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
