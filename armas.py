import math
import pygame


CATALOGO_ARMAS = {
    "rifle": {
        "nombre": "Rifle Pulso",
        "evol": "CAÑÓN PLASMA",
        "color": (255, 224, 102),
        "desc": "Disparo rápido de precisión (Nv.5: Plasma perforante)",
    },
    "orbital": {
        "nombre": "Orbes Orbitales",
        "evol": "SIERRA SOLAR",
        "color": (90, 235, 255),
        "desc": "Escudos giratorios que cortan enemigos (Nv.5: 6 Sierras)",
    },
    "nova": {
        "nombre": "Nova Eléctrica",
        "evol": "TORMENTA TESLA",
        "color": (195, 130, 255),
        "desc": "Descarga de rayos en área cercana (Nv.5: Rayos masivos)",
    },
    "escopeta": {
        "nombre": "Escopeta Criogénica",
        "evol": "VENTISCA",
        "color": (120, 210, 255),
        "desc": "Abanico que ralentiza enemigos (Nv.5: 9 balas heladas)",
    },
}


class OndaNova:
    """Efecto visual de la Nova Eléctrica / Tormenta Tesla."""
    def __init__(self, x, y, radio_max, color):
        self.x, self.y = x, y
        self.radio_max = radio_max
        self.color = color
        self.vida = 240
        self.vida_max = 240

    def actualizar(self, dt):
        self.vida -= dt
        return self.vida > 0

    def dibujar(self, pantalla):
        progreso = 1.0 - max(0, self.vida / self.vida_max)
        r = max(8, int(self.radio_max * progreso))
        pygame.draw.circle(pantalla, self.color, (int(self.x), int(self.y)), r, 3)


class Arsenal:
    """Gestiona múltiples armas simultáneas que evolucionan al llegar a nivel 5."""

    def __init__(self):
        self.niveles = {"rifle": 1}   # empieza con Rifle Pulso Nv.1
        self.timers = {"rifle": 0, "nova": 0, "escopeta": 0}
        self.angulo_orbita = 0.0
        self.golpe_orbital = {}       # id_enemigo -> cooldown ms

    def nivel_de(self, arma):
        return self.niveles.get(arma, 0)

    def evolucionada(self, arma):
        return self.niveles.get(arma, 0) >= 5

    def mejorar_arma(self, arma):
        actual = self.niveles.get(arma, 0)
        self.niveles[arma] = min(5, actual + 1)
        if arma not in self.timers:
            self.timers[arma] = 0

    def actualizar(self, jugador, enemigos, proyectiles, ondas, dt, snd):
        # Limpiar cooldowns de contacto orbital
        for eid in list(self.golpe_orbital):
            self.golpe_orbital[eid] -= dt
            if self.golpe_orbital[eid] <= 0:
                del self.golpe_orbital[eid]

        # 1. RIFLE PULSO / CAÑÓN PLASMA
        nv_rifle = self.nivel_de("rifle")
        if nv_rifle > 0:
            self.timers["rifle"] -= dt
            if self.timers["rifle"] <= 0 and enemigos:
                obj = min(enemigos, key=lambda e: (e.x - jugador.x) ** 2 + (e.y - jugador.y) ** 2)
                dx, dy = obj.x - jugador.x, obj.y - jugador.y
                d = math.hypot(dx, dy)
                if 0 < d <= jugador.alcance:
                    jugador.apunta = math.atan2(dy, dx)
                    evol = nv_rifle >= 5
                    balas = (3 if evol else 1 + nv_rifle // 3) + jugador.balas_extra
                    danio = jugador.danio + (2 if evol else nv_rifle // 2)
                    perf = jugador.perforacion + (2 if evol else (1 if nv_rifle >= 3 else 0))
                    cad = max(130, jugador.cadencia * (0.55 if evol else (1.0 - 0.08 * (nv_rifle - 1))))
                    for i in range(balas):
                        a = jugador.apunta + (i - (balas - 1) / 2) * 0.14
                        proyectiles.append(
                            jugador.crear_bala(math.cos(a), math.sin(a), danio, perf, jugador.hielo_ms, evol)
                        )
                    self.timers["rifle"] = cad
                    snd.play("disparo")

        # 2. ORBES ORBITALES / SIERRA SOLAR
        nv_orb = self.nivel_de("orbital")
        if nv_orb > 0:
            evol = nv_orb >= 5
            vel_giro = 4.6 if evol else (2.4 + 0.35 * nv_orb)
            self.angulo_orbita += vel_giro * dt / 1000
            for ox, oy, r_orbe in self.posiciones_orbitales(jugador):
                danio_orb = jugador.danio + (2 if evol else nv_orb)
                for e in enemigos:
                    if e.viva and id(e) not in self.golpe_orbital:
                        if math.hypot(e.x - ox, e.y - oy) < e.radio + r_orbe:
                            self.golpe_orbital[id(e)] = 260 if evol else 420
                            jugador.aplicar_impacto_directo(e, danio_orb, 600 if evol else 0)

        # 3. NOVA ELÉCTRICA / TORMENTA TESLA
        nv_nova = self.nivel_de("nova")
        if nv_nova > 0:
            self.timers["nova"] -= dt
            if self.timers["nova"] <= 0 and enemigos:
                evol = nv_nova >= 5
                radio_nova = 185 if evol else (115 + 14 * nv_nova)
                cerca = [e for e in enemigos if e.viva and math.hypot(e.x - jugador.x, e.y - jugador.y) <= radio_nova]
                if cerca:
                    danio_nova = jugador.danio + (3 if evol else nv_nova)
                    ondas.append(OndaNova(jugador.x, jugador.y, radio_nova, (220, 140, 255) if evol else (150, 110, 240)))
                    for e in cerca:
                        jugador.aplicar_impacto_directo(e, danio_nova, 1500 if evol else 500)
                    self.timers["nova"] = 1400 if evol else max(1600, 2800 - 220 * nv_nova)
                    snd.play("nivel")

        # 4. ESCOPETA CRIOGÉNICA / VENTISCA
        nv_esc = self.nivel_de("escopeta")
        if nv_esc > 0:
            self.timers["escopeta"] -= dt
            if self.timers["escopeta"] <= 0 and enemigos:
                obj = min(enemigos, key=lambda e: (e.x - jugador.x) ** 2 + (e.y - jugador.y) ** 2)
                dx, dy = obj.x - jugador.x, obj.y - jugador.y
                d = math.hypot(dx, dy)
                if 0 < d <= jugador.alcance * 0.9:
                    base_ang = math.atan2(dy, dx)
                    evol = nv_esc >= 5
                    perdigones = (9 if evol else 3 + nv_esc) + jugador.balas_extra
                    danio_esc = max(1, jugador.danio + (1 if evol else 0))
                    perf_esc = jugador.perforacion + (1 if evol else 0)
                    hielo = max(jugador.hielo_ms, 2200 if evol else 1400)
                    for i in range(perdigones):
                        a = base_ang + (i - (perdigones - 1) / 2) * 0.13
                        proyectiles.append(
                            jugador.crear_bala(math.cos(a), math.sin(a), danio_esc, perf_esc, hielo, evol)
                        )
                    self.timers["escopeta"] = 850 if evol else max(950, 1500 - 110 * nv_esc)
                    snd.play("disparo")

    def posiciones_orbitales(self, jugador):
        nv_orb = self.nivel_de("orbital")
        if nv_orb <= 0:
            return []
        evol = nv_orb >= 5
        cantidad = 6 if evol else (1 + nv_orb)
        dist = 66 if evol else (48 + nv_orb * 3)
        r_orbe = 9 if evol else 6
        res = []
        for i in range(cantidad):
            a = self.angulo_orbita + i * (math.tau / cantidad)
            res.append((jugador.x + math.cos(a) * dist, jugador.y + math.sin(a) * dist, r_orbe))
        return res

    def dibujar(self, pantalla, jugador):
        nv_orb = self.nivel_de("orbital")
        if nv_orb > 0:
            evol = nv_orb >= 5
            col = (255, 195, 75) if evol else (90, 235, 255)
            for ox, oy, r in self.posiciones_orbitales(jugador):
                pygame.draw.circle(pantalla, col, (int(ox), int(oy)), r)
                pygame.draw.circle(pantalla, (255, 255, 255), (int(ox), int(oy)), max(2, r - 4))