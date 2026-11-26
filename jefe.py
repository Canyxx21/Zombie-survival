import math
from collections import deque
import pygame
from settings import TAM
from busqueda.astar import astar, DIRS
from enemigo import Enemigo, centro
from ia.genetico import Genoma
from sprites import dibujar_entidad_estilizada


class Jefe(Enemigo):
    def __init__(self, x, y, ola, cerebro):
        self.genoma = Genoma("elite", 1, 1, 1)
        self.tipo = "jefe"
        self.color = (204, 108, 255)
        self.radio = 15
        self.vel = 90
        self.vida = 45 + 18 * (ola // 3)
        self.vida_max = self.vida
        self.danio = 18
        self.x, self.y = x, y
        self.angulo = 0.0
        self.flash = 0
        self.lento_ms = 0
        self.espera_golpe = 0
        self.recalculo = 0
        self.ruta = []
        self.viva = True
        self.danio_hecho = 0
        self.vivo_ms = 0
        self.dist_min = 999.0
        self.cerebro = cerebro
        self.mira = None
        self.estela = deque(maxlen=6)

    def objetivo(self, mapa, jugador, dt):
        if math.hypot(jugador.x - self.x, jugador.y - self.y) < TAM * 2.2:
            return jugador.x, jugador.y

        c = self.celda
        self.recalculo -= dt
        if self.recalculo <= 0 or not self.ruta:
            meta = self.cerebro.predecir(jugador, mapa)
            if not mapa.transitable(*meta):
                meta = jugador.celda
            self.mira = meta
            self.ruta, _ = astar(mapa, c, meta)
            if not self.ruta and meta != jugador.celda:
                self.ruta, _ = astar(mapa, c, jugador.celda)
            self.recalculo = 350

        while self.ruta and self.ruta[0] == c:
            self.ruta.pop(0)
        if self.ruta:
            return centro(self.ruta[0])

        vecinos = [(c[0] + dx, c[1] + dy) for dx, dy in DIRS]
        mejor = min(vecinos, key=lambda v: mapa.dist.get(v, 9999))
        if mapa.dist.get(mejor, 9999) < mapa.dist.get(c, 9999):
            return centro(mejor)
        return jugador.x, jugador.y

    def mover(self, mapa, jugador, dt):
        if self.vivo_ms % 60 < dt:
            self.estela.append((self.x, self.y))
        super().mover(mapa, jugador, dt)

    def dibujar(self, pantalla, debug=False):
        if debug and self.mira:
            mx, my = centro(self.mira)
            pygame.draw.circle(pantalla, self.color, (int(mx), int(my)), 14, 2)
            pygame.draw.line(pantalla, self.color, (self.x, self.y), (mx, my), 1)

        for i, (ex, ey) in enumerate(self.estela):
            r = int(self.radio * (i + 1) / (len(self.estela) + 2))
            pygame.draw.circle(pantalla, (85, 42, 115), (int(ex), int(ey)), max(3, r))

        pulso = int(3 * math.sin(self.vivo_ms / 150))
        pygame.draw.circle(pantalla, (130, 65, 175), (int(self.x), int(self.y)), self.radio + 4 + pulso, 2)

        dibujar_entidad_estilizada(
            pantalla, "jefe", self.x, self.y, self.radio,
            self.angulo, self._color_actual(), flash=(self.flash > 0)
        )

        w = 48
        pygame.draw.rect(pantalla, (28, 12, 42), (self.x - w / 2, self.y - self.radio - 11, w, 5))
        pygame.draw.rect(pantalla, self.color, (self.x - w / 2, self.y - self.radio - 11, w * max(0, self.vida) / self.vida_max, 5))