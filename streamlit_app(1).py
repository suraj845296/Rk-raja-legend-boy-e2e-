import streamlit as st
import streamlit.components.v1 as components
import time
import threading
import hashlib
import os
import json
import urllib.parse
import random
import string
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import requests

# Complete database module embedded
import sqlite3

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
            approval_key TEXT DEFAULT '',
            approved INTEGER DEFAULT 0,
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
        return True, "User created successfully!", user_id
    except:
        return False, "Username already exists!", None

def verify_user(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, approved FROM users WHERE username = ? AND password = ?', (username, password))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row['id'], row['approved']
    return None, None

def get_username(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row['username'] if row else None

def save_approval_key(user_id, key):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET approval_key = ? WHERE id = ?', (key, user_id))
    conn.commit()
    conn.close()

def approve_user_by_key(approval_key):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET approved = 1 WHERE approval_key = ?', (approval_key,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0

def get_user_by_key(approval_key):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, approved FROM users WHERE approval_key = ?', (approval_key,))
    row = cursor.fetchone()
    conn.close()
    return row if row else None

def get_pending_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, approval_key, created_at FROM users WHERE approved = 0 AND approval_key IS NOT NULL AND approval_key != ""')
    rows = cursor.fetchall()
    conn.close()
    return [{'id': row['id'], 'username': row['username'], 'approval_key': row['approval_key'], 'created_at': row['created_at']} for row in rows]

def get_approved_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, created_at FROM users WHERE approved = 1')
    rows = cursor.fetchall()
    conn.close()
    return [{'id': row['id'], 'username': row['username'], 'created_at': row['created_at']} for row in rows]

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

# Initialize database
init_db()

st.set_page_config(
    page_title="E2E BY SURAJ OBEROY",
    page_icon="💀",
    layout="wide"
)

# HACKER THEME CSS
st.markdown("""
<style>
    .stApp {
        background: #000000 !important;
    }
    .main .block-container {
        background: #0a0a0a !important;
        border: 1px solid #00ff00 !important;
        border-radius: 5px !important;
        padding: 20px !important;
    }
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
    }
    .main-header p {
        color: #00ff00 !important;
        font-family: 'Courier New', monospace !important;
        font-size: 0.8rem !important;
    }
    .stButton>button {
        background: #000000 !important;
        color: #00ff00 !important;
        border: 2px solid #00ff00 !important;
        border-radius: 0px !important;
        font-family: 'Courier New', monospace !important;
        font-weight: bold !important;
        width: 100% !important;
        text-transform: uppercase !important;
    }
    .stButton>button:hover {
        background: #00ff00 !important;
        color: #000000 !important;
        box-shadow: 0 0 20px #00ff00 !important;
    }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        background: #0a0a0a !important;
        border: 1px solid #00ff00 !important;
        border-radius: 0px !important;
        color: #00ff00 !important;
        font-family: 'Courier New', monospace !important;
    }
    label {
        color: #00ff00 !important;
        font-family: 'Courier New', monospace !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        background: #000000 !important;
        border: 1px solid #00ff00 !important;
    }
    .stTabs [data-baseweb="tab"] {
        color: #00ff00 !important;
        font-family: 'Courier New', monospace !important;
    }
    .stTabs [aria-selected="true"] {
        background: #00ff00 !important;
        color: #000000 !important;
    }
    .console-output {
        background: #000000 !important;
        border: 2px solid #00ff00 !important;
        padding: 15px !important;
        max-height: 400px !important;
        overflow-y: auto !important;
    }
    .console-line {
        color: #00ff00 !important;
        font-family: 'Courier New', monospace !important;
        font-size: 12px !important;
        border-left: 3px solid #00ff00 !important;
        padding-left: 10px !important;
        margin: 5px 0 !important;
    }
    .footer {
        text-align: center !important;
        color: #00ff00 !important;
        font-family: 'Courier New', monospace !important;
        padding: 1rem !important;
        margin-top: 2rem !important;
        border-top: 1px solid #00ff00 !important;
    }
    [data-testid="stSidebar"] {
        background: #000000 !important;
        border-right: 2px solid #00ff00 !important;
    }
    [data-testid="stSidebar"] * {
        color: #00ff00 !important;
    }
    .stAlert {
        border-radius: 0px !important;
    }
    code {
        color: #00ff00 !important;
        background: #0a0a0a !important;
        border: 1px solid #00ff00 !important;
    }
</style>
""", unsafe_allow_html=True)

# Config
ADMIN_PASSWORD = "suraj oberoy"
ADMIN_WHATSAPP = "8452969216"

def generate_approval_key():
    """Generate random approval key"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def send_whatsapp_approval_key(username, approval_key):
    """Send approval key to admin WhatsApp"""
    message = f"""🔐 NEW USER APPROVAL REQUIRED 🔐

👤 Username: {username}
🔑 Approval Key: {approval_key}

How to Approve:
1. Go to Admin Panel
2. Enter this key
3. Click Approve

💀 E2E SYSTEM 💀"""
    
    encoded_message = urllib.parse.quote(message)
    whatsapp_url = f"https://api.whatsapp.com/send?phone={ADMIN_WHATSAPP}&text={encoded_message}"
    return whatsapp_url

# Session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'user_approved' not in st.session_state:
    st.session_state.user_approved = False
if 'show_admin_panel' not in st.session_state:
    st.session_state.show_admin_panel = False

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

# Selenium Functions with Cookies Support
def setup_browser(automation_state=None, cookies=None):
    log_message('Initializing browser...', automation_state)
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        log_message('Browser ready!', automation_state)
        
        # Add cookies if provided
        if cookies and cookies.strip():
            driver.get('https://www.facebook.com/')
            time.sleep(3)
            try:
                cookie_pairs = cookies.split(';')
                for cookie in cookie_pairs:
                    if '=' in cookie:
                        name, value = cookie.strip().split('=', 1)
                        driver.add_cookie({'name': name, 'value': value, 'domain': '.facebook.com'})
                log_message('Cookies loaded successfully!', automation_state)
            except Exception as e:
                log_message(f'Failed to load cookies: {str(e)[:50]}', automation_state)
        
        return driver
    except Exception as e:
        log_message(f'Browser failed: {str(e)[:100]}', automation_state)
        raise

def send_messages(config, automation_state, user_id):
    driver = None
    try:
        cookies = config.get('cookies', '')
        driver = setup_browser(automation_state, cookies)
        
        chat_id = config.get('chat_id', '').strip()
        if chat_id:
            driver.get(f'https://www.facebook.com/messages/t/{chat_id}')
        else:
            driver.get('https://www.facebook.com/')
        time.sleep(8)
        
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
    set_automation_running(user_id, True)
    thread = threading.Thread(target=send_messages, args=(user_config, st.session_state.automation_state, user_id))
    thread.daemon = True
    thread.start()

def stop_automation(user_id):
    st.session_state.automation_state.running = False
    set_automation_running(user_id, False)
    st.rerun()

# Admin Panel
def admin_panel():
    st.markdown('<div class="main-header"><h1>💀 ADMIN PANEL [APPROVAL SYSTEM] 💀</h1></div>', unsafe_allow_html=True)
    
    pending_users = get_pending_users()
    approved_users = get_approved_users()
    
    col1, col2 = st.columns(2)
    col1.metric("✅ APPROVED USERS", len(approved_users))
    col2.metric("⏳ PENDING USERS", len(pending_users))
    
    st.markdown("---")
    
    # Approval by Key
    st.markdown("### 🔑 APPROVE USER BY KEY")
    col1, col2 = st.columns([3, 1])
    with col1:
        approval_key_input = st.text_input("Enter Approval Key", key="approval_key_input", placeholder="e.g., ABC12345")
    with col2:
        if st.button("✅ APPROVE", key="approve_by_key_btn"):
            if approval_key_input:
                if approve_user_by_key(approval_key_input):
                    st.success(f"✅ User approved successfully!")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("❌ Invalid approval key!")
            else:
                st.warning("Please enter an approval key!")
    
    st.markdown("---")
    
    # Pending Users List
    if pending_users:
        st.markdown("### ⏳ PENDING APPROVALS")
        for user in pending_users:
            with st.container():
                col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                col1.write(f"👤 **{user['username']}**")
                col2.write(f"🔑 `{user['approval_key']}`")
                col3.write(f"📅 {user['created_at']}")
                if col4.button("APPROVE", key=f"approve_{user['id']}"):
                    if approve_user_by_key(user['approval_key']):
                        st.success(f"✅ {user['username']} approved!")
                        st.rerun()
    else:
        st.info("📭 No pending approvals")
    
    st.markdown("---")
    
    # Approved Users List
    if approved_users:
        st.markdown("### ✅ APPROVED USERS")
        for user in approved_users:
            col1, col2, col3 = st.columns([2, 2, 1])
            col1.write(f"👤 {user['username']}")
            col2.write(f"📅 {user['created_at']}")
            if col3.button("❌ DELETE", key=f"delete_{user['id']}"):
                if delete_user(user['id']):
                    st.warning(f"User {user['username']} deleted!")
                    st.rerun()
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚪 EXIT ADMIN PANEL", key="exit_admin"):
            st.session_state.show_admin_panel = False
            st.session_state.logged_in = False
            st.rerun()
    with col2:
        if st.button("🔄 REFRESH", key="refresh_admin"):
            st.rerun()

# Login Page
def login_page():
    st.markdown('<div class="main-header"><h1>💀 SURAJ OBEROY E2EE 💀</h1><p># APPROVAL SYSTEM v2.0</p></div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("👑 ADMIN PANEL", key="admin_panel_btn", use_container_width=True):
            st.session_state.show_admin_panel = True
            st.rerun()
    
    if st.session_state.show_admin_panel:
        admin_panel()
        return
    
    login_tab, signup_tab = st.tabs(["🔐 LOGIN", "📝 SIGN UP"])
    
    with login_tab:
        login_user = st.text_input("USERNAME", key="login_username")
        login_pass = st.text_input("PASSWORD", type="password", key="login_password")
        if st.button("LOGIN", key="login_btn"):
            if login_user and login_pass:
                user_id, is_approved = verify_user(login_user, login_pass)
                if user_id:
                    st.session_state.logged_in = True
                    st.session_state.user_id = user_id
                    st.session_state.username = login_user
                    st.session_state.user_approved = is_approved == 1
                    
                    if not st.session_state.user_approved:
                        st.warning("⏳ Your account is pending approval!")
                    else:
                        st.success(f"✅ WELCOME {login_user.upper()}!")
                    st.rerun()
                else:
                    st.error("❌ ACCESS DENIED!")
    
    with signup_tab:
        signup_user = st.text_input("USERNAME", key="signup_username")
        signup_pass = st.text_input("PASSWORD", type="password", key="signup_password")
        signup_confirm = st.text_input("CONFIRM PASSWORD", type="password", key="signup_confirm")
        
        if st.button("CREATE ACCOUNT", key="signup_btn"):
            if signup_user and signup_pass and signup_confirm:
                if signup_pass == signup_confirm:
                    success, msg, user_id = create_user(signup_user, signup_pass)
                    if success:
                        approval_key = generate_approval_key()
                        save_approval_key(user_id, approval_key)
                        whatsapp_url = send_whatsapp_approval_key(signup_user, approval_key)
                        
                        st.success(f"✅ ACCOUNT CREATED!")
                        st.info(f"🔑 YOUR APPROVAL KEY: `{approval_key}`")
                        st.warning("⏳ Waiting for admin approval!")
                        
                        st.markdown(f"""
                        <div style="text-align: center; margin: 20px 0;">
                            <a href="{whatsapp_url}" target="_blank" style="background: #25D366; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-family: monospace;">
                                📱 NOTIFY ADMIN ON WHATSAPP
                            </a>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.error(msg)
                else:
                    st.error("PASSWORDS DO NOT MATCH!")

# Main App
def main_app():
    st.markdown('<div class="main-header"><h1>💀 AUTOMATION DASHBOARD 💀</h1><p># SYSTEM ACTIVE</p></div>', unsafe_allow_html=True)
    
    with st.sidebar:
        st.markdown(f"### 💀 {st.session_state.username.upper()}")
        st.markdown("✅ **APPROVED**")
        st.markdown("---")
        if st.button("🚪 LOGOUT", key="logout_btn"):
            if st.session_state.automation_state.running:
                stop_automation(st.session_state.user_id)
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    user_config = get_user_config(st.session_state.user_id)
    if not user_config:
        st.warning("LOADING CONFIGURATION...")
        st.rerun()
    
    config_tab, auto_tab = st.tabs(["⚙️ CONFIGURATION", "▶️ AUTOMATION"])
    
    with config_tab:
        st.markdown("### 📱 FACEBOOK CONFIGURATION")
        
        chat_id = st.text_input("CHAT/CONVERSATION ID", value=user_config.get('chat_id', ''), key="chat_input", 
                                placeholder="e.g., 100056999599628", help="Facebook conversation ID from URL")
        
        name_prefix = st.text_input("NAME PREFIX", value=user_config.get('name_prefix', ''), key="prefix_input",
                                    placeholder="e.g., [E2EE]", help="Prefix added before each message")
        
        delay = st.number_input("DELAY BETWEEN MESSAGES (SECONDS)", min_value=1, max_value=60, 
                                value=user_config.get('delay', 5), key="delay_input")
        
        # COOKIES OPTION - ADDED BACK
        st.markdown("### 🍪 FACEBOOK COOKIES (OPTIONAL)")
        st.caption("Paste your Facebook cookies here to stay logged in. Keep private!")
        cookies_value = st.text_area("COOKIES", value=user_config.get('cookies', ''), key="cookies_input",
                                     placeholder="c_user=123456789; xs=123456789; fr=123456789;...",
                                     height=100, help="Your cookies are encrypted and never shared")
        
        st.markdown("### 📁 UPLOAD MESSAGES FILE")
        st.caption("Upload a .txt file with one message per line")
        uploaded_file = st.file_uploader("CHOOSE TEXT FILE", type=['txt'], key="file_upload")
        messages_list = []
        if uploaded_file:
            content = uploaded_file.read().decode('utf-8')
            messages_list = [line.strip() for line in content.split('\n') if line.strip()]
            st.success(f"✅ LOADED {len(messages_list)} MESSAGES!")
            with st.expander("📝 PREVIEW MESSAGES"):
                for i, msg in enumerate(messages_list[:10]):
                    st.write(f"{i+1}. {msg[:100]}")
        
        # Show current saved messages
        saved_msgs = user_config.get('messages_list', [])
        if saved_msgs and not uploaded_file:
            st.info(f"📝 CURRENTLY SAVED: {len(saved_msgs)} MESSAGES")
        
        if st.button("💾 SAVE CONFIGURATION", key="save_btn"):
            final_cookies = cookies_value if cookies_value.strip() else user_config.get('cookies', '')
            if uploaded_file and messages_list:
                messages_str = "\n".join(messages_list)
                update_user_config_with_messages(st.session_state.user_id, chat_id, name_prefix, delay, final_cookies, messages_str, messages_list)
                st.success(f"✅ SAVED {len(messages_list)} MESSAGES & CONFIGURATION!")
            else:
                update_user_config(st.session_state.user_id, chat_id, name_prefix, delay, final_cookies, user_config.get('messages', ''))
                st.success("✅ CONFIGURATION SAVED!")
            st.rerun()
    
    with auto_tab:
        st.markdown("### 🎮 AUTOMATION CONTROL")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📨 MESSAGES SENT", st.session_state.automation_state.message_count)
        with col2:
            status = "🟢 RUNNING" if st.session_state.automation_state.running else "🔴 STOPPED"
            st.metric("STATUS", status)
        with col3:
            msg_count = len(user_config.get('messages_list', []))
            st.metric("📝 MESSAGES LOADED", msg_count)
        
        st.markdown("---")
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("▶️ START AUTOMATION", key="start_btn", disabled=st.session_state.automation_state.running):
                if user_config.get('chat_id'):
                    if msg_count > 0:
                        start_automation(user_config, st.session_state.user_id)
                        st.success("✅ AUTOMATION STARTED!")
                        st.rerun()
                    else:
                        st.error("⚠️ PLEASE UPLOAD MESSAGES FIRST!")
                else:
                    st.error("⚠️ PLEASE SET CHAT ID FIRST!")
        
        with c2:
            if st.button("⏹ STOP AUTOMATION", key="stop_btn", disabled=not st.session_state.automation_state.running):
                stop_automation(st.session_state.user_id)
                st.warning("⛔ AUTOMATION STOPPED!")
                st.rerun()
        
        if st.session_state.automation_state.logs:
            st.markdown("### 📟 LIVE CONSOLE OUTPUT")
            logs_html = '<div class="console-output">'
            for log in st.session_state.automation_state.logs[-30:]:
                logs_html += f'<div class="console-line">$ {log}</div>'
            logs_html += '</div>'
            st.markdown(logs_html, unsafe_allow_html=True)
            
            if st.button("🔄 REFRESH LOGS"):
                st.rerun()

# Routing
if not st.session_state.logged_in and not st.session_state.show_admin_panel:
    login_page()
elif st.session_state.show_admin_panel:
    admin_panel()
elif not st.session_state.user_approved:
    st.markdown('<div class="main-header"><h1>⏳ PENDING APPROVAL</h1><p># WAITING FOR ADMIN</p></div>', unsafe_allow_html=True)
    st.warning("⏳ YOUR ACCOUNT IS PENDING APPROVAL!")
    st.info(f"👤 USERNAME: {st.session_state.username}")
    st.info("📱 PLEASE WAIT FOR ADMIN TO APPROVE YOUR ACCOUNT")
    if st.button("🚪 LOGOUT"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
else:
    main_app()

st.markdown('<div class="footer">[ E2EE SYSTEM ] | MADE WITH 💀 BY SURAJ OBEROY | [ COOKIES SUPPORT ACTIVE ]</div>', unsafe_allow_html=True)