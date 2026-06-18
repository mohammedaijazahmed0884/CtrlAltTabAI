import json
import urllib.request
import math
from database import get_db, get_setting

def cosine_similarity(v1, v2):
    dot = sum(a * b for a, b in zip(v1, v2))
    mag1 = math.sqrt(sum(a * a for a in v1))
    mag2 = math.sqrt(sum(b * b for b in v2))
    if mag1 == 0 or mag2 == 0: return 0
    return dot / (mag1 * mag2)

class LLMService:
    def __init__(self, use_mock=True):
        self.use_mock = use_mock

    def _call_llm(self, system_prompt, user_prompt, expect_json=False):
        provider = get_setting('llm_provider', 'openai')
        api_key = get_setting('openai_api_key', '')
        if not api_key:
            return '{"draftText": "Mock response (No API key)", "confidence": 0, "reasoning": "Mock reasoning", "is_escalated": 0}' if expect_json else "Mock response"
        
        try:
            if provider == 'gemini':
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                payload = {"contents": [{"parts": [{"text": f"{system_prompt}\n\n{user_prompt}"}]}]}
                if expect_json:
                    payload["generationConfig"] = {"response_mime_type": "application/json"}
                
                req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
                with urllib.request.urlopen(req) as response:
                    res_data = json.loads(response.read().decode())
                    return res_data['candidates'][0]['content']['parts'][0]['text']
            else:
                import openai
                client_kwargs = {"api_key": api_key}
                model_name = "gpt-4o"
                if provider == 'groq':
                    client_kwargs["base_url"] = "https://api.groq.com/openai/v1"
                    model_name = "llama-3.1-8b-instant"
                    
                client = openai.OpenAI(**client_kwargs)
                kwargs = {
                    "model": model_name,
                    "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                    "max_tokens": 800
                }
                if expect_json:
                    kwargs["response_format"] = {"type": "json_object"}
                    
                response = client.chat.completions.create(**kwargs)
                return response.choices[0].message.content
        except Exception as e:
            print(f"LLM Error: {e}")
            if expect_json:
                return json.dumps({"draftText": f"Error: {str(e)}", "confidence": 0, "reasoning": "Failed to connect to API.", "is_escalated": 1})
            return f"Error: {str(e)}"

    def get_embedding(self, text):
        api_key = get_setting('openai_api_key', '')
        if not api_key: return [0.0]*768
        
        # We enforce using Gemini for embeddings as Groq doesn't support them yet
        url = f"https://generativelanguage.googleapis.com/v1beta/models/embedding-001:embedContent?key={api_key}"
        payload = {
            "model": "models/embedding-001",
            "content": {"parts": [{"text": text}]}
        }
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode())
                return res_data['embedding']['values']
        except Exception as e:
            print(f"Embedding error: {e}")
            return [0.0]*768

    def fetch_learned_context(self):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT original_source, approved_action FROM business_context ORDER BY id DESC LIMIT 5")
        history = cursor.fetchall()
        conn.close()

        if not history:
            return "No learned rules yet."

        context_string = ""
        for idx, row in enumerate(history):
            context_string += f"Scenario {idx+1}:\n- Input: {row['original_source']}\n- Approved Action: {row['approved_action']}\n\n"
        return context_string

    def perform_rag_search(self, query):
        query_vec = self.get_embedding(query)
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT title, content, embedding FROM documents")
        docs = cursor.fetchall()
        conn.close()
        
        if not docs:
            # Fallback to legacy static KB
            return get_setting('knowledge_base', 'No knowledge base provided.')
            
        scored_docs = []
        for doc in docs:
            try:
                doc_vec = json.loads(doc['embedding'])
                score = cosine_similarity(query_vec, doc_vec)
                scored_docs.append((score, f"Document: {doc['title']}\nContent: {doc['content']}"))
            except:
                pass
                
        scored_docs.sort(reverse=True, key=lambda x: x[0])
        top_docs = [doc[1] for doc in scored_docs[:3]]
        return "\n\n".join(top_docs)

    def generate_draft(self, incoming_text, item_type):
        business_type = get_setting('brand_name', 'General')
        
        # AGENT 0: Sentiment & Routing Agent
        sentiment_sys = "You are the Sentiment Agent. Classify the user's emotion as POSITIVE, NEUTRAL, or ANGRY. Output just the single word."
        sentiment = self._call_llm(sentiment_sys, incoming_text).strip().upper()
        
        is_angry = 1 if "ANGRY" in sentiment or "URGENT" in incoming_text.upper() else 0
        
        # AGENT 1: Researcher
        research_sys = f"You are the Researcher Agent for {business_type}. Analyze the incoming request, identify the core issues, and summarize what information is needed to resolve it."
        research_summary = self._call_llm(research_sys, incoming_text)
        
        rag_context = self.perform_rag_search(research_summary)
        learned_context = self.fetch_learned_context()
        
        # AGENT 2: Drafter (Omni-channel Aware)
        tone_instruction = "Use clear paragraph breaks. Include a greeting and sign-off."
        if item_type == 'whatsapp':
            tone_instruction = "Keep it very short, friendly, and use emojis. No formal sign-off needed. Max 2 sentences."
        elif item_type == 'slack':
            tone_instruction = "Keep it professional but casual. Use bullet points if needed. Max 3 sentences."
            
        drafter_sys = f"""You are the Drafter Agent for {business_type}. 
        Your job is to draft a highly professional response based on the research.
        CHANNEL SPECIFIC INSTRUCTIONS: {tone_instruction}
        Use placeholders like [Name] or [Date] if specific data is missing.
        """
        import re
        crm_context = "No CRM match found."
        if "ceo@" in incoming_text.lower() or "vip" in incoming_text.lower():
            crm_context = "CRM DATA MATCH: VIP Client Detected. Lifetime Value: $150,000. Priority: High."
            
        drafter_prompt = f"CRM CONTEXT:\n{crm_context}\n\nRESEARCH SUMMARY:\n{research_summary}\n\nKNOWLEDGE BASE CONTEXT:\n{rag_context}\n\nLEARNED CONTEXT:\n{learned_context}\n\nINCOMING INQUIRY:\n{incoming_text}\n\nDraft the response now."
        draft_text = self._call_llm(drafter_sys, drafter_prompt)
        
        # AGENT 3: Reviewer
        reviewer_sys = """You are the Compliance and Reviewer Agent. 
        You must evaluate the Drafter's response.
        Return ONLY valid JSON with:
        - "draftText": The final polished response. You can fix any errors.
        - "confidence": Integer 0-100 based on how perfectly it adheres to rules and resolves the issue.
        - "reasoning": 1 sentence explaining the score.
        - "is_escalated": 1 if the ORIGINAL INQUIRY contains ANY anger, frustration, threats, or if confidence is below 50. Otherwise 0. YOU MUST RETURN 1 if the customer expresses frustration.
        """
        reviewer_prompt = f"ORIGINAL INQUIRY:\n{incoming_text}\n\nDRAFT TO REVIEW:\n{draft_text}\n\nPlease output the JSON analysis."
        final_json_str = self._call_llm(reviewer_sys, reviewer_prompt, expect_json=True)
        
        try:
            parsed = json.loads(final_json_str)
            if 'is_escalated' not in parsed:
                parsed['is_escalated'] = 0
            if is_angry:
                parsed['is_escalated'] = 1
                parsed['reasoning'] = f"ESCALATED DUE TO HIGH ANGER/URGENCY: {parsed['reasoning']}"
            return parsed
        except Exception as e:
            return {"draftText": draft_text, "confidence": 50, "reasoning": "JSON parse error in reviewer.", "is_escalated": 0}

llm = LLMService(use_mock=True)
