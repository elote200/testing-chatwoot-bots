from flask import Flask, request
import requests
import os

app = Flask(__name__)

# Configura estos valores
CHATWOOT_URL = "http://localhost:3000"
BOT_TOKEN = "x3ZqMmuo6RZbdJiWdXNjiFmF"  # <-- PONÉ TU TOKEN

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    
    message_type = data.get('message_type')
    content = data.get('content', '')
    conversation_id = data['conversation']['id']
    account_id = data['account']['id']
    
    print(f"[{message_type}] Conversación {conversation_id}: {content}")
    
    # Solo responder a mensajes entrantes (del cliente)
    if message_type == 'incoming':
        # Plane tu respuesta
        reply = f"Recibí tu mensaje: '{content}'. Soy un bot de prueba hahaha!"
        
        # Enviar respuesta via API de Chatwoot
        url = f"{CHATWOOT_URL}/api/v1/accounts/{account_id}/conversations/{conversation_id}/messages"
        headers = {
            "Content-Type": "application/json",
            "api_access_token": BOT_TOKEN
        }
        requests.post(url, json={"content": reply}, headers=headers)
    
    return "OK", 200

if __name__ == '__main__':
    app.run(port=8000, debug=True)
