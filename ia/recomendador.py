import json
import os
import random

RUTA = os.path.join(os.path.dirname(__file__), "recomendador.json")
CONTEXTOS = ("normal", "horda", "peligro")


def obtener_contexto(jugador, num_enemigos):
    if jugador.vida / max(1, jugador.vida_max) < 0.45:
        return "peligro"
    if num_enemigos >= 22:
        return "horda"
    return "normal"


class Recomendador:
    """Bandido multibrazo contextual epsilon-greedy: adapta las recomendaciones al estado táctico."""

    def __init__(self, nombres, epsilon=0.22):
        self.nombres = list(nombres)
        self.eps = epsilon
        self.q = {c: {n: 5.0 for n in self.nombres} for c in CONTEXTOS}
        self.n = {c: {n: 0 for n in self.nombres} for c in CONTEXTOS}
        self.cargar()

    def recomendar(self, ofrecidas, contexto="normal"):
        """Devuelve (mejora, explorando)."""
        if random.random() < self.eps:
            return random.choice(ofrecidas), True
        tabla = self.q[contexto]
        return max(ofrecidas, key=lambda m: tabla[m]), False

    def aprender(self, mejora, recompensa, contexto="normal"):
        self.n[contexto][mejora] += 1
        k = self.n[contexto][mejora]
        self.q[contexto][mejora] += (recompensa - self.q[contexto][mejora]) / k
        self.guardar()

    def guardar(self):
        with open(RUTA, "w") as f:
            json.dump({"q": self.q, "n": self.n}, f, indent=2)

    def cargar(self):
        if os.path.exists(RUTA):
            try:
                with open(RUTA) as f:
                    datos = json.load(f)
                raw_q = datos.get("q", {})
                raw_n = datos.get("n", {})
                # Si el JSON es del formato anterior (sin contextos), se copia como base
                if raw_q and not isinstance(next(iter(raw_q.values())), dict):
                    for c in CONTEXTOS:
                        for m in self.nombres:
                            self.q[c][m] = raw_q.get(m, 5.0)
                            self.n[c][m] = raw_n.get(m, 0)
                else:
                    for c in CONTEXTOS:
                        for m in self.nombres:
                            self.q[c][m] = raw_q.get(c, {}).get(m, 5.0)
                            self.n[c][m] = raw_n.get(c, {}).get(m, 0)
            except (ValueError, KeyError, StopIteration):
                pass