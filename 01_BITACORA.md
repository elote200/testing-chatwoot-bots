# Bitácora de Desarrollo

## Sesión [2026-06-03-Part1] - Inicialización del Proyecto
- **Qué hicimos:** 
  - Creadas carpetas base: `chatwoot-server` y `agent-service`
  - Clonado repositorio oficial de Chatwoot
  - Configurado archivo `.env` para desarrollo local
  - Creado `SETUP_GUIDE.md` con guía de configuración
  - Creado `DEVELOPMENT_SETUP.md` con plan alternativo
  - Creado `docker-compose.minimal.yml` para servicios únicamente
  - Docker/Podman verificado pero con limitaciones de socket
  - Documentados problemas y soluciones alternativas

- **Problemas encontrados:** 
  - Docker daemon/Podman socket no completamente disponible en el environment
  - EOF errors al intentar conectar con podman para pull de imágenes
  - Restricciones de permisos en sockets de podman

- **Decisiones tomadas:** 
  - Usar Docker Compose para Chatwoot (desarrollo + testing)
  - Mantener código original de Chatwoot sin modificaciones
  - Crear documentación centralizada en WIKI.md
  - Estrategia alternativa: Proceder sin Chatwoot corriendo en este momento
  - Enfoque: Desarrollar agente C# primero, testear con API mockeada

- **Pendientes para la próxima:**
  - Resolver problemas de Docker/Podman socket (posible: contactar admin/usar K3s)

---

## Sesión [2026-06-03-Part2] - Estructura del Agente C# .NET
- **Qué hicimos:** 
  - ✅ Inicializado proyecto .NET 10 Web API
  - ✅ Creada estructura de carpetas (Services, Controllers, Dto, Configuration)
  - ✅ Agregadas dependencias:
    - Refit 11.0.0 (cliente HTTP type-safe)
    - Serilog 4.3.1 (logging estructurado)
    - Serilog.AspNetCore 10.0.0 (integración)
  - ✅ Implementado cliente HTTP para Chatwoot API (IChatwootClient)
  - ✅ Creados DTOs para Conversation, Message, Contact, Inbox
  - ✅ Implementado AgentService con lógica de negocio
  - ✅ Creado ConversationsController con endpoints
  - ✅ Configurado Program.cs con inyección de dependencias
  - ✅ Creado WIKI.md completo con documentación de APIs (11KB)
  - ✅ Creado README.md con instrucciones de setup
  - ✅ Creado .env.example con variables de configuración

- **Problemas encontrados:** 
  - Ninguno significativo

- **Decisiones tomadas:** 
  - Usar Refit para cliente HTTP (mejor que HttpClient puro)
  - Implementar patrón Repository con IAgentService
  - Usar Serilog para logging estructurado
  - Configuración basada en appsettings + environment variables
  - Endpoints RESTful simples y directos

- **Pendientes para la próxima:**
  - Cuando Docker esté listo: Probar contra Chatwoot real
  - Implementar webhook receiver desde Chatwoot
  - Agregar integración con modelo AI (Ollama/OpenAI)
  - Crear tests unitarios
  - Implementar caché de conversaciones
  - Agregar procesamiento de eventos
