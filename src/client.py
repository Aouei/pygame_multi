import asyncio
import json
import pygame
import websockets
import pandas as pd

FRAME_RATE = 60

PLAYER_SPEED = 5
PLAYER_SIZE = 32

BACKGROUND_COLOR = (127, 64, 0)

# Pygame setup
pygame.init()
pygame.joystick.init()
window = pygame.display.set_mode((800, 600))
# window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
WIDTH, HEIGHT = window.get_rect().width, window.get_rect().height
print(WIDTH, HEIGHT)
clock = pygame.time.Clock()

# Load sprites
player_sprite = pygame.image.load(r"C:\Users\sergi\Documents\repos\pygame_multi\assets\nave.png")
player_sprite = pygame.transform.scale(player_sprite, (PLAYER_SIZE, PLAYER_SIZE))

TILE_SIZE = 32
TILES = {
    'G1' : pygame.transform.scale(pygame.image.load(r"C:\Users\sergi\Documents\repos\pygame_multi\assets\Grass_1.png"), (TILE_SIZE, TILE_SIZE)),
    'G2' : pygame.transform.scale(pygame.image.load(r"C:\Users\sergi\Documents\repos\pygame_multi\assets\Grass_2.png"), (TILE_SIZE, TILE_SIZE)),
    'S1' : pygame.transform.scale(pygame.image.load(r"C:\Users\sergi\Documents\repos\pygame_multi\assets\Shore_1.png"), (TILE_SIZE, TILE_SIZE)),
    'S2' : pygame.transform.scale(pygame.image.load(r"C:\Users\sergi\Documents\repos\pygame_multi\assets\Shore_2.png"), (TILE_SIZE, TILE_SIZE)),
}

map = pd.read_csv(r'C:\Users\sergi\Documents\repos\pygame_multi\assets\map\map.csv', header=None)
def draw_map(surface : pygame.Surface):
    for i, row in enumerate(map.values):
        for j, col in enumerate(row):
            surface.blit(TILES[col], (j * TILE_SIZE, i * TILE_SIZE))

async def game_loop(websocket):
    players = {}
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            
                

        keys = pygame.key.get_pressed()
        dx, dy = 0, 0
        # Joystick support
        joystick_count = pygame.joystick.get_count()
        if joystick_count > 0:
            joystick = pygame.joystick.Joystick(0)
            joystick.init()
            axis_x = joystick.get_axis(0)
            axis_y = joystick.get_axis(1)
            # Deadzone para evitar drift
            deadzone = 0.2
            if abs(axis_x) > deadzone:
                dx = int(axis_x * PLAYER_SPEED)
            if abs(axis_y) > deadzone:
                dy = int(axis_y * PLAYER_SPEED)
        else:
            # Fallback a teclado si no hay joystick
            if keys[pygame.K_LEFT]: dx = -PLAYER_SPEED
            if keys[pygame.K_RIGHT]: dx = PLAYER_SPEED
            if keys[pygame.K_UP]: dy = -PLAYER_SPEED
            if keys[pygame.K_DOWN]: dy = PLAYER_SPEED
        if keys[pygame.K_ESCAPE]: return

        if dx != 0 or dy != 0:
            await websocket.send(json.dumps({"type": "move", "dx": dx, "dy": dy}))

        try:
            response = await asyncio.wait_for(websocket.recv(), timeout=0.1)
            data = json.loads(response)
            players = data.get("players", {})
        except asyncio.TimeoutError:
            pass

        window.fill(BACKGROUND_COLOR)
        draw_map(window)

        for player_id, player in players.items():
            window.blit(player_sprite, (player["x"], player["y"]))
        pygame.display.flip()
        clock.tick(FRAME_RATE)

async def main():
    async with websockets.connect("ws://localhost:8765") as websocket:
        await websocket.send(json.dumps({"type": "start", "x": WIDTH, "y": HEIGHT}))
        await game_loop(websocket)

asyncio.run(main())