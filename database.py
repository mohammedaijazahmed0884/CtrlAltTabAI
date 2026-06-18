import sqlite3
import os

DB_PATH = 'brain.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Table for incoming tasks
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pending_items (
            id TEXT PRIMARY KEY,
            type TEXT,
            iconClass TEXT,
            icon TEXT,
            timestamp TEXT,
            title TEXT,
            sourceText TEXT,
            draftText TEXT,
            status TEXT
        )
    ''')
    
    # Table for the Brain's memory (Approved contexts)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS business_context (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id TEXT,
            original_source TEXT,
            approved_action TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Table for API Keys and Settings
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # Table for Advanced RAG Vector Embeddings
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            embedding TEXT
        )
    ''')

    # Table for mock proactive actions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id TEXT PRIMARY KEY,
            customer_name TEXT,
            customer_email TEXT,
            amount TEXT,
            due_date TEXT,
            status TEXT
        )
    ''')
    
    # Migrations for Phase 9
    try:
        cursor.execute('ALTER TABLE pending_items ADD COLUMN confidence INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute('ALTER TABLE pending_items ADD COLUMN reasoning TEXT')
    except sqlite3.OperationalError:
        pass
        
    try:
        cursor.execute('ALTER TABLE business_context ADD COLUMN confidence INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute('ALTER TABLE business_context ADD COLUMN reasoning TEXT')
    except sqlite3.OperationalError:
        pass
        
    # Migrations for Phase 11
    try:
        cursor.execute('ALTER TABLE pending_items ADD COLUMN is_escalated INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass

    conn.commit()
    
    # Check if empty, then seed
    cursor.execute('SELECT COUNT(*) FROM pending_items')
    if cursor.fetchone()[0] == 0:
        seed_data(conn)
        
    conn.close()

def get_setting(key, default=''):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row['value']
    return default

def set_setting(key, value):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO settings (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
    ''', (key, value))
    conn.commit()
    conn.close()

def seed_data(conn):
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM pending_items')
    
    # Seed mock invoices
    cursor.execute('SELECT COUNT(*) FROM invoices')
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO invoices (id, customer_name, customer_email, amount, due_date, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('INV-9942', 'Acme Corp', 'billing@acmecorp.mock', '$4,500', '2026-06-10', 'overdue'))
        conn.commit()
        
    conn.close()

def seed_data(conn):
    items = [
        ('item_1', 'lead', 'icon-lead', '👋', '10 mins ago', 'New Lead: Sarah Jenkins', 
         'Message via Website Form:\n"Hi, I am interested in your services for my business. Can we jump on a quick call this week? We have a budget of around $5k/mo."',
         'Hi Sarah,\n\nThanks for reaching out! We would love to chat about how we can help your business.\n\nAre you available for a quick 15-minute discovery call this Thursday or Friday? Let me know what time works best for you, or feel free to book directly on my calendar here: [Link].\n\nLooking forward to speaking soon,\n[Your Name]',
         'pending'),
        ('item_2', 'support', 'icon-support', '⚠️', '1 hour ago', 'Customer Complaint: Order #9021',
         'Email from John Doe:\n"I still haven\'t received my deliverable from last week. This is holding up my entire team. Please advise immediately."',
         'Hi John,\n\nI am so sorry for the delay regarding order #9021. I have checked with our team, and there was a minor hold-up in QA. \n\nI have personally expedited this, and you will have the deliverable in your inbox by 3 PM EST today.\n\nThank you for your patience, and apologies again for the inconvenience.\n\nBest,\n[Your Name]',
         'pending'),
        ('item_3', 'invoice', 'icon-invoice', '📄', '2 hours ago', 'Vendor Invoice: Cloud Hosting',
         'Email from AWS Billing:\n"Your monthly invoice for May is attached. Total due: $245.50. Payment will be automatically deducted on the 15th."',
         'Action Logged to Brain:\n- Invoice amount: $245.50\n- Vendor: AWS\n- Category: Software Expense\n- Due Date: 15th\n\nProposed Action: Approve and log to Quickbooks automatically.',
         'pending')
    ]
    cursor = conn.cursor()
    cursor.executemany('''
        INSERT INTO pending_items (id, type, iconClass, icon, timestamp, title, sourceText, draftText, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', items)
    conn.commit()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully.")
