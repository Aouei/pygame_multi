# Documentación de Comunicación Cliente-Servidor

Este proyecto utiliza una arquitectura cliente-servidor para gestionar la lógica del juego y la interacción entre los jugadores. A continuación se describen los pasos y mensajes clave intercambiados entre el cliente y el servidor.

## Índice
- [Introducción](#introducción)
- [Arquitectura General](#arquitectura-general)
- [Flujo de Mensajes](#flujo-de-mensajes)
- [Ejemplo de Secuencia](#ejemplo-de-secuencia)
- [Referencias](#referencias)

## Introducción
El sistema está compuesto por un cliente (jugador) y un servidor (gestor del juego). Ambos se comunican mediante mensajes estructurados, generalmente en formato JSON, a través de sockets.

## Arquitectura General
```mermaid
graph TD
    Cliente --&gt; Servidor: Enviar acción del jugador
    Servidor --&gt; Cliente: Actualización del estado del juego
```

## Flujo de Mensajes
1. **Conexión Inicial**
    - El cliente se conecta al servidor.
    - El servidor responde con un mensaje de bienvenida o estado inicial.

2. **Envío de Acciones**
    - El cliente envía mensajes con las acciones del jugador (moverse, atacar, etc.).
    - Ejemplo:
      ```json
      {
        "type": "action",
        "action": "move",
        "direction": "up"
      }
      ```

3. **Procesamiento en el Servidor**
    - El servidor recibe la acción, actualiza el estado del juego y genera una respuesta.

4. **Actualización del Estado**
    - El servidor envía al cliente el nuevo estado del juego o eventos relevantes.
    - Ejemplo:
      ```json
      {
        "type": "state_update",
        "players": [...],
        "entities": [...],
        "events": [...]
      }
      ```

5. **Desconexión**
    - El cliente puede enviar un mensaje de desconexión.
    - El servidor limpia los recursos asociados.

## Ejemplo de Secuencia
```mermaid
sequenceDiagram
    participant C as Cliente
    participant S as Servidor
    C-&gt;>S: Conexión
    S-->>C: Estado inicial
    C-&gt;>S: Acción (mover)
    S-->>C: Actualización de estado
    C-&gt;>S: Acción (atacar)
    S-->>C: Actualización de estado
    C-&gt;>S: Desconexión
    S-->>C: Confirmación
```

## Referencias
- [Documentación oficial de Python sockets](https://docs.python.org/3/library/socket.html)
- [MkDocs](https://www.mkdocs.org/)
