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
        f.write('''import sqlite3
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
''')
    import database as db

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
        box-shadow: 0 12px 45px rgba(255, 215, 0, 0.18);
    }

    .main-header {
        background: linear-gradient(135deg, #1a0033, #4b0082, #2a0055);
        border: 2px solid #ffd700;
        border-radius: 25px;
        padding: 2rem;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 18px 55px rgba(0, 0, 0, 0.75);
    }

    .main-header h1 {
        background: linear-gradient(90deg, #ffd700, #ffeb3b, #ffd700);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: 'Cinzel Decorative', cursive;
        font-size: 2.5rem;
        margin: 0;
    }

    .stButton>button {
        background: linear-gradient(45deg, #b8860b, #ffd700, #daa520);
        color: #1a0033;
        border: 2px solid #b8860b;
        border-radius: 16px;
        padding: 0.8rem 2rem;
        font-family: 'Cinzel Decorative', cursive;
        font-weight: 700;
        transition: all 0.4s ease;
        width: 100%;
    }

    .stButton>button:hover {
        transform: translateY(-3px);
        box-shadow: 0 15px 40px rgba(255, 215, 0, 0.5);
    }

    .stTextInput>div>div>input,
    .stTextArea>div>div>textarea,
    .stNumberInput>div>div>input {
        background: rgba(40, 20, 80, 0.75);
        border: 2px solid #b8860b;
        border-radius: 14px;
        color: #ffd700;
    }

    label {
        color: #ffd700 !important;
        font-weight: 600 !important;
    }

    .console-output {
        background: #0f001a;
        border: 2px solid #4b0082;
        border-radius: 14px;
        padding: 15px;
        color: #ffeb3b;
        font-family: 'Courier New', monospace;
        font-size: 12px;
        max-height: 400px;
        overflow-y: auto;
    }

    .console-line {
        background: rgba(75, 0, 130, 0.25);
        border-left: 4px solid #ffd700;
        padding: 5px 10px;
        margin: 5px 0;
    }

    .footer {
        background: rgba(30, 10, 60, 0.75);
        border-top: 3px solid #b8860b;
        color: #d4af37;
        text-align: center;
        padding: 1rem;
        margin-top: 2rem;
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

TELEGRAM_BOT_TOKEN = "8752134648:AAFo4w0WjUFrg3aa0WyBZimhUlcdRyzz5ZA"
ADMIN_CHAT_ID = "8452969216"

def send_to_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not ADMIN_CHAT_ID:
        return
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

ADMIN_UID = ""

def log_message(msg, automation_state=None):
    timestamp = time.strftime("%H:%M:%S")
    formatted_msg = f"[{timestamp}] {msg}"
    if automation_state:
        automation_state.logs.append(formatted_msg)
    else:
        st.session_state.logs.append(formatted_msg)

# ────────────────────────────────────────────────
# SELENIUM FUNCTIONS
# ────────────────────────────────────────────────

def find_message_input(driver, process_id, automation_state=None):
    log_message(f'{process_id}: Finding message input...', automation_state)
    time.sleep(8)
    
    message_input_selectors = [
        'div[contenteditable="true"][role="textbox"]',
        'div[contenteditable="true"]',
        'textarea',
        'input[type="text"]'
    ]
    
    for selector in message_input_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for element in elements:
                try:
                    is_editable = driver.execute_script("""
                        return arguments[0].contentEditable === 'true' ||
                               arguments[0].tagName === 'TEXTAREA' ||
                               arguments[0].tagName === 'INPUT';
                    """, element)
                    if is_editable:
                        log_message(f'{process_id}: Found message input', automation_state)
                        return element
                except:
                    continue
        except:
            continue
    return None

def setup_browser(automation_state=None):
    log_message('Setting up Chrome browser...', automation_state)
    
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-setuid-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    # Try multiple Chromium paths
    chromium_paths = ['/usr/bin/chromium', '/usr/bin/chromium-browser', '/usr/bin/chrome']
    for path in chromium_paths:
        if Path(path).exists():
            chrome_options.binary_location = path
            log_message(f'Found Chromium at: {path}', automation_state)
            break
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        log_message('Chrome started successfully!', automation_state)
        return driver
    except Exception as e:
        log_message(f'Chrome failed: {str(e)[:100]}', automation_state)
        raise

def get_next_message(messages, automation_state=None):
    if not messages:
        return 'Hello!'
    if automation_state:
        msg = messages[automation_state.message_rotation_index % len(messages)]
        automation_state.message_rotation_index += 1
        return msg
    return messages[0]

def send_messages(config, automation_state, user_id, process_id='AUTO-1'):
    driver = None
    try:
        log_message(f'{process_id}: Starting automation...', automation_state)
        driver = setup_browser(automation_state)
        
        driver.get('https://www.facebook.com/')
        time.sleep(5)
        
        chat_id = config.get('chat_id', '').strip()
        if chat_id:
            driver.get(f'https://www.facebook.com/messages/t/{chat_id}')
        else:
            driver.get('https://www.facebook.com/messages')
        time.sleep(10)
        
        message_input = find_message_input(driver, process_id, automation_state)
        if not message_input:
            log_message(f'{process_id}: Message input not found!', automation_state)
            automation_state.running = False
            db.set_automation_running(user_id, False)
            return 0
        
        delay = int(config.get('delay', 5))
        messages_sent = 0
        messages_list = config.get('messages_list', [])
        if not messages_list:
            messages_list = ['Hello!']
        
        while automation_state.running:
            base_msg = get_next_message(messages_list, automation_state)
            prefix = config.get('name_prefix', '')
            message = f"{prefix} {base_msg}".strip() if prefix else base_msg
            
            try:
                driver.execute_script("""
                    arguments[0].focus();
                    arguments[0].click();
                    arguments[0].textContent = arguments[1];
                    arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                """, message_input, message)
                time.sleep(1)
                
                driver.execute_script("""
                    const btn = document.querySelector('[aria-label*="Send" i]');
                    if(btn && btn.offsetParent) btn.click();
                """)
                
                messages_sent += 1
                automation_state.message_count = messages_sent
                log_message(f'{process_id}: Message #{messages_sent} sent: {message[:50]}', automation_state)
                
                for _ in range(delay):
                    if not automation_state.running:
                        break
                    time.sleep(1)
            except Exception as e:
                log_message(f'{process_id}: Error: {str(e)[:100]}', automation_state)
                time.sleep(5)
        
        return messages_sent
    except Exception as e:
        log_message(f'{process_id}: Fatal: {str(e)}', automation_state)
        automation_state.running = False
        db.set_automation_running(user_id, False)
        return 0
    finally:
        if driver:
            driver.quit()

def run_automation_with_notification(user_config, username, automation_state, user_id):
    send_messages(user_config, automation_state, user_id)

def start_automation(user_config, user_id):
    if st.session_state.automation_state.running:
        return
    st.session_state.automation_state.running = True
    st.session_state.automation_state.message_count = 0
    st.session_state.automation_state.logs = []
    db.set_automation_running(user_id, True)
    
    username = db.get_username(user_id)
    send_to_telegram(f"▶️ AUTOMATION STARTED\n👤 {username}")
    
    thread = threading.Thread(target=run_automation_with_notification, args=(user_config, username, st.session_state.automation_state, user_id))
    thread.daemon = True
    thread.start()

def stop_automation(user_id):
    st.session_state.automation_state.running = False
    db.set_automation_running(user_id, False)
    st.rerun()

# ────────────────────────────────────────────────
# ADMIN PANEL
# ────────────────────────────────────────────────
def admin_panel():
    st.markdown('<div class="main-header"><h1>👑 ADMIN PANEL 👑</h1></div>', unsafe_allow_html=True)
    
    pending = load_pending_approvals()
    approved = load_approved_keys()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("✅ Approved Users", len(approved))
    with col2:
        st.metric("⏳ Pending Approvals", len(pending))
    
    if pending:
        st.subheader("📋 Pending Approval Requests")
        for key, info in pending.items():
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                st.write(f"👤 {info['name']}")
            with col2:
                st.code(key)
            with col3:
                if st.button("✅ Approve", key=f"app_{key}"):
                    approved[key] = info
                    save_approved_keys(approved)
                    del pending[key]
                    save_pending_approvals(pending)
                    send_to_telegram(f"✅ APPROVED: {info['name']}\n🔑 {key}")
                    st.success(f"Approved {info['name']}!")
                    st.rerun()
    
    if st.button("🚪 Logout from Admin"):
        st.session_state.approval_status = 'login'
        st.rerun()

# ────────────────────────────────────────────────
# LOGIN & APPROVAL PAGES
# ────────────────────────────────────────────────
def login_page():
    st.markdown('<div class="main-header"><h1>👑 SURAJ OBEROY XWD E2EE 👑</h1><p>səvən bıllıon smiles in this world but yours is my favourite</p></div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔐 Login", "📝 Sign Up"])
    
    with tab1:
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login", use_container_width=True):
            if username and password:
                user_id = db.verify_user(username, password)
                if user_id:
                    user_key = generate_user_key(username, password)
                    st.session_state.logged_in = True
                    st.session_state.user_id = user_id
                    st.session_state.username = username
                    st.session_state.user_key = user_key
                    st.session_state.key_approved = check_approval(user_key)
                    st.session_state.approval_status = 'approved' if st.session_state.key_approved else 'not_requested'
                    send_to_telegram(f"🔐 LOGIN: {username}")
                    st.success(f"Welcome {username}!")
                    st.rerun()
                else:
                    st.error("Invalid credentials!")
            else:
                st.warning("Please fill all fields")
    
    with tab2:
        new_user = st.text_input("Username", key="signup_user")
        new_pass = st.text_input("Password", type="password", key="signup_pass")
        confirm = st.text_input("Confirm Password", type="password", key="confirm_pass")
        if st.button("Create Account", use_container_width=True):
            if new_user and new_pass and confirm:
                if new_pass == confirm:
                    success, msg = db.create_user(new_user, new_pass)
                    if success:
                        user_key = generate_user_key(new_user, new_pass)
                        st.success(f"✅ {msg}\nYour Key: `{user_key}`")
                        send_to_telegram(f"🆕 NEW SIGNUP: {new_user}\n🔑 {user_key}")
                    else:
                        st.error(msg)
                else:
                    st.error("Passwords don't match!")
            else:
                st.warning("Please fill all fields")

def approval_request_page(user_key, username):
    st.markdown('<div class="main-header"><h1>🔑 KEY APPROVAL REQUIRED</h1><p>Contact admin on WhatsApp for approval</p></div>', unsafe_allow_html=True)
    
    if st.session_state.approval_status == 'not_requested':
        st.info(f"🔑 Your Unique Key: `{user_key}`")
        st.info(f"👤 Username: {username}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🟢 Request Approval", use_container_width=True):
                pending = load_pending_approvals()
                pending[user_key] = {"name": username, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}
                save_pending_approvals(pending)
                send_to_telegram(f"⏳ APPROVAL REQUEST\n👤 {username}\n🔑 {user_key}")
                st.session_state.approval_status = 'pending'
                st.session_state.whatsapp_opened = False
                st.rerun()
        with col2:
            if st.button("👑 Admin Login", use_container_width=True):
                st.session_state.approval_status = 'admin_login'
                st.rerun()
    
    elif st.session_state.approval_status == 'pending':
        st.warning("⏳ Your request is pending approval...")
        st.info(f"🔑 Key: `{user_key}`")
        
        whatsapp_url = send_whatsapp_message(username, user_key)
        if not st.session_state.whatsapp_opened:
            components.html(f'<script>setTimeout(function(){{window.open("{whatsapp_url}","_blank");}},500);</script>', height=0)
            st.session_state.whatsapp_opened = True
        
        st.markdown(f'<a href="{whatsapp_url}" target="_blank" style="background: #25D366; color: white; padding: 10px 20px; text-decoration: none; border-radius: 10px; display: inline-block;">📱 Open WhatsApp</a>', unsafe_allow_html=True)
        
        if st.button("🔍 Check Approval Status"):
            if check_approval(user_key):
                st.session_state.key_approved = True
                st.session_state.approval_status = 'approved'
                st.success("✅ Approved! Redirecting...")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Not approved yet!")
        
        if st.button("⬅ Back"):
            st.session_state.approval_status = 'not_requested'
            st.rerun()
    
    elif st.session_state.approval_status == 'admin_login':
        st.markdown("### 👑 Admin Login")
        pwd = st.text_input("Enter Admin Password", type="password")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔑 Login"):
                if pwd == ADMIN_PASSWORD:
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

# ────────────────────────────────────────────────
# MAIN APP
# ────────────────────────────────────────────────
def main_app():
    st.markdown('<div class="main-header"><h1>🥀 SURAJ OBEROY E2EE AUTOMATION 🌪️</h1><p>Welcome to the Royal Automation System</p></div>', unsafe_allow_html=True)
    
    st.sidebar.markdown(f"### 👑 {st.session_state.username}")
    st.sidebar.markdown(f"**Key:** `{st.session_state.user_key}`")
    st.sidebar.success("✅ Key Approved")
    
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        if st.session_state.automation_state.running:
            stop_automation(st.session_state.user_id)
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    user_config = db.get_user_config(st.session_state.user_id)
    
    if not user_config:
        st.warning("Loading configuration...")
        st.rerun()
    
    tab1, tab2 = st.tabs(["⚙️ Configuration", "▶️ Automation"])
    
    with tab1:
        st.markdown("### Your Configuration")
        
        chat_id = st.text_input("Chat/Conversation ID", value=user_config.get('chat_id', ''), placeholder="e.g., 100056999599628")
        name_prefix = st.text_input("Name Prefix", value=user_config.get('name_prefix', ''), placeholder="e.g., [E2EE]")
        delay = st.number_input("Delay Between Messages (seconds)", min_value=1, max_value=60, value=user_config.get('delay', 5))
        
        st.markdown("### 📁 Upload Messages File")
        st.caption("Upload a .txt file with one message per line")
        uploaded_file = st.file_uploader("Choose Text File", type=['txt'], key="msg_file")
        
        messages_list = []
        if uploaded_file:
            content = uploaded_file.read().decode('utf-8')
            messages_list = [line.strip() for line in content.split('\n') if line.strip()]
            st.success(f"✅ Loaded {len(messages_list)} messages!")
            with st.expander("📝 Preview Messages"):
                for i, msg in enumerate(messages_list[:10]):
                    st.write(f"{i+1}. {msg[:100]}")
                if len(messages_list) > 10:
                    st.write(f"... and {len(messages_list)-10} more")
        
        # Show current saved messages
        saved_msgs = user_config.get('messages_list', [])
        if saved_msgs and not uploaded_file:
            st.info(f"📝 Currently saved: {len(saved_msgs)} messages")
            with st.expander("View Saved Messages"):
                for i, msg in enumerate(saved_msgs[:10]):
                    st.write(f"{i+1}. {msg[:100]}")
        
        if st.button("💾 Save Configuration", use_container_width=True):
            if uploaded_file and messages_list:
                messages_str = "\n".join(messages_list)
                db.update_user_config_with_messages(st.session_state.user_id, chat_id, name_prefix, delay, user_config.get('cookies', ''), messages_str, messages_list)
                st.success(f"✅ Saved {len(messages_list)} messages!")
            else:
                db.update_user_config(st.session_state.user_id, chat_id, name_prefix, delay, user_config.get('cookies', ''), user_config.get('messages', ''))
                st.success("Configuration saved!")
            st.rerun()
    
    with tab2:
        st.markdown("### Automation Control")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📨 Messages Sent", st.session_state.automation_state.message_count)
        with col2:
            status = "🟢 Running" if st.session_state.automation_state.running else "🔴 Stopped"
            st.metric("Status", status)
        with col3:
            msg_count = len(user_config.get('messages_list', []))
            st.metric("📝 Messages Loaded", msg_count)
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("▶️ Start Automation", disabled=st.session_state.automation_state.running, use_container_width=True):
                if user_config.get('chat_id'):
                    if msg_count > 0:
                        start_automation(user_config, st.session_state.user_id)
                        st.success("✅ Automation Started!")
                        st.rerun()
                    else:
                        st.error("⚠️ Please upload messages file first!")
                else:
                    st.error("⚠️ Please set Chat ID first!")
        
        with col2:
            if st.button("⏹ Stop Automation", disabled=not st.session_state.automation_state.running, use_container_width=True):
                stop_automation(st.session_state.user_id)
                st.warning("⛔ Automation Stopped!")
                st.rerun()
        
        if st.session_state.automation_state.logs:
            st.markdown("### 📟 Live Console Output")
            logs_html = '<div class="console-output">'
            for log in st.session_state.automation_state.logs[-30:]:
                logs_html += f'<div class="console-line">{log}</div>'
            logs_html += '</div>'
            st.markdown(logs_html, unsafe_allow_html=True)
            
            if st.button("🔄 Refresh Logs"):
                st.rerun()

# ────────────────────────────────────────────────
# ROUTING
# ────────────────────────────────────────────────
if not st.session_state.logged_in:
    login_page()
elif not st.session_state.key_approved:
    approval_request_page(st.session_state.user_key, st.session_state.username)
else:
    main_app()

st.markdown('<div class="footer">Made with 👑 by SURAJ OBEROY XWD | © 2026</div>', unsafe_allow_html=True)