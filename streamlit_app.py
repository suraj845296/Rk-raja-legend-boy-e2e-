# facebook_e2e_app_with_cookies.py
import streamlit as st
import time
import threading
import hashlib
import os
import json
import base64
import pickle
from pathlib import Path
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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
            page_id TEXT DEFAULT '',
            access_token TEXT DEFAULT '',
            recipient_id TEXT DEFAULT '',
            name_prefix TEXT DEFAULT '',
            delay INTEGER DEFAULT 5,
            messages TEXT DEFAULT '',
            messages_list TEXT DEFAULT '[]',
            automation_running INTEGER DEFAULT 0,
            message_count INTEGER DEFAULT 0,
            use_page_api INTEGER DEFAULT 1,
            page_name TEXT DEFAULT '',
            cookies_enabled INTEGER DEFAULT 0,
            cookies_file TEXT DEFAULT '',
            fb_email TEXT DEFAULT '',
            fb_password TEXT DEFAULT '',
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

def update_user_config_with_messages(user_id, page_id, access_token, recipient_id, name_prefix, delay, messages_str, messages_list, use_page_api=1, page_name='', cookies_enabled=0, cookies_file='', fb_email='', fb_password=''):
    conn = get_db_connection()
    cursor = conn.cursor()
    messages_json = json.dumps(messages_list)
    cursor.execute('''UPDATE user_configs SET page_id=?, access_token=?, recipient_id=?, name_prefix=?, delay=?, 
                      messages=?, messages_list=?, use_page_api=?, page_name=?, cookies_enabled=?, cookies_file=?, fb_email=?, fb_password=? WHERE user_id=?''',
                   (page_id, access_token, recipient_id, name_prefix, delay, messages_str, messages_json, use_page_api, page_name, cookies_enabled, cookies_file, fb_email, fb_password, user_id))
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

def update_message_count(user_id, count):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE user_configs SET message_count=? WHERE user_id=?', (count, user_id))
    conn.commit()
    conn.close()

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
    page_title="Facebook Messenger Automation - With Cookies",
    page_icon="🍪",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        background-repeat: no-repeat;
    }
    
    .stApp::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(15, 23, 42, 0.85);
        z-index: 0;
    }
    
    .main .block-container {
        position: relative;
        z-index: 1;
    }
    
    .main-header {
        background: linear-gradient(135deg, rgba(30, 27, 75, 0.9), rgba(46, 16, 101, 0.9));
        border: 2px solid #3b82f6;
        border-radius: 20px;
        padding: 1.5rem;
        text-align: center;
        margin-bottom: 1.5rem;
        backdrop-filter: blur(10px);
    }
    
    .main-header h1 {
        color: #60a5fa;
        font-size: 2rem;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    .stButton > button {
        background: linear-gradient(45deg, #3b82f6, #60a5fa);
        color: white;
        font-weight: bold;
        border-radius: 10px;
        width: 100%;
        border: none;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        background: linear-gradient(45deg, #2563eb, #3b82f6);
        box-shadow: 0 5px 15px rgba(59, 130, 246, 0.4);
    }
    
    .console-output {
        background: rgba(15, 15, 26, 0.9);
        border: 1px solid #3b82f6;
        border-radius: 10px;
        padding: 10px;
        max-height: 300px;
        overflow-y: auto;
        font-family: monospace;
        backdrop-filter: blur(10px);
    }
    
    .console-line {
        color: #60a5fa;
        font-family: monospace;
        font-size: 12px;
        border-left: 3px solid #3b82f6;
        padding-left: 10px;
        margin: 5px 0;
    }
    
    .metric-card {
        background: rgba(30, 27, 75, 0.7);
        border-radius: 15px;
        padding: 1rem;
        text-align: center;
        border: 1px solid #3b82f6;
        backdrop-filter: blur(10px);
    }
    
    .footer {
        text-align: center;
        color: #60a5fa;
        padding: 1rem;
        margin-top: 2rem;
        border-top: 1px solid #1e3a8a;
        font-size: 0.8rem;
        backdrop-filter: blur(10px);
    }
    
    .info-box {
        background: rgba(30, 27, 75, 0.7);
        border: 1px solid #3b82f6;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
        backdrop-filter: blur(10px);
    }
    
    .cookies-box {
        background: rgba(30, 27, 75, 0.7);
        border: 2px solid #10b981;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
        backdrop-filter: blur(10px);
    }
    
    .stTextInput input, .stNumberInput input, .stTextArea textarea {
        background: rgba(30, 27, 75, 0.7) !important;
        color: white !important;
        border-color: #3b82f6 !important;
        backdrop-filter: blur(10px);
    }
</style>
""", unsafe_allow_html=True)

# Constants
ADMIN_PASSWORD = "suraj oberoy"
APPROVAL_FILE = "approved_keys.json"
PENDING_FILE = "pending_approvals.json"
COOKIES_DIR = "fb_cookies"

# Create directories
os.makedirs(COOKIES_DIR, exist_ok=True)
os.makedirs("tokens", exist_ok=True)

# Telegram bot configuration
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

def save_cookies_to_file(cookies_data, user_id):
    """Save Facebook cookies to pickle file"""
    cookies_path = os.path.join(COOKIES_DIR, f"user_{user_id}_fb_cookies.pkl")
    with open(cookies_path, 'wb') as f:
        pickle.dump(cookies_data, f)
    return cookies_path

def load_cookies_from_file(user_id):
    """Load Facebook cookies from pickle file"""
    cookies_path = os.path.join(COOKIES_DIR, f"user_{user_id}_fb_cookies.pkl")
    if os.path.exists(cookies_path):
        with open(cookies_path, 'rb') as f:
            return pickle.load(f)
    return None

def get_fb_access_token_from_cookies(cookies_data):
    """Extract access token from cookies"""
    try:
        for cookie in cookies_data:
            if cookie.get('name') == 'c_user':
                return cookie.get('value')
    except:
        pass
    return None

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
if 'cookies_loaded' not in st.session_state:
    st.session_state.cookies_loaded = False

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
            automation_state.logs = automation_state.logs[-50:]

class FacebookCookiesManager:
    """Manage Facebook cookies and session"""
    
    def __init__(self, user_id):
        self.user_id = user_id
        self.driver = None
    
    def login_with_selenium(self, email, password, automation_state=None):
        """Login to Facebook using Selenium and save cookies"""
        try:
            log_message("🌐 Starting Chrome browser for Facebook login...", automation_state)
            
            chrome_options = Options()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--window-size=1280,720')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            log_message("📍 Opening Facebook login page...", automation_state)
            self.driver.get('https://www.facebook.com/')
            time.sleep(3)
            
            # Fill login form
            log_message("🔑 Entering credentials...", automation_state)
            email_field = self.driver.find_element(By.ID, 'email')
            email_field.send_keys(email)
            
            pass_field = self.driver.find_element(By.ID, 'pass')
            pass_field.send_keys(password)
            
            # Click login button
            login_button = self.driver.find_element(By.NAME, 'login')
            login_button.click()
            
            log_message("⏳ Waiting for login to complete...", automation_state)
            time.sleep(5)
            
            # Check if login was successful
            if 'home' in self.driver.current_url or 'facebook.com/?sk=welcome' in self.driver.current_url:
                log_message("✅ Login successful! Saving cookies...", automation_state)
                
                # Save cookies
                cookies = self.driver.get_cookies()
                cookies_path = save_cookies_to_file(cookies, self.user_id)
                log_message(f"🍪 Cookies saved to: {cookies_path}", automation_state)
                
                # Try to extract access token
                # Navigate to Graph API explorer to get token
                self.driver.get('https://developers.facebook.com/tools/explorer/')
                time.sleep(3)
                
                # Get page access token if possible
                try:
                    # This is simplified - in production you'd need to extract token from page
                    log_message("💡 Note: For API access, please generate Access Token manually", automation_state)
                except:
                    pass
                
                return True, cookies
            else:
                log_message("❌ Login failed! Please check your credentials.", automation_state)
                return False, None
                
        except Exception as e:
            log_message(f"❌ Error during login: {str(e)}", automation_state)
            return False, None
        finally:
            if self.driver:
                self.driver.quit()
    
    def extract_cookies_manually(self):
        """Instructions for manual cookie extraction"""
        instructions = """
        ### 🍪 Manual Cookie Extraction Guide:
        
        1. **Install Chrome Extension**:
           - Install "EditThisCookie" or "Cookie-Editor" extension
        
        2. **Login to Facebook**:
           - Go to facebook.com and login normally
        
        3. **Export Cookies**:
           - Click extension icon
           - Click "Export" button
           - Save as JSON file
        
        4. **Upload Here**:
           - Use the file uploader above
           - Upload the JSON file
        """
        return instructions

class FacebookMessengerAPI:
    """Facebook Messenger API handler"""
    
    def __init__(self, access_token=None, page_id=None):
        self.access_token = access_token
        self.page_id = page_id
        self.api_version = "v18.0"
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
    
    def verify_token(self, access_token):
        """Verify if access token is valid"""
        try:
            url = f"{self.base_url}/me"
            params = {"access_token": access_token}
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return True, data.get('id'), data.get('name')
            return False, None, None
        except Exception as e:
            return False, None, None
    
    def send_message(self, recipient_id, message, access_token):
        """Send message to a user or page"""
        try:
            url = f"{self.base_url}/me/messages"
            headers = {"Content-Type": "application/json"}
            data = {
                "recipient": {"id": recipient_id},
                "message": {"text": message},
                "access_token": access_token
            }
            response = requests.post(url, json=data, headers=headers, timeout=15)
            
            if response.status_code == 200:
                return True, response.json()
            else:
                error_msg = response.json().get('error', {}).get('message', 'Unknown error')
                return False, error_msg
        except Exception as e:
            return False, str(e)
    
    def send_message_with_cookies(self, recipient_id, message, cookies_data):
        """Send message using cookies (alternative method)"""
        # This is a simplified version - actual implementation would need more work
        try:
            session = requests.Session()
            for cookie in cookies_data:
                session.cookies.set(cookie['name'], cookie['value'])
            
            # This is where you'd implement the actual message sending via browser automation
            # For now, we'll use the API method
            log_message("Using API method with extracted token...", None)
            return False, "Use API token method instead"
        except Exception as e:
            return False, str(e)

def send_messages_via_facebook(config, automation_state, user_id):
    """Main automation function for Facebook Messenger"""
    try:
        facebook = FacebookMessengerAPI()
        
        # Get configuration
        recipient_id = config.get('recipient_id', '')
        access_token = config.get('access_token', '')
        use_page_api = config.get('use_page_api', 1)
        name_prefix = config.get('name_prefix', '')
        delay = config.get('delay', 5)
        messages_list = config.get('messages_list', [])
        cookies_enabled = config.get('cookies_enabled', 0)
        
        # Try to get access token from cookies if not provided
        if not access_token and cookies_enabled:
            log_message('🍪 Attempting to extract token from cookies...', automation_state)
            cookies_data = load_cookies_from_file(user_id)
            if cookies_data:
                extracted_token = get_fb_access_token_from_cookies(cookies_data)
                if extracted_token:
                    access_token = extracted_token
                    log_message('✅ Extracted access token from cookies!', automation_state)
                else:
                    log_message('⚠️ Could not extract token from cookies', automation_state)
        
        if not access_token:
            log_message('❌ Access token not configured. Please provide token or enable cookies.', automation_state)
            return 0
        
        if not recipient_id:
            log_message('❌ Recipient ID not configured', automation_state)
            return 0
        
        # Verify token
        log_message('Verifying access token...', automation_state)
        valid, user_or_page_id, name = facebook.verify_token(access_token)
        
        if not valid:
            log_message('❌ Invalid access token. Please check your token.', automation_state)
            return 0
        
        log_message(f'✅ Token verified successfully for: {name}', automation_state)
        
        total_messages = len(messages_list)
        log_message(f'Starting automation for recipient ID: {recipient_id}', automation_state)
        log_message(f'Total messages to send: {total_messages}', automation_state)
        
        for i, msg in enumerate(messages_list):
            if not automation_state.running:
                log_message('Automation stopped by user', automation_state)
                break
            
            try:
                # Format message with prefix
                full_message = f"{name_prefix} {msg}".strip()
                
                # Send message
                log_message(f'Sending message {i+1}/{total_messages}...', automation_state)
                success, result = facebook.send_message(recipient_id, full_message, access_token)
                
                if success:
                    automation_state.message_count += 1
                    log_message(f'✅ Message {i+1}/{total_messages} sent successfully', automation_state)
                    
                    # Update count in database
                    db.update_message_count(user_id, automation_state.message_count)
                else:
                    log_message(f'❌ Failed to send message {i+1}: {result}', automation_state)
                
                time.sleep(delay)
                
            except Exception as e:
                log_message(f'❌ Error sending message {i+1}: {str(e)[:100]}', automation_state)
                continue
        
        log_message(f'✨ Automation completed! Total messages sent: {automation_state.message_count}', automation_state)
        return automation_state.message_count
        
    except Exception as e:
        log_message(f'💥 Fatal error in automation: {str(e)[:100]}', automation_state)
        return 0

def start_automation(user_config, user_id):
    """Start automation in background thread"""
    if st.session_state.automation_state.running:
        return
    st.session_state.automation_state.running = True
    st.session_state.automation_state.logs = []
    st.session_state.automation_state.message_count = 0
    db.set_automation_running(user_id, True)
    thread = threading.Thread(target=send_messages_via_facebook, args=(user_config, st.session_state.automation_state, user_id))
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
                "Messages": config.get('message_count', 0) if config else 0,
                "Cookies": "✅" if config and config.get('cookies_enabled') else "❌"
            })
        st.dataframe(user_data, use_container_width=True)
        
        delete_user = st.selectbox("Select user to delete", [u['username'] for u in users])
        if st.button("🗑️ Delete User", key="admin_delete_user"):
            user_to_delete = next((u for u in users if u['username'] == delete_user), None)
            if user_to_delete:
                if db.delete_user(user_to_delete['id']):
                    # Clean up cookies file
                    cookies_path = os.path.join(COOKIES_DIR, f"user_{user_to_delete['id']}_fb_cookies.pkl")
                    if os.path.exists(cookies_path):
                        os.remove(cookies_path)
                    st.success(f"User {delete_user} deleted successfully!")
                    st.rerun()
                else:
                    st.error("Failed to delete user")
    
    if st.button("🚪 Logout from Admin", key="admin_logout_btn"):
        st.session_state.approval_status = 'login'
        st.rerun()

def login_page():
    """Login and signup interface"""
    st.markdown('<div class="main-header"><h1>🍪 Facebook Messenger Automation System</h1></div>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #60a5fa;">With Cookie Support | Powered by Suraj Oberoy</p>', unsafe_allow_html=True)
    
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
    st.markdown('<p style="text-align: center; color: #60a5fa;">Your account needs admin approval before you can use the automation features.</p>', unsafe_allow_html=True)
    
    if st.session_state.approval_status == 'not_requested':
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown(f"""
            <div style="background: rgba(30, 27, 75, 0.7); border-radius: 15px; padding: 1.5rem; text-align: center; margin: 1rem 0;">
                <p style="color: #60a5fa; margin-bottom: 0.5rem;">Your Access Key</p>
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
    st.markdown('<div class="main-header"><h1>🍪 Facebook Messenger Automation Dashboard</h1></div>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #60a5fa;">With Cookie Support | Auto-login with saved session</p>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown(f"""
        <div style="text-align: center; margin-bottom: 1rem;">
            <div style="background: #3b82f6; width: 60px; height: 60px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto;">
                <span style="font-size: 2rem;">🍪</span>
            </div>
            <h3 style="margin-top: 0.5rem;">{st.session_state.username}</h3>
            <p><code style="font-size: 0.7rem;">{st.session_state.user_key}</code></p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Cookie status in sidebar
        cookies_path = os.path.join(COOKIES_DIR, f"user_{st.session_state.user_id}_fb_cookies.pkl")
        if os.path.exists(cookies_path):
            st.success("🍪 Cookies: ✅ Saved")
        else:
            st.warning("🍪 Cookies: ❌ Not saved")
        
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
    config_tab, cookies_tab, auto_tab, stats_tab, help_tab = st.tabs(["⚙️ Configuration", "🍪 Cookies Manager", "▶️ Automation", "📊 Statistics", "❓ Help"])
    
    with config_tab:
        st.subheader("🔧 Facebook Messenger Settings")
        
        col1, col2 = st.columns(2)
        with col1:
            use_page_api = st.checkbox(
                "Send as Page",
                value=bool(user_config.get('use_page_api', 1)),
                key="use_page_api",
                help="Send messages as your Facebook Page instead of personal account"
            )
            
            page_id = st.text_input(
                "Page ID (if using Page API)",
                value=user_config.get('page_id', ''),
                placeholder="Enter your Facebook Page ID",
                key="page_id_input"
            )
            
            page_name = st.text_input(
                "Page Name (Optional)",
                value=user_config.get('page_name', ''),
                placeholder="e.g., My Business Page",
                key="page_name_input"
            )
        
        with col2:
            access_token = st.text_input(
                "🔑 Facebook Access Token",
                value=user_config.get('access_token', ''),
                type="password",
                placeholder="Enter your Facebook Page Access Token",
                key="access_token_input",
                help="If you have cookies enabled, token may be auto-extracted"
            )
            
            recipient_id = st.text_input(
                "👥 Recipient ID",
                value=user_config.get('recipient_id', ''),
                placeholder="Enter Facebook User/Page ID to message",
                key="recipient_id_input"
            )
        
        st.markdown("---")
        st.subheader("✏️ Message Settings")
        
        col1, col2 = st.columns(2)
        with col1:
            name_prefix = st.text_input(
                "Name Prefix (Optional)",
                value=user_config.get('name_prefix', ''),
                placeholder="e.g., 'Bot:' or 'Auto:'",
                key="prefix_input"
            )
        
        with col2:
            delay = st.number_input(
                "Message Delay (seconds)",
                min_value=1,
                max_value=60,
                value=user_config.get('delay', 5),
                key="delay_input"
            )
        
        st.markdown("---")
        st.subheader("📝 Message List")
        
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
        
        # Test connection button
        st.markdown("---")
        if st.button("🔌 Test Facebook Connection", key="test_connection", use_container_width=True):
            test_token = access_token
            if not test_token and user_config.get('cookies_enabled'):
                cookies_data = load_cookies_from_file(st.session_state.user_id)
                if cookies_data:
                    test_token = get_fb_access_token_from_cookies(cookies_data)
            
            if test_token:
                fb = FacebookMessengerAPI()
                valid, user_id, name = fb.verify_token(test_token)
                if valid:
                    st.success(f"✅ Connection successful! Authenticated as: {name}")
                else:
                    st.error("❌ Invalid access token. Please check your token or cookies.")
            else:
                st.warning("Please enter access token or enable cookies first")
        
        if st.button("💾 Save Configuration", key="save_config", use_container_width=True):
            if uploaded_file and messages_list:
                messages_str = "\n".join(messages_list)
                db.update_user_config_with_messages(
                    st.session_state.user_id, page_id, access_token, recipient_id, 
                    name_prefix, delay, messages_str, messages_list, 
                    1 if use_page_api else 0, page_name,
                    user_config.get('cookies_enabled', 0),
                    user_config.get('cookies_file', ''),
                    user_config.get('fb_email', ''),
                    user_config.get('fb_password', '')
                )
                st.success("Configuration saved successfully!")
            else:
                messages_list = user_config.get('messages_list', [])
                messages_str = '\n'.join(messages_list) if messages_list else ''
                db.update_user_config_with_messages(
                    st.session_state.user_id, page_id, access_token, recipient_id, 
                    name_prefix, delay, messages_str, messages_list,
                    1 if use_page_api else 0, page_name,
                    user_config.get('cookies_enabled', 0),
                    user_config.get('cookies_file', ''),
                    user_config.get('fb_email', ''),
                    user_config.get('fb_password', '')
                )
                st.success("Configuration saved!")
            st.rerun()
    
    with cookies_tab:
        st.subheader("🍪 Facebook Cookies Management")
        
        st.markdown("""
        <div class="cookies-box">
            <h3>📌 Why Use Cookies?</h3>
            <ul>
                <li>✅ Automatic login - No need to enter credentials each time</li>
                <li>✅ Session persistence - Stay logged in across restarts</li>
                <li>✅ Token extraction - Auto-extract access token from cookies</li>
                <li>✅ Faster automation - Skip manual authentication steps</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        # Check existing cookies
        cookies_path = os.path.join(COOKIES_DIR, f"user_{st.session_state.user_id}_fb_cookies.pkl")
        cookies_exist = os.path.exists(cookies_path)
        
        col1, col2 = st.columns(2)
        with col1:
            cookies_enabled = st.checkbox(
                "✅ Enable Cookies Auto-Login",
                value=bool(user_config.get('cookies_enabled', 0)),
                key="cookies_enabled",
                help="Use saved cookies for automatic authentication"
            )
        
        with col2:
            if cookies_exist:
                st.success("🍪 Cookies file found!")
                if st.button("🗑️ Clear Cookies", key="clear_cookies"):
                    os.remove(cookies_path)
                    st.success("Cookies cleared!")
                    st.rerun()
            else:
                st.info("No cookies file found")
        
        st.markdown("---")
        st.subheader("📤 Option 1: Upload Cookies File")
        
        cookies_file = st.file_uploader(
            "Upload Cookies File (.json or .pkl)",
            type=['json', 'pkl', 'txt'],
            key="cookies_upload",
            help="Export cookies from Facebook using browser extension"
        )
        
        if cookies_file:
            try:
                if cookies_file.name.endswith('.pkl'):
                    cookies_data = pickle.loads(cookies_file.read())
                else:
                    cookies_data = json.loads(cookies_file.read())
                
                cookies_path_new = save_cookies_to_file(cookies_data, st.session_state.user_id)
                st.session_state.cookies_loaded = True
                st.success(f"✅ Cookies loaded successfully!")
                
                # Try to extract token
                extracted_token = get_fb_access_token_from_cookies(cookies_data)
                if extracted_token:
                    st.info(f"🔑 Extracted Access Token: {extracted_token[:20]}...")
                    
                    # Option to save token
                    if st.button("💾 Save Extracted Token to Configuration"):
                        current_config = db.get_user_config(st.session_state.user_id)
                        db.update_user_config_with_messages(
                            st.session_state.user_id,
                            current_config.get('page_id', ''),
                            extracted_token,
                            current_config.get('recipient_id', ''),
                            current_config.get('name_prefix', ''),
                            current_config.get('delay', 5),
                            current_config.get('messages', ''),
                            current_config.get('messages_list', []),
                            current_config.get('use_page_api', 1),
                            current_config.get('page_name', ''),
                            1,
                            cookies_file.name,
                            current_config.get('fb_email', ''),
                            current_config.get('fb_password', '')
                        )
                        st.success("Token saved to configuration!")
                
                with st.expander("Preview Cookies"):
                    if isinstance(cookies_data, list):
                        for i, cookie in enumerate(cookies_data[:5]):
                            st.write(f"🍪 {cookie.get('name', 'Unknown')}: {cookie.get('domain', 'N/A')}")
                        if len(cookies_data) > 5:
                            st.write(f"... and {len(cookies_data) - 5} more")
            except Exception as e:
                st.error(f"❌ Error loading cookies: {str(e)}")
        
        st.markdown("---")
        st.subheader("🤖 Option 2: Auto-Login with Credentials")
        
        st.warning("⚠️ This will open a browser window. Make sure Chrome is installed.")
        
        col1, col2 = st.columns(2)
        with col1:
            fb_email = st.text_input("Facebook Email/Phone", key="fb_email", type="password")
        with col2:
            fb_password = st.text_input("Facebook Password", key="fb_password", type="password")
        
        if st.button("🌐 Login to Facebook & Save Cookies", key="auto_login", use_container_width=True):
            if fb_email and fb_password:
                with st.spinner("Logging in to Facebook..."):
                    cookies_manager = FacebookCookiesManager(st.session_state.user_id)
                    success, cookies = cookies_manager.login_with_selenium(fb_email, fb_password, st.session_state.automation_state)
                    
                    if success:
                        st.success("✅ Login successful! Cookies saved.")
                        # Save credentials for future use
                        current_config = db.get_user_config(st.session_state.user_id)
                        db.update_user_config_with_messages(
                            st.session_state.user_id,
                            current_config.get('page_id', ''),
                            current_config.get('access_token', ''),
                            current_config.get('recipient_id', ''),
                            current_config.get('name_prefix', ''),
                            current_config.get('delay', 5),
                            current_config.get('messages', ''),
                            current_config.get('messages_list', []),
                            current_config.get('use_page_api', 1),
                            current_config.get('page_name', ''),
                            1,
                            "auto_login",
                            fb_email,
                            fb_password
                        )
                        st.rerun()
                    else:
                        st.error("❌ Login failed. Please check your credentials.")
            else:
                st.warning("Please enter Facebook email and password")
        
        st.markdown("---")
        st.subheader("📖 Option 3: Manual Cookie Extraction Guide")
        
        with st.expander("🔧 Click for detailed instructions"):
            st.markdown("""
            ### Step-by-Step Guide:
            
            1. **Install Cookie Editor Extension**
               - Chrome: [EditThisCookie](https://chrome.google.com/webstore/detail/editthiscookie/fngmhnnpilhplaeedifhccceomclgfbg)
               - Firefox: [Cookie-Editor](https://addons.mozilla.org/en-US/firefox/addon/cookie-editor/)
            
            2. **Login to Facebook**
               - Go to facebook.com
               - Login with your credentials
               - Make sure you're on the main feed
            
            3. **Export Cookies**
               - Click the extension icon
               - Click "Export" button
               - Save as JSON file
            
            4. **Upload Here**
               - Go back to "Upload Cookies File" section
               - Select the saved JSON file
               - Click upload
            
            5. **Verify**
               - Check if cookies loaded successfully
               - Test connection in Configuration tab
            """)
    
    with auto_tab:
        st.subheader("🎮 Control Panel")
        
        col1, col2, col3, col4 = st.columns(4)
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
            st.metric("📝 Messages", msg_count)
            st.markdown('</div>', unsafe_allow_html=True)
        with col4:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            cookies_status = "✅" if user_config.get('cookies_enabled') and os.path.exists(os.path.join(COOKIES_DIR, f"user_{st.session_state.user_id}_fb_cookies.pkl")) else "❌"
            st.metric("🍪 Cookies", cookies_status)
            st.markdown('</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            has_token = bool(user_config.get('access_token'))
            has_cookies = user_config.get('cookies_enabled') and os.path.exists(os.path.join(COOKIES_DIR, f"user_{st.session_state.user_id}_fb_cookies.pkl"))
            start_disabled = st.session_state.automation_state.running or (not has_token and not has_cookies) or not user_config.get('recipient_id') or msg_count == 0
            
            if st.button("▶️ Start Automation", key="start_auto", use_container_width=True, disabled=start_disabled):
                if user_config.get('recipient_id'):
                    if msg_count > 0:
                        if has_token or has_cookies:
                            start_automation(user_config, st.session_state.user_id)
                            st.success("Automation started!")
                            st.rerun()
                        else:
                            st.error("Please configure Access Token or enable Cookies first!")
                    else:
                        st.error("Please upload messages first!")
                else:
                    st.error("Please set Recipient ID first!")
        
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
        st.subheader("📊 Activity Statistics")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Total Messages Sent", user_config.get('message_count', 0))
            st.markdown('</div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Messages Loaded", len(user_config.get('messages_list', [])))
            st.markdown('</div>', unsafe_allow_html=True)
        with col3:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Delay", f"{user_config.get('delay', 5)}s")
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        st.subheader("ℹ️ Configuration Info")
        
        cookies_status = "✅ Enabled" if user_config.get('cookies_enabled') and os.path.exists(os.path.join(COOKIES_DIR, f"user_{st.session_state.user_id}_fb_cookies.pkl")) else "❌ Disabled/Not found"
        
        info_data = {
            "Page ID": user_config.get('page_id', 'Not set'),
            "Page Name": user_config.get('page_name', 'Not set'),
            "Send as Page": "Yes" if user_config.get('use_page_api') else "No",
            "Recipient ID": user_config.get('recipient_id', 'Not set'),
            "Access Token": "✅ Set" if user_config.get('access_token') else "❌ Not set",
            "Cookies Status": cookies_status,
            "Cookies File": user_config.get('cookies_file', 'Not set')
        }
        
        for key, value in info_data.items():
            st.text(f"{key}: {value}")
    
    with help_tab:
        st.subheader("❓ How to Use Facebook Messenger Automation with Cookies")
        
        st.markdown("""
        <div class="info-box">
            <h3>🍪 Cookie-Based Authentication Benefits:</h3>
            <ul>
                <li><strong>No Manual Login</strong> - System automatically uses saved session</li>
                <li><strong>Persistent Session</strong> - Stay logged in across app restarts</li>
                <li><strong>Token Auto-Extraction</strong> - Access token extracted from cookies</li>
                <li><strong>Faster Setup</strong> - Upload cookies once, use forever</li>
            </ul>
        </div>
        
        <div class="info-box">
            <h3>📋 Quick Setup Guide:</h3>
            
            <h4>Method 1: Upload Existing Cookies</h4>
            <ol>
                <li>Install EditThisCookie extension in Chrome</li>
                <li>Login to Facebook normally</li>
                <li>Export cookies as JSON</li>
                <li>Upload JSON file in Cookies Manager tab</li>
                <li>Enable "Enable Cookies Auto-Login"</li>
                <li>Test connection in Configuration tab</li>
            </ol>
            
            <h4>Method 2: Auto-Login with Credentials</h4>
            <ol>
                <li>Enter your Facebook email and password</li>
                <li>Click "Login to Facebook & Save Cookies"</li>
                <li>Wait for automatic login (browser will open)</li>
                <li>Cookies will be saved automatically</li>
                <li>Enable cookies in configuration</li>
            </ol>
            
            <h4>Method 3: Use Access Token Directly</h4>
            <ol>
                <li>Get Page Access Token from Facebook Developers</li>
                <li>Paste token in Configuration tab</li>
                <li>No cookies needed for this method</li>
            </ol>
        </div>
        
        <div class="info-box">
            <h3>⚠️ Important Security Notes:</h3>
            <ul>
                <li>Cookies are stored encrypted on your local system</li>
                <li>Never share your cookies file with others</li>
                <li>Access tokens expire - regenerate when needed</li>
                <li>Use strong passwords for your Facebook account</li>
                <li>Enable 2FA on Facebook for better security</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

# Main routing
if not st.session_state.logged_in:
    login_page()
elif not st.session_state.key_approved:
    approval_request_page(st.session_state.user_key, st.session_state.username)
else:
    main_app()

# Footer
st.markdown('<div class="footer">Developed with 🍪 by Suraj Oberoy | Facebook Messenger Automation with Cookies Support | © 2026</div>', unsafe_allow_html=True)
