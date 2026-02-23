import pygame
import sys

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
        self.image = ship_img
        self.rect = self.image.get_rect(center=(WIDTH//2, HEIGHT//2))

    def update(self, dx, dy):
        self.rect.x += dx
        self.rect.y += dy
        self.rect.clamp_ip(screen.get_rect())

    def draw(self, surface):
        surface.blit(self.image, self.rect)

class Bullet:
    def __init__(self, x, y):
        self.image = bullet_img
        self.rect = self.image.get_rect(center=(x, y))
        self.speed = 10

    def update(self):
        self.rect.y -= self.speed

    def draw(self, surface):
        surface.blit(self.image, self.rect)

# Inicializar joystick
pygame.joystick.init()
if pygame.joystick.get_count() > 0:
    joystick = pygame.joystick.Joystick(0)
    joystick.init()
else:
    joystick = None

# Objetos
ship = Ship()
bullets = []

clock = pygame.time.Clock()

# Loop principal
def main():
    while True:
        dx, dy = 0, 0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.JOYBUTTONDOWN:
                # Botón X (usualmente botón 2 en mandos tipo PlayStation)
                if joystick and joystick.get_button(2):
                    bullets.append(Bullet(ship.rect.centerx, ship.rect.top))

        # Leer joystick
        if joystick:
            dx = int(joystick.get_axis(0) * 8)  # Joystick izquierdo X
            dy = int(joystick.get_axis(1) * 8)  # Joystick izquierdo Y

        ship.update(dx, dy)

        # Actualizar balas
        for bullet in bullets[:]:
            bullet.update()
            if bullet.rect.bottom < 0:
                bullets.remove(bullet)

        # Dibujar
        screen.fill((30, 30, 30))
        ship.draw(screen)
        for bullet in bullets:
            bullet.draw(screen)
        pygame.display.flip()
        clock.tick(60)

if __name__ == '__main__':
    main()

