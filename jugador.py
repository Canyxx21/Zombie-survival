import math
import pygame
from settings import TAM, JUGADOR
from proyectil import Proyectil

class Jugador:
    def __init__(self, cx, cy):
        self.x = cx * TAM + TAM / 2
        self.y = cy * TAM + TAM / 2
        self.radio = 11
        self.vel = 220
        self.vida_max = 100
        self.vida = self.vida_max
        # arma automática
        self.cadencia = 450
        self.espera_arma = 0
        self.danio = 1
        self.alcance = 260
        self.balas = 1
        # progreso
        self.xp = 0
        self.nivel = 1
        self.iman = 70

    @property
    def celda(self):
        return int(self.x // TAM), int(self.y // TAM)

    @property
    def xp_sig(self):
        return 4 + 3 * self.nivel

    def mover(self, teclas, mapa, dt):
        dx = int(teclas[pygame.K_d] or teclas[pygame.K_RIGHT]) - int(teclas[pygame.K_a] or teclas[pygame.K_LEFT])
        dy = int(teclas[pygame.K_s] or teclas[pygame.K_DOWN]) - int(teclas[pygame.K_w] or teclas[pygame.K_UP])
        if dx and dy:
            dx *= 0.7071
            dy *= 0.7071
        paso = self.vel * dt / 1000 * (0.6 if self.celda in mapa.lodo else 1)
        nx = self.x + dx * paso
        if not mapa.choca(nx, self.y, self.radio):
            self.x = nx
        ny = self.y + dy * paso
        if not mapa.choca(self.x, ny, self.radio):
            self.y = ny

    def disparar(self, enemigos, proyectiles, dt):
        self.espera_arma -= dt
        if self.espera_arma > 0 or not enemigos:
            return
        objetivo = min(enemigos, key=lambda e: (e.x - self.x) ** 2 + (e.y - self.y) ** 2)
        dx, dy = objetivo.x - self.x, objetivo.y - self.y
        d = math.hypot(dx, dy)
        if d > self.alcance or d == 0:
            return
        base = math.atan2(dy, dx)
        for i in range(self.balas):
            a = base + (i - (self.balas - 1) / 2) * 0.18
            proyectiles.append(Proyectil(self.x, self.y, math.cos(a), math.sin(a), self.danio))
        self.espera_arma = self.cadencia

    def dibujar(self, pantalla):
        pygame.draw.circle(pantalla, JUGADOR, (int(self.x), int(self.y)), self.radio)