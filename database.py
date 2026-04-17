import sqlite3
import json
import os

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

def get_message_count(user_id):
    """Get total messages sent by user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT message_count FROM user_configs WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0

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
init_db()