import imaplib
import email
import smtplib
from email.message import EmailMessage
from email.header import decode_header
import time
import threading
import uuid

def decode_subject(header_value):
    if not header_value:
        return "(No Subject)"
    decoded_parts = decode_header(header_value)
    subject = ""
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            subject += part.decode(encoding or "utf-8", errors="ignore")
        else:
            subject += part
    return subject

def extract_body(msg):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                try:
                    body = part.get_payload(decode=True).decode()
                    break
                except:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode()
        except:
            pass
    return body[:1000] # Limit size for LLM

def poll_gmail_loop():
    from database import get_setting, get_db
    from llm_service import llm
    from email.utils import parsedate_to_datetime
    
    while True:
        try:
            addr = get_setting('gmail_address')
            pwd = get_setting('gmail_app_password')
            
            if addr and pwd:
                # Connect to IMAP
                mail = imaplib.IMAP4_SSL("imap.gmail.com")
                mail.login(addr, pwd)
                mail.select("inbox")
                
                # Search for unread SINCE today
                date_str = time.strftime("%d-%b-%Y")
                status, messages = mail.search(None, f'(UNSEEN SINCE "{date_str}")')
                
                if status == "OK" and messages[0]:
                    msg_ids = messages[0].split()
                    for msg_id in msg_ids:
                        res, msg_data = mail.fetch(msg_id, "(RFC822)")
                        for response_part in msg_data:
                            if isinstance(response_part, tuple):
                                msg = email.message_from_bytes(response_part[1])
                                subject = decode_subject(msg["Subject"])
                                sender = msg.get("From")
                                body = extract_body(msg)
                                
                                # Extract exact date
                                date_header = msg.get("Date")
                                try:
                                    from datetime import timezone, timedelta
                                    dt = parsedate_to_datetime(date_header)
                                    # Convert to Indian Standard Time (IST: UTC +5:30)
                                    ist_tz = timezone(timedelta(hours=5, minutes=30))
                                    dt_ist = dt.astimezone(ist_tz)
                                    timestamp_str = dt_ist.strftime("%d %b %Y, %I:%M %p")
                                except:
                                    timestamp_str = "Just now"
                                
                                source_text = f"From: {sender}\nSubject: {subject}\n\n{body}"
                                llm_result = llm.generate_draft(source_text, "gmail_real")
                                draft_text = llm_result.get('draftText', 'Failed to generate draft.')
                                confidence = llm_result.get('confidence', 0)
                                reasoning = llm_result.get('reasoning', '')
                                is_escalated = llm_result.get('is_escalated', 0)
                                
                                conn = get_db()
                                cursor = conn.cursor()
                                new_id = f"item_gmail_{uuid.uuid4().hex[:8]}"
                                
                                threshold_str = get_setting('autonomy_threshold', '100')
                                try:
                                    threshold = int(threshold_str)
                                except:
                                    threshold = 100
                                    
                                if confidence >= threshold and not is_escalated:
                                    # Auto-send the email
                                    try:
                                        send_gmail_reply(sender, "Re: " + subject, draft_text)
                                    except Exception as e:
                                        print(f"Autonomous send failed: {e}")
                                    # Log to context
                                    cursor.execute('''
                                        INSERT INTO business_context (item_id, original_source, approved_action, confidence, reasoning)
                                        VALUES (?, ?, ?, ?, ?)
                                    ''', (new_id, source_text, draft_text, confidence, reasoning))
                                else:
                                    cursor.execute('''
                                        INSERT INTO pending_items (id, type, iconClass, icon, timestamp, title, sourceText, draftText, status, confidence, reasoning, is_escalated)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    ''', (new_id, 'gmail_real', 'icon-support', '📧', timestamp_str, f"Real Email: {subject[:30]}...", source_text, draft_text, 'pending', confidence, reasoning, is_escalated))
                                    
                                conn.commit()
                                conn.close()
                                
                mail.logout()
        except Exception as e:
            print(f"Gmail Polling Error: {e}")
        
        time.sleep(15)

def start_gmail_listener():
    t = threading.Thread(target=poll_gmail_loop, daemon=True)
    t.start()

def send_gmail_reply(to_address, subject, body):
    from database import get_setting
    addr = get_setting('gmail_address')
    pwd = get_setting('gmail_app_password')
    
    if not addr or not pwd:
        print("Cannot send: missing credentials.")
        return
    
    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = f"Re: {subject}"
    msg['From'] = addr
    msg['To'] = to_address
    
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(addr, pwd)
        server.send_message(msg)
        server.quit()
        print(f"Successfully sent reply to {to_address}")
    except Exception as e:
        print(f"Failed to send email: {e}")
