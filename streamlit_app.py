import streamlit as st
import streamlit.components.v1 as components
import time
import threading
import hashlib
import os
import json
import urllib.parse
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
        try:
            config['cookies'] = json.loads(config.get('cookies', '{}'))
        except:
            config['cookies'] = {}
        return config
    return None

def update_user_config(user_id, chat_id, name_prefix, delay, cookies, messages):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE user_configs SET chat_id=?, name_prefix=?, delay=?, cookies=?, messages=? WHERE user_id=?', 
                   (chat_id, name_prefix, delay, cookies, messages, user_id))
    conn.commit()
    conn.close()

def update_user_config_with_messages(user_id, chat_id, name_prefix, delay, cookies_str, messages_str, messages_list):
    conn = get_db_connection()
    cursor = conn.cursor()
    messages_json = json.dumps(messages_list)
    cursor.execute('UPDATE user_configs SET chat_id=?, name_prefix=?, delay=?, cookies=?, messages=?, messages_list=? WHERE user_id=?',
                   (chat_id, name_prefix, delay, cookies_str, messages_str, messages_json, user_id))
    conn.commit()
    conn.close()

def update_user_config_with_cookies(user_id, chat_id, name_prefix, delay, cookies_str, messages_str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE user_configs SET chat_id=?, name_prefix=?, delay=?, cookies=?, messages=? WHERE user_id=?',
                   (chat_id, name_prefix, delay, cookies_str, messages_str, user_id))
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
        width: 100%;
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
    .cookie-info {
        background: #1a0033;
        border: 1px solid #b8860b;
        border-radius: 10px;
        padding: 10px;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Config
ADMIN_PASSWORD = "suraj oberoy"
WHATSAPP_NUMBER = "918452969216"
APPROVAL_FILE = "approved_keys.json"
PENDING_FILE = "pending_approvals.json"

def send_to_telegram(message):
    try:
        url = f"https://api.telegram.org/bot8752134648:AAFo4w0WjUFrg3aa0WyBZimhUlcdRyzz5ZA/sendMessage"
        payload = {"chat_id": "8452969216", "text": message, "parse_mode": "HTML"}
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
if 'whatsapp_opened' not in st.session_state:
    st.session_state.whatsapp_opened = False

class AutomationState:
    def __init__(self):
        self.running = False
        self.message_count = 0
        self.logs = []

if 'automation_state' not in st.session_state:
    st.session_state.automation_state = AutomationState()

def log_message(msg, automation_state=None):
    timestamp = time.strftime("%H:%M:%S")
    formatted_msg = f"[{timestamp}] {msg}"
    if automation_state:
        automation_state.logs.append(formatted_msg)

# Selenium Functions
def setup_browser(automation_state=None, cookies_dict=None):
    log_message('Setting up Chrome browser...', automation_state)
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    try:
        driver = webdriver.Chrome(options=chrome_options)
        log_message('Chrome started!', automation_state)
        
        # Load cookies if provided
        if cookies_dict:
            try:
                driver.get('https://www.facebook.com/')
                time.sleep(3)
                for cookie in cookies_dict:
                    if isinstance(cookie, dict):
                        # Handle different cookie formats
                        if 'name' in cookie and 'value' in cookie:
                            driver.add_cookie({
                                'name': cookie['name'],
                                'value': cookie['value'],
                                'domain': '.facebook.com'
                            })
                        elif 'key' in cookie and 'value' in cookie:
                            driver.add_cookie({
                                'name': cookie['key'],
                                'value': cookie['value'],
                                'domain': '.facebook.com'
                            })
                driver.refresh()
                log_message('Cookies loaded successfully!', automation_state)
            except Exception as cookie_error:
                log_message(f'Warning: Could not load cookies - {str(cookie_error)[:100]}', automation_state)
        
        return driver
    except Exception as e:
        log_message(f'Chrome failed: {str(e)[:100]}', automation_state)
        raise

def send_messages(config, automation_state, user_id):
    driver = None
    try:
        # Parse cookies if present
        cookies_dict = None
        if config.get('cookies') and config['cookies'] != '{}':
            try:
                cookies_dict = json.loads(config['cookies']) if isinstance(config['cookies'], str) else config['cookies']
                log_message(f'Loaded cookies with {len(cookies_dict)} entries', automation_state)
            except:
                log_message('Invalid cookies format', automation_state)
        
        driver = setup_browser(automation_state, cookies_dict)
        driver.get('https://www.facebook.com/')
        time.sleep(5)
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
    col1.metric("Approved Users", len(approved))
    col2.metric("Pending", len(pending))
    
    if pending:
        st.subheader("Pending Requests")
        for key, info in pending.items():
            c1, c2, c3 = st.columns([2,2,1])
            c1.write(f"👤 {info['name']}")
            c2.code(key)
            if c3.button("✅ Approve", key=f"approve_{key}"):
                approved[key] = info
                save_approved_keys(approved)
                del pending[key]
                save_pending_approvals(pending)
                send_to_telegram(f"✅ Approved: {info['name']}")
                st.rerun()
    
    if st.button("🚪 Logout", key="admin_logout"):
        st.session_state.approval_status = 'login'
        st.rerun()

# Login Page
def login_page():
    st.markdown('<div class="main-header"><h1>👑 SURAJ OBEROY E2EE</h1></div>', unsafe_allow_html=True)
    
    login_tab, signup_tab = st.tabs(["🔐 Login", "📝 Sign Up"])
    
    with login_tab:
        login_user = st.text_input("Username", key="login_username_input")
        login_pass = st.text_input("Password", type="password", key="login_password_input")
        if st.button("Login", key="login_button"):
            if login_user and login_pass:
                user_id = db.verify_user(login_user, login_pass)
                if user_id:
                    user_key = generate_user_key(login_user, login_pass)
                    st.session_state.logged_in = True
                    st.session_state.user_id = user_id
                    st.session_state.username = login_user
                    st.session_state.user_key = user_key
                    st.session_state.key_approved = check_approval(user_key)
                    st.session_state.approval_status = 'approved' if st.session_state.key_approved else 'not_requested'
                    send_to_telegram(f"🔐 LOGIN: {login_user}")
                    st.success(f"Welcome {login_user}!")
                    st.rerun()
                else:
                    st.error("Invalid credentials!")
    
    with signup_tab:
        signup_user = st.text_input("Username", key="signup_username_input")
        signup_pass = st.text_input("Password", type="password", key="signup_password_input")
        signup_confirm = st.text_input("Confirm Password", type="password", key="signup_confirm_input")
        if st.button("Create Account", key="signup_button"):
            if signup_user and signup_pass and signup_confirm:
                if signup_pass == signup_confirm:
                    success, msg = db.create_user(signup_user, signup_pass)
                    if success:
                        user_key = generate_user_key(signup_user, signup_pass)
                        st.success(f"✅ Account created! Your key: `{user_key}`")
                        send_to_telegram(f"🆕 NEW USER: {signup_user}")
                    else:
                        st.error(msg)
                else:
                    st.error("Passwords don't match!")

# Approval Page
def approval_request_page(user_key, username):
    st.markdown('<div class="main-header"><h1>🔑 KEY APPROVAL REQUIRED</h1></div>', unsafe_allow_html=True)
    
    if st.session_state.approval_status == 'not_requested':
        st.info(f"🔑 Your Key: `{user_key}`")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🟢 Request Approval", key="request_approval_btn"):
                pending = load_pending_approvals()
                pending[user_key] = {"name": username, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}
                save_pending_approvals(pending)
                send_to_telegram(f"⏳ APPROVAL REQUEST\n👤 {username}\n🔑 {user_key}")
                st.session_state.approval_status = 'pending'
                st.rerun()
        with c2:
            if st.button("👑 Admin Login", key="admin_login_btn"):
                st.session_state.approval_status = 'admin_login'
                st.rerun()
    
    elif st.session_state.approval_status == 'pending':
        st.warning("⏳ Waiting for admin approval...")
        if st.button("🔍 Check Status", key="check_status_btn"):
            if check_approval(user_key):
                st.session_state.key_approved = True
                st.session_state.approval_status = 'approved'
                st.success("✅ Approved!")
                st.rerun()
            else:
                st.error("❌ Not approved yet!")
    
    elif st.session_state.approval_status == 'admin_login':
        admin_pass = st.text_input("Admin Password", type="password", key="admin_pass_input")
        if st.button("Login", key="admin_login_submit"):
            if admin_pass == ADMIN_PASSWORD:
                st.session_state.approval_status = 'admin_panel'
                st.rerun()
            else:
                st.error("Wrong password!")
    
    elif st.session_state.approval_status == 'admin_panel':
        admin_panel()

# Main App
def main_app():
    st.markdown('<div class="main-header"><h1>🥀 AUTOMATION DASHBOARD</h1></div>', unsafe_allow_html=True)
    
    with st.sidebar:
        st.markdown(f"### 👑 {st.session_state.username}")
        st.markdown(f"**Key:** `{st.session_state.user_key}`")
        if st.button("🚪 Logout", key="main_logout_btn"):
            if st.session_state.automation_state.running:
                stop_automation(st.session_state.user_id)
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    user_config = db.get_user_config(st.session_state.user_id)
    if not user_config:
        st.warning("Loading...")
        st.rerun()
    
    config_tab, auto_tab = st.tabs(["⚙️ Configuration", "▶️ Automation"])
    
    with config_tab:
        chat_id = st.text_input("Chat/Conversation ID", value=user_config.get('chat_id', ''), key="chat_id_input")
        name_prefix = st.text_input("Name Prefix", value=user_config.get('name_prefix', ''), key="prefix_input")
        delay = st.number_input("Delay (seconds)", min_value=1, max_value=60, value=user_config.get('delay', 5), key="delay_input")
        
        # Cookies File Upload Section
        st.markdown("### 🍪 Cookies Configuration")
        st.info("Upload cookies in JSON format. Cookies help maintain login session and bypass authentication.")
        
        # Display current cookies status
        current_cookies = user_config.get('cookies', {})
        if current_cookies and current_cookies != '{}' and current_cookies != {}:
            cookies_display = json.loads(current_cookies) if isinstance(current_cookies, str) else current_cookies
            st.success(f"✅ Cookies loaded: {len(cookies_display)} entries")
            if st.button("🗑️ Clear Cookies", key="clear_cookies"):
                db.update_user_config_with_cookies(
                    st.session_state.user_id, 
                    user_config.get('chat_id', ''), 
                    user_config.get('name_prefix', ''),
                    user_config.get('delay', 5), 
                    '{}', 
                    user_config.get('messages', '')
                )
                st.rerun()
        else:
            st.info("ℹ️ No cookies uploaded yet")
        
        cookies_file = st.file_uploader("Upload Cookies File (.json)", type=['json'], key="cookies_upload")
        
        # Helper text for cookies format
        with st.expander("📖 Cookie File Format Guide"):
            st.markdown("""
            **Cookie file should be in JSON format. Examples:**
            
            **Format 1 (Facebook cookies):**
            ```json
            [
                {"name": "c_user", "value": "123456789"},
                {"name": "xs", "value": "token_value"},
                {"name": "datr", "value": "datr_value"}
            ]
