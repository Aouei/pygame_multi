# Diagramas de Clases

El proyecto sigue **Clean Architecture** en cuatro capas. La regla central: las capas internas nunca importan las externas. `domain/` y `use_cases/` tienen cero imports de `pygame`, `asyncio` ni `websockets`.

```
[ Frameworks & Drivers ]  →  [ Interface Adapters ]  →  [ Use Cases ]  →  [ Domain ]
  pygame, asyncio,             renderers, input          ServerSession,    entities,
  websockets, asset_store,     adapters, serializers,    ClientSession,    map_data,
  ws_runner, inputs            messages, camera          LobbyService      rules puras
```

---

## Visión global por capas

```mermaid
flowchart TB
    subgraph FW["Frameworks & Drivers"]
        direction LR
        AS[AssetStore\nsingleton sprites]
        WSR[ws_runner\nasyncio + websockets]
        IH[InputHandler\nteclado / mando]
        LOBBY_SH[lobby.Screen\npygame_gui]
        GAME_SH[game.Game\nbucle async]
    end

    subgraph AD["Interface Adapters"]
        direction LR
        MSG[messages.py\nJSON builders]
        WSSH[ws_server_handler\nhandle_client async]
        IA[InputAdapter\nInputHandler→PlayerIntention]
        CAM[Camera]
        GR[GameRenderer\ndraw_*]
        MR[MapRender\ntiles + minimap]
    end

    subgraph UC["Use Cases"]
        direction LR
        SS[ServerSession\ntick / snapshot]
        CS[ClientSession\napply_snapshot]
        LS[LobbyService\nstart_hosting]
        IT[input_translator\ntranslate_move / translate_shoot]
        DTOS[dtos.py\nGameSnapshot / DTOs]
        PORTS[ports.py\nIInputSource / IAssetProvider]
    end

    subgraph DOM["Domain"]
        direction LR
        ENT["Player · Bullet · Ship\nEnemy · Castle · Counter · Geometry"]
        MD[MapData\nKDTree + A*]
        RUL[rules.py\ncheck_intersection]
        ENUMS[enums.py\nROLE · STATE · COLLISIONS]
        PROTO[protocols.py\nLivingEntity · Collidable]
    end

    FW --> AD --> UC --> DOM
```

---

## Domain

Entidades puras sin dependencias externas. Contienen solo lógica de datos y reglas de negocio.

```mermaid
classDiagram
    direction TB

    class Player {
        +role: ROLE
        +x: int
        +y: int
        +live: int = 20
        +max_live: int = 20
        +radius: int = 20
        +speed: int = 5
        +state: STATE = DOWN
        +invulnerable: int = 0
        +update(data: dict)
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
        +update(data: dict)
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
        +update(data: dict)
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
        +update(data: dict)
        +dump() dict
    }

    class Castle {
        +x: int
        +y: int
        +live: int = 200
        +max_live: int = 200
        +radius: int = 64
        +invulnerable: int = 0
        +update(data: dict)
        +dump() dict
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

    class LivingEntity {
        <<protocol>>
        +live: int
        +max_live: int
    }

    class Collidable {
        <<protocol>>
        +x: int
        +y: int
        +radius: int
    }

    class MapData {
        +map: TileMap
        +scale: int
        +player_spawn_tiles: list
        +ship_spawn_tiles: list
        +disembark_tiles: list
        +enemy_target_tiles: set
        +castles: dict~int, Castle~
        +collision_shapes: dict
        +width: int
        +height: int
        +spawn(is_player) tuple
        +is_collision(pos, collision) bool
        +find_path(sc, sr, tc, tr, collision) list~STATE~
        +pixel_to_tile(x, y) tuple
        +tile_center(col, row) tuple
        +remove_castle(castle_id)
    }

    Player ..|> LivingEntity
    Ship ..|> LivingEntity
    Enemy ..|> LivingEntity
    Castle ..|> LivingEntity
    Player ..|> Collidable
    Bullet ..|> Collidable
    Ship ..|> Collidable
    Enemy ..|> Collidable
    Castle ..|> Collidable
    MapData *-- "0..*" Castle : castles
```

---

## Use Cases

Orquestadores de negocio. Sin imports de `pygame`, `asyncio` ni `websockets`.

```mermaid
classDiagram
    direction TB

    class ServerSession {
        +TICK_RATE: int = 20
        +IDS: set
        +MAX_SHIPS: int = 5
        +MAX_ENEMIES: int = 10
        +BULLET_VELOCITY: int = 30
        +CLIENTS: dict
        +PLAYERS: dict~int, Player~
        +BULLETS: list~Bullet~
        +SHIPS: list~Ship~
        +ENEMIES: list~Enemy~
        +MAP: MapData
        +running: bool
        +died_players: set
        +available_ids: list
        +new_player(socket) int
        +remove_player(id)
        +handle_message(id, data)
        +tick() set
        +snapshot() GameSnapshot
        +reset()
    }

    class ClientSession {
        +received_players: dict~int, Player~
        +received_bullets: list~Bullet~
        +received_ships: list~Ship~
        +received_enemies: list~Enemy~
        +received_castles: dict~int, Castle~
        +player: Player
        +ID: int
        +in_battle: bool
        +apply_snapshot(snap: GameSnapshot)
        +reset()
    }

    class LobbyService {
        -_runner: Callable
        -_server_obj: ServerSession
        -_server_thread: Thread
        +server_obj: ServerSession
        +start_hosting()
        +stop_hosting()
    }

    class PlayerIntention {
        <<dataclass>>
        +move_left: bool
        +move_right: bool
        +move_up: bool
        +move_down: bool
        +shoot: bool
        +mouse_pos: tuple
        +right_stick_x: float
        +right_stick_y: float
        +use_stick: bool
        +deadzone: float
    }

    class GameSnapshot {
        <<dataclass>>
        +clients: int
        +players: dict~int, PlayerDTO~
        +bullets: list~BulletDTO~
        +ships: list~ShipDTO~
        +enemies: list~EnemyDTO~
        +castles: dict~int, CastleDTO~
        +from_wire(data: dict)$ GameSnapshot
        +to_wire() dict
    }

    class PlayerDTO {
        <<dataclass>>
        +x: int
        +y: int
        +live: int
        +state: str
        +role: str
    }

    class BulletDTO {
        <<dataclass>>
        +x: int
        +y: int
        +dx: float
        +dy: float
        +role: str
    }

    class ShipDTO {
        <<dataclass>>
        +x: int
        +y: int
        +state: str
        +live: int
    }

    class EnemyDTO {
        <<dataclass>>
        +x: int
        +y: int
        +state: str
        +live: int
        +variant: int
    }

    class CastleDTO {
        <<dataclass>>
        +x: int
        +y: int
        +live: int
    }

    class IInputSource {
        <<protocol>>
        +read() PlayerIntention
    }

    class IAssetProvider {
        <<protocol>>
        +players: dict
        +bullets: dict
        +ships: dict
        +enemies: list
        +castle: object
    }

    class IServerProcess {
        <<protocol>>
        +running: bool
    }

    ServerSession *-- "0..4" Player : PLAYERS
    ServerSession *-- "*" Bullet : BULLETS
    ServerSession *-- "*" Ship : SHIPS
    ServerSession *-- "*" Enemy : ENEMIES
    ServerSession *-- MapData : MAP
    ServerSession ..> GameSnapshot : snapshot()
    ClientSession ..> GameSnapshot : apply_snapshot()
    GameSnapshot *-- PlayerDTO
    GameSnapshot *-- BulletDTO
    GameSnapshot *-- ShipDTO
    GameSnapshot *-- EnemyDTO
    GameSnapshot *-- CastleDTO
    LobbyService ..> ServerSession : crea
```

---

## Interface Adapters

Traducen entre el mundo externo (JSON, pygame, websockets) y los use cases.

```mermaid
classDiagram
    direction TB

    class InputAdapter {
        -_handler: InputHandler
        +read() PlayerIntention
    }

    class GameRenderer {
        +DEBUG: bool = False
        +ANIM_FPS: int = 8
        -_assets: AssetStore
        +draw(surface, session, dx, dy)
        +draw_player(surface, dx, dy, player)
        +draw_ship(surface, dx, dy, ship)
        +draw_enemy(surface, dx, dy, enemy)
        +draw_bullet(surface, x, y, role, dx, dy)
        +draw_castles(surface, dx, dy, castles)
        +draw_health_bar(surface, x, y, w, h, entity)
        +draw_ui(surface, dx, dy, session, map_r)
        +draw_minimap(surface, session, map_r)
    }

    class MapRender {
        +MINI_SIZE: int = 320
        +MINI_SCALE: float = 0.2
        -map: MapData
        -_full_surface: Surface
        -_layer_surfaces: dict
        -_precomputed_frames: dict
        +width: int
        +height: int
        +castles: dict
        +draw(surface, position)
        +draw_layer(surface, position, name)
        +draw_mini(surface, dx, dy, points, px, py)
        +draw_collision_debug(surface, position)
    }

    class Camera {
        +x: int
        +y: int
        +map_pixel_w: int
        +map_pixel_h: int
        +screen_w: int
        +screen_h: int
        +move(dx, dy)
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
        SHUT_DOWN = shut_down
    }

    InputAdapter ..> PlayerIntention : produce
    GameRenderer ..> MapRender : usa
    GameRenderer ..> ClientSession : lee estado
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

    class COLLISIONS {
        <<enumeration>>
        PLAYER = player
        BULLET = bullet
        SHIP = ship
        ENEMY = enemy
    }
```
