# Chatwoot API Integration — Documentación

Proyecto para integrar un Agent Bot AI con Chatwoot usando su API REST. Contiene la configuración necesaria para correr Chatwoot localmente, un bot funcional (`test-bot.py`) con múltiples proveedores AI, y toda la documentación del flujo de integración.

## Archivos de Documentación

La wiki está dividida en tres archivos para facilitar la navegación:

| Archivo | Contenido |
|---------|-----------|
| [wiki/general.md](wiki/general.md) | **Información General** — Flujo de integración, qué necesita un Agent Bot, endpoints, estructura de datos (Message/Conversation), contexto de conversación para AI, tipos de mensaje |
| [wiki/setup.md](wiki/setup.md) | **Instalación de Chatwoot Local** — Guía paso a paso para correr Chatwoot sin Docker (PostgreSQL + Redis en Docker), creación de Agent Bot, errores de instalación y soluciones, modificaciones realizadas |
| [wiki/bot.md](wiki/bot.md) | **Implementación del Bot** — Cómo correr test-bot.py, explicación del código (fetch_history, handle_openai, handle_ollama), modos del agente, variables de entorno, proyecto C# (.NET 10) de referencia |

## Archivos del Proyecto

| Archivo | Propósito |
|---------|-----------|
| `test-bot.py` | Bot principal (Flask, multi-provider, contexto de conversación, doble token) |
| `.env.example` | Ejemplo de configuración con todas las variables documentadas |
| `chatwoot-api-postman.json` | Colección de Postman con 13 endpoints organizados por categoría |
| `chatwoot-server/` | Repositorio de Chatwoot (submódulo git, no modificar código fuente) |
| `implementation-examples/` | Ejemplos adicionales (Rasa, LangChain, etc.) |

## Resumen Rápido

```
Cliente → Chatwoot (webhook) → Bot (AI) → Chatwoot (API) → Cliente
```

1. Chatwoot corre en `localhost:3000`
2. El bot corre en `127.0.0.1:8000`
3. Chatwoot envía mensajes entrantes al bot via webhook POST
4. El bot procesa con AI (Groq/Ollama/OpenAI) y responde via API de Chatwoot
5. Usa dos tokens: Agent Bot token (escribir) + Personal Access Token de usuario (leer historial)

Ver [Información General → Resumen del Flujo](wiki/general.md#resumen-del-flujo) para más detalle.
