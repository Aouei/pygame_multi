# Servidor vs Cliente

El proyecto separa la lógica en dos procesos independientes que se comunican exclusivamente por WebSocket.
Cada lado divide además sus responsabilidades entre un objeto **State** (datos) y un objeto **Logic** (comportamiento).

---

## Resumen de responsabilidades

| Aspecto | Servidor | Cliente |
|---|---|---|
| **Proceso** | `server.py` | `client.py` |
| **Fuente de verdad** | Sí — posiciones canónicas | No — recibe snapshots del servidor |
| **Mapa** | `MapData` — valida colisiones, A* | `MapRender` — renderiza tiles y minimap |
| **Jugadores** | `dict[id → Player]` con posición real | Dict de sprites por rol para dibujar |
| **Balas** | Mueve, detecta colisiones y elimina | Dibuja rotadas según dirección |
| **Barcos** | Pathfinding A*, movimiento suave, vida | Dibuja según `state` (dirección) |
| **Conexiones WS** | `dict[id → ClientConnection]` | — |
| **Input** | Nunca toca inputs | `InputHandler` teclado + mando |
| **Pygame / render** | No renderiza nada | Dibuja todo en pantalla a 60fps |
| **Tick rate** | 20Hz — broadcast + física | 60fps — render + envío de intenciones |

---

## Separación State / Logic

Tanto el servidor como el cliente separan los **datos** (State) del **comportamiento** (Logic).

```mermaid
flowchart LR
    subgraph SRV["Servidor"]
        direction TB
        SL["server_logic.Logic\n— handle_message()\n— tick()\n— serialize()"]
        SS["server_state.State\n— CLIENTS\n— PLAYERS\n— BULLETS / SHIPS\n— MAP: MapData"]
        SL -- accede --> SS
    end

    subgraph CLI["Cliente"]
        direction TB
        CL["client_logic.Logic\n— update_players/bullets/ships()\n— draw()"]
        CS["client_state.State\n— players_positions\n— bullets_positions\n— ships_positions\n— MAP: MapRender\n— sprites PLAYERS/SHIPS/BULLETS"]
        CL -- accede --> CS
    end

    SRV <-->|"WebSocket JSON\n(PLAYERS_UPDATE / WISH_MOVE / SHOT)"| CLI
```

---

## MapData (servidor) vs MapRender (cliente)

El mapa se carga dos veces, con responsabilidades distintas:

| Aspecto | `MapData` | `MapRender` |
|---|---|---|
| **Fichero** | `map.py` | `map.py` |
| **Usado en** | `server_state.State` | `client_state.State` |
| **Carga** | CSV con `pandas` → `ndarray` | `MapData` + sprites `pygame` |
| **Colisiones** | KDTree por tipo (`COLLISIONS`) | — |
| **Pathfinding** | A* (`find_path`) sobre grid de tiles | — |
| **Spawn tiles** | Player spawn, ship spawn, disembark | — |
| **Render tiles** | — | `pygame.Surface` precalculada |
| **Minimap** | — | Versión escalada al 10% + máscara circular |

---

## Ciclo de vida de un jugador en el servidor

```mermaid
stateDiagram-v2
    [*] --> Conectado : new_player(socket)\nHELLO enviado
    Conectado --> Registrado : handle_message ROLE\n→ Player creado en spawn
    Registrado --> Registrado : handle_message WISH_MOVE\n→ __try_move()
    Registrado --> Registrado : handle_message SHOT\n→ __new_bullet()
    Registrado --> [*] : ConnectionClosed\n→ remove_player(id)
    Conectado --> [*] : ConnectionClosed\n→ remove_player(id)
```

---

## Ciclo de vida de un barco

```mermaid
stateDiagram-v2
    [*] --> Navegando : __check_round() — Ship creado con path A*
    Navegando --> Navegando : __move_ships() — avanza hacia target, pop path[0] al llegar
    Navegando --> Llegado : path vacio — llego al destino
    Llegado --> [*] : eliminado de SHIPS
    Navegando --> [*] : impactado por bala — live llega a 0
```

---

## Flujo completo de datos (partida en curso)

```mermaid
flowchart LR
    subgraph SERVIDOR["Servidor — proceso autoritativo"]
        direction TB
        IH_S["WISH_MOVE / SHOT\n(intenciones del cliente)"]
        LG["server_logic.Logic\n__try_move()\n__new_bullet()\n__move_bullets()\n__move_ships()\n__check_round()"]
        MD["MapData\nKDTree colisiones\nA* pathfinding"]
        SER["serialize()\n{players, bullets, ships}"]
        IH_S --> LG
        LG <--> MD
        LG --> SER
    end

    subgraph RED["WebSocket — JSON"]
        direction TB
        WS_IN["→ WISH_MOVE / SHOT"]
        WS_OUT["← PLAYERS_UPDATE"]
    end

    subgraph CLIENTE["Cliente — proceso de render"]
        direction TB
        IH_C["InputHandler\nteclado / mando"]
        CG["game.Game\nloop 60fps\nwish_to_move()\nwish_to_shoot()"]
        CL["client_logic.Logic\nupdate_players/bullets/ships()\ndraw()"]
        CS["client_state.State\nposiciones recibidas\nsprites por rol"]
        MR["MapRender\ntiles + minimap circular"]
        IH_C --> CG
        CG -->|"WISH_MOVE / SHOT"| WS_IN
        WS_OUT --> CL
        CL --> CS --> MR
    end

    SER --> WS_OUT
    WS_IN --> IH_S
```

---

## server_logic.Logic — detalle de `handle_message`

```mermaid
flowchart TD
    A["handle_message(id, data)"] --> B["MESSAGES(data['type'])"]
    B --> C{tipo}

    C -->|ROLE| D["__set_player_class(id, data)"]
    D --> D1["x, y = MAP.spawn()"]
    D1 --> D2["PLAYERS[id] = Player(role, x, y)"]

    C -->|WISH_MOVE| E["__try_move(id, data)"]
    E --> E1["new_x = player.x + dx\nnew_y = player.y + dy"]
    E1 --> E2{"MAP.is_collision\n(Geometry, COLLISIONS.PLAYER)"}
    E2 -->|False| E3["player.x, player.y = new_x, new_y"]
    E2 -->|True| E4["movimiento descartado"]

    C -->|SHOT| F["__new_bullet(id, data)"]
    F --> F1["x = player.x + dx * BULLET_VELOCITY\ny = player.y + dy * BULLET_VELOCITY"]
    F1 --> F2["BULLETS.append(Bullet(x, y, dx, dy, role))"]
```

---

## client_logic.Logic — flujo de render

```mermaid
flowchart TD
    DR["Logic.draw(surface, dx, dy)"]
    DR --> M["MAP.draw(surface, offset)"]
    DR --> P["por cada player en players_positions\ndraw_player(surface, dx, dy, data)"]
    DR --> SH["por cada ship en ships_positions\ndraw_ship(surface, dx, dy, data)"]
    DR --> BU["por cada bullet en bullets_positions\ndraw_bullet(surface, x+dx, y+dy, role, vx, vy)"]
    DR --> MM["draw_minimap(surface)"]

    P --> P1["PLAYERS[ROLE][STATE].blit(surface, x+dx, y+dy)"]

    SH --> SH1["SHIPS[STATE].blit(surface, x+dx, y+dy)"]

    BU --> BU1["angle = atan2(-vy, vx) - 90°\nrotated = rotate(BULLETS[ROLE], angle)\nblit(rotated, center=(x,y))"]

    MM --> MM1["minimap_points ← players + ships + local player\nMAP.draw_mini(surface, 16, 16, points, px, py)"]
```

---

## Gestión de IDs en el servidor

```mermaid
flowchart LR
    A["IDS = {0,1,2,3}"] --> B{available_ids}
    C["CLIENTS.keys = {0,2}"] --> B
    B --> D["disponibles = {1,3}"]
    D --> E["new_player toma el primero: 1"]
    E --> F["CLIENTS[1] = socket"]
```

---

## Tabla de responsabilidades detallada

| Operación | `server_state.State` | `server_logic.Logic` | `client_state.State` | `client_logic.Logic` |
|---|:---:|:---:|:---:|:---:|
| Almacenar posiciones canónicas | ✓ | | | |
| Validar colisiones | | ✓ | | |
| Pathfinding A* | | ✓ | | |
| Mover barcos | | ✓ | | |
| Mover balas | | ✓ | | |
| Spawn de entidades | | ✓ | | |
| Gestionar conexiones WS | ✓ | | | |
| Serializar estado | | ✓ | | |
| Almacenar sprites / tiles | | | ✓ | |
| Almacenar snapshots recibidos | | | ✓ | |
| Renderizar mapa | | | | ✓ |
| Renderizar jugadores / barcos / balas | | | | ✓ |
| Renderizar minimap | | | | ✓ |
| Procesar input | | | | ✓ (vía Game) |
