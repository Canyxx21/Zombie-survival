import math
import random
import pygame


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
    for _ in range(cantidad):
        particulas.append(Particula(x, y, color))