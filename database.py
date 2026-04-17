import sqlite3
import os
import json
from datetime import datetime

DB_PATH = "users.db"

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # User configs table
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
    """Create a new user"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
        user_id = cursor.lastrowid
        cursor.execute('INSERT INTO user_configs (user_id) VALUES (?)', (user_id,))
        conn.commit()
        conn.close()
        return True, "User created successfully!"
    except sqlite3.IntegrityError:
        return False, "Username already exists!"
    except Exception as e:
        return False, str(e)

def verify_user(username, password):
    """Verify user credentials"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE username = ? AND password = ?', (username, password))
    row = cursor.fetchone()
    conn.close()
    return row['id'] if row else None

def get_username(user_id):
    """Get username by ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row['username'] if row else None

def get_user_config(user_id):
    """Get user configuration"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM user_configs WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        config = dict(row)
        # Parse messages_list from JSON
        if config.get('messages_list'):
            try:
                config['messages_list'] = json.loads(config['messages_list'])
            except:
                config['messages_list'] = []
        else:
            config['messages_list'] = []
        return config
    return None

def update_user_config(user_id, chat_id, name_prefix, delay, cookies, messages):
    """Update user configuration"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE user_configs 
        SET chat_id = ?, name_prefix = ?, delay = ?, cookies = ?, messages = ?
        WHERE user_id = ?
    ''', (chat_id, name_prefix, delay, cookies, messages, user_id))
    conn.commit()
    conn.close()

def update_user_config_with_messages(user_id, chat_id, name_prefix, delay, cookies, messages_str, messages_list):
    """Update user config with messages list"""
    conn = get_db_connection()
    cursor = conn.cursor()
    messages_json = json.dumps(messages_list)
    cursor.execute('''
        UPDATE user_configs 
        SET chat_id = ?, name_prefix = ?, delay = ?, cookies = ?, messages = ?, messages_list = ?
        WHERE user_id = ?
    ''', (chat_id, name_prefix, delay, cookies, messages_str, messages_json, user_id))
    conn.commit()
    conn.close()

def set_automation_running(user_id, running):
    """Set automation running status"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE user_configs SET automation_running = ? WHERE user_id = ?', (1 if running else 0, user_id))
    conn.commit()
    conn.close()

def get_automation_running(user_id):
    """Get automation running status"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT automation_running FROM user_configs WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] == 1 if row else False

def set_admin_e2ee_thread_id(user_id, thread_id, cookies, chat_type):
    """Set admin E2EE thread ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE user_configs SET admin_e2ee_thread_id = ? WHERE user_id = ?', (thread_id, user_id))
    conn.commit()
    conn.close()

def get_admin_e2ee_thread_id(user_id):
    """Get admin E2EE thread ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT admin_e2ee_thread_id FROM user_configs WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def get_all_users():
    """Get all users"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, created_at FROM users')
    users = [{'id': row[0], 'username': row[1], 'created_at': row[2]} for row in cursor.fetchall()]
    conn.close()
    return users

def delete_user(user_id):
    """Delete user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM user_configs WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

# Initialize database on import
init_db()print(f"→ DB exists?         {DB_PATH.exists()}\n")

# ────────────────────────────────────────────────

def get_encryption_key():
    """Get or create encryption key for cookie storage"""
    if ENCRYPTION_KEY_FILE.exists():
        with open(ENCRYPTION_KEY_FILE, 'rb') as f:
            return f.read()
    else:
        key = Fernet.generate_key()
        with open(ENCRYPTION_KEY_FILE, 'wb') as f:
            f.write(key)
        return key

ENCRYPTION_KEY = get_encryption_key()
cipher_suite = Fernet(ENCRYPTION_KEY)

def init_db():
    """Initialize database with tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
   
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
   
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            chat_id TEXT,
            name_prefix TEXT,
            delay INTEGER DEFAULT 30,
            cookies_encrypted TEXT,
            messages TEXT,
            automation_running INTEGER DEFAULT 0,
            locked_group_name TEXT,
            locked_nicknames TEXT,
            lock_enabled INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
   
    # Safe ALTER TABLE (ignore if column already exists)
    for column, definition in [
        ("automation_running", "INTEGER DEFAULT 0"),
        ("locked_group_name", "TEXT"),
        ("locked_nicknames", "TEXT"),
        ("lock_enabled", "INTEGER DEFAULT 0"),
    ]:
        try:
            cursor.execute(f'ALTER TABLE user_configs ADD COLUMN {column} {definition}')
            conn.commit()
        except sqlite3.OperationalError:
            pass
   
    conn.commit()
    conn.close()

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def encrypt_cookies(cookies):
    """Encrypt cookies for secure storage"""
    if not cookies:
        return None
    return cipher_suite.encrypt(cookies.encode()).decode()

def decrypt_cookies(encrypted_cookies):
    """Decrypt cookies"""
    if not encrypted_cookies:
        return ""
    try:
        return cipher_suite.decrypt(encrypted_cookies.encode()).decode()
    except:
        return ""

def create_user(username, password):
    """Create new user"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
   
    try:
        password_hash = hash_password(password)
        cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)',
                      (username, password_hash))
        user_id = cursor.lastrowid
       
        cursor.execute('''
            INSERT INTO user_configs (user_id, chat_id, name_prefix, delay, messages)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, '', '', 30, ''))
       
        conn.commit()
        return True, "Account created successfully!"
    except sqlite3.IntegrityError:
        return False, "Username already exists!"
    except Exception as e:
        return False, f"Error: {str(e)}"
    finally:
        conn.close()

def verify_user(username, password):
    """Verify user credentials using SHA-256"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
   
    try:
        cursor.execute('SELECT id, password_hash FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
       
        if user and user[1] == hash_password(password):
            return user[0]
        return None
    finally:
        conn.close()

def get_user_config(user_id):
    """Get user configuration"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
   
    try:
        cursor.execute('''
            SELECT chat_id, name_prefix, delay, cookies_encrypted, messages, automation_running
            FROM user_configs WHERE user_id = ?
        ''', (user_id,))
       
        config = cursor.fetchone()
       
        if config:
            return {
                'chat_id': config[0] or '',
                'name_prefix': config[1] or '',
                'delay': config[2] or 30,
                'cookies': decrypt_cookies(config[3]),
                'messages': config[4] or '',
                'automation_running': config[5] or 0
            }
        return None
    finally:
        conn.close()

def update_user_config(user_id, chat_id, name_prefix, delay, cookies, messages):
    """Update user configuration"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
   
    try:
        encrypted_cookies = encrypt_cookies(cookies)
       
        cursor.execute('''
            UPDATE user_configs
            SET chat_id = ?, name_prefix = ?, delay = ?, cookies_encrypted = ?,
                messages = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (chat_id, name_prefix, delay, encrypted_cookies, messages, user_id))
       
        conn.commit()
    finally:
        conn.close()

def get_username(user_id):
    """Get username by user ID"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
   
    try:
        cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        return user[0] if user else None
    finally:
        conn.close()

def set_automation_running(user_id, is_running):
    """Set automation running state for a user"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
   
    try:
        cursor.execute('''
            UPDATE user_configs
            SET automation_running = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (1 if is_running else 0, user_id))
       
        conn.commit()
    finally:
        conn.close()

def get_automation_running(user_id):
    """Get automation running state for a user"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
   
    try:
        cursor.execute('SELECT automation_running FROM user_configs WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        return bool(result[0]) if result else False
    finally:
        conn.close()

def get_lock_config(user_id):
    """Get lock configuration for a user"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
   
    try:
        cursor.execute('''
            SELECT chat_id, locked_group_name, locked_nicknames, lock_enabled, cookies_encrypted
            FROM user_configs WHERE user_id = ?
        ''', (user_id,))
       
        config = cursor.fetchone()
       
        if config:
            try:
                nicknames = json.loads(config[2]) if config[2] else {}
            except:
                nicknames = {}
           
            return {
                'chat_id': config[0] or '',
                'locked_group_name': config[1] or '',
                'locked_nicknames': nicknames,
                'lock_enabled': bool(config[3]),
                'cookies': decrypt_cookies(config[4])
            }
        return None
    finally:
        conn.close()

def update_lock_config(user_id, chat_id, locked_group_name, locked_nicknames, cookies=None):
    """Update complete lock configuration including chat_id and cookies"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
   
    try:
        nicknames_json = json.dumps(locked_nicknames)
       
        if cookies is not None:
            encrypted_cookies = encrypt_cookies(cookies)
            cursor.execute('''
                UPDATE user_configs
                SET chat_id = ?, locked_group_name = ?, locked_nicknames = ?,
                    cookies_encrypted = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (chat_id, locked_group_name, nicknames_json, encrypted_cookies, user_id))
        else:
            cursor.execute('''
                UPDATE user_configs
                SET chat_id = ?, locked_group_name = ?, locked_nicknames = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (chat_id, locked_group_name, nicknames_json, user_id))
       
        conn.commit()
    finally:
        conn.close()

def set_lock_enabled(user_id, enabled):
    """Enable or disable the lock system"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
   
    try:
        cursor.execute('''
            UPDATE user_configs
            SET lock_enabled = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (1 if enabled else 0, user_id))
       
        conn.commit()
    finally:
        conn.close()

def get_lock_enabled(user_id):
    """Check if lock is enabled for a user"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
   
    try:
        cursor.execute('SELECT lock_enabled FROM user_configs WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        return bool(result[0]) if result else False
    finally:
        conn.close()

# ────────────────────────────────────────────────
# Initialize on import / run
# ────────────────────────────────────────────────
init_db()
