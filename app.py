from flask import Flask, send_from_directory, jsonify, request
import os
from database import get_db, init_db
from agent import generate_random_incoming, generate_weekly_report

app = Flask(__name__, static_folder='.', static_url_path='')

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/pending', methods=['GET'])
def get_pending():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM pending_items ORDER BY rowid DESC')
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(items)

@app.route('/api/approve/<item_id>', methods=['POST'])
def approve_item(item_id):
    data = request.json
    final_draft = data.get('draftText', '')
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Get original item
    cursor.execute('SELECT type, sourceText, confidence, reasoning FROM pending_items WHERE id = ?', (item_id,))
    row = cursor.fetchone()
    if row:
        # If it's a real email, send it
        if row['type'] == 'gmail_real':
            from gmail_service import send_gmail_reply
            import re
            
            # Try to extract the sender's email and subject from sourceText
            sender_match = re.search(r"From: .*?<(.+?)>|From: (.+?)\n", row['sourceText'])
            subject_match = re.search(r"Subject: (.+?)\n", row['sourceText'])
            
            to_addr = sender_match.group(1) or sender_match.group(2) if sender_match else ""
            subj = subject_match.group(1) if subject_match else "Reply"
            
            if to_addr:
                send_gmail_reply(to_addr, subj, final_draft)

        # Save to business context (The Brain learns)
        cursor.execute('''
            INSERT INTO business_context (item_id, original_source, approved_action, confidence, reasoning)
            VALUES (?, ?, ?, ?, ?)
        ''', (item_id, row['sourceText'], final_draft, row['confidence'], row['reasoning']))
        
        # Remove from pending
        cursor.execute('DELETE FROM pending_items WHERE id = ?', (item_id,))
        conn.commit()
    
    conn.close()
    return jsonify({'success': True})

@app.route('/api/reject/<item_id>', methods=['POST'])
def reject_item(item_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM pending_items WHERE id = ?', (item_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/clear_pending', methods=['POST'])
def clear_pending():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM pending_items')
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/simulate', methods=['POST'])
def simulate():
    generate_random_incoming()
    return jsonify({'success': True})

@app.route('/api/webhook/universal', methods=['POST'])
def universal_webhook():
    import uuid, time
    from database import get_setting
    from llm_service import llm
    
    data = request.json
    source = data.get('source', 'webhook')
    title = data.get('title', 'New Webhook Event')
    text = data.get('text', str(data))
    
    new_id = f"item_webhook_{uuid.uuid4().hex[:8]}"
    
    llm_result = llm.generate_draft(text, source)
    draft_text = llm_result.get('draftText', 'Failed to generate draft.')
    confidence = llm_result.get('confidence', 0)
    reasoning = llm_result.get('reasoning', '')
    is_escalated = llm_result.get('is_escalated', 0)
    
    conn = get_db()
    cursor = conn.cursor()
    
    threshold_str = get_setting('autonomy_threshold', '100')
    try:
        threshold = int(threshold_str)
    except:
        threshold = 100
        
    if confidence >= threshold and not is_escalated:
        # Auto-Approve
        cursor.execute('''
            INSERT INTO business_context (item_id, original_source, approved_action, confidence, reasoning)
            VALUES (?, ?, ?, ?, ?)
        ''', (new_id, text, draft_text, confidence, reasoning))
    else:
        cursor.execute('''
            INSERT INTO pending_items (id, type, iconClass, icon, timestamp, title, sourceText, draftText, status, confidence, reasoning, is_escalated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (new_id, source, 'icon-support', '⚡', 'Just now', title, text, draft_text, 'pending', confidence, reasoning, is_escalated))
        
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'id': new_id, 'auto_approved': confidence >= threshold})

@app.route('/api/simulate-report', methods=['POST'])
def simulate_report():
    generate_weekly_report()
    return jsonify({'success': True})

@app.route('/api/context', methods=['GET'])
def get_context():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM business_context ORDER BY id DESC')
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(items)

@app.route('/api/crm/lookup', methods=['GET'])
def crm_lookup():
    email = request.args.get('email', '')
    if "vip" in email.lower() or "ceo" in email.lower():
        return jsonify({"is_vip": True, "lifetime_value": "$150,000", "company": "Acme Corp"})
    return jsonify({"is_vip": False, "lifetime_value": "$0", "company": "Unknown"})

@app.route('/api/stats/roi', methods=['GET'])
def get_roi_stats():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as total FROM business_context')
    row = cursor.fetchone()
    total_resolutions = row['total'] if row else 0
    conn.close()
    
    # Let's say each resolution saves 5 minutes, at $30/hour
    hours_saved = total_resolutions * (5 / 60)
    dollars_saved = hours_saved * 30
    
    return jsonify({
        "total_resolutions": total_resolutions,
        "hours_saved": round(hours_saved, 1),
        "dollars_saved": round(dollars_saved, 2)
    })

@app.route('/api/documents', methods=['GET'])
def get_documents():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, title, content FROM documents')
    docs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(docs)

@app.route('/api/documents', methods=['POST'])
def add_document():
    from llm_service import llm
    import json
    data = request.json
    title = data.get('title', 'Untitled')
    content = data.get('content', '')
    
    if not content:
        return jsonify({'success': False, 'error': 'Content is required'}), 400
        
    embedding = llm.get_embedding(content)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO documents (title, content, embedding) VALUES (?, ?, ?)', (title, content, json.dumps(embedding)))
    conn.commit()
    doc_id = cursor.lastrowid
    conn.close()
    
    return jsonify({'success': True, 'id': doc_id})

@app.route('/api/documents/<int:doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM documents WHERE id = ?', (doc_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/documents/upload', methods=['POST'])
def upload_document():
    from llm_service import llm
    import json
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No selected file'}), 400
        
    content = ""
    title = file.filename
    try:
        if title.lower().endswith('.pdf'):
            import PyPDF2
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    content += text + "\n"
        else:
            content = file.read().decode('utf-8', errors='ignore')
            
        if not content.strip():
            return jsonify({'success': False, 'error': 'File is empty or text could not be extracted.'}), 400
            
        embedding = llm.get_embedding(content)
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO documents (title, content, embedding) VALUES (?, ?, ?)', (title, content, json.dumps(embedding)))
        conn.commit()
        doc_id = cursor.lastrowid
        conn.close()
        
        return jsonify({'success': True, 'id': doc_id, 'title': title})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/settings', methods=['GET'])
def fetch_settings():
    from database import get_setting
    key = get_setting('openai_api_key', '')
    masked = f"sk-...{key[-4:]}" if key and len(key) > 8 else ""
    
    return jsonify({
        'openai_api_key': masked,
        'has_key': bool(key),
        'wizard_completed': get_setting('wizard_completed', 'false') == 'true',
        'autopilot_gmail': get_setting('autopilot_gmail', 'false') == 'true',
        'autopilot_docusign': get_setting('autopilot_docusign', 'false') == 'true',
        'autopilot_linkedin': get_setting('autopilot_linkedin', 'false') == 'true',
        'autopilot_stripe': get_setting('autopilot_stripe', 'false') == 'true',
        'autopilot_salesforce': get_setting('autopilot_salesforce', 'false') == 'true',
        'autopilot_zendesk': get_setting('autopilot_zendesk', 'false') == 'true',
        'brand_name': get_setting('brand_name', ''),
        'brand_icon': get_setting('brand_icon', ''),
        'gmail_address': get_setting('gmail_address', ''),
        'has_gmail': bool(get_setting('gmail_app_password', ''))
    })

@app.route('/api/settings', methods=['POST'])
def save_settings():
    from database import set_setting
    data = request.json
    for k, v in data.items():
        if k == 'openai_api_key' and not v:
            continue
        set_setting(k, str(v).lower() if isinstance(v, bool) else str(v))
    return jsonify({'success': True})

@app.route('/api/wizard', methods=['POST'])
def finish_wizard():
    from database import set_setting
    data = request.json
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO business_context (item_id, original_source, approved_action)
        VALUES (?, ?, ?)
    ''', ('setup_q1', 'What is the primary service or product your business offers?', data.get('q1', '')))
    cursor.execute('''
        INSERT INTO business_context (item_id, original_source, approved_action)
        VALUES (?, ?, ?)
    ''', ('setup_q2', 'What tone of voice should the AI use with clients?', data.get('q2', '')))
    cursor.execute('''
        INSERT INTO business_context (item_id, original_source, approved_action)
        VALUES (?, ?, ?)
    ''', ('setup_q3', 'If the AI encounters a completely unknown scenario, what is the fallback?', data.get('q3', '')))
    conn.commit()
    conn.close()
    
    set_setting('wizard_completed', 'true')
    return jsonify({'success': True})

@app.route('/api/webhook', methods=['POST'])
def incoming_webhook():
    import time
    from llm_service import llm
    
    data = request.json
    item_type = data.get('type', 'webhook')
    source_text = data.get('text', 'No content provided.')
    title = data.get('title', 'Incoming Webhook Event')
    icon = data.get('icon', '⚡')
    icon_class = data.get('iconClass', 'icon-invoice')
    
    # Send to LLM
    llm_result = llm.generate_draft(source_text, item_type)
    draft_text = llm_result.get('draftText', 'Failed to generate draft.')
    confidence = llm_result.get('confidence', 0)
    reasoning = llm_result.get('reasoning', '')
    is_escalated = llm_result.get('is_escalated', 0)
    
    new_id = f"item_webhook_{int(time.time() * 1000)}"
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO pending_items (id, type, iconClass, icon, timestamp, title, sourceText, draftText, status, confidence, reasoning, is_escalated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (new_id, item_type, icon_class, icon, 'Just now', title, source_text, draft_text, 'pending', confidence, reasoning, is_escalated))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'id': new_id})

if __name__ == '__main__':
    # Initialize DB if not exists
    if not os.path.exists('brain.db'):
        init_db()
        
    try:
        from gmail_service import start_gmail_listener
        start_gmail_listener()
    except ImportError:
        pass
        
    try:
        from proactive_service import start_proactive_listener
        start_proactive_listener()
    except ImportError:
        pass
    
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting Managed AI Employee Backend on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=False)
