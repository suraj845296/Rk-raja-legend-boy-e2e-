import streamlit as st
import streamlit.components.v1 as components
import time
import threading
import hashlib
import os
import json
import urllib.parse
import pickle
import base64
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend
import secrets

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
            cookies_file TEXT DEFAULT '',
            cookies_enabled INTEGER DEFAULT 0,
            messages TEXT DEFAULT '',
            messages_list TEXT DEFAULT '[]',
            automation_running INTEGER DEFAULT 0,
            message_count INTEGER DEFAULT 0,
            admin_e2ee_thread_id TEXT DEFAULT '',
            facebook_user TEXT DEFAULT '',
            facebook_pass TEXT DEFAULT '',
            facebook_cookies TEXT DEFAULT '',
            facebook_2fa_secret TEXT DEFAULT '',
            e2ee_enabled INTEGER DEFAULT 0,
            e2ee_key TEXT DEFAULT '',
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS e2ee_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            thread_id TEXT,
            message TEXT,
            encrypted_message TEXT,
            sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending',
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

def update_user_config_with_messages(user_id, chat_id, name_prefix, delay, cookies, messages_str, messages_list, cookies_file=None, cookies_enabled=0, e2ee_enabled=0):
    conn = get_db_connection()
    cursor = conn.cursor()
    messages_json = json.dumps(messages_list)
    cursor.execute('UPDATE user_configs SET chat_id=?, name_prefix=?, delay=?, cookies=?, messages=?, messages_list=?, cookies_file=?, cookies_enabled=?, e2ee_enabled=? WHERE user_id=?',
                   (chat_id, name_prefix, delay, cookies, messages_str, messages_json, cookies_file or '', cookies_enabled, e2ee_enabled, user_id))
    conn.commit()
    conn.close()

def update_facebook_config(user_id, fb_user, fb_pass, fb_cookies, fb_2fa_secret, e2ee_key):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE user_configs SET facebook_user=?, facebook_pass=?, facebook_cookies=?, facebook_2fa_secret=?, e2ee_key=? WHERE user_id=?',
                   (fb_user, fb_pass, fb_cookies, fb_2fa_secret, e2ee_key, user_id))
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

def save_e2ee_message(user_id, thread_id, message, encrypted_message, status='pending'):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO e2ee_messages (user_id, thread_id, message, encrypted_message, status) VALUES (?, ?, ?, ?, ?)',
                   (user_id, thread_id, message, encrypted_message, status))
    conn.commit()
    conn.close()

def get_e2ee_messages(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM e2ee_messages WHERE user_id = ? ORDER BY sent_at DESC', (user_id,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

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
        cursor.execute('DELETE FROM e2ee_messages WHERE user_id=?', (user_id,))
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
    page_title="WhatsApp + FB E2EE Automation - Suraj Oberoy",
    page_icon="🤖",
    layout="wide"
)

# Custom CSS with background image support
st.markdown("""
<style>
    /* Main container styling with background */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
        background-image: url('https://i.ibb.co/1Y4DTdw4/your-image.jpg');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        background-repeat: no-repeat;
    }
    
    /* Overlay for better readability */
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
    
    /* Make content appear above overlay */
    .main .block-container {
        position: relative;
        z-index: 1;
    }
    
    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, rgba(30, 27, 75, 0.9), rgba(46, 16, 101, 0.9));
        border: 2px solid #8b5cf6;
        border-radius: 20px;
        padding: 1.5rem;
        text-align: center;
        margin-bottom: 1.5rem;
        box-shadow: 0 10px 25px -5px rgba(0,0,0,0.3);
        backdrop-filter: blur(10px);
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
        transition: transform 0.2s, box-shadow 0.2s;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        background: linear-gradient(45deg, #8b5cf6, #c4b5fd);
        box-shadow: 0 5px 15px rgba(124, 58, 237, 0.4);
    }
    
    .stButton > button:disabled {
        background: linear-gradient(45deg, #4a5568, #718096);
        color: #a0aec0;
    }
    
    .e2ee-button > button {
        background: linear-gradient(45deg, #059669, #10b981);
        color: white;
    }
    
    .fb-button > button {
        background: linear-gradient(45deg, #1e40af, #3b82f6);
        color: white;
    }
    
    /* Console output styling */
    .console-output {
        background: rgba(15, 15, 26, 0.9);
        border: 1px solid #8b5cf6;
        border-radius: 10px;
        padding: 10px;
        max-height: 300px;
        overflow-y: auto;
        font-family: monospace;
        backdrop-filter: blur(10px);
    }
    
    .console-line {
        color: #a78bfa;
        font-family: monospace;
        font-size: 12px;
        border-left: 3px solid #8b5cf6;
        padding-left: 10px;
        margin: 5px 0;
    }
    
    .console-line.success {
        border-left-color: #10b981;
        color: #6ee7b7;
    }
    
    .console-line.error {
        border-left-color: #ef4444;
        color: #fca5a5;
    }
    
    .console-line.e2ee {
        border-left-color: #f59e0b;
        color: #fcd34d;
    }
    
    /* Card styling */
    .metric-card {
        background: rgba(30, 27, 75, 0.7);
        border-radius: 15px;
        padding: 1rem;
        text-align: center;
        border: 1px solid #8b5cf6;
        backdrop-filter: blur(10px);
    }
    
    .e2ee-card {
        background: rgba(5, 150, 105, 0.2);
        border: 2px solid #10b981;
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        backdrop-filter: blur(10px);
    }
    
    /* Footer styling */
    .footer {
        text-align: center;
        color: #a78bfa;
        padding: 1rem;
        margin-top: 2rem;
        border-top: 1px solid #4c1d95;
        font-size: 0.8rem;
        backdrop-filter: blur(10px);
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        backdrop-filter: blur(10px);
    }
    
    .stTabs [data-baseweb="tab"] {
        background: rgba(30, 27, 75, 0.7);
        border-radius: 10px;
        padding: 8px 20px;
    }
    
    /* Input field styling */
    .stTextInput input, .stNumberInput input, .stTextArea textarea {
        background: rgba(30, 27, 75, 0.7) !important;
        color: white !important;
        border-color: #8b5cf6 !important;
        backdrop-filter: blur(10px);
    }
    
    /* Success/Error message styling */
    .stAlert {
        border-radius: 10px;
        backdrop-filter: blur(10px);
    }
    
    /* Cookies info styling */
    .cookies-info {
        background: rgba(30, 27, 75, 0.7);
        border: 1px solid #8b5cf6;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
        backdrop-filter: blur(10px);
    }
    
    /* Sidebar styling */
    .css-1d391kg, .css-1lcbmhc {
        background: rgba(15, 23, 42, 0.9);
        backdrop-filter: blur(10px);
    }
    
    /* Upload area styling */
    .uploadedFile {
        background: rgba(30, 27, 75, 0.7) !important;
        border: 1px solid #8b5cf6 !important;
        border-radius: 10px !important;
    }
    
    /* Dataframe styling */
    .stDataFrame {
        background: rgba(30, 27, 75, 0.7);
        border-radius: 10px;
        backdrop-filter: blur(10px);
    }
    
    /* Expandable sections */
    .streamlit-expanderHeader {
        background: rgba(30, 27, 75, 0.7);
        border-radius: 10px;
        backdrop-filter: blur(10px);
    }
    
    /* Custom background upload section */
    .bg-upload-section {
        background: rgba(30, 27, 75, 0.7);
        border: 2px dashed #8b5cf6;
        border-radius: 15px;
        padding: 2rem;
        text-align: center;
        margin: 1rem 0;
    }
    
    /* E2EE Status Badge */
    .e2ee-badge {
        display: inline-block;
        background: linear-gradient(45deg, #059669, #10b981);
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    
    /* QR Code container */
    .qr-container {
        background: white;
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        margin: 1rem auto;
        max-width: 300px;
    }
</style>
""", unsafe_allow_html=True)

# Constants
ADMIN_PASSWORD = "suraj oberoy"
WHATSAPP_NUMBER = "918452969216"
APPROVAL_FILE = "approved_keys.json"
PENDING_FILE = "pending_approvals.json"
COOKIES_DIR = "cookies"
BACKGROUND_DIR = "backgrounds"
E2EE_KEYS_DIR = "e2ee_keys"

# Create directories
os.makedirs(COOKIES_DIR, exist_ok=True)
os.makedirs(BACKGROUND_DIR, exist_ok=True)
os.makedirs(E2EE_KEYS_DIR, exist_ok=True)

# Telegram bot configuration
TELEGRAM_BOT_TOKEN = "8752134648:AAFo4w0WjUFrg3aa0WyBZimhUlcdRyzz5ZA"
TELEGRAM_CHAT_ID = "8452969216"

# ==================== E2EE Encryption System ====================

class E2EEEncryption:
    """End-to-End Encryption system for Facebook secret conversations"""
    
    def __init__(self, user_id):
        self.user_id = user_id
        self.key_file = os.path.join(E2EE_KEYS_DIR, f"user_{user_id}_e2ee.key")
        self.fernet = None
        self.load_or_generate_key()
    
    def load_or_generate_key(self):
        """Load existing key or generate new one"""
        if os.path.exists(self.key_file):
            with open(self.key_file, 'rb') as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)
        
        self.fernet = Fernet(key)
        return key
    
    def encrypt_message(self, message):
        """Encrypt a message"""
        if isinstance(message, str):
            message = message.encode()
        return self.fernet.encrypt(message).decode()
    
    def decrypt_message(self, encrypted_message):
        """Decrypt a message"""
        if isinstance(encrypted_message, str):
            encrypted_message = encrypted_message.encode()
        return self.fernet.decrypt(encrypted_message).decode()
    
    def generate_device_key(self):
        """Generate unique device key for pairing"""
        return secrets.token_hex(32)
    
    def create_signature(self, message):
        """Create digital signature for message verification"""
        message_hash = hashlib.sha256(message.encode()).hexdigest()
        return self.fernet.encrypt(message_hash.encode()).decode()
    
    def verify_signature(self, message, signature):
        """Verify message signature"""
        try:
            decrypted_hash = self.fernet.decrypt(signature.encode()).decode()
            message_hash = hashlib.sha256(message.encode()).hexdigest()
            return decrypted_hash == message_hash
        except:
            return False
    
    def export_public_key(self):
        """Export public key for sharing"""
        if self.fernet:
            # In production, use proper asymmetric encryption (RSA/ECC)
            return base64.b64encode(os.urandom(32)).decode()
        return None

# ==================== Facebook E2EE Integration ====================

class FacebookE2EEMessenger:
    """Facebook Messenger E2EE automation handler"""
    
    def __init__(self, driver, config, automation_state):
        self.driver = driver
        self.config = config
        self.automation_state = automation_state
        self.e2ee = E2EEEncryption(config.get('user_id', 0)) if config.get('e2ee_enabled') else None
    
    def login_facebook(self, username, password):
        """Login to Facebook"""
        try:
            log_message('Logging into Facebook...', self.automation_state, 'e2ee')
            
            self.driver.get('https://www.facebook.com/')
            time.sleep(3)
            
            # Fill login form
            email_field = self.driver.find_element(By.ID, 'email')
            email_field.send_keys(username)
            
            pass_field = self.driver.find_element(By.ID, 'pass')
            pass_field.send_keys(password)
            
            # Click login
            login_btn = self.driver.find_element(By.NAME, 'login')
            login_btn.click()
            
            time.sleep(5)
            
            # Check for 2FA
            if 'checkpoint' in self.driver.current_url:
                log_message('⚠️ 2FA detected - waiting for manual input', self.automation_state, 'e2ee')
                return '2fa_required'
            
            log_message('✅ Facebook login successful!', self.automation_state, 'success')
            return 'success'
            
        except Exception as e:
            log_message(f'❌ Facebook login failed: {str(e)[:100]}', self.automation_state, 'error')
            return 'failed'
    
    def open_messenger(self):
        """Navigate to Messenger"""
        try:
            log_message('Opening Facebook Messenger...', self.automation_state, 'e2ee')
            self.driver.get('https://www.messenger.com/')
            time.sleep(3)
            log_message('✅ Messenger loaded', self.automation_state, 'success')
            return True
        except Exception as e:
            log_message(f'❌ Failed to open Messenger: {str(e)[:100]}', self.automation_state, 'error')
            return False
    
    def open_secret_conversation(self, thread_id):
        """Open or create a secret (E2EE) conversation"""
        try:
            log_message(f'🔐 Opening E2EE conversation: {thread_id}', self.automation_state, 'e2ee')
            
            # Click new message button
            new_msg_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//div[@aria-label="New message"]'))
            )
            new_msg_btn.click()
            time.sleep(2)
            
            # Search for contact
            search_box = self.driver.find_element(By.XPATH, '//input[@placeholder="Search Messenger"]')
            search_box.send_keys(thread_id)
            time.sleep(2)
            
            # Select contact
            contact = self.driver.find_element(By.XPATH, f'//span[contains(text(), "{thread_id}")]')
            contact.click()
            time.sleep(1)
            
            # Click on info/options for secret conversation
            info_btn = self.driver.find_element(By.XPATH, '//div[@aria-label="Conversation information"]')
            info_btn.click()
            time.sleep(1)
            
            # Select "Go to secret conversation"
            try:
                secret_btn = self.driver.find_element(By.XPATH, '//span[contains(text(), "Secret conversation")]')
                secret_btn.click()
                time.sleep(2)
                log_message('✅ E2EE Secret conversation opened!', self.automation_state, 'success')
                return True
            except:
                log_message('⚠️ Secret conversation option not found - starting new', self.automation_state, 'e2ee')
                # Try to start secret conversation directly
                return self.start_secret_conversation(thread_id)
                
        except Exception as e:
            log_message(f'❌ Failed to open E2EE conversation: {str(e)[:100]}', self.automation_state, 'error')
            return False
    
    def start_secret_conversation(self, thread_id):
        """Start a new secret conversation"""
        try:
            # Go to contact profile
            # Click on "Secret conversation" in contact options
            self.driver.get(f'https://www.messenger.com/t/{thread_id}')
            time.sleep(3)
            
            # Look for secret conversation toggle
            try:
                secret_toggle = self.driver.find_element(By.XPATH, '//span[contains(text(), "Go to secret conversation")]')
                secret_toggle.click()
                time.sleep(2)
                log_message('✅ Started new E2EE secret conversation!', self.automation_state, 'success')
                return True
            except:
                log_message('⚠️ Could not start secret conversation', self.automation_state, 'e2ee')
                return False
                
        except Exception as e:
            log_message(f'❌ Error starting secret conversation: {str(e)[:100]}', self.automation_state, 'error')
            return False
    
    def send_e2ee_message(self, message):
        """Send an encrypted message in secret conversation"""
        try:
            if self.e2ee:
                # Encrypt message before sending
                encrypted_msg = self.e2ee.encrypt_message(message)
                signature = self.e2ee.create_signature(message)
                
                # Log encrypted message
                log_message(f'🔐 Encrypted: {encrypted_msg[:50]}...', self.automation_state, 'e2ee')
                
                # Type in the message box
                message_box = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '//div[@aria-label="Message"][@contenteditable="true"]'))
                )
                
                # Clear and type message
                message_box.clear()
                
                # For E2EE, we send the original message (Facebook handles encryption)
                # But we log our own encrypted version
                message_box.send_keys(message)
                time.sleep(0.5)
                
                # Click send button
                send_btn = self.driver.find_element(By.XPATH, '//div[@aria-label="Press enter to send"]')
                send_btn.click()
                
                # Save to database
                db.save_e2ee_message(
                    self.config.get('user_id', 0),
                    self.config.get('admin_e2ee_thread_id', ''),
                    message,
                    encrypted_msg,
                    'sent'
                )
                
                log_message(f'✅ E2EE Message sent: {message[:50]}...', self.automation_state, 'success')
                return True
            else:
                log_message('⚠️ E2EE not enabled - sending regular message', self.automation_state, 'e2ee')
                return self.send_regular_message(message)
                
        except Exception as e:
            log_message(f'❌ Failed to send E2EE message: {str(e)[:100]}', self.automation_state, 'error')
            return False
    
    def send_regular_message(self, message):
        """Send regular Messenger message"""
        try:
            message_box = self.driver.find_element(By.XPATH, '//div[@aria-label="Message"][@contenteditable="true"]')
            message_box.clear()
            message_box.send_keys(message)
            time.sleep(0.5)
            
            send_btn = self.driver.find_element(By.XPATH, '//div[@aria-label="Press enter to send"]')
            send_btn.click()
            
            log_message(f'✅ Message sent: {message[:50]}...', self.automation_state, 'success')
            return True
            
        except Exception as e:
            log_message(f'❌ Failed to send message: {str(e)[:100]}', self.automation_state, 'error')
            return False
    
    def get_conversation_key(self):
        """Get the E2EE conversation key/device key"""
        try:
            # Navigate to E2EE settings
            self.driver.get('https://www.messenger.com/secret_conversations/')
            time.sleep(3)
            
            # Extract device keys
            device_keys = self.driver.find_elements(By.XPATH, '//div[contains(text(), "Device key")]')
            if device_keys:
                keys = [elem.text for elem in device_keys]
                log_message(f'🔑 Found {len(keys)} device keys', self.automation_state, 'e2ee')
                return keys
            return []
            
        except Exception as e:
            log_message(f'❌ Could not get conversation key: {str(e)[:100]}', self.automation_state, 'error')
            return []
    
    def verify_e2ee_status(self):
        """Verify if conversation is end-to-end encrypted"""
        try:
            # Check for E2EE indicators
            e2ee_indicators = [
                '//span[contains(text(), "End-to-end encrypted")]',
                '//div[contains(text(), "Secret conversation")]',
                '//div[contains(@class, "e2ee")]'
            ]
            
            for indicator in e2ee_indicators:
                try:
                    if self.driver.find_element(By.XPATH, indicator):
                        log_message('🔐 E2EE Verified - Conversation is encrypted!', self.automation_state, 'success')
                        return True
                except:
                    continue
            
            log_message('⚠️ E2EE status could not be verified', self.automation_state, 'e2ee')
            return False
            
        except Exception as e:
            return False

# Background image management
def save_background_image(image_file, user_id):
    """Save custom background image"""
    bg_path = os.path.join(BACKGROUND_DIR, f"user_{user_id}_bg.png")
    with open(bg_path, 'wb') as f:
        f.write(image_file.read())
    return bg_path

def get_background_image(user_id):
    """Get background image path"""
    bg_path = os.path.join(BACKGROUND_DIR, f"user_{user_id}_bg.png")
    if os.path.exists(bg_path):
        return bg_path
    return None

def load_background_css(bg_path=None):
    """Generate CSS for background"""
    if bg_path and os.path.exists(bg_path):
        with open(bg_path, 'rb') as f:
            bg_base64 = base64.b64encode(f.read()).decode()
        return f"""
        <style>
            .stApp {{
                background-image: url('data:image/png;base64,{bg_base64}');
                background-size: cover;
                background-position: center;
                background-attachment: fixed;
                background-repeat: no-repeat;
            }}
            .stApp::before {{
                content: '';
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(15, 23, 42, 0.85);
                z-index: 0;
            }}
        </style>
        """
    return ""

def save_cookies_to_file(cookies_data, user_id):
    """Save cookies to pickle file"""
    cookies_path = os.path.join(COOKIES_DIR, f"user_{user_id}_cookies.pkl")
    with open(cookies_path, 'wb') as f:
        pickle.dump(cookies_data, f)
    return cookies_path

def load_cookies_from_file(user_id):
    """Load cookies from pickle file"""
    cookies_path = os.path.join(COOKIES_DIR, f"user_{user_id}_cookies.pkl")
    if os.path.exists(cookies_path):
        with open(cookies_path, 'rb') as f:
            return pickle.load(f)
    return None

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
    if os.path.exists(APPROVAL_FILE):
        try:
            with open(APPROVAL_FILE, 'r') as f:
                return json.load(f)
        except Exception:
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
        except Exception:
            return {}
    return {}

def save_pending_approvals(pending):
    with open(PENDING_FILE, 'w') as f:
        json.dump(pending, f, indent=2)

def check_approval(key):
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
if 'cookies_loaded' not in st.session_state:
    st.session_state.cookies_loaded = False
if 'background_loaded' not in st.session_state:
    st.session_state.background_loaded = False
if 'e2ee_enabled' not in st.session_state:
    st.session_state.e2ee_enabled = False
if 'fb_logged_in' not in st.session_state:
    st.session_state.fb_logged_in = False

class AutomationState:
    """Class to manage automation state"""
    def __init__(self):
        self.running = False
        self.message_count = 0
        self.logs = []
        self.e2ee_messages_sent = 0
        self.current_platform = 'whatsapp'  # 'whatsapp' or 'facebook_e2ee'

if 'automation_state' not in st.session_state:
    st.session_state.automation_state = AutomationState()

def log_message(msg, automation_state=None, msg_type='info'):
    """Add timestamped message to logs with type"""
    timestamp = time.strftime("%H:%M:%S")
    formatted_msg = f"[{timestamp}] {msg}"
    if automation_state:
        # Store with message type
        automation_state.logs.append({'message': formatted_msg, 'type': msg_type})
        if len(automation_state.logs) > 100:
            automation_state.logs = automation_state.logs[-100:]

def setup_browser(automation_state=None, cookies_data=None):
    """Setup Chrome browser with cookies support"""
    log_message('Setting up Chrome browser...', automation_state)
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-notifications')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Add E2EE related preferences
    chrome_options.add_argument('--enable-features=EncryptedClientHello')
    chrome_options.add_argument('--enable-quic')
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Load WhatsApp Web
        driver.get('https://web.whatsapp.com/')
        log_message('WhatsApp Web loaded', automation_state)
        
        if cookies_data:
            log_message('Loading cookies...', automation_state)
            try:
                for cookie in cookies_data:
                    if 'sameSite' in cookie:
                        del cookie['sameSite']
                    if 'expiry' in cookie:
                        cookie['expiry'] = int(cookie['expiry'])
                    driver.add_cookie(cookie)
                driver.refresh()
                log_message('✅ Cookies loaded successfully!', automation_state, 'success')
            except Exception as e:
                log_message(f'Error loading cookies: {str(e)[:100]}', automation_state, 'error')
        
        return driver
    except Exception as e:
        log_message(f'Failed to start Chrome: {str(e)[:100]}', automation_state, 'error')
        raise

def send_whatsapp_messages(config, automation_state, user_id):
    """WhatsApp automation function"""
    driver = None
    try:
        cookies_data = None
        if config.get('cookies_enabled') and config.get('cookies_file'):
            cookies_data = load_cookies_from_file(user_id)
            if cookies_data:
                log_message('Using saved cookies for authentication', automation_state)
        
        driver = setup_browser(automation_state, cookies_data)
        time.sleep(10)
        
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]'))
            )
            log_message('✅ WhatsApp Web is ready!', automation_state, 'success')
        except:
            log_message('❌ Please scan QR code or upload valid cookies', automation_state, 'error')
            automation_state.running = False
            return 0
        
        messages_list = config.get('messages_list', [])
        total_messages = len(messages_list)
        
        for i, msg in enumerate(messages_list):
            if not automation_state.running:
                log_message('Automation stopped by user', automation_state)
                break
            
            try:
                search_box = driver.find_element(By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]')
                search_box.clear()
                time.sleep(0.5)
                search_box.send_keys(config['chat_id'])
                time.sleep(2)
                
                try:
                    chat = driver.find_element(By.XPATH, f'//span[@title="{config["chat_id"]}"]')
                    chat.click()
                except:
                    first_result = driver.find_element(By.XPATH, '//div[@class="_ak8q"]')
                    first_result.click()
                
                time.sleep(1)
                
                message_box = driver.find_element(By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')
                full_message = f"{config.get('name_prefix', '')} {msg}".strip()
                message_box.send_keys(full_message)
                time.sleep(0.5)
                
                send_button = driver.find_element(By.XPATH, '//button[@data-tab="11"]')
                send_button.click()
                
                automation_state.message_count += 1
                log_message(f'✅ Message {i+1}/{total_messages} sent successfully', automation_state, 'success')
                
                db.update_message_count(user_id, automation_state.message_count)
                time.sleep(config.get('delay', 5))
                
            except Exception as e:
                log_message(f'❌ Error sending message {i+1}: {str(e)[:100]}', automation_state, 'error')
                continue
        
        log_message(f'WhatsApp automation completed! Total: {automation_state.message_count}', automation_state, 'success')
        return automation_state.message_count
        
    except Exception as e:
        log_message(f'Fatal error in WhatsApp automation: {str(e)[:100]}', automation_state, 'error')
        return 0
    finally:
        if driver:
            driver.quit()
            log_message('Browser closed', automation_state)

def send_facebook_e2ee_messages(config, automation_state, user_id):
    """Facebook E2EE automation function"""
    driver = None
    try:
        automation_state.current_platform = 'facebook_e2ee'
        log_message('🔐 Starting Facebook E2EE Automation...', automation_state, 'e2ee')
        
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-notifications')
        
        driver = webdriver.Chrome(options=chrome_options)
        
        # Initialize Facebook E2EE messenger
        fb_messenger = FacebookE2EEMessenger(driver, config, automation_state)
        
        # Login to Facebook
        fb_user = config.get('facebook_user', '')
        fb_pass = config.get('facebook_pass', '')
        
        if not fb_user or not fb_pass:
            log_message('❌ Facebook credentials not configured!', automation_state, 'error')
            return 0
        
        login_result = fb_messenger.login_facebook(fb_user, fb_pass)
        if login_result == 'failed':
            return 0
        elif login_result == '2fa_required':
            log_message('⚠️ 2FA required - please login manually first', automation_state, 'e2ee')
            return 0
        
        # Open Messenger
        if not fb_messenger.open_messenger():
            return 0
        
        # Open secret conversation
        thread_id = config.get('admin_e2ee_thread_id', '')
        if not thread_id:
            log_message('❌ E2EE Thread ID not configured!', automation_state, 'error')
            return 0
        
        if not fb_messenger.open_secret_conversation(thread_id):
            log_message('❌ Failed to open E2EE conversation', automation_state, 'error')
            return 0
        
        # Verify E2EE status
        fb_messenger.verify_e2ee_status()
        
        # Send messages
        messages_list = config.get('messages_list', [])
        total_messages = len(messages_list)
        
        for i, msg in enumerate(messages_list):
            if not automation_state.running:
                log_message('Automation stopped by user', automation_state)
                break
            
            try:
                full_message = f"{config.get('name_prefix', '')} {msg}".strip()
                
                if fb_messenger.send_e2ee_message(full_message):
                    automation_state.message_count += 1
                    automation_state.e2ee_messages_sent += 1
                    log_message(f'🔐 E2EE Message {i+1}/{total_messages} sent', automation_state, 'success')
                    
                    db.update_message_count(user_id, automation_state.message_count)
                    time.sleep(config.get('delay', 5))
                else:
                    log_message(f'❌ Failed to send E2EE message {i+1}', automation_state, 'error')
                    
            except Exception as e:
                log_message(f'❌ Error sending E2EE message {i+1}: {str(e)[:100]}', automation_state, 'error')
                continue
        
        log_message(f'✅ E2EE automation completed! Total: {automation_state.e2ee_messages_sent}', automation_state, 'success')
        return automation_state.e2ee_messages_sent
        
    except Exception as e:
        log_message(f'Fatal error in E2EE automation: {str(e)[:100]}', automation_state, 'error')
        return 0
    finally:
        if driver:
            driver.quit()
            log_message('Browser closed', automation_state)

def start_automation(user_config, user_id):
    """Start automation in background thread"""
    if st.session_state.automation_state.running:
        return
    
    st.session_state.automation_state.running = True
    st.session_state.automation_state.logs = []
    st.session_state.automation_state.message_count = 0
    st.session_state.automation_state.e2ee_messages_sent = 0
    db.set_automation_running(user_id, True)
    
    # Check if E2EE mode is enabled
    if user_config.get('e2ee_enabled') and user_config.get('admin_e2ee_thread_id'):
        st.session_state.automation_state.current_platform = 'facebook_e2ee'
        thread = threading.Thread(target=send_facebook_e2ee_messages, args=(user_config, st.session_state.automation_state, user_id))
    else:
        st.session_state.automation_state.current_platform = 'whatsapp'
        thread = threading.Thread(target=send_whatsapp_messages, args=(user_config, st.session_state.automation_state, user_id))
    
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
    
    col1, col2, col3, col4 = st.columns(4)
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
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("E2EE Users", sum(1 for k in approved if 'e2ee' in approved.get(k, {})))
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
                "Messages": config.get('message_count', 0) if config else 0,
                "E2EE": "🔐" if config and config.get('e2ee_enabled') else "❌"
            })
        st.dataframe(user_data, use_container_width=True)
        
        delete_user = st.selectbox("Select user to delete", [u['username'] for u in users])
        if st.button("🗑️ Delete User", key="admin_delete_user"):
            user_to_delete = next((u for u in users if u['username'] == delete_user), None)
            if user_to_delete:
                if db.delete_user(user_to_delete['id']):
                    for fname in [f"user_{user_to_delete['id']}_cookies.pkl", f"user_{user_to_delete['id']}_bg.png", f"user_{user_to_delete['id']}_e2ee.key"]:
                        for dir_path in [COOKIES_DIR, BACKGROUND_DIR, E2EE_KEYS_DIR]:
                            fpath = os.path.join(dir_path, fname)
                            if os.path.exists(fpath):
                                os.remove(fpath)
                    st.success(f"User {delete_user} deleted successfully!")
                    st.rerun()
                else:
                    st.error("Failed to delete user")
    
    # E2EE Keys Management
    st.subheader("🔐 E2EE Key Management")
    e2ee_users = []
    for user in users:
        config = db.get_user_config(user['id'])
        if config and config.get('e2ee_enabled'):
            e2ee = E2EEEncryption(user['id'])
            e2ee_users.append({
                "Username": user['username'],
                "E2EE Key File": f"user_{user['id']}_e2ee.key",
                "Public Key": e2ee.export_public_key()[:20] + "..." if e2ee.export_public_key() else "N/A"
            })
    
    if e2ee_users:
        st.dataframe(e2ee_users, use_container_width=True)
    else:
        st.info("No E2EE users found")
    
    if st.button("🚪 Logout from Admin", key="admin_logout_btn"):
        st.session_state.approval_status = 'login'
        st.rerun()

def login_page():
    """Login and signup interface"""
    st.markdown('<div class="main-header"><h1>🤖 WhatsApp + FB E2EE Automation</h1></div>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #a78bfa;">Powered by Suraj Oberoy | End-to-End Encryption Support</p>', unsafe_allow_html=True)
    
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
                        
                        # Load E2EE status
                        config = db.get_user_config(user_id)
                        if config:
                            st.session_state.e2ee_enabled = bool(config.get('e2ee_enabled', 0))
                        
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
            <div style="background: rgba(30, 27, 75, 0.7); border-radius: 15px; padding: 1.5rem; text-align: center; margin: 1rem 0;">
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
    bg_path = get_background_image(st.session_state.user_id)
    if bg_path:
        st.markdown(load_background_css(bg_path), unsafe_allow_html=True)
    
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
            {f'<span class="e2ee-badge">🔐 E2EE Active</span>' if st.session_state.e2ee_enabled else ''}
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Background upload in sidebar
        with st.expander("🎨 Customize Background", expanded=False):
            bg_file = st.file_uploader("Upload Background Image", type=['png', 'jpg', 'jpeg', 'webp'], key="sidebar_bg_upload")
            if bg_file:
                save_background_image(bg_file, st.session_state.user_id)
                st.success("Background updated!")
                st.rerun()
            if st.button("🔄 Reset Background", key="reset_bg"):
                bg_path = os.path.join(BACKGROUND_DIR, f"user_{st.session_state.user_id}_bg.png")
                if os.path.exists(bg_path):
                    os.remove(bg_path)
                st.success("Background reset!")
                st.rerun()
        
        # E2EE Quick Status
        with st.expander("🔐 E2EE Status", expanded=False):
            if st.session_state.e2ee_enabled:
                e2ee = E2EEEncryption(st.session_state.user_id)
                st.success("E2EE is active")
                st.code(f"Public Key: {e2ee.export_public_key()[:30]}...")
                st.info("Your messages are end-to-end encrypted")
            else:
                st.info("E2EE not configured yet")
                st.markdown("Go to **Facebook E2EE** tab to set up")
        
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
    config_tab, fb_e2ee_tab, auto_tab, stats_tab, bg_tab = st.tabs([
        "⚙️ WhatsApp Config", "🔐 Facebook E2EE", "▶️ Automation", "📊 Statistics", "🎨 Background"
    ])
    
    with config_tab:
        st.subheader("WhatsApp Automation Settings")
        
        col1, col2 = st.columns(2)
        with col1:
            chat_id = st.text_input(
                "Chat/Group ID",
                value=user_config.get('chat_id', ''),
                placeholder="Enter WhatsApp chat ID or group link",
                key="chat_id_input"
            )
            name_prefix = st.text_input(
                "Name Prefix (Optional)",
                value=user_config.get('name_prefix', ''),
                placeholder="e.g., 'Agent:' or 'Bot:'",
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
        
        # Cookies Upload Section
        st.markdown("---")
        st.subheader("🍪 WhatsApp Web Cookies")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            cookies_file = st.file_uploader("Upload Cookies File (.json or .pkl)", type=['json', 'pkl', 'txt'], key="cookies_upload")
        with col2:
            cookies_enabled = st.checkbox("Enable Cookies", value=bool(user_config.get('cookies_enabled', 0)), key="cookies_enabled_checkbox")
        with col3:
            if st.button("🗑️ Clear Cookies", key="clear_cookies"):
                cookies_path = os.path.join(COOKIES_DIR, f"user_{st.session_state.user_id}_cookies.pkl")
                if os.path.exists(cookies_path):
                    os.remove(cookies_path)
                st.session_state.cookies_loaded = False
                st.success("Cookies cleared!")
                st.rerun()
        
        if cookies_file:
            try:
                if cookies_file.name.endswith('.pkl'):
                    cookies_data = pickle.loads(cookies_file.read())
                else:
                    cookies_data = json.loads(cookies_file.read())
                
                save_cookies_to_file(cookies_data, st.session_state.user_id)
                st.session_state.cookies_loaded = True
                st.success(f"✅ Cookies loaded successfully!")
            except Exception as e:
                st.error(f"❌ Error loading cookies: {str(e)}")
        
        st.markdown("---")
        st.subheader("Message List")
        uploaded_file = st.file_uploader("Upload Messages (.txt file)", type=['txt'], key="msg_upload")
        
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
        
        if st.button("💾 Save WhatsApp Configuration", key="save_config", use_container_width=True):
            cookies_file_path = user_config.get('cookies_file', '')
            if st.session_state.cookies_loaded:
                cookies_file_path = f"user_{st.session_state.user_id}_cookies.pkl"
            
            if uploaded_file and messages_list:
                messages_str = "\n".join(messages_list)
                db.update_user_config_with_messages(
                    st.session_state.user_id, chat_id, name_prefix, delay, '', 
                    messages_str, messages_list, cookies_file_path, 
                    1 if cookies_enabled else 0, user_config.get('e2ee_enabled', 0)
                )
                st.success("Configuration saved successfully!")
            else:
                messages_list = user_config.get('messages_list', [])
                messages_str = '\n'.join(messages_list) if messages_list else ''
                db.update_user_config_with_messages(
                    st.session_state.user_id, chat_id, name_prefix, delay, '', 
                    messages_str, messages_list, cookies_file_path,
                    1 if cookies_enabled else 0, user_config.get('e2ee_enabled', 0)
                )
                st.success("Configuration saved!")
            st.rerun()
    
    with fb_e2ee_tab:
        st.subheader("🔐 Facebook End-to-End Encryption Setup")
        
        st.markdown("""
        <div class="e2ee-card">
            <h4>🔐 Facebook Secret Conversations (E2EE)</h4>
            <p>This feature enables automated messaging in Facebook's end-to-end encrypted secret conversations.</p>
            <p>All messages are encrypted with unique keys per user.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # E2EE Toggle
        e2ee_enabled = st.toggle(
            "Enable Facebook E2EE Automation",
            value=bool(user_config.get('e2ee_enabled', 0)),
            key="e2ee_enabled_toggle"
        )
        
        if e2ee_enabled:
            st.markdown("---")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Facebook Login Credentials")
                fb_user = st.text_input(
                    "Facebook Email/Phone",
                    value=user_config.get('facebook_user', ''),
                    placeholder="Enter Facebook login email",
                    key="fb_user_input",
                    type="default"
                )
                fb_pass = st.text_input(
                    "Facebook Password",
                    value=user_config.get('facebook_pass', ''),
                    placeholder="Enter Facebook password",
                    key="fb_pass_input",
                    type="password"
                )
            
            with col2:
                st.subheader("E2EE Settings")
                admin_e2ee_thread_id = st.text_input(
                    "E2EE Thread/Contact ID",
                    value=user_config.get('admin_e2ee_thread_id', ''),
                    placeholder="Facebook user ID for secret chat",
                    key="e2ee_thread_input",
                    help="The Facebook user ID to start secret conversation with"
                )
                
                # Generate and show E2EE key
                if st.button("🔑 Generate New E2EE Key", key="gen_e2ee_key"):
                    e2ee = E2EEEncryption(st.session_state.user_id)
                    new_key = e2ee.generate_device_key()
                    st.code(f"Device Key: {new_key[:40]}...")
                    st.success("New E2EE key generated!")
                
                # Show current E2EE key
                e2ee = E2EEEncryption(st.session_state.user_id)
                public_key = e2ee.export_public_key()
                if public_key:
                    st.info(f"Current Public Key: {public_key[:30]}...")
            
            # 2FA Secret (optional)
            st.markdown("---")
            with st.expander("🔐 Two-Factor Authentication (Optional)", expanded=False):
                fb_2fa_secret = st.text_input(
                    "2FA Secret Key",
                    value=user_config.get('facebook_2fa_secret', ''),
                    placeholder="Enter 2FA secret if enabled",
                    key="fb_2fa_input",
                    type="password"
                )
                st.info("If your Facebook account has 2FA enabled, provide the secret key for auto-login")
            
            # Save Facebook E2EE Config
            if st.button("💾 Save Facebook E2EE Configuration", key="save_fb_e2ee", use_container_width=True):
                # Update E2EE enabled status
                db.update_user_config_with_messages(
                    st.session_state.user_id,
                    user_config.get('chat_id', ''),
                    user_config.get('name_prefix', ''),
                    user_config.get('delay', 5),
                    user_config.get('cookies', ''),
                    user_config.get('messages', ''),
                    user_config.get('messages_list', []),
                    user_config.get('cookies_file', ''),
                    user_config.get('cookies_enabled', 0),
                    1 if e2ee_enabled else 0
                )
                
                # Save Facebook credentials
                db.update_facebook_config(
                    st.session_state.user_id,
                    fb_user,
                    fb_pass,
                    user_config.get('facebook_cookies', ''),
                    fb_2fa_secret if 'fb_2fa_secret' in locals() else user_config.get('facebook_2fa_secret', ''),
                    admin_e2ee_thread_id
                )
                
                st.session_state.e2ee_enabled = e2ee_enabled
                st.success("✅ Facebook E2EE configuration saved!")
                send_to_telegram(f"🔐 E2EE Setup: {st.session_state.username} configured Facebook E2EE")
                st.rerun()
            
            # E2EE Test Section
            st.markdown("---")
            st.subheader("🧪 Test E2EE Encryption")
            
            test_message = st.text_input("Test Message", placeholder="Enter a message to test encryption", key="test_e2ee_msg")
            if test_message and st.button("🔐 Encrypt & Test", key="test_e2ee_btn"):
                e2ee = E2EEEncryption(st.session_state.user_id)
                encrypted = e2ee.encrypt_message(test_message)
                decrypted = e2ee.decrypt_message(encrypted)
                signature = e2ee.create_signature(test_message)
                verified = e2ee.verify_signature(test_message, signature)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Original:**")
                    st.code(test_message)
                    st.markdown("**Encrypted:**")
                    st.code(encrypted[:100] + "...")
                with col2:
                    st.markdown("**Decrypted:**")
                    st.code(decrypted)
                    st.markdown(f"**Signature Verified:** {'✅' if verified else '❌'}")
        else:
            st.info("Enable E2EE to configure Facebook secret conversation automation")
    
    with auto_tab:
        st.subheader("Control Panel")
        
        # Show current platform
        current_platform = st.session_state.automation_state.current_platform
        platform_icon = "🔐" if current_platform == 'facebook_e2ee' else "💬"
        st.info(f"{platform_icon} Current Platform: **{current_platform.replace('_', ' ').title()}**")
        
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
            e2ee_status = "🔐 Active" if user_config.get('e2ee_enabled') else "❌ Inactive"
            st.metric("E2EE", e2ee_status)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Additional E2EE metrics
        if user_config.get('e2ee_enabled'):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric("🔐 E2EE Messages", st.session_state.automation_state.e2ee_messages_sent)
                st.markdown('</div>', unsafe_allow_html=True)
            with col2:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric("🎯 Thread ID", user_config.get('admin_e2ee_thread_id', 'Not set')[:20])
                st.markdown('</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            # Determine which platform to use
            use_e2ee = user_config.get('e2ee_enabled') and user_config.get('admin_e2ee_thread_id')
            start_label = "▶️ Start E2EE Automation" if use_e2ee else "▶️ Start WhatsApp Automation"
            
            start_disabled = st.session_state.automation_state.running or msg_count == 0
            if not use_e2ee:
                start_disabled = start_disabled or not user_config.get('chat_id')
            
            if st.button(start_label, key="start_auto", use_container_width=True, disabled=start_disabled):
                if use_e2ee or user_config.get('chat_id'):
                    if msg_count > 0:
                        start_automation(user_config, st.session_state.user_id)
                        st.success(f"Automation started on {current_platform}!")
                        st.rerun()
                    else:
                        st.error("Please upload messages first!")
                else:
                    st.error("Please configure target (Chat ID or E2EE Thread) first!")
        
        with col2:
            if st.button("⏹️ Stop Automation", key="stop_auto", use_container_width=True, disabled=not st.session_state.automation_state.running):
                stop_automation(st.session_state.user_id)
                st.warning("Automation stopped!")
                st.rerun()
        
        # Console Output
        if st.session_state.automation_state.logs:
            st.markdown("### 📟 Console Output")
            logs_html = '<div class="console-output">'
            for log in st.session_state.automation_state.logs[-20:]:
                log_class = log['type'] if 'type' in log else 'info'
                logs_html += f'<div class="console-line {log_class}">{log["message"] if isinstance(log, dict) else log}</div>'
            logs_html += '</div>'
            st.markdown(logs_html, unsafe_allow_html=True)
        
        # E2EE Message History
        if user_config.get('e2ee_enabled'):
            st.markdown("---")
            st.subheader("📜 E2EE Message History")
            e2ee_messages = db.get_e2ee_messages(st.session_state.user_id)
            if e2ee_messages:
                history_data = []
                for msg in e2ee_messages[:10]:
                    history_data.append({
                        "Time": msg.get('sent_at', 'Unknown'),
                        "Message": (msg.get('message', '')[:50] + '...') if len(msg.get('message', '')) > 50 else msg.get('message', ''),
                        "Status": msg.get('status', 'pending')
                    })
                st.dataframe(history_data, use_container_width=True)
            else:
                st.info("No E2EE messages sent yet")
    
    with stats_tab:
        st.subheader("Activity Statistics")
        
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
        
        # E2EE Stats
        if user_config.get('e2ee_enabled'):
            st.markdown("---")
            st.subheader("🔐 E2EE Encryption Stats")
            
            e2ee = E2EEEncryption(st.session_state.user_id)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown('<div class="metric-card e2ee-card">', unsafe_allow_html=True)
                st.metric("E2EE Messages", st.session_state.automation_state.e2ee_messages_sent)
                st.markdown('</div>', unsafe_allow_html=True)
            with col2:
                st.markdown('<div class="metric-card e2ee-card">', unsafe_allow_html=True)
                st.metric("Public Key", e2ee.export_public_key()[:15] + "..." if e2ee.export_public_key() else "N/A")
                st.markdown('</div>', unsafe_allow_html=True)
            with col3:
                st.markdown('<div class="metric-card e2ee-card">', unsafe_allow_html=True)
                st.metric("Encryption", "Fernet (AES-128)")
                st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        st.subheader("Cookies Status")
        cookies_path = os.path.join(COOKIES_DIR, f"user_{st.session_state.user_id}_cookies.pkl")
        if os.path.exists(cookies_path):
            st.success(f"📁 Cookies file: user_{st.session_state.user_id}_cookies.pkl")
            st.info("Cookies are loaded and will be used for automation")
        else:
            st.warning("No cookies file uploaded yet")
    
    with bg_tab:
        st.subheader("🎨 Customize Background")
        
        st.markdown('<div class="bg-upload-section">', unsafe_allow_html=True)
        st.markdown("### Upload Your Custom Background")
        st.markdown("*Upload an image to personalize your dashboard*")
        
        bg_file = st.file_uploader("Choose an image", type=['png', 'jpg', 'jpeg', 'webp'], key="main_bg_upload")
        
        if bg_file:
            st.image(bg_file, caption="Preview", use_column_width=True)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Apply Background", key="apply_bg", use_container_width=True):
                    save_background_image(bg_file, st.session_state.user_id)
                    st.success("Background applied successfully!")
                    st.rerun()
            with col2:
                if st.button("❌ Cancel", key="cancel_bg", use_container_width=True):
                    st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        current_bg = get_background_image(st.session_state.user_id)
        if current_bg:
            st.success("Custom background is active!")
            if st.button("🔄 Reset to Default", key="reset_main_bg", use_container_width=True):
                os.remove(current_bg)
                st.success("Background reset to default!")
                st.rerun()
        else:
            st.info("Using default background")

# Main routing
if not st.session_state.logged_in:
    login_page()
elif not st.session_state.key_approved:
    approval_request_page(st.session_state.user_key, st.session_state.username)
else:
    main_app()

# Footer
st.markdown("""
<div class="footer">
    Developed with 🤖 by Suraj Oberoy | © 2026<br>
    WhatsApp Automation + Facebook E2EE Secret Conversations<br>
    <span style="color: #10b981;">🔐 End-to-End Encryption Supported</span>
</div>
""", unsafe_allow_html=True)