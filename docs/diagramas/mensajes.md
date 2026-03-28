# Paso de Mensajes

Toda la comunicación entre cliente y servidor se realiza mediante **WebSockets** con mensajes **JSON**.
Cada mensaje incluye un campo `"type"` que corresponde a un valor de la enum `MESSAGES` (definida en `adapters/messages.py`).

---

## Catálogo de mensajes

| `type` (enum) | Valor JSON | Dirección | Descripción |
|---|---|---|---|
| `MESSAGES.HELLO` | `"hello"` | Servidor → Cliente | Asigna ID al cliente recién conectado |
| `MESSAGES.ROLE` | `"role"` | Cliente → Servidor | Notifica el rol elegido; enviado al conectar |
| `MESSAGES.WISH_MOVE` | `"wish_mode"` | Cliente → Servidor | Solicita mover al jugador (delta + estado); solo si hay movimiento o cambio de estado |
| `MESSAGES.SHOT` | `"shot"` | Cliente → Servidor | Solicita disparar una bala (dirección normalizada ≠ 0) |
| `MESSAGES.PLAYERS_UPDATE` | `"players_update"` | Servidor → todos | `GameSnapshot` completo: jugadores, balas, barcos, enemigos y castillos (20Hz) |
| `MESSAGES.ROUND_START` | `"round_start"` | Servidor → todos | Nueva oleada generada |
| `MESSAGES.QUIT` | `"quit"` | Servidor → Cliente | El jugador es expulsado (murió o todos los castillos cayeron) |
| `MESSAGES.SHUT_DOWN` | `"shut_down"` | Servidor → Cliente | El servidor se está apagando |

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
        "0": { "x": 320, "y": 192, "state": "down", "role": "archer", "live": 10 },
        "2": { "x": 640, "y": 448, "state": "right", "role": "mage",   "live": 20 }
      },
      "bullets": [
        { "x": 400, "y": 200, "dx": 0.707, "dy": -0.707, "role": "archer" }
      ],
      "ships": [
        { "x": 960, "y": 320, "state": "left", "live": 20 }
      ],
      "enemies": [
        { "x": 800, "y": 400, "state": "down", "live": 5, "variant": 1 }
      ],
      "castles": {
        "0": { "x": 256, "y": 256, "live": 150 }
      }
    }
    ```

=== "QUIT / ROUND_START / SHUT_DOWN"
    ```json
    { "type": "quit" }
    { "type": "round_start" }
    { "type": "shut_down" }
    ```

---

## Secuencia: conexión e inicio de partida

Flujo completo desde que el usuario lanza el cliente hasta que entra en el game loop.

```mermaid
sequenceDiagram
    actor User as Usuario
    participant L  as lobby.Screen
    participant LS as LobbyService
    participant WSR as ws_runner
    participant G  as game.Game
    participant WS as WebSocket
    participant WSSH as ws_server_handler
    participant SS as ServerSession

    User->>L: lanza cliente
    L->>L: bucle síncrono — selección de rol

    opt Host
        User->>L: click "Host"
        L->>LS: start_hosting()
        LS->>WSR: asyncio.run(run(session)) en thread
        WSR->>SS: ServerSession() creado
    end

    User->>L: click "Connect"
    L->>L: _connect_ws() — sondea player_count

    User->>L: selecciona ROLE + click "Play"
    L-->>G: retorna ROLE seleccionado

    G->>WS: websockets.connect(ws://host:port)
    WS->>WSSH: handle_client(socket, session)
    WSSH->>SS: new_player(socket) → ID asignado

    WSSH->>WS: send(HELLO {id})
    WS-->>G: HELLO {id}
    G->>G: session.ID = data["id"]

    G->>WS: send(ROLE {role})
    WS->>WSSH: recibe ROLE
    WSSH->>SS: handle_message(ID, {type: role})
    SS->>SS: __set_player_class() — Player en spawn aleatorio

    Note over G,SS: Dos tareas asyncio arrancan en paralelo
    G->>G: recv_task = create_task(receive_from_server)
    G->>G: await loop(websocket)
```

---

## Secuencia: game loop (estado estable)

```mermaid
sequenceDiagram
    participant GL as Game.loop() — 60fps
    participant GR as Game.receive_from_server()
    participant WS as WebSocket
    participant WSSH as ws_server_handler
    participant WSR as ws_runner._game_loop() — 20Hz
    participant SS as ServerSession

    loop Cada frame (60fps)
        GL->>GL: InputHandler.update()
        GL->>GL: InputAdapter.read() → PlayerIntention
        GL->>GL: translate_move(intention, speed) → dx, dy, state
        alt hay movimiento o cambio de estado
            GL->>WS: send(WISH_MOVE {dx, dy, state})
            WS->>WSSH: handle_message(ID, WISH_MOVE)
            WSSH->>SS: handle_message → __try_move()
            SS->>SS: MAP.is_collision() — valida posición
        end
        GL->>GL: translate_shoot(intention, player_x, player_y, offset)
        alt disparo solicitado (dx,dy != 0)
            GL->>WS: send(SHOT {role, dx, dy})
            WS->>WSSH: handle_message(ID, SHOT)
            WSSH->>SS: handle_message → __new_bullet()
        end
        GL->>GL: GameRenderer.draw(surface, session, dx, dy)
        GL->>GL: pygame.display.flip()
        GL->>GL: await asyncio.sleep(0)
    end

    loop Cada 50ms (20Hz)
        WSR->>SS: tick()
        SS->>SS: __check_round() — spawn barcos
        SS->>SS: __move(ships/enemies)
        SS->>SS: __move_bullets() — colisiones
        SS->>SS: __check_enemy_hit_with_*()
        WSR->>SS: snapshot() → GameSnapshot
        WSR->>WS: broadcast(PLAYERS_UPDATE via update_clients)
        WS-->>GR: recibe PLAYERS_UPDATE
        GR->>GR: GameSnapshot.from_wire(data)
        GR->>GR: session.apply_snapshot(snapshot)
    end
```

---

## Secuencia: spawn de barcos (servidor)

```mermaid
sequenceDiagram
    participant WSR as ws_runner._game_loop()
    participant SS as ServerSession
    participant CT as Counter (spawn_ship_timer)
    participant MD as MapData

    Note over WSR,MD: Cuando SHIPS está vacío

    WSR->>SS: tick()
    SS->>SS: __check_round()
    SS->>CT: reset() — mientras haya barcos o enemigos
    Note over CT: Sin barcos ni enemigos → tick() cada llamada
    CT-->>SS: True — han pasado 30 segundos

    SS->>MD: random.sample(ship_spawn_tiles, n)
    SS->>MD: random.sample(disembark_tiles, n)
    loop Por cada spawn/target
        SS->>MD: find_path(sc, sr, tc, tr, COLLISIONS.SHIP)
        MD-->>SS: list[STATE] — ruta A*
        SS->>SS: Ship(x, y, path, target_x, target_y)
        SS->>SS: SHIPS.append(ship)
    end
```

---

## Secuencia: desconexión de un cliente

```mermaid
sequenceDiagram
    participant G  as game.Game
    participant WS as WebSocket
    participant WSSH as ws_server_handler
    participant SS as ServerSession
    participant OC as Otros Clientes

    alt El jugador pulsa quit
        G->>G: inputs.quit = True → sale del loop
        G->>G: recv_task.cancel()
        G-->>WS: cierra conexión WebSocket
    else Pérdida de conexión
        WS->>WS: ConnectionClosed exception
    end

    WS->>WSSH: handle_client — bloque finally
    WSSH->>SS: remove_player(ID)
    SS->>SS: CLIENTS.pop(ID)\nPLAYERS.pop(ID)

    Note over WSSH,OC: Próximo tick del broadcast loop
    WSSH->>SS: snapshot() — ya sin el jugador eliminado
    WSSH->>WS: broadcast(PLAYERS_UPDATE) — players sin ese ID
    WS-->>OC: reciben snapshot actualizado
```

---

## Flujo de despacho de mensajes en el servidor

```mermaid
flowchart TD
    A["ws_server_handler: WebSocket recibe mensaje"] --> B["json.loads(message)"]
    B --> C["session.handle_message(ID, data)"]
    C --> D{data type}

    D -->|role| E["__set_player_class(id, data)"]
    E --> E1["MAP.spawn() — posición aleatoria"]
    E1 --> E2["PLAYERS[id] = Player(role, x, y)"]

    D -->|wish_mode| F["__try_move(id, data)"]
    F --> F1["Geometry(new_x, new_y, radius)"]
    F1 --> F2{"colisión con ship\no castillo o mapa?"}
    F2 -->|False| F3["player.x, player.y = new_x, new_y"]
    F2 -->|True| F4["movimiento descartado"]

    D -->|shot| G["__new_bullet(id, data)"]
    G --> G1["x = player.x + dx * BULLET_VELOCITY"]
    G1 --> G2["BULLETS.append(Bullet(x, y, dx, dy, role))"]
```

---

## Flujo de mensajes salientes del servidor (20Hz)

```mermaid
flowchart TD
    T["ws_runner._game_loop() — cada 50ms"] --> A{"CLIENTS vacío?"}
    A -->|Sí| Z["session.reset() — vuelve a esperar"]
    A -->|No| TK["session.tick()"]
    TK --> DP{"died_players?"}
    DP -->|Sí| QT["send QUIT a cada jugador muerto\nremove_player(id)"]
    DP -->|No| SER
    QT --> SER["session.snapshot() → GameSnapshot"]
    SER --> TW["snapshot.to_wire() → dict"]
    TW --> BC["messages.update_clients(snapshot)\n→ broadcast PLAYERS_UPDATE"]
```
