import math
import os
import random
import pygame

BASE_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
_CACHE_FX = {}


def _cargar_tira_fx(nombre_archivo, subcarpeta="", tam=32):
    clave = (subcarpeta, nombre_archivo, tam)
    if clave in _CACHE_FX:
        return _CACHE_FX[clave]

    ruta = os.path.join(BASE_ASSETS, subcarpeta, nombre_archivo) if subcarpeta else os.path.join(BASE_ASSETS, nombre_archivo)
    if not os.path.exists(ruta):
        _CACHE_FX[clave] = None
        return None

    try:
        sheet = pygame.image.load(ruta).convert_alpha()
        w, h = sheet.get_size()
        n = max(1, w // h)
        ancho_frame = w // n
        frames = [
            pygame.transform.scale(sheet.subsurface((i * ancho_frame, 0, ancho_frame, h)), (tam, tam))
            for i in range(n)
        ]
        _CACHE_FX[clave] = frames
        return frames
    except pygame.error:
        _CACHE_FX[clave] = None
        return None


class EfectoSprite:
    """Reproduce una tira animada (sangre, impacto, fogonazo) dentro de la lista de partículas."""
    def __init__(self, x, y, archivo, subcarpeta="", tam=34, duracion_ms=220, angulo_rad=0.0):
        self.x, self.y = x, y
        self.frames = _cargar_tira_fx(archivo, subcarpeta, tam)
        self.vida = duracion_ms if self.frames else 0
        self.vida_max = max(1, duracion_ms)
        self.angulo_deg = -math.degrees(angulo_rad)

    def actualizar(self, dt):
        self.vida -= dt
        return self.vida > 0 and bool(self.frames)

    def dibujar(self, pantalla):
        if not self.frames:
            return
        progreso = 1.0 - max(0.0, self.vida / self.vida_max)
        idx = min(len(self.frames) - 1, int(progreso * len(self.frames)))
        img = self.frames[idx]
        if self.angulo_deg != 0:
            img = pygame.transform.rotate(img, self.angulo_deg)
        rect = img.get_rect(center=(int(self.x), int(self.y)))
        pantalla.blit(img, rect)


class Particula:
    def __init__(self, x, y, color):
        ang = random.uniform(0, math.tau)
        vel = random.uniform(55, 190)
        self.x, self.y = x, y
        self.vx = math.cos(ang) * vel
        self.vy = math.sin(ang) * vel
        self.color = color
        self.vida = random.uniform(180, 320)
        self.vida_max = self.vida
        self.tam = random.randint(3, 6)

    def actualizar(self, dt):
        self.x += self.vx * dt / 1000
        self.y += self.vy * dt / 1000
        self.vx *= 0.92
        self.vy *= 0.92
        self.vida -= dt
        return self.vida > 0

    def dibujar(self, pantalla):
        escala = max(0.2, self.vida / self.vida_max)
        lado = max(2, int(self.tam * escala))
        pygame.draw.rect(pantalla, self.color, (int(self.x - lado / 2), int(self.y - lado / 2), lado, lado))


class TextoFlotante:
    def __init__(self, x, y, texto, color=(255, 240, 210)):
        self.x = x + random.uniform(-6, 6)
        self.y = y - 8
        self.texto = str(texto)
        self.color = color
        self.vida = 550

    def actualizar(self, dt):
        self.y -= 38 * dt / 1000
        self.vida -= dt
        return self.vida > 0

    def dibujar(self, pantalla, fuente):
        sombra = fuente.render(self.texto, True, (15, 12, 10))
        img = fuente.render(self.texto, True, self.color)
        pos = (int(self.x - img.get_width() / 2), int(self.y))
        pantalla.blit(sombra, (pos[0] + 1, pos[1] + 1))
        pantalla.blit(img, pos)


def crear_explosion(particulas, x, y, color, cantidad=9):
    r, g, b = color[:3]
    # Detectar intención visual según el color que manda main.py
    if r > 170 and g < 100 and b < 100:
        # Sangre / daño
        archivo = "gore_burst_strip.png" if cantidad >= 12 else "blood_burst_strip.png"
        particulas.append(EfectoSprite(x, y, archivo, tam=40 if cantidad >= 12 else 30, duracion_ms=260))
    elif b > 200 and r < 150:
        # Impacto de hielo
        particulas.append(EfectoSprite(x, y, "magic_ice_burst_strip.png", subcarpeta="magic", tam=36, duracion_ms=240))
    else:
        # Chispa de impacto de bala
        particulas.append(EfectoSprite(x, y, "bullet_impact_strip.png", tam=24, duracion_ms=160))

    # Mantenemos unas cuantas partículas físicas para darle peso al impacto
    for _ in range(max(3, cantidad // 2)):
        particulas.append(Particula(x, y, color))