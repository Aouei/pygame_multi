# Paso de Mensajes

Toda la comunicación entre cliente y servidor se realiza mediante **WebSockets** con mensajes **JSON**.
Cada mensaje incluye un campo `"type"` que corresponde a un valor de la enum `MESSAGES`.

---

## Catálogo de mensajes

| `type` (enum) | Valor JSON | Dirección | Descripción |
|---|---|---|---|
| `MESSAGES.HELLO` | `"hello"` | Servidor → Cliente | Asigna ID al cliente recién conectado |
| `MESSAGES.ROLE` | `"role"` | Cliente → Servidor | Notifica el rol elegido; enviado al conectar, antes de recibir `HELLO` |
| `MESSAGES.WISH_MOVE` | `"wish_mode"` | Cliente → Servidor | Solicita mover al jugador (delta + estado); solo si hay movimiento o cambio de estado |
| `MESSAGES.SHOT` | `"shot"` | Cliente → Servidor | Solicita disparar una bala (dirección normalizada ≠ 0) |
| `MESSAGES.PLAYERS_UPDATE` | `"players_update"` | Servidor → todos | Snapshot completo: jugadores, balas, barcos, enemigos y castillos (20Hz) |
| `MESSAGES.ROUND_START` | `"round_start"` | Servidor → todos | Nueva oleada generada; enviado cuando `__check_round()` spawna barcos |
| `MESSAGES.QUIT` | `"quit"` | Servidor → Cliente | El jugador es expulsado (murió o todos los castillos cayeron) |

### Formato JSON de cada mensaje

=== "HELLO"
    ```json
    {
      "type": "hello",
      "id": 2
    }
    ```

=== "ROLE"
    ```json
    {
      "type": "role",
      "role": "mage"
    }
    ```

=== "WISH_MOVE"
    ```json
    {
      "type": "wish_mode",
      "dx": -5,
      "dy": 0,
      "state": "left"
    }
    ```

=== "SHOT"
    ```json
    {
      "type": "shot",
      "role": "archer",
      "dx": 0.707,
      "dy": -0.707
    }
    ```

=== "PLAYERS_UPDATE"
    ```json
    {
      "type": "players_update",
      "clients": 2,
      "players": {
        "0": { "x": 320, "y": 192, "state": "down", "role": "archer", "live": 10, "radius": 32 },
        "2": { "x": 640, "y": 448, "state": "right", "role": "mage",   "live": 10, "radius": 32 }
      },
      "bullets": [
        { "x": 400, "y": 200, "dx": 0.707, "dy": -0.707, "role": "archer" }
      ],
      "ships": [
        { "x": 960, "y": 320, "state": "left" }
      ],
      "enemies": [
        { "x": 800, "y": 400, "state": "down", "variant": 1 }
      ],
      "castles": {
        "0": { "x": 256, "y": 256, "live": 5 }
      }
    }
    ```

=== "ROUND_START"
    ```json
    {
      "type": "round_start"
    }
    ```

=== "QUIT"
    ```json
    {
      "type": "quit"
    }
    ```

---

## Secuencia: conexión e inicio de partida

Flujo completo desde que el usuario lanza `client.exe` hasta que entra en el game loop.

```mermaid
sequenceDiagram
    actor User as Usuario
    participant CLI as client.py
    participant L  as lobby.Screen
    participant G  as game.Game
    participant WS as WebSocket
    participant S  as Server
    participant SL as server_logic.Logic

    User->>CLI: lanza client.exe
    CLI->>L: LOBBY.reset()
    CLI->>L: LOBBY.loop(window, clock)
    L->>L: bucle síncrono — muestra selección de rol
    User->>L: selecciona ROLE (enter/botón)
    L-->>CLI: retorna ROLE seleccionado

    CLI->>G: asyncio.run(GAME.run(role))
    G->>G: LOGIC.reset()
    G->>WS: websockets.connect(ws://host:25565)
    WS->>S: handle_client(socket) — nueva corrutina
    S->>SL: new_player(socket) → ID asignado
    SL-->>S: ID (0–3)

    S->>WS: send(HELLO {id})
    WS-->>G: HELLO {id}
    G->>G: LOGIC.ID = data["id"]

    G->>WS: send(ROLE {role})
    WS->>S: recibe ROLE
    S->>SL: handle_message(ID, ROLE)
    SL->>SL: __set_player_class() — crea Player en spawn aleatorio

    Note over G,S: Dos tareas asyncio arrancan en paralelo
    G->>G: recv_task = create_task(receive_from_server)
    G->>G: await loop(websocket)
```

---

## Secuencia: game loop (estado estable)

Muestra la comunicación bidireccional asíncrona durante la partida.

```mermaid
sequenceDiagram
    participant GL as Game.loop() — 60fps
    participant GR as Game.receive_from_server()
    participant WS as WebSocket
    participant SH as Server.handle_client()
    participant SL as Server.loop() — 20Hz
    participant LG as server_logic.Logic

    loop Cada frame (60fps)
        GL->>GL: InputHandler.update()
        GL->>GL: Player.wish_to_move(inputs)
        alt hay movimiento (dx!=0 o dy!=0)
            GL->>WS: send(WISH_MOVE {dx, dy, state})
            WS->>SH: recibe WISH_MOVE
            SH->>LG: handle_message(ID, WISH_MOVE)
            LG->>LG: __try_move() → MAP.is_collision()
        end
        GL->>GL: Player.wish_to_shoot(inputs, offset)
        alt disparo solicitado
            GL->>WS: send(SHOT {role, dx, dy})
            WS->>SH: recibe SHOT
            SH->>LG: handle_message(ID, SHOT)
            LG->>LG: __new_bullet() — crea Bullet
        end
        GL->>GL: LOGIC.draw() — mapa, jugadores, barcos, balas, minimap
        GL->>GL: pygame.display.flip()
        GL->>GL: await asyncio.sleep(0) — cede control
    end

    loop Cada 50ms (20Hz)
        SL->>LG: tick()
        LG->>LG: __check_round() — spawn barcos si no hay
        LG->>LG: __move_ships() — mueven barcos step-by-step
        LG->>LG: __move_bullets() — mueven balas, detectan colisiones
        SL->>LG: serialize() → {players, bullets, ships}
        SL->>WS: broadcast(PLAYERS_UPDATE)
        WS-->>GR: recibe PLAYERS_UPDATE
        GR->>GR: LOGIC.update_players(players)
        GR->>GR: LOGIC.update_bullets(bullets)
        GR->>GR: LOGIC.update_ships(ships)
    end
```

---

## Secuencia: spawn de barcos

Flujo que ocurre automáticamente en el servidor cuando no quedan barcos en juego.

```mermaid
sequenceDiagram
    participant SL as Server.loop() — 20Hz
    participant LG as server_logic.Logic
    participant CT as Counter (spawn_timer)
    participant MD as MapData

    Note over SL,MD: Cuando STATE.SHIPS está vacío

    SL->>LG: tick()
    LG->>LG: __check_round()
    LG->>CT: reset() — mientras haya barcos
    Note over CT: Sin barcos → spawn_timer.tick() cada tick
    CT-->>LG: True — han pasado 10 segundos

    LG->>MD: random.sample(ship_spawn_tiles, n)
    LG->>MD: random.sample(disembark_tiles, n)
    loop Por cada spawn/target
        LG->>MD: find_path(sx, sy, tx, ty, COLLISIONS.SHIP)
        MD-->>LG: list[STATE] — ruta A*
        LG->>LG: Ship(x, y, path, target_x, target_y)
        LG->>LG: STATE.SHIPS.append(ship)
    end
    Note over LG: Cada tick siguiente: __move_ships()
```

---

## Secuencia: desconexión de un cliente

```mermaid
sequenceDiagram
    participant G  as game.Game
    participant WS as WebSocket
    participant S  as Server
    participant SL as server_logic.Logic
    participant OC as Otros Clientes

    alt El jugador pulsa quit
        G->>G: inputs.quit = True → sale del loop
        G->>G: recv_task.cancel()
        G-->>WS: cierra conexión WebSocket
    else Pérdida de conexión
        WS->>WS: ConnectionClosed exception
    end

    WS->>S: handle_client — ConnectionClosed capturada
    Note over S: bloque finally
    S->>SL: remove_player(ID)
    SL->>SL: CLIENTS.pop(ID)
    SL->>SL: PLAYERS.pop(ID)

    Note over S,OC: Próximo tick del broadcast loop
    S->>SL: serialize() — ya sin el jugador eliminado
    S->>WS: broadcast(PLAYERS_UPDATE) — players sin ese ID
    WS-->>OC: reciben snapshot actualizado
```

---

## Flujo de despacho de mensajes en el servidor

```mermaid
flowchart TD
    A["WebSocket recibe mensaje JSON"] --> B["json.loads(message)"]
    B --> C{"MESSAGES(data['type'])"}

    C -->|ROLE| D["__set_player_class(id, data)"]
    C -->|WISH_MOVE| E["__try_move(id, data)"]
    C -->|SHOT| F["__new_bullet(id, data)"]
    C -->|otros| G["ignorado"]

    D --> D1["ROLE(data['role'])"]
    D1 --> D2["Player creado con rol"]
    D2 --> D3["MAP.spawn() — posición aleatoria"]

    E --> E1["dx, dy, state = data[...]"]
    E1 --> E2["Geometry(new_x, new_y, radius)"]
    E2 --> E3{"colisión con ship\no castillo\no mapa?"}
    E3 -->|False| E4["player.x, player.y = new_x, new_y"]
    E3 -->|True| E5["movimiento descartado"]

    F --> F1["dx, dy, role = data[...]"]
    F1 --> F2["x = player.x + dx * BULLET_VELOCITY\ny = player.y + dy * BULLET_VELOCITY"]
    F2 --> F3["BULLETS.append(Bullet(x, y, dx, dy, role))"]
```

### Mensajes enviados por el servidor (salientes)

```mermaid
flowchart TD
    T["Server.loop() — cada 50ms"] --> A{"CLIENTS vacío?"}
    A -->|Sí| Z["skip"]
    A -->|No| TK["Logic.tick()"]
    TK --> NR{"new_round?"}
    NR -->|Sí| RS["broadcast → ROUND_START"]
    NR -->|No| DP
    RS --> DP{"died_players?"}
    DP -->|Sí| QT["send → QUIT a cada jugador muerto\nremove_player(id)"]
    DP -->|No| SER
    QT --> SER["Logic.serialize()"]
    SER --> BC["broadcast → PLAYERS_UPDATE\na todos los clientes restantes"]
```

---

## Flujo de tick del servidor (20Hz)

```mermaid
flowchart TD
    T["Logic.tick()"] --> A{"CLIENTS vacío?"}
    A -->|Sí| Z["saltar"]
    A -->|No| B["__check_round()"]
    B --> B1{"SHIPS vacío?"}
    B1 -->|No| B2["spawn_timer.reset()"]
    B1 -->|Sí| B3["spawn_timer.tick()"]
    B3 -->|False| B4["esperar más ticks"]
    B3 -->|True| B5["generar N barcos con ruta A*"]
    B --> C["__move_ships()"]
    C --> C1["por cada Ship con path\nmover speed px hacia target_x/y\nal llegar: pop path[0], next target"]
    C --> D["__move_bullets()"]
    D --> D1["por cada Bullet\nnew_x = x + dx * VELOCITY\nnew_y = y + dy * VELOCITY"]
    D1 --> D2{"colisiona con Ship?"}
    D2 -->|Sí| D3["ship.live -= 1\nsi live ≤ 0: eliminar ship\neliminar bullet"]
    D2 -->|No| D4{"MAP.is_collision\n(COLLISIONS.BULLET)?"}
    D4 -->|Sí| D5["eliminar bullet"]
    D4 -->|No| D6["bullet.x, bullet.y = new_x, new_y"]
```
