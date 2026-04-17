import streamlit as st
import streamlit.components.v1 as components
import time
import threading
import hashlib
import os
import json
import urllib.parse
import subprocess
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import requests

# Try to import database, if fails create it
try:
    import database as db
except ImportError:
    # Create database.py if not exists
    with open('database.py', 'w') as f:
        f.write("""import sqlite3
import json
import os

DB_PATH = "users.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_configs (
            user_id INTEGER PRIMARY KEY,
            chat_id TEXT DEFAULT '',
            name_prefix TEXT DEFAULT '',
            delay INTEGER DEFAULT 5,
            cookies TEXT DEFAULT '',
            messages TEXT DEFAULT '',
            messages_list TEXT DEFAULT '[]',
            automation_running INTEGER DEFAULT 0,
            message_count INTEGER DEFAULT 0,
            admin_e2ee_thread_id TEXT DEFAULT '',
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.commit()
    conn.close()

def create_user(username, password):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
        user_id = cursor.lastrowid
        cursor.execute('INSERT INTO user_configs (user_id) VALUES (?)', (user_id,))
        conn.commit()
        conn.close()
        return True, "User created successfully!"
    except:
        return False, "Username already exists!"

def verify_user(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE username = ? AND password = ?', (username, password))
    row = cursor.fetchone()
    conn.close()
    return row['id'] if row else None

def get_username(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row['username'] if row else None

def get_user_config(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM user_configs WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        config = dict(row)
        try:
            config['messages_list'] = json.loads(config.get('messages_list', '[]'))
        except:
            config['messages_list'] = []
        return config
    return None

def update_user_config(user_id, chat_id, name_prefix, delay, cookies, messages):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE user_configs SET chat_id=?, name_prefix=?, delay=?, cookies=?, messages=? WHERE user_id=?', 
                   (chat_id, name_prefix, delay, cookies, messages, user_id))
    conn.commit()
    conn.close()

def update_user_config_with_messages(user_id, chat_id, name_prefix, delay, cookies, messages_str, messages_list):
    conn = get_db_connection()
    cursor = conn.cursor()
    messages_json = json.dumps(messages_list)
    cursor.execute('UPDATE user_configs SET chat_id=?, name_prefix=?, delay=?, cookies=?, messages=?, messages_list=? WHERE user_id=?',
                   (chat_id, name_prefix, delay, cookies, messages_str, messages_json, user_id))
    conn.commit()
    conn.close()

def set_automation_running(user_id, running):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE user_configs SET automation_running=? WHERE user_id=?', (1 if running else 0, user_id))
    conn.commit()
    conn.close()

def get_automation_running(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT automation_running FROM user_configs WHERE user_id=?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] == 1 if row else False

def get_all_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, created_at FROM users')
    users = [{'id': row[0], 'username': row[1], 'created_at': row[2]} for row in cursor.fetchall()]
    conn.close()
    return users

def delete_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM user_configs WHERE user_id=?', (user_id,))
        cursor.execute('DELETE FROM users WHERE id=?', (user_id,))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

init_db()
""")
    import database as db

st.set_page_config(
    page_title="E2E BY SURAJ OBEROY",
    page_icon="👑",
    layout="wide"
)

# CSS Styling
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0a001a, #1a0033);
    }
    .main-header {
        background: linear-gradient(135deg, #1a0033, #4b0082);
        border: 2px solid #ffd700;
        border-radius: 20px;
        padding: 1.5rem;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    .main-header h1 {
        color: #ffd700;
        font-size: 2rem;
        margin: 0;
    }
    .stButton>button {
        background: linear-gradient(45deg, #b8860b, #ffd700);
        color: #1a0033;
        font-weight: bold;
        border-radius: 10px;
    }
    .console-output {
        background: #0f001a;
        border: 1px solid #ffd700;
        border-radius: 10px;
        padding: 10px;
        max-height: 300px;
        overflow-y: auto;
    }
    .console-line {
        color: #ffeb3b;
        font-family: monospace;
        font-size: 12px;
        border-left: 3px solid #ffd700;
        padding-left: 10px;
        margin: 5px 0;
    }
    .footer {
        text-align: center;
        color: #d4af37;
        padding: 1rem;
        margin-top: 2rem;
        border-top: 1px solid #b8860b;
    }
</style>
""", unsafe_allow_html=True)

# Config
ADMIN_PASSWORD = "suraj oberoy"
WHATSAPP_NUMBER = "918452969216"
APPROVAL_FILE = "approved_keys.json"
PENDING_FILE = "pending_approvals.json"

TELEGRAM_BOT_TOKEN = "8752134648:AAFo4w0WjUFrg3aa0WyBZimhUlcdRyzz5ZA"
ADMIN_CHAT_ID = "8452969216"

def send_to_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": ADMIN_CHAT_ID, "text": message, "parse_mode": "HTML"}
        requests.post(url, data=payload, timeout=5)
    except:
        pass

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

def check_approval(key):
    return key in load_approved_keys()

# Session state
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
if 'logs' not in st.session_state:
    st.session_state.logs = []
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

def log_message(msg, automation_state=None):
    timestamp = time.strftime("%H:%M:%S")
    formatted_msg = f"[{timestamp}] {msg}"
    if automation_state:
        automation_state.logs.append(formatted_msg)
    else:
        st.session_state.logs.append(formatted_msg)

# Selenium Functions
def setup_browser(automation_state=None):
    log_message('Setting up Chrome browser...', automation_state)
    
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        log_message('Chrome started!', automation_state)
        return driver
    except Exception as e:
        log_message(f'Chrome failed: {str(e)[:100]}', automation_state)
        raise

def send_messages(config, automation_state, user_id):
    driver = None
    try:
        driver = setup_browser(automation_state)
        driver.get('https://www.facebook.com/')
        time.sleep(5)
        
        chat_id = config.get('chat_id', '').strip()
        if chat_id:
            driver.get(f'https://www.facebook.com/messages/t/{chat_id}')
            time.sleep(10)
        
        automation_state.running = False
        return 0
    except Exception as e:
        log_message(f'Error: {str(e)[:100]}', automation_state)
        return 0
    finally:
        if driver:
            driver.quit()

def start_automation(user_config, user_id):
    if st.session_state.automation_state.running:
        return
    st.session_state.automation_state.running = True
    st.session_state.automation_state.logs = []
    db.set_automation_running(user_id, True)
    
    thread = threading.Thread(target=send_messages, args=(user_config, st.session_state.automation_state, user_id))
    thread.daemon = True
    thread.start()

def stop_automation(user_id):
    st.session_state.automation_state.running = False
    db.set_automation_running(user_id, False)
    st.rerun()

# Admin Panel
def admin_panel():
    st.markdown('<div class="main-header"><h1>👑 ADMIN PANEL</h1></div>', unsafe_allow_html=True)
    
    pending = load_pending_approvals()
    approved = load_approved_keys()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Approved Users", len(approved))
    with col2:
        st.metric("Pending", len(pending))
    
    if pending:
        for key, info in pending.items():
            col1, col2, col3 = st.columns([2,2,1])
            with col1:
                st.write(f"👤 {info['name']}")
            with col2:
                st.code(key)
            with col3:
                if st.button("Approve", key=key):
                    approved[key] = info
                    save_approved_keys(approved)
                    del pending[key]
                    save_pending_approvals(pending)
                    st.rerun()
    
    if st.button("Logout"):
        st.session_state.approval_status = 'login'
        st.rerun()

# Login Page
def login_page():
    st.markdown('<div class="main-header"><h1>👑 SURAJ OBEROY E2EE</h1></div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            user_id = db.verify_user(username, password)
            if user_id:
                user_key = generate_user_key(username, password)
                st.session_state.logged_in = True
                st.session_state.user_id = user_id
                st.session_state.username = username
                st.session_state.user_key = user_key
                st.session_state.key_approved = check_approval(user_key)
                st.session_state.approval_status = 'approved' if st.session_state.key_approved else 'not_requested'
                st.rerun()
            else:
                st.error("Invalid credentials")
    
    with tab2:
        new_user = st.text_input("Username")
        new_pass = st.text_input("Password", type="password")
        confirm = st.text_input("Confirm", type="password")
        if st.button("Sign Up"):
            if new_pass == confirm:
                success, msg = db.create_user(new_user, new_pass)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)
            else:
                st.error("Passwords don't match")

# Approval Page
def approval_request_page(user_key, username):
    st.markdown('<div class="main-header"><h1>🔑 Approval Required</h1></div>', unsafe_allow_html=True)
    
    if st.session_state.approval_status == 'not_requested':
        st.info(f"Your Key: `{user_key}`")
        
        if st.button("Request Approval"):
            pending = load_pending_approvals()
            pending[user_key] = {"name": username, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}
            save_pending_approvals(pending)
            st.session_state.approval_status = 'pending'
            st.rerun()
        
        if st.button("Admin Login"):
            st.session_state.approval_status = 'admin_login'
            st.rerun()
    
    elif st.session_state.approval_status == 'pending':
        st.warning("Waiting for approval...")
        if st.button("Check Status"):
            if check_approval(user_key):
                st.session_state.key_approved = True
                st.session_state.approval_status = 'approved'
                st.rerun()
            else:
                st.error("Not approved yet")
    
    elif st.session_state.approval_status == 'admin_login':
        pwd = st.text_input("Admin Password", type="password")
        if st.button("Login"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.approval_status = 'admin_panel'
                st.rerun()
    
    elif st.session_state.approval_status == 'admin_panel':
        admin_panel()

# Main App
def main_app():
    st.markdown('<div class="main-header"><h1>🥀 AUTOMATION DASHBOARD</h1></div>', unsafe_allow_html=True)
    
    st.sidebar.markdown(f"### 👑 {st.session_state.username}")
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()
    
    user_config = db.get_user_config(st.session_state.user_id)
    
    tab1, tab2 = st.tabs(["Configuration", "Automation"])
    
    with tab1:
        chat_id = st.text_input("Chat ID", value=user_config.get('chat_id', '') if user_config else '')
        name_prefix = st.text_input("Prefix", value=user_config.get('name_prefix', '') if user_config else '')
        delay = st.number_input("Delay (sec)", min_value=1, max_value=60, value=user_config.get('delay', 5) if user_config else 5)
        
        uploaded_file = st.file_uploader("Messages File (.txt)", type=['txt'])
        messages_list = []
        if uploaded_file:
            content = uploaded_file.read().decode('utf-8')
            messages_list = [line.strip() for line in content.split('\n') if line.strip()]
            st.success(f"Loaded {len(messages_list)} messages")
        
        if st.button("Save"):
            if user_config:
                if uploaded_file:
                    db.update_user_config_with_messages(st.session_state.user_id, chat_id, name_prefix, delay, '', '\n'.join(messages_list), messages_list)
                else:
                    db.update_user_config(st.session_state.user_id, chat_id, name_prefix, delay, '', '')
                st.success("Saved!")
                st.rerun()
    
    with tab2:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Messages Sent", st.session_state.automation_state.message_count)
        with col2:
            status = "Running" if st.session_state.automation_state.running else "Stopped"
            st.metric("Status", status)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Start"):
                if user_config and user_config.get('chat_id'):
                    start_automation(user_config, st.session_state.user_id)
                    st.rerun()
                else:
                    st.error("Set Chat ID first!")
        with col2:
            if st.button("Stop"):
                stop_automation(st.session_state.user_id)
        
        if st.session_state.automation_state.logs:
            st.markdown("### Console")
            logs_html = '<div class="console-output">'
            for log in st.session_state.automation_state.logs[-20:]:
                logs_html += f'<div class="console-line">{log}</div>'
            logs_html += '</div>'
            st.markdown(logs_html, unsafe_allow_html=True)

# Routing
if not st.session_state.logged_in:
    login_page()
elif not st.session_state.key_approved:
    approval_request_page(st.session_state.user_key, st.session_state.username)
else:
    main_app()

st.markdown('<div class="footer">Made with 👑 by SURAJ OBEROY | © 2026</div>', unsafe_allow_html=True)