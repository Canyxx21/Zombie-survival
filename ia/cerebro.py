import os
import random
from collections import deque
import numpy as np
from settings import COLUMNAS, FILAS, TAM

RUTA = os.path.join(os.path.dirname(__file__), "cerebro_jefe.npz")
ESCALA = 6.0     # casillas máximas que predice la red


class Cerebro:
    """Red 8-10-2 (tanh) entrenada en línea con percepción de movimiento y muros cercanos."""

    def __init__(self):
        self._iniciar_pesos()
        self.pos = deque(maxlen=2)     # posiciones de hace 250 ms y 500 ms
        self.pend = []                 # muestras esperando su etiqueta
        self.memoria = []
        self.acum = 0
        self.err_nn, self.err_base, self.muestras = 3.0, 3.0, 0
        self.cargar()

    def _iniciar_pesos(self):
        rng = np.random.default_rng(1)
        self.w1, self.b1 = rng.normal(0, 0.45, (8, 10)), np.zeros(10)
        self.w2, self.b2 = rng.normal(0, 0.45, (10, 2)), np.zeros(2)

    def reiniciar_estado(self):
        """Limpia el historial temporal al iniciar partida/ola para evitar saltos falsos."""
        self.pos.clear()
        self.pend.clear()
        self.acum = 0

    def adelante(self, x):
        h = np.tanh(x @ self.w1 + self.b1)
        o = np.tanh(h @ self.w2 + self.b2)
        return h, o

    def entrenar(self, x, t, lr=0.05):
        h, o = self.adelante(x)
        d_o = (o - t) * (1 - o ** 2)
        d_h = (d_o @ self.w2.T) * (1 - h ** 2)
        self.w2 -= lr * np.outer(h, d_o)
        self.b2 -= lr * d_o
        self.w1 -= lr * np.outer(x, d_h)
        self.b1 -= lr * d_h

    def features(self, cx, cy, mapa=None):
        gx, gy = int(cx), int(cy)
        espacio_x, espacio_y = 0.0, 0.0
        if mapa is not None:
            # +1 libre a la derecha / -1 libre a la izquierda (igual en vertical)
            espacio_x = (int(mapa.transitable(gx + 1, gy)) - int(mapa.transitable(gx - 1, gy))) * 0.5
            espacio_y = (int(mapa.transitable(gx, gy + 1)) - int(mapa.transitable(gx, gy - 1))) * 0.5

        f = [cx / COLUMNAS, cy / FILAS, 0.0, 0.0, 0.0, 0.0, espacio_x, espacio_y]
        if len(self.pos) == 2:
            (x1, y1), (x2, y2) = self.pos[-1], self.pos[-2]
            f[2:6] = [(cx - x2) / 4, (cy - y2) / 4, (cx - x1) / 2, (cy - y1) / 2]
        return np.array(f)

    def observar(self, j, dt, mapa=None):
        """Cada 250 ms guarda una muestra; 1.25 s después la usa para entrenar."""
        self.acum += dt
        if self.acum < 250:
            return
        self.acum = 0
        cx, cy = j.x / TAM, j.y / TAM
        f = self.features(cx, cy, mapa)
        self.pos.append((cx, cy))
        self.pend.append((f, cx, cy))
        if len(self.pend) > 5:
            f0, x0, y0 = self.pend.pop(0)
            t = np.clip(np.array([cx - x0, cy - y0]) / ESCALA, -1, 1)
            pred = self.adelante(f0)[1]
            self.err_nn = 0.95 * self.err_nn + 0.05 * float(np.linalg.norm((pred - t) * ESCALA))
            self.err_base = 0.95 * self.err_base + 0.05 * float(np.linalg.norm(t * ESCALA))
            self.memoria.append((f0, t))
            if len(self.memoria) > 800:
                self.memoria.pop(0)
            self.entrenar(f0, t)
            self.muestras += 1

    def predecir(self, j, mapa=None):
        """Casilla donde la red cree que estarás en ~1.2 s."""
        cx, cy = j.x / TAM, j.y / TAM
        o = self.adelante(self.features(cx, cy, mapa))[1]
        x = int(round(min(COLUMNAS - 2, max(1, cx + o[0] * ESCALA))))
        y = int(round(min(FILAS - 2, max(1, cy + o[1] * ESCALA))))
        return x, y

    def repasar(self, veces=300):
        for _ in range(veces if self.memoria else 0):
            f, t = random.choice(self.memoria)
            self.entrenar(f, t)

    def guardar(self):
        np.savez(RUTA, w1=self.w1, b1=self.b1, w2=self.w2, b2=self.b2,
                 err_nn=self.err_nn, err_base=self.err_base, muestras=self.muestras)

    def cargar(self):
        if os.path.exists(RUTA):
            try:
                d = np.load(RUTA)
                if d["w1"].shape != (8, 10):
                    # Migra limpio si el archivo previo era de la arquitectura 6-8-2
                    self._iniciar_pesos()
                    return
                self.w1, self.b1, self.w2, self.b2 = d["w1"], d["b1"], d["w2"], d["b2"]
                self.err_nn, self.err_base = float(d["err_nn"]), float(d["err_base"])
                self.muestras = int(d["muestras"])
            except (OSError, KeyError, ValueError):
                self._iniciar_pesos()