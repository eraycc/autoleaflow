#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LeafLow Auto Check-in Control Panel
Web-based management interface for the check-in system
"""

import os
import json
import sqlite3
import hashlib
import secrets
import threading
import schedule
import time
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import jwt
import logging
from checkin_token import LeafLowTokenCheckin
import random

# Configuration
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', secrets.token_hex(32))
CORS(app)

# Environment variables
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')
DB_TYPE = os.getenv('DB_TYPE', 'sqlite')  # sqlite or mysql
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '3306')
DB_NAME = os.getenv('DB_NAME', 'leaflow_checkin')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
PORT = int(os.getenv('PORT', '8181'))

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('control_panel.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        if DB_TYPE == 'mysql':
            import pymysql
            self.conn = pymysql.connect(
                host=DB_HOST,
                port=int(DB_PORT),
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                charset='utf8mb4'
            )
        else:
            self.conn = sqlite3.connect('leaflow_checkin.db', check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
        self.init_tables()
    
    def init_tables(self):
        cursor = self.conn.cursor()
        
        # Accounts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(255) UNIQUE NOT NULL,
                token_data TEXT NOT NULL,
                enabled BOOLEAN DEFAULT 1,
                checkin_time VARCHAR(5) DEFAULT '01:00',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Check-in history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS checkin_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                success BOOLEAN NOT NULL,
                message TEXT,
                checkin_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES accounts(id)
            )
        ''')
        
        # Notification settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notification_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                enabled BOOLEAN DEFAULT 1,
                telegram_bot_token TEXT,
                telegram_user_id TEXT,
                wechat_webhook_key TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Initialize notification settings if not exists
        cursor.execute('SELECT COUNT(*) as count FROM notification_settings')
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO notification_settings (enabled, telegram_bot_token, telegram_user_id, wechat_webhook_key)
                VALUES (?, ?, ?, ?)
            ''', (1, os.getenv('TG_BOT_TOKEN', ''), os.getenv('TG_USER_ID', ''), os.getenv('QYWX_KEY', '')))
        
        self.conn.commit()
    
    def execute(self, query, params=None):
        cursor = self.conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        self.conn.commit()
        return cursor
    
    def fetchone(self, query, params=None):
        cursor = self.execute(query, params)
        return cursor.fetchone()
    
    def fetchall(self, query, params=None):
        cursor = self.execute(query, params)
        return cursor.fetchall()

db = Database()

# JWT authentication decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token is invalid!'}), 401
        
        return f(*args, **kwargs)
    
    return decorated

# Scheduler for automatic check-ins
class CheckinScheduler:
    def __init__(self):
        self.scheduler_thread = None
        self.running = False
        
    def start(self):
        if not self.running:
            self.running = True
            self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self.scheduler_thread.start()
            logger.info("Scheduler started")
    
    def stop(self):
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        logger.info("Scheduler stopped")
    
    def _run_scheduler(self):
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def schedule_checkins(self):
        schedule.clear()
        accounts = db.fetchall('SELECT * FROM accounts WHERE enabled = 1')
        
        for account in accounts:
            checkin_time = account['checkin_time'] if 'checkin_time' in account else '01:00'
            schedule.every().day.at(checkin_time).do(self.perform_checkin, account['id'])
            logger.info(f"Scheduled check-in for account {account['name']} at {checkin_time}")
    
    def perform_checkin(self, account_id):
        account = db.fetchone('SELECT * FROM accounts WHERE id = ?', (account_id,))
        if not account or not account['enabled']:
            return
        
        try:
            # Add random delay for multiple accounts
            delay = random.randint(30, 60)
            time.sleep(delay)
            
            # Prepare account data for check-in
            token_data = json.loads(account['token_data'])
            account_data = {'token_data': token_data, 'enabled': True}
            
            # Create temporary config
            temp_config = {
                'settings': {
                    'log_level': 'INFO',
                    'retry_delay': 3,
                    'timeout': 30,
                    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                },
                'accounts': [account_data]
            }
            
            # Save temporary config
            with open('temp_config.json', 'w') as f:
                json.dump(temp_config, f)
            
            # Perform check-in
            checkin = LeafLowTokenCheckin('temp_config.json')
            success, message = checkin.perform_token_checkin(account_data, account['name'])
            
            # Record history
            db.execute('''
                INSERT INTO checkin_history (account_id, success, message, checkin_date)
                VALUES (?, ?, ?, ?)
            ''', (account_id, success, message, datetime.now().date()))
            
            # Send notification if enabled
            self.send_notification(account['name'], success, message)
            
            logger.info(f"Check-in for {account['name']}: {'Success' if success else 'Failed'} - {message}")
            
        except Exception as e:
            logger.error(f"Check-in error for account {account_id}: {str(e)}")
            db.execute('''
                INSERT INTO checkin_history (account_id, success, message, checkin_date)
                VALUES (?, ?, ?, ?)
            ''', (account_id, False, str(e), datetime.now().date()))
    
    def send_notification(self, account_name, success, message):
        settings = db.fetchone('SELECT * FROM notification_settings WHERE id = 1')
        if not settings or not settings['enabled']:
            return
        
        try:
            from notify import send
            title = f"LeafLow Check-in: {account_name}"
            content = f"{'✅ Success' if success else '❌ Failed'}: {message}"
            
            config = {}
            if settings['telegram_bot_token'] and settings['telegram_user_id']:
                config['TG_BOT_TOKEN'] = settings['telegram_bot_token']
                config['TG_USER_ID'] = settings['telegram_user_id']
            if settings['wechat_webhook_key']:
                config['QYWX_KEY'] = settings['wechat_webhook_key']
            
            if config:
                send(title, content, **config)
        except Exception as e:
            logger.error(f"Notification error: {str(e)}")

scheduler = CheckinScheduler()

# Routes
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        token = jwt.encode({
            'user': username,
            'exp': datetime.utcnow() + timedelta(days=7)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        return jsonify({'token': token, 'message': 'Login successful'})
    
    return jsonify({'message': 'Invalid credentials'}), 401

@app.route('/api/dashboard', methods=['GET'])
@token_required
def dashboard():
    # Get statistics
    total_accounts = db.fetchone('SELECT COUNT(*) as count FROM accounts')[0]
    enabled_accounts = db.fetchone('SELECT COUNT(*) as count FROM accounts WHERE enabled = 1')[0]
    
    # Today's check-ins
    today = datetime.now().date()
    today_checkins = db.fetchall('''
        SELECT a.name, ch.success, ch.message, ch.created_at
        FROM checkin_history ch
        JOIN accounts a ON ch.account_id = a.id
        WHERE ch.checkin_date = ?
        ORDER BY ch.created_at DESC
    ''', (today,))
    
    # Overall statistics
    total_checkins = db.fetchone('SELECT COUNT(*) as count FROM checkin_history')[0]
    successful_checkins = db.fetchone('SELECT COUNT(*) as count FROM checkin_history WHERE success = 1')[0]
    
    # Recent history (last 7 days)
    recent_history = db.fetchall('''
        SELECT checkin_date, 
               COUNT(*) as total,
               SUM(success) as successful
        FROM checkin_history
        WHERE checkin_date >= date('now', '-7 days')
        GROUP BY checkin_date
        ORDER BY checkin_date DESC
    ''')
    
    return jsonify({
        'total_accounts': total_accounts,
        'enabled_accounts': enabled_accounts,
        'today_checkins': [dict(row) for row in today_checkins],
        'total_checkins': total_checkins,
        'successful_checkins': successful_checkins,
        'success_rate': round(successful_checkins / total_checkins * 100, 2) if total_checkins > 0 else 0,
        'recent_history': [dict(row) for row in recent_history]
    })

@app.route('/api/accounts', methods=['GET'])
@token_required
def get_accounts():
    accounts = db.fetchall('SELECT id, name, enabled, checkin_time, created_at FROM accounts')
    return jsonify([dict(row) for row in accounts])

@app.route('/api/accounts', methods=['POST'])
@token_required
def add_account():
    data = request.json
    name = data.get('name')
    token_data = data.get('token_data')
    checkin_time = data.get('checkin_time', '01:00')
    
    if not name or not token_data:
        return jsonify({'message': 'Name and token_data are required'}), 400
    
    try:
        db.execute('''
            INSERT INTO accounts (name, token_data, checkin_time)
            VALUES (?, ?, ?)
        ''', (name, json.dumps(token_data), checkin_time))
        
        scheduler.schedule_checkins()
        return jsonify({'message': 'Account added successfully'})
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 400

@app.route('/api/accounts/<int:account_id>', methods=['PUT'])
@token_required
def update_account(account_id):
    data = request.json
    
    updates = []
    params = []
    
    if 'enabled' in data:
        updates.append('enabled = ?')
        params.append(data['enabled'])
    
    if 'checkin_time' in data:
        updates.append('checkin_time = ?')
        params.append(data['checkin_time'])
    
    if 'token_data' in data:
        updates.append('token_data = ?')
        params.append(json.dumps(data['token_data']))
    
    if updates:
        params.append(account_id)
        db.execute(f'''
            UPDATE accounts 
            SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', params)
        
        scheduler.schedule_checkins()
        return jsonify({'message': 'Account updated successfully'})
    
    return jsonify({'message': 'No updates provided'}), 400

@app.route('/api/accounts/<int:account_id>', methods=['DELETE'])
@token_required
def delete_account(account_id):
    db.execute('DELETE FROM checkin_history WHERE account_id = ?', (account_id,))
    db.execute('DELETE FROM accounts WHERE id = ?', (account_id,))
    scheduler.schedule_checkins()
    return jsonify({'message': 'Account deleted successfully'})

@app.route('/api/notification', methods=['GET'])
@token_required
def get_notification_settings():
    settings = db.fetchone('SELECT * FROM notification_settings WHERE id = 1')
    if settings:
        return jsonify(dict(settings))
    return jsonify({})

@app.route('/api/notification', methods=['PUT'])
@token_required
def update_notification_settings():
    data = request.json
    
    db.execute('''
        UPDATE notification_settings
        SET enabled = ?, telegram_bot_token = ?, telegram_user_id = ?, 
            wechat_webhook_key = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = 1
    ''', (
        data.get('enabled', True),
        data.get('telegram_bot_token', ''),
        data.get('telegram_user_id', ''),
        data.get('wechat_webhook_key', '')
    ))
    
    return jsonify({'message': 'Notification settings updated'})

@app.route('/api/checkin/manual/<int:account_id>', methods=['POST'])
@token_required
def manual_checkin(account_id):
    scheduler.perform_checkin(account_id)
    return jsonify({'message': 'Manual check-in triggered'})

# HTML Template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LeafLow Auto Check-in Control Panel</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
        .login-container { display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .login-box { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 10px 40px rgba(0,0,0,0.1); width: 400px; }
        .login-box h2 { margin-bottom: 30px; color: #333; text-align: center; }
        .form-group { margin-bottom: 20px; }
        .form-group label { display: block; margin-bottom: 5px; color: #666; }
        .form-group input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; font-size: 14px; }
        .btn { width: 100%; padding: 12px; background: #667eea; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; transition: background 0.3s; }
        .btn:hover { background: #5a67d8; }
        .dashboard { display: none; padding: 20px; background: #f5f5f5; min-height: 100vh; }
        .header { background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .stat-card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
        .stat-card h3 { color: #666; font-size: 14px; margin-bottom: 10px; }
        .stat-card .value { font-size: 32px; font-weight: bold; color: #333; }
        .section { background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
        .section h2 { margin-bottom: 20px; color: #333; }
        .table { width: 100%; border-collapse: collapse; }
        .table th, .table td { padding: 12px; text-align: left; border-bottom: 1px solid #eee; }
        .table th { background: #f8f9fa; font-weight: 600; }
        .badge { padding: 4px 8px; border-radius: 4px; font-size: 12px; }
        .badge-success { background: #d4edda; color: #155724; }
        .badge-danger { background: #f8d7da; color: #721c24; }
        .badge-warning { background: #fff3cd; color: #856404; }
        .btn-sm { padding: 6px 12px; font-size: 14px; }
        .btn-danger { background: #dc3545; }
        .btn-danger:hover { background: #c82333; }
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); justify-content: center; align-items: center; }
        .modal-content { background: white; padding: 30px; border-radius: 10px; width: 500px; max-width: 90%; }
        .modal-header { margin-bottom: 20px; }
        .modal-header h3 { color: #333; }
        .close { float: right; font-size: 24px; cursor: pointer; color: #999; }
        .close:hover { color: #333; }
        .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
        .switch { position: relative; display: inline-block; width: 50px; height: 24px; }
        .switch input { opacity: 0; width: 0; height: 0; }
        .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #ccc; transition: .4s; border-radius: 24px; }
        .slider:before { position: absolute; content: ""; height: 18px; width: 18px; left: 3px; bottom: 3px; background-color: white; transition: .4s; border-radius: 50%; }
        input:checked + .slider { background-color: #667eea; }
        input:checked + .slider:before { transform: translateX(26px); }
    </style>
</head>
<body>
    <div class="login-container" id="loginContainer">
        <div class="login-box">
            <h2>🔐 Admin Login</h2>
            <form id="loginForm">
                <div class="form-group">
                    <label>Username</label>
                    <input type="text" id="username" required>
                </div>
                <div class="form-group">
                    <label>Password</label>
                    <input type="password" id="password" required>
                </div>
                <button type="submit" class="btn">Login</button>
            </form>
        </div>
    </div>

    <div class="dashboard" id="dashboard">
        <div class="header">
            <h1>📊 LeafLow Check-in Dashboard</h1>
            <button class="btn btn-danger btn-sm" onclick="logout()">Logout</button>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <h3>Total Accounts</h3>
                <div class="value" id="totalAccounts">0</div>
            </div>
            <div class="stat-card">
                <h3>Active Accounts</h3>
                <div class="value" id="activeAccounts">0</div>
            </div>
            <div class="stat-card">
                <h3>Total Check-ins</h3>
                <div class="value" id="totalCheckins">0</div>
            </div>
            <div class="stat-card">
                <h3>Success Rate</h3>
                <div class="value" id="successRate">0%</div>
            </div>
        </div>

        <div class="section">
            <h2>📅 Today's Check-ins</h2>
            <table class="table">
                <thead>
                    <tr>
                        <th>Account</th>
                        <th>Status</th>
                        <th>Message</th>
                        <th>Time</th>
                    </tr>
                </thead>
                <tbody id="todayCheckins"></tbody>
            </table>
        </div>

        <div class="section">
            <h2>👥 Account Management</h2>
            <button class="btn btn-sm" onclick="showAddAccountModal()" style="margin-bottom: 15px;">+ Add Account</button>
            <table class="table">
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Status</th>
                        <th>Check-in Time</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="accountsList"></tbody>
            </table>
        </div>

        <div class="section">
            <h2>🔔 Notification Settings</h2>
            <div class="form-group">
                <label>
                    <input type="checkbox" id="notifyEnabled"> Enable Notifications
                </label>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Telegram Bot Token</label>
                    <input type="text" id="tgBotToken" placeholder="Bot token">
                </div>
                <div class="form-group">
                    <label>Telegram User ID</label>
                    <input type="text" id="tgUserId" placeholder="User ID">
                </div>
            </div>
            <div class="form-group">
                <label>WeChat Webhook Key</label>
                <input type="text" id="wechatKey" placeholder="Webhook key">
            </div>
            <button class="btn btn-sm" onclick="saveNotificationSettings()">Save Settings</button>
        </div>
    </div>

    <!-- Add Account Modal -->
    <div class="modal" id="addAccountModal">
        <div class="modal-content">
            <div class="modal-header">
                <span class="close" onclick="closeModal()">&times;</span>
                <h3>Add New Account</h3>
            </div>
            <form id="addAccountForm">
                <div class="form-group">
                    <label>Account Name</label>
                    <input type="text" id="accountName" required>
                </div>
                <div class="form-group">
                    <label>Check-in Time</label>
                    <input type="time" id="checkinTime" value="01:00" required>
                </div>
                <div class="form-group">
                    <label>Token Data (JSON)</label>
                    <textarea id="tokenData" rows="6" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px;" placeholder='{"cookies": {"session": "..."}}' required></textarea>
                </div>
                <button type="submit" class="btn">Add Account</button>
            </form>
        </div>
    </div>

    <script>
        let authToken = localStorage.getItem('authToken');

        // Check authentication
        if (authToken) {
            showDashboard();
        }

        // Login form
        document.getElementById('loginForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;

            try {
                const response = await fetch('/api/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password })
                });

                const data = await response.json();
                if (response.ok) {
                    authToken = data.token;
                    localStorage.setItem('authToken', authToken);
                    showDashboard();
                } else {
                    alert('Login failed: ' + data.message);
                }
            } catch (error) {
                alert('Login error: ' + error.message);
            }
        });

        function showDashboard() {
            document.getElementById('loginContainer').style.display = 'none';
            document.getElementById('dashboard').style.display = 'block';
            loadDashboard();
            loadAccounts();
            loadNotificationSettings();
            // Refresh every 30 seconds
            setInterval(loadDashboard, 30000);
        }

        function logout() {
            localStorage.removeItem('authToken');
            location.reload();
        }

        async function apiCall(url, options = {}) {
            const response = await fetch(url, {
                ...options,
                headers: {
                    'Authorization': 'Bearer ' + authToken,
                    'Content-Type': 'application/json',
                    ...options.headers
                }
            });

            if (response.status === 401) {
                logout();
                return;
            }

            return response.json();
        }

        async function loadDashboard() {
            const data = await apiCall('/api/dashboard');
            if (!data) return;

            document.getElementById('totalAccounts').textContent = data.total_accounts;
            document.getElementById('activeAccounts').textContent = data.enabled_accounts;
            document.getElementById('totalCheckins').textContent = data.total_checkins;
            document.getElementById('successRate').textContent = data.success_rate + '%';

            // Today's check-ins
            const tbody = document.getElementById('todayCheckins');
            tbody.innerHTML = '';
            data.today_checkins.forEach(checkin => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${checkin.name}</td>
                    <td><span class="badge ${checkin.success ? 'badge-success' : 'badge-danger'}">${checkin.success ? 'Success' : 'Failed'}</span></td>
                    <td>${checkin.message}</td>
                    <td>${new Date(checkin.created_at).toLocaleTimeString()}</td>
                `;
                tbody.appendChild(tr);
            });
        }

        async function loadAccounts() {
            const accounts = await apiCall('/api/accounts');
            if (!accounts) return;

            const tbody = document.getElementById('accountsList');
            tbody.innerHTML = '';
            accounts.forEach(account => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${account.name}</td>
                    <td>
                        <label class="switch">
                            <input type="checkbox" ${account.enabled ? 'checked' : ''} onchange="toggleAccount(${account.id}, this.checked)">
                            <span class="slider"></span>
                        </label>
                    </td>
                    <td>
                        <input type="time" value="${account.checkin_time}" onchange="updateCheckinTime(${account.id}, this.value)" style="border: 1px solid #ddd; padding: 4px; border-radius: 4px;">
                    </td>
                    <td>
                        <button class="btn btn-sm" onclick="manualCheckin(${account.id})">Check-in Now</button>
                        <button class="btn btn-danger btn-sm" onclick="deleteAccount(${account.id})">Delete</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        }

        async function loadNotificationSettings() {
            const settings = await apiCall('/api/notification');
            if (!settings) return;

            document.getElementById('notifyEnabled').checked = settings.enabled;
            document.getElementById('tgBotToken').value = settings.telegram_bot_token || '';
            document.getElementById('tgUserId').value = settings.telegram_user_id || '';
            document.getElementById('wechatKey').value = settings.wechat_webhook_key || '';
        }

        async function toggleAccount(id, enabled) {
            await apiCall(`/api/accounts/${id}`, {
                method: 'PUT',
                body: JSON.stringify({ enabled })
            });
            loadAccounts();
        }

        async function updateCheckinTime(id, checkin_time) {
            await apiCall(`/api/accounts/${id}`, {
                method: 'PUT',
                body: JSON.stringify({ checkin_time })
            });
        }

        async function manualCheckin(id) {
            if (confirm('Perform manual check-in for this account?')) {
                const result = await apiCall(`/api/checkin/manual/${id}`, { method: 'POST' });
                alert(result.message);
                setTimeout(loadDashboard, 2000);
            }
        }

        async function deleteAccount(id) {
            if (confirm('Delete this account?')) {
                await apiCall(`/api/accounts/${id}`, { method: 'DELETE' });
                loadAccounts();
            }
        }

        async function saveNotificationSettings() {
            const settings = {
                enabled: document.getElementById('notifyEnabled').checked,
                telegram_bot_token: document.getElementById('tgBotToken').value,
                telegram_user_id: document.getElementById('tgUserId').value,
                wechat_webhook_key: document.getElementById('wechatKey').value
            };

            const result = await apiCall('/api/notification', {
                method: 'PUT',
                body: JSON.stringify(settings)
            });
            alert(result.message);
        }

        function showAddAccountModal() {
            document.getElementById('addAccountModal').style.display = 'flex';
        }

        function closeModal() {
            document.getElementById('addAccountModal').style.display = 'none';
        }

        document.getElementById('addAccountForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            try {
                const tokenData = JSON.parse(document.getElementById('tokenData').value);
                const account = {
                    name: document.getElementById('accountName').value,
                    checkin_time: document.getElementById('checkinTime').value,
                    token_data: tokenData
                };

                const result = await apiCall('/api/accounts', {
                    method: 'POST',
                    body: JSON.stringify(account)
                });
                
                alert(result.message);
                closeModal();
                loadAccounts();
                document.getElementById('addAccountForm').reset();
            } catch (error) {
                alert('Invalid JSON format: ' + error.message);
            }
        });

        // Close modal when clicking outside
        window.onclick = function(event) {
            const modal = document.getElementById('addAccountModal');
            if (event.target == modal) {
                closeModal();
            }
        }
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    # Start scheduler
    scheduler.start()
    scheduler.schedule_checkins()
    
    # Start Flask app
    logger.info(f"Starting control panel on port {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False)
