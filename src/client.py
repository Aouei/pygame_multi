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
PLAYER_SIZE  = 32
TILE_SIZE    = 32
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
TILES_DIR   = os.path.join(ASSETS_DIR, "tiles")
MAP_PATH    = os.path.join(ASSETS_DIR, "map", "map.csv")
SPRITE_PATH = os.path.join(ASSETS_DIR, "nave.png")

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
player_sprite = pygame.transform.scale(
    pygame.image.load(SPRITE_PATH), (PLAYER_SIZE, PLAYER_SIZE)
)

TILES = {
    str(i): pygame.transform.scale(
        pygame.image.load(os.path.join(TILES_DIR, f"tile_{i}_{'shore' if i <= 5 else 'grass'}.png")),
        (TILE_SIZE, TILE_SIZE),
    )
    for i in range(1, 11)
}

map_data = pd.read_csv(MAP_PATH, header=None)

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
        if keys[pygame.K_LEFT]:  dx = -PLAYER_SPEED
        if keys[pygame.K_RIGHT]: dx =  PLAYER_SPEED
        if keys[pygame.K_UP]:    dy = -PLAYER_SPEED
        if keys[pygame.K_DOWN]:  dy =  PLAYER_SPEED
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
            # Client-side prediction: move locally right away without waiting
            # for the server tick. The server remains authoritative — if it
            # corrects us we'll snap/lerp back, but in practice on LAN/local
            # the correction is invisible.
            if local_pos["ready"]:
                local_pos["x"] = max(0.0, min(local_pos["x"] + dx, WIDTH  - PLAYER_SIZE))
                local_pos["y"] = max(0.0, min(local_pos["y"] + dy, HEIGHT - PLAYER_SIZE))
            await websocket.send(json.dumps({"type": "move", "dx": dx, "dy": dy}))

        # --- Interpolate remote players toward their server positions ---
        for pid, srv in server_positions.items():
            rnd = render_positions.get(pid)
            if rnd is None:
                render_positions[pid] = {"x": float(srv["x"]), "y": float(srv["y"])}
                continue
            if str(pid) == str(my_id):
                # Own player: use local predicted position, but softly correct
                # toward server position to avoid drifting out of sync.
                if local_pos["ready"]:
                    local_pos["x"] = lerp(local_pos["x"], float(srv["x"]), 0.05)
                    local_pos["y"] = lerp(local_pos["y"], float(srv["y"]), 0.05)
                    rnd["x"] = local_pos["x"]
                    rnd["y"] = local_pos["y"]
            else:
                # Remote players: smooth interpolation to hide network jitter
                rnd["x"] = lerp(rnd["x"], float(srv["x"]), LERP_ALPHA)
                rnd["y"] = lerp(rnd["y"], float(srv["y"]), LERP_ALPHA)

        # --- Draw ---
        window.fill(BACKGROUND_COLOR)
        window.blit(MAP_SURFACE, (0, 0))

        for pid, pos in render_positions.items():
            window.blit(player_sprite, (int(pos["x"]), int(pos["y"])))

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