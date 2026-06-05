# Chatwoot API Integration Wiki

## Índice
1. [Autenticación](#autenticación)
2. [Endpoints Principales](#endpoints-principales)
3. [Flujo de Agent Bot](#flujo-de-agent-bot)
4. [Estructuras de Datos](#estructuras-de-datos)
5. [Errores Comunes](#errores-comunes)
6. [Ejemplos de Integración](#ejemplos-de-integración)

---

## Autenticación

### Método: API Key

Todas las solicitudes a la API de Chatwoot requieren un header `api_access_token`:

```
api_access_token: your_api_key_here
```

### Obtener API Key

1. Ir a Chatwoot Dashboard
2. Navegas a Settings → Access Tokens
3. Crear nuevo token con permisos necesarios
4. Copiar el token generado

### Headers Requeridos

```
Content-Type: application/json
api_access_token: YOUR_API_KEY
```

---

## Endpoints Principales

### 1. Conversations (Conversaciones)

#### Obtener Conversación

```
GET /api/v1/accounts/{account_id}/conversations/{conversation_id}
```

**Headers:**
```
api_access_token: YOUR_API_KEY
```

**Response (200 OK):**
```json
{
  "payload": {
    "id": 123,
    "inbox_id": 1,
    "contact_id": 456,
    "status": "open",
    "created_at": "2024-01-01T10:00:00Z",
    "updated_at": "2024-01-01T10:30:00Z",
    "messages": [
      {
        "id": 1,
        "conversation_id": 123,
        "message_type": "incoming",
        "content": "Hello",
        "sender_id": 456,
        "created_at": "2024-01-01T10:00:00Z"
      }
    ]
  }
}
```

#### Listar Conversaciones

```
GET /api/v1/accounts/{account_id}/conversations?status=open&limit=20
```

**Query Parameters:**
- `status`: open, pending, resolved, snoozed
- `limit`: Número de conversaciones (default: 15, max: 100)
- `offset`: Para paginación

---

### 2. Messages (Mensajes)

#### Enviar Mensaje

```
POST /api/v1/accounts/{account_id}/conversations/{conversation_id}/messages
```

**Request Body:**
```json
{
  "content": "Thank you for reaching out!",
  "message_type": "outgoing",
  "private": false
}
```

**Response (201 Created):**
```json
{
  "payload": {
    "id": 2,
    "conversation_id": 123,
    "content": "Thank you for reaching out!",
    "message_type": "outgoing",
    "sender_id": null,
    "created_at": "2024-01-01T10:05:00Z"
  }
}
```

**Message Types:**
- `incoming`: Mensaje del cliente
- `outgoing`: Mensaje del agente
- `activity`: Evento de actividad

---

### 3. Contacts (Contactos)

#### Obtener Contacto

```
GET /api/v1/accounts/{account_id}/contacts/{contact_id}
```

**Response:**
```json
{
  "payload": {
    "id": 456,
    "email": "customer@example.com",
    "name": "John Doe",
    "phone_number": "+1234567890",
    "created_at": "2024-01-01T09:00:00Z"
  }
}
```

---

### 4. Inboxes (Bandejas)

#### Listar Inboxes

```
GET /api/v1/accounts/{account_id}/inboxes
```

**Response:**
```json
{
  "payload": [
    {
      "id": 1,
      "account_id": 1,
      "name": "Support",
      "channel_type": "web_widget",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

---

## Flujo de Agent Bot

### Diagrama de Flujo

```
┌─────────────────────────────────────────────────────────────┐
│ Cliente envia mensaje a Chatwoot                             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Chatwoot recibe mensaje (webhook o polling)                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Agent Service procesa el mensaje                            │
│ - Obtiene contexto de conversación                          │
│ - Genera respuesta (AI model)                               │
│ - Prepara reply                                             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Agent envia respuesta via API                               │
│ POST /api/v1/accounts/{id}/conversations/{id}/messages     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Cliente recibe respuesta en Chatwoot                         │
└─────────────────────────────────────────────────────────────┘
```

### Flujo en Código

```csharp
// 1. Obtener conversación pendiente
var conversation = await chatwootClient.GetConversationAsync(accountId, conversationId, apiKey);

// 2. Procesar último mensaje
var lastMessage = conversation.Messages.Last();
var userInput = lastMessage.Content;

// 3. Generar respuesta (con AI model)
var aiResponse = await aiModel.GenerateResponse(userInput);

// 4. Enviar respuesta
var sendRequest = new SendMessageRequest { Content = aiResponse };
await chatwootClient.SendMessageAsync(accountId, conversationId, sendRequest, apiKey);

// 5. Actualizar estado si es necesario
// await chatwootClient.UpdateConversationStatusAsync(accountId, conversationId, "resolved", apiKey);
```

---

## Estructuras de Datos

### Conversation Object

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | int | ID único de la conversación |
| `inbox_id` | int | ID de la bandeja |
| `contact_id` | int | ID del contacto |
| `status` | string | open, pending, resolved, snoozed |
| `messages` | array | Array de mensajes |
| `created_at` | datetime | Fecha de creación |
| `updated_at` | datetime | Última actualización |

### Message Object

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | int | ID único del mensaje |
| `conversation_id` | int | ID de la conversación |
| `content` | string | Contenido del mensaje |
| `message_type` | string | incoming, outgoing, activity |
| `sender_id` | int | ID de quien envía (null si es bot) |
| `created_at` | datetime | Fecha de creación |

### Contact Object

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | int | ID único del contacto |
| `email` | string | Email del contacto |
| `name` | string | Nombre completo |
| `phone_number` | string | Número de teléfono |
| `created_at` | datetime | Fecha de creación |

---

## Errores Comunes

### 401 Unauthorized

```json
{
  "error": "Unauthorized"
}
```

**Causas:**
- API key inválido o expirado
- Header `api_access_token` faltante
- Account ID incorrecto

**Solución:**
- Verificar API key en Chatwoot
- Validar formato del header

### 404 Not Found

```json
{
  "error": "Not Found"
}
```

**Causas:**
- Conversation ID no existe
- Account ID incorrecto
- Inbox no existe

**Solución:**
- Verificar IDs en el dashboard
- Confirmar que la conversación/contacto existe

### 422 Unprocessable Entity

```json
{
  "error": "Invalid parameters"
}
```

**Causas:**
- Datos inválidos en el request
- Mensaje vacío
- Formato incorrecto

**Solución:**
- Validar datos antes de enviar
- Revisar estructura del request

### 429 Too Many Requests

```json
{
  "error": "Rate limit exceeded"
}
```

**Causas:**
- Demasiadas solicitudes en poco tiempo

**Solución:**
- Implementar rate limiting en el agente
- Usar exponential backoff

---

## Ejemplos de Integración

### Ejemplo 1: Polling de Conversaciones

```csharp
var accountId = 1;
var apiKey = "your_api_key";

// Obtener conversaciones pendientes
var response = await chatwootClient.GetConversationsAsync(accountId, apiKey);

if (response.IsSuccessStatusCode)
{
    foreach (var conversation in response.Content)
    {
        if (conversation.Status == "pending")
        {
            // Procesar conversación
            var lastMessage = conversation.Messages?.LastOrDefault();
            if (lastMessage?.MessageType == "incoming")
            {
                var reply = GenerateResponse(lastMessage.Content);
                await SendReply(accountId, conversation.Id, reply);
            }
        }
    }
}
```

### Ejemplo 2: Webhook Receiver

```csharp
[HttpPost("webhook/message")]
public async Task<IActionResult> HandleMessageWebhook([FromBody] WebhookPayload payload)
{
    // Chatwoot envía el evento
    var conversationId = payload.Data.ConversationId;
    var messageContent = payload.Data.Message.Content;
    
    // Generar respuesta
    var response = await _aiService.GenerateResponse(messageContent);
    
    // Enviar reply
    await _agentService.SendReplyAsync(conversationId, response);
    
    return Ok();
}
```

### Ejemplo 3: Con AI Model (Ollama)

```csharp
public async Task ProcessConversation(int conversationId)
{
    // 1. Obtener contexto
    var conversation = await _chatwootClient.GetConversationAsync(
        _settings.AccountId, conversationId, _settings.ApiKey);
    
    // 2. Extraer mensaje
    var messages = conversation.Messages
        .OrderBy(m => m.CreatedAt)
        .Select(m => new { role = m.MessageType, content = m.Content })
        .ToList();
    
    // 3. Generar respuesta con Ollama
    var ollamaResponse = await _httpClient.PostAsync(
        "http://localhost:11434/api/generate",
        new StringContent(JsonConvert.SerializeObject(new {
            model = "llama2",
            prompt = messages.Last().content,
            stream = false
        }))
    );
    
    var result = JsonConvert.DeserializeObject<dynamic>(
        await ollamaResponse.Content.ReadAsStringAsync());
    
    // 4. Enviar respuesta
    await _agentService.SendReplyAsync(conversationId, result.response);
}
```

---

## Rate Limiting

Chatwoot implementa rate limiting:
- **Límite:** Típicamente 1000 requests por minuto
- **Header de respuesta:** `RateLimit-Remaining`

Para implementar en el agente:

```csharp
public class RateLimitHandler : DelegatingHandler
{
    private int _remainingRequests = 1000;
    
    protected override async Task<HttpResponseMessage> SendAsync(
        HttpRequestMessage request, CancellationToken cancellationToken)
    {
        var response = await base.SendAsync(request, cancellationToken);
        
        if (response.Headers.TryGetValues("RateLimit-Remaining", out var values))
        {
            if (int.TryParse(values.First(), out var remaining))
            {
                _remainingRequests = remaining;
                if (_remainingRequests < 10)
                    _logger.Warning("Rate limit approaching: {Remaining}", _remainingRequests);
            }
        }
        
        return response;
    }
}
```

---

## Recursos

- [Documentación oficial de Chatwoot API](https://developers.chatwoot.com/api-reference/introduction)
- [Agent Bots Guide](https://www.chatwoot.com/hc/articles/1677497472-how-to-use-agent-bots)
- [Webhooks Documentation](https://developers.chatwoot.com/docs/product/conversations/webhooks)
- [Rate Limiting Info](https://developers.chatwoot.com/docs/platform/api/rate-limiting)

---

## Últimas Actualizaciones

- **2024-01-01**: Documentación inicial creada
- **Versión Chatwoot API:** v1
- **Última revisión:** 2024-01-01
