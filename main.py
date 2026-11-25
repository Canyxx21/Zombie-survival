import pygame
from settings import ANCHO, ALTO, FPS, FONDO
from mapa import Mapa
from jugador import Jugador
from zombi import Zombi

def main():
    pygame.init()
    pantalla = pygame.display.set_mode((ANCHO, ALTO))
    pygame.display.set_caption("Zombie Survival")
    reloj = pygame.time.Clock()
    fuente = pygame.font.SysFont("consolas", 16)

    mapa = Mapa()
    mapa.generar_obstaculos()
    jugador = Jugador(15, 10)
    zombis = [
        Zombi(1, 1, "A*"),
        Zombi(28, 1, "Voraz"),
        Zombi(1, 18, "DFS"),
        Zombi(28, 18, "BFS"),
    ]
    debug = False

    corriendo = True
    while corriendo:
        dt = reloj.tick(FPS)
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                corriendo = False
            if evento.type == pygame.KEYDOWN and evento.key == pygame.K_p:
                debug = not debug

        jugador.mover(pygame.key.get_pressed(), mapa, dt)
        for z in zombis:
            z.actualizar(mapa, jugador, dt, zombis)
        pantalla.fill(FONDO)
        mapa.dibujar(pantalla)
        for z in zombis:
            z.dibujar(pantalla, debug)
        jugador.dibujar(pantalla)

        for i, z in enumerate(zombis):
            linea = f"{z.tipo}: {z.promedio_nodos():.0f} nodos | costo {z.promedio_costo():.1f}"
            pantalla.blit(fuente.render(linea, True, z.color), (8, 6 + i * 18))
        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()