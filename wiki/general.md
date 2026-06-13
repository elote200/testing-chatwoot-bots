# Información General de la Integración Chatwoot + Agent Bot

- [Resumen del Flujo](#resumen-del-flujo)
- [¿Qué necesita un Agent Bot?](#qué-necesita-un-agent-bot)
- [Endpoints de la Integración](#endpoints-de-la-integración)
- [Ver Mensajes y Conversaciones](#ver-mensajes-y-conversaciones)
- [Estructura de Conversaciones y Mensajes](#estructura-de-conversaciones-y-mensajes)
- [Contexto de Conversacion (para el AI)](#contexto-de-conversacion-para-el-ai)
- [Últimas Actualizaciones](#últimas-actualizaciones)

**Archivos relacionados:**
- [Instalación de Chatwoot Local](setup.md) — cómo correr Chatwoot sin Docker
- [Implementación del Bot](bot.md) — cómo correr test-bot.py, variables, modos
- [Testing de Conversaciones](testing.md) — widget test, crear cuentas/inboxes, flujo de prueba

---

## Resumen del Flujo

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────────────┐
│   Cliente    │     │   Chatwoot       │     │   Agent Bot          │
│  (Widget)    │────>│  (localhost:3000) │────>│  (127.0.0.1:8000)    │
│              │     │                   │     │                      │
│  Envía msj   │     │  1. Recibe msj   │     │  3. Procesa msj      │
│              │     │  2. Webhook POST │     │     (AI: Ollama,     │
│              │     │     al bot       │     │      Groq, OpenAI,   │
│              │     │                   │     │      Rasa, etc.)    │
│              │<────│  5. Muestra resp │<────│  4. POST respuesta   │
│              │     │                   │     │     a Chatwoot API  │
└──────────────┘     └──────────────────┘     └──────────────────────┘
```

### Paso a paso:

1. El **cliente** envía un mensaje desde el widget de Chatwoot
2. **Chatwoot** recibe el mensaje y dispara un **webhook POST** al `outgoing_url` del Agent Bot
3. El **Agent Bot** recibe el webhook, extrae el mensaje, y lo procesa (lo envía a un modelo AI: Ollama, Groq, OpenAI, Rasa, etc.)
4. El **Agent Bot** toma la respuesta del modelo y la envía de vuelta a Chatwoot mediante `POST /api/v1/accounts/{id}/conversations/{id}/messages`
5. **Chatwoot** muestra la respuesta al cliente en el widget

---

## ¿Qué necesita un Agent Bot?

Para que un agente AI externo se conecte a Chatwoot, necesita **exactamente 4 cosas**:

### 1. URL de Chatwoot
La dirección base del servidor Chatwoot. En local: `http://localhost:3000`.

### 2. Token de acceso (API Key)
Chatwoot genera un token único para cada Agent Bot. Se obtiene desde la consola de Rails (ver [Crear un Agent Bot](setup.md#crear-un-agent-bot-en-chatwoot)):

```ruby
bot = AgentBot.create!(name: "Mi Bot", outgoing_url: "http://...")
bot.access_token.token
# => "x3ZqMmuo6RZbdJiWdXNjiFmF"
```

Este token se usa como `api_access_token` en los headers para autenticar las llamadas a la API de Chatwoot.

### 3. Outgoing URL
La URL que Chatwoot va a llamar cuando llegue un mensaje. Se define al crear el Agent Bot:

```ruby
outgoing_url: "http://127.0.0.1:8000/webhook"
```

Chatwoot envía un `POST` a esta URL con el payload del mensaje.

### 4. Una ruta POST que recibe el webhook
El agente debe tener un endpoint HTTP **POST** exactamente en la misma URL definida como `outgoing_url`. Cuando Chatwoot recibe un mensaje, envía allí un JSON con esta estructura:

```json
{
  "message_type": "incoming",
  "content": "Hola, necesito ayuda",
  "conversation": {"id": 1},
  "sender": {"id": 1},
  "account": {"id": 1}
}
```

### 5. Una ruta POST para responder a Chatwoot
Para enviar la respuesta de vuelta, el agente llama a la API de Chatwoot:

```
POST http://localhost:3000/api/v1/accounts/{account_id}/conversations/{conversation_id}/messages
Headers:
  Content-Type: application/json
  api_access_token: <token_del_bot>
Body:
  { "content": "Respuesta generada por el bot" }
```

### Resumen visual de la configuración:

```
┌─────────────────────────────────────────────────────────┐
│                    CHATWOOT                              │
│                                                         │
│  Agent Bot: "Mi AI Bot"                                 │
│  ├── Token:     x3ZqMmuo6RZbdJiWdXNjiFmF               │
│  └── Outgoing:  http://127.0.0.1:8000/webhook           │
│                                                         │
│  ┌─ Inbox ──────────────────────────────────────────┐   │
│  │  "Acme Support" (vinculado al Agent Bot)         │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
         │                           ▲
         │  POST /webhook            │  POST /api/v1/.../messages
         │  (mensaje del cliente)    │  (respuesta del bot)
         ▼                           │
┌─────────────────────────────────────────────────────────┐
│                    AGENT BOT                             │
│                                                         │
│  router (127.0.0.1:8000)                                 │
│                                                         │
│  POST /webhook → recibe mensaje                         │
│                → llama a AI (Ollama/Groq/OpenAI/Rasa)   │
│                → POST respuesta a Chatwoot              │
│                                                         │
│  Variables:                                             │
│  ├── CHATWOOT_URL    = http://localhost:3000            │
│  ├── CHATWOOT_TOKEN  = x3ZqMmuo6RZbdJiWdXNjiFmF       │
│  ├── AGENT_MODE      = direct | ollama | openai | rasa │
│  └── (según modo): OLLAMA_URL, OPENAI_API_KEY, etc.    │
└─────────────────────────────────────────────────────────┘
```

---

## Endpoints de la Integración

| Endpoint | Método | Quién llama | Propósito |
|----------|--------|-------------|-----------|
| `POST /webhook` (bot) | POST | Chatwoot | Chatwoot envía el mensaje del cliente al bot |
| `POST /api/v1/accounts/{id}/conversations/{id}/messages` | POST | Agent Bot | El bot envía la respuesta a Chatwoot |
| `GET /health` (bot) | GET | - | Health check del bot |

El payload de entrada (Chatwoot → Bot):

```json
{
  "message_type": "incoming",
  "content": "texto del mensaje",
  "conversation": { "id": 1 },
  "sender": { "id": 1 },
  "account": { "id": 1 }
}
```

El payload de salida (Bot → Chatwoot):

```json
{
  "content": "respuesta del bot"
}
```

### Tipos de mensaje (message_type)

| Codigo | Nombre | Descripcion |
|--------|--------|-------------|
| `0` | `incoming` | Mensaje del cliente (contact) |
| `1` | `outgoing` | Respuesta automatica del bot |
| `2` | `outgoing` | Respuesta de un agente humano |
| `3` | `template` | Mensaje con plantilla (WhatsApp, etc.) |
| `16` | `input_select` | Menu de opciones |
| `17` | `cards` | Tarjetas con acciones |
| `18` | `form` | Formulario |

### Coleccion de Postman

En la raiz del proyecto hay un archivo `chatwoot-api-postman.json` que podes importar en Postman. Contiene todos los endpoints organizados por categoria con variables y cuerpos de ejemplo listos para completar tus datos.

---

## Ver Mensajes y Conversaciones

### Desde la consola de Rails

```bash
cd chatwoot-server
bundle exec rails c
```

```ruby
# Todas las conversaciones
Conversation.all

# Mensajes de la conversacion 1
c = Conversation.find(1)
c.messages.each do |m|
  puts "[#{m.message_type}] #{m.sender&.name}: #{m.content}"
end

# message_type:
#   0 = incoming (mensaje del cliente)
#   1 = outgoing (respuesta automatica del bot)
#   2 = outgoing (respuesta de un agente humano)

# Solo los del bot:
c.messages.where(message_type: 1).each do |m|
  puts "BOT: #{m.content}"
end

# Contar mensajes por tipo:
c.messages.group(:message_type).count

# Ver todas las conversaciones de un inbox:
inbox = Inbox.find(1)
inbox.conversations.each do |conv|
  puts "--- Conversacion #{conv.id} ---"
  conv.messages.each do |m|
    puts "  [#{m.message_type}] #{m.content[0..60]}"
  end
end
```

### Desde la API REST

```bash
# Obtener mensajes de una conversacion
curl -s "http://localhost:3000/api/v1/accounts/1/conversations/1/messages" \
  -H "api_access_token: tu_token_aqui" | python3 -m json.tool

# Obtener lista de conversaciones
curl -s "http://localhost:3000/api/v1/accounts/1/conversations" \
  -H "api_access_token: tu_token_aqui" | python3 -m json.tool
```

### Estructura de la respuesta API

Todas las respuestas de la API REST de Chatwoot envuelven los datos en un objeto con dos claves:

```json
{
  "meta": { ... },
  "payload": [ ... ]
}
```

- **`payload`**: contiene los datos principales (array de mensajes, conversaciones, etc.)
- **`meta`**: contiene metadatos como paginación, conteos, etc.

Ejemplo real de `GET /conversations/1/messages`:

```json
{
  "meta": {
    "sender": {
      "id": 1,
      "name": "Test Customer",
      "thumbnail": "",
      "channel": "Channel::Widget"
    },
    "assignee": null
  },
  "payload": [
    {
      "id": 1,
      "content": "Hola, necesito ayuda",
      "message_type": 0,
      "content_type": "text",
      "source_id": null,
      "sender": {
        "id": 1,
        "name": "Test Customer",
        "type": "Contact"
      },
      "conversation_id": 1,
      "created_at": 1712345678,
      "updated_at": 1712345678
    }
  ]
}
```

> **IMPORTANTE:** Cuando leas mensajes via API desde tu bot (para contexto), siempre extrae el array de `payload`, no uses el objeto entero.

### Relaciones clave entre objetos

```
Account (1) ── tiene muchos ──> Inboxes
Account (1) ── tiene muchos ──> Conversations
Inbox (1) ── tiene muchos ────> Conversations
Conversation (1) ── tiene muchos ──> Messages
Contact ── tiene muchos ───────> Conversations (a traves de ConversationAssignee)
AgentBot ── tiene muchos ──────> Inboxes (a traves de AgentBotInbox)
```

---

## Estructura de Conversaciones y Mensajes

Esta sección detalla la estructura completa de los objetos `Message` y `Conversation` tal como los devuelve la API REST de Chatwoot. Es útil para entender qué información está disponible al construir el contexto para el AI.

### Objeto Message (desde la API)

Cuando llamas a `GET /api/v1/accounts/{id}/conversations/{id}/messages`, cada elemento del array `payload` tiene esta estructura:

```json
{
  "id": 1,
  "content": "Texto del mensaje",
  "content_type": "text",
  "content_attributes": {},
  "message_type": 0,
  "source_id": null,
  "sender": {
    "id": 1,
    "name": "John Doe",
    "type": "Contact"
  },
  "conversation_id": 1,
  "attachments": [],
  "created_at": 1712345678,
  "updated_at": 1712345678
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | integer | ID único del mensaje |
| `content` | string | Texto del mensaje |
| `content_type` | string | Tipo de contenido: `text`, `input_select`, `cards`, `form`, `article`, etc. |
| `content_attributes` | object | Atributos adicionales (opciones del menú, items del formulario, etc.) |
| `message_type` | integer | 0=incoming (cliente), 1=outgoing (bot automático), 2=outgoing (agente), 3=template, 16=input_select, 17=cards, 18=form |
| `source_id` | string | ID del mensaje en la fuente original (WhatsApp, Facebook, etc.) |
| `sender` | object | Objeto con `id`, `name`, y `type` (`Contact`, `User`, `AgentBot`) |
| `conversation_id` | integer | ID de la conversación a la que pertenece |
| `attachments` | array | Archivos adjuntos (imágenes, documentos, etc.) |
| `created_at` | integer | Timestamp Unix (segundos desde epoch) |
| `updated_at` | integer | Timestamp Unix |

### Objeto Conversation (desde la API)

Cuando llamas a `GET /api/v1/accounts/{id}/conversations`, cada elemento del array `payload` tiene esta estructura (simplificada a los campos más útiles):

```json
{
  "id": 1,
  "inbox_id": 1,
  "status": "open",
  "contact_inbox_id": 1,
  "assignee": {
    "id": 1,
    "name": "Agent Smith"
  },
  "contact": {
    "id": 1,
    "name": "John Doe",
    "email": "john@example.com",
    "phone_number": ""
  },
  "messages": [
    {
      "id": 1,
      "content": "Ultimo mensaje de la conversacion",
      "message_type": 0,
      "created_at": 1712345678,
      "sender": {
        "id": 1,
        "name": "John Doe",
        "type": "Contact"
      }
    }
  ],
  "created_at": 1712345678,
  "updated_at": 1712345678
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | integer | ID único de la conversación |
| `inbox_id` | integer | ID del inbox al que pertenece |
| `status` | string | `open`, `resolved`, `pending`, `snoozed` |
| `assignee` | object | Agente asignado (`null` si no tiene) |
| `contact` | object | Contacto que inició la conversación (nombre, email, teléfono) |
| `messages` | array | Últimos mensajes (tipicamente solo el último, no el historial completo) |
| `created_at` | integer | Timestamp Unix |
| `updated_at` | integer | Timestamp Unix |

> Para obtener **todos** los mensajes de una conversación (historial completo), usa el endpoint específico `GET /api/v1/accounts/{id}/conversations/{id}/messages`.

### Mapeo de `sender.type` a `role` para AI context

| `sender.type` | `message_type` | Se mapea a |
|---------------|----------------|------------|
| `Contact` | 0 | `role: "user"` |
| `AgentBot` | 1 | `role: "assistant"` |
| `User` | 2 | `role: "assistant"` |
| *(cualquiera)* | 3 (template) | Se omite (no es conversación humana) |

Este mapeo es el que usa `test-bot.py` para construir el historial que se envía al modelo AI. Ver [Implementación del Bot](bot.md) para más detalles.

---

## Contexto de Conversacion (para el AI)

### ¿Por qué es necesario?

Cuando Chatwoot envía un webhook al bot, el payload solo contiene **el mensaje actual**. El AI no sabe qué se dijo antes, y cada respuesta sería independiente del historial. Para que el AI entienda el contexto completo, el bot debe obtener explícitamente todos los mensajes anteriores de la conversación.

### Cómo funciona el pipeline de contexto

```
Chatwoot → Webhook (solo mensaje actual) → Bot
                                            │
                                            ▼
                          GET /api/v1/.../conversations/{id}/messages
                                            │
                                            ▼
                          Extraer payload (array de mensajes)
                                            │
                                            ▼
                          Mapear mensajes a {role, content}
                            message_type=0  → "user"
                            message_type=1  → "assistant"
                            message_type=2  → "assistant"
                            message_type=3+ → se omite
                                            │
                                            ▼
                          Construir array: [system, user, assistant, user, ...]
                                            │
                                            ▼
                          Enviar al AI → genera respuesta contextualizada
```

### Código (test-bot.py)

```python
def build_context(messages):
    """Convierte mensajes de Chatwoot a formato {role, content} para el AI."""
    context = []
    for msg in messages:
        role = None
        if msg.get("message_type") == 0:
            role = "user"
        elif msg.get("message_type") in (1, 2):
            role = "assistant"

        if role and msg.get("content"):
            context.append({"role": role, "content": msg["content"]})
    return context
```

La función completa `fetch_history()` está documentada en [Implementación del Bot](bot.md).

### El prompt completo que recibe el AI

```
System: You are a helpful support assistant for Chatwoot. Reply in the same language
        the user is writing in. Keep responses concise and friendly.

User:   Hola, necesito ayuda con mi pedido
Assistant: Claro, dime el numero de pedido y lo reviso
User:   12345
Assistant: El pedido 12345 esta en camino, llega el viernes
User:   Gracias! Y como puedo cambiar la direccion?
Assistant: <responde sabiendo que el usuario ya dio el numero de pedido>
```

### Sistema de dos tokens

El Agent Bot token **no puede leer mensajes** via la API REST. Si intentas:

```bash
curl -s "http://localhost:3000/api/v1/accounts/1/conversations/1/messages" \
  -H "api_access_token: <BOT_TOKEN>" | python3 -m json.tool
```

...obtienes:

```json
{
  "error": "Access to this endpoint is not authorized for bots"
}
```

**Solución:** Usar un **Personal Access Token de usuario** para leer, y el token del Agent Bot para escribir.

| Variable | Token de | Permiso |
|----------|----------|---------|
| `CHATWOOT_BOT_TOKEN` | Agent Bot | ✅ Escribir mensajes (aparece como "Mi AI Bot") |
| `CHATWOOT_READ_TOKEN` | Usuario | ✅ Leer historial de conversaciones |

Para generar un token de usuario: **Settings → Profile → Personal Access Tokens** en Chatwoot.

### Configuración en .env

```env
# Token del Agent Bot (para escribir respuestas)
CHATWOOT_BOT_TOKEN=x3ZqMmuo6RZbdJiWdXNjiFmF

# Token de usuario (para leer historial)
CHATWOOT_READ_TOKEN=tu_token_de_usuario_aqui

# Activar/desactivar contexto
ENABLE_CONTEXT=true
```

Si no se define `CHATWOOT_READ_TOKEN`, el bot usa el mismo `BOT_TOKEN` para leer (modo degradado: contexto vacío).

### Límite de tokens y performance

- El contexto incluye **todos** los mensajes de la conversación (sin límite actualmente).
- Conversaciones largas (>20 mensajes) pueden consumir muchos tokens del modelo AI.
- Considera implementar un límite (ej: últimos 30 mensajes) en producción.
- El overhead de la llamada `GET /messages` es mínimo (solo texto, sin archivos).

### Reintento y fallback

- Si `GET /messages` falla (error de red, token inválido), el bot responde solo con el mensaje actual.
- No hay reintento automático. El log muestra `[BOT] Warning: Could not fetch context`.
- La respuesta se envía igual, pero sin historial.

---

## Últimas Actualizaciones

- **2024-01-01**: Documentación inicial creada
- **2025-06-11**: Agregada guía de instalación Chatwoot sin Docker, Agent Bots, y ejemplos
- **2026-06-12**: Wiki dividida en archivos separados (general.md, setup.md, bot.md). Agregada estructura detallada de objetos Message y Conversation, mapeo sender.type → role, sección dedicada al contexto de conversación
- **Versión Chatwoot API:** v1
- **Última revisión:** 2026-06-12
