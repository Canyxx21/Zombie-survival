import random
from collections import deque
import pygame
from settings import (
    COLUMNAS, FILAS, TAM, PISO, PISO_GRID,
    PARED, PARED_BORDE, PARED_SOMBRA, LODO, LODO_BRILLO
)


class Mapa:
    def __init__(self):
        # 0 = piso, 1 = pared
        self.celdas = [[0] * COLUMNAS for _ in range(FILAS)]
        for x in range(COLUMNAS):
            self.celdas[0][x] = self.celdas[FILAS - 1][x] = 1
        for y in range(FILAS):
            self.celdas[y][0] = self.celdas[y][COLUMNAS - 1] = 1
        self.dist = {}
        self.lodo = set()
        self.flujo_meta = None

    def generar_obstaculos(self, cantidad=18, origen=(15, 10)):
        """Genera muros aleatorios y garantiza que todo el piso siga conectado."""
        while True:
            for y in range(1, FILAS - 1):
                for x in range(1, COLUMNAS - 1):
                    self.celdas[y][x] = 0

            for _ in range(cantidad):
                x = random.randint(3, COLUMNAS - 5)
                y = random.randint(3, FILAS - 5)
                horizontal = random.random() < 0.5
                for k in range(random.randint(2, 5)):
                    cx, cy = (x + k, y) if horizontal else (x, y + k)
                    if self.dentro(cx, cy) and not (abs(cx - origen[0]) < 3 and abs(cy - origen[1]) < 3):
                        self.celdas[cy][cx] = 1

            self.calcular_flujo(origen)
            transitables = sum(
                1 for y in range(1, FILAS - 1)
                for x in range(1, COLUMNAS - 1)
                if self.celdas[y][x] == 0
            )
            if len(self.dist) == transitables:
                break

    def dentro(self, x, y):
        return 0 <= x < COLUMNAS and 0 <= y < FILAS

    def transitable(self, x, y):
        return self.dentro(x, y) and self.celdas[y][x] == 0

    def costo(self, x, y):
        return 4 if (x, y) in self.lodo else 1

    def ve(self, a, b, alcance):
        """Línea de visión con Bresenham: las paredes bloquean."""
        (x0, y0), (x1, y1) = a, b
        if ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5 > alcance:
            return False
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while (x0, y0) != (x1, y1):
            if self.celdas[y0][x0] == 1:
                return False
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy
        return True

    def choca(self, px, py, r):
        """¿Un círculo en (px, py) con radio r toca alguna pared?"""
        for cy in range(int((py - r) // TAM), int((py + r) // TAM) + 1):
            for cx in range(int((px - r) // TAM), int((px + r) // TAM) + 1):
                if not self.dentro(cx, cy) or self.celdas[cy][cx] == 1:
                    mx = max(cx * TAM, min(px, cx * TAM + TAM))
                    my = max(cy * TAM, min(py, cy * TAM + TAM))
                    if (px - mx) ** 2 + (py - my) ** 2 < r * r:
                        return True
        return False

    def calcular_flujo(self, meta):
        """BFS desde la meta: distancia de cada casilla hasta el jugador."""
        dist = {meta: 0}
        cola = deque([meta])
        while cola:
            ax, ay = cola.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                v = (ax + dx, ay + dy)
                if v not in dist and self.transitable(*v):
                    dist[v] = dist[(ax, ay)] + 1
                    cola.append(v)
        self.dist = dist
        self.flujo_meta = meta

    def generar_lodo(self, parches=7):
        self.lodo.clear()
        for _ in range(parches):
            x = random.randint(2, COLUMNAS - 6)
            y = random.randint(2, FILAS - 5)
            for dy in range(3):
                for dx in range(4):
                    if self.transitable(x + dx, y + dy):
                        self.lodo.add((x + dx, y + dy))

    def dibujar(self, pantalla):
        for y in range(FILAS):
            for x in range(COLUMNAS):
                rx, ry = x * TAM, y * TAM
                if self.celdas[y][x]:
                    pygame.draw.rect(pantalla, PARED_SOMBRA, (rx, ry, TAM, TAM))
                    pygame.draw.rect(pantalla, PARED, (rx + 1, ry + 1, TAM - 2, TAM - 4))
                    pygame.draw.rect(pantalla, PARED_BORDE, (rx + 1, ry + 1, TAM - 2, 3))
                elif (x, y) in self.lodo:
                    pygame.draw.rect(pantalla, LODO, (rx, ry, TAM, TAM))
                    pygame.draw.circle(pantalla, LODO_BRILLO, (rx + (x * 7 + y * 5) % 20 + 6, ry + (y * 9) % 18 + 7), 2)
                else:
                    pygame.draw.rect(pantalla, PISO, (rx, ry, TAM, TAM))
                    pygame.draw.rect(pantalla, PISO_GRID, (rx, ry, TAM, TAM), 1)