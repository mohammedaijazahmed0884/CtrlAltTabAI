# CtrlAltTab AI - CAT AI

CAT AI is an autonomous customer support agent and business operations platform built for modern enterprises. It actively monitors your incoming data streams (Email, WhatsApp, Slack, Zendesk, Salesforce) and autonomously resolves issues using LLMs and business context memory.

## Features
- **Omni-channel Parsing**: Ingests and formats data from Slack, WhatsApp, Zendesk, and more.
- **The Brain (Memory)**: Automatically learns your specific business logic when you approve or reject drafts.
- **Sentiment Routing**: Automatically detects angry or urgent messages and flags them for human escalation before sending an automated response.
- **ROI Dashboard**: Live metrics calculating exactly how much time and money the AI has saved your team.

## Getting Started

### Prerequisites
- Python 3.9+
- An OpenAI or Groq API Key

### Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/your-username/ctrl-alt-tab-ai.git
   cd ctrl-alt-tab-ai
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python app.py
   ```

4. Open your browser and navigate to:
   `http://localhost:5000`

### Initial Setup
When you first boot up the app, click the **Settings** tab.
1. Enter your OpenAI or Groq API Key.
2. Select your Model.
3. Configure your Autopilot Threshold.

## Technical Architecture
- **Backend:** Flask (Python)
- **Database:** SQLite3
- **Frontend:** HTML5, Vanilla JS, CSS (Glassmorphism UI)
- **LLM Integrations:** OpenAI, Groq, Gemini
