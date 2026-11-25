import pygame
from settings import COLUMNAS, FILAS, TAM, PISO, PARED
import random

class Mapa:
    def __init__(self):
        # 0 = piso, 1 = pared
        self.celdas = [[0] * COLUMNAS for _ in range(FILAS)]
        for x in range(COLUMNAS):
            self.celdas[0][x] = self.celdas[FILAS - 1][x] = 1
        for y in range(FILAS):
            self.celdas[y][0] = self.celdas[y][COLUMNAS - 1] = 1
            
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
    def dentro(self, x, y):
        return 0 <= x < COLUMNAS and 0 <= y < FILAS

    def transitable(self, x, y):
        return self.dentro(x, y) and self.celdas[y][x] == 0
    def costo(self, x, y):
        return 1
    def dibujar(self, pantalla):
        for y in range(FILAS):
            for x in range(COLUMNAS):
                color = PARED if self.celdas[y][x] else PISO
                pygame.draw.rect(pantalla, color, (x * TAM, y * TAM, TAM, TAM))
    