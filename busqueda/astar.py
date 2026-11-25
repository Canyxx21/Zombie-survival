import heapq
from itertools import count

DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))

def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def astar(mapa, inicio, meta, voraz=False):
    """A*: f = g + h.  Voraz: f = h (ignora lo ya recorrido)."""
    desempate = count()
    abierta = [(manhattan(inicio, meta), next(desempate), inicio)]
    g = {inicio: 0}
    padre = {inicio: None}
    cerrados = set()

    while abierta:
        _, _, actual = heapq.heappop(abierta)
        if actual in cerrados:
            continue
        cerrados.add(actual)
        if actual == meta:
            break
        x, y = actual
        for dx, dy in DIRS:
            vecino = (x + dx, y + dy)
            if not mapa.transitable(*vecino):
                continue
            nuevo = g[actual] + mapa.costo(*vecino)
            if vecino not in g or nuevo < g[vecino]:
                g[vecino] = nuevo
                padre[vecino] = actual
                h = manhattan(vecino, meta)
                f = h if voraz else nuevo + h
                heapq.heappush(abierta, (f, next(desempate), vecino))

    if meta not in cerrados:
        return [], cerrados
    ruta, nodo = [], meta
    while nodo != inicio:
        ruta.append(nodo)
        nodo = padre[nodo]
    ruta.reverse()
    return ruta, cerrados