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

# Database setup - create if not exists
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

# Page configuration
st.set_page_config(
    page_title="WhatsApp Automation - Suraj Oberoy",
    page_icon="🤖",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    /* Main container styling */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
    }
    
    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #1e1b4b, #2e1065);
        border: 2px solid #8b5cf6;
        border-radius: 20px;
        padding: 1.5rem;
        text-align: center;
        margin-bottom: 1.5rem;
        box-shadow: 0 10px 25px -5px rgba(0,0,0,0.3);
    }
    
    .main-header h1 {
        color: #a78bfa;
        font-size: 2rem;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(45deg, #7c3aed, #a78bfa);
        color: white;
        font-weight: bold;
        border-radius: 10px;
        width: 100%;
        border: none;
        transition: transform 0.2s;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        background: linear-gradient(45deg, #8b5cf6, #c4b5fd);
    }
    
    /* Console output styling */
    .console-output {
        background: #0f0f1a;
        border: 1px solid #8b5cf6;
        border-radius: 10px;
        padding: 10px;
        max-height: 300px;
        overflow-y: auto;
        font-family: monospace;
    }
    
    .console-line {
        color: #a78bfa;
        font-family: monospace;
        font-size: 12px;
        border-left: 3px solid #8b5cf6;
        padding-left: 10px;
        margin: 5px 0;
    }
    
    /* Card styling */
    .metric-card {
        background: rgba(30, 27, 75, 0.5);
        border-radius: 15px;
        padding: 1rem;
        text-align: center;
        border: 1px solid #8b5cf6;
    }
    
    /* Footer styling */
    .footer {
        text-align: center;
        color: #a78bfa;
        padding: 1rem;
        margin-top: 2rem;
        border-top: 1px solid #4c1d95;
        font-size: 0.8rem;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: rgba(30, 27, 75, 0.5);
        border-radius: 10px;
        padding: 8px 20px;
    }
    
    /* Input field styling */
    .stTextInput input, .stNumberInput input, .stTextArea textarea {
        background: #1e1b4b !important;
        color: white !important;
        border-color: #8b5cf6 !important;
    }
    
    /* Success/Error message styling */
    .stAlert {
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Constants
ADMIN_PASSWORD = "suraj oberoy"
WHATSAPP_NUMBER = "918452969216"
APPROVAL_FILE = "approved_keys.json"
PENDING_FILE = "pending_approvals.json"

# Telegram bot configuration (consider moving to environment variables)
TELEGRAM_BOT_TOKEN = "8752134648:AAFo4w0WjUFrg3aa0WyBZimhUlcdRyzz5ZA"
TELEGRAM_CHAT_ID = "8452969216"

def send_to_telegram(message):
    """Send notification to Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
        requests.post(url, data=payload, timeout=5)
    except Exception:
        pass

def generate_user_key(username, password):
    """Generate unique key for user"""
    combined = f"{username}:{password}"
    key_hash = hashlib.sha256(combined.encode()).hexdigest()[:8].upper()
    return f"KEY-{key_hash}"

def load_approved_keys():
    """Load approved keys from file"""
    if os.path.exists(APPROVAL_FILE):
        try:
            with open(APPROVAL_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_approved_keys(keys):
    """Save approved keys to file"""
    with open(APPROVAL_FILE, 'w') as f:
        json.dump(keys, f, indent=2)

def load_pending_approvals():
    """Load pending approvals from file"""
    if os.path.exists(PENDING_FILE):
        try:
            with open(PENDING_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_pending_approvals(pending):
    """Save pending approvals to file"""
    with open(PENDING_FILE, 'w') as f:
        json.dump(pending, f, indent=2)

def check_approval(key):
    """Check if key is approved"""
    return key in load_approved_keys()

# Initialize session state
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

class AutomationState:
    """Class to manage automation state"""
    def __init__(self):
        self.running = False
        self.message_count = 0
        self.logs = []

if 'automation_state' not in st.session_state:
    st.session_state.automation_state = AutomationState()

def log_message(msg, automation_state=None):
    """Add timestamped message to logs"""
    timestamp = time.strftime("%H:%M:%S")
    formatted_msg = f"[{timestamp}] {msg}"
    if automation_state:
        automation_state.logs.append(formatted_msg)
        if len(automation_state.logs) > 100:
            automation_state.logs = automation_state.logs[-100:]

def setup_browser(automation_state=None):
    """Setup Chrome browser in headless mode"""
    log_message('Setting up Chrome browser...', automation_state)
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-notifications')
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        log_message('Chrome browser started successfully', automation_state)
        return driver
    except Exception as e:
        log_message(f'Failed to start Chrome: {str(e)[:100]}', automation_state)
        raise

def send_messages(config, automation_state, user_id):
    """Main automation function to send messages"""
    driver = None
    try:
        driver = setup_browser(automation_state)
        driver.get('https://web.whatsapp.com/')
        log_message('WhatsApp Web loaded, waiting for QR scan...', automation_state)
        time.sleep(15)  # Wait for QR scan
        
        automation_state.running = False
        return 0
    except Exception as e:
        log_message(f'Error in automation: {str(e)[:100]}', automation_state)
        return 0
    finally:
        if driver:
            driver.quit()

def start_automation(user_config, user_id):
    """Start automation in background thread"""
    if st.session_state.automation_state.running:
        return
    st.session_state.automation_state.running = True
    st.session_state.automation_state.logs = []
    db.set_automation_running(user_id, True)
    thread = threading.Thread(target=send_messages, args=(user_config, st.session_state.automation_state, user_id))
    thread.daemon = True
    thread.start()

def stop_automation(user_id):
    """Stop automation"""
    st.session_state.automation_state.running = False
    db.set_automation_running(user_id, False)
    st.rerun()

def admin_panel():
    """Admin panel interface"""
    st.markdown('<div class="main-header"><h1>👑 Admin Control Panel</h1></div>', unsafe_allow_html=True)
    
    pending = load_pending_approvals()
    approved = load_approved_keys()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Total Users", len(db.get_all_users()))
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Approved Keys", len(approved))
        st.markdown('</div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Pending Requests", len(pending))
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Pending requests section
    if pending:
        st.subheader("📋 Pending Approval Requests")
        for key, info in pending.items():
            with st.container():
                col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                col1.write(f"👤 {info.get('name', 'Unknown')}")
                col2.code(key)
                col3.write(f"📅 {info.get('timestamp', 'Unknown')}")
                if col4.button("✅ Approve", key=f"approve_{key}"):
                    approved[key] = info
                    save_approved_keys(approved)
                    del pending[key]
                    save_pending_approvals(pending)
                    send_to_telegram(f"✅ User Approved: {info.get('name')}\n🔑 Key: {key}")
                    st.success(f"Approved {info.get('name')}!")
                    st.rerun()
    
    # User management section
    st.subheader("👥 User Management")
    users = db.get_all_users()
    if users:
        user_data = []
        for user in users:
            config = db.get_user_config(user['id'])
            user_data.append({
                "ID": user['id'],
                "Username": user['username'],
                "Created": user['created_at'],
                "Status": "Active",
                "Messages": config.get('message_count', 0) if config else 0
            })
        st.dataframe(user_data, use_container_width=True)
        
        # Delete user option
        delete_user = st.selectbox("Select user to delete", [u['username'] for u in users])
        if st.button("🗑️ Delete User", key="admin_delete_user"):
            user_to_delete = next((u for u in users if u['username'] == delete_user), None)
            if user_to_delete:
                if db.delete_user(user_to_delete['id']):
                    st.success(f"User {delete_user} deleted successfully!")
                    st.rerun()
                else:
                    st.error("Failed to delete user")
    
    # Admin logout
    if st.button("🚪 Logout from Admin", key="admin_logout_btn"):
        st.session_state.approval_status = 'login'
        st.rerun()

def login_page():
    """Login and signup interface"""
    st.markdown('<div class="main-header"><h1>🤖 WhatsApp Automation System</h1></div>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #a78bfa;">Powered by Suraj Oberoy</p>', unsafe_allow_html=True)
    
    login_tab, signup_tab = st.tabs(["🔐 Login", "📝 Create Account"])
    
    with login_tab:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            login_user = st.text_input("Username", placeholder="Enter your username", key="login_username")
            login_pass = st.text_input("Password", type="password", placeholder="Enter your password", key="login_password")
            
            if st.button("Login", key="login_button", use_container_width=True):
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
                        send_to_telegram(f"🔐 User Login: {login_user}")
                        st.success(f"Welcome back, {login_user}!")
                        st.rerun()
                    else:
                        st.error("❌ Invalid username or password!")
                else:
                    st.warning("Please enter both username and password")
    
    with signup_tab:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            signup_user = st.text_input("Choose Username", placeholder="Username", key="signup_username")
            signup_pass = st.text_input("Create Password", type="password", placeholder="Password", key="signup_password")
            signup_confirm = st.text_input("Confirm Password", type="password", placeholder="Confirm password", key="signup_confirm")
            
            if st.button("Create Account", key="signup_button", use_container_width=True):
                if signup_user and signup_pass and signup_confirm:
                    if len(signup_user) >= 3:
                        if signup_pass == signup_confirm:
                            if len(signup_pass) >= 4:
                                success, msg = db.create_user(signup_user, signup_pass)
                                if success:
                                    user_key = generate_user_key(signup_user, signup_pass)
                                    st.success(f"✅ Account created successfully!")
                                    st.info(f"🔑 Your access key: `{user_key}`\n\nPlease save this key for approval.")
                                    send_to_telegram(f"🆕 New Registration: {signup_user}\n🔑 Key: {user_key}")
                                else:
                                    st.error(msg)
                            else:
                                st.error("Password must be at least 4 characters long!")
                        else:
                            st.error("Passwords do not match!")
                    else:
                        st.error("Username must be at least 3 characters long!")
                else:
                    st.warning("Please fill all fields")

def approval_request_page(user_key, username):
    """Key approval interface"""
    st.markdown('<div class="main-header"><h1>🔑 Key Approval Required</h1></div>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #a78bfa;">Your account needs admin approval before you can use the automation features.</p>', unsafe_allow_html=True)
    
    if st.session_state.approval_status == 'not_requested':
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown(f"""
            <div style="background: #1e1b4b; border-radius: 15px; padding: 1.5rem; text-align: center; margin: 1rem 0;">
                <p style="color: #a78bfa; margin-bottom: 0.5rem;">Your Access Key</p>
                <code style="background: #0f0f1a; padding: 10px; border-radius: 8px; font-size: 1.2rem;">{user_key}</code>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("📤 Request Approval", key="request_approval", use_container_width=True):
                pending = load_pending_approvals()
                pending[user_key] = {
                    "name": username,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                save_pending_approvals(pending)
                send_to_telegram(f"⏳ New Approval Request\n👤 {username}\n🔑 {user_key}")
                st.session_state.approval_status = 'pending'
                st.success("Approval request sent! Admin will review shortly.")
                st.rerun()
            
            st.markdown("---")
            st.markdown("<p style='text-align: center;'>Already have admin access?</p>", unsafe_allow_html=True)
            if st.button("👑 Admin Login", key="admin_access", use_container_width=True):
                st.session_state.approval_status = 'admin_login'
                st.rerun()
    
    elif st.session_state.approval_status == 'pending':
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.warning("⏳ Waiting for admin approval...")
            st.info("Please check back later or contact admin on WhatsApp.")
            if st.button("🔄 Check Status", key="check_status", use_container_width=True):
                if check_approval(user_key):
                    st.session_state.key_approved = True
                    st.session_state.approval_status = 'approved'
                    st.success("✅ Your key has been approved! Redirecting...")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Not approved yet. Please wait for admin approval.")
    
    elif st.session_state.approval_status == 'admin_login':
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown('<div class="main-header" style="padding: 1rem;"><h2>Admin Access</h2></div>', unsafe_allow_html=True)
            admin_pass = st.text_input("Admin Password", type="password", placeholder="Enter admin password", key="admin_pass")
            if st.button("Login", key="admin_login", use_container_width=True):
                if admin_pass == ADMIN_PASSWORD:
                    st.session_state.approval_status = 'admin_panel'
                    st.rerun()
                else:
                    st.error("❌ Invalid admin password!")
    
    elif st.session_state.approval_status == 'admin_panel':
        admin_panel()

def main_app():
    """Main application interface"""
    st.markdown('<div class="main-header"><h1>🤖 Automation Dashboard</h1></div>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown(f"""
        <div style="text-align: center; margin-bottom: 1rem;">
            <div style="background: #8b5cf6; width: 60px; height: 60px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto;">
                <span style="font-size: 2rem;">👑</span>
            </div>
            <h3 style="margin-top: 0.5rem;">{st.session_state.username}</h3>
            <p><code style="font-size: 0.7rem;">{st.session_state.user_key}</code></p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        if st.button("🚪 Logout", key="main_logout", use_container_width=True):
            if st.session_state.automation_state.running:
                stop_automation(st.session_state.user_id)
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    # Load user configuration
    user_config = db.get_user_config(st.session_state.user_id)
    if not user_config:
        st.warning("Loading configuration...")
        st.rerun()
    
    # Tabs
    config_tab, auto_tab, stats_tab = st.tabs(["⚙️ Configuration", "▶️ Automation", "📊 Statistics"])
    
    with config_tab:
        st.subheader("Automation Settings")
        
        col1, col2 = st.columns(2)
        with col1:
            chat_id = st.text_input(
                "Chat/Group ID",
                value=user_config.get('chat_id', ''),
                placeholder="Enter WhatsApp chat ID or group link",
                key="chat_id_input",
                help="The chat ID or group where messages will be sent"
            )
            
            name_prefix = st.text_input(
                "Name Prefix (Optional)",
                value=user_config.get('name_prefix', ''),
                placeholder="e.g., 'Agent:' or 'Bot:'",
                key="prefix_input",
                help="Add a prefix before each message"
            )
        
        with col2:
            delay = st.number_input(
                "Message Delay (seconds)",
                min_value=1,
                max_value=60,
                value=user_config.get('delay', 5),
                key="delay_input",
                help="Time between consecutive messages"
            )
        
        st.subheader("Message List")
        uploaded_file = st.file_uploader(
            "Upload Messages (.txt file)",
            type=['txt'],
            key="msg_upload",
            help="Each line in the file will be sent as a separate message"
        )
        
        messages_list = []
        if uploaded_file:
            content = uploaded_file.read().decode('utf-8')
            messages_list = [line.strip() for line in content.split('\n') if line.strip()]
            st.success(f"✅ Loaded {len(messages_list)} messages!")
            with st.expander("Preview Messages"):
                for i, msg in enumerate(messages_list[:10]):
                    st.write(f"{i+1}. {msg[:100]}...")
                if len(messages_list) > 10:
                    st.write(f"... and {len(messages_list) - 10} more")
        
        if st.button("💾 Save Configuration", key="save_config", use_container_width=True):
            if uploaded_file and messages_list:
                messages_str = "\n".join(messages_list)
                db.update_user_config_with_messages(
                    st.session_state.user_id, chat_id, name_prefix, delay, '', messages_str, messages_list
                )
                st.success("Configuration saved successfully!")
            else:
                db.update_user_config(st.session_state.user_id, chat_id, name_prefix, delay, '', '')
                st.success("Configuration saved!")
            st.rerun()
    
    with auto_tab:
        st.subheader("Control Panel")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("📨 Messages Sent", st.session_state.automation_state.message_count)
            st.markdown('</div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            status = "🟢 Running" if st.session_state.automation_state.running else "🔴 Stopped"
            st.metric("Status", status)
            st.markdown('</div>', unsafe_allow_html=True)
        with col3:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            msg_count = len(user_config.get('messages_list', []))
            st.metric("📝 Messages Loaded", msg_count)
            st.markdown('</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            start_disabled = st.session_state.automation_state.running or not user_config.get('chat_id') or msg_count == 0
            if st.button("▶️ Start Automation", key="start_auto", use_container_width=True, disabled=start_disabled):
                if user_config.get('chat_id'):
                    if msg_count > 0:
                        start_automation(user_config, st.session_state.user_id)
                        st.success("Automation started!")
                        st.rerun()
                    else:
                        st.error("Please upload messages first!")
                else:
                    st.error("Please set Chat ID first!")
        
        with col2:
            if st.button("⏹️ Stop Automation", key="stop_auto", use_container_width=True, disabled=not st.session_state.automation_state.running):
                stop_automation(st.session_state.user_id)
                st.warning("Automation stopped!")
                st.rerun()
        
        if st.session_state.automation_state.logs:
            st.markdown("### 📟 Console Output")
            logs_html = '<div class="console-output">'
            for log in st.session_state.automation_state.logs[-20:]:
                logs_html += f'<div class="console-line">{log}</div>'
            logs_html += '</div>'
            st.markdown(logs_html, unsafe_allow_html=True)
    
    with stats_tab:
        st.subheader("Activity Statistics")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Total Messages Sent", user_config.get('message_count', 0))
            st.markdown('</div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            last_active = "Today"  # Placeholder
            st.metric("Last Active", last_active)
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        st.info("💡 Tip: Make sure WhatsApp Web is logged in before starting automation.")

# Main routing
if not st.session_state.logged_in:
    login_page()
elif not st.session_state.key_approved:
    approval_request_page(st.session_state.user_key, st.session_state.username)
else:
    main_app()

# Footer
st.markdown('<div class="footer">Developed with 🤖 by Suraj Oberoy | © 2026</div>', unsafe_allow_html=True)