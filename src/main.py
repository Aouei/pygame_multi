import asyncio
import sys
import pygame

from levels import lobby, game, menu
from frameworks.inputs import InputHandler
from loguru import logger


pygame.init()
INPUTS = InputHandler()
CLOCK = pygame.time.Clock()

window = pygame.display.set_mode((700, 700))
# window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)

MENU  = menu.Screen(window, INPUTS, CLOCK)
LOBBY = lobby.Screen(window, INPUTS, CLOCK)
GAME  = game.Game(window, INPUTS, CLOCK)

if __name__ == "__main__":
    while True:
        result = MENU.loop()
        if result != "play":
            break

        LOBBY.reset()
        role = LOBBY.loop()
        if role is None:
            continue

        try:
            result = asyncio.run(GAME.run(role, LOBBY.host.value, LOBBY.port.value))
        except Exception as e:
            logger.error(f"Unexpected game crash: {e}")
            result = "lobby"
        if result == "quit":
            break

    pygame.quit()
    sys.exit()
