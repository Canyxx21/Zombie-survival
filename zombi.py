import pygame
from settings import TAM, ALCANCE
from busqueda.bfs import bfs, bfs_cercano
from busqueda.dfs import dfs
from busqueda.astar import astar

ALGORITMOS = {
    "A*":    (lambda m, i, f: astar(m, i, f),              (200, 55, 45)),
    "Voraz": (lambda m, i, f: astar(m, i, f, voraz=True),  (224, 138, 44)),
    "DFS":   (dfs,                                          (201, 194, 74)),
    "BFS":   (bfs,                                          (120, 200, 120)),
}
AZUL = (74, 163, 199)

class Zombi:
    RETARDO = 450  # ms por casilla

    def __init__(self, x, y, tipo):
        self.x, self.y = x, y
        self.tipo = tipo
        self.buscar, self.color = ALGORITMOS[tipo]
        self.recalcula_cada = 6 if tipo == "DFS" else 1   # DFS sigue su ruta guardada
        self.pasos = 0
        self.espera = 0
        self.ruta = []
        self.explorados = set()
        self.modo = "busqueda"
        self.ultima_vista = None
        self.visitadas = set()
        # estadísticas (solo cuando persigue)
        self.busquedas = 0
        self.total_nodos = 0
        self.total_costo = 0

    def promedio_nodos(self):
        return self.total_nodos / self.busquedas if self.busquedas else 0

    def promedio_costo(self):
        return self.total_costo / self.busquedas if self.busquedas else 0

    def _marcar_visibles(self, mapa):
        """Las casillas que ve ya no hace falta explorarlas."""
        for cy in range(self.y - ALCANCE, self.y + ALCANCE + 1):
            for cx in range(self.x - ALCANCE, self.x + ALCANCE + 1):
                if mapa.dentro(cx, cy) and mapa.ve((self.x, self.y), (cx, cy), ALCANCE):
                    self.visitadas.add((cx, cy))

    def actualizar(self, mapa, jugador, dt, otros):
        self.espera -= dt
        if self.espera > 0:
            return
        pos = (self.x, self.y)
        meta = (jugador.x, jugador.y)

        # --- estados ---
        if mapa.ve(pos, meta, ALCANCE):
            self.modo = "persecucion"
            self.ultima_vista = meta
            self.visitadas.clear()
        elif self.modo == "persecucion" and pos == self.ultima_vista:
            self.modo = "busqueda"
            self.ultima_vista = None

        # --- decidir ruta ---
        if self.modo == "persecucion":
            if not self.ruta or self.pasos % self.recalcula_cada == 0:
                self.ruta, self.explorados = self.buscar(mapa, pos, self.ultima_vista)
                self.busquedas += 1
                self.total_nodos += len(self.explorados)
                self.total_costo += sum(mapa.costo(cx, cy) for cx, cy in self.ruta)
        else:
            self._marcar_visibles(mapa)
            self.ruta, self.explorados = bfs_cercano(
                mapa, pos, lambda c: c not in self.visitadas)

        # --- moverse (sin encimarse) ---
        if self.ruta:
            sig = self.ruta[0]
            ocupada = sig == meta or any((o.x, o.y) == sig for o in otros if o is not self)
            if ocupada:
                self.ruta = []
                self.espera = 150
                return
            self.x, self.y = sig
            self.ruta.pop(0)
            self.pasos += 1
        self.espera = self.RETARDO

    def dibujar(self, pantalla, debug=False):
        if debug:
            capa = pygame.Surface((TAM, TAM), pygame.SRCALPHA)
            capa.fill((*self.color, 35))
            for cx, cy in self.explorados:
                pantalla.blit(capa, (cx * TAM, cy * TAM))
            if self.ruta:
                puntos = [(self.x * TAM + TAM // 2, self.y * TAM + TAM // 2)]
                puntos += [(cx * TAM + TAM // 2, cy * TAM + TAM // 2) for cx, cy in self.ruta]
                pygame.draw.lines(pantalla, self.color, False, puntos, 2)
        centro = (self.x * TAM + TAM // 2, self.y * TAM + TAM // 2)
        pygame.draw.circle(pantalla, self.color, centro, TAM // 2 - 4)
        if self.modo == "busqueda":
            pygame.draw.circle(pantalla, AZUL, centro, TAM // 2 - 1, 2)   # anillo azul