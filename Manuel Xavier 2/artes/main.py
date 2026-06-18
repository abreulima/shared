from __future__ import annotations

from pathlib import Path
import tkinter as tk


WIDTH = 900
HEIGHT = 540
FPS = 60
GRAVITY = 0.75
MOVE_SPEED = 5.2
JUMP_SPEED = -14.2
PLAYER_SIZE = 48
ENEMY_SIZE = 44

ROOT = Path(__file__).resolve().parent


class PlatformGame:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Aventura no Castelo")
        self.root.resizable(False, False)

        self.canvas = tk.Canvas(self.root, width=WIDTH, height=HEIGHT, highlightthickness=0)
        self.canvas.pack()

        self.keys: set[str] = set()
        self.images = self.load_images()

        self.root.bind("<KeyPress>", self.on_key_press)
        self.root.bind("<KeyRelease>", self.on_key_release)

        self.reset_game()
        self.tick()

    def load_images(self) -> dict[str, tk.PhotoImage]:
        files = {
            "player": "jogdor.png",
            "enemy": "inimigo.png",
        }
        images: dict[str, tk.PhotoImage] = {}
        for name, filename in files.items():
            path = ROOT / filename
            if not path.exists():
                continue
            try:
                images[name] = tk.PhotoImage(file=path).zoom(2, 2)
            except tk.TclError:
                pass
        return images

    def reset_game(self) -> None:
        self.game_over = False
        self.victory = False
        self.camera_x = 0.0
        self.score = 0
        self.lives = 2
        self.spawn = (62.0, 390.0)
        self.player = {
            "x": self.spawn[0],
            "y": self.spawn[1],
            "w": PLAYER_SIZE,
            "h": PLAYER_SIZE,
            "vx": 0.0,
            "vy": 0.0,
            "on_ground": False,
        }

        self.platforms = [
            (0, 488, 310, 52),
            (430, 450, 150, 28),
            (715, 405, 130, 28),
            (985, 462, 190, 28),
            (1325, 408, 135, 28),
            (1600, 350, 115, 28),
            (1840, 432, 160, 28),
            (2195, 380, 125, 28),
            (2475, 455, 310, 52),
        ]
        self.world_width = 2840
        self.coins = [
            {"x": x, "y": y, "taken": False}
            for x, y in [
                (475, 400),
                (540, 400),
                (760, 355),
                (1015, 410),
                (1130, 410),
                (1375, 358),
                (1645, 300),
                (1970, 380),
                (2240, 330),
                (2535, 405),
                (2640, 405),
            ]
        ]
        self.enemies = [
            {"x": 510.0, "y": 406.0, "vx": 2.4, "left": 430.0, "right": 536.0},
            {"x": 1040.0, "y": 418.0, "vx": 2.8, "left": 985.0, "right": 1130.0},
            {"x": 1365.0, "y": 364.0, "vx": 2.3, "left": 1325.0, "right": 1416.0},
            {"x": 1880.0, "y": 388.0, "vx": 2.7, "left": 1840.0, "right": 1956.0},
            {"x": 2535.0, "y": 411.0, "vx": 3.0, "left": 2475.0, "right": 2736.0},
        ]
        self.goal = {"x": 2745, "y": 373, "w": 36, "h": 82}
        self.clouds = [
            (120, 70, 88),
            (520, 110, 78),
            (940, 75, 92),
            (1370, 125, 74),
            (1880, 85, 86),
            (2390, 115, 80),
        ]

    def on_key_press(self, event: tk.Event) -> None:
        key = event.keysym.lower()
        self.keys.add(key)
        if key == "r" and (self.game_over or self.victory):
            self.reset_game()

    def on_key_release(self, event: tk.Event) -> None:
        self.keys.discard(event.keysym.lower())

    def tick(self) -> None:
        if not self.game_over and not self.victory:
            self.update()
        self.draw()
        self.root.after(int(1000 / FPS), self.tick)

    def update(self) -> None:
        self.handle_input()
        self.move_player()
        self.move_enemies()
        self.collect_coins()
        self.check_enemy_hits()
        self.check_goal()
        self.update_camera()

    def handle_input(self) -> None:
        left = "left" in self.keys or "a" in self.keys
        right = "right" in self.keys or "d" in self.keys
        jump = "space" in self.keys or "up" in self.keys or "w" in self.keys

        self.player["vx"] = 0.0
        if left:
            self.player["vx"] -= MOVE_SPEED
        if right:
            self.player["vx"] += MOVE_SPEED
        if jump and self.player["on_ground"]:
            self.player["vy"] = JUMP_SPEED
            self.player["on_ground"] = False

    def move_player(self) -> None:
        self.player["x"] += self.player["vx"]
        self.player["x"] = max(0, min(self.player["x"], self.world_width - self.player["w"]))

        self.player["vy"] += GRAVITY
        self.player["y"] += self.player["vy"]
        self.player["on_ground"] = False

        player_rect = self.player_rect()
        for platform in self.platforms:
            if not self.rects_overlap(player_rect, platform):
                continue

            px, py, pw, ph = player_rect
            x, y, w, h = platform
            if self.player["vy"] >= 0 and py + ph - self.player["vy"] <= y:
                self.player["y"] = y - self.player["h"]
                self.player["vy"] = 0.0
                self.player["on_ground"] = True
            elif self.player["vy"] < 0 and py - self.player["vy"] >= y + h:
                self.player["y"] = y + h
                self.player["vy"] = 0.0
            elif px + pw / 2 < x + w / 2:
                self.player["x"] = x - self.player["w"]
            else:
                self.player["x"] = x + w
            player_rect = self.player_rect()

        if self.player["y"] > HEIGHT + 80:
            self.lose_life()

    def move_enemies(self) -> None:
        for enemy in self.enemies:
            enemy["x"] += enemy["vx"]
            if enemy["x"] <= enemy["left"] or enemy["x"] + ENEMY_SIZE >= enemy["right"]:
                enemy["vx"] *= -1
                enemy["x"] = max(enemy["left"], min(enemy["x"], enemy["right"] - ENEMY_SIZE))

    def collect_coins(self) -> None:
        player_rect = self.player_rect()
        for coin in self.coins:
            if coin["taken"]:
                continue
            coin_rect = (coin["x"], coin["y"], 22, 22)
            if self.rects_overlap(player_rect, coin_rect):
                coin["taken"] = True
                self.score += 1

    def check_enemy_hits(self) -> None:
        player_rect = self.player_rect()
        for enemy in self.enemies[:]:
            enemy_rect = (enemy["x"], enemy["y"], ENEMY_SIZE, ENEMY_SIZE)
            if not self.rects_overlap(player_rect, enemy_rect):
                continue

            player_bottom = self.player["y"] + self.player["h"]
            stomped = self.player["vy"] > 3 and player_bottom - enemy["y"] < ENEMY_SIZE * 0.55
            if stomped:
                self.enemies.remove(enemy)
                self.player["vy"] = JUMP_SPEED * 0.62
            else:
                self.lose_life()
            break

    def check_goal(self) -> None:
        goal_rect = (self.goal["x"], self.goal["y"], self.goal["w"], self.goal["h"])
        if self.rects_overlap(self.player_rect(), goal_rect):
            self.victory = True

    def lose_life(self) -> None:
        self.lives -= 1
        if self.lives <= 0:
            self.game_over = True
            return

        self.player.update(
            {
                "x": self.spawn[0],
                "y": self.spawn[1],
                "vx": 0.0,
                "vy": 0.0,
                "on_ground": False,
            }
        )
        self.camera_x = 0.0

    def update_camera(self) -> None:
        target = self.player["x"] - WIDTH * 0.42
        self.camera_x += (target - self.camera_x) * 0.12
        self.camera_x = max(0, min(self.camera_x, self.world_width - WIDTH))

    def player_rect(self) -> tuple[float, float, float, float]:
        return (self.player["x"], self.player["y"], self.player["w"], self.player["h"])

    @staticmethod
    def rects_overlap(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
        ax, ay, aw, ah = a
        bx, by, bw, bh = b
        return ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by

    def screen_x(self, world_x: float) -> float:
        return world_x - self.camera_x

    def draw(self) -> None:
        self.canvas.delete("all")
        self.draw_background()
        self.draw_platforms()
        self.draw_coins()
        self.draw_enemies()
        self.draw_goal()
        self.draw_player()
        self.draw_hud()

        if self.game_over:
            self.draw_center_message("Fim do jogo", "Prima R para tentar de novo")
        elif self.victory:
            self.draw_center_message("Vitoria!", f"Moedas: {self.score}  |  Prima R para jogar de novo")

    def draw_background(self) -> None:
        self.canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#5d7292", outline="")
        self.canvas.create_rectangle(0, 255, WIDTH, HEIGHT, fill="#26364a", outline="")
        self.canvas.create_oval(730, 38, 805, 113, fill="#f3df9d", outline="")

        for x, y, size in self.clouds:
            sx = self.screen_x(x * 0.45)
            self.canvas.create_oval(sx, y, sx + size, y + size * 0.48, fill="#b9c6d6", outline="")
            self.canvas.create_oval(
                sx + size * 0.35,
                y - size * 0.18,
                sx + size * 1.2,
                y + size * 0.52,
                fill="#c6d0dd",
                outline="",
            )
            self.canvas.create_oval(
                sx + size * 0.75,
                y + size * 0.02,
                sx + size * 1.55,
                y + size * 0.55,
                fill="#b9c6d6",
                outline="",
            )

        self.draw_castle()

    def draw_castle(self) -> None:
        base_x = self.screen_x(170)
        wall_top = 230
        wall_bottom = 492
        stone = "#7d8797"
        shadow = "#5d6878"
        dark = "#2b3443"
        roof = "#733544"

        for i in range(12):
            hill_x = self.screen_x(i * 280 * 0.7)
            color = "#65b96f" if i % 2 else "#55a965"
            self.canvas.create_polygon(
                hill_x - 160,
                500,
                hill_x + 120,
                260 + (i % 3) * 28,
                hill_x + 430,
                500,
                fill=color,
                outline="",
            )

        self.canvas.create_rectangle(base_x - 60, wall_top, base_x + 2790, wall_bottom, fill=stone, outline="")
        for x in range(-40, 2780, 72):
            sx = base_x + x
            self.canvas.create_rectangle(sx, wall_top, sx + 36, wall_top + 34, fill=stone, outline=dark)
        for x in range(-20, 2840, 112):
            sx = base_x + x
            self.canvas.create_rectangle(sx, 275, sx + 22, 300, fill=dark, outline="")
            self.canvas.create_rectangle(sx + 6, 342, sx + 28, 367, fill=dark, outline="")

        for tower_x, tower_w, tower_h in [
            (-110, 120, 300),
            (360, 105, 245),
            (930, 130, 325),
            (1500, 100, 260),
            (2085, 120, 305),
            (2570, 110, 250),
        ]:
            sx = base_x + tower_x
            top = wall_bottom - tower_h
            self.canvas.create_rectangle(sx, top, sx + tower_w, wall_bottom, fill=shadow, outline="")
            self.canvas.create_polygon(
                sx - 14,
                top,
                sx + tower_w / 2,
                top - 70,
                sx + tower_w + 14,
                top,
                fill=roof,
                outline="",
            )
            for slit_y in range(int(top + 58), wall_bottom - 40, 78):
                self.canvas.create_rectangle(
                    sx + tower_w / 2 - 8,
                    slit_y,
                    sx + tower_w / 2 + 8,
                    slit_y + 35,
                    fill=dark,
                    outline="",
                )

    def draw_platforms(self) -> None:
        for x, y, w, h in self.platforms:
            sx = self.screen_x(x)
            self.canvas.create_rectangle(sx, y, sx + w, y + h, fill="#4f5867", outline="")
            self.canvas.create_rectangle(sx, y, sx + w, y + 10, fill="#8a949f", outline="")
            for pebble_x in range(int(x + 16), int(x + w), 42):
                px = self.screen_x(pebble_x)
                self.canvas.create_rectangle(px, y + 21, px + 18, y + 31, fill="#626d7d", outline="")

    def draw_coins(self) -> None:
        for coin in self.coins:
            if coin["taken"]:
                continue
            sx = self.screen_x(coin["x"])
            y = coin["y"]
            self.canvas.create_oval(sx, y, sx + 22, y + 22, fill="#f5c84b", outline="#7d5b00", width=2)
            self.canvas.create_line(sx + 11, y + 4, sx + 11, y + 18, fill="#fff4a8", width=2)

    def draw_enemies(self) -> None:
        for enemy in self.enemies:
            sx = self.screen_x(enemy["x"])
            if "enemy" in self.images:
                self.canvas.create_image(
                    sx + ENEMY_SIZE / 2,
                    enemy["y"] + ENEMY_SIZE / 2,
                    image=self.images["enemy"],
                )
            else:
                self.canvas.create_rectangle(
                    sx,
                    enemy["y"],
                    sx + ENEMY_SIZE,
                    enemy["y"] + ENEMY_SIZE,
                    fill="#a83232",
                    outline="",
                )
                self.canvas.create_oval(sx + 10, enemy["y"] + 11, sx + 18, enemy["y"] + 19, fill="white", outline="")
                self.canvas.create_oval(sx + 28, enemy["y"] + 11, sx + 36, enemy["y"] + 19, fill="white", outline="")

    def draw_goal(self) -> None:
        sx = self.screen_x(self.goal["x"])
        y = self.goal["y"]
        self.canvas.create_rectangle(sx, y, sx + self.goal["w"], y + self.goal["h"], fill="#2f7d46", outline="")
        self.canvas.create_polygon(sx + self.goal["w"], y, sx + 82, y + 18, sx + self.goal["w"], y + 36, fill="#f4d35e", outline="")
        self.canvas.create_rectangle(sx - 8, y + self.goal["h"], sx + self.goal["w"] + 8, y + self.goal["h"] + 12, fill="#3b2d25", outline="")

    def draw_player(self) -> None:
        sx = self.screen_x(self.player["x"])
        y = self.player["y"]
        if "player" in self.images:
            self.canvas.create_image(sx + PLAYER_SIZE / 2, y + PLAYER_SIZE / 2, image=self.images["player"])
            return

        self.canvas.create_rectangle(sx + 8, y + 12, sx + 40, y + 48, fill="#2f6fdb", outline="")
        self.canvas.create_oval(sx + 10, y, sx + 38, y + 28, fill="#f1c27d", outline="")
        self.canvas.create_rectangle(sx + 12, y + 28, sx + 22, y + 48, fill="#222", outline="")
        self.canvas.create_rectangle(sx + 28, y + 28, sx + 38, y + 48, fill="#222", outline="")

    def draw_hud(self) -> None:
        self.canvas.create_text(
            18,
            18,
            anchor="nw",
            text=f"Moedas: {self.score}   Vidas: {self.lives}",
            font=("Segoe UI", 15, "bold"),
            fill="#f8fbff",
        )
        self.canvas.create_text(
            WIDTH - 18,
            18,
            anchor="ne",
            text="Setas/WASD + Espaco",
            font=("Segoe UI", 12),
            fill="#dce6f2",
        )

    def draw_center_message(self, title: str, subtitle: str) -> None:
        self.canvas.create_rectangle(230, 180, WIDTH - 230, 320, fill="#182232", outline="#dce6f2", width=2)
        self.canvas.create_text(WIDTH / 2, 220, text=title, font=("Segoe UI", 28, "bold"), fill="#f8fbff")
        self.canvas.create_text(WIDTH / 2, 270, text=subtitle, font=("Segoe UI", 14), fill="#dce6f2")

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    PlatformGame().run()
