import math
import os
import pygame
from settings import BALA

BASE_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
_CACHE_PROJ = {}


def _cortar_tira(ruta, tam):
    if not os.path.exists(ruta):
        return None
    try:
        sheet = pygame.image.load(ruta).convert_alpha()
        w, h = sheet.get_size()
        n = max(1, w // h)
        ancho_frame = w // n
        frames = []
        for i in range(n):
            sub = sheet.subsurface((i * ancho_frame, 0, ancho_frame, h))
            frames.append(pygame.transform.scale(sub, (tam, tam)))
        return frames
    except pygame.error:
        return None


def _cargar_recurso(clave, tam):
    if clave in _CACHE_PROJ:
        return _CACHE_PROJ[clave]

    res = None
    if clave == "bala":
        ruta = os.path.join(BASE_ASSETS, "bullet.png")
        if os.path.exists(ruta):
            img = pygame.image.load(ruta).convert_alpha()
            res = [pygame.transform.scale(img, (tam, max(6, tam // 2)))]
    elif clave == "hielo":
        ruta = os.path.join(BASE_ASSETS, "projectiles", "proj_iceball_strip.png")
        res = _cortar_tira(ruta, tam)
    elif clave == "plasma":
        ruta = os.path.join(BASE_ASSETS, "projectiles", "proj_energy_ball_strip.png")
        res = _cortar_tira(ruta, tam)

    _CACHE_PROJ[clave] = res
    return res


class Proyectil:
    VEL = 540

    def __init__(self, x, y, dx, dy, danio, perforacion=0, hielo_ms=0, evol=False):
        self.x, self.y = x, y
        self.vx, self.vy = dx * self.VEL * (1.18 if evol else 1.0), dy * self.VEL * (1.18 if evol else 1.0)
        self.angulo_deg = -math.degrees(math.atan2(dy, dx))
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
        if self.hielo_ms > 0:
            tipo, tam = "hielo", (22 if self.evol else 16)
        elif self.evol:
            tipo, tam = "plasma", 22
        else:
            tipo, tam = "bala", 14

        frames = _cargar_recurso(tipo, tam)
        if frames:
            idx = (pygame.time.get_ticks() // 70) % len(frames)
            rotado = pygame.transform.rotate(frames[idx], self.angulo_deg)
            rect = rotado.get_rect(center=(int(self.x), int(self.y)))
            pantalla.blit(rotado, rect)
            return

        # Respaldo geométrico
        if self.evol:
            col = (120, 240, 255) if self.hielo_ms > 0 else (255, 110, 210)
            pygame.draw.circle(pantalla, col, (int(self.x), int(self.y)), self.radio)
            pygame.draw.circle(pantalla, (255, 255, 255), (int(self.x), int(self.y)), 2)
        else:
            col = (130, 225, 255) if self.hielo_ms > 0 else BALA
            pygame.draw.circle(pantalla, col, (int(self.x), int(self.y)), self.radio)