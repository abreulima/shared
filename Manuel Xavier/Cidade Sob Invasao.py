import pygame
import random
import math

pygame.init()

LARGURA = 1000
ALTURA = 700
TAMANHO_CELULA = 48

TELA = pygame.display.set_mode((LARGURA, ALTURA))
pygame.display.set_caption("Cidade Sob Invasao")

FPS = 60
RELOGIO = pygame.time.Clock()

PRETO = (0, 0, 0)
BRANCO = (240, 240, 240)
CINZA = (35, 38, 42)
CINZA_CLARO = (95, 105, 115)
AZUL_NEON = (35, 190, 255)
VERMELHO = (230, 60, 70)
VERDE = (70, 210, 120)
AMARELO = (255, 210, 60)
ROXO = (180, 90, 255)
LARANJA = (255, 130, 40)

MAPA_LARGURA = 18
MAPA_ALTURA = 12
TAMANHO_MAPA_X = MAPA_LARGURA * TAMANHO_CELULA
TAMANHO_MAPA_Y = MAPA_ALTURA * TAMANHO_CELULA

FONTE_TITULO = pygame.font.SysFont("consolas", 34, bold=True)
FONTE = pygame.font.SysFont("consolas", 20)

CORES_INIMIGOS = {
    "patrulha": (180, 190, 200),
    "atirador": (150, 220, 255),
    "guardia": (255, 90, 90),
    "chefe": (255, 60, 220),
}

INIMIGOS_POR_NUCLEO = 4


class Jogador:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.raio = 17
        self.velocidade = 210
        self.vida_max = 100
        self.vida = self.vida_max
        self.sucata = 0
        self.nivel = 1
        self.xp = 0
        self.xp_para_proximo = 50
        self.dano = 25
        self.alcance_tiro = 520
        self.cooldown_tiro = 0
        self.invulneravel = 0
        self.direcao = (1, 0)
        self.nucleos_destruidos = 0
        self.moedas = 0

    def rect(self):
        return pygame.Rect(self.x - self.raio, self.y - self.raio, self.raio * 2, self.raio * 2)

    def mover(self, teclas, mapa, dt):
        dx = 0
        dy = 0
        if teclas[pygame.K_LEFT] or teclas[pygame.K_a]:
            dx -= 1
        if teclas[pygame.K_RIGHT] or teclas[pygame.K_d]:
            dx += 1
        if teclas[pygame.K_UP] or teclas[pygame.K_w]:
            dy -= 1
        if teclas[pygame.K_DOWN] or teclas[pygame.K_s]:
            dy += 1

        tamanho = math.hypot(dx, dy)
        if tamanho > 0:
            dx /= tamanho
            dy /= tamanho
            self.direcao = (dx, dy)

        novo_x = self.x + dx * self.velocidade * dt
        novo_y = self.y + dy * self.velocidade * dt

        if not colide_com_parede(novo_x, self.y, self.raio, mapa):
            self.x = novo_x
        if not colide_com_parede(self.x, novo_y, self.raio, mapa):
            self.y = novo_y

        self.x = max(self.raio, min(self.x, TAMANHO_MAPA_X - self.raio))
        self.y = max(self.raio, min(self.y, TAMANHO_MAPA_Y - self.raio))

        if self.cooldown_tiro > 0:
            self.cooldown_tiro -= dt
        if self.invulneravel > 0:
            self.invulneravel -= dt

    def atirar(self, projeteis):
        if self.cooldown_tiro > 0:
            return False

        dx, dy = self.direcao
        if dx == 0 and dy == 0:
            dx = 1

        projeteis.append({
            "x": self.x + dx * 24,
            "y": self.y + dy * 24,
            "vx": dx * 520,
            "vy": dy * 520,
            "raio": 6,
            "vida": 0.65,
            "dano": self.dano,
        })
        self.cooldown_tiro = 0.28
        return True

    def receber_dano(self, dano):
        if self.invulneravel > 0:
            return False
        self.vida = max(0, self.vida - dano)
        self.invulneravel = 0.7
        return True

    def ganhar_xp(self, quantidade):
        self.xp += quantidade
        if self.xp >= self.xp_para_proximo:
            self.xp -= self.xp_para_proximo
            self.xp_para_proximo = int(self.xp_para_proximo * 1.35)
            self.nivel += 1
            self.vida_max += 15
            self.vida = self.vida_max
            self.dano += 8
            self.alcance_tiro += 25
            return True
        return False


class Inimigo:
    def __init__(self, x, y, tipo, nivel_area):
        self.x = x
        self.y = y
        self.tipo = tipo
        dados = {
            "patrulha": {"vida": 45, "velocidade": 80, "dano": 10, "raio": 15, "xp": 12, "sucata": 1},
            "atirador": {"vida": 35, "velocidade": 55, "dano": 8, "raio": 14, "xp": 14, "sucata": 1},
            "guardia": {"vida": 90, "velocidade": 45, "dano": 18, "raio": 19, "xp": 22, "sucata": 2},
            "chefe": {"vida": 220, "velocidade": 70, "dano": 28, "raio": 26, "xp": 60, "sucata": 6},
        }[tipo]

        escala = 1 + (nivel_area - 1) * 0.18
        for atributo in ("vida", "dano", "xp", "sucata"):
            dados[atributo] = int(dados[atributo] * escala)

        self.vida_max = dados["vida"]
        self.vida = self.vida_max
        self.velocidade = dados["velocidade"]
        self.dano = dados["dano"]
        self.raio = dados["raio"]
        self.xp = dados["xp"]
        self.sucata = dados["sucata"]
        self.moedas = random.randint(2, 5) * nivel_area
        if tipo == "chefe":
            self.moedas = 25 * nivel_area
        self.cooldown_tiro = random.uniform(0.6, 1.4)
        self.morto = False

    def atualizar(self, jogador, mapa, dt):
        if self.morto:
            return None, 0, 0

        dx = jogador.x - self.x
        dy = jogador.y - self.y
        distancia = math.hypot(dx, dy)

        if distancia > 0:
            dx /= distancia
            dy /= distancia

        if self.tipo == "atirador":
            if distancia < 170:
                self.x -= dx * self.velocidade * dt
                self.y -= dy * self.velocidade * dt
            self.cooldown_tiro -= dt
            if distancia < 430 and self.cooldown_tiro <= 0:
                return "tiro", dx, dy
        else:
            alcance = 185 if self.tipo == "guardia" else 260
            if distancia > alcance:
                self.x += dx * self.velocidade * dt
                self.y += dy * self.velocidade * dt

        if distancia <= self.raio + jogador.raio:
            if jogador.receber_dano(self.dano):
                return "dano", 0, 0

        self.x = max(self.raio, min(self.x, TAMANHO_MAPA_X - self.raio))
        self.y = max(self.raio, min(self.y, TAMANHO_MAPA_Y - self.raio))
        return None, 0, 0


class Moeda:
    def __init__(self, x, y, valor):
        self.x = x
        self.y = y
        self.valor = valor
        self.raio = 8
        self.vida = 18
        self.pulsacao = 0

    def atualizar(self, jogador):
        self.pulsacao += 0.08
        self.vida -= 1 / 60
        distancia = math.hypot(jogador.x - self.x, jogador.y - self.y)
        if distancia < 80:
            self.x += (jogador.x - self.x) * 0.08
            self.y += (jogador.y - self.y) * 0.08
        if distancia < self.raio + jogador.raio + 18:
            jogador.moedas += self.valor
            return True
        return False


class Nucleo:
    def __init__(self, x, y, indice):
        self.x = x
        self.y = y
        self.indice = indice
        self.raio = 24
        self.vida = 180
        self.vida_max = 180
        self.ativo = True
        self.cooldown_tiro = 1.2
        self.pulsacao = 0

    def atualizar(self, jogador, projeteis, dt):
        if not self.ativo:
            return None

        self.pulsacao += dt * 5
        self.cooldown_tiro -= dt

        distancia = math.hypot(jogador.x - self.x, jogador.y - self.y)
        if distancia < self.raio + jogador.raio:
            if jogador.receber_dano(22):
                return "dano"

        if distancia < 520 and self.cooldown_tiro <= 0:
            dx = (jogador.x - self.x) / max(distancia, 1)
            dy = (jogador.y - self.y) / max(distancia, 1)
            projeteis.append({
                "x": self.x,
                "y": self.y,
                "vx": dx * 250,
                "vy": dy * 250,
                "raio": 8,
                "vida": 2.2,
                "dano": 18,
                "inimigo": True,
            })
            self.cooldown_tiro = 2.1
        return None


class Particula:
    def __init__(self, x, y, cor, vida):
        self.x = x
        self.y = y
        angulo = random.uniform(0, math.tau)
        velocidade = random.uniform(40, 180)
        self.vx = math.cos(angulo) * velocidade
        self.vy = math.sin(angulo) * velocidade
        self.cor = cor
        self.vida = vida
        self.vida_max = vida
        self.raio = random.randint(2, 5)

    def atualizar(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vida -= dt
        self.vx *= 0.96
        self.vy *= 0.96


def colide_com_parede(x, y, raio, mapa):
    esquerda = max(0, int((x - raio) // TAMANHO_CELULA))
    direita = min(MAPA_LARGURA - 1, int((x + raio) // TAMANHO_CELULA))
    cima = max(0, int((y - raio) // TAMANHO_CELULA))
    baixo = min(MAPA_ALTURA - 1, int((y + raio) // TAMANHO_CELULA))

    for yy in range(cima, baixo + 1):
        for xx in range(esquerda, direita + 1):
            if mapa[yy][xx] == "#":
                return True
    return False


def gerar_mapa():
    mapa = [["." for _ in range(MAPA_LARGURA)] for _ in range(MAPA_ALTURA)]

    for y in range(MAPA_ALTURA):
        mapa[y][0] = "#"
        mapa[y][MAPA_LARGURA - 1] = "#"
    for x in range(MAPA_LARGURA):
        mapa[0][x] = "#"
        mapa[MAPA_ALTURA - 1][x] = "#"

    paredes = [
        (3, 2), (4, 2), (5, 2),
        (8, 2), (9, 2),
        (13, 2), (14, 2),
        (2, 4), (3, 4),
        (6, 4), (7, 4),
        (11, 4), (12, 4),
        (15, 4),
        (4, 6), (5, 6),
        (9, 6), (10, 6),
        (14, 6), (15, 6),
        (2, 8),
        (6, 8), (7, 8), (8, 8),
        (12, 8), (13, 8),
        (3, 10), (4, 10),
        (9, 10), (10, 10),
        (14, 10), (15, 10),
    ]

    for x, y in paredes:
        mapa[y][x] = "#"

    return mapa


def centro_celula(x, y):
    return x * TAMANHO_CELULA + TAMANHO_CELULA // 2, y * TAMANHO_CELULA + TAMANHO_CELULA // 2


def criar_inimigos(mapa, nivel_area, quantidade):
    inimigos = []
    tipos = ["patrulha", "patrulha", "atirador", "guardia"]
    if nivel_area >= 3:
        tipos.append("chefe")

    tentativas = 0
    while len(inimigos) < quantidade and tentativas < 800:
        tentativas += 1
        x = random.randint(3 * TAMANHO_CELULA, TAMANHO_MAPA_X - 3 * TAMANHO_CELULA)
        y = random.randint(3 * TAMANHO_CELULA, TAMANHO_MAPA_Y - 3 * TAMANHO_CELULA)
        if colide_com_parede(x, y, 20, mapa):
            continue
        if abs(x - TAMANHO_MAPA_X // 2) < 180 and abs(y - TAMANHO_MAPA_Y // 2) < 180:
            continue
        tipo = random.choice(tipos)
        inimigos.append(Inimigo(x, y, tipo, nivel_area))
    return inimigos


def criar_nucleo(mapa, indice):
    posicoes = [
        centro_celula(2, 2),
        centro_celula(15, 2),
        centro_celula(2, 9),
        centro_celula(15, 9),
    ]
    return Nucleo(*posicoes[indice], indice)


def desenhar_mapa(tela, mapa, camera_x, camera_y):
    for y, linha in enumerate(mapa):
        for x, celula in enumerate(linha):
            px = x * TAMANHO_CELULA - camera_x
            py = y * TAMANHO_CELULA - camera_y

            if celula == "#":
                pygame.draw.rect(tela, CINZA_CLARO, (px, py, TAMANHO_CELULA, TAMANHO_CELULA))
                pygame.draw.rect(tela, PRETO, (px, py, TAMANHO_CELULA, TAMANHO_CELULA), 2)
            else:
                cor = (31, 34, 39) if (x + y) % 2 == 0 else (35, 38, 43)
                pygame.draw.rect(tela, cor, (px, py, TAMANHO_CELULA, TAMANHO_CELULA))


def desenhar_nucleo(tela, nucleo, camera_x, camera_y):
    if not nucleo.ativo:
        return

    px = nucleo.x - camera_x
    py = nucleo.y - camera_y
    pulsacao = math.sin(nucleo.pulsacao) * 4

    pygame.draw.circle(tela, (80, 0, 120), (int(px), int(py)), int(nucleo.raio + 10 + pulsacao))
    pygame.draw.circle(tela, ROXO, (int(px), int(py)), int(nucleo.raio + pulsacao))
    pygame.draw.circle(tela, BRANCO, (int(px), int(py)), max(4, int(nucleo.raio * 0.35)))

    largura = 58
    altura = 7
    pygame.draw.rect(tela, PRETO, (px - largura // 2, py - nucleo.raio - 18, largura, altura))
    pygame.draw.rect(tela, ROXO, (px - largura // 2, py - nucleo.raio - 18, int(largura * nucleo.vida / nucleo.vida_max), altura))


def desenhar_jogador(tela, jogador, camera_x, camera_y):
    px = jogador.x - camera_x
    py = jogador.y - camera_y

    if jogador.invulneravel > 0 and int(jogador.invulneravel * 18) % 2 == 0:
        return

    pygame.draw.circle(tela, AZUL_NEON, (int(px), int(py)), jogador.raio + 7)
    pygame.draw.circle(tela, (30, 120, 255), (int(px), int(py)), jogador.raio)
    pygame.draw.circle(tela, BRANCO, (int(px), int(py)), 6)

    dx, dy = jogador.direcao
    if dx or dy:
        pygame.draw.line(tela, AMARELO, (int(px), int(py)), (int(px + dx * 28), int(py + dy * 28)), 4)


def desenhar_inimigo(tela, inimigo, camera_x, camera_y):
    if inimigo.morto:
        return

    px = inimigo.x - camera_x
    py = inimigo.y - camera_y
    cor = CORES_INIMIGOS[inimigo.tipo]

    pygame.draw.circle(tela, (20, 20, 25), (int(px), int(py)), inimigo.raio + 5)
    pygame.draw.circle(tela, cor, (int(px), int(py)), inimigo.raio)

    olhos = 4
    pygame.draw.circle(tela, PRETO, (int(px - olhos), int(py - 4)), 2)
    pygame.draw.circle(tela, PRETO, (int(px + olhos), int(py - 4)), 2)

    if inimigo.tipo in ("atirador", "chefe"):
        pygame.draw.circle(tela, LARANJA, (int(px), int(py)), max(2, inimigo.raio // 3))

    largura = 44
    altura = 5
    pygame.draw.rect(tela, PRETO, (px - largura // 2, py - inimigo.raio - 12, largura, altura))
    pygame.draw.rect(tela, VERMELHO, (px - largura // 2, py - inimigo.raio - 12, int(largura * inimigo.vida / inimigo.vida_max), altura))


def desenhar_moeda(tela, moeda, camera_x, camera_y):
    px = moeda.x - camera_x
    py = moeda.y - camera_y
    pulsacao = math.sin(moeda.pulsacao) * 2

    pygame.draw.circle(tela, (255, 235, 120), (int(px), int(py)), int(moeda.raio + 3 + pulsacao))
    pygame.draw.circle(tela, AMARELO, (int(px), int(py)), int(moeda.raio + pulsacao))
    pygame.draw.circle(tela, (170, 110, 0), (int(px), int(py)), max(2, moeda.raio - 4))


def desenhar_projeteil(tela, projetil, camera_x, camera_y):
    cor = LARANJA if projetil.get("inimigo") else AMARELO
    pygame.draw.circle(tela, cor, (int(projetil["x"] - camera_x), int(projetil["y"] - camera_y)), projetil["raio"])
    pygame.draw.circle(tela, BRANCO, (int(projetil["x"] - camera_x), int(projetil["y"] - camera_y)), max(2, projetil["raio"] // 3))


def desenhar_particulas(tela, particulas, camera_x, camera_y):
    for particula in particulas:
        alpha = max(0, int(255 * particula.vida / particula.vida_max))
        tamanho = max(1, particula.raio)
        superficie = pygame.Surface((tamanho * 2, tamanho * 2), pygame.SRCALPHA)
        pygame.draw.circle(superficie, (*particula.cor, alpha), (tamanho, tamanho), tamanho)
        tela.blit(superficie, (particula.x - camera_x - tamanho, particula.y - camera_y - tamanho))


def desenhar_interface(tela, jogador, nivel_area, nucleos):
    pygame.draw.rect(tela, (10, 12, 15), (0, 0, LARGURA, 86))
    pygame.draw.line(tela, AZUL_NEON, (0, 86), (LARGURA, 86), 2)

    texto = FONTE_TITULO.render("Cidade Sob Invasao", True, AZUL_NEON)
    tela.blit(texto, (18, 10))

    texto = FONTE.render(f"Bairro: {nivel_area}   Nivel: {jogador.nivel}   XP: {jogador.xp}/{jogador.xp_para_proximo}", True, BRANCO)
    tela.blit(texto, (18, 50))

    barra_vida = 220
    altura_barra = 18
    x = LARGURA - barra_vida - 24
    pygame.draw.rect(tela, PRETO, (x, 18, barra_vida, altura_barra))
    pygame.draw.rect(tela, PRETO, (x, 18, barra_vida, altura_barra), 2)
    pygame.draw.rect(tela, VERDE, (x, 18, int(barra_vida * jogador.vida / jogador.vida_max), altura_barra))

    texto = FONTE.render(f"Vida {jogador.vida}/{jogador.vida_max}", True, BRANCO)
    tela.blit(texto, (x, 40))

    texto = FONTE.render(f"Sucata: {jogador.sucata}   Moedas: {jogador.moedas}   Dano: {jogador.dano}", True, AMARELO)
    tela.blit(texto, (330, 18))

    texto = FONTE.render(f"Nucleos: {jogador.nucleos_destruidos}/4", True, ROXO)
    tela.blit(texto, (330, 50))

    nucleos_ativos = sum(1 for nucleo in nucleos if nucleo.ativo)
    texto = FONTE.render(f"Nucleos ativos: {nucleos_ativos}", True, ROXO)
    tela.blit(texto, (600, 50))


def desenhar_mensagem(tela, texto, subtexto=""):
    superficie = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
    superficie.fill((0, 0, 0, 170))
    tela.blit(superficie, (0, 0))

    titulo = FONTE_TITULO.render(texto, True, AZUL_NEON)
    tela.blit(titulo, (LARGURA // 2 - titulo.get_width() // 2, ALTURA // 2 - 40))

    if subtexto:
        texto_pequeno = FONTE.render(subtexto, True, BRANCO)
        tela.blit(texto_pequeno, (LARGURA // 2 - texto_pequeno.get_width() // 2, ALTURA // 2 + 10))


def criar_particulas(x, y, cor, quantidade=12):
    return [Particula(x, y, cor, random.uniform(0.3, 0.8)) for _ in range(quantidade)]


def remover_colisoes(lista):
    return [item for item in lista if not item.get("remover")]


def jogo():
    mapa = gerar_mapa()
    jogador = Jogador(TAMANHO_MAPA_X // 2, TAMANHO_MAPA_Y // 2)
    nivel_area = 1
    inimigos = criar_inimigos(mapa, nivel_area, INIMIGOS_POR_NUCLEO + 1)
    nucleos = [criar_nucleo(mapa, i) for i in range(4)]
    projeteis = []
    moedas = []
    particulas = []
    mensagem = "Derrote maquinas, recolha sucata e destrua os 4 nucleos da IA."
    tempo_mensagem = 5
    rodando = True
    venceu = False

    while rodando:
        dt = RELOGIO.tick(FPS) / 1000
        agora = pygame.time.get_ticks()

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False
            if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
                rodando = False
            if evento.type == pygame.KEYDOWN and evento.key == pygame.K_r and (jogador.vida <= 0 or venceu):
                return jogo()
            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1 and jogador.vida > 0 and not venceu:
                jogador.atirar(projeteis)

        if jogador.vida > 0 and not venceu:
            teclas = pygame.key.get_pressed()
            jogador.mover(teclas, mapa, dt)

            for nucleo in nucleos:
                resultado = nucleo.atualizar(jogador, projeteis, dt)
                if resultado == "dano":
                    particulas.extend(criar_particulas(jogador.x, jogador.y, VERMELHO, 8))

            for inimigo in inimigos:
                acao, dx, dy = inimigo.atualizar(jogador, mapa, dt)
                if acao == "tiro":
                    projeteis.append({
                        "x": inimigo.x + dx * 18,
                        "y": inimigo.y + dy * 18,
                        "vx": dx * 300,
                        "vy": dy * 300,
                        "raio": 5,
                        "vida": 1.6,
                        "dano": inimigo.dano,
                        "inimigo": True,
                    })
                elif acao == "dano":
                    particulas.extend(criar_particulas(jogador.x, jogador.y, VERMELHO, 8))

            for projetil in projeteis:
                projetil["x"] += projetil["vx"] * dt
                projetil["y"] += projetil["vy"] * dt
                projetil["vida"] -= dt

                if projetil["vida"] <= 0 or colide_com_parede(projetil["x"], projetil["y"], projetil["raio"], mapa):
                    projetil["remover"] = True
                    particulas.extend(criar_particulas(projetil["x"], projetil["y"], LARANJA if projetil.get("inimigo") else AMARELO, 5))

                if not projetil.get("inimigo"):
                    for inimigo in inimigos:
                        if inimigo.morto:
                            continue
                        distancia = math.hypot(projetil["x"] - inimigo.x, projetil["y"] - inimigo.y)
                        if distancia <= projetil["raio"] + inimigo.raio:
                            projetil["remover"] = True
                            inimigo.vida -= projetil["dano"]
                            particulas.extend(criar_particulas(inimigo.x, inimigo.y, CORES_INIMIGOS[inimigo.tipo], 10))
                            if inimigo.vida <= 0:
                                inimigo.morto = True
                                jogador.sucata += inimigo.sucata
                                moedas.append(Moeda(inimigo.x, inimigo.y, inimigo.moedas))
                                nivelou = jogador.ganhar_xp(inimigo.xp)
                                if nivelou:
                                    mensagem = f"Nivel {jogador.nivel} alcancado! Dano aumentado."
                                    tempo_mensagem = 3
                            break

                    if not projetil.get("remover"):
                        for nucleo in nucleos:
                            if not nucleo.ativo:
                                continue
                            distancia = math.hypot(projetil["x"] - nucleo.x, projetil["y"] - nucleo.y)
                            if distancia <= projetil["raio"] + nucleo.raio:
                                projetil["remover"] = True
                                nucleo.vida -= projetil["dano"]
                                particulas.extend(criar_particulas(nucleo.x, nucleo.y, ROXO, 14))
                                if nucleo.vida <= 0:
                                    nucleo.ativo = False
                                    jogador.nucleos_destruidos += 1
                                    jogador.sucata += 8
                                    mensagem = f"Nucleo {jogador.nucleos_destruidos}/4 destruido. A cidade reage."
                                    tempo_mensagem = 3
                                    if jogador.nucleos_destruidos < 4:
                                        inimigos.extend(criar_inimigos(mapa, nivel_area, 2))
                                break
                else:
                    distancia = math.hypot(projetil["x"] - jogador.x, projetil["y"] - jogador.y)
                    if distancia <= projetil["raio"] + jogador.raio:
                        projetil["remover"] = True
                        if jogador.receber_dano(projetil["dano"]):
                            particulas.extend(criar_particulas(jogador.x, jogador.y, VERMELHO, 10))

            projeteis = remover_colisoes(projeteis)
            for moeda in moedas:
                if moeda.atualizar(jogador):
                    moeda.vida = 0
            moedas = [moeda for moeda in moedas if moeda.vida > 0]
            particulas = [p for p in particulas if p.vida > 0]
            for particula in particulas:
                particula.atualizar(dt)

            if sum(1 for nucleo in nucleos if not nucleo.ativo) >= nivel_area:
                nivel_area += 1
                if nivel_area <= 4:
                    inimigos.extend(criar_inimigos(mapa, nivel_area, INIMIGOS_POR_NUCLEO + nivel_area))
                    mensagem = f"Bairro {nivel_area} liberado. Mais maquinas avancam."
                    tempo_mensagem = 4

            if jogador.nucleos_destruidos >= 4:
                venceu = True
                mensagem = "A IA central foi destruida. A cidade esta livre."
                tempo_mensagem = 999

            if jogador.vida <= 0:
                mensagem = "Fim de jogo."
                tempo_mensagem = 999

            if tempo_mensagem > 0:
                tempo_mensagem -= dt

        camera_x = jogador.x - LARGURA // 2
        camera_y = jogador.y - ALTURA // 2
        camera_x = max(0, min(camera_x, TAMANHO_MAPA_X - LARGURA))
        camera_y = max(0, min(camera_y, TAMANHO_MAPA_Y - ALTURA))

        TELA.fill(CINZA)
        desenhar_mapa(TELA, mapa, camera_x, camera_y)

        for nucleo in nucleos:
            desenhar_nucleo(TELA, nucleo, camera_x, camera_y)

        for inimigo in inimigos:
            desenhar_inimigo(TELA, inimigo, camera_x, camera_y)

        for moeda in moedas:
            desenhar_moeda(TELA, moeda, camera_x, camera_y)

        desenhar_jogador(TELA, jogador, camera_x, camera_y)

        for projetil in projeteis:
            desenhar_projeteil(TELA, projetil, camera_x, camera_y)

        desenhar_particulas(TELA, particulas, camera_x, camera_y)
        desenhar_interface(TELA, jogador, nivel_area, nucleos)

        if tempo_mensagem > 0:
            desenhar_mensagem(TELA, mensagem)
        elif jogador.vida <= 0:
            desenhar_mensagem(TELA, "Fim de jogo", "Pressione R para reiniciar ou ESC para sair")
        elif venceu:
            desenhar_mensagem(TELA, "Vitoria!", "Pressione R para jogar novamente ou ESC para sair")

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    jogo()
