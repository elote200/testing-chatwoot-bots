#!/usr/bin/env python3
"""
Chatwoot Agent Bot — single file, Flask.
Recibe webhooks de Chatwoot, consulta un modelo AI y responde.

Modos (via AGENT_MODE en .env o variable de entorno):
  - direct   → responde inline (pruebas, default)
  - openai   → OpenAI, Groq, Google Gemini, etc. (API compatible)
  - ollama   → modelo local

Ejemplo con Groq:
  AGENT_MODE=openai \
  OPENAI_URL=https://api.groq.com/openai/v1 \
  OPENAI_API_KEY=gsk_... \
  OPENAI_MODEL=llama-3.3-70b-versatile \
  python3 test-bot.py
"""

import os

import requests
from dotenv import load_dotenv
from flask import Flask, request

load_dotenv()

# ── Config desde variables de entorno ──────────────────────────
CHATWOOT_URL = os.environ.get('CHATWOOT_URL', 'http://localhost:3000')
BOT_TOKEN = os.environ.get('CHATWOOT_BOT_TOKEN', 'x3ZqMmuo6RZbdJiWdXNjiFmF')
AGENT_MODE = os.environ.get('AGENT_MODE', 'direct')

# OpenAI-compatible (Groq, OpenAI, Google Gemini, etc.)
OPENAI_URL = os.environ.get('OPENAI_URL', 'https://api.openai.com/v1')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')

# Ollama
OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama3.2')

SYSTEM_PROMPT = (
    "You are a helpful support assistant. "
    "Answer concisely and naturally in the same language as the user."
)

app = Flask(__name__)


# ── Handlers por modo ──────────────────────────────────────────

def handle_direct(sender, message):
    return f"Recibi tu mensaje: \"{message}\". Bot conectado a Chatwoot."


def handle_openai(sender, message):
    if not OPENAI_API_KEY:
        return "Error: OPENAI_API_KEY no configurada."
    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}",
    }
    r = requests.post(
        f"{OPENAI_URL.rstrip('/')}/chat/completions",
        json=payload, headers=headers, timeout=60,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def handle_ollama(sender, message):
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": message,
        "stream": False,
    }
    r = requests.post(
        f"{OLLAMA_URL.rstrip('/')}/api/generate",
        json=payload, timeout=120,
    )
    r.raise_for_status()
    return r.json()["response"]


BACKENDS = {
    "direct": handle_direct,
    "openai": handle_openai,
    "ollama": handle_ollama,
}

reply_to_message = BACKENDS.get(AGENT_MODE, handle_direct)


# ── Rutas ──────────────────────────────────────────────────────

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    message_type = data.get('message_type')
    content = data.get('content', '')
    conversation_id = data.get('conversation', {}).get('id')
    sender_id = data.get('sender', {}).get('id')
    account_id = data.get('account', {}).get('id')

    print(f"[{message_type}] Conv {conversation_id}: {content[:80]}")

    if message_type == 'incoming' and account_id and conversation_id:
        try:
            bot_reply = reply_to_message(sender_id, content)
            send_to_chatwoot(account_id, conversation_id, bot_reply)
        except Exception as e:
            print(f"[ERROR] {e}")

    return {"status": "ok"}, 200


@app.route('/health')
def health():
    return {"status": "healthy", "mode": AGENT_MODE}


# ── Helper ─────────────────────────────────────────────────────

def send_to_chatwoot(account, conversation, content):
    url = (
        f"{CHATWOOT_URL}/api/v1/accounts/{account}"
        f"/conversations/{conversation}/messages"
    )
    headers = {
        "Content-Type": "application/json",
        "api_access_token": BOT_TOKEN,
    }
    r = requests.post(url, json={"content": content}, headers=headers, timeout=30)
    print(f"[CHATWOOT] {r.status_code} — {content[:80]}")
    return r.json()


# ── Entry point ────────────────────────────────────────────────

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    print(f"[BOT] Modo={AGENT_MODE} | Puerto={port} | Chatwoot={CHATWOOT_URL}")
    print(f"[BOT] Esperando webhooks en POST /webhook ...")
    app.run(host='0.0.0.0', port=port, debug=True)
