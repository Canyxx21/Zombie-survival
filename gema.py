import math
import pygame

class Gema:
    def __init__(self, x, y, valor):
        self.x, self.y, self.valor = x, y, valor

    def actualizar(self, jugador, dt):
        """Se acerca si estás en el rango del imán. True si ya la recogiste."""
        dx, dy = jugador.x - self.x, jugador.y - self.y
        d = math.hypot(dx, dy)
        if 0 < d < jugador.iman:
            paso = 380 * dt / 1000
            self.x += dx / d * paso
            self.y += dy / d * paso
        return d < jugador.radio + 4

    def dibujar(self, pantalla):
        x, y = int(self.x), int(self.y)
        pygame.draw.polygon(pantalla, (90, 200, 255), [(x, y - 5), (x + 4, y), (x, y + 5), (x - 4, y)])