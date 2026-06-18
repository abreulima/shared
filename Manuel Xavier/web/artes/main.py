from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import math
import random
from typing import Iterable

import pygame


WIDTH = 1000
HEIGHT = 700
FPS = 60
TILE = 48
WORLD_WIDTH = 2400
WORLD_HEIGHT = 1728

ROOT = Path(__file__).resolve().parent


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def distance(a: pygame.Vector2, b: pygame.Vector2) -> float:
    return (a - b).length()


@dataclass
class Reactor:
    rect: pygame.Rect
    hp: int = 150
    max_hp: int = 150
    active: bool = True
    pulse: float = 0.0
    district: int = 0


@dataclass
class Drop:
    kind: str
    pos: pygame.Vector2
    amount: int = 1
    ttl: float = 18.0
    pulse: float = 0.0

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.pos.x) - 12, int(self.pos.y) - 12, 24, 24)


@dataclass
class Bullet:
    pos: pygame.Vector2
    vel: pygame.Vector2
    damage: int
    friendly: bool
    life: float = 1.8
    radius: int = 5

    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.pos.x) - self.radius, int(self.pos.y) - self.radius, self.radius * 2, self.radius * 2)


@dataclass
class Particle:
    pos: pygame.Vector2
    vel: pygame.Vector2
    color: tuple[int, int, int]
    life: float
    radius: int


@dataclass
class Turret:
    pos: pygame.Vector2
    fire_delay: float = 0.55
    fire_timer: float = 0.2
    range: float = 330.0
    damage: int = 12
    life: float = 40.0


@dataclass
class Mine:
    pos: pygame.Vector2
    radius: int = 18
    damage: int = 28
    armed: bool = True
    life: float = 20.0


@dataclass
class Enemy:
    kind: str
    pos: pygame.Vector2
    home: pygame.Vector2
    hp: int
    max_hp: int
    speed: float
    damage: int
    detection: float
    fire_delay: float
    radius: int
    wander_angle: float = field(default_factory=lambda: random.uniform(0, math.tau))
    fire_timer: float = field(default_factory=lambda: random.uniform(0.1, 1.0))
    drift: float = field(default_factory=lambda: random.uniform(0.3, 1.2))

    @property
    def alive(self) -> bool:
        return self.hp > 0

    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.pos.x) - self.radius, int(self.pos.y) - self.radius, self.radius * 2, self.radius * 2)


@dataclass
class Player:
    pos: pygame.Vector2
    hp: int = 100
    max_hp: int = 100
    scrap: int = 0
    speed: float = 220.0
    damage: int = 22
    fire_delay: float = 0.23
    special_charges: int = 0
    dash_charges: int = 0
    turret_charges: int = 0
    mine_charges: int = 0
    tech_level: int = 0
    fire_timer: float = 0.0
    invuln: float = 0.0
    dash_timer: float = 0.0
    facing: pygame.Vector2 = field(default_factory=lambda: pygame.Vector2(1, 0))
    radius: int = 18

    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.pos.x) - self.radius, int(self.pos.y) - self.radius, self.radius * 2, self.radius * 2)


class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Cidade Sob Invasao")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
        self.clock = pygame.time.Clock()

        self.font_title = pygame.font.SysFont("consolas", 42, bold=True)
        self.font_big = pygame.font.SysFont("consolas", 26, bold=True)
        self.font = pygame.font.SysFont("consolas", 18)
        self.font_small = pygame.font.SysFont("consolas", 15)

        self.images = self.load_assets()
        self.keys: set[int] = set()
        self.state = "menu"
        self.reset_game()

    def load_image(self, filename: str, size: tuple[int, int] | None = None, alpha: bool = True) -> pygame.Surface | None:
        path = ROOT / filename
        if not path.exists():
            return None

        image = pygame.image.load(str(path))
        image = image.convert_alpha() if alpha else image.convert()
        if size is not None:
            image = pygame.transform.scale(image, size)
        return image

    def load_assets(self) -> dict[str, pygame.Surface | None]:
        return {
            "cover": self.load_image("Capa do jogo. png.png", (WIDTH, HEIGHT), alpha=False),
            "background": self.load_image("fundo.png", (WIDTH, HEIGHT), alpha=False),
            "tile_top": self.load_image("relvatopo.png", (TILE, TILE)),
            "tile_mid": self.load_image("relvameio.png", (TILE, TILE)),
            "player": self.load_image("jogador.png", (48, 48)),
            "enemy": self.load_image("inimigo.png", (48, 48)),
            "boss": self.load_image("boss.png", (96, 96)),
            "weapon": self.load_image("arma.png", (28, 28)),
            "scrap": self.load_image("coletavel.png", (24, 24)),
            "life": self.load_image("vida.png", (24, 24)),
            "special": self.load_image("especial.png", (24, 24)),
            "objective": self.load_image("objetivo.png", (54, 54)),
            "workbench": self.load_image("oficina.png", (96, 96)),
        }

    def reset_game(self) -> None:
        self.running = True
        self.player = Player(pygame.Vector2(220, 220))
        self.camera = pygame.Vector2(0, 0)
        self.bullets: list[Bullet] = []
        self.enemies: list[Enemy] = []
        self.drops: list[Drop] = []
        self.particles: list[Particle] = []
        self.turrets: list[Turret] = []
        self.mines: list[Mine] = []
        self.walls = self.create_walls()
        self.workbench = self.place_clear_rect(120, 120, 96, 96)
        self.extractor = self.place_clear_rect(WORLD_WIDTH - 220, WORLD_HEIGHT - 220, 96, 96)
        self.reactors = self.create_reactors()
        self.district_liberated = [False, False, False, False]
        self.extractor_active = False
        self.boss = self.create_boss()
        self.boss_spawned = False
        self.boss_defeated = False
        self.victory = False
        self.game_over = False
        self.crafting_open = False
        self.wave_timer = 8.0
        self.drop_timer = 14.0
        self.message = "Explore a cidade, destrua os reatores e recolha sucata."
        self.message_timer = 5.0
        self.spawn_initial_enemies()

    def create_reactors(self) -> list[Reactor]:
        positions = [
            (650, 360),
            (1780, 360),
            (650, 1260),
            (1780, 1260),
        ]
        reactors = []
        for index, (x, y) in enumerate(positions):
            rect = self.place_clear_rect(x - 26, y - 26, 52, 52)
            reactors.append(Reactor(rect, district=index))
        return reactors

    def create_boss(self) -> Enemy:
        return Enemy(
            kind="boss",
            pos=pygame.Vector2(1460, 940),
            home=pygame.Vector2(1460, 940),
            hp=420,
            max_hp=420,
            speed=92,
            damage=24,
            detection=900,
            fire_delay=1.0,
            radius=34,
            fire_timer=1.2,
        )

    def create_walls(self) -> list[pygame.Rect]:
        walls = [
            pygame.Rect(-40, -40, 40, WORLD_HEIGHT + 80),
            pygame.Rect(WORLD_WIDTH, -40, 40, WORLD_HEIGHT + 80),
            pygame.Rect(-40, -40, WORLD_WIDTH + 80, 40),
            pygame.Rect(-40, WORLD_HEIGHT, WORLD_WIDTH + 80, 40),
        ]

        # Blocos urbanos que criam cobertura sem fechar o mapa.
        buildings = [
            (320, 260, 210, 120),
            (520, 720, 190, 120),
            (820, 160, 180, 110),
            (980, 520, 240, 140),
            (1260, 220, 180, 120),
            (1460, 760, 230, 140),
            (1880, 220, 160, 120),
            (1860, 720, 210, 120),
            (340, 1180, 220, 130),
            (960, 1240, 220, 120),
            (1280, 1100, 170, 130),
            (1680, 1180, 250, 150),
            (1180, 860, 160, 100),
            (1520, 420, 160, 100),
            (620, 920, 160, 100),
        ]
        for x, y, w, h in buildings:
            walls.append(pygame.Rect(x, y, w, h))
        return walls

    def find_open_point(self, x: float, y: float, radius: int) -> pygame.Vector2:
        candidate = pygame.Vector2(x, y)
        rect = pygame.Rect(int(candidate.x) - radius, int(candidate.y) - radius, radius * 2, radius * 2)
        if not self.hit_wall(rect):
            return candidate

        for spread in range(24, 280, 24):
            for angle_deg in range(0, 360, 30):
                angle = math.radians(angle_deg)
                candidate = pygame.Vector2(x + math.cos(angle) * spread, y + math.sin(angle) * spread)
                candidate.x = clamp(candidate.x, radius, WORLD_WIDTH - radius)
                candidate.y = clamp(candidate.y, radius, WORLD_HEIGHT - radius)
                rect = pygame.Rect(int(candidate.x) - radius, int(candidate.y) - radius, radius * 2, radius * 2)
                if not self.hit_wall(rect):
                    return candidate

        return pygame.Vector2(
            clamp(x, radius, WORLD_WIDTH - radius),
            clamp(y, radius, WORLD_HEIGHT - radius),
        )

    def place_clear_rect(self, x: float, y: float, w: int, h: int) -> pygame.Rect:
        rect = pygame.Rect(int(x), int(y), w, h)
        if not self.rect_blocked(rect):
            return rect

        center_x = rect.centerx
        center_y = rect.centery
        radius = max(w, h) // 2
        for spread in range(24, 360, 24):
            for angle_deg in range(0, 360, 30):
                angle = math.radians(angle_deg)
                candidate_center = pygame.Vector2(
                    center_x + math.cos(angle) * spread,
                    center_y + math.sin(angle) * spread,
                )
                candidate_rect = pygame.Rect(0, 0, w, h)
                candidate_rect.center = (
                    int(clamp(candidate_center.x, radius, WORLD_WIDTH - radius)),
                    int(clamp(candidate_center.y, radius, WORLD_HEIGHT - radius)),
                )
                if not self.rect_blocked(candidate_rect):
                    return candidate_rect

        return rect

    def rect_blocked(self, rect: pygame.Rect) -> bool:
        return (
            self.hit_wall(rect)
            or rect.colliderect(getattr(self, "workbench", pygame.Rect(-10_000, -10_000, 1, 1)))
            or rect.colliderect(getattr(self, "extractor", pygame.Rect(-10_000, -10_000, 1, 1)))
            or any(rect.colliderect(reactor.rect) for reactor in getattr(self, "reactors", []))
        )

    def spawn_initial_enemies(self) -> None:
        presets = [
            ("patrol", 520, 220, 1),
            ("patrol", 840, 420, 1),
            ("shooter", 1180, 280, 1),
            ("guardian", 1540, 420, 1),
            ("patrol", 1960, 260, 1),
            ("shooter", 520, 980, 2),
            ("patrol", 860, 1320, 2),
            ("guardian", 1220, 1180, 2),
            ("shooter", 1740, 1360, 2),
            ("patrol", 2060, 1240, 2),
        ]
        for kind, x, y, district in presets:
            self.enemies.append(self.create_enemy(kind, x, y, district))

    def create_enemy(self, kind: str, x: float, y: float, district: int) -> Enemy:
        tuning = {
            "patrol": (48, 80, 12, 0.0, 18, 42),
            "shooter": (38, 60, 8, 1.25, 14, 36),
            "guardian": (88, 50, 18, 0.0, 22, 46),
        }
        if kind not in tuning:
            kind = "patrol"
        hp, speed, damage, fire_delay, radius, detection = tuning[kind]
        scale = 1.0 + (district - 1) * 0.18
        position = self.find_open_point(x, y, radius)
        return Enemy(
            kind=kind,
            pos=position,
            home=position.copy(),
            hp=int(hp * scale),
            max_hp=int(hp * scale),
            speed=speed * scale,
            damage=int(damage * scale),
            detection=detection * (1.0 + (district - 1) * 0.1),
            fire_delay=fire_delay,
            radius=radius,
        )

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.process_events()
            self.update(dt)
            self.draw()
            pygame.display.flip()
        pygame.quit()

    def process_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self.keys.add(event.key)
                self.handle_keydown(event.key)
            elif event.type == pygame.KEYUP:
                self.keys.discard(event.key)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.try_shoot()

    def handle_keydown(self, key: int) -> None:
        if key == pygame.K_ESCAPE:
            self.running = False
            return

        if key == pygame.K_RETURN and self.state == "menu":
            self.state = "play"
            self.set_message("Cidade sob ataque. Reaja, recolha sucata e evolua.", 4.0)
            return

        if key == pygame.K_r and self.state in {"game_over", "victory"}:
            self.reset_game()
            self.state = "play"
            return

        if self.state != "play":
            return

        if key == pygame.K_c:
            if self.player_in_workbench_range():
                self.crafting_open = not self.crafting_open
                self.set_message("Oficina aberta." if self.crafting_open else "Oficina fechada.", 2.0)
            else:
                self.set_message("Chegue a oficina para craftar.", 2.0)

        if key == pygame.K_LSHIFT and self.player.dash_charges > 0 and not self.crafting_open:
            self.player.dash_charges -= 1
            self.player.dash_timer = 0.18
            self.spawn_particles(self.player.pos.x, self.player.pos.y, (80, 200, 255), 14, 90)
            self.set_message("Impulso usado.", 1.4)

        if key == pygame.K_e:
            self.use_special()

        if key == pygame.K_z and self.player.turret_charges > 0 and not self.crafting_open:
            self.place_turret()

        if key == pygame.K_x and self.player.mine_charges > 0 and not self.crafting_open:
            self.place_mine()

        if self.crafting_open:
            self.handle_crafting_key(key)

        if key == pygame.K_SPACE:
            self.try_shoot()

    def handle_crafting_key(self, key: int) -> None:
        costs = {
            pygame.K_1: ("damage", 8),
            pygame.K_2: ("fire", 8),
            pygame.K_3: ("hp", 6),
            pygame.K_4: ("special", 10),
            pygame.K_5: ("dash", 10),
            pygame.K_6: ("turret", 12),
            pygame.K_7: ("mine", 8),
        }
        if key not in costs:
            return

        upgrade, cost = costs[key]
        if self.player.scrap < cost:
            self.set_message("Sucata insuficiente.", 2.0)
            return

        self.player.scrap -= cost
        if upgrade == "damage":
            self.player.damage += 6
            self.set_message("Arma reforcada. Dano aumentado.", 3.0)
        elif upgrade == "fire":
            self.player.fire_delay = max(0.08, self.player.fire_delay * 0.88)
            self.set_message("Mecanismo ajustado. Disparo mais rapido.", 3.0)
        elif upgrade == "hp":
            self.player.max_hp += 20
            self.player.hp = self.player.max_hp
            self.set_message("Placas de armadura instaladas.", 3.0)
        elif upgrade == "special":
            self.player.special_charges += 1
            self.set_message("Carga especial adicionada.", 3.0)
        elif upgrade == "dash":
            self.player.dash_charges += 1
            self.set_message("Impulso extra liberado.", 3.0)
        elif upgrade == "turret":
            self.player.turret_charges += 1
            self.set_message("Modulo de torreta fabricado.", 3.0)
        elif upgrade == "mine":
            self.player.mine_charges += 1
            self.set_message("Carga de mina fabricada.", 3.0)

    def player_in_workbench_range(self) -> bool:
        return self.player.rect().inflate(70, 70).colliderect(self.workbench)

    def use_special(self) -> None:
        if self.state != "play" or self.crafting_open:
            return
        if self.player.special_charges <= 0:
            self.set_message("Sem carga especial.", 1.6)
            return

        self.player.special_charges -= 1
        center = self.player.pos.copy()
        self.spawn_particles(center.x, center.y, (255, 120, 40), 30, 170)
        for enemy in self.enemies:
            if not enemy.alive:
                continue
            if distance(center, enemy.pos) <= 170:
                enemy.hp -= 35
        if self.boss_spawned and self.boss.alive and distance(center, self.boss.pos) <= 220:
            self.boss.hp -= 40
        self.set_message("Pulso eletromagnetico ativado.", 2.0)

    def place_turret(self) -> None:
        if self.player.turret_charges <= 0:
            return
        spot = self.find_open_point(self.player.pos.x + self.player.facing.x * 46, self.player.pos.y + self.player.facing.y * 46, 16)
        self.turrets.append(Turret(pos=spot))
        self.player.turret_charges -= 1
        self.spawn_particles(spot.x, spot.y, (120, 220, 255), 10, 45)
        self.set_message("Torreta posicionada.", 1.6)

    def place_mine(self) -> None:
        if self.player.mine_charges <= 0:
            return
        spot = self.find_open_point(self.player.pos.x, self.player.pos.y, 16)
        self.mines.append(Mine(pos=spot))
        self.player.mine_charges -= 1
        self.spawn_particles(spot.x, spot.y, (255, 200, 80), 8, 35)
        self.set_message("Mina armada.", 1.6)

    def try_shoot(self) -> None:
        if self.state != "play" or self.crafting_open or self.player.fire_timer > 0:
            return

        mouse = pygame.Vector2(pygame.mouse.get_pos()) + self.camera
        direction = mouse - self.player.pos
        if direction.length_squared() == 0:
            direction = pygame.Vector2(1, 0)
        else:
            direction = direction.normalize()
        self.player.facing = direction
        self.bullets.append(
            Bullet(
                pos=self.player.pos + direction * 26,
                vel=direction * 620,
                damage=self.player.damage,
                friendly=True,
                life=1.3,
                radius=5,
            )
        )
        self.player.fire_timer = self.player.fire_delay
        self.spawn_particles(self.player.pos.x, self.player.pos.y, (255, 220, 70), 6, 40)

    def set_message(self, text: str, seconds: float) -> None:
        self.message = text
        self.message_timer = seconds

    def update(self, dt: float) -> None:
        if self.state != "play":
            return

        if self.message_timer > 0:
            self.message_timer = max(0.0, self.message_timer - dt)

        if self.crafting_open:
            self.update_camera(dt)
            return

        self.update_player(dt)
        self.update_enemies(dt)
        self.update_bullets(dt)
        self.update_drops(dt)
        self.update_particles(dt)
        self.update_turrets(dt)
        self.update_mines(dt)
        self.update_reactors(dt)
        self.update_spawns(dt)
        self.update_camera(dt)
        self.check_victory_conditions()
        self.check_game_over()

    def update_player(self, dt: float) -> None:
        move = pygame.Vector2(0, 0)
        if self.keys.__contains__(pygame.K_w) or self.keys.__contains__(pygame.K_UP):
            move.y -= 1
        if self.keys.__contains__(pygame.K_s) or self.keys.__contains__(pygame.K_DOWN):
            move.y += 1
        if self.keys.__contains__(pygame.K_a) or self.keys.__contains__(pygame.K_LEFT):
            move.x -= 1
        if self.keys.__contains__(pygame.K_d) or self.keys.__contains__(pygame.K_RIGHT):
            move.x += 1

        if move.length_squared() > 0:
            move = move.normalize()
            self.player.facing = move

        self.player.dash_timer = max(0.0, self.player.dash_timer - dt)
        speed = self.player.speed * (1.85 if self.player.dash_timer > 0 and move.length_squared() > 0 else 1.0)

        delta = move * speed * dt
        self.move_with_walls(self.player.pos, delta, self.player.radius)

        self.player.fire_timer = max(0.0, self.player.fire_timer - dt)
        self.player.invuln = max(0.0, self.player.invuln - dt)

    def move_with_walls(self, position: pygame.Vector2, delta: pygame.Vector2, radius: int) -> None:
        rect = pygame.Rect(int(position.x) - radius, int(position.y) - radius, radius * 2, radius * 2)
        solid_walls = self.walls[4:]

        rect.x += int(delta.x)
        for wall in solid_walls:
            if rect.colliderect(wall):
                if delta.x > 0:
                    rect.right = wall.left
                elif delta.x < 0:
                    rect.left = wall.right

        rect.y += int(delta.y)
        for wall in solid_walls:
            if rect.colliderect(wall):
                if delta.y > 0:
                    rect.bottom = wall.top
                elif delta.y < 0:
                    rect.top = wall.bottom

        position.update(rect.centerx, rect.centery)
        if rect.left < 0 or rect.top < 0 or rect.right > WORLD_WIDTH or rect.bottom > WORLD_HEIGHT:
            self.player.hp = 0
            self.set_message("Saíste do mapa. Pressione R para tentar novamente.", 999.0)

    def update_enemies(self, dt: float) -> None:
        for enemy in self.enemies:
            if not enemy.alive:
                continue

            enemy.fire_timer = max(0.0, enemy.fire_timer - dt)
            to_player = self.player.pos - enemy.pos
            dist = to_player.length()
            direction = to_player.normalize() if dist > 0 else pygame.Vector2(1, 0)

            if enemy.kind == "shooter":
                # Atiradores caçam o jogador, mas tentam manter uma distância de disparo.
                if dist > 210:
                    self.move_enemy(enemy, direction * enemy.speed * 0.8 * dt)
                elif dist < 150:
                    self.move_enemy(enemy, -direction * enemy.speed * 0.45 * dt)
                if dist < 520 and enemy.fire_timer <= 0:
                    self.spawn_enemy_bullet(enemy, direction, 330, 1.8)
                    enemy.fire_timer = enemy.fire_delay
            elif enemy.kind == "guardian":
                self.move_enemy(enemy, direction * enemy.speed * 1.05 * dt)
            else:
                self.move_enemy(enemy, direction * enemy.speed * 1.0 * dt)

            if dist <= enemy.radius + self.player.radius:
                self.damage_player(enemy.damage)

        if self.boss_spawned and self.boss.alive:
            self.update_boss(dt)

    def move_enemy(self, enemy: Enemy, delta: pygame.Vector2) -> None:
        enemy_rect = pygame.Rect(int(enemy.pos.x) - enemy.radius, int(enemy.pos.y) - enemy.radius, enemy.radius * 2, enemy.radius * 2)

        enemy_rect.x += int(delta.x)
        for wall in self.walls:
            if enemy_rect.colliderect(wall):
                if delta.x > 0:
                    enemy_rect.right = wall.left
                elif delta.x < 0:
                    enemy_rect.left = wall.right

        enemy_rect.y += int(delta.y)
        for wall in self.walls:
            if enemy_rect.colliderect(wall):
                if delta.y > 0:
                    enemy_rect.bottom = wall.top
                elif delta.y < 0:
                    enemy_rect.top = wall.bottom

        enemy.pos.update(enemy_rect.centerx, enemy_rect.centery)
        enemy.pos.x = clamp(enemy.pos.x, enemy.radius, WORLD_WIDTH - enemy.radius)
        enemy.pos.y = clamp(enemy.pos.y, enemy.radius, WORLD_HEIGHT - enemy.radius)

    def update_boss(self, dt: float) -> None:
        boss = self.boss
        boss.fire_timer = max(0.0, boss.fire_timer - dt)
        to_player = self.player.pos - boss.pos
        dist = to_player.length()
        direction = to_player.normalize() if dist > 0 else pygame.Vector2(1, 0)

        if dist > 320:
            self.move_enemy(boss, direction * boss.speed * dt)
        elif dist < 210:
            self.move_enemy(boss, -direction * boss.speed * 0.7 * dt)

        if boss.fire_timer <= 0:
            if dist < 760:
                for angle in (-0.22, 0.0, 0.22):
                    vec = direction.rotate_rad(angle)
                    self.spawn_enemy_bullet(boss, vec, 280, 2.0, damage=24)
            else:
                self.spawn_enemy_bullet(boss, direction, 320, 2.2, damage=24)
            boss.fire_timer = boss.fire_delay

        if dist <= boss.radius + self.player.radius:
            self.damage_player(boss.damage)

    def spawn_enemy_bullet(self, enemy: Enemy, direction: pygame.Vector2, speed: float, life: float, damage: int | None = None) -> None:
        self.bullets.append(
            Bullet(
                pos=enemy.pos + direction * (enemy.radius + 12),
                vel=direction * speed,
                damage=damage if damage is not None else enemy.damage,
                friendly=False,
                life=life,
                radius=6 if enemy.kind == "boss" else 4,
            )
        )
        self.spawn_particles(enemy.pos.x, enemy.pos.y, (255, 110, 60), 5, 25)

    def damage_player(self, amount: int) -> None:
        if self.player.invuln > 0 or self.state != "play":
            return
        self.player.hp = max(0, self.player.hp - amount)
        self.player.invuln = 0.75
        self.spawn_particles(self.player.pos.x, self.player.pos.y, (255, 70, 70), 14, 80)
        self.set_message("Recebeu dano!", 1.0)

    def update_bullets(self, dt: float) -> None:
        remaining: list[Bullet] = []
        for bullet in self.bullets:
            bullet.life -= dt
            bullet.pos += bullet.vel * dt

            if bullet.life <= 0:
                continue
            if not (0 <= bullet.pos.x <= WORLD_WIDTH and 0 <= bullet.pos.y <= WORLD_HEIGHT):
                continue

            if self.hit_wall(bullet.rect()):
                self.spawn_particles(bullet.pos.x, bullet.pos.y, (255, 200, 80) if bullet.friendly else (255, 120, 60), 4, 18)
                continue

            if bullet.friendly:
                if self.hit_reactors(bullet) or self.hit_enemies(bullet):
                    continue
                if self.hit_boss(bullet):
                    continue
            else:
                if self.player.rect().colliderect(bullet.rect()):
                    self.damage_player(bullet.damage)
                    self.spawn_particles(bullet.pos.x, bullet.pos.y, (255, 70, 70), 8, 35)
                    continue

            remaining.append(bullet)
        self.bullets = remaining

    def hit_wall(self, rect: pygame.Rect) -> bool:
        return any(rect.colliderect(wall) for wall in self.walls)

    def hit_enemies(self, bullet: Bullet) -> bool:
        for enemy in self.enemies:
            if not enemy.alive:
                continue
            if bullet.rect().colliderect(enemy.rect()):
                enemy.hp -= bullet.damage
                self.spawn_particles(enemy.pos.x, enemy.pos.y, (160, 220, 255), 10, 40)
                if enemy.hp <= 0:
                    self.kill_enemy(enemy)
                return True
        return False

    def hit_boss(self, bullet: Bullet) -> bool:
        if not self.boss_spawned or not self.boss.alive:
            return False
        if bullet.rect().colliderect(self.boss.rect()):
            self.boss.hp -= bullet.damage
            self.spawn_particles(self.boss.pos.x, self.boss.pos.y, (255, 120, 255), 14, 60)
            if self.boss.hp <= 0:
                self.kill_boss()
            return True
        return False

    def hit_reactors(self, bullet: Bullet) -> bool:
        for reactor in self.reactors:
            if not reactor.active:
                continue
            if bullet.rect().colliderect(reactor.rect):
                reactor.hp -= bullet.damage
                reactor.pulse = 0.18
                self.spawn_particles(reactor.rect.centerx, reactor.rect.centery, (255, 210, 70), 8, 30)
                if reactor.hp <= 0:
                    self.destroy_reactor(reactor)
                return True
        return False

    def destroy_reactor(self, reactor: Reactor) -> None:
        reactor.active = False
        self.district_liberated[reactor.district] = True
        self.player.scrap += 8
        self.player.special_charges += 1
        self.player.tech_level = min(3, self.player.tech_level + 1)
        self.spawn_drop("scrap", reactor.rect.center, 4)
        self.spawn_drop("life", reactor.rect.center, 1)
        self.spawn_drop("special", reactor.rect.center, 1)
        count = sum(1 for r in self.reactors if not r.active)
        self.set_message(f"Reator destruido: bairro {reactor.district + 1} liberado ({count}/4).", 3.0)
        self.spawn_reinforcements()
        if count >= 4 and not self.boss_spawned:
            self.spawn_boss()

    def spawn_reinforcements(self) -> None:
        active_positions = [r.rect.center for r in self.reactors if r.active]
        if not active_positions:
            active_positions = [(WORLD_WIDTH / 2, WORLD_HEIGHT / 2)]
        for _ in range(3):
            base = pygame.Vector2(random.choice(active_positions))
            offset = pygame.Vector2(random.randint(-100, 100), random.randint(-100, 100))
            pos = self.find_open_point((base + offset).x, (base + offset).y, 24)
            kind = random.choice(["patrol", "patrol", "shooter", "guardian"])
            district = self.district_index_for(pos)
            self.enemies.append(self.create_enemy(kind, pos.x, pos.y, district))

    def spawn_boss(self) -> None:
        self.boss_spawned = True
        self.boss.pos = self.find_open_point(1460, 940, self.boss.radius)
        self.boss.home = self.boss.pos.copy()
        self.boss.hp = self.boss.max_hp
        self.boss.fire_timer = 1.2
        self.set_message("A IA central entrou em campo.", 4.0)

    def kill_enemy(self, enemy: Enemy) -> None:
        enemy.hp = 0
        self.player.scrap += 1 if enemy.kind != "guardian" else 2
        drop_kind = random.choices(["scrap", "life", "special"], weights=[70, 20, 10])[0]
        self.spawn_drop(drop_kind, enemy.pos, 1)
        self.spawn_particles(enemy.pos.x, enemy.pos.y, (200, 220, 255), 16, 50)

    def kill_boss(self) -> None:
        self.boss.hp = 0
        self.boss_defeated = True
        self.extractor_active = True
        self.spawn_drop("scrap", self.boss.pos, 10)
        self.spawn_drop("life", self.boss.pos, 2)
        self.spawn_drop("special", self.boss.pos, 2)
        self.spawn_particles(self.boss.pos.x, self.boss.pos.y, (255, 80, 255), 40, 120)
        self.set_message("Nucleo central destruido. Alcance a saida.", 4.0)

    def spawn_drop(self, kind: str, center: Iterable[float] | pygame.Vector2, amount: int) -> None:
        pos = pygame.Vector2(center)
        if kind == "scrap":
            offset = pygame.Vector2(random.randint(-18, 18), random.randint(-18, 18))
        else:
            offset = pygame.Vector2(random.randint(-10, 10), random.randint(-10, 10))
        final_pos = self.find_open_point((pos + offset).x, (pos + offset).y, 12)
        self.drops.append(Drop(kind=kind, pos=final_pos, amount=amount))

    def update_drops(self, dt: float) -> None:
        remaining: list[Drop] = []
        for drop in self.drops:
            drop.ttl -= dt
            drop.pulse += dt * 4
            if drop.ttl <= 0:
                continue
            if self.player.rect().inflate(18, 18).colliderect(drop.rect):
                if drop.kind == "scrap":
                    self.player.scrap += drop.amount
                elif drop.kind == "life":
                    self.player.hp = min(self.player.max_hp, self.player.hp + 25 * drop.amount)
                elif drop.kind == "special":
                    self.player.special_charges += drop.amount
                self.spawn_particles(drop.pos.x, drop.pos.y, (255, 230, 120), 8, 20)
                continue
            remaining.append(drop)
        self.drops = remaining

    def update_particles(self, dt: float) -> None:
        remaining: list[Particle] = []
        for particle in self.particles:
            particle.life -= dt
            particle.pos += particle.vel * dt
            particle.vel *= 0.94
            if particle.life > 0:
                remaining.append(particle)
        self.particles = remaining

    def update_turrets(self, dt: float) -> None:
        remaining: list[Turret] = []
        for turret in self.turrets:
            turret.life -= dt
            turret.fire_timer = max(0.0, turret.fire_timer - dt)
            target = self.find_turret_target(turret)
            if target is not None and turret.fire_timer <= 0:
                direction = (target.pos - turret.pos)
                if direction.length_squared() > 0:
                    direction = direction.normalize()
                    self.bullets.append(
                        Bullet(
                            pos=turret.pos + direction * 20,
                            vel=direction * 520,
                            damage=turret.damage,
                            friendly=True,
                            life=1.2,
                            radius=4,
                        )
                    )
                    turret.fire_timer = turret.fire_delay
                    self.spawn_particles(turret.pos.x, turret.pos.y, (120, 220, 255), 4, 24)
            if turret.life > 0:
                remaining.append(turret)
        self.turrets = remaining

    def find_turret_target(self, turret: Turret) -> Enemy | None:
        best: Enemy | None = None
        best_dist = turret.range
        for enemy in self.enemies:
            if not enemy.alive:
                continue
            dist = distance(turret.pos, enemy.pos)
            if dist < best_dist:
                best = enemy
                best_dist = dist
        if self.boss_spawned and self.boss.alive:
            boss_dist = distance(turret.pos, self.boss.pos)
            if boss_dist < best_dist:
                return self.boss
        return best

    def update_mines(self, dt: float) -> None:
        remaining: list[Mine] = []
        for mine in self.mines:
            mine.life -= dt
            if mine.life <= 0:
                continue
            if mine.armed:
                hit = False
                for enemy in self.enemies:
                    if not enemy.alive:
                        continue
                    if distance(mine.pos, enemy.pos) <= mine.radius + enemy.radius:
                        enemy.hp -= mine.damage
                        hit = True
                        if enemy.hp <= 0:
                            self.kill_enemy(enemy)
                        break
                if not hit and self.boss_spawned and self.boss.alive and distance(mine.pos, self.boss.pos) <= mine.radius + self.boss.radius:
                    self.boss.hp -= mine.damage
                    hit = True
                    if self.boss.hp <= 0:
                        self.kill_boss()
                if hit:
                    mine.life = 0
                    self.spawn_particles(mine.pos.x, mine.pos.y, (255, 200, 80), 18, 55)
                    continue
            remaining.append(mine)
        self.mines = remaining

    def spawn_particles(self, x: float, y: float, color: tuple[int, int, int], amount: int, strength: float) -> None:
        origin = pygame.Vector2(x, y)
        for _ in range(amount):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(strength * 0.35, strength)
            vel = pygame.Vector2(math.cos(angle), math.sin(angle)) * speed
            self.particles.append(
                Particle(
                    pos=origin.copy(),
                    vel=vel,
                    color=color,
                    life=random.uniform(0.25, 0.85),
                    radius=random.randint(2, 5),
                )
            )

    def update_reactors(self, dt: float) -> None:
        for reactor in self.reactors:
            reactor.pulse = max(0.0, reactor.pulse - dt)
            if reactor.active and distance(self.player.pos, pygame.Vector2(reactor.rect.center)) < 54:
                reactor.pulse = max(reactor.pulse, 0.15)

    def update_spawns(self, dt: float) -> None:
        self.wave_timer -= dt
        self.drop_timer -= dt

        if self.wave_timer <= 0:
            self.wave_timer = 12.0
            if len([e for e in self.enemies if e.alive]) < 16:
                self.spawn_wave()

        if self.drop_timer <= 0:
            self.drop_timer = random.uniform(18.0, 26.0)
            self.spawn_event_drop()

    def spawn_wave(self) -> None:
        active_reactors = [r for r in self.reactors if r.active]
        if active_reactors:
            chosen = random.choice(active_reactors)
            district = chosen.district
            center = pygame.Vector2(chosen.rect.center)
        else:
            district = random.randint(0, 3)
            center = pygame.Vector2(WORLD_WIDTH / 2, WORLD_HEIGHT / 2)

        for _ in range(random.randint(2, 4)):
            offset = pygame.Vector2(random.randint(-140, 140), random.randint(-140, 140))
            pos = self.find_open_point((center + offset).x, (center + offset).y, 24)
            kind = random.choice(["patrol", "shooter", "guardian"])
            district = self.district_index_for(pos)
            self.enemies.append(self.create_enemy(kind, pos.x, pos.y, district))

        self.set_message("Ataque mecanico detectado.", 2.5)

    def district_index_for(self, pos: pygame.Vector2) -> int:
        if pos.x < WORLD_WIDTH / 2 and pos.y < WORLD_HEIGHT / 2:
            return 1 if self.district_liberated[0] else 2
        if pos.x >= WORLD_WIDTH / 2 and pos.y < WORLD_HEIGHT / 2:
            return 1 if self.district_liberated[1] else 2
        if pos.x < WORLD_WIDTH / 2 and pos.y >= WORLD_HEIGHT / 2:
            return 1 if self.district_liberated[2] else 2
        return 1 if self.district_liberated[3] else 2

    def spawn_event_drop(self) -> None:
        choice = random.choices(["scrap", "life", "special"], weights=[60, 25, 15])[0]
        x = clamp(self.player.pos.x + random.randint(-220, 220), 120, WORLD_WIDTH - 120)
        y = clamp(self.player.pos.y + random.randint(-220, 220), 120, WORLD_HEIGHT - 120)
        self.spawn_drop(choice, (x, y), 1 if choice != "scrap" else random.randint(2, 4))
        texts = {
            "scrap": "Queda de sucata localizada.",
            "life": "Kit de reparo caiu na area.",
            "special": "Carga especial disponivel.",
        }
        self.set_message(texts[choice], 2.2)

    def update_camera(self, dt: float) -> None:
        target = self.player.pos - pygame.Vector2(WIDTH / 2, HEIGHT / 2)
        self.camera += (target - self.camera) * min(1.0, 5.5 * dt)
        self.camera.x = clamp(self.camera.x, 0, WORLD_WIDTH - WIDTH)
        self.camera.y = clamp(self.camera.y, 0, WORLD_HEIGHT - HEIGHT)

    def check_victory_conditions(self) -> None:
        if self.boss_defeated and self.extractor_active and self.player.rect().colliderect(self.extractor):
            self.victory = True
            self.state = "victory"
            self.set_message("A cidade foi recuperada.", 999.0)

    def check_game_over(self) -> None:
        if self.player.hp <= 0 and self.state == "play":
            self.game_over = True
            self.state = "game_over"
            if self.message_timer <= 0 or self.message == "":
                self.set_message("Fim de jogo. Pressione R para tentar novamente.", 999.0)

    def draw(self) -> None:
        if self.state == "menu":
            self.draw_menu()
            return

        self.draw_world()
        self.draw_entities()
        self.draw_hud()
        self.draw_overlays()

    def draw_menu(self) -> None:
        if self.images["cover"] is not None:
            self.screen.blit(self.images["cover"], (0, 0))
        elif self.images["background"] is not None:
            self.screen.blit(self.images["background"], (0, 0))
        else:
            self.screen.fill((20, 28, 40))

        tint = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        tint.fill((8, 10, 16, 120))
        self.screen.blit(tint, (0, 0))

        title = self.font_title.render("Cidade Sob Invasao", True, (120, 220, 255))
        subtitle = self.font_big.render("Exploracao, combate e crafting", True, (245, 245, 245))
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 80))
        self.screen.blit(subtitle, (WIDTH // 2 - subtitle.get_width() // 2, 140))

        lines = [
            "WASD ou setas para mover",
            "Mouse ou ESPACO para disparar",
            "E para especial, C perto da oficina para craftar",
            "SHIFT ativa impulso se tiver carga",
            "Z para torreta e X para mina",
            "Destrua os 4 reatores, derrube o boss e alcance a saida",
            "Pressione ENTER para comecar",
        ]
        y = 260
        for line in lines:
            text = self.font.render(line, True, (230, 235, 240))
            self.screen.blit(text, (WIDTH // 2 - text.get_width() // 2, y))
            y += 34

        if self.images["objective"] is not None:
            self.screen.blit(self.images["objective"], (WIDTH // 2 - 26, 520))

    def draw_world(self) -> None:
        if self.images["background"] is not None:
            self.screen.blit(self.images["background"], (-int(self.camera.x * 0.12), -int(self.camera.y * 0.08)))
        else:
            self.screen.fill((30, 40, 28))

        self.draw_cyber_city_overlay()
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 14, 18, 40))
        self.screen.blit(overlay, (0, 0))

        self.draw_tile_layer()
        self.draw_walls()
        self.draw_map_bounds()
        self.draw_workbench()
        self.draw_reactors()
        self.draw_extractor()

    def draw_cyber_city_overlay(self) -> None:
        skyline_scroll = self.camera.x * 0.35
        horizon = HEIGHT - 220
        buildings = [
            (0.00, 0.12, 170, 85, (34, 42, 58)),
            (0.08, 0.18, 220, 120, (28, 38, 54)),
            (0.19, 0.10, 150, 100, (42, 50, 68)),
            (0.33, 0.22, 260, 145, (31, 44, 66)),
            (0.52, 0.14, 190, 110, (44, 52, 74)),
            (0.68, 0.20, 240, 140, (29, 36, 52)),
            (0.83, 0.12, 180, 95, (39, 46, 62)),
        ]
        for index, (x_factor, width_factor, width_px, height_px, color) in enumerate(buildings):
            x = int((WIDTH * x_factor + skyline_scroll * width_factor) % (WIDTH + 240) - 120)
            y = horizon - height_px
            rect = pygame.Rect(x, y, width_px, height_px)
            pygame.draw.rect(self.screen, color, rect)
            pygame.draw.rect(self.screen, (10, 12, 18), rect, 2)
            window_color = (70, 220, 255) if index % 2 == 0 else (255, 110, 220)
            for wy in range(y + 16, y + height_px - 10, 18):
                for wx in range(x + 12, x + width_px - 10, 22):
                    if (wx // 22 + wy // 18 + index) % 3 != 0:
                        pygame.draw.rect(self.screen, window_color, (wx, wy, 8, 10))
            antenna_x = x + width_px // 2
            pygame.draw.line(self.screen, (110, 220, 255), (antenna_x, y), (antenna_x, y - 18 - index * 2), 2)
            pygame.draw.circle(self.screen, (255, 90, 180), (antenna_x, y - 18 - index * 2), 3)

        road = pygame.Rect(0, HEIGHT - 160, WIDTH, 160)
        pygame.draw.rect(self.screen, (18, 18, 24), road)
        pygame.draw.rect(self.screen, (255, 90, 180), (0, HEIGHT - 162, WIDTH, 2))
        for i in range(0, WIDTH, 60):
            pygame.draw.rect(self.screen, (55, 60, 72), (i, HEIGHT - 85, 34, 6))

        neon_fog = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for i, alpha in enumerate((24, 18, 12)):
            pygame.draw.ellipse(
                neon_fog,
                (60, 190, 255, alpha),
                (80 - i * 60, 110 + i * 30, WIDTH - 160 + i * 120, 180),
            )
        self.screen.blit(neon_fog, (0, 0))

    def draw_tile_layer(self) -> None:
        if self.images["tile_mid"] is None:
            return

        start_x = max(0, int(self.camera.x // TILE) - 1)
        end_x = min(WORLD_WIDTH // TILE + 1, int((self.camera.x + WIDTH) // TILE) + 2)
        start_y = max(0, int(self.camera.y // TILE) - 1)
        end_y = min(WORLD_HEIGHT // TILE + 1, int((self.camera.y + HEIGHT) // TILE) + 2)

        for ty in range(start_y, end_y):
            for tx in range(start_x, end_x):
                image = self.images["tile_top"] if ty == 0 else self.images["tile_mid"]
                if image is None:
                    continue
                self.screen.blit(image, (tx * TILE - self.camera.x, ty * TILE - self.camera.y))

    def draw_walls(self) -> None:
        for wall in self.walls[4:]:
            rect = pygame.Rect(wall.x - self.camera.x, wall.y - self.camera.y, wall.w, wall.h)
            pygame.draw.rect(self.screen, (55, 60, 70), rect, border_radius=8)
            pygame.draw.rect(self.screen, (25, 28, 35), rect, 2, border_radius=8)

    def draw_map_bounds(self) -> None:
        left = -self.camera.x
        top = -self.camera.y
        bounds = pygame.Rect(left, top, WORLD_WIDTH, WORLD_HEIGHT)
        pygame.draw.rect(self.screen, (60, 150, 255), bounds, 4)

    def draw_workbench(self) -> None:
        rect = pygame.Rect(self.workbench.x - self.camera.x, self.workbench.y - self.camera.y, self.workbench.w, self.workbench.h)
        if self.images["workbench"] is not None:
            self.screen.blit(self.images["workbench"], rect)
        else:
            pygame.draw.rect(self.screen, (82, 52, 22), rect, border_radius=10)
            pygame.draw.rect(self.screen, (255, 210, 100), rect, 2, border_radius=10)
        label = self.font_small.render("OFICINA", True, (255, 235, 120))
        self.screen.blit(label, (rect.centerx - label.get_width() // 2, rect.y - 18))

    def draw_reactors(self) -> None:
        for reactor in self.reactors:
            center = pygame.Vector2(reactor.rect.center) - self.camera
            pulse = math.sin(reactor.pulse * 18.0) * 4 if reactor.pulse > 0 else 0
            if reactor.active:
                glow = (255, 90, 90) if reactor.hp < reactor.max_hp * 0.4 else (255, 180, 60)
                pygame.draw.circle(self.screen, glow, (int(center.x), int(center.y)), 34 + int(pulse), 2)
                pygame.draw.rect(self.screen, (200, 80, 80), reactor.rect.move(-self.camera.x, -self.camera.y))
                self.draw_objective_marker(center)
                bar_w = 64
                bar_h = 7
                bar_x = int(center.x - bar_w / 2)
                bar_y = int(center.y - 48)
                pygame.draw.rect(self.screen, (20, 20, 20), (bar_x, bar_y, bar_w, bar_h))
                pygame.draw.rect(self.screen, (255, 90, 90), (bar_x, bar_y, int(bar_w * reactor.hp / reactor.max_hp), bar_h))
            else:
                pygame.draw.circle(self.screen, (90, 20, 20), (int(center.x), int(center.y)), 20)

    def draw_extractor(self) -> None:
        if not self.extractor_active:
            return
        rect = pygame.Rect(self.extractor.x - self.camera.x, self.extractor.y - self.camera.y, self.extractor.w, self.extractor.h)
        pygame.draw.rect(self.screen, (70, 150, 240), rect, border_radius=10)
        pygame.draw.rect(self.screen, (220, 245, 255), rect, 2, border_radius=10)
        self.draw_objective_marker(pygame.Vector2(rect.center))
        text = self.font_small.render("SAIDA", True, (230, 245, 255))
        self.screen.blit(text, (rect.centerx - text.get_width() // 2, rect.bottom + 6))

    def draw_objective_marker(self, center: pygame.Vector2) -> None:
        sprite = self.images["objective"]
        if sprite is None:
            return

        sprite_rect = sprite.get_rect(center=(int(center.x), int(center.y)))
        world_rect = pygame.Rect(sprite_rect.x + self.camera.x, sprite_rect.y + self.camera.y, sprite_rect.w, sprite_rect.h)

        # Se o marcador cair dentro de um objeto sólido, tenta empurrá-lo para uma zona livre.
        if self.hit_wall(world_rect) or world_rect.colliderect(self.workbench) or world_rect.colliderect(self.extractor):
            for spread in range(18, 150, 18):
                for angle_deg in range(0, 360, 30):
                    angle = math.radians(angle_deg)
                    offset = pygame.Vector2(math.cos(angle), math.sin(angle)) * spread
                    candidate = center + offset
                    candidate_rect = sprite.get_rect(center=(int(candidate.x), int(candidate.y)))
                    candidate_world_rect = pygame.Rect(
                        candidate_rect.x + self.camera.x,
                        candidate_rect.y + self.camera.y,
                        candidate_rect.w,
                        candidate_rect.h,
                    )
                    if not self.hit_wall(candidate_world_rect) and not candidate_world_rect.colliderect(self.workbench) and not candidate_world_rect.colliderect(self.extractor):
                        sprite_rect = candidate_rect
                        break
                else:
                    continue
                break
            else:
                return

        self.screen.blit(sprite, sprite_rect)

    def draw_entities(self) -> None:
        for drop in self.drops:
            self.draw_drop(drop)
        for bullet in self.bullets:
            self.draw_bullet(bullet)
        for particle in self.particles:
            self.draw_particle(particle)
        for mine in self.mines:
            self.draw_mine(mine)
        for turret in self.turrets:
            self.draw_turret(turret)
        for enemy in self.enemies:
            if enemy.alive:
                self.draw_enemy(enemy)
        if self.boss_spawned and self.boss.alive:
            self.draw_boss(self.boss)
        self.draw_player()

    def draw_drop(self, drop: Drop) -> None:
        pos = drop.pos - self.camera
        bob = math.sin(drop.pulse) * 3
        if drop.kind == "scrap":
            x = int(pos.x)
            y = int(pos.y + bob)
            pygame.draw.polygon(
                self.screen,
                (130, 140, 150),
                [(x - 10, y + 4), (x - 2, y - 10), (x + 11, y - 2), (x + 6, y + 10)],
            )
            pygame.draw.polygon(
                self.screen,
                (80, 88, 96),
                [(x - 8, y + 2), (x + 2, y - 8), (x + 12, y), (x + 4, y + 11)],
                2,
            )
            pygame.draw.circle(self.screen, (60, 65, 72), (x - 2, y + 1), 2)
            pygame.draw.circle(self.screen, (60, 65, 72), (x + 6, y - 1), 2)
        else:
            if drop.kind == "life" and self.images["life"] is not None:
                img = self.images["life"]
            elif drop.kind == "special" and self.images["special"] is not None:
                img = self.images["special"]
            else:
                img = None
            if img is not None:
                rect = img.get_rect(center=(int(pos.x), int(pos.y + bob)))
                self.screen.blit(img, rect)
            else:
                color = {"life": (240, 90, 90), "special": (110, 255, 220)}[drop.kind]
                pygame.draw.circle(self.screen, color, (int(pos.x), int(pos.y + bob)), 10)

    def draw_bullet(self, bullet: Bullet) -> None:
        pos = bullet.pos - self.camera
        color = (255, 220, 80) if bullet.friendly else (255, 120, 70)
        pygame.draw.circle(self.screen, color, (int(pos.x), int(pos.y)), bullet.radius)
        pygame.draw.circle(self.screen, (255, 255, 255), (int(pos.x), int(pos.y)), max(1, bullet.radius // 3))

    def draw_turret(self, turret: Turret) -> None:
        pos = turret.pos - self.camera
        body = pygame.Rect(int(pos.x) - 12, int(pos.y) - 12, 24, 24)
        pygame.draw.rect(self.screen, (40, 90, 130), body, border_radius=6)
        pygame.draw.rect(self.screen, (120, 220, 255), body, 2, border_radius=6)
        pygame.draw.circle(self.screen, (160, 240, 255), (int(pos.x), int(pos.y)), 4)

    def draw_mine(self, mine: Mine) -> None:
        pos = mine.pos - self.camera
        pygame.draw.circle(self.screen, (90, 90, 90), (int(pos.x), int(pos.y)), mine.radius)
        pygame.draw.circle(self.screen, (255, 200, 80), (int(pos.x), int(pos.y)), mine.radius, 2)
        pygame.draw.line(self.screen, (255, 200, 80), (int(pos.x - 8), int(pos.y)), (int(pos.x + 8), int(pos.y)), 2)
        pygame.draw.line(self.screen, (255, 200, 80), (int(pos.x), int(pos.y - 8)), (int(pos.x), int(pos.y + 8)), 2)

    def draw_particle(self, particle: Particle) -> None:
        pos = particle.pos - self.camera
        alpha = int(255 * clamp(particle.life / 0.85, 0.0, 1.0))
        surf = pygame.Surface((particle.radius * 2, particle.radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*particle.color, alpha), (particle.radius, particle.radius), particle.radius)
        self.screen.blit(surf, (pos.x - particle.radius, pos.y - particle.radius))

    def draw_enemy(self, enemy: Enemy) -> None:
        pos = enemy.pos - self.camera
        body = pygame.Rect(int(pos.x) - enemy.radius, int(pos.y) - enemy.radius, enemy.radius * 2, enemy.radius * 2)
        # Corpo principal do robô.
        chassis_color = (52, 58, 72)
        trim_color = (170, 184, 198)
        accent_color = (90, 220, 255) if enemy.kind != "shooter" else (255, 175, 70)
        eye_color = (255, 70, 70)

        pygame.draw.rect(self.screen, chassis_color, body, border_radius=7)
        pygame.draw.rect(self.screen, trim_color, body, 2, border_radius=7)
        pygame.draw.rect(self.screen, (78, 86, 100), (body.x + 5, body.y + 7, body.w - 10, 8), border_radius=4)

        eye_y = body.y + body.h // 2 - 4
        pygame.draw.circle(self.screen, eye_color, (body.centerx - 7, eye_y), 3)
        pygame.draw.circle(self.screen, eye_color, (body.centerx + 7, eye_y), 3)
        pygame.draw.rect(self.screen, accent_color, (body.centerx - 5, body.y + 9, 10, 4), border_radius=2)

        # Braços e pernas mecânicas.
        pygame.draw.line(self.screen, trim_color, (body.left - 5, body.centery - 2), (body.left - 14, body.centery - 8), 3)
        pygame.draw.line(self.screen, trim_color, (body.right + 5, body.centery - 2), (body.right + 14, body.centery - 8), 3)
        pygame.draw.line(self.screen, (38, 42, 50), (body.x + 8, body.bottom - 1), (body.x + 6, body.bottom + 12), 4)
        pygame.draw.line(self.screen, (38, 42, 50), (body.right - 8, body.bottom - 1), (body.right - 6, body.bottom + 12), 4)
        pygame.draw.circle(self.screen, accent_color, (body.x + 5, body.bottom + 10), 3)
        pygame.draw.circle(self.screen, accent_color, (body.right - 5, body.bottom + 10), 3)

        if enemy.kind == "shooter":
            pygame.draw.rect(self.screen, (255, 175, 70), (body.centerx - 3, body.bottom - 10, 6, 10))
            pygame.draw.line(self.screen, (255, 175, 70), (body.centerx, body.top - 6), (body.centerx, body.top - 18), 2)
        elif enemy.kind == "guardian":
            pygame.draw.rect(self.screen, (120, 130, 145), (body.x + 2, body.y + 2, body.w - 4, body.h - 4), 2, border_radius=6)
            pygame.draw.circle(self.screen, (80, 220, 255), (body.centerx, body.centery + 5), 5)
            pygame.draw.circle(self.screen, (80, 220, 255), (body.centerx, body.centery - 10), 4)
        else:
            pygame.draw.line(self.screen, trim_color, (body.left - 4, body.centery), (body.left - 10, body.centery - 2), 2)
            pygame.draw.line(self.screen, trim_color, (body.right + 4, body.centery), (body.right + 10, body.centery - 2), 2)

        pygame.draw.rect(self.screen, (25, 28, 35), (body.x + 2, body.bottom - 4, body.w - 4, 6), border_radius=2)
        self.draw_life_bar(pos, enemy.hp, enemy.max_hp, enemy.radius, (255, 80, 80))

    def draw_boss(self, boss: Enemy) -> None:
        pos = boss.pos - self.camera
        body = pygame.Rect(int(pos.x) - boss.radius, int(pos.y) - boss.radius, boss.radius * 2, boss.radius * 2)
        pygame.draw.rect(self.screen, (40, 26, 58), body, border_radius=10)
        pygame.draw.rect(self.screen, (220, 110, 255), body, 3, border_radius=10)
        pygame.draw.rect(self.screen, (96, 58, 134), (body.x + 8, body.y + 10, body.w - 16, 14), border_radius=6)
        pygame.draw.rect(self.screen, (72, 80, 96), (body.x + 14, body.y + 36, body.w - 28, body.h - 48), border_radius=8)
        pygame.draw.circle(self.screen, (255, 120, 255), (body.centerx, body.centery - 8), 8)
        pygame.draw.circle(self.screen, (80, 220, 255), (body.centerx, body.centery - 8), 3)
        pygame.draw.rect(self.screen, (120, 70, 150), (body.centerx - 6, body.bottom - 18, 12, 18))
        pygame.draw.line(self.screen, (220, 110, 255), (body.left - 10, body.centery), (body.left - 26, body.centery - 8), 4)
        pygame.draw.line(self.screen, (220, 110, 255), (body.right + 10, body.centery), (body.right + 26, body.centery - 8), 4)
        pygame.draw.circle(self.screen, (255, 120, 255), (body.left + 8, body.top - 6), 4)
        pygame.draw.circle(self.screen, (255, 120, 255), (body.right - 8, body.top - 6), 4)
        self.draw_life_bar(pos, boss.hp, boss.max_hp, boss.radius, (255, 120, 255), width=110, offset=-62)

    def draw_player(self) -> None:
        pos = self.player.pos - self.camera
        if self.player.invuln > 0 and int(self.player.invuln * 20) % 2 == 0:
            return

        px, py = int(pos.x), int(pos.y)
        skin = (238, 193, 144)
        shirt = (40, 120, 210)
        pants = (34, 34, 42)

        head = pygame.Rect(px - 10, py - 25, 20, 20)
        torso = pygame.Rect(px - 12, py - 5, 24, 27)
        pygame.draw.ellipse(self.screen, skin, head)
        pygame.draw.rect(self.screen, shirt, torso, border_radius=6)
        pygame.draw.line(self.screen, skin, (px - 12, py + 2), (px - 26, py + 11), 4)
        pygame.draw.line(self.screen, skin, (px + 12, py + 2), (px + 26, py + 11), 4)
        pygame.draw.line(self.screen, skin, (px - 8, py + 21), (px - 10, py + 35), 4)
        pygame.draw.line(self.screen, skin, (px + 8, py + 21), (px + 10, py + 35), 4)
        pygame.draw.line(self.screen, pants, (px - 8, py + 21), (px - 10, py + 35), 6)
        pygame.draw.line(self.screen, pants, (px + 8, py + 21), (px + 10, py + 35), 6)
        pygame.draw.circle(self.screen, (40, 35, 35), (px - 4, py - 17), 2)
        pygame.draw.circle(self.screen, (40, 35, 35), (px + 4, py - 17), 2)
        pygame.draw.arc(self.screen, (160, 70, 70), (px - 5, py - 13, 10, 8), math.pi * 0.1, math.pi - 0.1, 1)

        for i in range(self.player.tech_level):
            off = 18 + i * 5
            pygame.draw.circle(self.screen, (120, 220, 255), (int(pos.x + off), int(pos.y - 12)), 3)
            pygame.draw.circle(self.screen, (120, 220, 255), (int(pos.x - off), int(pos.y - 12)), 3)

        weapon = self.images["weapon"]
        if weapon is not None:
            angle = -math.degrees(math.atan2(self.player.facing.y, self.player.facing.x))
            rotated = pygame.transform.rotate(weapon, angle)
            offset = pygame.Vector2(self.player.facing) * 18
            rect = rotated.get_rect(center=(int(pos.x + offset.x), int(pos.y + offset.y)))
            self.screen.blit(rotated, rect)

    def draw_life_bar(
        self,
        pos: pygame.Vector2,
        hp: int,
        max_hp: int,
        radius: int,
        color: tuple[int, int, int],
        width: int = 48,
        offset: int = -36,
    ) -> None:
        x = int(pos.x - width / 2)
        y = int(pos.y + offset)
        pygame.draw.rect(self.screen, (18, 18, 18), (x, y, width, 6))
        pygame.draw.rect(self.screen, color, (x, y, int(width * hp / max_hp), 6))

    def draw_hud(self) -> None:
        pygame.draw.rect(self.screen, (8, 10, 16), (0, 0, WIDTH, 94))
        pygame.draw.line(self.screen, (110, 220, 255), (0, 94), (WIDTH, 94), 2)

        title = self.font_big.render("Cidade Sob Invasao", True, (120, 220, 255))
        self.screen.blit(title, (18, 12))

        district = sum(1 for reactor in self.reactors if not reactor.active)
        hud_line = f"Bairros libertados: {district}/4   Vida: {self.player.hp}/{self.player.max_hp}   Dano: {self.player.damage}"
        text = self.font.render(hud_line, True, (240, 245, 250))
        self.screen.blit(text, (18, 52))

        scrap_icon_x = 420
        self.draw_icon(self.images["scrap"], scrap_icon_x, 44)
        self.screen.blit(self.font.render(str(self.player.scrap), True, (255, 220, 80)), (scrap_icon_x + 30, 46))

        life_icon_x = 515
        self.draw_icon(self.images["life"], life_icon_x, 44)
        self.screen.blit(self.font.render(str(self.player.max_hp), True, (255, 180, 180)), (life_icon_x + 30, 46))

        special_icon_x = 615
        self.draw_icon(self.images["special"], special_icon_x, 44)
        self.screen.blit(self.font.render(str(self.player.special_charges), True, (120, 255, 220)), (special_icon_x + 30, 46))

        support_text = self.font_small.render(
            f"Torreta {self.player.turret_charges}   Mina {self.player.mine_charges}   Nivel tech {self.player.tech_level}",
            True,
            (200, 220, 240),
        )
        self.screen.blit(support_text, (18, 74))

        if self.player_in_workbench_range():
            tip = self.font_small.render("C para abrir a oficina", True, (255, 235, 120))
            self.screen.blit(tip, (WIDTH - tip.get_width() - 18, 16))

    def draw_icon(self, image: pygame.Surface | None, x: int, y: int) -> None:
        if image is not None:
            self.screen.blit(image, (x, y))
        else:
            pygame.draw.rect(self.screen, (255, 255, 255), (x, y, 24, 24), 1)

    def draw_overlays(self) -> None:
        if self.message_timer > 0 and self.message:
            box = pygame.Surface((WIDTH, 70), pygame.SRCALPHA)
            box.fill((0, 0, 0, 140))
            self.screen.blit(box, (0, HEIGHT - 80))
            text = self.font.render(self.message, True, (245, 245, 245))
            self.screen.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT - 53))

        if self.crafting_open and self.state == "play":
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 170))
            self.screen.blit(overlay, (0, 0))
            panel = pygame.Rect(120, 110, WIDTH - 240, HEIGHT - 220)
            pygame.draw.rect(self.screen, (20, 28, 40), panel, border_radius=14)
            pygame.draw.rect(self.screen, (120, 220, 255), panel, 2, border_radius=14)
            title = self.font_title.render("OFICINA", True, (120, 220, 255))
            self.screen.blit(title, (panel.centerx - title.get_width() // 2, panel.y + 20))

            lines = [
                f"Sucata disponivel: {self.player.scrap}",
                "1 - +Dano  (8 sucata)",
                "2 - +Cadencia de tiro  (8 sucata)",
                "3 - +Vida maxima e cura  (6 sucata)",
                "4 - +Carga especial  (10 sucata)",
                "5 - +Impulso de movimento  (10 sucata)",
                "6 - +Torreta  (12 sucata)",
                "7 - +Mina  (8 sucata)",
                "C - fechar oficina",
                "Z - colocar torreta, X - colocar mina",
            ]
            y = panel.y + 110
            for line in lines:
                text = self.font.render(line, True, (240, 245, 250))
                self.screen.blit(text, (panel.x + 40, y))
                y += 34

        if self.state == "game_over":
            self.draw_center_banner("Fim de jogo", "Pressione R para reiniciar")
        elif self.state == "victory":
            self.draw_center_banner("Vitoria", "Pressione R para jogar outra vez")

    def draw_center_banner(self, title: str, subtitle: str) -> None:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))
        panel = pygame.Rect(180, 220, WIDTH - 360, 220)
        pygame.draw.rect(self.screen, (18, 24, 36), panel, border_radius=16)
        pygame.draw.rect(self.screen, (120, 220, 255), panel, 2, border_radius=16)
        title_surf = self.font_title.render(title, True, (120, 220, 255))
        sub_surf = self.font_big.render(subtitle, True, (240, 245, 250))
        self.screen.blit(title_surf, (panel.centerx - title_surf.get_width() // 2, panel.y + 50))
        self.screen.blit(sub_surf, (panel.centerx - sub_surf.get_width() // 2, panel.y + 125))


if __name__ == "__main__":
    Game().run()
