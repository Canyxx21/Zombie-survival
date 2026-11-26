import json
import os
import random

RUTA = os.path.join(os.path.dirname(__file__), "recomendador.json")

class Recomendador:
    """Bandido multibrazo epsilon-greedy: aprende qué mejoras le sirven al jugador."""

    def __init__(self, nombres, epsilon=0.25):
        self.eps = epsilon
        self.q = {n: 5.0 for n in nombres}    # valor inicial optimista: invita a probar todo
        self.n = {n: 0 for n in nombres}
        self.cargar()

    def recomendar(self, ofrecidas):
        """Devuelve (mejora, explorando)."""
        if random.random() < self.eps:
            return random.choice(ofrecidas), True
        return max(ofrecidas, key=lambda m: self.q[m]), False

    def aprender(self, mejora, recompensa):
        self.n[mejora] += 1
        self.q[mejora] += (recompensa - self.q[mejora]) / self.n[mejora]   # promedio incremental
        self.guardar()

    def guardar(self):
        with open(RUTA, "w") as f:
            json.dump({"q": self.q, "n": self.n}, f)

    def cargar(self):
        if os.path.exists(RUTA):
            try:
                with open(RUTA) as f:
                    datos = json.load(f)
                for m in self.q:
                    self.q[m] = datos["q"].get(m, self.q[m])
                    self.n[m] = datos["n"].get(m, 0)
            except (ValueError, KeyError):
                pass