# Diagramas de Clases

## Diagrama global del sistema

Visión de alto nivel: qué módulos/clases pertenecen al servidor, al cliente, y cuáles son compartidos.

```mermaid
flowchart TB
    subgraph SERVER["Servidor — server.py"]
        direction TB
        SVR[Server\nTICK_RATE=20]
        SL[server_logic.Logic\ntick / serialize]
        SS[server_state.State\nCLIENTS / PLAYERS / SHIPS / BULLETS / ENEMIES]
        MD[MapData\nA★ / colisiones KDTree]
    end

    subgraph SHARED["Entidades compartidas — entities.py / enums.py / messages.py / protocols.py"]
        direction LR
        ENT["Player · Bullet · Ship · Enemy · Castle · Counter · Geometry"]
        PROTO["LivingEntity (Protocol)"]
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
    SL & CL -. usa .-> PROTO
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
        +spawn_ship_timer: Counter
        +spawn_enemy_timer: Counter
        +died_players: set
        +new_round: bool
        +CLIENTS: dict
        +new_player(socket) int
        +remove_player(id)
        +handle_message(id, data) MESSAGES
        +tick() tuple
        +serialize() dict
        -__set_player_class(id, data)
        -__try_move(id, data)
        -__new_bullet(id, data)
        -__move_bullets()
        -__move(enemies)
        -__spawn_enemies()
        -__redirect_enemies()
        -__check_round()
        -__check_enemy_hit_with_castle()
        -__check_enemy_hit_with_player()
        -__tick_invulnerability()
    }

    class State {
        <<server_state>>
        +IDS: set~0..3~
        +CLIENTS: dict
        +PLAYERS: dict
        +BULLETS: list
        +SHIPS: list
        +ENEMIES: list
        +MAX_SHIPS: int = 5
        +MAX_ENEMIES: int = 5
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
        +enemy_target_tiles: set
        +castles: dict
        +width: int
        +height: int
        +spawn() tuple
        +is_collision(pos, collision) bool
        +find_path(sx, sy, tx, ty, collision) list~STATE~
        +pixel_to_tile(x, y) tuple
        +tile_center(col, row) tuple
    }

    class Player {
        <<entities>>
        +role: ROLE
        +x: int
        +y: int
        +live: int = 20
        +max_live: int = 20
        +radius: int = 25
        +speed: int = 5
        +state: STATE = DOWN
        +invulnerable: int = 0
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
        +damage: int = 2
        +radius: int = 16
        +update(data)
        +dump() dict
    }

    class Ship {
        <<entities>>
        +x: int
        +y: int
        +path: list~STATE~
        +live: int = 20
        +max_live: int = 20
        +radius: int = 32
        +speed: int = 5
        +state: STATE = DOWN
        +target_x: int
        +target_y: int
        +update(data)
        +dump() dict
    }

    class Enemy {
        <<entities>>
        +x: int
        +y: int
        +path: list~STATE~
        +variant: int
        +live: int = 5
        +max_live: int = 5
        +radius: int = 25
        +speed: int = 15
        +damage: int = 4
        +state: STATE = LEFT
        +target_x: int
        +target_y: int
        +update(data)
        +dump() dict
    }

    class Castle {
        <<entities>>
        +x: int
        +y: int
        +live: int = 50
        +max_live: int = 50
        +radius: int = 64
        +invulnerable: int = 0
        +update(data)
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

    class LivingEntity {
        <<protocol>>
        +live: int
        +max_live: int
    }

    Server *-- Logic : LOGIC
    Logic *-- State : STATE
    Logic *-- Counter : spawn_ship_timer
    Logic *-- Counter : spawn_enemy_timer
    State *-- MapData : MAP
    State *-- "0..4" Player : PLAYERS[id]
    State *-- "*" Bullet : BULLETS
    State *-- "*" Ship : SHIPS
    State *-- "*" Enemy : ENEMIES
    Player ..|> LivingEntity
    Ship ..|> LivingEntity
    Enemy ..|> LivingEntity
    Castle ..|> LivingEntity
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
        +host: TextInput
        +port: TextInput
        -_connected: bool
        -_player_count: int
        -_server_proc: Popen
        +reset()
        +loop() ROLE
        +handle_events()
        +draw(surface)
        -_launch_server()
        -_connect_ws()
        -_disconnect_ws()
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
        +connected: bool
        +run(role, host, port) async str
        +loop(websocket) async
        +receive_from_server(websocket) async
        -__handle_player_actions(websocket) async
        -__center_screen()
    }

    class Logic {
        <<client_logic>>
        +STATE: State
        +DEBUG: bool
        -_in_battle: bool
        +ANIM_FPS: int = 8
        +player: Player
        +ID: int
        +reset()
        +update_players(players)
        +update_bullets(bullets)
        +update_ships(ships)
        +update_enemies(enemies)
        +update_castles(castles)
        +draw(surface, dx, dy)
        +draw_minimap(surface)
        +start_music()
        +stop_music()
        -draw_player(surface, dx, dy, player)
        -draw_ship(surface, dx, dy, ship)
        -draw_enenmy(surface, dx, dy, enemy)
        -draw_castles(surface, dx, dy)
        -draw_bullet(surface, x, y, role, dx, dy)
        -draw_ui(surface, dx, dy)
        -draw_health_bar(surface, x, y, w, h, entity)
        -_update_music()
        -_anim_frame(n_frames) int
    }

    class State {
        <<client_state>>
        +MAP: MapRender
        +PLAYERS: dict
        +BULLETS: dict
        +SHIPS: dict
        +ENEMIES: dict
        +COLORS: dict
        +castles: dict
        +castle_image: Surface
        +received_players: dict
        +received_bullets: list
        +received_ships: list
        +received_enemies: list
        +player: Player
        +ID: int
    }

    class MapRender {
        +width: int
        +height: int
        +map: MapData
        +draw_layer(surface, offset, layer)
        +draw_mini(surface, dx, dy, points, px, py)
        +draw_collision_debug(surface, offset)
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

    Orchestrator *-- Screen : LOBBY
    Orchestrator *-- Game : GAME
    Orchestrator *-- InputHandler : INPUTS
    Game *-- Logic : LOGIC
    Logic *-- State : STATE
    State *-- MapRender : MAP
    State o-- Player : player actual
    Game o-- InputHandler : inputs
    Screen o-- InputHandler : inputs
```

---

## Entidades compartidas

Dataclasses definidas en `entities.py` y protocol en `protocols.py`. Son usadas tanto por el servidor (lógica autoritativa) como por el cliente (render).

```mermaid
classDiagram
    direction LR

    class LivingEntity {
        <<protocol>>
        +live: int
        +max_live: int
    }

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
        +live: int = 20
        +max_live: int = 20
        +radius: int = 25
        +speed: int = 5
        +state: STATE = DOWN
        +invulnerable: int = 0
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
        +damage: int = 2
        +radius: int = 16
        +update(data)
        +dump() dict
    }

    class Ship {
        +x: int
        +y: int
        +path: list~STATE~
        +live: int = 20
        +max_live: int = 20
        +radius: int = 32
        +speed: int = 5
        +state: STATE = DOWN
        +target_x: int
        +target_y: int
        +update(data)
        +dump() dict
    }

    class Enemy {
        +x: int
        +y: int
        +path: list~STATE~
        +variant: int
        +live: int = 5
        +max_live: int = 5
        +radius: int = 25
        +speed: int = 15
        +damage: int = 4
        +state: STATE = LEFT
        +target_x: int
        +target_y: int
        +update(data)
        +dump() dict
    }

    class Castle {
        +x: int
        +y: int
        +live: int = 50
        +max_live: int = 50
        +radius: int = 64
        +invulnerable: int = 0
        +update(data)
        +dump() dict
    }

    Player ..|> LivingEntity
    Ship ..|> LivingEntity
    Enemy ..|> LivingEntity
    Castle ..|> LivingEntity

    Player --> ROLE : rol del personaje
    Player --> STATE : dirección / animación
    Bullet --> ROLE : clase del autor
    Ship --> STATE : dirección actual
    Enemy --> STATE : dirección actual
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
        IDLE = idle
    }

    class MESSAGES {
        <<enumeration>>
        HELLO = hello
        ROLE = role
        WISH_MOVE = wish_mode
        PLAYERS_UPDATE = players_update
        SHOT = shot
        QUIT = quit
        ROUND_START = round_start
    }

    class COLLISIONS {
        <<enumeration>>
        PLAYER = player
        BULLET = bullet
        SHIP = ship
        ENEMY = enemy
    }
```
