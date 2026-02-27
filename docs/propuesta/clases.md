# Diagrama de clases — Propuesta

## Vista completa

```mermaid
classDiagram
    direction TB

    %% ── SERVIDOR ──────────────────────────────────────────────────

    class Server {
        +TICK_RATE: int
        +state: GameState
        +logic: GameLogic
        +handle_client(socket) async
        +loop() async
    }

    class GameState {
        +IDs: set
        +clients: dict
        +players: dict
        +bullets: list
        +ships: list
        +enemies: list
        +round: int
        +spawn_timer: float
        +MAP: MapData
        +available_ids: list
    }

    class GameLogic {
        +state: GameState
        +handle_message(id, data)
        +tick(dt)
        +serialize() dict
        -new_player(socket) int
        -remove_player(id)
        -try_spawn_round(dt)
        -move_ships(dt)
        -check_ship_landing()
        -move_bullets(dt)
        -check_bullet_hits()
        -try_move(id, dx, dy, state)
        -cleanup()
    }

    %% ── ENTIDADES SERVIDOR ────────────────────────────────────────

    class ServerEntity {
        <<abstract>>
        +x: float
        +y: float
        +radius: int
        +hp: int
        +dump() dict
    }

    class ServerPlayer {
        +radius: int
        +speed: int
        +player_class: PLAYER_CLASS
        +current_state: STATE
        +move(x, y, state)
        +dump() dict
    }

    class Bullet {
        +radius: int
        +vx: float
        +vy: float
        +owner_id: int
    }

    class EnemyShip {
        +radius: int
        +vx: float
        +vy: float
        +landed: bool
    }

    class Enemy {
        +radius: int
        +target_id: int
    }

    %% ── MAPA ──────────────────────────────────────────────────────

    class MapData {
        +SOLID_TILES: set
        +LANDING_TILES: set
        +SPAWN_CODE: int
        +TILE_SIZE: int
        +data: ndarray
        +solid_positions: list
        +solid_tree: KDTree
        +spawn_tiles: list
        +width: int
        +height: int
        +spawn() tuple
        +is_collision(x, y, radius) bool
    }

    class MapRenderer {
        +TILES: dict
        +prev_map: Surface
        +mini_map_full: Surface
        +MINI_SIZE: int
        +MINI_SCALE: float
        +draw(surface, position)
        +draw_mini(surface, dx, dy, points, px, py)
    }

    %% ── CLIENTE ───────────────────────────────────────────────────

    class Client {
        +INPUTS: InputHandler
        +CLOCK: Clock
        +FRAME_RATE: int
        +state: ClientState
        +ID: int
        +server_snapshot: dict
        +render_positions: dict
        +player: ClientPlayer
        +update(websocket) async
        +loop(websocket) async
        +connect(player_class) async
    }

    class ClientState {
        +MAP: MapRenderer
        +PLAYERS: dict
        +BULLETS: dict
        +SHIPS: dict
        +ENEMIES: dict
        +COLORS: dict
        +draw_player(surface, dx, dy, data)
        +draw_bullet(surface, dx, dy, data)
        +draw_ship(surface, dx, dy, data)
        +draw_enemy(surface, dx, dy, data)
    }

    class ClientPlayer {
        +states: dict
        +masks: dict
        +player_class: PLAYER_CLASS
        +current_state: STATE
        +speed: int
        +x: float
        +y: float
        +wish_to_move(inputs) tuple
        +move(x, y, state)
        +draw(surface, dx, dy)
    }

    class InputHandler {
        +quit: bool
        +con_left: bool
        +con_right: bool
        +con_up: bool
        +con_down: bool
        +shot: bool
        +shoot_dx: float
        +shoot_dy: float
        +update()
    }

    class Screen {
        +inputs: InputHandler
        +classes: list
        +current_class: int
        +selection: PLAYER_CLASS
        +loop(window, clock, frames) PLAYER_CLASS
    }

    %% ── ENUMS ─────────────────────────────────────────────────────

    class PLAYER_CLASS {
        <<enumeration>>
        ARCHER
        FARMER
        MAGE
        MUSKETEER
    }

    class STATE {
        <<enumeration>>
        UP
        DOWN
        LEFT
        RIGHT
        SHOT
    }

    class MESSAGES {
        <<enumeration>>
        HELLO
        PLAYER_CLASS
        WISH_MOVE
        SHOOT
        PLAYERS_UPDATE
    }

    %% ── RELACIONES ────────────────────────────────────────────────

    Server *-- GameState
    Server *-- GameLogic
    GameLogic o-- GameState

    GameState *-- ServerPlayer
    GameState *-- Bullet
    GameState *-- EnemyShip
    GameState *-- Enemy
    GameState o-- MapData

    ServerEntity <|-- ServerPlayer
    ServerEntity <|-- Bullet
    ServerEntity <|-- EnemyShip
    ServerEntity <|-- Enemy

    MapData <|-- MapRenderer

    Client *-- ClientState
    Client *-- InputHandler
    Client o-- ClientPlayer
    ClientState o-- MapRenderer
    ClientState *-- ClientPlayer

    Screen o-- InputHandler

    ServerPlayer --> PLAYER_CLASS
    ServerPlayer --> STATE
    ClientPlayer --> PLAYER_CLASS
    ClientPlayer --> STATE
    GameLogic --> MESSAGES
```

---

## Jerarquía de entidades del servidor

Todas las entidades del servidor heredan de `ServerEntity`, que define
solo la geometría de colisión (sin sprites ni pygame).

```mermaid
classDiagram
    direction LR

    class ServerEntity {
        <<abstract>>
        +x: float
        +y: float
        +radius: int
        +hp: int
        +dump() dict
    }

    class ServerPlayer {
        +radius = 28
        +speed: int
        +player_class: PLAYER_CLASS
        +current_state: STATE
    }

    class Bullet {
        +radius = 8
        +vx: float
        +vy: float
        +owner_id: int
    }

    class EnemyShip {
        +radius = 40
        +vx: float
        +vy: float
        +landed: bool
    }

    class Enemy {
        +radius = 20
        +target_id: int
    }

    ServerEntity <|-- ServerPlayer
    ServerEntity <|-- Bullet
    ServerEntity <|-- EnemyShip
    ServerEntity <|-- Enemy
```

La colisión entre cualquier par de entidades se resuelve con una sola función:

```python
def overlaps(a: ServerEntity, b: ServerEntity) -> bool:
    dx, dy = a.x - b.x, a.y - b.y
    return dx*dx + dy*dy <= (a.radius + b.radius) ** 2
```

---

## Split de Map: MapData vs MapRenderer

```mermaid
classDiagram
    direction LR

    class MapData {
        +solid_tree: KDTree
        +spawn_tiles: list
        +LANDING_TILES: set
        +is_collision(x, y, radius) bool
        +spawn() tuple
    }

    class MapRenderer {
        +TILES: dict
        +prev_map: Surface
        +mini_map_full: Surface
        +draw(surface, position)
        +draw_mini(surface, dx, dy, points, px, py)
    }

    MapData <|-- MapRenderer : hereda datos y colisión

    note for MapData "Usado en servidor y cliente\nSin dependencias de pygame"
    note for MapRenderer "Solo en cliente\nCarga TILES con factories.load_tiles()"
```

`is_collision` cambia de firma: recibe `radius: int` en lugar de `pygame.mask.Mask`,
eliminando la dependencia de sprites en el servidor.

---

## Sprites por propietario

```mermaid
flowchart LR
    subgraph MapRenderer["MapRenderer (mapa)"]
        T["TILES: dict[int, Surface]\nload_tiles()"]
    end

    subgraph ClientState["ClientState (actores)"]
        P["PLAYERS: dict[PLAYER_CLASS, ClientPlayer]\nload_player()"]
        B["BULLETS: dict[PLAYER_CLASS, Surface]\nload_bullet()"]
        S["SHIPS: dict[..., Surface]\nload_ship()"]
        E["ENEMIES: dict[..., Surface]\nload_enemy()"]
    end
```

---

## Tick del servidor — orden de operaciones

```mermaid
flowchart TD
    A["GameLogic.tick(dt)"]
    A --> B["try_spawn_round(dt)\nsi no hay enemigos: timer += dt\nsi timer >= 5s: spawn barcos"]
    B --> C["move_ships(dt)\nbarcos avanzan según velocidad"]
    C --> D["check_ship_landing()\nsi barco toca LANDING_TILE:\n landed=True, spawn enemies"]
    D --> E["move_bullets(dt)\nbalas avanzan según vx,vy"]
    E --> F["check_bullet_hits()\nbala vs tiles: is_collision()\nbala vs entidades: overlaps()"]
    F --> G["try_move(id,...)\nintenta mover jugadores\nsi hay WISH_MOVE pendiente"]
    G --> H["cleanup()\nelimina bullets agotadas\nelimina entidades con hp <= 0"]
    H --> I["serialize()\nempaqueta todo para broadcast"]
```
