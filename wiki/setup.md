# Instalación y Configuración de Chatwoot Local

Esta guía explica cómo ejecutar Chatwoot localmente **sin Docker** (modo desarrollo local), usando solo Docker para los servicios de infraestructura (PostgreSQL y Redis).

- [Prerrequisitos](#prerrequisitos)
- [Paso 1: Infraestructura con Docker](#paso-1-infraestructura-con-docker-postgresql--redis)
- [Paso 2: Configurar variables de entorno](#paso-2-configurar-variables-de-entorno)
- [Paso 3: Instalar Ruby 3.4.4](#paso-3-instalar-ruby-344)
- [Paso 4: Instalar dependencias Ruby](#paso-4-instalar-dependencias-ruby-bundler)
- [Paso 5: Instalar pnpm y dependencias frontend](#paso-5-instalar-pnpm-y-dependencias-frontend)
- [Paso 6: Configurar la base de datos](#paso-6-configurar-la-base-de-datos)
- [Paso 7: Iniciar Chatwoot](#paso-7-iniciar-chatwoot)
- [Paso 7.5: Compilar el SDK del Widget](#paso-75-compilar-el-sdk-del-widget-obligatorio)
- [Paso 8: Verificar que funciona](#paso-8-verificar-que-funciona)
- [Crear un Agent Bot en Chatwoot](#crear-un-agent-bot-en-chatwoot)
- [Errores de Instalación y Soluciones](#errores-de-instalación-y-soluciones)
- [Modificaciones a Chatwoot](#modificaciones-a-chatwoot)

**Archivos relacionados:**
- [Información General](general.md) — flujo de integración, endpoints, estructuras de datos
- [Implementación del Bot](bot.md) — cómo correr test-bot.py, variables, modos

---

## Prerrequisitos

| Herramienta | Versión | Cómo verificar |
|-------------|---------|---------------|
| Ruby | 3.4.4 | `ruby --version` |
| Node.js | >= 18 | `node --version` |
| pnpm | >= 8 | `pnpm --version` |
| PostgreSQL | 16+ | `psql --version` |
| Redis | 6+ | `redis-cli ping` |
| rbenv | - | `rbenv --version` |

---

## Paso 1: Infraestructura con Docker (PostgreSQL + Redis)

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
> **Importante:** Si usas `docker compose up -d postgres redis mailhog`, el PostgreSQL del compose usa el puerto **5432** por defecto. Configura `POSTGRES_PORT=5432` en ese caso.

---

## Paso 2: Configurar variables de entorno

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

---

## Paso 3: Instalar Ruby 3.4.4

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

---

## Paso 4: Instalar dependencias Ruby (Bundler)

```bash
cd chatwoot-server
gem install bundler
bundle install
```

> **Solución de errores comunes:**
> - `Gem::Ext::BuildError`: instala paquetes faltantes con `sudo apt install build-essential libpq-dev libssl-dev libreadline-dev zlib1g-dev libyaml-dev`
> - Si falla `pg` gem: `sudo apt install libpq-dev`

---

## Paso 5: Instalar pnpm y dependencias frontend

```bash
# Instalar pnpm globalmente si no lo tienes
npm install -g pnpm

cd chatwoot-server
pnpm install
```

---

## Paso 6: Configurar la base de datos

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

---

## Paso 7: Iniciar Chatwoot

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

---

## Paso 7.5: Compilar el SDK del Widget (obligatorio)

El widget de Chatwoot tiene un SDK separado que **no se compila automáticamente** con `vite:dev`. Hay que buildearlo manualmente.

```bash
cd chatwoot-server

# Asegurar permisos
sudo chown -R $USER:$USER public/packs
# Si no tenes sudo: rm -rf public/packs && mkdir -p public/packs/js

# Compilar SDK
pnpm run build:sdk
```

---

## Paso 8: Verificar que funciona

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
bot = AgentBot.create!(name: "Mi AI Bot", outgoing_url: "http://127.0.0.1:8000/webhook")
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

> Si usas `docker compose up -d postgres`, PostgreSQL queda en puerto **5432**. Si creaste el contenedor manualmente con `docker run -p 5433:5432`, usa el **5433**. Siempre verifica con `docker ps`.

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

**Solución:** No requiere acción. Se puede ignorar.

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

### Error 9: El bot responde a veces sí y a veces no ("Connection refused ::1")

**Síntoma:** El bot funciona intermitentemente. En el log de Chatwoot aparece:
```
Failed to open TCP connection to ::1:8000 (Connection refused)
```

**Causa:** `localhost` resuelve a veces a IPv4 (`127.0.0.1`) y a veces a IPv6 (`::1`). Si el bot solo escucha en IPv4, la conexión por IPv6 falla.

**Solución:** Cambiar el `outgoing_url` del Agent Bot para que use `127.0.0.1` explícitamente:

```bash
cd chatwoot-server
bundle exec rails runner "
bot = AgentBot.find_by(name: 'Mi AI Bot')
bot.update!(outgoing_url: 'http://127.0.0.1:8000/webhook')
puts 'OK: ' + bot.outgoing_url
"
```

Luego reiniciar overmind para que tome el cambio.

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
