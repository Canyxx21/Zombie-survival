import math
import pygame
from settings import TAM
from busqueda.astar import astar
from enemigo import Enemigo, centro
from ia.genetico import Genoma


class Jefe(Enemigo):
    def __init__(self, x, y, ola, cerebro):
        self.genoma = Genoma("elite", 1, 1, 1)    # genoma de relleno: el jefe no evoluciona
        self.tipo = "jefe"
        self.color = (182, 95, 209)
        self.radio = 18
        self.vel = 85
        self.vida = 40 + 15 * (ola // 3)
        self.vida_max = self.vida
        self.danio = 18
        self.x, self.y = x, y
        self.espera_golpe = 0
        self.recalculo = 0
        self.ruta = []
        self.viva = True
        self.danio_hecho = 0
        self.vivo_ms = 0
        self.cerebro = cerebro
        self.mira = None

    def objetivo(self, mapa, jugador, dt):
        if math.hypot(jugador.x - self.x, jugador.y - self.y) < TAM * 2:
            return jugador.x, jugador.y                    # ya está encima: atacar directo
        self.recalculo -= dt
        if self.recalculo <= 0:
            meta = self.cerebro.predecir(jugador)          # la red decide a dónde ir
            if not mapa.transitable(*meta):
                meta = jugador.celda
            self.mira = meta
            self.ruta, _ = astar(mapa, self.celda, meta)
            self.recalculo = 350
        while self.ruta and self.ruta[0] == self.celda:
            self.ruta.pop(0)
        if self.ruta:
            return centro(self.ruta[0])
        return jugador.x, jugador.y

    def dibujar(self, pantalla, debug=False):
        if debug and self.mira:
            mx, my = centro(self.mira)
            pygame.draw.circle(pantalla, self.color, (int(mx), int(my)), 14, 2)   # casilla que predijo
            pygame.draw.line(pantalla, self.color, (self.x, self.y), (mx, my), 1)
        pygame.draw.circle(pantalla, self.color, (int(self.x), int(self.y)), self.radio)
        w = 44
        pygame.draw.rect(pantalla, (30, 10, 40), (self.x - w / 2, self.y - self.radio - 10, w, 5))
        pygame.draw.rect(pantalla, self.color, (self.x - w / 2, self.y - self.radio - 10, w * self.vida / self.vida_max, 5))