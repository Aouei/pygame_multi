import asyncio
import sys
import pygame

from levels import lobby, game
from inputs import InputHandler


pygame.init()
INPUTS = InputHandler()
CLOCK = pygame.time.Clock()
FRAME_RATE = 60

# window = pygame.display.set_mode((500, 500))
window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)

LOBBY = lobby.Screen(window, INPUTS, CLOCK)
GAME = game.Game(window, INPUTS, CLOCK)

if __name__ == "__main__":
    while True:
        LOBBY.reset()
        role = LOBBY.loop()
        if role is None:
            break

        result = asyncio.run(GAME.run(role, LOBBY.host.value, LOBBY.port.value))
        if result == "quit":
            break

    pygame.quit()
    sys.exit()
