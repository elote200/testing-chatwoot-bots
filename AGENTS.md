# Contexto del Proyecto: Testing Chatwoot API BotsAgents

## Descripción
El objetivo de este proyecto es para crear una documentacion/proof of concepts sobre la API de chatwoot para conectar un Agente que funcionaria como un bot. La idea es simular el flujo de un servidor que esta corriendo chatwoot y otro que esta corriendo un agente AI que simplemente recibe consultas atraves de la API de chatwoot y este agente le responde atraves de la API de chatwoot. Y documentar todo esto, mas precisamente cuales son las APIs, que necesita el Agente AI para poder conectar a la API de chatwoot.

El agenta puede simplemente utilizar un modelo de ollama que esta corriendo localmente o setear una API KEY desde .env de un proveedor y su respectivo modelo. Es algo simple que conteste algunas preguntas muy generales.

## Stack Tecnológico
- Lenguaje: C# 
- Framework: .NET 10
- Otras herramientas: Repositorio Chatwoot:https://github.com/chatwoot/chatwoot

## Reglas / Estilo
- "Prefiero funciones puras", "Usar nombres en inglés", "Cero comentarios redundantes"
- Todo la documentacion necesaria va en un archivo llamado WIKI.md
- Una carpeta para correr independientemente chatwoot y otra para correr el agente.
- No tocar NADA del codigo de chatwoot simplemente para correrlo como esta el modelo.

## Objetivo Final
- Wiki detallada sobre como conectar un Bot Agente AI propio a Chatwoot y que este funcional al 100%.
- Wiki que detalla que cosas espera chatwoot, que cosas necesita el agente para poder conectarse a chatwoot, etc.
- Un flujo de desarrollo/implementacion para un agente que se va a conectar a chatwoot

