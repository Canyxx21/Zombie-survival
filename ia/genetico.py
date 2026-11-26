import csv
import os
import random
import time

TIPOS_GEN = ["horda", "corredor", "tonto", "elite"]
RUTA_CSV = os.path.join(os.path.dirname(__file__), "genetico_historial.csv")
PRESUPUESTO = 3.0
CAMPOS = ["partida", "generacion", "ola", "media", "maxima",
          "horda", "corredor", "tonto", "elite", "vel", "vida", "danio"]


class Genoma:
    def __init__(self, tipo, vel, vida, danio):
        self.tipo = tipo
        self.vel, self.vida, self.danio = vel, vida, danio
        self.normalizar()
        self.acum = 0.0     # aptitud acumulada en la ola
        self.n = 0          # enemigos con este genoma
        self.fit = 0.0

    def normalizar(self):
        """Limita cada gen y reparte el presupuesto: vel + vida + danio = 3."""
        for _ in range(2):
            v = [min(2.0, max(0.4, x)) for x in (self.vel, self.vida, self.danio)]
            k = PRESUPUESTO / sum(v)
            self.vel, self.vida, self.danio = (x * k for x in v)

    @staticmethod
    def aleatorio():
        return Genoma(random.choice(TIPOS_GEN), *(random.uniform(0.6, 1.4) for _ in range(3)))

    def copia(self):
        return Genoma(self.tipo, self.vel, self.vida, self.danio)


class Poblacion:
    def __init__(self, tamano=24):
        self.genomas = [Genoma.aleatorio() for _ in range(tamano)]
        self.generacion = 1
        self.historial = []
        self.partida = int(time.time())

    def registrar(self, genoma, aptitud):
        genoma.acum += aptitud
        genoma.n += 1

    def conteo(self):
        return {t: sum(1 for g in self.genomas if g.tipo == t) for t in TIPOS_GEN}

    # ---- operadores genéticos ----
    def _torneo(self, k=3):
        return max(random.sample(self.genomas, k), key=lambda g: g.fit)

    def _cruce(self, a, b):
        pick = lambda x, y: random.choice((x, y))
        return Genoma(pick(a.tipo, b.tipo), pick(a.vel, b.vel), pick(a.vida, b.vida), pick(a.danio, b.danio))

    def _mutar(self, g):
        if random.random() < 0.12:
            g.tipo = random.choice(TIPOS_GEN)
        if random.random() < 0.35:
            g.vel += random.gauss(0, 0.25)
        if random.random() < 0.35:
            g.vida += random.gauss(0, 0.25)
        if random.random() < 0.35:
            g.danio += random.gauss(0, 0.25)
        g.normalizar()
        return g

    def evolucionar(self, ola):
        for g in self.genomas:
            g.fit = g.acum / g.n if g.n else 0.0
        orden = sorted(self.genomas, key=lambda g: g.fit, reverse=True)
        n = len(self.genomas)
        stats = dict(
            generacion=self.generacion, ola=ola,
            media=sum(g.fit for g in self.genomas) / n, maxima=orden[0].fit,
            vel=sum(g.vel for g in self.genomas) / n,
            vida=sum(g.vida for g in self.genomas) / n,
            danio=sum(g.danio for g in self.genomas) / n,
            **self.conteo())
        self.historial.append(stats)
        self._guardar(stats)

        nueva = [g.copia() for g in orden[:2]]                 # elitismo
        while len(nueva) < n:
            nueva.append(self._mutar(self._cruce(self._torneo(), self._torneo())))
        self.genomas = nueva
        self.generacion += 1
        return stats

    def _guardar(self, s):
        nuevo = not os.path.exists(RUTA_CSV)
        fila = {"partida": self.partida}
        fila.update({k: round(v, 2) if isinstance(v, float) else v for k, v in s.items()})
        with open(RUTA_CSV, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=CAMPOS)
            if nuevo:
                w.writeheader()
            w.writerow(fila)