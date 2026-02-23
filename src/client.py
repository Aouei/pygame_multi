import pygame
import sys
import math
import asyncio
import websockets

# Inicialización
pygame.init()

# Configuración de pantalla
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Juego rápido: nave y balas')

# Cargar assets
ship_img = pygame.image.load('../assets/nave.png').convert_alpha()
bullet_img = pygame.image.load('../assets/bala.png').convert_alpha()

# Clases
class Ship:
    def __init__(self):
        self.original_image = ship_img
        self.image = self.original_image
        self.rect = self.image.get_rect(center=(WIDTH//2, HEIGHT//2))
        self.angle = 0
        self.last_dx = 0
        self.last_dy = -1  # Por defecto apunta hacia arriba

    def update(self, dx, dy):
        self.rect.x += dx
        self.rect.y += dy
        self.rect.clamp_ip(screen.get_rect())
        # Rotar según joystick
        if dx != 0 or dy != 0:
            self.last_dx = dx
            self.last_dy = dy
            self.angle = math.degrees(math.atan2(-self.last_dx, -self.last_dy))
            self.image = pygame.transform.rotate(self.original_image, self.angle)
            self.rect = self.image.get_rect(center=self.rect.center)

    def draw(self, surface):
        surface.blit(self.image, self.rect)

class Bullet:
    def __init__(self, x, y, angle):
        # Ajustar el ángulo para que la bala salga desde el "norte" de la nave
        self.original_image = bullet_img
        self.angle = angle
        self.image = pygame.transform.rotate(self.original_image, self.angle)
        self.rect = self.image.get_rect(center=(x, y))
        self.speed = 10
        # Restar 90 grados para que el disparo salga desde el "norte"
        rad = math.radians(angle + 90)
        self.dx = math.cos(rad) * self.speed
        self.dy = -math.sin(rad) * self.speed

    def update(self):
        self.rect.x += int(self.dx)
        self.rect.y += int(self.dy)

    def draw(self, surface):
        surface.blit(self.image, self.rect)

# Inicializar joystick
pygame.joystick.init()
if pygame.joystick.get_count() > 0:
    joystick = pygame.joystick.Joystick(0)
    joystick.init()
else:
    joystick = None

# Cliente WebSocket para enviar posición y disparos
class NetworkClient:
    def __init__(self, uri):
        self.uri = uri
        self.ws = None

    async def connect(self):
        self.ws = await websockets.connect(self.uri)

    async def send_state(self, state):
        if self.ws:
            await self.ws.send(state)

    async def receive(self):
        if self.ws:
            return await self.ws.recv()
        return None

async def game_loop(network):
    # Inicialización pygame
    pygame.init()
    WIDTH, HEIGHT = 800, 600
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption('Juego rápido: nave y balas')
    ship_img = pygame.image.load('../assets/nave.png').convert_alpha()
    bullet_img = pygame.image.load('../assets/bala.png').convert_alpha()

    class Ship:
        def __init__(self):
            self.original_image = ship_img
            self.image = self.original_image
            self.rect = self.image.get_rect(center=(WIDTH//2, HEIGHT//2))
            self.angle = 0
            self.last_dx = 0
            self.last_dy = -1
        def update(self, dx, dy):
            self.rect.x += dx
            self.rect.y += dy
            self.rect.clamp_ip(screen.get_rect())
            if dx != 0 or dy != 0:
                self.last_dx = dx
                self.last_dy = dy
                self.angle = math.degrees(math.atan2(-self.last_dx, -self.last_dy))
                self.image = pygame.transform.rotate(self.original_image, self.angle)
                self.rect = self.image.get_rect(center=self.rect.center)
        def draw(self, surface):
            surface.blit(self.image, self.rect)
    class Bullet:
        def __init__(self, x, y, angle):
            self.original_image = bullet_img
            self.angle = angle
            self.image = pygame.transform.rotate(self.original_image, self.angle)
            self.rect = self.image.get_rect(center=(x, y))
            self.speed = 10
            rad = math.radians(angle + 90)
            self.dx = math.cos(rad) * self.speed
            self.dy = -math.sin(rad) * self.speed
        def update(self):
            self.rect.x += int(self.dx)
            self.rect.y += int(self.dy)
        def draw(self, surface):
            surface.blit(self.image, self.rect)

    pygame.joystick.init()
    if pygame.joystick.get_count() > 0:
        joystick = pygame.joystick.Joystick(0)
        joystick.init()
    else:
        joystick = None

    ship = Ship()
    bullets = []
    clock = pygame.time.Clock()

    while True:
        dx, dy = 0, 0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                await network.ws.close()
                sys.exit()
            if event.type == pygame.JOYBUTTONDOWN:
                if joystick and joystick.get_button(2):
                    bullets.append(Bullet(ship.rect.centerx, ship.rect.centery, ship.angle))
                    state = f"SHOOT:{ship.rect.centerx},{ship.rect.centery},{ship.angle}"
                    await network.send_state(state)
        if joystick:
            dx = int(joystick.get_axis(0) * 8)
            dy = int(joystick.get_axis(1) * 8)
        ship.update(dx, dy)
        state = f"POS:{ship.rect.centerx},{ship.rect.centery},{ship.angle}"
        await network.send_state(state)
        for bullet in bullets[:]:
            bullet.update()
            if (bullet.rect.bottom < 0 or bullet.rect.top > HEIGHT or
                bullet.rect.right < 0 or bullet.rect.left > WIDTH):
                bullets.remove(bullet)
        screen.fill((30, 30, 30))
        ship.draw(screen)
        for bullet in bullets:
            bullet.draw(screen)
        pygame.display.flip()
        clock.tick(60)

async def main():
    network = NetworkClient('ws://localhost:8765')
    await network.connect()
    await game_loop(network)

if __name__ == '__main__':
    asyncio.run(main())

