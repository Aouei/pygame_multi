# Paso de Mensajes

Toda la comunicación entre cliente y servidor se realiza mediante **WebSockets** con mensajes **JSON**.
Cada mensaje incluye un campo `"type"` que corresponde a un valor de la enum `MESSAGES`.

---

## Catálogo de mensajes

| `type` (enum) | Valor JSON | Dirección | Descripción |
|---|---|---|---|
| `MESSAGES.HELLO` | `"hello"` | Servidor → Cliente | Asigna ID al cliente recién conectado |
| `MESSAGES.PLAYER_CLASS` | `"player_class"` | Cliente → Servidor | Notifica la clase elegida en el lobby |
| `MESSAGES.WISH_MOVE` | `"wish_mode"` | Cliente → Servidor | Solicita mover al jugador (delta + estado) |
| `MESSAGES.PLAYERS_UPDATE` | `"players_update"` | Servidor → todos | Snapshot de posiciones de todos los jugadores |
| `MESSAGES.MOVE` | `"move"` | — | Definido, no usado actualmente |

### Formato JSON de cada mensaje

=== "HELLO"
    ```json
    {
      "type": "hello",
      "id": 2
    }
    ```

=== "PLAYER_CLASS"
    ```json
    {
      "type": "player_class",
      "class": "mage"
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

=== "PLAYERS_UPDATE"
    ```json
    {
      "type": "players_update",
      "players": {
        "0": { "x": 320, "y": 192, "state": "down", "type_class": "archer" },
        "2": { "x": 640, "y": 448, "state": "right", "type_class": "mage" }
      }
    }
    ```

---

## Secuencia: conexión e inicio de partida

Flujo completo desde que el usuario lanza `client.exe` hasta que entra en el game loop.

```mermaid
sequenceDiagram
    actor User as Usuario
    participant L  as Screen (lobby)
    participant C  as Client
    participant WS as WebSocket
    participant S  as Server
    participant SS as ServerState

    User->>L: lanza client.exe
    L->>L: loop() — muestra selección de clase
    User->>L: selecciona PLAYER_CLASS (enter/botón)
    L-->>C: retorna PLAYER_CLASS seleccionada

    C->>WS: websockets.connect(ws://host:25565)
    WS->>S: handle_client(socket) — nueva corrutina
    S->>SS: new_player(socket) → ID asignado
    SS-->>S: ID (0-3)

    S->>WS: send(HELLO {id})
    WS-->>C: HELLO {id}
    C->>C: self.ID = data["id"]

    C->>WS: send(PLAYER_CLASS {class})
    WS->>S: recibe PLAYER_CLASS
    S->>SS: handle_message(ID, PLAYER_CLASS)
    SS->>SS: __set_player_class() — crea Player
    SS->>SS: Player.move(*MAP.spawn(), STATE.DOWN)

    Note over C,S: Ambas corrutinas arrancan en paralelo
    C->>C: asyncio.gather(update(), loop())
```

---

## Secuencia: game loop (estado estable)

Muestra la comunicación bidireccional asíncrona durante la partida.

```mermaid
sequenceDiagram
    participant CL as Client.loop() — 60fps
    participant CU as Client.update() — async recv
    participant WS as WebSocket
    participant SH as Server.handle_client()
    participant SL as Server.loop() — 20Hz
    participant SS as ServerState

    loop Cada frame (60fps)
        CL->>CL: InputHandler.update()
        CL->>CL: Player.wish_to_move(inputs)
        alt hay movimiento (dx!=0 o dy!=0)
            CL->>WS: send(WISH_MOVE {dx, dy, state})
            WS->>SH: recibe WISH_MOVE
            SH->>SS: handle_message(ID, WISH_MOVE)
            SS->>SS: __try_move()
            SS->>SS: Map.is_collision(x+dx, y+dy, mask)
            alt sin colisión
                SS->>SS: Player.move(x+dx, y+dy, state)
            end
        end

        CL->>CL: interpolar render_positions ← server_positions
        CL->>CL: Map.draw() + draw_player() × N
        CL->>CL: Map.draw_mini()
        CL->>CL: pygame.display.flip()
        CL->>CL: await asyncio.sleep(0) — cede control
    end

    loop Cada 50ms (20Hz)
        SL->>SS: get_players() → dict de todos
        SL->>WS: broadcast(PLAYERS_UPDATE) a todos los clientes
        WS-->>CU: recibe PLAYERS_UPDATE
        CU->>CU: server_positions.update(players)
        CU->>CU: inicializa render_positions para nuevos PIDs
        CU->>CU: elimina render_positions de PIDs desconectados
    end
```

---

## Secuencia: desconexión de un cliente

```mermaid
sequenceDiagram
    participant C  as Client
    participant WS as WebSocket
    participant S  as Server
    participant SS as ServerState
    participant OC as Otros Clientes

    alt El cliente cierra la ventana
        C->>C: pygame.quit() / sys.exit()
        C->>WS: cierra conexión WebSocket
    else El cliente pierde conexión
        WS->>WS: ConnectionClosed exception
    end

    WS->>S: handle_client — ConnectionClosed capturada
    Note over S: bloque finally
    S->>SS: remove_player(ID)
    SS->>SS: clients.pop(ID)
    SS->>SS: players.pop(ID)

    Note over SL,OC: Próximo tick del broadcast loop
    S->>SS: get_players() — ya sin el jugador eliminado
    S->>WS: broadcast(PLAYERS_UPDATE) — players sin ese ID
    WS-->>OC: reciben PLAYERS_UPDATE actualizado
    OC->>OC: render_positions.pop(ID desaparecido)
```

---

## Flujo de despacho de mensajes en el servidor

```mermaid
flowchart TD
    A["WebSocket recibe mensaje JSON"] --> B["json.loads"]
    B --> C{"message_type"}
    C -->|PLAYER_CLASS| D["__set_player_class()"]
    C -->|WISH_MOVE| E["__try_move()"]
    C -->|otros| F["ignorado"]

    D --> G["PLAYER_CLASS(data['class'])"]
    G --> H["Player creado con clase"]
    H --> I["MAP.spawn() — posición aleatoria"]
    I --> J["Player.move a spawn"]

    E --> K["extraer dx, dy, state"]
    K --> L["MAP.is_collision(x+dx, y+dy, mask)"]
    L -->|"False — sin colisión"| M["Player.move a nueva posición"]
    L -->|"True — colisión"| N["movimiento descartado"]
```