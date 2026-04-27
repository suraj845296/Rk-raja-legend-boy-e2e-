# fb_cookies_server.py
import os
import json
import pickle
import time
import threading
from pathlib import Path
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
from datetime import datetime
import hashlib
import uuid

app = Flask(__name__)
CORS(app)

# Configuration
COOKIES_DIR = "fb_cookies"
SESSIONS_DIR = "sessions"
os.makedirs(COOKIES_DIR, exist_ok=True)
os.makedirs(SESSIONS_DIR, exist_ok=True)

# Store active sessions
active_sessions = {}

# HTML Template for Web Interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Facebook E2E Cookies Server</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #eee;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            text-align: center;
            padding: 30px 0;
            border-bottom: 1px solid #2c3e66;
            margin-bottom: 30px;
        }
        
        .header h1 {
            font-size: 2.5rem;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .header p {
            color: #888;
            margin-top: 10px;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .card {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            padding: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
        }
        
        .card h2 {
            margin-bottom: 20px;
            font-size: 1.3rem;
            color: #667eea;
        }
        
        .form-group {
            margin-bottom: 15px;
        }
        
        label {
            display: block;
            margin-bottom: 5px;
            color: #aaa;
            font-size: 0.9rem;
        }
        
        input, textarea, select {
            width: 100%;
            padding: 10px;
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid #2c3e66;
            border-radius: 8px;
            color: #eee;
            font-size: 0.9rem;
        }
        
        input:focus, textarea:focus, select:focus {
            outline: none;
            border-color: #667eea;
        }
        
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.9rem;
            transition: transform 0.2s, opacity 0.2s;
        }
        
        button:hover {
            transform: translateY(-2px);
            opacity: 0.9;
        }
        
        button.danger {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }
        
        button.success {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        }
        
        .status {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: bold;
        }
        
        .status.online {
            background: #10b981;
            color: white;
        }
        
        .status.offline {
            background: #ef4444;
            color: white;
        }
        
        .status.pending {
            background: #f59e0b;
            color: white;
        }
        
        .log-container {
            background: rgba(0, 0, 0, 0.4);
            border-radius: 10px;
            padding: 15px;
            max-height: 300px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 0.8rem;
        }
        
        .log-entry {
            padding: 5px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            color: #10b981;
        }
        
        .log-entry.error {
            color: #ef4444;
        }
        
        .log-entry.warning {
            color: #f59e0b;
        }
        
        .session-list {
            margin-top: 15px;
        }
        
        .session-item {
            background: rgba(0, 0, 0, 0.3);
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .session-info {
            flex: 1;
        }
        
        .session-name {
            font-weight: bold;
            color: #667eea;
        }
        
        .session-status {
            font-size: 0.8rem;
            margin-top: 4px;
        }
        
        .api-section {
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #2c3e66;
        }
        
        .api-endpoint {
            background: rgba(0, 0, 0, 0.3);
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 10px;
        }
        
        .method {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: bold;
            margin-right: 10px;
        }
        
        .method.post {
            background: #10b981;
        }
        
        .method.get {
            background: #3b82f6;
        }
        
        .url {
            color: #aaa;
            font-family: monospace;
        }
        
        .response-example {
            background: rgba(0, 0, 0, 0.3);
            padding: 10px;
            border-radius: 8px;
            margin-top: 10px;
            font-family: monospace;
            font-size: 0.7rem;
            overflow-x: auto;
        }
        
        @media (max-width: 768px) {
            .grid {
                grid-template-columns: 1fr;
            }
            
            .header h1 {
                font-size: 1.8rem;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🍪 Facebook E2E Cookies Server</h1>
            <p>Complete Facebook Messenger Automation with Cookie-Based Authentication</p>
        </div>
        
        <div class="grid">
            <!-- Create Session Card -->
            <div class="card">
                <h2>🔐 Create New Session</h2>
                <div class="form-group">
                    <label>Session Name</label>
                    <input type="text" id="sessionName" placeholder="e.g., my_business_account">
                </div>
                <div class="form-group">
                    <label>Facebook Email</label>
                    <input type="email" id="fbEmail" placeholder="your@email.com">
                </div>
                <div class="form-group">
                    <label>Facebook Password</label>
                    <input type="password" id="fbPassword" placeholder="********">
                </div>
                <button onclick="createSession()">Create Session & Login</button>
                <div class="api-section">
                    <p style="font-size: 0.8rem; color: #888; margin-top: 10px;">
                        💡 Or upload existing cookies JSON file:
                    </p>
                    <input type="file" id="cookiesFile" accept=".json" style="margin-top: 10px;">
                    <button onclick="uploadCookies()" style="margin-top: 10px;">Upload Cookies</button>
                </div>
            </div>
            
            <!-- Sessions Card -->
            <div class="card">
                <h2>📱 Active Sessions</h2>
                <div id="sessionsList" class="session-list">
                    <p style="color: #888;">No active sessions. Create one above.</p>
                </div>
            </div>
        </div>
        
        <!-- Send Message Card -->
        <div class="card">
            <h2>✉️ Send Message</h2>
            <div class="form-group">
                <label>Select Session</label>
                <select id="sendSession">
                    <option value="">-- Select Session --</option>
                </select>
            </div>
            <div class="form-group">
                <label>Recipient ID (Facebook User/Page ID)</label>
                <input type="text" id="recipientId" placeholder="e.g., 1000123456789">
            </div>
            <div class="form-group">
                <label>Message</label>
                <textarea id="message" rows="3" placeholder="Enter your message here..."></textarea>
            </div>
            <div class="form-group">
                <label>Send as Page (if available)</label>
                <select id="sendAsPage">
                    <option value="false">No - Send as Profile</option>
                    <option value="true">Yes - Send as Page</option>
                </select>
            </div>
            <button class="success" onclick="sendMessage()">📤 Send Message</button>
        </div>
        
        <!-- Bulk Messages Card -->
        <div class="card">
            <h2>📨 Bulk Messages</h2>
            <div class="form-group">
                <label>Select Session</label>
                <select id="bulkSession">
                    <option value="">-- Select Session --</option>
                </select>
            </div>
            <div class="form-group">
                <label>Recipient ID</label>
                <input type="text" id="bulkRecipientId" placeholder="Facebook User/Page ID">
            </div>
            <div class="form-group">
                <label>Messages (one per line)</label>
                <textarea id="bulkMessages" rows="5" placeholder="Message 1&#10;Message 2&#10;Message 3"></textarea>
            </div>
            <div class="form-group">
                <label>Delay between messages (seconds)</label>
                <input type="number" id="messageDelay" value="5" min="1" max="60">
            </div>
            <button onclick="sendBulkMessages()">🚀 Start Bulk Sending</button>
        </div>
        
        <!-- Logs Card -->
        <div class="card">
            <h2>📋 Activity Logs</h2>
            <div id="logs" class="log-container">
                <div class="log-entry">Server ready. Ready to handle requests...</div>
            </div>
            <button onclick="clearLogs()" style="margin-top: 10px;" class="danger">Clear Logs</button>
        </div>
        
        <!-- API Documentation -->
        <div class="card">
            <h2>📚 API Documentation</h2>
            <div class="api-endpoint">
                <span class="method post">POST</span>
                <span class="url">/api/session/create</span>
                <div class="response-example">
                    { "name": "session_name", "email": "user@example.com", "password": "*****" }
                </div>
            </div>
            <div class="api-endpoint">
                <span class="method post">POST</span>
                <span class="url">/api/session/upload-cookies</span>
                <div class="response-example">
                    { "name": "session_name", "cookies": [...] }
                </div>
            </div>
            <div class="api-endpoint">
                <span class="method get">GET</span>
                <span class="url">/api/sessions</span>
                <div class="response-example">
                    { "sessions": [...] }
                </div>
            </div>
            <div class="api-endpoint">
                <span class="method post">POST</span>
                <span class="url">/api/send</span>
                <div class="response-example">
                    { "session": "name", "recipient_id": "123", "message": "Hello" }
                </div>
            </div>
            <div class="api-endpoint">
                <span class="method post">POST</span>
                <span class="url">/api/send-bulk</span>
                <div class="response-example">
                    { "session": "name", "recipient_id": "123", "messages": ["msg1", "msg2"], "delay": 5 }
                </div>
            </div>
            <div class="api-endpoint">
                <span class="method get">GET</span>
                <span class="url">/api/status/&lt;session_name&gt;</span>
            </div>
            <div class="api-endpoint">
                <span class="method delete">DELETE</span>
                <span class="url">/api/session/&lt;session_name&gt;</span>
            </div>
        </div>
    </div>
    
    <script>
        let logInterval = null;
        
        function addLog(message, type = 'info') {
            const logsDiv = document.getElementById('logs');
            const logEntry = document.createElement('div');
            logEntry.className = `log-entry ${type === 'error' ? 'error' : (type === 'warning' ? 'warning' : '')}`;
            const timestamp = new Date().toLocaleTimeString();
            logEntry.textContent = `[${timestamp}] ${message}`;
            logsDiv.appendChild(logEntry);
            logsDiv.scrollTop = logsDiv.scrollHeight;
            
            // Keep only last 100 logs
            while (logsDiv.children.length > 100) {
                logsDiv.removeChild(logsDiv.firstChild);
            }
        }
        
        async function createSession() {
            const name = document.getElementById('sessionName').value;
            const email = document.getElementById('fbEmail').value;
            const password = document.getElementById('fbPassword').value;
            
            if (!name || !email || !password) {
                addLog('Please fill all fields', 'error');
                return;
            }
            
            addLog(`Creating session "${name}"...`);
            
            try {
                const response = await fetch('/api/session/create', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name, email, password })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    addLog(`✅ Session "${name}" created and logged in successfully!`);
                    loadSessions();
                    clearForm();
                } else {
                    addLog(`❌ Error: ${data.error}`, 'error');
                }
            } catch (error) {
                addLog(`❌ Request failed: ${error.message}`, 'error');
            }
        }
        
        async function uploadCookies() {
            const fileInput = document.getElementById('cookiesFile');
            const sessionName = document.getElementById('sessionName').value;
            
            if (!sessionName) {
                addLog('Please enter a session name first', 'error');
                return;
            }
            
            if (!fileInput.files.length) {
                addLog('Please select a cookies JSON file', 'error');
                return;
            }
            
            const file = fileInput.files[0];
            const reader = new FileReader();
            
            reader.onload = async function(e) {
                try {
                    const cookies = JSON.parse(e.target.result);
                    
                    const response = await fetch('/api/session/upload-cookies', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ name: sessionName, cookies })
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        addLog(`✅ Session "${sessionName}" created with uploaded cookies!`);
                        loadSessions();
                        clearForm();
                    } else {
                        addLog(`❌ Error: ${data.error}`, 'error');
                    }
                } catch (error) {
                    addLog(`❌ Invalid cookies file: ${error.message}`, 'error');
                }
            };
            
            reader.readAsText(file);
        }
        
        async function loadSessions() {
            try {
                const response = await fetch('/api/sessions');
                const data = await response.json();
                
                const sessionsList = document.getElementById('sessionsList');
                const sendSelect = document.getElementById('sendSession');
                const bulkSelect = document.getElementById('bulkSession');
                
                if (data.sessions && data.sessions.length > 0) {
                    sessionsList.innerHTML = '';
                    sendSelect.innerHTML = '<option value="">-- Select Session --</option>';
                    bulkSelect.innerHTML = '<option value="">-- Select Session --</option>';
                    
                    data.sessions.forEach(session => {
                        // Add to sessions list
                        const sessionDiv = document.createElement('div');
                        sessionDiv.className = 'session-item';
                        sessionDiv.innerHTML = `
                            <div class="session-info">
                                <div class="session-name">${session.name}</div>
                                <div class="session-status">
                                    Status: <span class="status ${session.status === 'online' ? 'online' : 'offline'}">${session.status}</span>
                                    ${session.page_name ? `<br>Page: ${session.page_name}` : ''}
                                </div>
                            </div>
                            <div>
                                <button onclick="deleteSession('${session.name}')" class="danger" style="padding: 5px 10px; font-size: 0.8rem;">Delete</button>
                            </div>
                        `;
                        sessionsList.appendChild(sessionDiv);
                        
                        // Add to send select
                        const option = document.createElement('option');
                        option.value = session.name;
                        option.textContent = `${session.name} (${session.status})`;
                        sendSelect.appendChild(option);
                        
                        const bulkOption = document.createElement('option');
                        bulkOption.value = session.name;
                        bulkOption.textContent = `${session.name} (${session.status})`;
                        bulkSelect.appendChild(bulkOption);
                    });
                } else {
                    sessionsList.innerHTML = '<p style="color: #888;">No active sessions. Create one above.</p>';
                }
            } catch (error) {
                addLog(`Failed to load sessions: ${error.message}`, 'error');
            }
        }
        
        async function sendMessage() {
            const session = document.getElementById('sendSession').value;
            const recipientId = document.getElementById('recipientId').value;
            const message = document.getElementById('message').value;
            const sendAsPage = document.getElementById('sendAsPage').value === 'true';
            
            if (!session || !recipientId || !message) {
                addLog('Please fill all fields', 'error');
                return;
            }
            
            addLog(`Sending message via "${session}"...`);
            
            try {
                const response = await fetch('/api/send', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session, recipient_id: recipientId, message, send_as_page: sendAsPage })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    addLog(`✅ Message sent successfully! Message ID: ${data.message_id || 'N/A'}`);
                    document.getElementById('message').value = '';
                } else {
                    addLog(`❌ Failed to send: ${data.error}`, 'error');
                }
            } catch (error) {
                addLog(`❌ Request failed: ${error.message}`, 'error');
            }
        }
        
        async function sendBulkMessages() {
            const session = document.getElementById('bulkSession').value;
            const recipientId = document.getElementById('bulkRecipientId').value;
            const messagesText = document.getElementById('bulkMessages').value;
            const delay = parseInt(document.getElementById('messageDelay').value);
            
            if (!session || !recipientId || !messagesText) {
                addLog('Please fill all fields', 'error');
                return;
            }
            
            const messages = messagesText.split('\\n').filter(m => m.trim());
            
            if (messages.length === 0) {
                addLog('Please enter at least one message', 'error');
                return;
            }
            
            addLog(`Starting bulk send: ${messages.length} messages with ${delay}s delay`);
            
            try {
                const response = await fetch('/api/send-bulk', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session, recipient_id: recipientId, messages, delay })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    addLog(`✅ Bulk send completed! Sent: ${data.sent}, Failed: ${data.failed}`);
                    document.getElementById('bulkMessages').value = '';
                } else {
                    addLog(`❌ Bulk send failed: ${data.error}`, 'error');
                }
            } catch (error) {
                addLog(`❌ Request failed: ${error.message}`, 'error');
            }
        }
        
        async function deleteSession(sessionName) {
            if (!confirm(`Delete session "${sessionName}"?`)) return;
            
            try {
                const response = await fetch(`/api/session/${sessionName}`, { method: 'DELETE' });
                const data = await response.json();
                
                if (data.success) {
                    addLog(`✅ Session "${sessionName}" deleted`);
                    loadSessions();
                } else {
                    addLog(`❌ Failed to delete: ${data.error}`, 'error');
                }
            } catch (error) {
                addLog(`❌ Request failed: ${error.message}`, 'error');
            }
        }
        
        function clearForm() {
            document.getElementById('sessionName').value = '';
            document.getElementById('fbEmail').value = '';
            document.getElementById('fbPassword').value = '';
            document.getElementById('cookiesFile').value = '';
        }
        
        function clearLogs() {
            const logsDiv = document.getElementById('logs');
            logsDiv.innerHTML = '<div class="log-entry">Logs cleared.</div>';
        }
        
        // Auto-refresh sessions every 10 seconds
        setInterval(loadSessions, 10000);
        
        // Initial load
        loadSessions();
    </script>
</body>
</html>
"""


class FacebookSession:
    """Manage Facebook session with cookies"""
    
    def __init__(self, name, cookies_data=None, email=None, password=None):
        self.name = name
        self.email = email
        self.password = password
        self.cookies_data = cookies_data
        self.access_token = None
        self.user_id = None
        self.page_id = None
        self.page_name = None
        self.status = "offline"
        self.created_at = datetime.now()
        self.api_version = "v18.0"
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        
        if cookies_data:
            self.load_from_cookies(cookies_data)
    
    def load_from_cookies(self, cookies_data):
        """Extract information from cookies"""
        self.cookies_data = cookies_data
        for cookie in cookies_data:
            if cookie.get('name') == 'c_user':
                self.user_id = cookie.get('value')
            elif cookie.get('name') == 'xs':
                self.xs_token = cookie.get('value')
        
        self.status = "online" if self.user_id else "pending"
        self.save_cookies()
    
    def save_cookies(self):
        """Save cookies to file"""
        cookies_path = os.path.join(COOKIES_DIR, f"{self.name}_cookies.pkl")
        with open(cookies_path, 'wb') as f:
            pickle.dump(self.cookies_data, f)
        
        # Also save session info
        session_info = {
            'name': self.name,
            'email': self.email,
            'user_id': self.user_id,
            'page_id': self.page_id,
            'page_name': self.page_name,
            'status': self.status,
            'created_at': self.created_at.isoformat()
        }
        with open(os.path.join(SESSIONS_DIR, f"{self.name}.json"), 'w') as f:
            json.dump(session_info, f, indent=2)
    
    @classmethod
    def load(cls, name):
        """Load existing session"""
        cookies_path = os.path.join(COOKIES_DIR, f"{name}_cookies.pkl")
        info_path = os.path.join(SESSIONS_DIR, f"{name}.json")
        
        if os.path.exists(cookies_path) and os.path.exists(info_path):
            with open(cookies_path, 'rb') as f:
                cookies_data = pickle.load(f)
            
            with open(info_path, 'r') as f:
                info = json.load(f)
            
            session = cls(name, cookies_data)
            session.email = info.get('email')
            session.user_id = info.get('user_id')
            session.page_id = info.get('page_id')
            session.page_name = info.get('page_name')
            session.status = info.get('status', 'online')
            return session
        
        return None
    
    def login_with_selenium(self, email, password, log_callback=None):
        """Login to Facebook using Selenium and save cookies"""
        driver = None
        try:
            if log_callback:
                log_callback(f"🌐 Starting Chrome browser for {self.name}...")
            
            chrome_options = Options()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--window-size=1280,720')
            chrome_options.add_argument('--headless')  # Run in background
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            driver = webdriver.Chrome(options=chrome_options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            if log_callback:
                log_callback(f"📍 Opening Facebook login page...")
            
            driver.get('https://www.facebook.com/')
            time.sleep(3)
            
            # Fill login form
            if log_callback:
                log_callback(f"🔑 Entering credentials...")
            
            email_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, 'email'))
            )
            email_field.send_keys(email)
            
            pass_field = driver.find_element(By.ID, 'pass')
            pass_field.send_keys(password)
            
            login_button = driver.find_element(By.NAME, 'login')
            login_button.click()
            
            if log_callback:
                log_callback(f"⏳ Waiting for login to complete...")
            
            time.sleep(5)
            
            # Check if login was successful
            if 'home' in driver.current_url or 'facebook.com/?sk=welcome' in driver.current_url:
                if log_callback:
                    log_callback(f"✅ Login successful! Saving cookies...")
                
                cookies = driver.get_cookies()
                self.cookies_data = cookies
                self.email = email
                self.password = password
                
                # Extract user ID from cookies
                for cookie in cookies:
                    if cookie.get('name') == 'c_user':
                        self.user_id = cookie.get('value')
                
                self.status = "online"
                self.save_cookies()
                
                # Try to get pages
                self.get_user_pages(log_callback)
                
                return True, "Login successful"
            else:
                if log_callback:
                    log_callback(f"❌ Login failed! Please check your credentials.")
                return False, "Login failed"
                
        except Exception as e:
            if log_callback:
                log_callback(f"❌ Error during login: {str(e)}")
            return False, str(e)
        finally:
            if driver:
                driver.quit()
    
    def get_user_pages(self, log_callback=None):
        """Get pages managed by user"""
        try:
            # This would require an access token
            # For now, we'll set a placeholder
            if log_callback:
                log_callback(f"💡 Note: For Page API access, you need a Page Access Token")
        except Exception as e:
            if log_callback:
                log_callback(f"⚠️ Could not fetch pages: {str(e)}")
    
    def get_access_token(self):
        """Extract or generate access token"""
        # Try to get from cookies first
        if self.cookies_data:
            for cookie in self.cookies_data:
                if cookie.get('name') == 'c_user':
                    # This is not a real token, just the user ID
                    # Actual token needs to be obtained via Graph API
                    pass
        
        # Return dummy for now - real implementation would need OAuth
        return None
    
    def send_message(self, recipient_id, message, send_as_page=False, log_callback=None):
        """Send a message via Facebook Graph API or direct request"""
        try:
            # Try using Graph API first
            access_token = self.get_access_token()
            
            if access_token:
                url = f"{self.base_url}/me/messages"
                headers = {"Content-Type": "application/json"}
                data = {
                    "recipient": {"id": recipient_id},
                    "message": {"text": message},
                    "access_token": access_token
                }
                
                if send_as_page and self.page_id:
                    data["messaging_type"] = "RESPONSE"
                
                response = requests.post(url, json=data, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    result = response.json()
                    return True, result.get('message_id', 'sent')
                else:
                    error_msg = response.json().get('error', {}).get('message', 'Unknown error')
                    return False, error_msg
            else:
                # Fallback to cookie-based method (limited functionality)
                return False, "Access token required. Please configure a valid Facebook Access Token."
                
        except Exception as e:
            return False, str(e)
    
    def delete(self):
        """Delete session files"""
        cookies_path = os.path.join(COOKIES_DIR, f"{self.name}_cookies.pkl")
        info_path = os.path.join(SESSIONS_DIR, f"{self.name}.json")
        
        if os.path.exists(cookies_path):
            os.remove(cookies_path)
        if os.path.exists(info_path):
            os.remove(info_path)


class CookieServer:
    """Main server class to manage Facebook sessions"""
    
    def __init__(self):
        self.sessions = {}
        self.load_existing_sessions()
    
    def load_existing_sessions(self):
        """Load all existing sessions from disk"""
        if os.path.exists(SESSIONS_DIR):
            for file in os.listdir(SESSIONS_DIR):
                if file.endswith('.json'):
                    session_name = file[:-5]
                    session = FacebookSession.load(session_name)
                    if session:
                        self.sessions[session_name] = session
    
    def create_session(self, name, email, password, log_callback=None):
        """Create new session with login"""
        if name in self.sessions:
            return False, "Session name already exists"
        
        session = FacebookSession(name)
        success, message = session.login_with_selenium(email, password, log_callback)
        
        if success:
            self.sessions[name] = session
            return True, message
        else:
            return False, message
    
    def create_session_with_cookies(self, name, cookies_data, log_callback=None):
        """Create session from existing cookies"""
        if name in self.sessions:
            return False, "Session name already exists"
        
        session = FacebookSession(name, cookies_data)
        self.sessions[name] = session
        
        if log_callback:
            log_callback(f"✅ Session '{name}' created from cookies")
        
        return True, "Session created"
    
    def get_session(self, name):
        """Get session by name"""
        return self.sessions.get(name)
    
    def delete_session(self, name):
        """Delete session"""
        if name in self.sessions:
            self.sessions[name].delete()
            del self.sessions[name]
            return True
        return False
    
    def get_all_sessions(self):
        """Get all sessions info"""
        sessions_info = []
        for name, session in self.sessions.items():
            sessions_info.append({
                'name': name,
                'status': session.status,
                'user_id': session.user_id,
                'page_name': session.page_name,
                'created_at': session.created_at.isoformat() if session.created_at else None
            })
        return sessions_info


# Initialize server
server = CookieServer()
session_logs = {}


def add_log(session_name, message, level='info'):
    """Add log entry for a session"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    
    if session_name not in session_logs:
        session_logs[session_name] = []
    
    session_logs[session_name].append({
        'timestamp': timestamp,
        'message': message,
        'level': level
    })
    
    # Keep only last 100 logs per session
    if len(session_logs[session_name]) > 100:
        session_logs[session_name] = session_logs[session_name][-100:]
    
    # Also print to console
    print(f"[{session_name}] {message}")


# API Routes
@app.route('/')
def index():
    """Main web interface"""
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/session/create', methods=['POST'])
def create_session():
    """Create new session with login"""
    data = request.json
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    
    if not all([name, email, password]):
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400
    
    def log_callback(msg):
        add_log(name, msg)
    
    success, message = server.create_session(name, email, password, log_callback)
    
    if success:
        return jsonify({'success': True, 'message': message, 'session': name})
    else:
        return jsonify({'success': False, 'error': message}), 400


@app.route('/api/session/upload-cookies', methods=['POST'])
def upload_cookies():
    """Create session from uploaded cookies"""
    data = request.json
    name = data.get('name')
    cookies = data.get('cookies')
    
    if not name or not cookies:
        return jsonify({'success': False, 'error': 'Missing name or cookies'}), 400
    
    if not isinstance(cookies, list):
        return jsonify({'success': False, 'error': 'Cookies must be an array'}), 400
    
    def log_callback(msg):
        add_log(name, msg)
    
    success, message = server.create_session_with_cookies(name, cookies, log_callback)
    
    if success:
        return jsonify({'success': True, 'message': message, 'session': name})
    else:
        return jsonify({'success': False, 'error': message}), 400


@app.route('/api/sessions', methods=['GET'])
def list_sessions():
    """List all sessions"""
    sessions = server.get_all_sessions()
    return jsonify({'sessions': sessions, 'count': len(sessions)})


@app.route('/api/session/<name>', methods=['DELETE'])
def delete_session(name):
    """Delete a session"""
    if server.delete_session(name):
        return jsonify({'success': True, 'message': f'Session {name} deleted'})
    else:
        return jsonify({'success': False, 'error': 'Session not found'}), 404


@app.route('/api/session/<name>/status', methods=['GET'])
def session_status(name):
    """Get session status"""
    session = server.get_session(name)
    if session:
        return jsonify({
            'success': True,
            'session': {
                'name': session.name,
                'status': session.status,
                'user_id': session.user_id,
                'page_name': session.page_name,
                'created_at': session.created_at.isoformat() if session.created_at else None
            }
        })
    else:
        return jsonify({'success': False, 'error': 'Session not found'}), 404


@app.route('/api/send', methods=['POST'])
def send_message():
    """Send a single message"""
    data = request.json
    session_name = data.get('session')
    recipient_id = data.get('recipient_id')
    message = data.get('message')
    send_as_page = data.get('send_as_page', False)
    
    if not all([session_name, recipient_id, message]):
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400
    
    session = server.get_session(session_name)
    if not session:
        return jsonify({'success': False, 'error': 'Session not found'}), 404
    
    def log_callback(msg):
        add_log(session_name, msg)
    
    add_log(session_name, f"📤 Sending message to {recipient_id}: {message[:50]}...")
    
    success, result = session.send_message(recipient_id, message, send_as_page, log_callback)
    
    if success:
        add_log(session_name, f"✅ Message sent successfully: {result}")
        return jsonify({'success': True, 'message_id': result})
    else:
        add_log(session_name, f"❌ Failed to send: {result}", 'error')
        return jsonify({'success': False, 'error': result}), 400


@app.route('/api/send-bulk', methods=['POST'])
def send_bulk_messages():
    """Send multiple messages with delay"""
    data = request.json
    session_name = data.get('session')
    recipient_id = data.get('recipient_id')
    messages = data.get('messages', [])
    delay = data.get('delay', 5)
    send_as_page = data.get('send_as_page', False)
    
    if not all([session_name, recipient_id]):
        return jsonify({'success': False, 'error': 'Missing session or recipient_id'}), 400
    
    if not messages or not isinstance(messages, list):
        return jsonify({'success': False, 'error': 'Messages must be a non-empty array'}), 400
    
    session = server.get_session(session_name)
    if not session:
        return jsonify({'success': False, 'error': 'Session not found'}), 404
    
    add_log(session_name, f"🚀 Starting bulk send: {len(messages)} messages to {recipient_id}")
    
    sent = 0
    failed = 0
    results = []
    
    for i, msg in enumerate(messages):
        msg = msg.strip()
        if not msg:
            continue
        
        add_log(session_name, f"📤 Sending message {i+1}/{len(messages)}...")
        
        success, result = session.send_message(recipient_id, msg, send_as_page)
        
        if success:
            sent += 1
            add_log(session_name, f"✅ Message {i+1}/{len(messages)} sent")
            results.append({'message': msg[:50] + '...', 'status': 'sent', 'message_id': result})
        else:
            failed += 1
            add_log(session_name, f"❌ Message {i+1}/{len(messages)} failed: {result}", 'error')
            results.append({'message': msg[:50] + '...', 'status': 'failed', 'error': result})
        
        if i < len(messages) - 1:
            time.sleep(delay)
    
    add_log(session_name, f"✅ Bulk send completed: Sent: {sent}, Failed: {failed}")
    
    return jsonify({
        'success': True,
        'sent': sent,
        'failed': failed,
        'total': len(messages),
        'results': results
    })


@app.route('/api/logs/<session_name>', methods=['GET'])
def get_logs(session_name):
    """Get logs for a session"""
    logs = session_logs.get(session_name, [])
    return jsonify({'session': session_name, 'logs': logs})


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'sessions': len(server.sessions),
        'timestamp': datetime.now().isoformat()
    })


if __name__ == '__main__':
    print("=" * 60)
    print("🍪 Facebook E2E Cookies Server")
    print("=" * 60)
    print(f"📁 Cookies Directory: {os.path.abspath(COOKIES_DIR)}")
    print(f"📁 Sessions Directory: {os.path.abspath(SESSIONS_DIR)}")
    print("")
    print("🌐 Web Interface: http://localhost:5000")
    print("📚 API Base URL: http://localhost:5000/api")
    print("")
    print("Available Endpoints:")
    print("  POST   /api/session/create         - Create new session with login")
    print("  POST   /api/session/upload-cookies - Upload existing cookies")
    print("  GET    /api/sessions               - List all sessions")
    print("  GET    /api/session/<name>/status  - Get session status")
    print("  DELETE /api/session/<name>         - Delete session")
    print("  POST   /api/send                   - Send single message")
    print("  POST   /api/send-bulk              - Send multiple messages")
    print("  GET    /api/logs/<session_name>    - Get session logs")
    print("  GET    /api/health                 - Health check")
    print("=" * 60)
    print("")
    print("⚠️  Requirements:")
    print("   - Chrome browser installed")
    print("   - ChromeDriver matching Chrome version")
    print("   - For manual cookies: Export as JSON from browser extension")
    print("")
    
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
