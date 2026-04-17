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
    page_icon="💀",
    layout="wide"
)

# HACKER THEME CSS - Black & White / Matrix Style
st.markdown("""
<style>
    /* Main background - Pure Black */
    .stApp {
        background: #000000 !important;
    }
    
    /* Main container */
    .main .block-container {
        background: #0a0a0a !important;
        border: 1px solid #00ff00 !important;
        border-radius: 5px !important;
        padding: 20px !important;
    }
    
    /* Header Style - Hacker Style */
    .main-header {
        background: #000000 !important;
        border: 2px solid #00ff00 !important;
        border-radius: 5px !important;
        padding: 1.5rem !important;
        text-align: center !important;
        margin-bottom: 1.5rem !important;
        box-shadow: 0 0 20px rgba(0, 255, 0, 0.2) !important;
    }
    
    .main-header h1 {
        color: #00ff00 !important;
        font-family: 'Courier New', monospace !important;
        font-size: 2rem !important;
        margin: 0 !important;
        text-shadow: 0 0 10px #00ff00 !important;
        letter-spacing: 2px !important;
    }
    
    .main-header p {
        color: #00ff00 !important;
        font-family: 'Courier New', monospace !important;
        font-size: 0.8rem !important;
        opacity: 0.8 !important;
    }
    
    /* Buttons - Hacker Style */
    .stButton>button {
        background: #000000 !important;
        color: #00ff00 !important;
        border: 2px solid #00ff00 !important;
        border-radius: 0px !important;
        font-family: 'Courier New', monospace !important;
        font-weight: bold !important;
        transition: all 0.3s ease !important;
        width: 100% !important;
        text-transform: uppercase !important;
        letter-spacing: 2px !important;
    }
    
    .stButton>button:hover {
        background: #00ff00 !important;
        color: #000000 !important;
        border-color: #00ff00 !important;
        box-shadow: 0 0 20px #00ff00 !important;
        transform: scale(1.02) !important;
    }
    
    /* Input Fields - Hacker Style */
    .stTextInput>div>div>input,
    .stTextArea>div>div>textarea,
    .stNumberInput>div>div>input {
        background: #0a0a0a !important;
        border: 1px solid #00ff00 !important;
        border-radius: 0px !important;
        color: #00ff00 !important;
        font-family: 'Courier New', monospace !important;
    }
    
    .stTextInput>div>div>input:focus,
    .stTextArea>div>div>textarea:focus {
        border-color: #00ff00 !important;
        box-shadow: 0 0 10px rgba(0, 255, 0, 0.5) !important;
    }
    
    /* Labels */
    label {
        color: #00ff00 !important;
        font-family: 'Courier New', monospace !important;
        font-weight: bold !important;
    }
    
    /* Tabs - Hacker Style */
    .stTabs [data-baseweb="tab-list"] {
        background: #000000 !important;
        border: 1px solid #00ff00 !important;
        border-radius: 0px !important;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: #000000 !important;
        color: #00ff00 !important;
        font-family: 'Courier New', monospace !important;
        border-radius: 0px !important;
    }
    
    .stTabs [aria-selected="true"] {
        background: #00ff00 !important;
        color: #000000 !important;
    }
    
    /* Metrics - Hacker Style */
    [data-testid="stMetricValue"] {
        color: #00ff00 !important;
        font-family: 'Courier New', monospace !important;
        font-size: 2rem !important;
        text-shadow: 0 0 5px #00ff00 !important;
    }
    
    [data-testid="stMetricLabel"] {
        color: #00ff00 !important;
        font-family: 'Courier New', monospace !important;
    }
    
    /* Console Output - Hacker Style */
    .console-output {
        background: #000000 !important;
        border: 2px solid #00ff00 !important;
        border-radius: 0px !important;
        padding: 15px !important;
        max-height: 400px !important;
        overflow-y: auto !important;
        font-family: 'Courier New', monospace !important;
    }
    
    .console-line {
        color: #00ff00 !important;
        font-family: 'Courier New', monospace !important;
        font-size: 12px !important;
        border-left: 3px solid #00ff00 !important;
        padding-left: 10px !important;
        margin: 5px 0 !important;
    }
    
    /* Sidebar - Hacker Style */
    [data-testid="stSidebar"] {
        background: #000000 !important;
        border-right: 2px solid #00ff00 !important;
    }
    
    [data-testid="stSidebar"] * {
        color: #00ff00 !important;
        font-family: 'Courier New', monospace !important;
    }
    
    /* Success/Error/Warning Messages */
    .stAlert {
        border-radius: 0px !important;
    }
    
    .stAlert [data-testid="stMarkdownContainer"] {
        font-family: 'Courier New', monospace !important;
    }
    
    /* File Uploader */
    .stFileUploader {
        border: 1px dashed #00ff00 !important;
        background: #0a0a0a !important;
    }
    
    /* Footer */
    .footer {
        text-align: center !important;
        color: #00ff00 !important;
        font-family: 'Courier New', monospace !important;
        padding: 1rem !important;
        margin-top: 2rem !important;
        border-top: 1px solid #00ff00 !important;
        opacity: 0.7 !important;
    }
    
    /* Scrollbar - Hacker Style */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #000000;
        border: 1px solid #00ff00;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #00ff00;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #00ff00;
        box-shadow: 0 0 10px #00ff00;
    }
    
    /* Select Box */
    .stSelectbox div[data-baseweb="select"] {
        background: #0a0a0a !important;
        border: 1px solid #00ff00 !important;
    }
    
    /* Code blocks */
    code {
        color: #00ff00 !important;
        background: #0a0a0a !important;
        border: 1px solid #00ff00 !important;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: #0a0a0a !important;
        border: 1px solid #00ff00 !important;
        color: #00ff00 !important;
        font-family: 'Courier New', monospace !important;
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
def setup_browser(automation_state=None):
    log_message('Initializing HACK-MODE browser...', automation_state)
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    try:
        driver = webdriver.Chrome(options=chrome_options)
        log_message('[✓] Chrome exploited successfully!', automation_state)
        return driver
    except Exception as e:
        log_message(f'[✗] Exploit failed: {str(e)[:100]}', automation_state)
        raise

def send_messages(config, automation_state, user_id):
    driver = None
    try:
        driver = setup_browser(automation_state)
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
    st.markdown('<div class="main-header"><h1>💀 ADMIN PANEL [ROOT ACCESS] 💀</h1><p># HACK THE PLANET</p></div>', unsafe_allow_html=True)
    pending = load_pending_approvals()
    approved = load_approved_keys()
    
    col1, col2 = st.columns(2)
    col1.metric("APPROVED USERS", len(approved))
    col2.metric("PENDING REQUESTS", len(pending))
    
    if pending:
        st.markdown("### 📡 PENDING REQUESTS")
        for key, info in pending.items():
            c1, c2, c3 = st.columns([2,2,1])
            c1.write(f"👤 {info['name']}")
            c2.code(key)
            if c3.button("✅ APPROVE", key=f"approve_{key}"):
                approved[key] = info
                save_approved_keys(approved)
                del pending[key]
                save_pending_approvals(pending)
                send_to_telegram(f"✅ Approved: {info['name']}")
                st.rerun()
    
    if st.button("🚪 EXIT ROOT MODE", key="admin_logout"):
        st.session_state.approval_status = 'login'
        st.rerun()

# Login Page
def login_page():
    st.markdown('<div class="main-header"><h1>💀 SURAJ OBEROY E2EE [BLACK EDITION] 💀</h1><p># ACCESS GRANTED OR DIE TRYING</p></div>', unsafe_allow_html=True)
    
    login_tab, signup_tab = st.tabs(["🔐 LOGIN", "📝 SIGN UP"])
    
    with login_tab:
        login_user = st.text_input("USERNAME", key="login_username_input")
        login_pass = st.text_input("PASSWORD", type="password", key="login_password_input")
        if st.button("LOGIN", key="login_button"):
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
                    st.success(f"WELCOME {login_user.upper()}!")
                    st.rerun()
                else:
                    st.error("ACCESS DENIED!")
    
    with signup_tab:
        signup_user = st.text_input("USERNAME", key="signup_username_input")
        signup_pass = st.text_input("PASSWORD", type="password", key="signup_password_input")
        signup_confirm = st.text_input("CONFIRM PASSWORD", type="password", key="signup_confirm_input")
        if st.button("CREATE ACCOUNT", key="signup_button"):
            if signup_user and signup_pass and signup_confirm:
                if signup_pass == signup_confirm:
                    success, msg = db.create_user(signup_user, signup_pass)
                    if success:
                        user_key = generate_user_key(signup_user, signup_pass)
                        st.success(f"✅ ACCOUNT CREATED! YOUR KEY: `{user_key}`")
                        send_to_telegram(f"🆕 NEW USER: {signup_user}")
                    else:
                        st.error(msg)
                else:
                    st.error("PASSWORDS DO NOT MATCH!")

# Approval Page
def approval_request_page(user_key, username):
    st.markdown('<div class="main-header"><h1>🔑 KEY APPROVAL REQUIRED</h1><p># WAITING FOR ROOT ACCESS</p></div>', unsafe_allow_html=True)
    
    if st.session_state.approval_status == 'not_requested':
        st.info(f"🔑 YOUR KEY: `{user_key}`")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🟢 REQUEST ACCESS", key="request_approval_btn"):
                pending = load_pending_approvals()
                pending[user_key] = {"name": username, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}
                save_pending_approvals(pending)
                send_to_telegram(f"⏳ APPROVAL REQUEST\n👤 {username}\n🔑 {user_key}")
                st.session_state.approval_status = 'pending'
                st.rerun()
        with c2:
            if st.button("👑 ROOT ACCESS", key="admin_login_btn"):
                st.session_state.approval_status = 'admin_login'
                st.rerun()
    
    elif st.session_state.approval_status == 'pending':
        st.warning("⏳ WAITING FOR ROOT APPROVAL...")
        if st.button("🔍 CHECK STATUS", key="check_status_btn"):
            if check_approval(user_key):
                st.session_state.key_approved = True
                st.session_state.approval_status = 'approved'
                st.success("✅ ACCESS GRANTED!")
                st.rerun()
            else:
                st.error("❌ ACCESS DENIED!")
    
    elif st.session_state.approval_status == 'admin_login':
        admin_pass = st.text_input("ROOT PASSWORD", type="password", key="admin_pass_input")
        if st.button("AUTHENTICATE", key="admin_login_submit"):
            if admin_pass == ADMIN_PASSWORD:
                st.session_state.approval_status = 'admin_panel'
                st.rerun()
            else:
                st.error("ACCESS DENIED!")
    
    elif st.session_state.approval_status == 'admin_panel':
        admin_panel()

# Main App
def main_app():
    st.markdown('<div class="main-header"><h1>💀 AUTOMATION DASHBOARD [E2EE MODE] 💀</h1><p># SYSTEM READY FOR DEPLOYMENT</p></div>', unsafe_allow_html=True)
    
    with st.sidebar:
        st.markdown(f"### 💀 {st.session_state.username.upper()}")
        st.markdown(f"**KEY:** `{st.session_state.user_key}`")
        st.markdown("---")
        st.markdown("### SYSTEM STATUS")
        st.markdown("🟢 ACTIVE" if st.session_state.automation_state.running else "🔴 STANDING BY")
        st.markdown("---")
        if st.button("🚪 LOGOUT", key="main_logout_btn"):
            if st.session_state.automation_state.running:
                stop_automation(st.session_state.user_id)
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    user_config = db.get_user_config(st.session_state.user_id)
    if not user_config:
        st.warning("LOADING CONFIGURATION...")
        st.rerun()
    
    config_tab, auto_tab = st.tabs(["⚙️ CONFIGURATION", "▶️ AUTOMATION"])
    
    with config_tab:
        chat_id = st.text_input("CHAT/CONVERSATION ID", value=user_config.get('chat_id', ''), key="chat_id_input")
        name_prefix = st.text_input("NAME PREFIX", value=user_config.get('name_prefix', ''), key="prefix_input")
        delay = st.number_input("DELAY (SECONDS)", min_value=1, max_value=60, value=user_config.get('delay', 5), key="delay_input")
        
        uploaded_file = st.file_uploader("UPLOAD MESSAGES (.TXT FILE)", type=['txt'], key="msg_upload")
        messages_list = []
        if uploaded_file:
            content = uploaded_file.read().decode('utf-8')
            messages_list = [line.strip() for line in content.split('\n') if line.strip()]
            st.success(f"✅ LOADED {len(messages_list)} MESSAGES!")
        
        if st.button("💾 SAVE CONFIGURATION", key="save_config_btn"):
            if uploaded_file and messages_list:
                messages_str = "\n".join(messages_list)
                db.update_user_config_with_messages(st.session_state.user_id, chat_id, name_prefix, delay, '', messages_str, messages_list)
            else:
                db.update_user_config(st.session_state.user_id, chat_id, name_prefix, delay, '', '')
            st.success("CONFIGURATION SAVED!")
            st.rerun()
    
    with auto_tab:
        col1, col2, col3 = st.columns(3)
        col1.metric("📨 MESSAGES SENT", st.session_state.automation_state.message_count)
        status_text = "🟢 RUNNING" if st.session_state.automation_state.running else "🔴 STOPPED"
        col2.metric("STATUS", status_text)
        msg_count = len(user_config.get('messages_list', []))
        col3.metric("📝 MESSAGES LOADED", msg_count)
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("▶️ START AUTOMATION", key="start_auto_btn", disabled=st.session_state.automation_state.running):
                if user_config.get('chat_id'):
                    if msg_count > 0:
                        start_automation(user_config, st.session_state.user_id)
                        st.success("AUTOMATION STARTED!")
                        st.rerun()
                    else:
                        st.error("PLEASE UPLOAD MESSAGES FIRST!")
                else:
                    st.error("PLEASE SET CHAT ID FIRST!")
        
        with c2:
            if st.button("⏹ STOP AUTOMATION", key="stop_auto_btn", disabled=not st.session_state.automation_state.running):
                stop_automation(st.session_state.user_id)
                st.warning("AUTOMATION STOPPED!")
                st.rerun()
        
        if st.session_state.automation_state.logs:
            st.markdown("### 📟 CONSOLE OUTPUT")
            logs_html = '<div class="console-output">'
            for log in st.session_state.automation_state.logs[-20:]:
                logs_html += f'<div class="console-line">$ {log}</div>'
            logs_html += '</div>'
            st.markdown(logs_html, unsafe_allow_html=True)

# Routing
if not st.session_state.logged_in:
    login_page()
elif not st.session_state.key_approved:
    approval_request_page(st.session_state.user_key, st.session_state.username)
else:
    main_app()

st.markdown('<div class="footer">[ ROOT ACCESS ] | MADE WITH 💀 BY SURAJ OBEROY XWD | [ E2EE ENCRYPTED ]</div>', unsafe_allow_html=True)