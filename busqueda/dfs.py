DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))

def dfs(mapa, inicio, meta):
    """Pila LIFO: se va por una rama hasta el fondo. No garantiza la ruta corta."""
    pila = [inicio]
    padre = {inicio: None}
    visitados = set()

    while pila:
        actual = pila.pop()
        if actual in visitados:
            continue
        visitados.add(actual)
        if actual == meta:
            break
        x, y = actual
        for dx, dy in DIRS:
            vecino = (x + dx, y + dy)
            if vecino not in visitados and mapa.transitable(*vecino):
                padre[vecino] = actual
                pila.append(vecino)

    if meta not in visitados:
        return [], visitados
    ruta, nodo = [], meta
    while nodo != inicio:
        ruta.append(nodo)
        nodo = padre[nodo]
    ruta.reverse()
    return ruta, visitados