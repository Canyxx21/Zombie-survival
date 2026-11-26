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
from mejoras import MEJORAS
from sonido import Sonidos
from ia.recomendador import Recomendador
from ia.genetico import Poblacion
from ia.cerebro import Cerebro
from busqueda.astar import DIRS

VALOR_XP = {"horda": 1, "corredor": 1, "tonto": 2, "elite": 5, "jefe": 15}
VENTANA = 15000      # ms que se observan los resultados de una mejora
OLA_MS = 40000       # duración de cada ola
JEFE_CADA = 3        # un jefe cada 3 olas (ponlo en 1 para probarlo ya)
TEXTO = (233, 226, 214)
GRIS = (150, 142, 130)
MORADO = (182, 95, 209)
VERDE = (156, 207, 90)
BASE = os.path.dirname(os.path.abspath(__file__))
RUTA_SESIONES = os.path.join(BASE, "ia", "sesiones.csv")
CARPETA_CAPTURAS = os.path.join(BASE, "capturas")


class Partida:
    def __init__(self, cerebro):
        self.cerebro = cerebro
        for v in ESTAD.values():
            v.update(busquedas=0, nodos=0, costo=0)
        self.mapa = Mapa()
        self.mapa.generar_obstaculos(18)
        self.mapa.generar_lodo(7)
        self.jugador = Jugador(15, 10)
        self.enemigos, self.proyectiles, self.gemas = [], [], []
        self.bajas = 0
        self.tiempo = 0
        self.opciones = []        # si hay opciones, el juego está en pausa
        self.recomendada = None
        self.explora = False
        self.pendiente = None
        self.pob = Poblacion()
        self.ola = 0
        self.intermedio = None    # estadísticas de la ola, mientras se muestra el resumen
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


def punto_de_aparicion(mapa, jugador):
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

# ---------- aprendizaje por refuerzo ----------
def cerrar_pendiente(p, rec):
    """Calcula la recompensa de la última mejora elegida y se la pasa al recomendador."""
    if not p.pendiente:
        return
    pen = p.pendiente
    seg = max(1, (p.tiempo - pen["t0"]) / 1000)
    perdida = max(0, pen["vida"] - p.jugador.vida)
    recompensa = ((p.bajas - pen["bajas"]) - perdida / 5) / seg * 15
    rec.aprender(pen["mejora"], recompensa)
    p.pendiente = None

def ofrecer(p, rec, snd):
    j = p.jugador
    j.xp -= j.xp_sig
    j.nivel += 1
    cerrar_pendiente(p, rec)
    p.opciones = random.sample(list(MEJORAS), 3)
    p.recomendada, p.explora = rec.recomendar(p.opciones)
    snd.play("nivel")

def elegir(p, i):
    m = p.opciones[i]
    MEJORAS[m][1](p.jugador)
    p.pendiente = dict(mejora=m, t0=p.tiempo, bajas=p.bajas, vida=p.jugador.vida)
    p.opciones = []

# ---------- algoritmo genético ----------
def terminar_ola(p, snd):
    for e in p.enemigos:                       # los sobrevivientes también cuentan
        p.pob.registrar(e.genoma, e.fitness())
    p.enemigos, p.proyectiles = [], []
    p.intermedio = p.pob.evolucionar(p.ola)
    j = p.jugador
    j.vida = min(j.vida_max, j.vida + 0.3 * j.vida_max)
    p.cerebro.repasar()
    p.cerebro.guardar()
    snd.play("ola")

def siguiente_ola(p):
    p.intermedio = None
    p.iniciar_ola()

# ---------- resultados para el reporte ----------
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

# ---------- lógica ----------
def actualizar(p, dt, teclas, rec, snd):
    j = p.jugador
    if j.vida <= 0 or p.opciones or p.intermedio:
        return
    p.tiempo += dt
    p.t_ola += dt
    if p.pendiente and p.tiempo - p.pendiente["t0"] >= VENTANA:
        cerrar_pendiente(p, rec)

    j.mover(teclas, p.mapa, dt)
    antes = len(p.proyectiles)
    j.disparar(p.enemigos, p.proyectiles, dt)
    if len(p.proyectiles) > antes:
        snd.play("disparo")
    p.cerebro.observar(j, dt)                        # la red del jefe aprende de ti

    if p.mapa.flujo_meta != j.celda:                 # un BFS para toda la horda
        p.mapa.calcular_flujo(j.celda)
        ESTAD["horda"]["busquedas"] += 1
        ESTAD["horda"]["nodos"] += len(p.mapa.dist)

    p.aparicion -= dt
    if p.aparicion <= 0 and p.creados < p.total_ola:
        genoma = p.pob.genomas[p.creados % len(p.pob.genomas)]
        p.enemigos.append(Enemigo(*punto_de_aparicion(p.mapa, j), genoma, p.ola))
        p.creados += 1
        p.aparicion = p.intervalo

    if p.jefe_pendiente:
        p.enemigos.append(Jefe(*punto_de_aparicion(p.mapa, j), p.ola, p.cerebro))
        p.jefe_pendiente = False
        snd.play("jefe")

    for e in p.enemigos:
        e.mover(p.mapa, j, dt)
        if e.toca(j) and e.espera_golpe <= 0:
            j.vida -= e.danio
            e.danio_hecho += e.danio
            e.espera_golpe = 600
            snd.play("golpe")
    separar(p.enemigos, p.mapa)

    for pr in p.proyectiles:
        pr.mover(p.mapa, dt)
        for e in p.enemigos:
            if e.viva and math.hypot(pr.x - e.x, pr.y - e.y) < pr.radio + e.radio:
                e.vida -= pr.danio
                pr.viva = False
                if e.vida <= 0:
                    e.viva = False
                    p.bajas += 1
                    p.gemas.append(Gema(e.x, e.y, VALOR_XP[e.tipo]))
                    p.pob.registrar(e.genoma, e.fitness())
                    snd.play("muerte")
                break

    for g in p.gemas:
        if g.actualizar(j, dt):
            j.xp += g.valor
            g.valor = 0
            snd.play("gema")
    p.gemas = [g for g in p.gemas if g.valor > 0]
    p.enemigos = [e for e in p.enemigos if e.viva]
    p.proyectiles = [x for x in p.proyectiles if x.viva]

    if j.vida <= 0:
        cerrar_pendiente(p, rec)
        p.cerebro.guardar()
        guardar_sesion(p)
        snd.play("fin")
    elif p.t_ola >= OLA_MS and not any(e.tipo == "jefe" for e in p.enemigos):
        terminar_ola(p, snd)                         # con jefe vivo, la ola no termina
    elif j.xp >= j.xp_sig:
        ofrecer(p, rec, snd)

# ---------- dibujo ----------
def dibujar_flujo(pantalla, mapa):
    for (cx, cy), d in mapa.dist.items():
        if d == 0:
            continue
        mejor = min(((cx + dx, cy + dy) for dx, dy in DIRS), key=lambda v: mapa.dist.get(v, 9999))
        a = (cx * TAM + TAM // 2, cy * TAM + TAM // 2)
        b = (mejor[0] * TAM + TAM // 2, mejor[1] * TAM + TAM // 2)
        pygame.draw.line(pantalla, (70, 110, 70), a, (a[0] + (b[0] - a[0]) * .4, a[1] + (b[1] - a[1]) * .4), 2)

def velo(pantalla, alfa=215):
    v = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
    v.fill((8, 6, 5, alfa))
    pantalla.blit(v, (0, 0))

def texto_centrado(pantalla, fuente, txt, y, color=TEXTO):
    t = fuente.render(txt, True, color)
    pantalla.blit(t, (ANCHO // 2 - t.get_width() // 2, y))

def dibujar_menu(pantalla, fuente, grande, titulo):
    velo(pantalla, 225)
    texto_centrado(pantalla, titulo, "ZOMBIE SURVIVAL", 70, (200, 55, 45))
    texto_centrado(pantalla, fuente, "La horda inteligente", 120, GRIS)
    lineas = [
        ("Zombis verdes", "BFS con campo de flujo: una sola búsqueda para toda la horda", TIPOS["horda"]["color"]),
        ("Corredores",    "Búsqueda voraz: rápidos pero caen en el lodo", TIPOS["corredor"]["color"]),
        ("Tontos",        "DFS: se pierden por rutas larguísimas", TIPOS["tonto"]["color"]),
        ("Élites",        "A*: la ruta óptima, rodean el lodo", TIPOS["elite"]["color"]),
        ("Jefe",          "Red neuronal 6-8-2: predice a dónde vas e intenta interceptarte", MORADO),
        ("Evolución",     "Algoritmo genético: la horda se adapta ola tras ola", TEXTO),
        ("Mejoras",       "Aprendizaje por refuerzo: el juego aprende cuál te sirve", VERDE),
    ]
    y = 175
    for nombre, desc, col in lineas:
        pantalla.blit(fuente.render(nombre, True, col), (ANCHO // 2 - 330, y))
        pantalla.blit(fuente.render(desc, True, GRIS), (ANCHO // 2 - 190, y))
        y += 26
    texto_centrado(pantalla, fuente, "WASD / flechas: mover    Disparo: automático    ESC: pausa    M: sonido", 400)
    texto_centrado(pantalla, fuente, "P: ver la IA    TAB: ocultar paneles    F12: captura de pantalla", 424)
    texto_centrado(pantalla, titulo, "ENTER para jugar", 490, VERDE)

def dibujar_pausa(pantalla, fuente, grande):
    velo(pantalla, 190)
    texto_centrado(pantalla, grande, "PAUSA", 230)
    texto_centrado(pantalla, fuente, "ESC para continuar    M: sonido    F12: captura", 290, GRIS)

def dibujar_fin(pantalla, p, fuente, grande):
    velo(pantalla, 215)
    texto_centrado(pantalla, grande, "GAME OVER", 150, (200, 55, 45))
    c = p.cerebro
    datos = [
        f"Llegaste a la ola {p.ola}  (nivel {p.jugador.nivel})",
        f"Bajas: {p.bajas}     Tiempo: {p.tiempo // 60000}:{(p.tiempo // 1000) % 60:02d}",
        f"Generaciones de la horda: {p.pob.generacion - 1}",
        f"Red del jefe: error {c.err_nn:.2f} casillas (base {c.err_base:.2f}), {c.muestras} muestras",
    ]
    for i, d in enumerate(datos):
        texto_centrado(pantalla, fuente, d, 230 + i * 26)
    texto_centrado(pantalla, fuente, "Resultados guardados en ia/sesiones.csv", 350, GRIS)
    texto_centrado(pantalla, grande, "R para reiniciar", 410, VERDE)

def rects_cartas():
    x0, y = (ANCHO - 900) // 2, ALTO // 2 - 95
    return [pygame.Rect(x0 + i * 310, y, 280, 190) for i in range(3)]

def dibujar_cartas(pantalla, p, rec, fuente, grande):
    velo(pantalla)
    texto_centrado(pantalla, grande, f"¡Nivel {p.jugador.nivel}!  Elige una mejora", 110)
    for i, (r, m) in enumerate(zip(rects_cartas(), p.opciones)):
        es_rec = m == p.recomendada
        pygame.draw.rect(pantalla, (40, 34, 29), r, border_radius=8)
        pygame.draw.rect(pantalla, VERDE if es_rec else (90, 80, 70), r, 3, border_radius=8)
        pantalla.blit(grande.render(str(i + 1), True, VERDE), (r.x + 14, r.y + 8))
        pantalla.blit(fuente.render(MEJORAS[m][0], True, TEXTO), (r.x + 14, r.y + 70))
        if es_rec:
            txt, col = ("PRUEBA (exploración)", (224, 138, 44)) if p.explora else ("RECOMENDADA", VERDE)
            pantalla.blit(fuente.render(txt, True, col), (r.x + 14, r.y + 110))
        pantalla.blit(fuente.render(f"Q = {rec.q[m]:.1f}   elegida {rec.n[m]} veces", True, GRIS), (r.x + 14, r.y + 150))

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
    texto_centrado(pantalla, grande, f"Ola {p.ola} superada", 70)
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
    pygame.draw.rect(pantalla, (30, 26, 22), (gx, gy, gw, gh))
    pygame.draw.rect(pantalla, (90, 80, 70), (gx, gy, gw, gh), 2)
    vals = [h["media"] for h in p.pob.historial]
    tope = max(vals) or 1
    pts = [(gx + 20 + i * (gw - 40) / max(1, len(vals) - 1), gy + gh - 20 - (v / tope) * (gh - 50))
           for i, v in enumerate(vals)]
    if len(pts) > 1:
        pygame.draw.lines(pantalla, VERDE, False, pts, 3)
    for pt in pts:
        pygame.draw.circle(pantalla, VERDE, pt, 4)
    pantalla.blit(fuente.render("Aptitud media por generación", True, GRIS), (gx + 10, gy + 8))
    texto_centrado(pantalla, fuente, "ESPACIO para la siguiente ola", 490, VERDE)

def dibujar_paneles(pantalla, p, rec, fuente):
    y = 52
    for tipo, cfg in TIPOS.items():
        s = ESTAD[tipo]
        prom = s["nodos"] / s["busquedas"] if s["busquedas"] else 0
        costo = s["costo"] / s["busquedas"] if s["busquedas"] and tipo != "horda" else 0
        vivos = sum(1 for e in p.enemigos if e.tipo == tipo)
        linea = f"{cfg['alg']:<5} x{vivos:<3} {prom:>5.0f} nodos  costo {costo:>5.1f}"
        pantalla.blit(fuente.render(linea, True, cfg["color"]), (10, y))
        y += 18

    x = ANCHO - 290
    pantalla.blit(fuente.render("Recomendador (Q de cada mejora)", True, TEXTO), (x, 10))
    for i, m in enumerate(sorted(rec.q, key=rec.q.get, reverse=True)):
        pantalla.blit(fuente.render(f"{m:<10} {rec.q[m]:>6.1f}  n={rec.n[m]}", True, GRIS), (x, 30 + i * 17))

    pantalla.blit(fuente.render(f"Genética: generación {p.pob.generacion}", True, TEXTO), (x, 160))
    conteo = p.pob.conteo()
    for i, (t, cfg) in enumerate(TIPOS.items()):
        pantalla.blit(fuente.render(f"{cfg['alg']:<5} {conteo[t]:>2} genomas", True, cfg["color"]), (x, 180 + i * 17))
    if p.pob.historial:
        pantalla.blit(fuente.render(f"aptitud media {p.pob.historial[-1]['media']:.1f}", True, GRIS), (x, 252))

    c = p.cerebro
    pantalla.blit(fuente.render("Red neuronal del jefe (6-8-2)", True, TEXTO), (x, 275))
    pantalla.blit(fuente.render(f"error red   {c.err_nn:.2f} casillas", True, MORADO), (x, 293))
    pantalla.blit(fuente.render(f"error base  {c.err_base:.2f} (quedarse quieto)", True, GRIS), (x, 310))
    pantalla.blit(fuente.render(f"muestras {c.muestras}", True, GRIS), (x, 327))

def main():
    pygame.init()
    pantalla = pygame.display.set_mode((ANCHO, ALTO))
    pygame.display.set_caption("Zombie Survival")
    reloj = pygame.time.Clock()
    fuente = pygame.font.SysFont("consolas", 15)
    grande = pygame.font.SysFont("consolas", 36, bold=True)

    snd = Sonidos()
    rec = Recomendador(MEJORAS.keys())
    cerebro = Cerebro()
    p = Partida(cerebro)
    estado = "menu"          # menu, juego, pausa
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

        # ---- dibujo ----
        pantalla.fill(FONDO)
        p.mapa.dibujar(pantalla)
        if debug:
            dibujar_flujo(pantalla, p.mapa)
        for g in p.gemas:
            g.dibujar(pantalla)
        for e in p.enemigos:
            e.dibujar(pantalla, debug)
        for pr in p.proyectiles:
            pr.dibujar(pantalla)
        p.jugador.dibujar(pantalla)

        j = p.jugador
        pygame.draw.rect(pantalla, (60, 20, 20), (10, 10, 200, 14))
        pygame.draw.rect(pantalla, VERDE, (10, 10, max(0, 200 * j.vida / j.vida_max), 14))
        pygame.draw.rect(pantalla, (20, 30, 45), (0, ALTO - 8, ANCHO, 8))
        pygame.draw.rect(pantalla, (90, 200, 255), (0, ALTO - 8, ANCHO * j.xp / j.xp_sig, 8))
        restante = max(0, (OLA_MS - p.t_ola) // 1000)
        info = (f"Ola {p.ola} ({restante}s)  Nivel {j.nivel}  Bajas {p.bajas}  "
                f"Enemigos {len(p.enemigos)}  FPS {reloj.get_fps():.0f}"
                f"{'' if snd.activo else '  [sin sonido]'}")
        pantalla.blit(fuente.render(info, True, TEXTO), (10, 30))
        if paneles:
            dibujar_paneles(pantalla, p, rec, fuente)

        if estado == "menu":
            dibujar_menu(pantalla, fuente, grande, grande)
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