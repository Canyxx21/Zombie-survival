from armas import CATALOGO_ARMAS


def _mul(attr, factor):
    return lambda j: setattr(j, attr, getattr(j, attr) * factor)


def _sum(attr, valor):
    return lambda j: setattr(j, attr, getattr(j, attr) + valor)


def _cadencia(j):
    j.cadencia = max(140, j.cadencia * 0.82)


def _vida(j):
    j.vida_max += 25
    j.vida = min(j.vida_max, j.vida + 25)


def _hielo(j):
    j.hielo_ms = max(1800, j.hielo_ms + 600)


def _escudo(j):
    if j.escudo_recarga == 0:
        j.escudo_recarga = 12000
    else:
        j.escudo_recarga = max(5000, j.escudo_recarga - 2500)
    j.escudo_activo = True
    j.escudo_cd = 0


def _arma(clave):
    return lambda j: j.arsenal.mejorar_arma(clave)


MEJORAS = {
    "arma_rifle":    ("Arma: Rifle Pulso / Plasma", _arma("rifle")),
    "arma_orbital":  ("Arma: Orbes Orbitales / Sierra", _arma("orbital")),
    "arma_nova":     ("Arma: Nova Eléctrica / Tesla", _arma("nova")),
    "arma_escopeta": ("Arma: Escopeta Fría / Ventisca", _arma("escopeta")),
    "cadencia":      ("Cadencia global +18%", _cadencia),
    "danio":         ("Daño global +1", _sum("danio", 1)),
    "velocidad":     ("Velocidad +12%", _mul("vel", 1.12)),
    "balas":         ("Proyectil extra +1", _sum("balas_extra", 1)),
    "perforacion":   ("Perforación +1 enemigo", _sum("perforacion", 1)),
    "hielo":         ("Munición fría (+ralentización)", _hielo),
    "escudo":        ("Escudo recargable", _escudo),
    "vida":          ("Vida máxima +25 y curación", _vida),
}


def mejoras_disponibles(jugador):
    """Filtra las armas que ya llegaron a Nv.5 (EVOLUCIÓN) para no ofrecerlas de más."""
    disponibles = []
    for k in MEJORAS:
        if k.startswith("arma_"):
            clave = k.split("_", 1)[1]
            if jugador.arsenal.nivel_de(clave) >= 5:
                continue
        disponibles.append(k)
    return disponibles


def texto_carta(clave, jugador):
    if clave.startswith("arma_"):
        arma = clave.split("_", 1)[1]
        nv = jugador.arsenal.nivel_de(arma)
        cfg = CATALOGO_ARMAS[arma]
        if nv == 0:
            return f"NUEVA: {cfg['nombre']}", cfg["desc"]
        if nv == 4:
            return f"¡EVOLUCIÓN! {cfg['evol']}", "Nv.5 MAX: Transformación definitiva"
        return f"{cfg['nombre']} (Nv.{nv} -> {nv + 1})", cfg["desc"]
    return MEJORAS[clave][0], "Mejora pasiva acumulable"