import csv
import math
import os
import random
import pygame
from settings import ANCHO, ALTO, FPS, FONDO, COLUMNAS, FILAS, TAM
from mapa import Mapa
from jugador import Jugador
from enemigo import Enemigo, TIPOS, ESTAD
from jefe import Jefe
from gema import Gema
from mejoras import MEJORAS, mejoras_disponibles, texto_carta
from armas import CATALOGO_ARMAS
from sonido import Sonidos
from efectos import TextoFlotante, crear_explosion
from ia.recomendador import Recomendador, obtener_contexto
from ia.genetico import Poblacion
from ia.cerebro import Cerebro
from busqueda.astar import DIRS

VALOR_XP = {"horda": 1, "corredor": 1, "tonto": 2, "elite": 5, "jefe": 15}
VENTANA = 15000
OLA_MS = 40000
JEFE_CADA = 3
TEXTO = (238, 242, 250)
GRIS = (145, 158, 182)
MORADO = (204, 108, 255)
VERDE = (92, 228, 145)
ROJO = (242, 72, 82)
CIAN = (74, 225, 255)
DORADO = (255, 208, 84)
BASE = os.path.dirname(os.path.abspath(__file__))
RUTA_SESIONES = os.path.join(BASE, "ia", "sesiones.csv")
CARPETA_CAPTURAS = os.path.join(BASE, "capturas")


class Partida:
    def __init__(self, cerebro):
        self.cerebro = cerebro
        self.cerebro.reiniciar_estado()
        for v in ESTAD.values():
            v.update(busquedas=0, nodos=0, costo=0)
        self.mapa = Mapa()
        self.mapa.generar_obstaculos(18, origen=(15, 10))
        self.mapa.generar_lodo(7)
        self.jugador = Jugador(15, 10)
        self.enemigos, self.proyectiles, self.gemas = [], [], []
        self.spawns, self.ondas = [], []
        self.particulas, self.textos = [], []
        self.shake_ms = 0
        self.dano_flash_ms = 0
        self.bajas = 0
        self.tiempo = 0
        self.opciones = []
        self.ctx_oferta = "normal"
        self.recomendada = None
        self.explora = False
        self.pendiente = None
        self.pob = Poblacion()
        self.ola = 0
        self.intermedio = None
        self.guardada = False
        self.iniciar_ola()

    def iniciar_ola(self):
        self.ola += 1
        self.t_ola = 0
        self.total_ola = min(90, max(len(self.pob.genomas), 20 + 8 * self.ola))
        self.creados = 0
        self.aparicion = 0
        self.intervalo = OLA_MS * 0.6 / self.total_ola
        self.jefe_pendiente = self.ola % JEFE_CADA == 0
        self.spawns.clear()
        self.cerebro.reiniciar_estado()


def punto_de_aparicion(mapa, jugador):
    candidatas = [
        (cx, cy) for (cx, cy) in mapa.dist
        if math.hypot(cx * TAM + TAM / 2 - jugador.x, cy * TAM + TAM / 2 - jugador.y) > 300
    ]
    if candidatas:
        cx, cy = random.choice(candidatas)
        return cx * TAM + TAM / 2, cy * TAM + TAM / 2
    while True:
        cx, cy = random.randint(1, COLUMNAS - 2), random.randint(1, FILAS - 2)
        px, py = cx * TAM + TAM / 2, cy * TAM + TAM / 2
        if mapa.celdas[cy][cx] == 0 and math.hypot(px - jugador.x, py - jugador.y) > 300:
            return px, py


def separar(enemigos, mapa):
    for i, a in enumerate(enemigos):
        for b in enemigos[i + 1:]:
            dx, dy = b.x - a.x, b.y - a.y
            d2 = dx * dx + dy * dy
            m = a.radio + b.radio
            if 0 < d2 < m * m:
                d = math.sqrt(d2)
                push = (m - d) / 2
                ux, uy = dx / d, dy / d
                for e, s in ((a, -1), (b, 1)):
                    nx, ny = e.x + ux * push * s, e.y + uy * push * s
                    if not mapa.choca(nx, e.y, e.radio):
                        e.x = nx
                    if not mapa.choca(e.x, ny, e.radio):
                        e.y = ny


def cerrar_pendiente(p, rec):
    if not p.pendiente:
        return
    pen = p.pendiente
    seg = max(1, (p.tiempo - pen["t0"]) / 1000)
    perdida = max(0, pen["vida"] - p.jugador.vida)
    recompensa = ((p.bajas - pen["bajas"]) - perdida / 5) / seg * 15
    rec.aprender(pen["mejora"], recompensa, pen["ctx"])
    p.pendiente = None


def ofrecer(p, rec, snd):
    j = p.jugador
    j.xp -= j.xp_sig
    j.nivel += 1
    cerrar_pendiente(p, rec)
    p.ctx_oferta = obtener_contexto(j, len(p.enemigos))
    pool = mejoras_disponibles(j)
    p.opciones = random.sample(pool, min(3, len(pool)))
    p.recomendada, p.explora = rec.recomendar(p.opciones, p.ctx_oferta)
    snd.play("nivel")


def elegir(p, i):
    m = p.opciones[i]
    MEJORAS[m][1](p.jugador)
    if m == "vida":
        p.textos.append(TextoFlotante(p.jugador.x, p.jugador.y - 10, "+25", VERDE))
    elif m == "escudo":
        p.textos.append(TextoFlotante(p.jugador.x, p.jugador.y - 10, "ESCUDO", CIAN))
    elif m.startswith("arma_"):
        arma = m.split("_", 1)[1]
        if p.jugador.arsenal.evolucionada(arma):
            p.textos.append(TextoFlotante(p.jugador.x, p.jugador.y - 14, "¡EVOLUCIÓN!", DORADO))
    p.pendiente = dict(mejora=m, t0=p.tiempo, bajas=p.bajas, vida=p.jugador.vida, ctx=p.ctx_oferta)
    p.opciones = []


def terminar_ola(p, snd):
    for e in p.enemigos:
        p.pob.registrar(e.genoma, e.fitness())
    p.enemigos, p.proyectiles, p.spawns, p.ondas = [], [], [], []
    p.intermedio = p.pob.evolucionar(p.ola)
    j = p.jugador
    j.vida = min(j.vida_max, j.vida + 0.3 * j.vida_max)
    p.cerebro.repasar()
    p.cerebro.guardar()
    snd.play("ola")


def siguiente_ola(p):
    p.intermedio = None
    p.iniciar_ola()


def guardar_sesion(p):
    if p.guardada:
        return
    p.guardada = True
    c = p.cerebro
    nuevo = not os.path.exists(RUTA_SESIONES)
    with open(RUTA_SESIONES, "a", newline="") as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(["partida", "olas", "bajas", "tiempo_s", "nivel", "error_red", "error_base"])
        w.writerow([p.pob.partida, p.ola, p.bajas, p.tiempo // 1000, p.jugador.nivel,
                    round(c.err_nn, 2), round(c.err_base, 2)])


def captura(pantalla):
    os.makedirs(CARPETA_CAPTURAS, exist_ok=True)
    n = len(os.listdir(CARPETA_CAPTURAS)) + 1
    pygame.image.save(pantalla, os.path.join(CARPETA_CAPTURAS, f"captura_{n:02d}.png"))


def _danar_enemigo(p, e, danio, hielo_ms, snd):
    if not e.viva:
        return
    e.vida -= danio
    e.flash = 80
    if hielo_ms > 0:
        e.lento_ms = max(e.lento_ms, hielo_ms)
    p.textos.append(TextoFlotante(e.x, e.y - e.radio, f"-{danio}"))
    if e.vida <= 0:
        e.viva = False
        p.bajas += 1
        cant = 24 if e.tipo == "jefe" else 9
        crear_explosion(p.particulas, e.x, e.y, e.color, cant)
        p.gemas.append(Gema(e.x, e.y, VALOR_XP[e.tipo]))
        p.pob.registrar(e.genoma, e.fitness())
        snd.play("muerte")


def actualizar(p, dt, teclas, rec, snd):
    j = p.jugador
    if j.vida <= 0 or p.opciones or p.intermedio:
        return
    p.tiempo += dt
    p.t_ola += dt
    p.shake_ms = max(0, p.shake_ms - dt)
    p.dano_flash_ms = max(0, p.dano_flash_ms - dt)

    if p.pendiente and p.tiempo - p.pendiente["t0"] >= VENTANA:
        cerrar_pendiente(p, rec)

    j.actualizar_escudo(dt)
    j.mover(teclas, p.mapa, dt)
    j.disparar(p.enemigos, p.proyectiles, p.ondas, dt, snd)

    # Procesar impactos de Orbes Orbitales y Nova Eléctrica
    while j._cola_impactos:
        enem, d_imp, h_imp = j._cola_impactos.pop(0)
        _danar_enemigo(p, enem, d_imp, h_imp, snd)

    p.cerebro.observar(j, dt, p.mapa)

    if p.mapa.flujo_meta != j.celda:
        p.mapa.calcular_flujo(j.celda)
        ESTAD["horda"]["busquedas"] += 1
        ESTAD["horda"]["nodos"] += len(p.mapa.dist)

    p.aparicion -= dt
    if p.aparicion <= 0 and p.creados < p.total_ola:
        genoma = p.pob.genomas[p.creados % len(p.pob.genomas)]
        sx, sy = punto_de_aparicion(p.mapa, j)
        p.spawns.append([sx, sy, 900, genoma])
        p.creados += 1
        p.aparicion = p.intervalo

    if p.jefe_pendiente:
        sx, sy = punto_de_aparicion(p.mapa, j)
        p.spawns.append([sx, sy, 1200, None])
        p.jefe_pendiente = False
        snd.play("jefe")

    pendientes_spawn = []
    for sp in p.spawns:
        sp[2] -= dt
        if sp[2] <= 0:
            if sp[3] is None:
                p.enemigos.append(Jefe(sp[0], sp[1], p.ola, p.cerebro))
            else:
                p.enemigos.append(Enemigo(sp[0], sp[1], sp[3], p.ola))
        else:
            pendientes_spawn.append(sp)
    p.spawns = pendientes_spawn

    for e in p.enemigos:
        e.mover(p.mapa, j, dt)
        if e.toca(j) and e.espera_golpe <= 0:
            e.espera_golpe = 600
            if j.escudo_activo:
                j.escudo_activo = False
                j.escudo_cd = j.escudo_recarga
                p.shake_ms = 70
                crear_explosion(p.particulas, j.x, j.y, CIAN, 14)
                p.textos.append(TextoFlotante(j.x, j.y - 12, "BLOQUEADO", CIAN))
                snd.play("gema")
            else:
                j.vida -= e.danio
                e.danio_hecho += e.danio
                p.shake_ms = 140
                p.dano_flash_ms = 180
                p.textos.append(TextoFlotante(j.x, j.y - 12, f"-{e.danio}", ROJO))
                snd.play("golpe")
    separar(p.enemigos, p.mapa)

    for pr in p.proyectiles:
        pr.mover(p.mapa, dt)
        if not pr.viva:
            continue
        for e in p.enemigos:
            if e.viva and id(e) not in pr.golpeados and math.hypot(pr.x - e.x, pr.y - e.y) < pr.radio + e.radio:
                pr.golpeados.add(id(e))
                _danar_enemigo(p, e, pr.danio, pr.hielo_ms, snd)
                if pr.perforacion > 0:
                    pr.perforacion -= 1
                else:
                    pr.viva = False
                    break

    for g in p.gemas:
        if g.actualizar(j, dt):
            j.xp += g.valor
            g.valor = 0
            snd.play("gema")

    p.ondas = [o for o in p.ondas if o.actualizar(dt)]
    p.particulas = [pt for pt in p.particulas if pt.actualizar(dt)]
    p.textos = [tx for tx in p.textos if tx.actualizar(dt)]
    p.gemas = [g for g in p.gemas if g.valor > 0]
    p.enemigos = [e for e in p.enemigos if e.viva]
    p.proyectiles = [x for x in p.proyectiles if x.viva]

    fin_ola_tiempo = p.t_ola >= OLA_MS
    sin_jefe = not any(e.tipo == "jefe" for e in p.enemigos) and not any(sp[3] is None for sp in p.spawns)
    if j.vida <= 0:
        cerrar_pendiente(p, rec)
        p.cerebro.guardar()
        guardar_sesion(p)
        snd.play("fin")
    elif fin_ola_tiempo and sin_jefe:
        terminar_ola(p, snd)
    elif j.xp >= j.xp_sig:
        ofrecer(p, rec, snd)


def dibujar_spawns(pantalla, spawns):
    for sx, sy, ms, genoma in spawns:
        col = MORADO if genoma is None else TIPOS[genoma.tipo]["color"]
        r = max(4, int(18 * (ms / 900)))
        pygame.draw.circle(pantalla, col, (int(sx), int(sy)), r, 2)
        pygame.draw.circle(pantalla, col, (int(sx), int(sy)), 3)


def dibujar_flujo(pantalla, mapa):
    for (cx, cy), d in mapa.dist.items():
        if d == 0:
            continue
        mejor = min(((cx + dx, cy + dy) for dx, dy in DIRS), key=lambda v: mapa.dist.get(v, 9999))
        a = (cx * TAM + TAM // 2, cy * TAM + TAM // 2)
        b = (mejor[0] * TAM + TAM // 2, mejor[1] * TAM + TAM // 2)
        pygame.draw.line(pantalla, (50, 95, 75), a, (a[0] + (b[0] - a[0]) * .4, a[1] + (b[1] - a[1]) * .4), 2)


def velo(pantalla, alfa=215):
    v = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
    v.fill((10, 12, 18, alfa))
    pantalla.blit(v, (0, 0))


def texto_centrado(pantalla, fuente, txt, y, color=TEXTO):
    t = fuente.render(txt, True, color)
    pantalla.blit(t, (ANCHO // 2 - t.get_width() // 2, y))


def dibujar_menu(pantalla, fuente, grande, titulo, t_ms):
    velo(pantalla, 215)
    # Marco neón estilo Swarm
    panel = pygame.Rect(ANCHO // 2 - 420, 48, 840, 560)
    pygame.draw.rect(pantalla, (18, 22, 32), panel, border_radius=14)
    pygame.draw.rect(pantalla, (64, 195, 240), panel, 2, border_radius=14)

    texto_centrado(pantalla, titulo, "ZOMBIE SURVIVAL: SWARM IA", 76, CIAN)
    texto_centrado(pantalla, fuente, "Supervivencia Bullet-Heaven impulsada por 7 motores de Inteligencia Artificial", 122, DORADO)

    lineas = [
        ("Horda (BFS)",       "Campo de flujo compartido: persecución coordinada en masa", TIPOS["horda"]["color"]),
        ("Corredores (Voraz)","Asalto rápido directo: caen en trampas de bio-ácido", TIPOS["corredor"]["color"]),
        ("Tontos (DFS)",      "Exploración errática en profundidad", TIPOS["tonto"]["color"]),
        ("Élites (A*)",       "Navegación óptima rodeando terrenos tóxicos", TIPOS["elite"]["color"]),
        ("Jefe (Red 8-10-2)", "Red neuronal en vivo: predice tu ruta y te corta el paso", MORADO),
        ("Genético",          "Evolución entre olas: muta velocidad, vida, daño y clases", TEXTO),
        ("RL Contextual",     "Bandido contextual: adapta tus cartas de armas y mejoras", VERDE),
    ]
    y = 175
    for nombre, desc, col in lineas:
        pygame.draw.circle(pantalla, col, (ANCHO // 2 - 365, y + 8), 5)
        pantalla.blit(fuente.render(nombre, True, col), (ANCHO // 2 - 350, y))
        pantalla.blit(fuente.render(desc, True, GRIS), (ANCHO // 2 - 175, y))
        y += 30

    pygame.draw.line(pantalla, (45, 55, 75), (ANCHO // 2 - 370, 405), (ANCHO // 2 + 370, 405), 1)
    texto_centrado(pantalla, fuente, "Acumula hasta 4 armas simultáneas y súbelas a Nv.5 para EVOLUCIONARLAS", 422, DORADO)
    texto_centrado(pantalla, fuente, "WASD / Flechas: Mover   |   P: Ver IA   |   TAB: Paneles   |   M: Audio   |   F12: Captura", 454, TEXTO)

    pulso = VERDE if (t_ms // 450) % 2 == 0 else CIAN
    texto_centrado(pantalla, titulo, "[ PRESIONA ENTER PARA INICIAR ]", 520, pulso)


def dibujar_pausa(pantalla, fuente, grande):
    velo(pantalla, 190)
    texto_centrado(pantalla, grande, "PAUSA", 240, CIAN)
    texto_centrado(pantalla, fuente, "ESC para continuar   |   M: sonido   |   F12: captura", 300, GRIS)


def dibujar_fin(pantalla, p, fuente, grande):
    velo(pantalla, 215)
    texto_centrado(pantalla, grande, "OPERACIÓN FALLIDA", 150, ROJO)
    c = p.cerebro
    datos = [
        f"Sobreviviste hasta la ola {p.ola}  (Nivel {p.jugador.nivel})",
        f"Bajas totales: {p.bajas}     Tiempo: {p.tiempo // 60000}:{(p.tiempo // 1000) % 60:02d}",
        f"Generaciones evolucionadas: {p.pob.generacion - 1}",
        f"Red del jefe: error {c.err_nn:.2f} casillas (base {c.err_base:.2f}), {c.muestras} muestras",
    ]
    for i, d in enumerate(datos):
        texto_centrado(pantalla, fuente, d, 230 + i * 28)
    texto_centrado(pantalla, fuente, "Resultados guardados en ia/sesiones.csv", 360, GRIS)
    texto_centrado(pantalla, grande, "R para volver a desplegar", 420, VERDE)


def rects_cartas():
    x0, y = (ANCHO - 960) // 2, ALTO // 2 - 105
    return [pygame.Rect(x0 + i * 330, y, 300, 210) for i in range(3)]


def dibujar_cartas(pantalla, p, rec, fuente, grande):
    velo(pantalla)
    texto_centrado(pantalla, grande, f"¡NIVEL {p.jugador.nivel}!  Elige mejora o arma", 90, CIAN)
    texto_centrado(pantalla, fuente, f"Estado táctico detectado: {p.ctx_oferta.upper()}", 140, DORADO)
    q_ctx = rec.q[p.ctx_oferta]
    n_ctx = rec.n[p.ctx_oferta]
    for i, (r, m) in enumerate(zip(rects_cartas(), p.opciones)):
        es_rec = m == p.recomendada
        es_arma = m.startswith("arma_")
        borde = VERDE if es_rec else (DORADO if es_arma else (70, 82, 105))
        pygame.draw.rect(pantalla, (22, 27, 38), r, border_radius=10)
        pygame.draw.rect(pantalla, borde, r, 3, border_radius=10)

        titulo_c, desc_c = texto_carta(m, p.jugador)
        pantalla.blit(grande.render(str(i + 1), True, borde), (r.x + 14, r.y + 8))
        pantalla.blit(fuente.render(titulo_c, True, DORADO if es_arma else TEXTO), (r.x + 14, r.y + 62))
        pantalla.blit(fuente.render(desc_c[:36], True, GRIS), (r.x + 14, r.y + 92))
        if len(desc_c) > 36:
            pantalla.blit(fuente.render(desc_c[36:], True, GRIS), (r.x + 14, r.y + 112))

        if es_rec:
            txt, col = ("PRUEBA (exploración)", (255, 148, 56)) if p.explora else ("RECOMENDADA POR IA", VERDE)
            pantalla.blit(fuente.render(txt, True, col), (r.x + 14, r.y + 145))
        pantalla.blit(fuente.render(f"Q[{p.ctx_oferta}] = {q_ctx[m]:.1f}  (n={n_ctx[m]})", True, GRIS), (r.x + 14, r.y + 175))


def fila_tipos(pantalla, fuente, titulo, conteo, x, y):
    pantalla.blit(fuente.render(titulo, True, GRIS), (x, y))
    x += 150
    for t, cfg in TIPOS.items():
        pantalla.blit(fuente.render(f"{cfg['alg']} x{conteo[t]}", True, cfg["color"]), (x, y))
        x += 95


def dibujar_intermedio(pantalla, p, fuente, grande):
    s = p.intermedio
    velo(pantalla)
    cx = ANCHO // 2
    texto_centrado(pantalla, grande, f"OLA {p.ola} COMPLETADA", 70, VERDE)
    pantalla.blit(fuente.render(
        f"Generación {s['generacion']}   aptitud media {s['media']:.1f}   mejor {s['maxima']:.1f}",
        True, TEXTO), (cx - 280, 140))
    fila_tipos(pantalla, fuente, "Jugaron:", s, cx - 280, 175)
    fila_tipos(pantalla, fuente, "Evolucionan a:", p.pob.conteo(), cx - 280, 200)
    pantalla.blit(fuente.render(
        f"Genes medios  vel {s['vel']:.2f}  vida {s['vida']:.2f}  daño {s['danio']:.2f}   (presupuesto 3.0)",
        True, GRIS), (cx - 280, 230))
    c = p.cerebro
    pantalla.blit(fuente.render(
        f"Red del jefe: error {c.err_nn:.2f} casillas  (base {c.err_base:.2f})  muestras {c.muestras}",
        True, MORADO), (cx - 280, 250))

    gx, gy, gw, gh = cx - 280, 280, 560, 180
    pygame.draw.rect(pantalla, (18, 22, 32), (gx, gy, gw, gh))
    pygame.draw.rect(pantalla, (70, 82, 105), (gx, gy, gw, gh), 2)
    vals = [h["media"] for h in p.pob.historial]
    tope = max(vals) or 1
    pts = [(gx + 20 + i * (gw - 40) / max(1, len(vals) - 1), gy + gh - 20 - (v / tope) * (gh - 50))
           for i, v in enumerate(vals)]
    if len(pts) > 1:
        pygame.draw.lines(pantalla, VERDE, False, pts, 3)
    for pt in pts:
        pygame.draw.circle(pantalla, VERDE, pt, 4)
    pantalla.blit(fuente.render("Aptitud media por generación", True, GRIS), (gx + 10, gy + 8))
    texto_centrado(pantalla, fuente, "ESPACIO para la siguiente ola", 490, CIAN)


def dibujar_arsenal_hud(pantalla, jugador, fuente_chica):
    """Muestra las armas activas y su nivel/evolución arriba a la izquierda."""
    x, y = 10, 72
    for clave, nv in jugador.arsenal.niveles.items():
        cfg = CATALOGO_ARMAS[clave]
        evol = nv >= 5
        nombre = cfg["evol"] if evol else f"{cfg['nombre']} Nv.{nv}"
        col = DORADO if evol else cfg["color"]
        caja = pygame.Rect(x, y, 185, 22)
        pygame.draw.rect(pantalla, (18, 22, 32), caja, border_radius=5)
        pygame.draw.rect(pantalla, col, caja, 1, border_radius=5)
        pantalla.blit(fuente_chica.render(nombre, True, col), (x + 7, y + 4))
        y += 26
    return y + 6


def dibujar_paneles(pantalla, p, rec, fuente, y_izq):
    y = y_izq
    for tipo, cfg in TIPOS.items():
        s = ESTAD[tipo]
        prom = s["nodos"] / s["busquedas"] if s["busquedas"] else 0
        costo = s["costo"] / s["busquedas"] if s["busquedas"] and tipo != "horda" else 0
        vivos = sum(1 for e in p.enemigos if e.tipo == tipo)
        linea = f"{cfg['alg']:<5} x{vivos:<3} {prom:>5.0f} nodos  costo {costo:>5.1f}"
        pantalla.blit(fuente.render(linea, True, cfg["color"]), (10, y))
        y += 18

    x = ANCHO - 305
    ctx = obtener_contexto(p.jugador, len(p.enemigos))
    q_ctx = rec.q[ctx]
    n_ctx = rec.n[ctx]
    pantalla.blit(fuente.render(f"Recomendador [{ctx}]", True, CIAN), (x, 10))
    for i, m in enumerate(sorted(q_ctx, key=q_ctx.get, reverse=True)):
        etiqueta = m.replace("arma_", "*").upper() if m.startswith("arma_") else m
        pantalla.blit(fuente.render(f"{etiqueta:<12} {q_ctx[m]:>6.1f} n={n_ctx[m]}", True, GRIS), (x, 30 + i * 16))

    y_gen = 30 + len(q_ctx) * 16 + 10
    pantalla.blit(fuente.render(f"Genética: generación {p.pob.generacion}", True, CIAN), (x, y_gen))
    conteo = p.pob.conteo()
    for i, (t, cfg) in enumerate(TIPOS.items()):
        pantalla.blit(fuente.render(f"{cfg['alg']:<5} {conteo[t]:>2} genomas", True, cfg["color"]), (x, y_gen + 20 + i * 16))
    if p.pob.historial:
        pantalla.blit(fuente.render(f"aptitud media {p.pob.historial[-1]['media']:.1f}", True, GRIS), (x, y_gen + 86))

    y_nn = y_gen + 108
    c = p.cerebro
    pantalla.blit(fuente.render("Red neuronal jefe (8-10-2)", True, CIAN), (x, y_nn))
    pantalla.blit(fuente.render(f"error red   {c.err_nn:.2f} casillas", True, MORADO), (x, y_nn + 18))
    pantalla.blit(fuente.render(f"error base  {c.err_base:.2f} (quieto)", True, GRIS), (x, y_nn + 35))
    pantalla.blit(fuente.render(f"muestras {c.muestras}", True, GRIS), (x, y_nn + 52))


def main():
    pygame.init()
    pantalla = pygame.display.set_mode((ANCHO, ALTO))
    escena = pygame.Surface((ANCHO, ALTO))
    pygame.display.set_caption("Zombie Survival: Swarm IA")
    reloj = pygame.time.Clock()
    fuente = pygame.font.SysFont("consolas", 15)
    fuente_chica = pygame.font.SysFont("consolas", 13, bold=True)
    grande = pygame.font.SysFont("consolas", 34, bold=True)

    snd = Sonidos()
    rec = Recomendador(MEJORAS.keys())
    cerebro = Cerebro()
    p = Partida(cerebro)
    estado = "menu"
    debug = False
    paneles = True

    corriendo = True
    while corriendo:
        dt = reloj.tick(FPS)
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                cerebro.guardar()
                corriendo = False
            if ev.type == pygame.KEYDOWN:
                k = ev.key
                if k == pygame.K_m:
                    snd.activo = not snd.activo
                elif k == pygame.K_F12:
                    captura(pantalla)
                elif k == pygame.K_TAB:
                    paneles = not paneles
                elif k == pygame.K_p:
                    debug = not debug
                if estado == "menu":
                    if k == pygame.K_RETURN:
                        estado = "juego"
                    elif k == pygame.K_ESCAPE:
                        cerebro.guardar()
                        corriendo = False
                elif estado == "juego":
                    if k == pygame.K_ESCAPE and not p.opciones and not p.intermedio and p.jugador.vida > 0:
                        estado = "pausa"
                    elif k == pygame.K_r and p.jugador.vida <= 0:
                        p = Partida(cerebro)
                    elif k == pygame.K_SPACE and p.intermedio:
                        siguiente_ola(p)
                    elif p.opciones and k in (pygame.K_1, pygame.K_2, pygame.K_3):
                        elegir(p, k - pygame.K_1)
                elif estado == "pausa" and k == pygame.K_ESCAPE:
                    estado = "juego"
            if ev.type == pygame.MOUSEBUTTONDOWN and estado == "juego" and p.opciones:
                for i, r in enumerate(rects_cartas()):
                    if r.collidepoint(ev.pos):
                        elegir(p, i)
                        break

        if estado == "juego":
            actualizar(p, dt, pygame.key.get_pressed(), rec, snd)

        escena.fill(FONDO)
        p.mapa.dibujar(escena)
        if debug:
            dibujar_flujo(escena, p.mapa)
        dibujar_spawns(escena, p.spawns)
        for o in p.ondas:
            o.dibujar(escena)
        for g in p.gemas:
            g.dibujar(escena)
        for pt in p.particulas:
            pt.dibujar(escena)
        for e in p.enemigos:
            e.dibujar(escena, debug)
        for pr in p.proyectiles:
            pr.dibujar(escena)
        p.jugador.dibujar(escena)
        for tx in p.textos:
            tx.dibujar(escena, fuente_chica)

        ox = random.randint(-4, 4) if p.shake_ms > 0 else 0
        oy = random.randint(-4, 4) if p.shake_ms > 0 else 0
        pantalla.fill(FONDO)
        pantalla.blit(escena, (ox, oy))

        if p.dano_flash_ms > 0:
            alfa = int(110 * p.dano_flash_ms / 180)
            borde = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
            pygame.draw.rect(borde, (242, 65, 75, alfa), (0, 0, ANCHO, ALTO), 14)
            pantalla.blit(borde, (0, 0))

        j = p.jugador
        pygame.draw.rect(pantalla, (45, 18, 26), (10, 10, 210, 14), border_radius=4)
        pygame.draw.rect(pantalla, VERDE, (10, 10, max(0, 210 * j.vida / j.vida_max), 14), border_radius=4)
        pantalla.blit(fuente_chica.render(f"{max(0, int(j.vida))}/{j.vida_max}", True, TEXTO), (228, 10))
        pygame.draw.rect(pantalla, (18, 25, 38), (0, ALTO - 8, ANCHO, 8))
        pygame.draw.rect(pantalla, CIAN, (0, ALTO - 8, ANCHO * j.xp / j.xp_sig, 8))

        restante = max(0, (OLA_MS - p.t_ola) // 1000)
        info = (f"Ola {p.ola} ({restante}s)  Nivel {j.nivel}  Bajas {p.bajas}  "
                f"Enemigos {len(p.enemigos)}  FPS {reloj.get_fps():.0f}"
                f"{'' if snd.activo else '  [sin sonido]'}")
        pantalla.blit(fuente.render(info, True, TEXTO), (10, 30))

        esc_txt = ""
        if j.escudo_recarga > 0:
            esc_txt = " | Escudo: LISTO" if j.escudo_activo else f" | Escudo: {j.escudo_cd / 1000:.1f}s"
        stats_arma = f"Daño +{j.danio} | Vel {int(j.vel)}{esc_txt}"
        pantalla.blit(fuente_chica.render(stats_arma, True, GRIS), (10, 49))

        y_despues_armas = dibujar_arsenal_hud(pantalla, j, fuente_chica)
        if paneles:
            dibujar_paneles(pantalla, p, rec, fuente, y_despues_armas)

        if estado == "menu":
            dibujar_menu(pantalla, fuente, grande, grande, pygame.time.get_ticks())
        elif estado == "pausa":
            dibujar_pausa(pantalla, fuente, grande)
        elif p.opciones:
            dibujar_cartas(pantalla, p, rec, fuente, grande)
        elif p.intermedio:
            dibujar_intermedio(pantalla, p, fuente, grande)
        elif j.vida <= 0:
            dibujar_fin(pantalla, p, fuente, grande)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()