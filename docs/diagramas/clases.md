# Diagramas de Clases

## Diagrama completo del sistema

Visión global de todas las clases, sus atributos, métodos y relaciones.

```mermaid
classDiagram
    direction TB

    class Server {
        +TICK_RATE: int
        +state: ServerState
        +handle_client(socket) async
        +loop() async
    }

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
        -__set_player_class(id, data)
        -__try_move(id, data)
    }

    class Client {
        +INPUTS: InputHandler
        +CLOCK: Clock
        +FRAME_RATE: int
        +state: ClientState
        +ID: int
        +server_positions: dict
        +render_positions: dict
        +player: Player
        +update(websocket) async
        +loop(websocket) async
        +connect(player_class) async
    }

    class ClientState {
        +MAP: Map
        +PLAYERS: dict
        +BULLETS: dict
        +COLORS: dict
        +draw_player(surface, dx, dy, data)
    }

    class Player {
        +PLAYER_SIZE: int
        +BULLET_SIZE: int
        +states: dict
        +masks: dict
        +player_class: PLAYER_CLASS
        +current_state: STATE
        +speed: int
        +x: int
        +y: int
        +class_type: str
        +mask: Mask
        +wish_to_move(inputs) tuple
        +move(new_x, new_y, state)
        +dump() dict
        +draw(surface, dx, dy)
    }

    class Bullet {
        +image: Surface
        +mask: Mask
        +x: int
        +y: int
        +size: int
        +draw(surface, dx, dy)
    }

    class Map {
        +SOLID_TILES: set
        +SPAWN_CODE: int
        +TILE_SIZE: int
        +MINI_SIZE: int
        +MINI_SCALE: float
        +data: ndarray
        +solid_positions: list
        +solid_tree: KDTree
        +spawn_tiles: list
        +width: int
        +height: int
        +spawn() tuple
        +is_collision(x, y, mask) bool
        +draw(surface, position)
        +draw_mini(surface, dx, dy, points, px, py)
    }

    class InputHandler {
        +deadzone: float
        +quit: bool
        +k_left: bool
        +k_right: bool
        +k_enter: bool
        +con_left: bool
        +con_right: bool
        +con_up: bool
        +con_down: bool
        +shot: bool
        +update()
        -_handle_keyboard(events)
        -_handle_joystick(events)
        -_try_init_joystick()
        -_reset()
    }

    class Screen {
        +inputs: InputHandler
        +classes: list
        +current_class: int
        +selection: PLAYER_CLASS
        +loop(window, clock, frames) PLAYER_CLASS
        +handle_events()
        +draw(surface)
    }

    class messages {
        <<module>>
        +hello(id, socket)
        +player_class(type, socket)
        +wish_move(dx, dy, state, socket)
        +players_state(state, socket)
    }

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
        MOVE
        PLAYERS_UPDATE
    }

    %% Composición / Agregación
    Server *-- ServerState : compone
    Client *-- ClientState : compone
    Client *-- InputHandler : tiene
    Client o-- Player : jugador local

    ServerState *-- Player : jugadores activos
    ServerState o-- Map : clase compartida

    ClientState o-- Map : clase compartida
    ClientState *-- Player : plantillas de render

    Screen o-- InputHandler : usa

    %% Dependencias de datos
    Player --> PLAYER_CLASS : tipado por
    Player --> STATE : usa
    messages --> MESSAGES : serializa
    Client --> messages : envía con
    Server --> messages : envía con
    ServerState --> messages : indirectamente
```

---

## Lado servidor

Foco en las clases que corren en `server.py`.

```mermaid
classDiagram
    direction LR

    class Server {
        +TICK_RATE: int
        +state: ServerState
        +handle_client(socket) async
        +loop() async
    }

    class ServerState {
        +IDs: set
        +MAP: Map
        +players: dict
        +clients: dict
        +available_ids: list
        +new_player(socket) int
        +remove_player(id)
        +handle_message(id, data)
        +get_players() dict
        -__set_player_class(id, data)
        -__try_move(id, data)
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

    class Map {
        +solid_tree: KDTree
        +spawn_tiles: list
        +spawn() tuple
        +is_collision(x, y, mask) bool
    }

    class MESSAGES {
        <<enumeration>>
        PLAYER_CLASS
        WISH_MOVE
        PLAYERS_UPDATE
        HELLO
    }

    Server *-- "1" ServerState
    ServerState *-- "0..4" Player : players[id]
    ServerState o-- "1" Map : Map — clase
    ServerState --> MESSAGES : despacha por tipo
    Map --> Player : valida colisión con mask
```

---

## Lado cliente

Foco en las clases que corren en `client.py`.

```mermaid
classDiagram
    direction LR

    class Client {
        +ID: int
        +server_positions: dict
        +render_positions: dict
        +player: Player
        +state: ClientState
        +update(websocket) async
        +loop(websocket) async
        +connect(player_class) async
    }

    class ClientState {
        +MAP: Map
        +PLAYERS: dict
        +BULLETS: dict
        +COLORS: dict
        +draw_player(surface, dx, dy, data)
    }

    class Player {
        +states: dict
        +masks: dict
        +speed: int
        +x: int
        +y: int
        +wish_to_move(inputs) tuple
        +move(new_x, new_y, state)
        +draw(surface, dx, dy)
    }

    class Bullet {
        +image: Surface
        +mask: Mask
        +draw(surface, dx, dy)
    }

    class Map {
        +width: int
        +height: int
        +draw(surface, position)
        +draw_mini(surface, dx, dy, points, px, py)
    }

    class InputHandler {
        +quit: bool
        +con_left: bool
        +con_right: bool
        +con_up: bool
        +con_down: bool
        +shot: bool
        +update()
    }

    class Screen {
        +current_class: int
        +selection: PLAYER_CLASS
        +loop(window, clock, frames) PLAYER_CLASS
    }

    Client *-- "1" ClientState
    Client *-- "1" InputHandler
    Client o-- "1" Player : jugador local
    ClientState o-- "1" Map
    ClientState *-- "4" Player : plantillas PLAYER_CLASS
    ClientState *-- "4" Bullet : plantillas PLAYER_CLASS
    Screen o-- InputHandler : comparte INPUTS
```

---

## Enumeraciones

```mermaid
classDiagram
    class PLAYER_CLASS {
        <<enumeration>>
        ARCHER = archer
        FARMER = farmer
        MAGE = mage
        MUSKETEER = musketeer
    }

    class STATE {
        <<enumeration>>
        UP = up
        DOWN = down
        LEFT = left
        RIGHT = right
        SHOT = shot
    }

    class MESSAGES {
        <<enumeration>>
        HELLO = hello
        PLAYER_CLASS = player_class
        WISH_MOVE = wish_mode
        MOVE = move
        PLAYERS_UPDATE = players_update
    }

    PLAYER_CLASS -- Player : clase del personaje
    STATE -- Player : estado de animación
    MESSAGES -- messages : tipo de mensaje JSON
```
