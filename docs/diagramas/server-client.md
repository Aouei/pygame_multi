# Servidor vs Cliente

El proyecto separa la lógica en dos procesos independientes que se comunican exclusivamente por WebSocket.
Cada lado está organizado en capas Clean Architecture: el servidor corre `ServerSession` (use_cases) orquestado por `ws_runner` (frameworks); el cliente corre `ClientSession` + `GameRenderer` (use_cases + adapters) orquestado por `game.Game` (frameworks).

---

## Resumen de responsabilidades

| Aspecto | Servidor | Cliente |
|---|---|---|
| **Entry point** | `server.py` → `ws_runner.run()` | `main.py` → `game.Game.run()` |
| **Fuente de verdad** | Sí — `ServerSession` tiene posiciones canónicas | No — recibe `GameSnapshot` del servidor |
| **Mapa** | `MapData` — valida colisiones, A* | `MapRender` — renderiza tiles y minimap |
| **Jugadores** | `dict[id → Player]` con posición real | `ClientSession.received_players` |
| **Balas** | Mueve, detecta colisiones y elimina | Dibuja rotadas según dirección |
| **Barcos** | Pathfinding A*, movimiento suave, vida | Dibuja según `state` (dirección) |
| **Conexiones WS** | `ServerSession.CLIENTS: dict[id → socket]` | — |
| **Input** | Nunca toca inputs | `InputHandler` → `InputAdapter` → `PlayerIntention` |
| **Pygame / render** | No renderiza nada | `GameRenderer` dibuja todo a 60fps |
| **Tick rate** | 20Hz — broadcast + física | 60fps — render + envío de intenciones |
| **DTOs** | `snapshot() → GameSnapshot` | `apply_snapshot(GameSnapshot)` |

---

## Separación por capas (lado servidor vs cliente)

```mermaid
flowchart LR
    subgraph SRV["Servidor"]
        direction TB
        WSR["ws_runner\n_game_loop() 20Hz"]
        WSSH["ws_server_handler\nhandle_client()"]
        SS["ServerSession\ntick() / snapshot()"]
        MD["MapData\nKDTree + A*"]
        MSG_S["messages.py\nupdate_clients(GameSnapshot)"]
        WSR --> SS
        WSSH --> SS
        SS --> MD
        SS --> MSG_S
    end

    subgraph CLI["Cliente"]
        direction TB
        GAME["game.Game\nloop 60fps"]
        IA["InputAdapter\nread() → PlayerIntention"]
        CS["ClientSession\napply_snapshot(GameSnapshot)"]
        GR["GameRenderer\ndraw(surface, session, dx, dy)"]
        AS["AssetStore\nsprites / MapRender"]
        GAME --> IA
        GAME --> CS
        GAME --> GR
        GR --> AS
    end

    SRV <-->|"WebSocket JSON\nPLAYERS_UPDATE / WISH_MOVE / SHOT"| CLI
```

---

## Flujo de datos: GameSnapshot

El snapshot es el objeto que cruza la frontera entre servidor y cliente. Es el único punto de acoplamiento entre ambos lados.

```mermaid
flowchart LR
    SS["ServerSession\nentidades de dominio"] -->|"snapshot()"| GS["GameSnapshot\nDTOs puros"]
    GS -->|"to_wire()"| JSON["JSON string\ntipo: players_update"]
    JSON -->|"WebSocket broadcast"| RAW["JSON recibido por cliente"]
    RAW -->|"GameSnapshot.from_wire()"| GS2["GameSnapshot\nDTOs puros"]
    GS2 -->|"apply_snapshot()"| CS["ClientSession\nentidades de dominio"]
```

---

## MapData (servidor) vs MapRender (cliente)

El mapa se carga dos veces, con responsabilidades distintas:

| Aspecto | `MapData` | `MapRender` |
|---|---|---|
| **Capa** | `domain/map_data.py` | `adapters/renderer.py` |
| **Usado en** | `ServerSession` | `AssetStore` → `GameRenderer` |
| **Parser** | `tiledpy.Parser.load()` → `TileMap` | `MapData` + `tiledpy.map.render` |
| **Colisiones** | `KDTree` por tipo (`COLLISIONS`) | — |
| **Pathfinding** | A* sobre grid de tiles | — |
| **Spawn tiles** | Player spawn, ship spawn, disembark | — |
| **Render tiles** | — | `pygame.Surface` precalculada por capa |
| **Minimap** | — | Versión escalada al 20% + máscara circular |
| **Capas animadas** | — | Precomputa frames por `tick_ms` con `gcd` |

---

## Ciclo de vida de un jugador en el servidor

```mermaid
stateDiagram-v2
    [*] --> Conectado : new_player(socket)\nHELLO enviado
    Conectado --> Registrado : handle_message ROLE\n→ Player creado en spawn
    Registrado --> Registrado : handle_message WISH_MOVE\n→ __try_move()
    Registrado --> Registrado : handle_message SHOT\n→ __new_bullet()
    Registrado --> Muerto : tick() detecta live ≤ 0\no castillos destruidos
    Muerto --> [*] : QUIT enviado\nremove_player(id)
    Conectado --> [*] : ConnectionClosed\n→ remove_player(id)
    Registrado --> [*] : ConnectionClosed\n→ remove_player(id)
```

---

## Ciclo de vida de un barco

```mermaid
stateDiagram-v2
    [*] --> Navegando : __check_round() — Ship creado con path A*
    Navegando --> Navegando : __move() — avanza hacia target, pop path[0] al llegar
    Navegando --> Llegado : path vacío — llegó al destino (desembarcó)
    Llegado --> SpawnEnemigos : __spawn_enemies() genera Enemy desde ship.x/y
    SpawnEnemigos --> Llegado : spawn_enemy_timer.tick() cada 5s
    Llegado --> [*] : impactado por bala — live llega a 0
    Navegando --> [*] : impactado por bala — live llega a 0
```

---

## Flujo completo de datos (partida en curso)

```mermaid
flowchart LR
    subgraph SERVIDOR["Servidor — proceso autoritativo"]
        direction TB
        IH_S["WISH_MOVE / SHOT\n(intenciones del cliente)"]
        SS2["ServerSession\n__try_move()\n__new_bullet()\n__move_bullets()\n__move(ships/enemies)\n__check_round()"]
        MD2["MapData\nKDTree colisiones\nA* pathfinding"]
        SER["snapshot() → GameSnapshot\nto_wire() → JSON"]
        IH_S --> SS2
        SS2 <--> MD2
        SS2 --> SER
    end

    subgraph RED["WebSocket — JSON"]
        direction TB
        WS_IN["→ WISH_MOVE / SHOT"]
        WS_OUT["← PLAYERS_UPDATE"]
    end

    subgraph CLIENTE["Cliente — proceso de render"]
        direction TB
        IH_C["InputHandler\nteclado / mando"]
        IA2["InputAdapter\nread() → PlayerIntention"]
        GAME2["game.Game\nloop 60fps"]
        CS2["ClientSession\napply_snapshot(GameSnapshot)"]
        GR2["GameRenderer\ndraw(surface, session, dx, dy)"]
        AS2["AssetStore\nsprites + MapRender"]
        IH_C --> IA2 --> GAME2
        GAME2 -->|"WISH_MOVE / SHOT"| WS_IN
        WS_OUT --> GAME2
        GAME2 -->|"apply_snapshot"| CS2
        GR2 --> AS2
        CS2 -.-> GR2
    end

    SER --> WS_OUT
    WS_IN --> IH_S
```

---

## ServerSession — detalle de `handle_message`

```mermaid
flowchart TD
    A["handle_message(id, data)"] --> B["msg_type = data['type']"]
    B --> C{tipo}

    C -->|role| D["__set_player_class(id, data)"]
    D --> D1["x, y = MAP.spawn()"]
    D1 --> D2["PLAYERS[id] = Player(role, x, y)"]

    C -->|wish_mode| E["__try_move(id, data)"]
    E --> E1["new_x = player.x + dx\nnew_y = player.y + dy"]
    E1 --> E2{"colisión con ship\no castillo\no MAP?"}
    E2 -->|False| E3["player.x, player.y = new_x, new_y"]
    E2 -->|True| E4["movimiento descartado"]

    C -->|shot| F["__new_bullet(id, data)"]
    F --> F1["x = player.x + dx * BULLET_VELOCITY"]
    F1 --> F2["BULLETS.append(Bullet(x, y, dx, dy, role))"]
```

---

## GameRenderer — flujo de render

```mermaid
flowchart TD
    DR["GameRenderer.draw(surface, session, dx, dy)"]
    DR --> M1["map_r.draw_layer(surface, offset, 'water')"]
    DR --> M2["map_r.draw_layer(surface, offset, 'cliff')"]
    DR --> P["por cada player en received_players\ndraw_player(surface, dx, dy, player)"]
    DR --> SH["por cada ship en received_ships\ndraw_ship(surface, dx, dy, ship)"]
    DR --> EN["por cada enemy en received_enemies\ndraw_enemy(surface, dx, dy, enemy)"]
    DR --> BU["por cada bullet en received_bullets\ndraw_bullet(surface, x+dx, y+dy, role, dx, dy)"]
    DR --> M3["map_r.draw_layer(surface, offset, 'buildings')"]
    DR --> CA["draw_castles(surface, dx, dy, castles)"]
    DR --> UI["draw_ui(surface, dx, dy, session, map_r)"]

    P --> P1["frames = assets.players[role][state]\nblit(frames[anim_frame], x+dx, y+dy)"]
    BU --> BU1["angle = atan2(-dy, dx) - 90°\nrotated = rotate(assets.bullets[role], angle)\nblit(rotated, center=(x,y))"]
    UI --> MM["draw_minimap(surface, session, map_r)"]
```

---

## Tabla de responsabilidades detallada

| Operación | `ServerSession` | `ClientSession` | `GameRenderer` | `AssetStore` |
|---|:---:|:---:|:---:|:---:|
| Almacenar posiciones canónicas | ✓ | | | |
| Validar colisiones con mapa | ✓ | | | |
| Pathfinding A* | ✓ | | | |
| Mover barcos y enemigos | ✓ | | | |
| Mover balas | ✓ | | | |
| Spawn de entidades | ✓ | | | |
| Gestionar conexiones WS | ✓ | | | |
| Serializar estado → GameSnapshot | ✓ | | | |
| Almacenar snapshots recibidos | | ✓ | | |
| Aplicar GameSnapshot del servidor | | ✓ | | |
| Almacenar sprites / MapRender | | | | ✓ |
| Renderizar mapa por capas | | | ✓ | |
| Renderizar jugadores / barcos / balas | | | ✓ | |
| Renderizar HUD y minimap | | | ✓ | |
| Procesar input | | | | |
