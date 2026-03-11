# Diagrama de Estados y Condiciones de Mensajes

Esta página muestra los **estados por los que pasan el cliente y el servidor**, y bajo qué condiciones exactas se envía cada mensaje WebSocket — tanto en la fase de **Lobby** como en la de **Juego**.

---

## Estados del cliente

```mermaid
stateDiagram-v2
    [*] --> Lobby

    state Lobby {
        [*] --> Desconectado
        Desconectado --> Monitorizando : btn_connect / btn_host\nWS connect (hilo daemon)
        Monitorizando --> Desconectado : btn_disconnect\nWS close
        Monitorizando --> Monitorizando : ← PLAYERS_UPDATE\nactualiza contador N/4
    }

    Lobby --> Juego : rol seleccionado\n(enter / btn_play + connected)\nWS lobby desconectado

    state Juego {
        [*] --> Conectando
        Conectando --> EnPartida : ← HELLO {id}\nLOGIC.ID asignado

        state EnPartida {
            [*] --> Activo
            Activo --> Activo : → WISH_MOVE\nsi dx≠0 · dy≠0 · o state cambió
            Activo --> Activo : → SHOT\nsi dirección de disparo ≠ (0,0)
            Activo --> Activo : ← PLAYERS_UPDATE\nactualiza jugadores/balas/barcos/enemigos/castillos
            Activo --> Activo : ← ROUND_START\n(nueva oleada — no procesado explícitamente)
            Activo --> Expulsado : ← QUIT\nconnected = False
            Activo --> Saliendo : inputs.quit = True
        }

        Expulsado --> [*]
        Saliendo --> [*]
    }

    Juego --> Lobby : return "lobby"
    Lobby --> [*] : inputs.quit
```

!!! note "ROLE se envía antes de recibir HELLO"
    En `game.py`, el cliente envía `ROLE` **inmediatamente** al establecer la conexión, sin esperar a recibir `HELLO`. El servidor asigna el ID al aceptar la conexión, por lo que el `ROLE` siempre llega cuando el jugador ya está registrado internamente.

---

## Estados del servidor por cliente

```mermaid
stateDiagram-v2
    [*] --> Conectado : handle_client(socket)\nnew_player() → ID asignado

    Conectado --> HelloEnviado : → HELLO {id}

    HelloEnviado --> Registrado : ← ROLE {role}\n__set_player_class()\nPlayer creado en spawn aleatorio

    state Registrado {
        [*] --> Vivo
        Vivo --> Vivo : ← WISH_MOVE\n__try_move() — valida colisión
        Vivo --> Vivo : ← SHOT\n__new_bullet()
        Vivo --> Vivo : tick 20Hz\n→ PLAYERS_UPDATE broadcast
        Vivo --> NuevaOleada : __check_round()\nSHIPS+ENEMIES vacíos y timer agotado
        NuevaOleada --> Vivo : → ROUND_START broadcast\nnuevos Ships generados con A*
        Vivo --> Muerto : tick detecta live ≤ 0\no todos los castillos destruidos
    }

    Muerto --> [*] : → QUIT enviado\nremove_player(id)
    Registrado --> [*] : ConnectionClosed\nremove_player(id)
    HelloEnviado --> [*] : ConnectionClosed\nremove_player(id)
    Conectado --> [*] : no hay slots libres\nID = -1
```

---

## Condiciones de disparo por mensaje

| Mensaje | Dirección | Fase | Condición exacta |
|---|---|---|---|
| `HELLO` | S → C | Juego | Al aceptar nueva conexión WS en `handle_client` |
| `ROLE` | C → S | Juego | Al conectar, antes de recibir `HELLO` (`game.run`) |
| `WISH_MOVE` | C → S | Juego | Cada frame si `dx≠0` ó `dy≠0` ó `state` cambió respecto al último enviado |
| `SHOT` | C → S | Juego | Cada frame si `(dx, dy) ≠ (0, 0)` tras calcular dirección de disparo |
| `PLAYERS_UPDATE` | S → C (broadcast) | Juego | Cada tick (20Hz) si hay al menos 1 cliente conectado |
| `ROUND_START` | S → C (broadcast) | Juego | Cuando `__check_round()` genera una nueva oleada de barcos |
| `QUIT` | S → C | Juego | Cuando `tick()` detecta que un jugador murió (`live ≤ 0`) o todos los castillos cayeron |
| `PLAYERS_UPDATE` | S → C | Lobby | Cada tick (20Hz) — el lobby lo consume solo para leer `clients` (contador) |

---

## Flujo completo Lobby → Juego

```mermaid
sequenceDiagram
    actor U as Usuario
    participant L as lobby.Screen
    participant G as game.Game
    participant S as Server

    U->>L: lanza client.exe
    Note over L: Lobby loop — síncrono 60fps

    opt Monitorizar jugadores conectados
        U->>L: btn_connect / btn_host
        L->>S: WS connect (hilo daemon)
        S-->>L: ← HELLO {id}
        loop cada tick 20Hz
            S-->>L: ← PLAYERS_UPDATE {clients: N}
            L->>L: lbl_players = "N/4"
        end
    end

    U->>L: selecciona rol + enter / btn_play
    L->>L: _disconnect_ws() — cierra WS de monitorización
    L-->>G: retorna ROLE seleccionado

    G->>S: WS connect
    G->>S: → ROLE {role}
    S-->>G: ← HELLO {id}
    Note over G: LOGIC.ID asignado

    par recv_task (asyncio.Task)
        loop recibe mensajes del servidor
            S-->>G: ← PLAYERS_UPDATE
            G->>G: update_players/bullets/ships/enemies/castles
        end
    and loop() — 60fps
        loop cada frame
            G->>G: InputHandler.update()
            opt dx≠0 o dy≠0 o state cambió
                G->>S: → WISH_MOVE {dx, dy, state}
            end
            opt dirección de disparo ≠ (0,0)
                G->>S: → SHOT {role, dx, dy}
            end
            G->>G: LOGIC.draw()
        end
    end

    alt jugador muere / castillos destruidos
        S-->>G: ← QUIT
        G->>G: connected = False → sale del loop
    else usuario pulsa quit
        G->>G: inputs.quit = True → sale del loop
    end

    G-->>L: return "lobby"
```

---

## Tabla resumen de mensajes en Lobby vs Juego

| Mensaje | En Lobby | En Juego |
|---|:---:|:---:|
| `HELLO` | Recibido (ignorado) | Recibido → asigna ID |
| `ROLE` | — | Enviado al conectar |
| `WISH_MOVE` | — | Enviado cada frame (condicional) |
| `SHOT` | — | Enviado cada frame (condicional) |
| `PLAYERS_UPDATE` | Recibido → solo lee `clients` | Recibido → actualiza toda la escena |
| `ROUND_START` | — | Recibido (no procesado explícitamente) |
| `QUIT` | — | Recibido → termina partida |
