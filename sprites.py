import math
import os
import pygame

BASE_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
_CACHE = {}
_FALLIDOS = set()

# Mapeo entre los nombres internos de tu juego y las carpetas en assets/
MAPEO_CARPETAS = {
    "jugador": "survivor",
    "corredor": "runner",
    "elite": "hazmat",
    "jefe": "brute",
    "tonto": "walker_b",
    "horda": "walker",
    "zombie": "walker",
}


def _angulo_a_direccion(angulo):
    """Convierte el ángulo en radianes hacia la dirección 3/4 correspondiente."""
    grados = math.degrees(angulo) % 360
    if 45 <= grados < 135:
        return "down"
    elif 135 <= grados < 225:
        return "left"
    elif 225 <= grados < 315:
        return "up"
    return "right"


def _resolver_carpeta(nombre):
    subcarpeta = MAPEO_CARPETAS.get(nombre, nombre)
    ruta_frames = os.path.join(BASE_ASSETS, subcarpeta, "frames")
    if os.path.isdir(ruta_frames):
        return ruta_frames
    ruta_directa = os.path.join(BASE_ASSETS, subcarpeta)
    if os.path.isdir(ruta_directa):
        return ruta_directa
    return None


def _cargar_animaciones(nombre, tam):
    clave = (nombre, tam)
    if clave in _CACHE:
        return _CACHE[clave]
    if clave in _FALLIDOS:
        return None

    carpeta = _resolver_carpeta(nombre)
    if not carpeta:
        _FALLIDOS.add(clave)
        return None

    animaciones = {}
    for estado in ("walk", "idle"):
        for direccion in ("down", "up", "left", "right"):
            frames = []
            idx = 0
            while True:
                ruta = os.path.join(carpeta, f"{estado}_{direccion}_{idx:02d}.png")
                if not os.path.exists(ruta):
                    break
                try:
                    img = pygame.image.load(ruta).convert_alpha()
                    # scale (sin smooth) mantiene el pixel art nítido y sin bordes borrosos
                    img = pygame.transform.scale(img, (tam, tam))
                    frames.append(img)
                except pygame.error:
                    break
                idx += 1
            if frames:
                animaciones[f"{estado}_{direccion}"] = frames

    if animaciones:
        _CACHE[clave] = animaciones
        return animaciones

    _FALLIDOS.add(clave)
    return None


def _aplicar_flash(surface):
    """Crea un destello blanco respetando la silueta transparente del sprite."""
    copia = surface.copy()
    copia.fill((255, 255, 255, 180), special_flags=pygame.BLEND_RGBA_ADD)
    return copia


def dibujar_entidad_estilizada(pantalla, nombre, x, y, radio, angulo, color, flash=False):
    cx, cy = int(x), int(y)
    # Sombra suave en el suelo
    pygame.draw.ellipse(pantalla, (10, 12, 18), (cx - radio, cy + int(radio * 0.45), radio * 2, int(radio * 0.8)))

    # Escala visual proporcional al hitbox (ajusta 3.4 si los quieres más grandes o chicos)
    tam = max(24, int(radio * 3.4))
    animaciones = _cargar_animaciones(nombre, tam)

    if animaciones is not None:
        direccion = _angulo_a_direccion(angulo)
        frames = animaciones.get(f"walk_{direccion}") or animaciones.get(f"idle_{direccion}")

        if frames:
            idx = (pygame.time.get_ticks() // 115) % len(frames)
            sprite = frames[idx]
            if flash:
                sprite = _aplicar_flash(sprite)
            # Subimos un poco el centro (- radio * 0.25) para que los pies queden sobre el hitbox
            rect = sprite.get_rect(center=(cx, cy - int(radio * 0.25)))
            pantalla.blit(sprite, rect)
            return

    # --- Respaldo geométrico original si falta algún sprite ---
    col = (255, 255, 255) if flash else color
    borde = tuple(min(255, c + 55) for c in col)
    oscuro = tuple(max(0, int(c * 0.45)) for c in col)

    if nombre == "jugador":
        pygame.draw.circle(pantalla, oscuro, (cx, cy), radio + 1)
        pygame.draw.circle(pantalla, col, (cx, cy), radio - 1)
        vx = x + math.cos(angulo) * (radio * 0.45)
        vy = y + math.sin(angulo) * (radio * 0.45)
        pygame.draw.circle(pantalla, (235, 252, 255), (int(vx), int(vy)), max(3, radio // 2))
        px = x + math.cos(angulo) * (radio + 6)
        py = y + math.sin(angulo) * (radio + 6)
        pygame.draw.line(pantalla, (255, 230, 120), (cx, cy), (int(px), int(py)), 3)

    elif nombre == "corredor":
        r = radio + 3
        pts = [
            (x + math.cos(angulo) * r, y + math.sin(angulo) * r),
            (x + math.cos(angulo + 2.35) * r, y + math.sin(angulo + 2.35) * r),
            (x + math.cos(angulo + math.pi) * (r * 0.45), y + math.sin(angulo + math.pi) * (r * 0.45)),
            (x + math.cos(angulo - 2.35) * r, y + math.sin(angulo - 2.35) * r),
        ]
        pygame.draw.polygon(pantalla, col, pts)
        pygame.draw.polygon(pantalla, borde, pts, 2)

    elif nombre == "elite":
        pts = [
            (x + math.cos(angulo + i * math.pi / 3) * radio,
             y + math.sin(angulo + i * math.pi / 3) * radio)
            for i in range(6)
        ]
        pygame.draw.polygon(pantalla, oscuro, pts)
        pygame.draw.polygon(pantalla, col, pts, 3)
        pygame.draw.circle(pantalla, borde, (cx, cy), max(3, radio // 3))

    elif nombre == "jefe":
        pts = [
            (x + math.cos(angulo + i * math.pi / 4) * radio,
             y + math.sin(angulo + i * math.pi / 4) * radio)
            for i in range(8)
        ]
        pygame.draw.polygon(pantalla, oscuro, pts)
        pygame.draw.polygon(pantalla, col, pts, 3)
        pygame.draw.circle(pantalla, (245, 195, 255), (cx, cy), 6)

    else:
        pygame.draw.circle(pantalla, oscuro, (cx, cy), radio)
        pygame.draw.circle(pantalla, col, (cx, cy), radio - 2)
        if nombre == "tonto":
            pygame.draw.circle(pantalla, (45, 42, 15), (cx, cy), radio - 5, 2)
        for lado in (-0.45, 0.45):
            ex = x + math.cos(angulo + lado) * (radio * 0.55)
            ey = y + math.sin(angulo + lado) * (radio * 0.55)
            pygame.draw.circle(pantalla, (255, 245, 200), (int(ex), int(ey)), 2)