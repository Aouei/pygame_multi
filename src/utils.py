import pygame, sys


def exit_game():
    if pygame.event.get(pygame.QUIT):
        pygame.quit()
        sys.exit()

    if pygame.key.get_pressed()[pygame.K_ESCAPE]:
        pygame.quit()
        sys.exit()