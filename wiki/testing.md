# Testing de Conversaciones en Chatwoot

Guía práctica para crear y probar conversaciones en Chatwoot con múltiples cuentas, inboxes y el Agent Bot.

- [Ver inboxes disponibles](#ver-inboxes-disponibles)
- [Widget test page (`/widget_tests`)](#widget-test-page-widget_tests)
- [Crear conversaciones desde la API REST](#crear-conversaciones-desde-la-api-rest)
- [Crear conversaciones desde la consola de Rails](#crear-conversaciones-desde-la-consola-de-rails)
- [Crear múltiples cuentas (empresas)](#crear-múltiples-cuentas-empresas)
- [Crear inboxes y vincularlos al bot](#crear-inboxes-y-vincularlos-al-bot)
- [Flujo completo: cuenta nueva + inbox + bot + widget test](#flujo-completo-cuenta-nueva--inbox--bot--widget-test)
- [Referencia rápida de comandos](#referencia-rápida-de-comandos)

**Archivos relacionados:**
- [Información General](general.md) — flujo de integración, endpoints, estructuras de datos
- [Instalación de Chatwoot Local](setup.md) — cómo correr Chatwoot sin Docker
- [Implementación del Bot](bot.md) — cómo correr test-bot.py, variables, modos

---

## Ver inboxes disponibles

### Desde la consola de Rails

```bash
cd chatwoot-server
bundle exec rails c
```

```ruby
# Todos los inboxes con tipo y cuenta
Inbox.all.each do |i|
  puts "ID #{i.id} | #{i.name} | Tipo: #{i.channel_type} | Cuenta: #{i.account.name}"
end

# Solo los de tipo Web Widget (los que funcionan con /widget_tests)
Channel::WebWidget.all.each do |w|
  puts "Inbox ID #{w.inbox.id} — #{w.inbox.name} (website_token: #{w.website_token})"
end
```

### Desde el navegador

`http://localhost:3000` → **Settings** (⚙️) → **Inboxes**

### Desde la API REST

```bash
curl -s "http://localhost:3000/api/v1/accounts/1/inboxes" \
  -H "api_access_token: TU_TOKEN" | python3 -m json.tool
```

---

## Widget test page (`/widget_tests`)

Chatwoot incluye una página de prueba para el widget: `http://localhost:3000/widget_tests`.

### Cómo funciona internamente

El controller `WidgetTestsController` usa esta lógica para decidir qué inbox cargar:

```ruby
def inbox_id
  @inbox_id ||= params[:inbox_id] || Channel::WebWidget.first.inbox.id
end
```

Es decir:
- Si pasás `?inbox_id=N` en la URL, usa ese inbox
- Si no, usa **el primer inbox de tipo Web Widget** que exista en la DB

### Usar un inbox específico

```
http://localhost:3000/widget_tests?inbox_id=1
http://localhost:3000/widget_tests?inbox_id=2
http://localhost:3000/widget_tests?inbox_id=3
```

### Parámetros adicionales del widget test

| Parámetro | Valores | Default | Ejemplo |
|-----------|---------|---------|---------|
| `inbox_id` | ID del inbox | `Channel::WebWidget.first.inbox.id` | `?inbox_id=2` |
| `position` | `left`, `right` | `left` | `?position=right` |
| `type` | `standard`, `expanded_bubble` | `expanded_bubble` | `?type=standard` |
| `widget_style` | `standard` | `standard` | — |
| `dark_mode` | `light`, `dark` | `light` | `?dark_mode=dark` |

### Crear una conversación completamente nueva

Cada vez que abrís `/widget_tests` **en una ventana de incógnito** (o limpiando cookies), el SDK crea un nuevo contacto y una nueva conversación. También podés refrescar la página si el SDK detecta que la conversación fue resuelta.

Para forzar una conversación nueva sin cerrar el navegador: abrí la URL en una ventana de incógnito distinta.

---

## Crear conversaciones desde la API REST

### Opción 1: Via widget API (como si fuera el SDK)

Esto es lo que realmente hace el SDK del widget. Crear un contacto nuevo automáticamente crea una conversación nueva.

Primero necesitás el `website_token` del inbox:

```bash
# Obtener website_token
cd chatwoot-server
bundle exec rails runner "puts Inbox.find(1).channel.website_token"
```

```bash
# Enviar mensaje como contacto nuevo (crea conversación automáticamente)
curl -s -X POST "http://localhost:3000/api/v1/widget/messages" \
  -H "Content-Type: application/json" \
  -d '{
    "website_token": "EL_WEBSITE_TOKEN",
    "contact": {
      "email": "test-'$(date +%s)'@example.com",
      "name": "Test User"
    },
    "message": {
      "content": "Hola! soy un contacto nuevo"
    }
  }' | python3 -m json.tool
```

Usar `$(date +%s)` en el email garantiza un contacto único cada vez.

### Opción 2: Via REST API (control total)

```bash
# 1. Crear un contacto
curl -s -X POST "http://localhost:3000/api/v1/accounts/1/contacts" \
  -H "api_access_token: TU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "inbox_id": 1,
    "name": "Test '$RANDOM'",
    "email": "test'$RANDOM'@example.com"
  }' | python3 -m json.tool
# → Guardar el "id" del contacto de la respuesta

# 2. Crear la conversación con un mensaje inicial
curl -s -X POST "http://localhost:3000/api/v1/accounts/1/conversations" \
  -H "api_access_token: TU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source_id": "src-'$(date +%s)'",
    "inbox_id": 1,
    "contact_id": <CONTACT_ID>,
    "message": {
      "content": "Hola, necesito ayuda"
    }
  }' | python3 -m json.tool
```

---

## Crear conversaciones desde la consola de Rails

Para debugging rápido:

```bash
cd chatwoot-server
bundle exec rails c
```

```ruby
# Crear contacto nuevo
contact = Contact.create!(
  account: Account.first,
  name: "Test #{Time.now.to_i}",
  email: "test#{Time.now.to_i}@example.com"
)

# Vincular contacto al inbox
inbox = Inbox.first
contact_inbox = ContactInbox.create!(
  contact: contact,
  inbox: inbox,
  source_id: SecureRandom.uuid
)

# Crear conversación
conv = Conversation.create!(
  account: Account.first,
  inbox: inbox,
  contact: contact,
  contact_inbox: contact_inbox,
  status: :open
)

# Poner un mensaje del cliente (dispara el webhook al bot)
conv.messages.create!(
  message_type: :incoming,
  content: "Hola, necesito ayuda con mi pedido",
  sender: contact,
  account: Account.first
)

puts "✅ Conversación #{conv.id} creada — el bot debería responder"
```

---

## Crear múltiples cuentas (empresas)

Cada cuenta en Chatwoot es independiente: tiene sus propios inboxes, contactos, agentes y conversaciones.

### Desde Rails console

```ruby
# Crear cuenta
nueva = Account.create!(name: "Mi Otra Empresa")

# Verificar que arranca vacía
nueva.inboxes.count   # → 0
nueva.contacts.count  # → 0
```

### Desde el Super Admin (navegador)

```
http://localhost:3000/super_admin
```

Ahí hay un panel para crear cuentas gráficamente.

### Desde la API REST

```bash
curl -s -X POST "http://localhost:3000/api/v1/accounts" \
  -H "api_access_token: TU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Mi Otra Empresa"}' | python3 -m json.tool
```

---

## Crear inboxes y vincularlos al bot

Una cuenta nueva no tiene inboxes. Hay que crearlos.

### Paso 1: Crear un inbox de tipo Web Widget

```ruby
account = Account.find(2) # o Account.find_by(name: "Mi Otra Empresa")

web_widget = Channel::WebWidget.create!(
  account: account,
  website_url: 'https://miempresa.com'
)

inbox = Inbox.create!(
  channel: web_widget,
  account: account,
  name: 'Widget Principal'
)

puts "Inbox ID: #{inbox.id}"
puts "website_token: #{web_widget.website_token}"
```

### Paso 2: Vincular el Agent Bot al inbox

Sin este paso, el bot **no responde** los mensajes de ese inbox.

```ruby
bot = AgentBot.find_by(name: "Mi AI Bot")
AgentBotInbox.create!(inbox: inbox, agent_bot: bot)
```

### Paso 3: Verificar la vinculación

```ruby
bot = AgentBot.find_by(name: "Mi AI Bot")
bot.inboxes.each do |i|
  puts "Bot vinculado a: Inbox #{i.id} — #{i.name} (Cuenta: #{i.account.name})"
end
```

### Tipos de inbox que soporta el widget test

El widget test **solo funciona** con inboxes de tipo `Channel::WebWidget`. Si creás un inbox de otro tipo (API, Email, etc.), tenés que probar la comunicación por otros medios.

---

## Flujo completo: cuenta nueva + inbox + bot + widget test

```ruby
# 1. Crear cuenta
account = Account.create!(name: "Empresa de Prueba")

# 2. Crear inbox tipo Web Widget
web_widget = Channel::WebWidget.create!(
  account: account,
  website_url: 'https://ejemplo.com'
)
inbox = Inbox.create!(
  channel: web_widget,
  account: account,
  name: 'Soporte'
)

# 3. Vincular el Agent Bot
bot = AgentBot.find_by(name: "Mi AI Bot")
AgentBotInbox.create!(inbox: inbox, agent_bot: bot)

# 4. Mostrar datos para usar
puts "Account ID: #{account.id}"
puts "Inbox ID: #{inbox.id}"
puts "website_token: #{web_widget.website_token}"
```

Después abrí en el navegador:

```
http://localhost:3000/widget_tests?inbox_id=<INBOX_ID>
```

El bot va a responder usando el nombre de la cuenta ("Empresa de Prueba") en el system prompt, gracias a `get_account_name()` que busca dinámicamente el nombre de la cuenta desde la API de Chatwoot.

---

## Referencia rápida de comandos

### Rails console

```bash
cd chatwoot-server
bundle exec rails c
```

| Comando | Propósito |
|---------|-----------|
| `Inbox.all.each { \|i\| puts "\#{i.id} — \#{i.name} (\#{i.channel_type})" }` | Listar inboxes |
| `Channel::WebWidget.all.each { \|w\| puts w.inbox.id }` | Listar IDs de inboxes web widget |
| `Account.create!(name: "...")` | Crear cuenta |
| `Inbox.create!(channel: Channel::WebWidget.new(...), account: Account.find(N), name: "...")` | Crear inbox |
| `AgentBotInbox.create!(inbox: Inbox.find(N), agent_bot: AgentBot.last)` | Vincular bot a inbox |
| `AgentBot.last.inboxes` | Ver inboxes vinculados al bot |

### URLs de prueba

| URL | Propósito |
|-----|-----------|
| `http://localhost:3000/widget_tests` | Widget test (primer inbox) |
| `http://localhost:3000/widget_tests?inbox_id=2` | Widget test con inbox específico |
| `http://localhost:3000/super_admin` | Panel Super Admin |
| `http://localhost:3000` | Login / Dashboard |

### curl

| Comando | Propósito |
|---------|-----------|
| `curl -s .../api/v1/accounts/1/inboxes` | Listar inboxes via API |
| `curl -s -X POST .../api/v1/accounts` | Crear cuenta via API |
| `curl -s -X POST .../api/v1/widget/messages` | Enviar mensaje como contacto nuevo |

### Postman

Usar la colección `chatwoot-api-postman.json`. Los endpoints relevantes para testing:

| Endpoint | Propósito |
|----------|-----------|
| `GET List Inboxes` | Ver inboxes disponibles |
| `POST Create Contact` | Crear contacto nuevo |
| `POST Create Conversation` | Crear conversación |
| `POST Send Message` | Enviar mensaje |
