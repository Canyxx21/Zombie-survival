import math
import pygame
from settings import TAM, JUGADOR
from proyectil import Proyectil
from armas import Arsenal
from sprites import dibujar_entidad_estilizada


class Jugador:
    def __init__(self, cx, cy):
        self.x = cx * TAM + TAM / 2
        self.y = cy * TAM + TAM / 2
        self.radio = 12
        self.vel = 225
        self.vida_max = 100
        self.vida = self.vida_max
        self.apunta = 0.0
        # estadísticas globales de ataque
        self.cadencia = 440
        self.danio = 1
        self.alcance = 280
        self.balas_extra = 0
        self.perforacion = 0
        self.hielo_ms = 0
        self.arsenal = Arsenal()
        self._cola_impactos = []
        # escudo táctico
        self.escudo_recarga = 0
        self.escudo_activo = False
        self.escudo_cd = 0
        # progreso
        self.xp = 0
        self.nivel = 1
        self.iman = 75

    @property
    def celda(self):
        return int(self.x // TAM), int(self.y // TAM)

    @property
    def xp_sig(self):
        return 4 + 3 * self.nivel

    def crear_bala(self, dx, dy, danio, perforacion, hielo_ms, evol=False):
        return Proyectil(self.x, self.y, dx, dy, danio, perforacion, hielo_ms, evol)

    def aplicar_impacto_directo(self, enemigo, danio, hielo_ms=0):
        self._cola_impactos.append((enemigo, danio, hielo_ms))

    def actualizar_escudo(self, dt):
        if self.escudo_recarga > 0 and not self.escudo_activo:
            self.escudo_cd -= dt
            if self.escudo_cd <= 0:
                self.escudo_activo = True

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

    def disparar(self, enemigos, proyectiles, ondas, dt, snd):
        self.arsenal.actualizar(self, enemigos, proyectiles, ondas, dt, snd)

    def dibujar(self, pantalla):
        self.arsenal.dibujar(pantalla, self)
        dibujar_entidad_estilizada(pantalla, "jugador", self.x, self.y, self.radio, self.apunta, JUGADOR)
        if self.escudo_activo:
            pygame.draw.circle(pantalla, (90, 235, 255), (int(self.x), int(self.y)), self.radio + 6, 2)