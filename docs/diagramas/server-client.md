# ServerState & ClientState

`ServerState` y `ClientState` son las dos clases centrales del proyecto.
Ambas viven en `src/states.py` y representan la **división de responsabilidades** entre la lógica autoritativa del servidor y el estado de renderizado del cliente.

---

## Resumen de responsabilidades

| Aspecto | `ServerState` | `ClientState` |
|---|---|---|
| **Proceso** | `server.py` | `client.py` |
| **Fuente de verdad** | Sí — posiciones canónicas | No — recibe datos del servidor |
| **Mapa** | Valida colisiones | Solo renderiza |
| **Jugadores** | `dict[id → Player]` con estado real | Plantillas por clase para dibujar |
| **Conexiones** | `dict[id → ClientConnection]` | — |
| **Input** | Nunca toca inputs | Indirecto via `Client` |
| **Pygame** | No renderiza nada | Dibuja todo en pantalla |
| **Mutación de Player** | `Player.move()` si válido | `player.move()` solo para posicionar sprite |

---

## ServerState — diseño en profundidad

### Diagrama de clases de ServerState

```mermaid
classDiagram
    direction TB

    class ServerState {
        +PLAYER_SIZE: int
        +TILE_SIZE: int
        +IDs: set
        +MAP: Map
        +players: dict
        +clients: dict
        +available_ids: list
        +new_player(socket) int
        +remove_player(id)
        +handle_message(id, data)
        +get_players() dict
        -set_player_class(id, data)
        -try_move(id, data)
    }

    class Map {
        +solid_tree: KDTree
        +spawn_tiles: list
        +spawn() tuple
        +is_collision(x, y, mask) bool
    }

    class Player {
        +player_class: PLAYER_CLASS
        +current_state: STATE
        +x: int
        +y: int
        +mask: Mask
        +move(new_x, new_y, state)
        +dump() dict
    }

    class ClientConnection {
        <<websockets>>
        +send(data)
        +recv()
    }

    ServerState o-- "1" Map : clase compartida
    ServerState *-- "0..4" Player : jugadores[id]
    ServerState *-- "0..4" ClientConnection : clientes[id]
    Map ..> Player : valida mask
```

### Gestión de IDs

`ServerState` mantiene un pool fijo de IDs `{0, 1, 2, 3}` (máximo 4 jugadores).
La propiedad `available_ids` calcula la diferencia entre el pool y las claves activas de `clients`.

```mermaid
flowchart LR
    A["IDs = {0,1,2,3}"] --> B{available_ids}
    C["clients.keys = {0,2}"] --> B
    B --> D["available = {1,3}"]
    D --> E["new_player toma el primero: 1"]
```

### Ciclo de vida de un jugador en el servidor

```mermaid
stateDiagram-v2
    [*] --> Conectado : new_player(socket) + HELLO
    Conectado --> Registrado : handle_message PLAYER_CLASS
    Registrado --> Registrado : handle_message WISH_MOVE
    Registrado --> [*] : remove_player(id) — finally
    Conectado --> [*] : remove_player(id) — finally
```

### Flujo de `handle_message`

```mermaid
flowchart TD
    A["handle_message(id, data)"] --> B["MESSAGES(data['type'])"]
    B --> C{tipo}
    C -->|PLAYER_CLASS| D["__set_player_class(id, data)"]
    C -->|WISH_MOVE| E["__try_move(id, data)"]

    D --> D1["PLAYER_CLASS(data['class'])"]
    D1 --> D2["players[id] = Player(type)"]
    D2 --> D3["MAP.spawn() → (x, y)"]
    D3 --> D4["players[id].move(x, y, STATE.DOWN)"]

    E --> E1["dx, dy, state = data[...]"]
    E1 --> E2["player = players[id]"]
    E2 --> E3["MAP.is_collision(x+dx, y+dy, player.mask)"]
    E3 -->|False| E4["player.move(x+dx, y+dy, state)"]
    E3 -->|True| E5["movimiento descartado"]
```

### `get_players()` — serialización del estado

El broadcast loop llama a `get_players()` cada 50ms para serializar el estado completo:

```python
# Equivalente a:
{
    0: { 'x': 320, 'y': 192, 'state': 'down', 'type_class': 'archer' },
    2: { 'x': 640, 'y': 448, 'state': 'right', 'type_class': 'mage' }
}
```

```mermaid
flowchart LR
    A["players: dict[int, Player]"] --> B["player.dump()"]
    B --> C["{'x', 'y', 'state', 'type_class'}"]
    C --> D["get_players() → dict completo"]
    D --> E["json.dumps → PLAYERS_UPDATE payload"]
    E --> F["broadcast a todos los clientes"]
```

---

## ClientState — diseño en profundidad

### Diagrama de clases de ClientState

```mermaid
classDiagram
    direction TB

    class ClientState {
        +MAP: Map
        +PLAYERS: dict
        +BULLETS: dict
        +COLORS: dict
        +draw_player(surface, dx, dy, data)
    }

    class Map {
        +width: int
        +height: int
        +draw(surface, position)
        +draw_mini(surface, dx, dy, points, px, py)
    }

    class Player {
        +states: dict
        +masks: dict
        +move(new_x, new_y, state)
        +draw(surface, dx, dy)
    }

    class Bullet {
        +image: Surface
        +draw(surface, dx, dy)
    }

    class PLAYER_CLASS {
        <<enumeration>>
        ARCHER
        FARMER
        MAGE
        MUSKETEER
    }

    ClientState o-- "1" Map
    ClientState *-- "4" Player : PLAYERS[PLAYER_CLASS]
    ClientState *-- "4" Bullet : BULLETS[PLAYER_CLASS]
    Player --> PLAYER_CLASS
    Bullet --> PLAYER_CLASS
```

### Atributos de clase vs. instancia

!!! note "Atributos de clase compartidos"
    `MAP`, `PLAYERS`, `BULLETS` y `COLORS` están definidos **a nivel de clase** (`cls`), no de instancia.
    Esto significa que se inicializan una sola vez y son compartidos si hubiera múltiples instancias de `ClientState`.

```mermaid
classDiagram
    class ClientState {
        MAP: Map
        PLAYERS: dict
        BULLETS: dict
        COLORS: dict
    }
```

### Flujo de `draw_player`

`draw_player` recibe un dict deserializado de `PLAYERS_UPDATE` y delega en la plantilla de `Player` correcta:

```mermaid
flowchart TD
    A["data = {'x', 'y', 'state', 'type_class'}"]
    A --> B["PLAYER_CLASS(type_class)"]
    B --> C["player = PLAYERS[type_class]"]
    C --> D["player.move(x, y, state) — posiciona la plantilla"]
    D --> E["player.draw(surface, dx, dy) — blitea sprite"]
```

!!! warning "Plantilla compartida"
    `ClientState.PLAYERS` tiene **una sola instancia de `Player` por clase**.
    Al llamar `player.move()` antes de `player.draw()` se mueve la plantilla a la posición correcta antes de dibujar.
    Esto funciona porque los jugadores se renderizan en secuencia, no en paralelo.

---

## Interacción entre ServerState y ClientState

Ambos estados nunca interactúan directamente — están en procesos distintos y se comunican **solo a través de la red**.

```mermaid
sequenceDiagram
    participant SS as ServerState
    participant NET as WebSocket / JSON
    participant CS as ClientState

    Note over SS: Cada 50ms — Server.loop()
    SS->>SS: get_players()
    SS->>NET: broadcast PLAYERS_UPDATE JSON

    Note over CS: Recibido en Client.update()
    NET-->>CS: PLAYERS_UPDATE

    loop Por cada pid en players
        CS->>CS: server_positions.update(pid → data)
    end

    Note over CS: En Client.loop() — cada frame
    CS->>CS: render_positions ← server_positions
    CS->>CS: draw_player(surface, dx, dy, pos)
    CS->>CS: MAP.draw() + MAP.draw_mini()
```

### Comparación de flujos de datos

```mermaid
flowchart LR
    subgraph SERVIDOR["Servidor — proceso autoritativo"]
        direction TB
        IN["InputHandler\n(via WISH_MOVE)"] --> SS["ServerState\nvalida colisiones\nmantiene posición canónica"]
        SS --> MAP_S["Map.is_collision\nKDTree"]
        SS --> OUT["get_players()\ndump a JSON"]
    end

    subgraph RED["WebSocket — JSON"]
        direction TB
        WS_IN["WISH_MOVE →"]
        WS_OUT["← PLAYERS_UPDATE"]
    end

    subgraph CLIENTE["Cliente — proceso de render"]
        direction TB
        IH["InputHandler\nteclado / mando"] --> CL["Client.loop()\nwish_to_move → WISH_MOVE"]
        CU["Client.update()\nrecibe snapshots"] --> SP["server_positions"]
        SP --> RP["render_positions\n(interpolación directa)"]
        RP --> CS["ClientState.draw_player\nplantilla por clase"]
        CS --> MAP_C["Map.draw\nMap.draw_mini"]
    end

    IN -.->|recibido| WS_IN
    WS_IN --> SS
    OUT -->|enviado| WS_OUT
    WS_OUT -.-> CU
    IH --> WS_IN
```

---

## Tabla de responsabilidades

| Operación | `ServerState` | `ClientState` | Quién lo hace |
|---|:---:|:---:|---|
| Cargar mapa CSV | ✓ | ✓ | Ambos cargan su propia copia |
| Validar colisiones | ✓ | ✗ | Solo servidor |
| Calcular spawn | ✓ | ✗ | Solo servidor |
| Mantener posición canónica | ✓ | ✗ | Solo servidor |
| Almacenar conexiones WS | ✓ | ✗ | Solo servidor |
| Broadcast de estado | ✓ | ✗ | Solo servidor |
| Cargar sprites | ✗ | ✓ | Solo cliente |
| Renderizar mapa | ✗ | ✓ | Solo cliente |
| Renderizar jugadores | ✗ | ✓ | Solo cliente |
| Renderizar minimap | ✗ | ✓ | Solo cliente |
| Interpolar posiciones | ✗ | ✓ | Solo cliente |
| Gestionar colores minimap | ✗ | ✓ | Solo cliente |
