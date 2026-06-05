# Lista de Tareas

## Completadas ✅
- [ ] Clonar repositorio de Chatwoot
- [ ] Configurar archivo .env para desarrollo
- [ ] Crear estructura base de carpetas
- [ ] Verificar Docker/Docker Compose disponible
- [ ] Crear SETUP_GUIDE.md
- [ ] Inicializar proyecto .NET 10 Web API
- [ ] Crear estructura de carpetas (Services, Controllers, Dto, Configuration)
- [ ] Agregar dependencias (Refit, Serilog)
- [ ] Implementar cliente HTTP (IChatwootClient)
- [ ] Crear DTOs para modelos de Chatwoot
- [ ] Implementar AgentService
- [ ] Crear ConversationsController
- [ ] Configurar Program.cs con DI
- [ ] Crear WIKI.md con documentación completa de APIs
- [ ] Crear README.md para agent-service

## En proceso 🚀
- [ ] Resolver Docker/Podman socket
- [ ] Testing contra Chatwoot real

## Próximas tareas
- [ ] Implementar webhook receiver desde Chatwoot
- [ ] Agregar integración con modelo AI (Ollama)
- [ ] Agregar integración con OpenAI API
- [ ] Crear tests unitarios para AgentService
- [ ] Implementar caché de conversaciones (Redis)
- [ ] Agregar procesamiento de eventos en tiempo real
- [ ] Implementar flujo de procesamiento de mensajes
- [ ] Crear dashboard/UI para monitoreo
- [ ] Documentar flujo end-to-end
- [ ] Crear ejemplos de integración

## Backlog (Ideas a futuro)
- [ ] Soporte para múltiples modelos AI
- [ ] Rate limiting y retry logic mejorado
- [ ] Base de datos para historial de conversaciones
- [ ] Sistema de templates para respuestas
- [ ] Análisis de sentimientos
- [ ] Enrutamiento inteligente de conversaciones
- [ ] Integración con sistemas CRM
- [ ] Dashboard de métricas y analíticas
- [ ] API para configuración dinámica
- [ ] Deployment en Kubernetes

## Notas Importantes
- El proyecto está estructurado para permitir desarrollo paralelo
- Chatwoot Server está configurado pero no corriendo (falta resolver socket de Docker)
- Agent Service está listo para probar sin Chatwoot (se puede mockear la API)
- Toda la documentación está centralizada en WIKI.md
