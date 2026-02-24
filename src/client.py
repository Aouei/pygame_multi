import asyncio
import json
import os
import sys
import pygame
import websockets
import pandas as pd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
FRAME_RATE   = 60
PLAYER_SPEED = 5
PLAYER_SIZE  = 64
TILE_SIZE    = 64
BACKGROUND_COLOR = (127, 64, 0)

# Interpolation factor: how quickly remote players catch up to their server
# position each frame.  0.0 = never moves, 1.0 = instant snap.
LERP_ALPHA = 0.2

# ---------------------------------------------------------------------------
# Paths (relative to this file so the project is portable)
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
ASSETS_DIR  = os.path.join(BASE_DIR, "assets")
PLAYER_DIR  = os.path.join(ASSETS_DIR, "player")
TILES_DIR   = os.path.join(ASSETS_DIR, "tiles")
MAP_PATH    = os.path.join(ASSETS_DIR, "map", "map.csv")

PLAYER = {
    'up' : pygame.transform.scale(pygame.image.load(os.path.join(PLAYER_DIR, "up.png")), (PLAYER_SIZE, PLAYER_SIZE)),
    'down' : pygame.transform.scale(pygame.image.load(os.path.join(PLAYER_DIR, "down.png")), (PLAYER_SIZE, PLAYER_SIZE)),
    'right' : pygame.transform.scale(pygame.image.load(os.path.join(PLAYER_DIR, "right.png")), (PLAYER_SIZE, PLAYER_SIZE)),
    'left' : pygame.transform.scale(pygame.image.load(os.path.join(PLAYER_DIR, "left.png")), (PLAYER_SIZE, PLAYER_SIZE)),
}
CURRENT_STATE = 'down'

# ---------------------------------------------------------------------------
# Pygame setup
# ---------------------------------------------------------------------------
pygame.init()
pygame.joystick.init()
window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
WIDTH, HEIGHT = window.get_size()
clock = pygame.time.Clock()

# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------
TILES = {
    str(i): pygame.transform.scale(
        pygame.image.load(os.path.join(TILES_DIR, f"tile_{i}_{'shore' if i <= 5 else 'grass'}.png")),
        (TILE_SIZE, TILE_SIZE),
    )
    for i in range(1, 11)
}

map_data = pd.read_csv(MAP_PATH, header=None)
MINIMAP_SIZE = 200  # Size of minimap square
MINIMAP_MARGIN = 20 # Margin from top-left corner
PLAYER_COLORS = [(255,0,0), (0,255,0), (0,0,255), (255,255,0)]

def render_minimap(surface: pygame.Surface, player_positions: dict, my_id: int | None):
    # Draw minimap background
    minimap = pygame.Surface((MINIMAP_SIZE, MINIMAP_SIZE))
    minimap.fill((30, 30, 30))
    # Draw map tiles (scaled down)
    rows, cols = map_data.shape
    tile_w = MINIMAP_SIZE / cols
    tile_h = MINIMAP_SIZE / rows
    for i, row in enumerate(map_data.values):
        for j, col in enumerate(row):
            color = (80, 40, 0) if int(col) <= 5 else (60, 120, 60)
            pygame.draw.rect(minimap, color, (j*tile_w, i*tile_h, tile_w, tile_h))
    # Draw players
    for idx, (pid, pos) in enumerate(list(player_positions.items())[:4]):
        px = pos["x"] / (cols * TILE_SIZE) * MINIMAP_SIZE
        py = pos["y"] / (rows * TILE_SIZE) * MINIMAP_SIZE
        color = PLAYER_COLORS[idx % 4]
        radius = 8 if str(pid) == str(my_id) else 6
        pygame.draw.circle(minimap, color, (int(px), int(py)), radius)
    # Blit minimap to main surface
    surface.blit(minimap, (MINIMAP_MARGIN, MINIMAP_MARGIN))

def draw_map(surface: pygame.Surface) -> None:
    for i, row in enumerate(map_data.values):
        for j, col in enumerate(row):
            surface.blit(TILES[str(col)], (j * TILE_SIZE, i * TILE_SIZE))

# Pre-render map onto a static surface so we only blit once per frame
MAP_SURFACE = pygame.Surface((len(map_data.columns) * TILE_SIZE, len(map_data) * TILE_SIZE))
draw_map(MAP_SURFACE)

# ---------------------------------------------------------------------------
# Game state
# ---------------------------------------------------------------------------
my_id: int | None = None

# server_positions holds the authoritative positions received from the server.
# render_positions holds the smoothly interpolated positions used for drawing.
server_positions: dict[str, dict] = {}
render_positions: dict[str, dict] = {}

# Local predicted position for our own player (updated every frame immediately)
local_pos: dict = {"x": 0.0, "y": 0.0, "ready": False}


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------
def get_input() -> tuple[int, int]:
    global CURRENT_STATE
    dx, dy = 0, 0

    if pygame.joystick.get_count() > 0:
        js = pygame.joystick.Joystick(0)
        js.init()
        deadzone = 0.2
        ax = js.get_axis(0)
        ay = js.get_axis(1)
        if abs(ax) > deadzone:
            dx = int(ax * PLAYER_SPEED)
        if abs(ay) > deadzone:
            dy = int(ay * PLAYER_SPEED)
    else:
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:  
            dx = -PLAYER_SPEED
            CURRENT_STATE = 'left'
        if keys[pygame.K_RIGHT]: 
            dx =  PLAYER_SPEED
            CURRENT_STATE = 'right'
        if keys[pygame.K_UP]:    
            dy = -PLAYER_SPEED
            CURRENT_STATE = 'up'
        if keys[pygame.K_DOWN]:  
            dy =  PLAYER_SPEED
            CURRENT_STATE = 'down'
    return dx, dy


# ---------------------------------------------------------------------------
# Receive coroutine — runs concurrently with the game loop
# ---------------------------------------------------------------------------
async def receive_loop(websocket) -> None:
    """Continuously reads server messages and updates shared state."""
    global my_id
    async for raw in websocket:
        data = json.loads(raw)
        if data["type"] == "hello":
            my_id = data["id"]
        elif data["type"] == "update":
            server_positions.clear()
            server_positions.update(data.get("players", {}))
            # Initialise render position for newly connected players
            for pid, pos in server_positions.items():
                if pid not in render_positions:
                    render_positions[pid] = {"x": float(pos["x"]), "y": float(pos["y"])}
                # Initialise local prediction from the first server position we receive
                if str(pid) == str(my_id) and not local_pos["ready"]:
                    local_pos["x"] = float(pos["x"])
                    local_pos["y"] = float(pos["y"])
                    local_pos["ready"] = True
            # Remove players that have disconnected
            for pid in list(render_positions):
                if pid not in server_positions:
                    del render_positions[pid]


# ---------------------------------------------------------------------------
# Main game loop
# ---------------------------------------------------------------------------
async def game_loop(websocket) -> None:
    global CURRENT_STATE
    while True:
        # --- Events ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit() # TODO: message to server to quit

        keys = pygame.key.get_pressed()
        if keys[pygame.K_ESCAPE]:
            pygame.quit()
            sys.exit() # TODO: message to server to quit

        # --- Input & send ---
        dx, dy = get_input()
        if dx != 0 or dy != 0:
            await websocket.send(json.dumps({"type": "move", "dx": dx, "dy": dy, 'state' : CURRENT_STATE}))

        for pid, srv in server_positions.items():
            rnd = render_positions.get(pid)
            if rnd is None:
                render_positions[pid] = {"x": float(srv["x"]), "y": float(srv["y"])}
                continue
            # All players, including own, update position directly from server
            rnd["x"] = float(srv["x"])
            rnd["y"] = float(srv["y"])
            rnd["state"] = srv["state"]

        # --- Draw ---
        window.fill(BACKGROUND_COLOR)
        window.blit(MAP_SURFACE, (0, 0))

        # Draw minimap in top-left corner
        render_minimap(window, render_positions, my_id)

        for pid, pos in render_positions.items():
            print(pos)
            window.blit(PLAYER[pos['state']], (int(pos["x"]), int(pos["y"]), PLAYER_SIZE, PLAYER_SIZE))

        pygame.display.flip()
        clock.tick(FRAME_RATE)

        # Yield control so receive_loop can run between frames
        await asyncio.sleep(0)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
async def main() -> None:
    async with websockets.connect("ws://25.33.144.47:25565") as websocket:
        await websocket.send(json.dumps({"type": "start", "x": WIDTH, "y": HEIGHT}))
        # Run receive loop and game loop concurrently
        await asyncio.gather(
            receive_loop(websocket),
            game_loop(websocket),
        )


asyncio.run(main())