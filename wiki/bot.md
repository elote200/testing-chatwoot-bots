# Implementación del Bot Agente

- [Cómo correr el bot (test-bot.py)](#cómo-correr-el-bot-test-botpy)
- [Explicación del Código](#explicación-del-código)
- [Contexto de Conversacion](#contexto-de-conversacion-enable_context)
- [Formas alternativas de iniciar](#formas-alternativas-de-iniciar)
- [Modos del agente](#modos-del-agente)
- [Variables de entorno](#variables-de-entorno)
- [Otras implementaciones](#otras-implementaciones)
- [Configuración del Proyecto C# (.NET 10)](#configuración-del-proyecto-c-net-10-para-el-bot-agent)

**Archivos relacionados:**
- [Información General](general.md) — flujo de integración, endpoints, estructuras de datos
- [Instalación de Chatwoot Local](setup.md) — cómo correr Chatwoot sin Docker

---

## Cómo correr el bot (test-bot.py)

### Requisitos

- Python 3.10+
- pip

### 1. Primer inicio (solo una vez)

```bash
# Ir a la raiz del proyecto
cd /home/kelvin/concu/chatwoot-api-agent-test

# Crear entorno virtual
python3 -m venv .venv

# Activar entorno
source .venv/bin/activate

# Instalar dependencias
pip install flask requests python-dotenv gunicorn

# (Opcional) Copiar ejemplo de configuracion
cp .env.example .env
```

### 2. Configurar (.env)

Editar `.env` con los valores correspondientes:

```env
CHATWOOT_URL=http://localhost:3000
CHATWOOT_BOT_TOKEN=x3ZqMmuo6RZbdJiWdXNjiFmF
AGENT_MODE=openai
OPENAI_URL=https://api.groq.com/openai/v1
OPENAI_API_KEY=gsk_tu_api_key
OPENAI_MODEL=llama-3.3-70b-versatile
```

> Si no tenes API key de Groq, usa `AGENT_MODE=direct` para probar sin conexion externa.

### 3. Iniciar el bot

Con el `.env` configurado:

```bash
source .venv/bin/activate   # si no lo activaste
python3 test-bot.py
```

Deberias ver:

```
[BOT] Modo=openai | Puerto=8000 | Chatwoot=http://localhost:3000
 * Running on http://0.0.0.0:8000
```

### 4. Verificar que funciona

```bash
# Health check
curl http://localhost:8000/health
# → {"status": "healthy", "mode": "openai"}

# Simular un webhook de Chatwoot
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "message_type": "incoming",
    "content": "Hola, esto es una prueba",
    "conversation": {"id": 1},
    "sender": {"id": 1},
    "account": {"id": 1}
  }'
```

### 5. Probar desde el widget

Abrir en el navegador:

```
http://localhost:3000/widget_tests
```

Escribi un mensaje y el bot deberia responder automaticamente.

---

## Explicación del Código

El archivo `test-bot.py` implementa un bot Flask con tres modos de respuesta. Acá están las partes clave:

### Estructura general

```
test-bot.py
├── Config (variables de entorno)
├── fetch_history()    → Obtiene mensajes previos de Chatwoot
├── handle_direct()    → Responde sin AI (modo prueba)
├── handle_openai()    → Responde via API compatible con OpenAI
├── handle_ollama()    → Responde via Ollama local
├── POST /webhook      → Ruta que recibe el webhook de Chatwoot
├── GET /health        → Health check
└── send_to_chatwoot() → Envia la respuesta a Chatwoot
```

### fetch_history(account_id, conversation_id)

**Propósito:** Ir a buscar a Chatwoot todos los mensajes anteriores de una conversación y transformarlos al formato `{role, content}` que entiende un LLM.

**Flujo interno:**

1. Hace `GET /api/v1/accounts/{id}/conversations/{id}/messages` usando `READ_TOKEN`
2. Extrae el array `payload` de la respuesta (Chatwoot envuelve en `{"meta":{...}, "payload":[...]}`)
3. Itera cada mensaje y mapea `message_type` a `role`:
   - `message_type=0` (incoming, cliente) → `"user"`
   - `message_type=1` (outgoing, bot) o `2` (outgoing, agente) → `"assistant"`
   - Otros tipos se ignoran (templates, input_select, cards, form)
4. Devuelve un array como `[{"role": "user", "content": "Hola"}, {"role": "assistant", "content": "Dime"}]`

**Si falla** (token inválido, error de red, formato inesperado), devuelve lista vacía y el bot responde solo con el mensaje actual.

```python
def fetch_history(account_id, conversation_id):
    url = f"{CHATWOOT_URL}/api/v1/accounts/{account_id}/conversations/{conversation_id}/messages"
    headers = {"api_access_token": READ_TOKEN}
    r = requests.get(url, headers=headers, timeout=30)

    if not r.ok:
        return []  # fallback silencioso

    messages = r.json()
    if isinstance(messages, dict):
        messages = messages.get('payload', [])

    history = []
    for msg in messages:
        role = msg.get('message_type')
        content = msg.get('content', '')
        if not content:
            continue
        if role == 0:
            history.append({"role": "user", "content": content})
        elif role in (1, 2):
            history.append({"role": "assistant", "content": content})
    return history
```

### handle_openai(sender, message, history)

**Propósito:** Enviar el mensaje y el historial a un API compatible con OpenAI (OpenAI, Groq, Google Gemini, etc.) y devolver la respuesta.

**Por qué el orden `[system, ...history, user]`:**

```python
messages = [{"role": "system", "content": SYSTEM_PROMPT}]   # 1. Instrucciones fijas
messages.extend(history)                                      # 2. Historial completo
messages.append({"role": "user", "content": message})        # 3. Mensaje actual
```

Los modelos de lenguaje procesan el texto de **izquierda a derecha** (son autoregresivos). El orden importa porque construye la ventana de atención:

1. **`system` primero** — Define el comportamiento del asistente antes de ver cualquier mensaje. Si estuviera al final, el modelo procesaría toda la conversación sin saber qué rol tiene.

2. **`history` después** — Le da contexto de lo que ya pasó. Así entiende referencias como "mi pedido" o "como te decía".

3. **`user` al final** — Es el mensaje nuevo que debe responder **ahora**. El modelo asume que el último mensaje es el que necesita respuesta inmediata.

**Ejemplo de lo que recibe el modelo:**
```
System: Sos un asistente de soporte...
User:   Hola, necesito ayuda
Assistant: Claro, decime tu numero de pedido
User:   12345
User:   Gracias! Ya llegó?      ← mensaje actual, necesita respuesta
```

### handle_ollama(sender, message, history)

Exactamente el mismo patrón que `handle_openai`, pero llama al endpoint `/api/chat` de Ollama en lugar de `/chat/completions`.

### POST /webhook — Ruta principal

```python
@app.route('/webhook', methods=['POST'])
def webhook():
```

1. Extrae `message_type`, `content`, `conversation.id`, `account.id`, `sender.id` del JSON
2. Ignora mensajes que no son `"incoming"` (no responde a sus propias respuestas)
3. Ignora mensajes duplicados (usa un **cache en memoria** `_processed_ids` para evitar loops)
4. Si `ENABLE_CONTEXT=true`, llama a `fetch_history()` para obtener los mensajes previos
5. Llama al handler según el modo (`handle_direct`, `handle_openai`, `handle_ollama`)
6. Envia la respuesta a Chatwoot via `send_to_chatwoot()`

### send_to_chatwoot(account, conversation, content)

Hace `POST /api/v1/accounts/{id}/conversations/{id}/messages` con el token del Agent Bot (`BOT_TOKEN`).

```python
def send_to_chatwoot(account, conversation, content):
    url = f"{CHATWOOT_URL}/api/v1/accounts/{account}/conversations/{conversation}/messages"
    headers = {"Content-Type": "application/json", "api_access_token": BOT_TOKEN}
    r = requests.post(url, json={"content": content}, headers=headers, timeout=30)
```

---

## Contexto de Conversacion (ENABLE_CONTEXT)

Por defecto, el bot obtiene **todos los mensajes anteriores** de la conversacion y se los pasa al AI como contexto. Asi el AI no solo responde el ultimo mensaje, sino que entiende todo el historial.

**Configuración rápida:**

```env
# Token del Agent Bot (para escribir respuestas)
CHATWOOT_BOT_TOKEN=x3ZqMmuo6RZbdJiWdXNjiFmF

# Token de usuario (para leer historial)
CHATWOOT_READ_TOKEN=tu_token_de_usuario_aqui

# Activar/desactivar contexto
ENABLE_CONTEXT=true
```

La explicación detallada del pipeline de contexto, el mapeo de roles, el sistema de dos tokens, y la estructura de datos está en [Información General → Contexto de Conversacion](general.md#contexto-de-conversacion-para-el-ai).

---

## Formas alternativas de iniciar

### Sin .env (variables inline)

```bash
source .venv/bin/activate

# Groq
AGENT_MODE=openai \
  OPENAI_URL=https://api.groq.com/openai/v1 \
  OPENAI_API_KEY=gsk_tu_api_key \
  OPENAI_MODEL=llama-3.3-70b-versatile \
  python3 test-bot.py

# OpenAI
AGENT_MODE=openai \
  OPENAI_API_KEY=sk-... \
  OPENAI_MODEL=gpt-4o-mini \
  python3 test-bot.py

# Google Gemini
AGENT_MODE=openai \
  OPENAI_URL=https://generativelanguage.googleapis.com/v1beta/openai \
  OPENAI_API_KEY=AIza... \
  OPENAI_MODEL=gemini-2.0-flash \
  python3 test-bot.py

# Ollama (local)
AGENT_MODE=ollama OLLAMA_MODEL=llama3.2 python3 test-bot.py

# Modo directo (sin AI, para probar el flujo)
AGENT_MODE=direct python3 test-bot.py
```

### En background (para no ocupar la terminal)

```bash
nohup python3 test-bot.py > bot.log 2>&1 &
```

### Con gunicorn (produccion)

```bash
source .venv/bin/activate
pip install gunicorn
python3 -m gunicorn --workers=1 test-bot:app -b 0.0.0.0:8000
```

---

## Modos del agente

| Modo | `AGENT_MODE=` | ¿Qué hace? |
|------|--------------|------------|
| `direct` | `direct` | Responde inline (para pruebas, default) |
| `openai` | `openai` | OpenAI, Groq, Google Gemini, etc. |
| `ollama` | `ollama` | Modelo local con Ollama |

---

## Variables de entorno

| Variable | Default | Descripción |
|---|---|---|
| `CHATWOOT_URL` | `http://localhost:3000` | Chatwoot server base URL |
| `CHATWOOT_BOT_TOKEN` | `x3ZqMmuo6RZbdJiWdXNjiFmF` | Token del Agent Bot (para escribir, aparece como el bot) |
| `CHATWOOT_READ_TOKEN` | *(= BOT_TOKEN)* | Token de usuario para leer historial. Sino usa el mismo BOT_TOKEN |
| `AGENT_MODE` | `direct` | Backend mode: `direct`, `openai`, or `ollama` |
| `OPENAI_URL` | `https://api.openai.com/v1` | Base URL del API (OpenAI, Groq, Gemini, etc.) |
| `OPENAI_API_KEY` | *(requerido en openai mode)* | API key del proveedor |
| `OPENAI_MODEL` | `gpt-4o-mini` | Modelo a usar |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.2` | Ollama model name |
| `ENABLE_CONTEXT` | `true` | Pasa el historial completo de la conversacion al AI |
| `PORT` | `8000` | Puerto donde corre el bot |

---

## Otras implementaciones

En `implementation-examples/` hay ejemplos adicionales (Rasa, LangChain, etc.) como referencia para arquitecturas más complejas, pero el `test-bot.py` raíz es suficiente para el caso de uso principal.

---

## Configuración del Proyecto C# (.NET 10) para el Bot Agent

Cuando estés listo para crear tu propio agente en C#, aquí está la estructura mínima:

```bash
# Crear el proyecto
dotnet new webapi -n ChatwootBotAgent
cd ChatwootBotAgent
```

**Endpoints necesarios que tu agente debe implementar:**

| Endpoint | Método | Propósito |
|----------|--------|-----------|
| `POST /webhook` | POST | Recibir mensajes de Chatwoot (cuando se configura como Agent Bot) |
| `GET /health` | GET | Health check |

**Requerimientos del agente:**

1. **Webhook receptor** — Endpoint POST que Chatwoot llama cuando llega un mensaje
2. **Cliente HTTP para Chatwoot API** — Enviar respuestas via `POST /api/v1/accounts/{id}/conversations/{id}/messages`
3. **Conexión a modelo AI** — Ollama local, Groq, OpenAI, Anthropic, etc.
4. **Token de acceso** — El `api_access_token` del Agent Bot creado en Chatwoot

**Variables de entorno necesarias (.env):**

```
CHATWOOT_URL=http://localhost:3000
CHATWOOT_ACCESS_TOKEN=<agent_bot_token>
AI_PROVIDER=groq           # ollama | openai | groq | anthropic
AI_MODEL=llama-3.3-70b-versatile
AI_API_KEY=                # solo si AI_PROVIDER != ollama
OLLAMA_URL=http://localhost:11434
```
