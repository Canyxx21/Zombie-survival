import math
import random
import pygame
from settings import TAM
from busqueda.astar import astar, DIRS
from busqueda.dfs import dfs

TIPOS = {
    "horda":    dict(color=(120, 200, 120), radio=9,  vel=75,  vida=3,  danio=6,  alg="BFS"),
    "corredor": dict(color=(224, 138, 44),  radio=8,  vel=130, vida=2,  danio=5,  alg="Voraz"),
    "tonto":    dict(color=(201, 194, 74),  radio=10, vel=55,  vida=4,  danio=6,  alg="DFS"),
    "elite":    dict(color=(200, 55, 45),   radio=13, vel=95,  vida=10, danio=12, alg="A*"),
}
RECALCULO = {"corredor": 400, "tonto": 1800, "elite": 500}   # ms entre búsquedas
ESTAD = {t: {"busquedas": 0, "nodos": 0, "costo": 0} for t in TIPOS}

def centro(c):
    return c[0] * TAM + TAM / 2, c[1] * TAM + TAM / 2

class Enemigo:
    def __init__(self, x, y, genoma, ola=1):
        cfg = TIPOS[genoma.tipo]
        self.genoma = genoma
        self.tipo = genoma.tipo
        self.color, self.radio = cfg["color"], cfg["radio"]
        self.vel = cfg["vel"] * genoma.vel
        self.vida = max(1, round(cfg["vida"] * genoma.vida * (1 + 0.08 * (ola - 1))))
        self.danio = max(1, round(cfg["danio"] * genoma.danio))
        self.x, self.y = x, y
        self.espera_golpe = 0
        self.recalculo = random.uniform(0, 400)    # evita que todos busquen en el mismo cuadro
        self.ruta = []
        self.viva = True
        self.danio_hecho = 0
        self.vivo_ms = 0

    def fitness(self):
        """Aptitud: daño causado + 0.5 por segundo sobrevivido."""
        return self.danio_hecho + self.vivo_ms / 2000

    @property
    def celda(self):
        return int(self.x // TAM), int(self.y // TAM)

    def objetivo(self, mapa, jugador, dt):
        c = self.celda
        if math.hypot(jugador.x - self.x, jugador.y - self.y) < TAM * 1.5:
            return jugador.x, jugador.y

        if self.tipo == "horda":                      # campo de flujo (BFS)
            vecinos = [(c[0] + dx, c[1] + dy) for dx, dy in DIRS]
            mejor = min(vecinos, key=lambda v: mapa.dist.get(v, 9999))
            if mapa.dist.get(mejor, 9999) < mapa.dist.get(c, 9999):
                return centro(mejor)
            return jugador.x, jugador.y

        self.recalculo -= dt                          # búsqueda individual
        if self.recalculo <= 0 or not self.ruta:
            meta = jugador.celda
            if self.tipo == "elite":
                self.ruta, explorados = astar(mapa, c, meta)
            elif self.tipo == "corredor":
                self.ruta, explorados = astar(mapa, c, meta, voraz=True)
            else:
                self.ruta, explorados = dfs(mapa, c, meta)
            ESTAD[self.tipo]["busquedas"] += 1
            ESTAD[self.tipo]["nodos"] += len(explorados)
            ESTAD[self.tipo]["costo"] += sum(mapa.costo(*cel) for cel in self.ruta)
            self.recalculo = RECALCULO[self.tipo]

        while self.ruta and self.ruta[0] == c:
            self.ruta.pop(0)
        if self.ruta:
            return centro(self.ruta[0])
        return jugador.x, jugador.y

    def mover(self, mapa, jugador, dt):
        self.espera_golpe -= dt
        self.vivo_ms += dt
        tx, ty = self.objetivo(mapa, jugador, dt)
        dx, dy = tx - self.x, ty - self.y
        d = math.hypot(dx, dy) or 1
        paso = self.vel * dt / 1000 * (0.5 if self.celda in mapa.lodo else 1)
        nx = self.x + dx / d * paso
        if not mapa.choca(nx, self.y, self.radio):
            self.x = nx
        ny = self.y + dy / d * paso
        if not mapa.choca(self.x, ny, self.radio):
            self.y = ny

    def toca(self, jugador):
        return math.hypot(jugador.x - self.x, jugador.y - self.y) < self.radio + jugador.radio

    def dibujar(self, pantalla, debug=False):
        if debug and self.ruta:
            pts = [(self.x, self.y)] + [centro(c) for c in self.ruta]
            if len(pts) > 1:
                pygame.draw.lines(pantalla, self.color, False, pts, 1)
        pygame.draw.circle(pantalla, self.color, (int(self.x), int(self.y)), self.radio)