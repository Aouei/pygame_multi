# Diagramas

Esta sección contiene los diagramas de arquitectura del proyecto, generados con Mermaid.

El proyecto sigue **Clean Architecture** en cuatro capas: `domain/`, `use_cases/`, `adapters/`, `frameworks/`. Las capas internas nunca importan las externas.

- **[Clases](clases.md)** — relaciones entre todas las clases organizadas por capa
- **[Paso de Mensajes](mensajes.md)** — secuencias de comunicación WebSocket y flujo de `GameSnapshot`
- **[Estados y Condiciones](estados.md)** — diagrama de estados del cliente y servidor
- **[ServerSession & ClientSession](server-client.md)** — análisis profundo de la separación servidor/cliente
