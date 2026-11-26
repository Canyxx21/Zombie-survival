import math
import random
import pygame
from settings import TAM
from busqueda.astar import astar, DIRS
from busqueda.dfs import dfs
from sprites import dibujar_entidad_estilizada

TIPOS = {
    "horda":    dict(color=(88, 224, 132),  radio=9,  vel=75,  vida=3,  danio=6,  alg="BFS"),
    "corredor": dict(color=(255, 148, 56),  radio=8,  vel=130, vida=2,  danio=5,  alg="Voraz"),
    "tonto":    dict(color=(230, 214, 72),  radio=10, vel=55,  vida=4,  danio=6,  alg="DFS"),
    "elite":    dict(color=(242, 68, 78),   radio=13, vel=95,  vida=10, danio=12, alg="A*"),
}
RECALCULO = {"corredor": 400, "tonto": 1800, "elite": 500}
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
        self.vida_max = self.vida
        self.danio = max(1, round(cfg["danio"] * genoma.danio))
        self.x, self.y = x, y
        self.angulo = 0.0
        self.flash = 0
        self.lento_ms = 0
        self.espera_golpe = 0
        self.recalculo = random.uniform(0, 400)
        self.ruta = []
        self.viva = True
        self.danio_hecho = 0
        self.vivo_ms = 0
        self.dist_min = 999.0

    def fitness(self):
        cercania = max(0.0, 14.0 - self.dist_min) * 0.8
        supervivencia = min(self.vivo_ms, 15000) / 5000.0
        return self.danio_hecho * 3.0 + cercania + supervivencia

    @property
    def celda(self):
        return int(self.x // TAM), int(self.y // TAM)

    def objetivo(self, mapa, jugador, dt):
        c = self.celda
        if math.hypot(jugador.x - self.x, jugador.y - self.y) < TAM * 1.5:
            return jugador.x, jugador.y

        if self.tipo == "horda":
            vecinos = [(c[0] + dx, c[1] + dy) for dx, dy in DIRS]
            mejor = min(vecinos, key=lambda v: mapa.dist.get(v, 9999))
            if mapa.dist.get(mejor, 9999) < mapa.dist.get(c, 9999):
                return centro(mejor)
            return jugador.x, jugador.y

        self.recalculo -= dt
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
        self.flash = max(0, self.flash - dt)
        self.lento_ms = max(0, self.lento_ms - dt)
        self.vivo_ms += dt

        dist_celdas = math.hypot(jugador.x - self.x, jugador.y - self.y) / TAM
        if dist_celdas < self.dist_min:
            self.dist_min = dist_celdas

        tx, ty = self.objetivo(mapa, jugador, dt)
        dx, dy = tx - self.x, ty - self.y
        d = math.hypot(dx, dy) or 1
        self.angulo = math.atan2(dy, dx)

        factor_lodo = 0.5 if self.celda in mapa.lodo else 1.0
        factor_hielo = 0.65 if self.lento_ms > 0 else 1.0
        paso = self.vel * dt / 1000 * factor_lodo * factor_hielo

        vx, vy = (dx / d) * paso, (dy / d) * paso
        movio = False
        if not mapa.choca(self.x + vx, self.y, self.radio):
            self.x += vx
            movio = True
        if not mapa.choca(self.x, self.y + vy, self.radio):
            self.y += vy
            movio = True

        if not movio:
            for sx, sy in ((-vy, vx), (vy, -vx)):
                if not mapa.choca(self.x + sx, self.y + sy, self.radio):
                    self.x += sx
                    self.y += sy
                    break

    def toca(self, jugador):
        return math.hypot(jugador.x - self.x, jugador.y - self.y) < self.radio + jugador.radio

    def _color_actual(self):
        if self.lento_ms > 0:
            return (110, 210, 255)
        return self.color

    def dibujar(self, pantalla, debug=False):
        if debug and self.ruta:
            pts = [(self.x, self.y)] + [centro(c) for c in self.ruta]
            if len(pts) > 1:
                pygame.draw.lines(pantalla, self.color, False, pts, 1)

        dibujar_entidad_estilizada(
            pantalla, self.tipo, self.x, self.y, self.radio,
            self.angulo, self._color_actual(), flash=(self.flash > 0)
        )

        if self.tipo == "elite" and self.vida < self.vida_max:
            w = 26
            pygame.draw.rect(pantalla, (35, 14, 20), (self.x - w / 2, self.y - self.radio - 8, w, 3))
            pygame.draw.rect(pantalla, self.color, (self.x - w / 2, self.y - self.radio - 8, w * max(0, self.vida) / self.vida_max, 3))