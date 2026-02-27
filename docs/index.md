# Pygame Multi

Juego multijugador 2D en tiempo real construido con **Python + Pygame + WebSockets**.

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| Renderizado | Pygame |
| Red | websockets (asyncio) |
| Servidor | Python asyncio |
| Mapa / Colisiones | Pandas (CSV) + SciPy KDTree |
| Build | PyInstaller |

## Arquitectura general

El sistema sigue un modelo **cliente-servidor autoritativo**: el servidor es la única fuente de verdad sobre las posiciones de los jugadores. Los clientes envían *intenciones* de movimiento y el servidor decide si son válidas.

```mermaid
graph LR
    subgraph SERVER["Servidor (server.py)"]
        S[Server] --> SS[ServerState]
        SS --> MAP_S[Map — autoridad]
        SS --> PL[Players dict]
    end

    subgraph CLIENT_A["Cliente A (client.py)"]
        CA[Client] --> CSA[ClientState]
        CSA --> MAP_CA[Map — render]
        CA --> INA[InputHandler]
    end

    subgraph CLIENT_B["Cliente B (client.py)"]
        CB[Client] --> CSB[ClientState]
        CB --> INB[InputHandler]
    end

    INA -->|WISH_MOVE| S
    INB -->|WISH_MOVE| S
    S -->|PLAYERS_UPDATE broadcast| CA
    S -->|PLAYERS_UPDATE broadcast| CB
```

## Flujo de vida de una sesión

```mermaid
stateDiagram-v2
    [*] --> Lobby : iniciar client.exe
    Lobby --> Conectando : seleccionar clase
    Conectando --> EnPartida : recibir HELLO
    EnPartida --> EnPartida : loop 60fps + recv async
    EnPartida --> [*] : quit o desconexion
```

## Módulos del proyecto

| Archivo | Responsabilidad |
|---|---|
| `server.py` | Entry-point servidor, WebSocket listener, broadcast loop |
| `client.py` | Entry-point cliente, render loop, conexión WS |
| `states.py` | `ServerState` (lógica) y `ClientState` (render) |
| `messages.py` | Funciones de serialización JSON de cada mensaje |
| `enums.py` | `PLAYER_CLASS`, `STATE`, `MESSAGES` |
| `entities/player.py` | `Player` y `Bullet` |
| `maps.py` | `Map` — carga CSV, colisiones KDTree, minimap |
| `factories.py` | Carga de sprites y tiles desde disco |
| `inputs.py` | `InputHandler` — teclado y mando |
| `levels/lobby.py` | Pantalla de selección de personaje |
| `paths.py` | Rutas de assets (compatible PyInstaller) |

## Navegación

- **[Diagramas de Clases](diagramas/clases.md)** — jerarquía completa de clases
- **[Paso de Mensajes](diagramas/mensajes.md)** — secuencias WebSocket y formato JSON
- **[ServerState & ClientState](diagramas/server-client.md)** — diseño e interacción en profundidad
