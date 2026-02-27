# Estructura de archivos propuesta

Reorganización del proyecto para separar código de servidor y cliente.

## Árbol de archivos

```
pygame_multi/
├── src/
│   ├── server.py              # Entry-point servidor (sin cambios de interfaz)
│   ├── client.py              # Entry-point cliente (sin cambios de interfaz)
│   ├── enums.py               # PLAYER_CLASS, STATE, MESSAGES (+ SHOOT)
│   ├── paths.py               # Rutas de assets
│   ├── factories.py           # load_tiles, load_player, load_bullet, load_ship, load_enemy
│   ├── inputs.py              # InputHandler (+ shoot_dx, shoot_dy)
│   │
│   ├── maps/
│   │   ├── __init__.py
│   │   ├── map_data.py        # MapData  — CSV + KDTree + is_collision(x, y, radius)
│   │   └── map_renderer.py    # MapRenderer(MapData) — sprites tiles + draw + draw_mini
│   │
│   ├── entities/
│   │   ├── __init__.py
│   │   ├── base.py            # ServerEntity — x, y, radius, hp, dump()
│   │   ├── player.py          # ServerPlayer(ServerEntity) + ClientPlayer (sprites)
│   │   ├── bullet.py          # Bullet(ServerEntity) — vx, vy, owner_id
│   │   ├── enemy_ship.py      # EnemyShip(ServerEntity) — vx, vy, landed
│   │   └── enemy.py           # Enemy(ServerEntity) — target_id
│   │
│   ├── server/
│   │   ├── __init__.py
│   │   ├── game_state.py      # GameState — contenedor puro de datos
│   │   └── game_logic.py      # GameLogic — tick, handle_message, serialize
│   │
│   ├── client/
│   │   ├── __init__.py
│   │   └── client_state.py    # ClientState — sprites de actores + draw_*
│   │
│   ├── messages/
│   │   ├── __init__.py
│   │   ├── server_msgs.py     # hello(), players_update()
│   │   └── client_msgs.py     # player_class(), wish_move(), shoot()
│   │
│   └── levels/
│       ├── __init__.py
│       └── lobby.py           # Screen — selección de personaje
│
├── assets/
│   ├── player/
│   ├── bullets/
│   ├── ships/                 # nuevo
│   ├── enemies/               # nuevo
│   ├── tiles/
│   └── map/
│       └── map.csv
│
├── docs/
├── mkdocs.yml
└── build.py
```

## Qué cambia respecto a la estructura actual

| Archivo actual | Destino propuesto | Cambio |
|---|---|---|
| `src/maps.py` | `src/maps/map_data.py` + `src/maps/map_renderer.py` | Split por responsabilidad |
| `src/states.py` | `src/server/game_state.py` + `src/server/game_logic.py` + `src/client/client_state.py` | Split datos / lógica / render |
| `src/entities/player.py` | `src/entities/base.py` + `src/entities/player.py` | Añade `ServerEntity` base |
| `src/messages.py` | `src/messages/server_msgs.py` + `src/messages/client_msgs.py` | Separar dirección |
| — | `src/entities/bullet.py` | Nuevo — bala con física |
| — | `src/entities/enemy_ship.py` | Nuevo |
| — | `src/entities/enemy.py` | Nuevo |
