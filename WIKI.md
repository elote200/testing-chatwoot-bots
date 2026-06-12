# Chatwoot API Integration Wiki

## Índice

- [Resumen del Flujo](#resumen-del-flujo)
- [¿Qué necesita un Agent Bot?](#qué-necesita-un-agent-bot)
- [Endpoints de la Integración](#endpoints-de-la-integración)
- [Guía de Instalación: Chatwoot sin Docker](#guía-de-instalación-chatwoot-sin-docker)
- [Crear un Agent Bot en Chatwoot](#crear-un-agent-bot-en-chatwoot)
- [Correr las Implementaciones de Ejemplo](#correr-las-implementaciones-de-ejemplo)
- [Errores de Instalación y Soluciones](#errores-de-instalación-y-soluciones)
- [Modificaciones a Chatwoot](#modificaciones-a-chatwoot)
- [Configuración del Proyecto C# (.NET 10) para el Bot Agent](#configuración-del-proyecto-c-net-10-para-el-bot-agent)

---

## Resumen del Flujo

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────────────┐
│   Cliente    │     │   Chatwoot       │     │   Agent Bot          │
│  (Widget)    │────>│  (localhost:3000) │────>│  (localhost:8000)    │
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
Chatwoot genera un token único para cada Agent Bot. Se obtiene desde la consola de Rails:

```ruby
bot = AgentBot.create!(name: "Mi Bot", outgoing_url: "http://...")
bot.access_token.token
# => "x3ZqMmuo6RZbdJiWdXNjiFmF"
```

Este token se usa como `api_access_token` en los headers para autenticar las llamadas a la API de Chatwoot.

### 3. Outgoing URL
La URL que Chatwoot va a llamar cuando llegue un mensaje. Se define al crear el Agent Bot:

```ruby
outgoing_url: "http://localhost:8000/webhook"
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
│  └── Outgoing:  http://localhost:8000/webhook            │
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
│  router (localhost:8000)                                 │
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

---

## Guía de Instalación: Chatwoot sin Docker

Esta guía explica cómo ejecutar Chatwoot localmente **sin Docker** (modo desarrollo local), usando solo Docker para los servicios de infraestructura (PostgreSQL y Redis). Esto es necesario para que los agentes bots puedan comunicarse con Chatwoot a través de `localhost`.

### Prerrequisitos

| Herramienta | Versión | Cómo verificar |
|-------------|---------|---------------|
| Ruby | 3.4.4 | `ruby --version` |
| Node.js | >= 18 | `node --version` |
| pnpm | >= 8 | `pnpm --version` |
| PostgreSQL | 16+ | `psql --version` |
| Redis | 6+ | `redis-cli ping` |
| rbenv | - | `rbenv --version` |

### Paso 1: Infraestructura con Docker (PostgreSQL + Redis)

Solo PostgreSQL y Redis corren en Docker. Chatwoot corre localmente.

```bash
# Opción A: Usar docker-compose solo para los servicios
cd chatwoot-server
docker compose up -d postgres redis mailhog

# Opción B: PostgreSQL manual con port mapping
docker run -d \
  --name chatwoot-postgres \
  -e POSTGRES_DB=chatwoot_dev \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5433:5432 \
  pgvector/pgvector:pg16

# Redis (usar el que ya está corriendo o iniciar uno)
docker run -d \
  --name chatwoot-redis \
  -p 6379:6379 \
  redis:alpine
```

> **Nota de puertos:** Si ya tienes PostgreSQL en el puerto 5432, usa el 5433. Luego configura `POSTGRES_PORT=5433` en el `.env`.
>
> ⚠️ **Importante:** Si usas `docker compose up -d postgres redis mailhog`, el PostgreSQL del compose usa el puerto **5432** por defecto. Configura `POSTGRES_PORT=5432` en ese caso.

### Paso 2: Configurar variables de entorno

```bash
cd chatwoot-server
cp .env.example .env
```

Edita `.env` con estos valores clave:

```env
# Database - apuntando a localhost
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_USERNAME=postgres
POSTGRES_PASSWORD=postgres
RAILS_MAX_THREADS=5

# Redis local
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=

# Chatwoot
FRONTEND_URL=http://localhost:3000
RAILS_ENV=development
SECRET_KEY_BASE=your_secret_key_here_min_30_chars
ENABLE_ACCOUNT_SIGNUP=true
FORCE_SSL=false

# Permitir webhooks a localhost (necesario para Agent Bots locales)
# Sin esto, Chatwoot bloquea los webhooks a localhost/127.0.0.1 por seguridad SSRF
SAFE_FETCH_ALLOW_PRIVATE_NETWORK=true
```

### Paso 3: Instalar Ruby 3.4.4

```bash
# Instalar rbenv si no lo tienes
git clone https://github.com/rbenv/rbenv.git ~/.rbenv
git clone https://github.com/rbenv/ruby-build.git ~/.rbenv/plugins/ruby-build

# Agregar rbenv al PATH
echo 'export PATH="$HOME/.rbenv/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(rbenv init -)"' >> ~/.bashrc
source ~/.bashrc

# Instalar Ruby 3.4.4
rbenv install 3.4.4
rbenv local 3.4.4    # dentro de chatwoot-server/
ruby --version       # debe mostrar 3.4.4
```

> **Tiempo estimado:** 5-15 minutos. Ruby se compila desde fuente.

### Paso 4: Instalar dependencias Ruby (Bundler)

```bash
cd chatwoot-server
gem install bundler
bundle install
```

> **Solución de errores comunes:**
> - `Gem::Ext::BuildError`: instala paquetes faltantes con `sudo apt install build-essential libpq-dev libssl-dev libreadline-dev zlib1g-dev libyaml-dev`
> - Si falla `pg` gem: `sudo apt install libpq-dev`

### Paso 5: Instalar pnpm y dependencias frontend

```bash
# Instalar pnpm globalmente si no lo tienes
npm install -g pnpm

cd chatwoot-server
pnpm install
```

### Paso 6: Configurar la base de datos

```bash
cd chatwoot-server

# Crear la base de datos
bundle exec rails db:create

# Ejecutar migraciones
bundle exec rails db:migrate

# Sembrar datos de prueba (opcional pero recomendado)
bundle exec rails db:seed
```

> **Nota:** `db:seed` crea una cuenta de prueba, inbox y datos básicos.

### Paso 7: Iniciar Chatwoot

Chatwoot necesita 3 procesos: Rails server, Vite (frontend), y Sidekiq (background jobs).

```bash
# Desde chatwoot-server/, en 3 terminales distintas:

# Terminal 1 - Rails API + Web
bundle exec rails s -b 0.0.0.0 -p 3000

# Terminal 2 - Frontend (Vite)
pnpm run vite:dev

# Terminal 3 - Sidekiq (procesamiento en segundo plano)
bundle exec sidekiq
```

O usa `overmind` (recomendado):

```bash
# Instalar overmind
gem install overmind

# Iniciar todo
overmind start -f ./Procfile.dev
```

### Paso 7.5: Compilar el SDK del Widget (obligatorio)

El widget de Chatwoot tiene un SDK separado que **no se compila automáticamente** con `vite:dev`. Hay que buildearlo manualmente.

```bash
cd chatwoot-server

# Asegurar permisios
sudo chown -R $USER:$USER public/packs
# Si no tenes sudo: rm -rf public/packs && mkdir -p public/packs/js

# Compilar SDK
pnpm run build:sdk
```

### Paso 8: Verificar que funciona

1. Abre `http://localhost:3000` en el navegador
2. Deberías ver la página de login de Chatwoot
3. Si ejecutaste `db:seed`, las credenciales por defecto son:
   - **URL:** `http://localhost:3000`
   - **Email:** Revisa la salida del seed (usualmente `admin@chatwoot.com` o similar)
   - **Password:** `Password1!`

---

## Crear un Agent Bot en Chatwoot

Una vez que Chatwoot está corriendo, necesitas crear un Agent Bot para que tu agente AI pueda conectarse.

### Paso 1: Obtener un Access Token de Agent Bot

Abre la consola de Rails:

```bash
cd chatwoot-server
bundle exec rails c
```

Dentro de la consola, ejecuta:

```ruby
bot = AgentBot.create!(name: "Mi AI Bot", outgoing_url: "http://localhost:8000/webhook")
bot.access_token.token
# => "tu_token_generado"
```

Guarda ese token. Es lo que el agente usará para autenticarse.

### Paso 2: Conectar el Agent Bot a un Inbox

```ruby
# En la misma consola de Rails:
inbox = Inbox.first
bot = AgentBot.last
AgentBotInbox.create!(inbox: inbox, agent_bot: bot)
```

### Paso 3: Obtener IDs necesarios

```ruby
Account.first.id          # account_id (usualmente 1)
Inbox.first.id            # inbox_id
```

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

### Formas alternativas de iniciar

#### Sin .env (variables inline)

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

#### En background (para no ocupar la terminal)

```bash
nohup python3 test-bot.py > bot.log 2>&1 &
```

#### Con gunicorn (produccion)

```bash
source .venv/bin/activate
pip install gunicorn
python3 -m gunicorn --workers=1 test-bot:app -b 0.0.0.0:8000
```

---

### Modos del agente

| Modo | `AGENT_MODE=` | ¿Qué hace? |
|------|--------------|------------|
| `direct` | `direct` | Responde inline (para pruebas, default) |
| `openai` | `openai` | OpenAI, Groq, Google Gemini, etc. |
| `ollama` | `ollama` | Modelo local con Ollama |

### Variables de entorno

| Variable | Default | Descripción |
|---|---|---|
| `CHATWOOT_URL` | `http://localhost:3000` | Chatwoot server base URL |
| `CHATWOOT_BOT_TOKEN` | `x3ZqMmuo6RZbdJiWdXNjiFmF` | Agent Bot API token |
| `AGENT_MODE` | `direct` | Backend mode: `direct`, `openai`, or `ollama` |
| `OPENAI_URL` | `https://api.openai.com/v1` | Base URL del API (OpenAI, Groq, Gemini, etc.) |
| `OPENAI_API_KEY` | *(requerido en openai mode)* | API key del proveedor |
| `OPENAI_MODEL` | `gpt-4o-mini` | Modelo a usar |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.2` | Ollama model name |
| `PORT` | `8000` | Puerto donde corre el bot |

---

### Otras implementaciones

En `implementation-examples/` hay ejemplos adicionales (Rasa, LangChain, etc.) como referencia para arquitecturas más complejas, pero el `test-bot.py` raíz es suficiente para el caso de uso principal.

---

## Errores de Instalación y Soluciones

Todos los errores que encontramos durante la instalación local, junto con sus soluciones.

### Error 1: Ruby no compila — `psych: Could not be configured`

**Error:**
```
*** Following extensions are not compiled:
psych:
Could not be configured. It will not be installed.
BUILD FAILED
```

**Causa:** Falta `libyaml-dev` en el sistema. La gema `psych` (parser YAML de Ruby) necesita esta librería para compilarse. Sin YAML, Rails no arranca.

**Solución:**
```bash
sudo apt install -y libyaml-dev libffi-dev libgmp-dev
# Luego limpiar y reinstalar
rbenv uninstall 3.4.4
rbenv install 3.4.4
```

**Dependencias completas recomendadas antes de instalar Ruby:**
```bash
sudo apt install -y \
  build-essential \
  libssl-dev \
  libreadline-dev \
  zlib1g-dev \
  libyaml-dev \
  libffi-dev \
  libgmp-dev \
  libpq-dev \
  libcurl4-openssl-dev
```

---

### Error 2: `Errno::EACCES: Permission denied @ rb_sysopen - log/development.log`

**Error:**
```
Errno::EACCES: Permission denied @ rb_sysopen - .../chatwoot-server/log/development.log
```

**Causa:** La carpeta `log/` no existe o no tiene permisos de escritura. Rails intenta crear/abrir el archivo de log y falla.

**Solución:**
```bash
cd chatwoot-server
mkdir -p log tmp public/assets public/packs
chmod -R u+w log tmp
```

---

### Error 3: `Connection refused` a PostgreSQL

**Error:**
```
connection to server at "127.0.0.1", port 5433 failed: Connection refused
Is the server running on that host and accepting TCP/IP connections?
Couldn't create 'chatwoot_dev' database.
```

**Causa:** El contenedor de PostgreSQL se detuvo, se eliminó, o el puerto configurado en `.env` no coincide con el puerto real del contenedor. Esto pasa típicamente cuando:
- Docker reinicia y los contenedores personalizados se pierden
- Se usa `docker compose` que levanta PostgreSQL en un puerto diferente al configurado

**Solución:**
```bash
# Verificar contenedores activos
docker ps --format "table {{.Names}}\t{{.Ports}}\t{{.Status}}"

# Verificar que PostgreSQL responde en el puerto correcto
PGPASSWORD=postgres psql -h localhost -p 5432 -U postgres -c "SELECT 1"

# Ajustar .env al puerto correcto (comúnmente 5432 o 5433)
# POSTGRES_PORT=5432  ó  POSTGRES_PORT=5433
```

> ⚠️ Si usas `docker compose up -d postgres`, PostgreSQL queda en puerto **5432**. Si creaste el contenedor manualmente con `docker run -p 5433:5432`, usa el **5433**. Siempre verifica con `docker ps`.

---

### Error 4: `uninitialized constant ActsAsTaggableOn::Taggable::Cache`

**Error al ejecutar `db:migrate`:**
```
uninitialized constant ActsAsTaggableOn::Taggable::Cache
Did you mean?  CacheKeys
db/migrate/20231211010807_add_cached_labels_list.rb:5:in 'AddCachedLabelsList#change'
```

**Causa:** La gema `acts-as-taggable-on` se actualizó a v12, que eliminó el módulo `ActsAsTaggableOn::Taggable::Cache`. Una migration vieja de Chatwoot (del 2023) intenta usarlo.

**Solución (modificar el archivo de migration):**

Editar `db/migrate/20231211010807_add_cached_labels_list.rb` y eliminar la línea del Cache:

```ruby
# Antes (roto):
class AddCachedLabelsList < ActiveRecord::Migration[7.0]
  def change
    add_column :conversations, :cached_label_list, :string
    Conversation.reset_column_information
    ActsAsTaggableOn::Taggable::Cache.included(Conversation)  # <-- esta línea falla
  end
end

# Después (arreglado):
class AddCachedLabelsList < ActiveRecord::Migration[7.0]
  def change
    add_column :conversations, :cached_label_list, :string
  end
end
```

**¿Por qué es seguro?** La línea eliminada solo inicializaba un concern de cache tagging que ya no existe en la gema v12. La columna `cached_label_list` se agrega correctamente, y el modelo `Conversation` maneja el etiquetado por sí mismo.

---

### Error 5: Warning de `fiddle` — librería estándar obsoleta

**Warning:**
```
warning: .../fiddle.rb was loaded from the standard library,
but will no longer be part of the default gems starting from Ruby 3.5.0.
```

**Causa:** La gema `reline-0.3.6` usa `fiddle` que viene en la stdlib pero será eliminada en Ruby 3.5. Es solo un **warning**, no un error.

**Solución:** No requiere acción. Se puede ignorar. Para silenciarlo en el futuro, se puede agregar `gem 'fiddle'` al Gemfile de Chatwoot, pero no es necesario para el funcionamiento.

---

### Error 6: Base de datos no existe en `db:seed`

**Error:**
```
ActiveRecord::NoDatabaseError: We could not find your database: chatwoot_dev
```

**Causa:** No se ejecutó `db:create` o `db:migrate` antes de `db:seed`.

**Solución:**
```bash
# El orden correcto es:
bundle exec rails db:create
bundle exec rails db:migrate
bundle exec rails db:seed
```

---

### Error 7: `address already in use` al iniciar servicios

**Error:**
```
ERROR: for postgres  Cannot start service postgres: driver failed programming external connectivity...
Error starting userland proxy: listen tcp4 0.0.0.0:5432: bind: address already in use
```

**Causa:** Otro servicio (como `knowledge-postgres` u otra instancia de PostgreSQL) ya está usando el puerto 5432.

**Solución:**
```bash
# Identificar qué está usando el puerto
sudo lsof -i :5432

# Opción A: Detener el otro servicio
docker stop knowledge-postgres

# Opción B: Usar un puerto diferente (ej: 5433) creando el contenedor manualmente
docker run -d --name chatwoot-postgres -e POSTGRES_DB=chatwoot_dev \
  -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres \
  -p 5433:5432 pgvector/pgvector:pg16
# Y configurar POSTGRES_PORT=5433 en el .env
```

---

### Error 8: Webhook bloqueado por SSRF filter

**Problema:** El bot recibe el webhook pero Sidekiq registra `Invalid webhook URL http://localhost:8000/webhook`.

**Causa:** Chatwoot tiene un filtro SSRF (`lib/safe_fetch.rb`) que bloquea conexiones a direcciones de red privada (`localhost`, `127.0.0.1`, `10.x.x.x`, etc.) por seguridad. En producción esto es correcto, pero en desarrollo local necesitamos deshabilitarlo.

**Solución:** Agregar al `.env`:
```env
SAFE_FETCH_ALLOW_PRIVATE_NETWORK=true
```

Luego reiniciar overmind (`Ctrl+C` y `overmind start -f ./Procfile.dev`).

---

## Modificaciones a Chatwoot

Para que Chatwoot funcione correctamente en entorno local sin Docker, se modificaron estos archivos. Si clonas el repo en otra máquina, tendrás que aplicar los mismos cambios.

### 1. `chatwoot-server/.env` — Configuración local

**Cambios respecto al `.env.example` original:**

| Variable | Valor original (Docker) | Valor modificado (local) |
|----------|------------------------|--------------------------|
| `POSTGRES_HOST` | `postgres` | `localhost` |
| `POSTGRES_PORT` | *(no definido)* | `5432` (o `5433` según el puerto) |
| `POSTGRES_USERNAME` | `postgres` | `postgres` |
| `POSTGRES_PASSWORD` | *(vacío)* | `postgres` |
| `REDIS_URL` | `redis://redis:6379` | `redis://localhost:6379` |
| `ENABLE_ACCOUNT_SIGNUP` | `false` | `true` (para desarrollo) |
| `SAFE_FETCH_ALLOW_PRIVATE_NETWORK` | *(no existe)* | `true` (para webhooks locales) |

Además se quitaron variables que apuntaban a servicios Docker como `SMTP_ADDRESS=mailhog`.

### 2. `chatwoot-server/db/migrate/20231211010807_add_cached_labels_list.rb` — Parche de migration

**Archivo:** `db/migrate/20231211010807_add_cached_labels_list.rb`

**Cambio:** Se eliminó la línea `ActsAsTaggableOn::Taggable::Cache.included(Conversation)`.

**Razón:** La gema `acts-as-taggable-on` v12 eliminó el módulo `Cache`. Sin este cambio, `bundle exec rails db:migrate` falla con `uninitialized constant ActsAsTaggableOn::Taggable::Cache`.

**Cómo aplicar el mismo cambio en una máquina nueva:**
```bash
# Después de clonar el repo, editar la migration
nano db/migrate/20231211010807_add_cached_labels_list.rb
# Eliminar la línea 5 (ActsAsTaggableOn::Taggable::Cache.included(Conversation))
```

O puedes aplicar este parche vía sed:
```bash
sed -i '/ActsAsTaggableOn::Taggable::Cache.included/d' \
  db/migrate/20231211010807_add_cached_labels_list.rb
```

### 3. Sin cambios en el código de Chatwoot

No se modificó ningún archivo de la aplicación (modelos, controladores, vistas, etc.). Solo el `.env` y la migration mencionada. Como indica la regla del proyecto: **no tocar el código de Chatwoot**.

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

---

## Últimas Actualizaciones

- **2024-01-01**: Documentación inicial creada
- **2025-06-11**: Agregada guía de instalación Chatwoot sin Docker, Agent Bots, y ejemplos
- **Versión Chatwoot API:** v1
- **Última revisión:** 2025-06-11
