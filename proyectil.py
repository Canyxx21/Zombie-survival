import pygame
from settings import BALA


class Proyectil:
    VEL = 540

    def __init__(self, x, y, dx, dy, danio, perforacion=0, hielo_ms=0, evol=False):
        self.x, self.y = x, y
        self.vx, self.vy = dx * self.VEL * (1.18 if evol else 1.0), dy * self.VEL * (1.18 if evol else 1.0)
        self.danio = danio
        self.perforacion = perforacion
        self.hielo_ms = hielo_ms
        self.evol = evol
        self.golpeados = set()
        self.radio = 6 if evol else 4
        self.vida = 1300
        self.viva = True

    def mover(self, mapa, dt):
        self.x += self.vx * dt / 1000
        self.y += self.vy * dt / 1000
        self.vida -= dt
        if self.vida <= 0 or mapa.choca(self.x, self.y, self.radio):
            self.viva = False

    def dibujar(self, pantalla):
        if self.evol:
            col = (120, 240, 255) if self.hielo_ms > 0 else (255, 110, 210)
            pygame.draw.circle(pantalla, col, (int(self.x), int(self.y)), self.radio)
            pygame.draw.circle(pantalla, (255, 255, 255), (int(self.x), int(self.y)), 2)
        else:
            col = (130, 225, 255) if self.hielo_ms > 0 else BALA
            pygame.draw.circle(pantalla, col, (int(self.x), int(self.y)), self.radio)