import numpy as np
import pygame

RATE = 44100


def _onda(freq, ms, vol=0.3, ruido=False):
    n = int(RATE * ms / 1000)
    t = np.linspace(0, ms / 1000, n, False)
    if ruido:
        onda = np.random.uniform(-1, 1, n)
    else:
        onda = 0.6 * np.sign(np.sin(2 * np.pi * freq * t)) + 0.4 * np.sin(2 * np.pi * freq * t)
    onda *= np.linspace(1, 0, n) ** 2          # caída para que no truene
    return (onda * vol * 32767).astype(np.int16)


def _sonido(*partes):
    mono = np.concatenate(partes)
    estereo = np.ascontiguousarray(np.column_stack((mono, mono)))
    return pygame.sndarray.make_sound(estereo)


class Sonidos:
    def __init__(self):
        self.ok = True
        self.activo = True
        self.ultimo = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=RATE, size=-16, channels=2)
            self.s = {
                "disparo": _sonido(_onda(700, 60, 0.10)),
                "golpe":   _sonido(_onda(0, 130, 0.30, ruido=True)),
                "muerte":  _sonido(_onda(220, 90, 0.15)),
                "gema":    _sonido(_onda(1200, 50, 0.08)),
                "nivel":   _sonido(_onda(523, 90, 0.2), _onda(659, 90, 0.2), _onda(784, 160, 0.2)),
                "ola":     _sonido(_onda(392, 120, 0.2), _onda(523, 220, 0.2)),
                "jefe":    _sonido(_onda(110, 600, 0.4)),
                "fin":     _sonido(_onda(196, 250, 0.3), _onda(147, 500, 0.3)),
            }
        except Exception:
            self.ok = False       # sin audio el juego sigue funcionando

    def play(self, nombre):
        if not (self.ok and self.activo):
            return
        ahora = pygame.time.get_ticks()
        if ahora - self.ultimo.get(nombre, 0) < 60:    # evita saturar el audio
            return
        self.ultimo[nombre] = ahora
        self.s[nombre].play()