import time
import threading
import uuid
from database import get_db, get_setting
from llm_service import llm

def run_proactive_loop():
    print("Started Proactive AI Employee background thread...")
    while True:
        try:
            # Wake up every 60 seconds
            time.sleep(60)
            
            conn = get_db()
            cursor = conn.cursor()
            
            # Check for late invoices
            cursor.execute("SELECT * FROM invoices WHERE status = 'overdue'")
            overdue_invoices = cursor.fetchall()
            
            for invoice in overdue_invoices:
                # Check if we already created a pending item for this invoice
                # We use a special ID format to track it
                proactive_id = f"item_proactive_invoice_{invoice['id']}"
                cursor.execute("SELECT id FROM pending_items WHERE id = ?", (proactive_id,))
                if cursor.fetchone():
                    continue # Already drafted a follow-up
                    
                # Create the proactive draft
                source_text = f"Proactive Notification:\nInvoice {invoice['id']} for {invoice['customer_name']} ({invoice['customer_email']}) is OVERDUE. Amount: {invoice['amount']}. Due Date: {invoice['due_date']}."
                
                llm_result = llm.generate_draft(source_text, "proactive_followup")
                draft_text = llm_result.get('draftText', 'Failed to generate draft.')
                confidence = llm_result.get('confidence', 0)
                reasoning = llm_result.get('reasoning', '')
                is_escalated = llm_result.get('is_escalated', 0)
                
                cursor.execute('''
                    INSERT INTO pending_items (id, type, iconClass, icon, timestamp, title, sourceText, draftText, status, confidence, reasoning, is_escalated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (proactive_id, 'proactive', 'icon-invoice', '🤖', 'Just now', f"Proactive Action: Late Invoice {invoice['id']}", source_text, draft_text, 'pending', confidence, reasoning, is_escalated))
                conn.commit()
                print(f"Proactive Action Drafted for Invoice {invoice['id']}")
            
            conn.close()
            
        except Exception as e:
            print(f"Proactive Loop Error: {e}")

def start_proactive_listener():
    t = threading.Thread(target=run_proactive_loop, daemon=True)
    t.start()
