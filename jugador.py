import pygame
from settings import TAM, JUGADOR

class Jugador:
    RETARDO = 110  # ms entre un paso y otro

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.vida = 10
        self.espera = 0

    def mover(self, teclas, mapa, dt):
        self.espera -= dt
        if self.espera > 0:
            return

        dx = int(teclas[pygame.K_d] or teclas[pygame.K_RIGHT]) - int(teclas[pygame.K_a] or teclas[pygame.K_LEFT])
        dy = int(teclas[pygame.K_s] or teclas[pygame.K_DOWN]) - int(teclas[pygame.K_w] or teclas[pygame.K_UP])
        if dx and dy:      # sin diagonales, igual que en tus algoritmos de 4 direcciones
            dy = 0

        if (dx or dy) and mapa.transitable(self.x + dx, self.y + dy):
            self.x += dx
            self.y += dy
            self.espera = self.RETARDO

    def dibujar(self, pantalla):
        centro = (self.x * TAM + TAM // 2, self.y * TAM + TAM // 2)
        pygame.draw.circle(pantalla, JUGADOR, centro, TAM // 2 - 3)