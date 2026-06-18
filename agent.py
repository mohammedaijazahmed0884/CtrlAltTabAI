from database import get_db
from llm_service import llm
import time
import random

def generate_random_incoming():
    from database import get_setting
    types = {
        'linkedin': { 'type': 'lead', 'iconClass': 'icon-lead', 'icon': '👋', 'title': 'New Lead: Alex M.', 'text': 'Message via LinkedIn:\n"Hey, saw your post about AI automation. Can you help my real estate agency?"', 'draft': 'Hi Alex,\n\nAbsolutely. Real estate agencies are actually one of our best use cases. We help automate lead follow-ups and CRM data entry.\n\nDo you have 10 minutes tomorrow to discuss your current bottleneck?' },
        'gmail': { 'type': 'support', 'iconClass': 'icon-support', 'icon': '⚠️', 'title': 'Refund Request', 'text': 'Email from Client:\n"I need to cancel my subscription for next month as we are shutting down our project."', 'draft': 'Hi there,\n\nI\'m sorry to hear your project is shutting down. I have processed your cancellation, and you will not be billed for next month.\n\nWe wish you the best, and please reach out if you ever need our services again.' },
        'docusign': { 'type': 'invoice', 'iconClass': 'icon-invoice', 'icon': '📄', 'title': 'Contract Signature', 'text': 'Notification from DocuSign:\n"Client X has signed the service agreement."', 'draft': 'Action Logged to Brain:\n- Contract Signed: Client X\n- Next Step: Trigger onboarding sequence.\n\nProposed Action: Draft Welcome Email to Client X and create Slack channel.' },
        'stripe': { 'type': 'payment', 'iconClass': 'icon-invoice', 'icon': '💳', 'title': 'Stripe Payment Failed', 'text': 'Webhook from Stripe:\n"Payment of $499 failed for Customer Y due to insufficient funds."', 'draft': 'Hi Customer Y,\n\nIt looks like your recent payment of $499 was declined by your bank. Could you please update your payment method so your services are not interrupted?\n\nHere is a secure link to update your card details: [Link]' },
        'salesforce': { 'type': 'crm', 'iconClass': 'icon-lead', 'icon': '☁️', 'title': 'Salesforce Deal Won', 'text': 'Webhook from Salesforce:\n"Opportunity \'Enterprise Package\' moved to Closed/Won for Acme Corp."', 'draft': 'Action Logged to Brain:\n- Deal Won: Acme Corp Enterprise Package\n\nProposed Action: Send automated congratulatory email to Sales rep and draft introductory kick-off agenda for Acme Corp.' },
        'zendesk': { 'type': 'ticket', 'iconClass': 'icon-support', 'icon': '💬', 'title': 'Zendesk Urgent Ticket', 'text': 'Webhook from Zendesk:\n"Server is down, we cannot access our dashboard. Priority: Urgent"', 'draft': 'Hi there,\n\nWe have received your urgent ticket regarding the dashboard outage. I have immediately escalated this to our Tier 3 engineering team.\n\nWe will update you within the next 15 minutes with our findings.' },
        'whatsapp': { 'type': 'whatsapp', 'iconClass': 'icon-whatsapp', 'icon': '💬', 'title': 'WhatsApp from VIP Client', 'text': 'Message from ceo@acmecorp.com via WhatsApp:\n"WHERE IS MY REPORT? I AM VERY ANGRY AND THIS IS URGENT!"', 'draft': 'I apologize for the delay. I am escalating this immediately to our manager to get your report right now.' },
        'slack': { 'type': 'slack', 'iconClass': 'icon-slack', 'icon': '#', 'title': 'Slack from Team', 'text': 'Message in #general via Slack:\n"Can someone send me the latest logo files?"', 'draft': 'Here are the latest logo files.' }
    }
    
    source_key = random.choice(list(types.keys()))
    
    # Force WhatsApp and Slack to be included to demonstrate omni-channel right away
    events_to_run = [types[source_key]]
    if source_key != 'whatsapp': events_to_run.append(types['whatsapp'])
    if source_key != 'slack': events_to_run.append(types['slack'])
    
    conn = get_db()
    cursor = conn.cursor()
    threshold_str = get_setting('autonomy_threshold', '100')
    try:
        threshold = int(threshold_str)
    except:
        threshold = 100
        
    for idx, event in enumerate(events_to_run):
        new_id = f"item_{int(time.time() * 1000)}_{idx}"
        
        llm_result = llm.generate_draft(event['text'], event['type'])
        draft_text = llm_result.get('draftText', event['draft'])
        confidence = llm_result.get('confidence', 0)
        reasoning = llm_result.get('reasoning', '')
        is_escalated = llm_result.get('is_escalated', 0)
        
        is_autopilot = confidence >= threshold and not is_escalated
        
        if is_autopilot:
            cursor.execute('''
                INSERT INTO business_context (item_id, original_source, approved_action, confidence, reasoning)
                VALUES (?, ?, ?, ?, ?)
            ''', (new_id, event['text'], draft_text, confidence, reasoning))
        else:
            cursor.execute('''
                INSERT INTO pending_items (id, type, iconClass, icon, timestamp, title, sourceText, draftText, status, confidence, reasoning, is_escalated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (new_id, event['type'], event['iconClass'], event['icon'], 'Just now', event['title'], event['text'], draft_text, 'pending', confidence, reasoning, is_escalated))
        
    conn.commit()
    conn.close()
    return "multiple_items"

def generate_weekly_report():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM business_context")
    actions_taken = cursor.fetchone()[0]
    conn.close()
    
    report_text = f"Weekly AI Summary:\n\n- Actions Approved by Human: {actions_taken}\n- Estimated Hours Saved: {actions_taken * 0.25} hours\n- New Rules Learned: {actions_taken}\n\nThe Brain has been successfully updated with your preferences from this week's approvals."
    
    new_id = f"item_report_{int(time.time() * 1000)}"
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO pending_items (id, type, iconClass, icon, timestamp, title, sourceText, draftText, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (new_id, 'report', 'icon-invoice', '📊', 'Just now', 'Weekly Operations Report', 'System generated trigger: End of Week.', report_text, 'pending'))
    conn.commit()
    conn.close()
    return new_id
