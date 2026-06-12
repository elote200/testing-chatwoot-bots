#!/usr/bin/env python3
"""
Chatwoot Agent Bot — single file, Flask.
Recibe webhooks de Chatwoot, consulta un modelo AI y responde.

Caracteristicas:
  - Contexto de conversacion: obtiene todos los mensajes previos
    para que el AI sepa de que se venia hablando.
  - Modos: direct, openai (Groq/OpenAI/Gemini), ollama

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
ENABLE_CONTEXT = os.environ.get('ENABLE_CONTEXT', 'true').lower() == 'true'

# OpenAI-compatible (Groq, OpenAI, Google Gemini, etc.)
OPENAI_URL = os.environ.get('OPENAI_URL', 'https://api.openai.com/v1')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')

# Ollama
OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama3.2')

SYSTEM_PROMPT = (
    "You are a helpful support assistant for a company called Acme Inc. "
    "Answer concisely and naturally in the same language as the user. "
    "Use the conversation history to understand the context."
)

app = Flask(__name__)


# ── Obtener historial de la conversacion desde Chatwoot ──────

def fetch_history(account_id, conversation_id):
    """Obtiene todos los mensajes de una conversacion y los ordena
    como una lista de {role, content} para pasar al AI.

    Nota: El token de Agent Bot no tiene permiso para leer mensajes
    via API REST. Si falla, se devuelve lista vacia (solo el mensaje
    actual se usara como contexto).
    """
    url = (
        f"{CHATWOOT_URL}/api/v1/accounts/{account_id}"
        f"/conversations/{conversation_id}/messages"
    )
    headers = {"api_access_token": BOT_TOKEN}
    r = requests.get(url, headers=headers, timeout=30)

    if not r.ok:
        print(f"[CONTEXT] No se pudo obtener historial "
              f"(HTTP {r.status_code}): usando solo mensaje actual")
        return []

    messages = r.json()
    if not isinstance(messages, list):
        print(f"[CONTEXT] Respuesta inesperada de la API, usando solo mensaje actual")
        return []

    history = []
    for msg in messages:
        role = msg.get('message_type')
        content = msg.get('content', '')

        if not content:
            continue

        # message_type: 0=incoming (cliente), 1=outgoing (bot), 2=outgoing (agente)
        if role == 0:
            history.append({"role": "user", "content": content})
        elif role in (1, 2):
            history.append({"role": "assistant", "content": content})

    return history


# ── Handlers por modo ──────────────────────────────────────────

def handle_direct(sender, message, history):
    return f"Recibi tu mensaje: \"{message}\". Bot conectado a Chatwoot."


def handle_openai(sender, message, history):
    if not OPENAI_API_KEY:
        return "Error: OPENAI_API_KEY no configurada."

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": message})

    payload = {"model": OPENAI_MODEL, "messages": messages}
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


def handle_ollama(sender, message, history):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": message})

    payload = {"model": OLLAMA_MODEL, "messages": messages, "stream": False}
    r = requests.post(
        f"{OLLAMA_URL.rstrip('/')}/api/chat",
        json=payload, timeout=120,
    )
    r.raise_for_status()
    return r.json()["message"]["content"]


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
            # Obtener contexto de la conversacion (mensajes anteriores)
            history = []
            if ENABLE_CONTEXT:
                history = fetch_history(account_id, conversation_id)
                print(f"[CONTEXT] {len(history)} mensajes previos cargados")

            bot_reply = reply_to_message(sender_id, content, history)
            send_to_chatwoot(account_id, conversation_id, bot_reply)
        except Exception as e:
            print(f"[ERROR] {e}")

    return {"status": "ok"}, 200


@app.route('/health')
def health():
    return {
        "status": "healthy",
        "mode": AGENT_MODE,
        "context": ENABLE_CONTEXT,
    }


# ── Helpers ────────────────────────────────────────────────────

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
    print(f"[BOT] Modo={AGENT_MODE} | Contexto={ENABLE_CONTEXT} | Puerto={port}")
    print(f"[BOT] Esperando webhooks en POST /webhook ...")
    app.run(host='0.0.0.0', port=port, debug=True)
