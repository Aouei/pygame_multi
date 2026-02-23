import pygame
import sys
import math
import asyncio
import websockets
import json

WIDTH, HEIGHT = 800, 600
pygame.init()

ship_img = pygame.image.load('../assets/nave.png')
bullet_img = pygame.image.load('../assets/bala.png')

async def main():
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption('Juego rápido: nave y balas')
    pygame.joystick.init()
    if pygame.joystick.get_count() > 0:
        joystick = pygame.joystick.Joystick(0)
        joystick.init()
    else:
        joystick = None

    uri = 'ws://localhost:8765'
    async with websockets.connect(uri) as ws:
        my_id = str(id(ws))
        clock = pygame.time.Clock()
        # Variables persistentes de posición y ángulo
        my_x = WIDTH // 2
        my_y = HEIGHT // 2
        my_angle = 0
        while True:
            dx, dy = 0, 0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    await ws.close()
                    sys.exit()
                if event.type == pygame.JOYBUTTONDOWN:
                    if joystick and joystick.get_button(2):
                        await ws.send(json.dumps({'type': 'shoot', 'x': my_x, 'y': my_y, 'angle': my_angle}))
            if joystick:
                dx = int(joystick.get_axis(0) * 8)
                dy = int(joystick.get_axis(1) * 8)
                my_x += dx
                my_y += dy
                if dx != 0 or dy != 0:
                    my_angle = math.degrees(math.atan2(-dx, -dy))
            # Limitar dentro de pantalla
            my_x = max(0, min(WIDTH, my_x))
            my_y = max(0, min(HEIGHT, my_y))
            await ws.send(json.dumps({'type': 'move', 'x': my_x, 'y': my_y, 'angle': my_angle}))
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=0.05)
                state = json.loads(msg)
            except:
                state = {'players': {}, 'bullets': []}
            screen.fill((30, 30, 30))
            # Dibujar jugadores
            for pid, pdata in state['players'].items():
                img = ship_img
                angle = pdata['angle']
                img_rot = pygame.transform.rotate(img, angle)
                rect = img_rot.get_rect(center=(pdata['x'], pdata['y']))
                screen.blit(img_rot, rect)
            # Dibujar balas
            for b in state['bullets']:
                img = bullet_img
                img_rot = pygame.transform.rotate(img, b['angle'])
                rect = img_rot.get_rect(center=(b['x'], b['y']))
                screen.blit(img_rot, rect)
            pygame.display.flip()
            clock.tick(60)

if __name__ == '__main__':
    asyncio.run(main())

