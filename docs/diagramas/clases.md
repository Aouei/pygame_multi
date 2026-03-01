# Diagramas de Clases

## Diagrama global del sistema

Visión de alto nivel: qué módulos/clases pertenecen al servidor, al cliente, y cuáles son compartidos.

```mermaid
flowchart TB
    subgraph SERVER["Servidor — server.py"]
        direction TB
        SVR[Server\nTICK_RATE=20]
        SL[server_logic.Logic\ntick / serialize]
        SS[server_state.State\nCLIENTS / PLAYERS / SHIPS / BULLETS]
        MD[MapData\nA★ / colisiones KDTree]
    end

    subgraph SHARED["Entidades compartidas — entities.py / enums.py / messages.py"]
        direction LR
        ENT["Player · Bullet · Ship · Counter · Geometry"]
        ENUMS["ROLE · STATE · MESSAGES · COLLISIONS"]
        MSG[messages.py]
    end

    subgraph CLIENT["Cliente — client.py"]
        direction TB
        CLI[client.py\norquestador]
        LOBBY[lobby.Screen\nselección de rol]
        GAME[game.Game\ngame loop async]
        CL[client_logic.Logic\ndraw / update]
        CS[client_state.State\nsprites / posiciones]
        MR[MapRender\nrender tiles + minimap]
        IH[InputHandler\nteclado / mando]
    end

    SVR --> SL --> SS --> MD

    CLI --> LOBBY
    CLI --> GAME
    GAME --> CL --> CS --> MR
    LOBBY & GAME --> IH

    SVR <-->|"WebSocket\nJSON"| GAME

    SS -. usa .-> ENT
    CS -. usa .-> ENT
    SVR & GAME -. usa .-> MSG
    SL & CL -. usa .-> ENUMS
```

---

## Lado servidor

Clases que corren en `server.py`. La lógica de juego está separada en `Logic` (comportamiento) y `State` (datos).

```mermaid
classDiagram
    direction TB

    class Server {
        +TICK_RATE: int = 20
        +LOGIC: Logic
        +handle_client(socket) async
        +loop() async
    }

    class Logic {
        <<server_logic>>
        +STATE: State
        +spawn_timer: Counter
        +CLIENTS: dict
        +new_player(socket) int
        +remove_player(id)
        +handle_message(id, data)
        +tick()
        +serialize() dict
        -__set_player_class(id, data)
        -__try_move(id, data)
        -__new_bullet(id, data)
        -__move_bullets()
        -__move_ships()
        -__check_round()
    }

    class State {
        <<server_state>>
        +IDS: set~0..3~
        +CLIENTS: dict
        +PLAYERS: dict
        +BULLETS: list
        +SHIPS: list
        +MAX_SHIPS: int = 16
        +MAP: MapData
        +BULLET_VELOCITY: int = 30
        +available_ids: list
    }

    class MapData {
        +TILE_SIZE: int = 64
        +COLLISION_TILES: dict
        +player_spawn_tiles: list
        +ship_spawn_tiles: list
        +disembark_tiles: list
        +width: int
        +height: int
        +spawn() tuple
        +is_collision(pos, collision) bool
        +find_path(sx, sy, tx, ty, collision) list~STATE~
    }

    class Player {
        <<entities>>
        +role: ROLE
        +x: int
        +y: int
        +live: int = 10
        +radius: int = 32
        +speed: int = 5
        +state: STATE
        +wish_to_move(inputs) tuple
        +wish_to_shoot(inputs, ox, oy) tuple
        +update(data)
        +dump() dict
    }

    class Bullet {
        <<entities>>
        +x: int
        +y: int
        +dx: float
        +dy: float
        +owner: ROLE
        +radius: int = 16
        +dump() dict
    }

    class Ship {
        <<entities>>
        +x: int
        +y: int
        +path: list~STATE~
        +live: int = 10
        +radius: int = 32
        +speed: int = 15
        +state: STATE
        +target_x: int
        +target_y: int
        +dump() dict
    }

    class Counter {
        <<entities>>
        +seconds: float
        +rate: int = 20
        -_count: int
        +tick() bool
        +reset()
    }

    Server *-- Logic : LOGIC
    Logic *-- State : STATE
    Logic *-- Counter : spawn_timer
    State *-- MapData : MAP
    State *-- "0..4" Player : PLAYERS[id]
    State *-- "*" Bullet : BULLETS
    State *-- "*" Ship : SHIPS
```

---

## Lado cliente

Clases que corren en `client.py`. El orquestador (`client.py`) alterna entre lobby (síncrono) y game loop (async WebSocket).

```mermaid
classDiagram
    direction TB

    class Orchestrator {
        <<client.py>>
        +INPUTS: InputHandler
        +CLOCK: Clock
        +LOBBY: Screen
        +GAME: Game
        +main loop
    }

    class Screen {
        <<levels/lobby>>
        +inputs: InputHandler
        +classes: list
        +current_class: int
        +selection: ROLE
        +reset()
        +loop(window, clock) ROLE
        +handle_events()
        +draw(surface)
    }

    class Game {
        <<levels/game>>
        +LOGIC: Logic
        +FRAME_RATE: int = 60
        +inputs: InputHandler
        +clock: Clock
        +window: Surface
        +offset_x: int
        +offset_y: int
        +run(role) async str
        +loop(websocket) async
        +receive_from_server(websocket) async
        -__handle_player_actions(websocket) async
        -__center_screen()
    }

    class Logic {
        <<client_logic>>
        +STATE: State
        +player: Player
        +ID: int
        +reset()
        +update_players(players)
        +update_bullets(bullets)
        +update_ships(ships)
        +draw(surface, dx, dy)
        +draw_minimap(surface)
        -draw_player(surface, dx, dy, data)
        -draw_ship(surface, dx, dy, data)
        -draw_bullet(surface, x, y, role, vx, vy)
    }

    class State {
        <<client_state>>
        +MAP: MapRender
        +PLAYERS: dict
        +BULLETS: dict
        +SHIPS: dict
        +COLORS: dict
        +received_players: dict
        +received_bullets: list
        +received_ships: list
        +player: Player
        +ID: int
    }

    class MapRender {
        +MINI_SIZE: int = 320
        +MINI_SCALE: float = 0.1
        +width: int
        +height: int
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
        +mouse_pos: tuple
        +right_stick: tuple
        +update()
        +_reset()
        -_handle_keyboard(events)
        -_handle_joystick(events)
    }

    class Player {
        <<entities>>
        +role: ROLE
        +x: int
        +y: int
        +radius: int = 32
        +speed: int = 5
        +state: STATE
        +wish_to_move(inputs) tuple
        +wish_to_shoot(inputs, ox, oy) tuple
        +update(data)
        +dump() dict
    }

    Orchestrator *-- Screen : LOBBY
    Orchestrator *-- Game : GAME
    Orchestrator *-- InputHandler : INPUTS
    Game *-- Logic : LOGIC
    Logic *-- State : STATE
    State *-- MapRender : MAP
    State o-- Player : current player
    Game o-- InputHandler : inputs
    Screen o-- InputHandler : inputs
```

---

## Entidades compartidas

Dataclasses definidas en `entities.py`. Son usadas tanto por el servidor (lógica autoritativa) como por el cliente (render/input).

```mermaid
classDiagram
    direction LR

    class Counter {
        +seconds: float
        +rate: int = 20
        -_count: int
        +tick() bool
        +reset()
    }

    class Geometry {
        +x: int
        +y: int
        +radius: int
    }

    class Player {
        +role: ROLE
        +x: int
        +y: int
        +live: int = 10
        +radius: int = 32
        +speed: int = 5
        +state: STATE
        +wish_to_move(inputs) tuple
        +wish_to_shoot(inputs, ox, oy) tuple
        +update(data)
        +dump() dict
    }

    class Bullet {
        +x: int
        +y: int
        +dx: float
        +dy: float
        +owner: ROLE
        +radius: int = 16
        +dump() dict
    }

    class Ship {
        +x: int
        +y: int
        +path: list~STATE~
        +live: int = 10
        +radius: int = 32
        +speed: int = 15
        +state: STATE
        +target_x: int
        +target_y: int
        +dump() dict
    }

    Player --> ROLE : rol del personaje
    Player --> STATE : dirección / animación
    Bullet --> ROLE : clase del autor
    Ship --> STATE : dirección actual
```

---

## Enumeraciones

```mermaid
classDiagram
    direction LR

    class ROLE {
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
    }

    class MESSAGES {
        <<enumeration>>
        HELLO = hello
        ROLE = role
        WISH_MOVE = wish_mode
        MOVE = move
        PLAYERS_UPDATE = players_update
        SHOT = shot
    }

    class COLLISIONS {
        <<enumeration>>
        PLAYER = player
        BULLET = bullet
        SHIP = ship
    }
```
