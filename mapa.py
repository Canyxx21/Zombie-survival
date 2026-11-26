import random
from collections import deque
import pygame
from settings import COLUMNAS, FILAS, TAM, PISO, PARED,LODO


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

    def generar_obstaculos(self, cantidad=14):
        for _ in range(cantidad):
            x = random.randint(3, COLUMNAS - 5)
            y = random.randint(3, FILAS - 5)
            horizontal = random.random() < 0.5
            for k in range(random.randint(2, 5)):
                cx, cy = (x + k, y) if horizontal else (x, y + k)
                # dejamos libre el centro, donde aparece el jugador
                if self.dentro(cx, cy) and not (abs(cx - 15) < 3 and abs(cy - 10) < 3):
                    self.celdas[cy][cx] = 1

    def dentro(self, x, y):
        return 0 <= x < COLUMNAS and 0 <= y < FILAS

    def transitable(self, x, y):
        return self.dentro(x, y) and self.celdas[y][x] == 0

    def costo(self, x, y):
        return 1

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
                    # punto del rectángulo más cercano al centro del círculo
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
    def costo(self,x,y):
        return 4 if (x,y) in self.lodo else 1
    def generar_lodo(self, parches=7):
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
                if self.celdas[y][x]:
                    color = PARED
                elif (x, y) in self.lodo:
                    color = LODO
                else:
                    color = PISO
                pygame.draw.rect(pantalla, color, (x * TAM, y * TAM, TAM, TAM))