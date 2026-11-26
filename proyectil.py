import pygame
from settings import BALA

class Proyectil:
    VEL = 520  # píxeles por segundo

    def __init__(self, x, y, dx, dy, danio):
        self.x, self.y = x, y
        self.vx, self.vy = dx * self.VEL, dy * self.VEL
        self.danio = danio
        self.radio = 4
        self.vida = 1200      # ms antes de desaparecer
        self.viva = True

    def mover(self, mapa, dt):
        self.x += self.vx * dt / 1000
        self.y += self.vy * dt / 1000
        self.vida -= dt
        if self.vida <= 0 or mapa.choca(self.x, self.y, self.radio):
            self.viva = False

    def dibujar(self, pantalla):
        pygame.draw.circle(pantalla, BALA, (int(self.x), int(self.y)), self.radio)