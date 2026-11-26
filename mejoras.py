def _mul(attr, factor):
    return lambda j: setattr(j, attr, getattr(j, attr) * factor)

def _sum(attr, valor):
    return lambda j: setattr(j, attr, getattr(j, attr) + valor)

def _cadencia(j):
    j.cadencia = max(120, j.cadencia * 0.8)

def _vida(j):
    j.vida_max += 25
    j.vida = min(j.vida_max, j.vida + 25)

MEJORAS = {
    "cadencia":  ("Cadencia +20%", _cadencia),
    "danio":     ("Daño +1", _sum("danio", 1)),
    "velocidad": ("Velocidad +12%", _mul("vel", 1.12)),
    "alcance":   ("Alcance +25%", _mul("alcance", 1.25)),
    "balas":     ("Una bala extra por disparo", _sum("balas", 1)),
    "iman":      ("Imán de gemas +50%", _mul("iman", 1.5)),
    "vida":      ("Vida máxima +25 y curación", _vida),
}