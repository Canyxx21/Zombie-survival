from collections import deque

def bfs(mapa, inicio, meta):
    """Devuelve (ruta, explorados). Cola FIFO: expande por niveles."""
    cola = deque([inicio])
    padre = {inicio: None}          # sirve como "visitados" y para reconstruir la ruta

    while cola:
        actual = cola.popleft()
        if actual == meta:
            break
        x, y = actual
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            vecino = (x + dx, y + dy)
            if vecino not in padre and mapa.transitable(*vecino):
                padre[vecino] = actual
                cola.append(vecino)

    if meta not in padre:
        return [], set(padre)

    ruta = []
    nodo = meta
    while nodo != inicio:
        ruta.append(nodo)
        nodo = padre[nodo]
    ruta.reverse()
    return ruta, set(padre)
def bfs_cercano(mapa, inicio, es_meta):
    """BFS hacia la casilla más cercana que cumpla es_meta (no se conoce la posición)."""
    cola = deque([inicio])
    padre = {inicio: None}
    while cola:
        actual = cola.popleft()
        if actual != inicio and es_meta(actual):
            ruta, nodo = [], actual
            while nodo != inicio:
                ruta.append(nodo)
                nodo = padre[nodo]
            ruta.reverse()
            return ruta, set(padre)
        x, y = actual
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            vecino = (x + dx, y + dy)
            if vecino not in padre and mapa.transitable(*vecino):
                padre[vecino] = actual
                cola.append(vecino)
    return [], set(padre)