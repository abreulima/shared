(function () {
  "use strict";

  const WORLD_WIDTH = 2400;
  const WORLD_HEIGHT = 1728;
  const TILE = 48;
  const FPS = 60;

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function lerp(a, b, t) {
    return a + (b - a) * t;
  }

  function distance(a, b) {
    const dx = a.x - b.x;
    const dy = a.y - b.y;
    return Math.hypot(dx, dy);
  }

  function rectsOverlap(a, b) {
    return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
  }

  function rectFromCenter(x, y, w, h) {
    return { x: x - w / 2, y: y - h / 2, w, h };
  }

  function rectCenter(rect) {
    return { x: rect.x + rect.w / 2, y: rect.y + rect.h / 2 };
  }

  function pointRect(x, y, size) {
    return { x: x - size / 2, y: y - size / 2, w: size, h: size };
  }

  class Vec2 {
    constructor(x = 0, y = 0) {
      this.x = x;
      this.y = y;
    }

    copy() {
      return new Vec2(this.x, this.y);
    }

    set(x, y) {
      this.x = x;
      this.y = y;
      return this;
    }

    add(v) {
      this.x += v.x;
      this.y += v.y;
      return this;
    }

    sub(v) {
      this.x -= v.x;
      this.y -= v.y;
      return this;
    }

    mul(s) {
      this.x *= s;
      this.y *= s;
      return this;
    }

    length() {
      return Math.hypot(this.x, this.y);
    }

    lengthSq() {
      return this.x * this.x + this.y * this.y;
    }

    normalize() {
      const len = this.length();
      if (len > 0) {
        this.x /= len;
        this.y /= len;
      }
      return this;
    }

    rotate(rad) {
      const c = Math.cos(rad);
      const s = Math.sin(rad);
      const x = this.x * c - this.y * s;
      const y = this.x * s + this.y * c;
      this.x = x;
      this.y = y;
      return this;
    }
  }

  class Game {
    constructor(canvas) {
      this.canvas = canvas;
      this.ctx = canvas.getContext("2d");
      this.viewW = 0;
      this.viewH = 0;

      this.assets = this.createAssets();
      this.assetsReady = false;
      this.inputs = new Set();
      this.pointer = { x: 0, y: 0, down: false };
      this.state = "menu";
      this.running = true;
      this.message = "";
      this.messageTimer = 0;
      this.coverFade = 1;

      this.resize = this.resize.bind(this);
      this.loop = this.loop.bind(this);

      window.addEventListener("resize", this.resize);
      window.addEventListener("keydown", (event) => this.onKeyDown(event));
      window.addEventListener("keyup", (event) => this.inputs.delete(event.code));
      window.addEventListener("pointermove", (event) => this.onPointerMove(event));
      window.addEventListener("pointerdown", (event) => this.onPointerDown(event));
      window.addEventListener("contextmenu", (event) => event.preventDefault());

      this.resize();
      this.loadAssets().then(() => {
        this.assetsReady = true;
      });
      this.resetGame();
      requestAnimationFrame(this.loop);
    }

    createAssets() {
      const base = "../artes/";
      return {
        cover: { src: base + "Capa do jogo. png.png", image: null },
        background: { src: base + "fundo.png", image: null },
        tileTop: { src: base + "relvatopo.png", image: null },
        tileMid: { src: base + "relvameio.png", image: null },
        player: { src: base + "jogador.png", image: null },
        enemy: { src: base + "inimigo.png", image: null },
        boss: { src: base + "boss.png", image: null },
        weapon: { src: base + "arma.png", image: null },
        scrap: { src: base + "coletavel.png", image: null },
        life: { src: base + "vida.png", image: null },
        special: { src: base + "especial.png", image: null },
        objective: { src: base + "objetivo.png", image: null },
        workbench: { src: base + "oficina.png", image: null },
      };
    }

    loadImage(entry) {
      return new Promise((resolve) => {
        const image = new Image();
        image.onload = () => resolve(image);
        image.onerror = () => resolve(null);
        image.src = entry.src;
      });
    }

    async loadAssets() {
      const keys = Object.keys(this.assets);
      const results = await Promise.all(keys.map((key) => this.loadImage(this.assets[key])));
      keys.forEach((key, index) => {
        this.assets[key].image = results[index];
      });
    }

    resize() {
      this.viewW = window.innerWidth;
      this.viewH = window.innerHeight;
      this.canvas.width = Math.max(1, Math.floor(this.viewW * window.devicePixelRatio));
      this.canvas.height = Math.max(1, Math.floor(this.viewH * window.devicePixelRatio));
      this.canvas.style.width = `${this.viewW}px`;
      this.canvas.style.height = `${this.viewH}px`;
      this.ctx.setTransform(window.devicePixelRatio, 0, 0, window.devicePixelRatio, 0, 0);
    }

    resetGame() {
      this.camera = new Vec2(0, 0);
      this.player = {
        pos: new Vec2(220, 220),
        hp: 100,
        maxHp: 100,
        scrap: 0,
        speed: 220,
        damage: 22,
        fireDelay: 0.23,
        specialCharges: 0,
        dashCharges: 0,
        turretCharges: 0,
        mineCharges: 0,
        techLevel: 0,
        fireTimer: 0,
        invuln: 0,
        dashTimer: 0,
        facing: new Vec2(1, 0),
        radius: 18,
      };

      this.bullets = [];
      this.enemies = [];
      this.drops = [];
      this.particles = [];
      this.turrets = [];
      this.mines = [];
      this.walls = this.createWalls();
      this.workbench = this.placeClearRect(120, 120, 96, 96);
      this.extractor = this.placeClearRect(WORLD_WIDTH - 220, WORLD_HEIGHT - 220, 96, 96);
      this.reactors = this.createReactors();
      this.districtLiberated = [false, false, false, false];
      this.extractorActive = false;
      this.boss = this.createBoss();
      this.bossSpawned = false;
      this.bossDefeated = false;
      this.victory = false;
      this.gameOver = false;
      this.craftingOpen = false;
      this.waveTimer = 8;
      this.dropTimer = 14;
      this.message = "Explore a cidade, destrua os reatores e recolha sucata.";
      this.messageTimer = 5;
      this.spawnInitialEnemies();
    }

    createWalls() {
      const walls = [
        { x: -40, y: -40, w: 40, h: WORLD_HEIGHT + 80 },
        { x: WORLD_WIDTH, y: -40, w: 40, h: WORLD_HEIGHT + 80 },
        { x: -40, y: -40, w: WORLD_WIDTH + 80, h: 40 },
        { x: -40, y: WORLD_HEIGHT, w: WORLD_WIDTH + 80, h: 40 },
      ];

      const buildings = [
        [320, 260, 210, 120],
        [520, 720, 190, 120],
        [820, 160, 180, 110],
        [980, 520, 240, 140],
        [1260, 220, 180, 120],
        [1460, 760, 230, 140],
        [1880, 220, 160, 120],
        [1860, 720, 210, 120],
        [340, 1180, 220, 130],
        [960, 1240, 220, 120],
        [1280, 1100, 170, 130],
        [1680, 1180, 250, 150],
        [1180, 860, 160, 100],
        [1520, 420, 160, 100],
        [620, 920, 160, 100],
      ];

      buildings.forEach(([x, y, w, h]) => walls.push({ x, y, w, h }));
      return walls;
    }

    createReactors() {
      const positions = [
        [650, 360],
        [1780, 360],
        [650, 1260],
        [1780, 1260],
      ];
      return positions.map((pos, index) => {
        const rect = this.placeClearRect(pos[0] - 26, pos[1] - 26, 52, 52);
        return { rect, hp: 150, maxHp: 150, active: true, pulse: 0, district: index };
      });
    }

    createBoss() {
      return {
        kind: "boss",
        pos: new Vec2(1460, 940),
        home: new Vec2(1460, 940),
        hp: 420,
        maxHp: 420,
        speed: 92,
        damage: 24,
        detection: 900,
        fireDelay: 1.0,
        radius: 34,
        fireTimer: 1.2,
      };
    }

    createEnemy(kind, x, y, district) {
      const tuning = {
        patrol: [48, 80, 12, 0.0, 18, 42],
        shooter: [38, 60, 8, 1.25, 14, 36],
        guardian: [88, 50, 18, 0.0, 22, 46],
      };
      if (!tuning[kind]) {
        kind = "patrol";
      }
      const [hp, speed, damage, fireDelay, radius, detection] = tuning[kind];
      const scale = 1 + (district - 1) * 0.18;
      const position = this.findOpenPoint(x, y, radius);
      return {
        kind,
        pos: position,
        home: position.copy(),
        hp: Math.round(hp * scale),
        maxHp: Math.round(hp * scale),
        speed: speed * scale,
        damage: Math.round(damage * scale),
        detection: detection * (1 + (district - 1) * 0.1),
        fireDelay,
        radius,
        wanderAngle: Math.random() * Math.PI * 2,
        fireTimer: 0.2 + Math.random() * 0.8,
        drift: 0.3 + Math.random() * 0.9,
      };
    }

    spawnInitialEnemies() {
      const presets = [
        ["patrol", 420, 260, 0],
        ["shooter", 1180, 280, 1],
        ["guardian", 1540, 420, 1],
        ["patrol", 1960, 260, 1],
        ["shooter", 520, 980, 2],
        ["patrol", 860, 1320, 2],
        ["guardian", 1220, 1180, 2],
        ["shooter", 1740, 1360, 2],
        ["patrol", 2060, 1240, 2],
      ];
      presets.forEach(([kind, x, y, district]) => {
        this.enemies.push(this.createEnemy(kind, x, y, district));
      });
    }

    rectBlocked(rect) {
      if (this.hitWall(rect)) {
        return true;
      }
      if (this.workbench && rectsOverlap(rect, this.workbench)) {
        return true;
      }
      if (this.extractor && rectsOverlap(rect, this.extractor)) {
        return true;
      }
      return this.reactors && this.reactors.some((reactor) => rectsOverlap(rect, reactor.rect));
    }

    placeClearRect(x, y, w, h) {
      let candidate = { x, y, w, h };
      if (!this.rectBlocked(candidate)) {
        return candidate;
      }

      const centerX = x + w / 2;
      const centerY = y + h / 2;
      const minHalf = Math.max(w, h) / 2;
      for (let spread = 24; spread < 360; spread += 24) {
        for (let angleDeg = 0; angleDeg < 360; angleDeg += 30) {
          const angle = (angleDeg * Math.PI) / 180;
          const cx = clamp(centerX + Math.cos(angle) * spread, minHalf, WORLD_WIDTH - minHalf);
          const cy = clamp(centerY + Math.sin(angle) * spread, minHalf, WORLD_HEIGHT - minHalf);
          candidate = rectFromCenter(cx, cy, w, h);
          if (!this.rectBlocked(candidate)) {
            return candidate;
          }
        }
      }

      return candidate;
    }

    findOpenPoint(x, y, radius) {
      const size = radius * 2;
      let candidate = rectFromCenter(x, y, size, size);
      if (!this.rectBlocked(candidate)) {
        return new Vec2(x, y);
      }

      for (let spread = 24; spread < 280; spread += 24) {
        for (let angleDeg = 0; angleDeg < 360; angleDeg += 30) {
          const angle = (angleDeg * Math.PI) / 180;
          const cx = clamp(x + Math.cos(angle) * spread, radius, WORLD_WIDTH - radius);
          const cy = clamp(y + Math.sin(angle) * spread, radius, WORLD_HEIGHT - radius);
          candidate = rectFromCenter(cx, cy, size, size);
          if (!this.rectBlocked(candidate)) {
            return new Vec2(cx, cy);
          }
        }
      }

      return new Vec2(clamp(x, radius, WORLD_WIDTH - radius), clamp(y, radius, WORLD_HEIGHT - radius));
    }

    startGame() {
      this.resetGame();
      this.state = "play";
      this.tryFullscreen();
      this.setMessage("Cidade sob ataque. Reaja, recolha sucata e evolua.", 4);
    }

    tryFullscreen() {
      const target = this.canvas;
      if (document.fullscreenElement || !target.requestFullscreen) {
        return;
      }
      target.requestFullscreen().catch(() => {});
    }

    onPointerMove(event) {
      this.pointer.x = event.clientX;
      this.pointer.y = event.clientY;
    }

    onPointerDown(event) {
      this.pointer.x = event.clientX;
      this.pointer.y = event.clientY;
      this.pointer.down = true;

      if (this.state === "menu") {
        this.startGame();
        return;
      }
      if (event.button === 0 && this.state === "play") {
        this.tryShoot();
      }
    }

    onKeyDown(event) {
      this.inputs.add(event.code);

      if (event.code === "Escape") {
        if (this.craftingOpen) {
          this.craftingOpen = false;
        }
        return;
      }

      if (event.code === "Enter" && this.state === "menu") {
        this.startGame();
        return;
      }

      if (event.code === "KeyR" && (this.state === "game_over" || this.state === "victory")) {
        this.resetGame();
        this.state = "play";
        return;
      }

      if (this.state !== "play") {
        return;
      }

      if (event.code === "KeyC") {
        if (this.playerInWorkbenchRange()) {
          this.craftingOpen = !this.craftingOpen;
          this.setMessage(this.craftingOpen ? "Oficina aberta." : "Oficina fechada.", 2);
        } else {
          this.setMessage("Chegue a oficina para craftar.", 2);
        }
      }

      if (event.code === "ShiftLeft" || event.code === "ShiftRight") {
        if (this.player.dashCharges > 0 && !this.craftingOpen) {
          this.player.dashCharges -= 1;
          this.player.dashTimer = 0.18;
          this.spawnParticles(this.player.pos.x, this.player.pos.y, [80, 200, 255], 14, 90);
          this.setMessage("Impulso usado.", 1.4);
        }
      }

      if (event.code === "KeyE") {
        this.useSpecial();
      }

      if (event.code === "KeyZ" && this.player.turretCharges > 0 && !this.craftingOpen) {
        this.placeTurret();
      }

      if (event.code === "KeyX" && this.player.mineCharges > 0 && !this.craftingOpen) {
        this.placeMine();
      }

      if (this.craftingOpen) {
        this.handleCraftingKey(event.code);
      }

      if (event.code === "Space") {
        this.tryShoot();
      }
    }

    handleCraftingKey(code) {
      const costs = {
        Digit1: ["damage", 8],
        Digit2: ["fire", 8],
        Digit3: ["hp", 6],
        Digit4: ["special", 10],
        Digit5: ["dash", 10],
        Digit6: ["turret", 12],
        Digit7: ["mine", 8],
      };
      if (!costs[code]) {
        return;
      }

      const [upgrade, cost] = costs[code];
      if (this.player.scrap < cost) {
        this.setMessage("Sucata insuficiente.", 2);
        return;
      }

      this.player.scrap -= cost;
      if (upgrade === "damage") {
        this.player.damage += 6;
        this.setMessage("Arma reforcada. Dano aumentado.", 3);
      } else if (upgrade === "fire") {
        this.player.fireDelay = Math.max(0.08, this.player.fireDelay * 0.88);
        this.setMessage("Mecanismo ajustado. Disparo mais rapido.", 3);
      } else if (upgrade === "hp") {
        this.player.maxHp += 20;
        this.player.hp = this.player.maxHp;
        this.setMessage("Placas de armadura instaladas.", 3);
      } else if (upgrade === "special") {
        this.player.specialCharges += 1;
        this.setMessage("Carga especial adicionada.", 3);
      } else if (upgrade === "dash") {
        this.player.dashCharges += 1;
        this.setMessage("Impulso extra liberado.", 3);
      } else if (upgrade === "turret") {
        this.player.turretCharges += 1;
        this.setMessage("Modulo de torreta fabricado.", 3);
      } else if (upgrade === "mine") {
        this.player.mineCharges += 1;
        this.setMessage("Carga de mina fabricada.", 3);
      }
    }

    setMessage(text, seconds) {
      this.message = text;
      this.messageTimer = seconds;
    }

    playerInWorkbenchRange() {
      const pr = this.playerRect();
      return rectsOverlap(expandRect(pr, 70, 70), this.workbench);
    }

    playerRect() {
      return {
        x: this.player.pos.x - this.player.radius,
        y: this.player.pos.y - this.player.radius,
        w: this.player.radius * 2,
        h: this.player.radius * 2,
      };
    }

    useSpecial() {
      if (this.state !== "play" || this.craftingOpen) {
        return;
      }
      if (this.player.specialCharges <= 0) {
        this.setMessage("Sem carga especial.", 1.6);
        return;
      }

      this.player.specialCharges -= 1;
      const center = this.player.pos.copy();
      this.spawnParticles(center.x, center.y, [255, 120, 40], 30, 170);
      for (const enemy of this.enemies) {
        if (enemy.hp <= 0) continue;
        if (distance(center, enemy.pos) <= 170) {
          enemy.hp -= 35;
        }
      }
      if (this.bossSpawned && this.boss.hp > 0 && distance(center, this.boss.pos) <= 220) {
        this.boss.hp -= 40;
      }
      this.setMessage("Pulso eletromagnetico ativado.", 2);
    }

    placeTurret() {
      if (this.player.turretCharges <= 0) {
        return;
      }
      const spot = this.findOpenPoint(this.player.pos.x + this.player.facing.x * 46, this.player.pos.y + this.player.facing.y * 46, 16);
      this.turrets.push({
        pos: spot,
        fireDelay: 0.55,
        fireTimer: 0.2,
        range: 330,
        damage: 12,
        life: 40,
      });
      this.player.turretCharges -= 1;
      this.spawnParticles(spot.x, spot.y, [120, 220, 255], 10, 45);
      this.setMessage("Torreta posicionada.", 1.6);
    }

    placeMine() {
      if (this.player.mineCharges <= 0) {
        return;
      }
      const spot = this.findOpenPoint(this.player.pos.x, this.player.pos.y, 16);
      this.mines.push({
        pos: spot,
        radius: 18,
        damage: 28,
        armed: true,
        life: 20,
      });
      this.player.mineCharges -= 1;
      this.spawnParticles(spot.x, spot.y, [255, 200, 80], 8, 35);
      this.setMessage("Mina armada.", 1.6);
    }

    tryShoot() {
      if (this.state !== "play" || this.craftingOpen || this.player.fireTimer > 0) {
        return;
      }

      const mouse = this.getMouseWorld();
      let direction = mouse.sub(this.player.pos.copy());
      if (direction.lengthSq() === 0) {
        direction = new Vec2(1, 0);
      } else {
        direction.normalize();
      }
      this.player.facing = direction.copy();
      this.bullets.push({
        pos: this.player.pos.copy().add(direction.copy().mul(26)),
        vel: direction.copy().mul(620),
        damage: this.player.damage,
        friendly: true,
        life: 1.3,
        radius: 5,
      });
      this.player.fireTimer = this.player.fireDelay;
      this.spawnParticles(this.player.pos.x, this.player.pos.y, [255, 220, 70], 6, 40);
    }

    getMouseWorld() {
      return new Vec2(this.pointer.x + this.camera.x, this.pointer.y + this.camera.y);
    }

    update(dt) {
      if (this.messageTimer > 0) {
        this.messageTimer = Math.max(0, this.messageTimer - dt);
      }

      if (this.state !== "play") {
        return;
      }

      if (this.craftingOpen) {
        this.updateCamera(dt);
        return;
      }

      this.updatePlayer(dt);
      this.updateEnemies(dt);
      this.updateBullets(dt);
      this.updateDrops(dt);
      this.updateParticles(dt);
      this.updateTurrets(dt);
      this.updateMines(dt);
      this.updateReactors(dt);
      this.updateSpawns(dt);
      this.updateCamera(dt);
      this.checkVictory();
      this.checkGameOver();
    }

    updatePlayer(dt) {
      const move = new Vec2(0, 0);
      if (this.inputs.has("KeyW") || this.inputs.has("ArrowUp")) move.y -= 1;
      if (this.inputs.has("KeyS") || this.inputs.has("ArrowDown")) move.y += 1;
      if (this.inputs.has("KeyA") || this.inputs.has("ArrowLeft")) move.x -= 1;
      if (this.inputs.has("KeyD") || this.inputs.has("ArrowRight")) move.x += 1;

      if (move.lengthSq() > 0) {
        move.normalize();
        this.player.facing = move.copy();
      }

      this.player.dashTimer = Math.max(0, this.player.dashTimer - dt);
      const speed = this.player.speed * (this.player.dashTimer > 0 && move.lengthSq() > 0 ? 1.85 : 1.0);
      const delta = move.mul(speed * dt);
      this.moveWithWalls(this.player.pos, delta, this.player.radius);
      if (
        this.player.pos.x < this.player.radius ||
        this.player.pos.y < this.player.radius ||
        this.player.pos.x > WORLD_WIDTH - this.player.radius ||
        this.player.pos.y > WORLD_HEIGHT - this.player.radius
      ) {
        this.player.hp = 0;
        this.setMessage("Saiste do mapa. Pressione R para tentar novamente.", 999);
      }
      this.player.fireTimer = Math.max(0, this.player.fireTimer - dt);
      this.player.invuln = Math.max(0, this.player.invuln - dt);
    }

    moveWithWalls(position, delta, radius) {
      const solidWalls = this.walls.slice(4);
      const rect = { x: position.x - radius, y: position.y - radius, w: radius * 2, h: radius * 2 };

      rect.x += delta.x;
      for (const wall of solidWalls) {
        if (rectsOverlap(rect, wall)) {
          if (delta.x > 0) {
            rect.x = wall.x - rect.w;
          } else if (delta.x < 0) {
            rect.x = wall.x + wall.w;
          }
        }
      }

      rect.y += delta.y;
      for (const wall of solidWalls) {
        if (rectsOverlap(rect, wall)) {
          if (delta.y > 0) {
            rect.y = wall.y - rect.h;
          } else if (delta.y < 0) {
            rect.y = wall.y + wall.h;
          }
        }
      }

      position.set(rect.x + rect.w / 2, rect.y + rect.h / 2);
    }

    updateEnemies(dt) {
      for (const enemy of this.enemies) {
        if (enemy.hp <= 0) continue;

        enemy.fireTimer = Math.max(0, enemy.fireTimer - dt);
        const toPlayer = this.player.pos.copy().sub(enemy.pos.copy());
        const dist = toPlayer.length();
        const direction = dist > 0 ? toPlayer.copy().normalize() : new Vec2(1, 0);

        if (enemy.kind === "shooter") {
          if (dist > 210) {
            this.moveEnemy(enemy, direction.copy().mul(enemy.speed * 0.8 * dt));
          } else if (dist < 150) {
            this.moveEnemy(enemy, direction.copy().mul(-enemy.speed * 0.45 * dt));
          }
          if (dist < 520 && enemy.fireTimer <= 0) {
            this.spawnEnemyBullet(enemy, direction, 330, 1.8);
            enemy.fireTimer = enemy.fireDelay;
          }
        } else if (enemy.kind === "guardian") {
          this.moveEnemy(enemy, direction.copy().mul(enemy.speed * 1.05 * dt));
        } else {
          this.moveEnemy(enemy, direction.copy().mul(enemy.speed * 1.0 * dt));
        }

        if (dist <= enemy.radius + this.player.radius) {
          this.damagePlayer(enemy.damage);
        }
      }

      if (this.bossSpawned && this.boss.hp > 0) {
        this.updateBoss(dt);
      }
    }

    moveEnemy(enemy, delta) {
      const rect = {
        x: enemy.pos.x - enemy.radius,
        y: enemy.pos.y - enemy.radius,
        w: enemy.radius * 2,
        h: enemy.radius * 2,
      };
      const walls = this.walls.slice(4);

      rect.x += delta.x;
      for (const wall of walls) {
        if (rectsOverlap(rect, wall)) {
          rect.x = delta.x > 0 ? wall.x - rect.w : wall.x + wall.w;
        }
      }

      rect.y += delta.y;
      for (const wall of walls) {
        if (rectsOverlap(rect, wall)) {
          rect.y = delta.y > 0 ? wall.y - rect.h : wall.y + wall.h;
        }
      }

      enemy.pos.set(rect.x + rect.w / 2, rect.y + rect.h / 2);
      enemy.pos.x = clamp(enemy.pos.x, enemy.radius, WORLD_WIDTH - enemy.radius);
      enemy.pos.y = clamp(enemy.pos.y, enemy.radius, WORLD_HEIGHT - enemy.radius);
    }

    updateBoss(dt) {
      const boss = this.boss;
      boss.fireTimer = Math.max(0, boss.fireTimer - dt);
      const toPlayer = this.player.pos.copy().sub(boss.pos.copy());
      const dist = toPlayer.length();
      const direction = dist > 0 ? toPlayer.copy().normalize() : new Vec2(1, 0);

      if (dist > 320) {
        this.moveEnemy(boss, direction.copy().mul(boss.speed * dt));
      } else if (dist < 210) {
        this.moveEnemy(boss, direction.copy().mul(-boss.speed * 0.7 * dt));
      }

      if (boss.fireTimer <= 0) {
        if (dist < 760) {
          [-0.22, 0, 0.22].forEach((angle) => {
            const vec = direction.copy().rotate(angle);
            this.spawnEnemyBullet(boss, vec, 280, 2.0, 24);
          });
        } else {
          this.spawnEnemyBullet(boss, direction, 320, 2.2, 24);
        }
        boss.fireTimer = boss.fireDelay;
      }

      if (dist <= boss.radius + this.player.radius) {
        this.damagePlayer(boss.damage);
      }
    }

    spawnEnemyBullet(enemy, direction, speed, life, damage = null) {
      this.bullets.push({
        pos: enemy.pos.copy().add(direction.copy().mul(enemy.radius + 12)),
        vel: direction.copy().mul(speed),
        damage: damage ?? enemy.damage,
        friendly: false,
        life,
        radius: enemy.kind === "boss" ? 6 : 4,
      });
      this.spawnParticles(enemy.pos.x, enemy.pos.y, [255, 110, 60], 5, 25);
    }

    damagePlayer(amount) {
      if (this.player.invuln > 0 || this.state !== "play") {
        return;
      }
      this.player.hp = Math.max(0, this.player.hp - amount);
      this.player.invuln = 0.75;
      this.spawnParticles(this.player.pos.x, this.player.pos.y, [255, 70, 70], 14, 80);
      this.setMessage("Recebeu dano!", 1);
    }

    updateBullets(dt) {
      const remaining = [];
      for (const bullet of this.bullets) {
        bullet.life -= dt;
        bullet.pos.add(bullet.vel.copy().mul(dt));

        if (bullet.life <= 0) continue;
        if (bullet.pos.x < 0 || bullet.pos.y < 0 || bullet.pos.x > WORLD_WIDTH || bullet.pos.y > WORLD_HEIGHT) continue;

        if (this.hitWall(bulletRect(bullet))) {
          this.spawnParticles(bullet.pos.x, bullet.pos.y, bullet.friendly ? [255, 200, 80] : [255, 120, 60], 4, 18);
          continue;
        }

        if (bullet.friendly) {
          if (this.hitReactors(bullet) || this.hitEnemies(bullet) || this.hitBoss(bullet)) {
            continue;
          }
        } else if (rectsOverlap(this.playerRect(), bulletRect(bullet))) {
          this.damagePlayer(bullet.damage);
          this.spawnParticles(bullet.pos.x, bullet.pos.y, [255, 70, 70], 8, 35);
          continue;
        }

        remaining.push(bullet);
      }
      this.bullets = remaining;
    }

    hitWall(rect) {
      return this.walls.some((wall) => rectsOverlap(rect, wall));
    }

    hitEnemies(bullet) {
      const rect = bulletRect(bullet);
      for (const enemy of this.enemies) {
        if (enemy.hp <= 0) continue;
        if (rectsOverlap(rect, enemyRect(enemy))) {
          enemy.hp -= bullet.damage;
          this.spawnParticles(enemy.pos.x, enemy.pos.y, [160, 220, 255], 10, 40);
          if (enemy.hp <= 0) {
            this.killEnemy(enemy);
          }
          return true;
        }
      }
      return false;
    }

    hitBoss(bullet) {
      if (!this.bossSpawned || this.boss.hp <= 0) {
        return false;
      }
      if (rectsOverlap(bulletRect(bullet), enemyRect(this.boss))) {
        this.boss.hp -= bullet.damage;
        this.spawnParticles(this.boss.pos.x, this.boss.pos.y, [255, 120, 255], 14, 60);
        if (this.boss.hp <= 0) {
          this.killBoss();
        }
        return true;
      }
      return false;
    }

    hitReactors(bullet) {
      const rect = bulletRect(bullet);
      for (const reactor of this.reactors) {
        if (!reactor.active) continue;
        if (rectsOverlap(rect, reactor.rect)) {
          reactor.hp -= bullet.damage;
          reactor.pulse = 0.18;
          this.spawnParticles(reactor.rect.x + reactor.rect.w / 2, reactor.rect.y + reactor.rect.h / 2, [255, 210, 70], 8, 30);
          if (reactor.hp <= 0) {
            this.destroyReactor(reactor);
          }
          return true;
        }
      }
      return false;
    }

    killEnemy(enemy) {
      enemy.hp = 0;
      this.player.scrap += enemy.kind === "guardian" ? 2 : 1;
      const dropKind = randomChoice(["scrap", "life", "special"], [70, 20, 10]);
      this.spawnDrop(dropKind, enemy.pos, 1);
      this.spawnParticles(enemy.pos.x, enemy.pos.y, [200, 220, 255], 16, 50);
    }

    killBoss() {
      this.boss.hp = 0;
      this.bossDefeated = true;
      this.extractorActive = true;
      this.spawnDrop("scrap", this.boss.pos, 10);
      this.spawnDrop("life", this.boss.pos, 2);
      this.spawnDrop("special", this.boss.pos, 2);
      this.spawnParticles(this.boss.pos.x, this.boss.pos.y, [255, 80, 255], 40, 120);
      this.setMessage("Nucleo central destruido. Alcance a saida.", 4);
    }

    destroyReactor(reactor) {
      reactor.active = false;
      this.districtLiberated[reactor.district] = true;
      this.player.scrap += 8;
      this.player.specialCharges += 1;
      this.player.techLevel = Math.min(3, this.player.techLevel + 1);
      this.spawnDrop("scrap", rectCenter(reactor.rect), 4);
      this.spawnDrop("life", rectCenter(reactor.rect), 1);
      this.spawnDrop("special", rectCenter(reactor.rect), 1);
      const count = this.reactors.filter((item) => !item.active).length;
      this.setMessage(`Reator destruido: bairro ${reactor.district + 1} liberado (${count}/4).`, 3);
      this.spawnReinforcements();
      if (count >= 4 && !this.bossSpawned) {
        this.spawnBoss();
      }
    }

    spawnReinforcements() {
      let activePositions = this.reactors.filter((r) => r.active).map((r) => rectCenter(r.rect));
      if (!activePositions.length) {
        activePositions = [{ x: WORLD_WIDTH / 2, y: WORLD_HEIGHT / 2 }];
      }
      for (let i = 0; i < 3; i += 1) {
        const base = randomChoice(activePositions);
        const offset = new Vec2(randInt(-100, 100), randInt(-100, 100));
        const pos = this.findOpenPoint(base.x + offset.x, base.y + offset.y, 24);
        const kind = randomChoice(["patrol", "patrol", "shooter", "guardian"]);
        const district = this.districtIndexFor(pos);
        this.enemies.push(this.createEnemy(kind, pos.x, pos.y, district));
      }
    }

    spawnBoss() {
      this.bossSpawned = true;
      this.boss.pos = this.findOpenPoint(1460, 940, this.boss.radius);
      this.boss.home = this.boss.pos.copy();
      this.boss.hp = this.boss.maxHp;
      this.boss.fireTimer = 1.2;
      this.setMessage("A IA central entrou em campo.", 4);
    }

    spawnDrop(kind, center, amount) {
      const pos = center instanceof Vec2 ? center.copy() : new Vec2(center.x, center.y);
      const offset = kind === "scrap" ? new Vec2(randInt(-18, 18), randInt(-18, 18)) : new Vec2(randInt(-10, 10), randInt(-10, 10));
      const finalPos = this.findOpenPoint(pos.x + offset.x, pos.y + offset.y, 12);
      this.drops.push({
        kind,
        pos: finalPos,
        amount,
        ttl: 18,
        pulse: 0,
      });
    }

    updateDrops(dt) {
      const remaining = [];
      for (const drop of this.drops) {
        drop.ttl -= dt;
        drop.pulse += dt * 4;
        if (drop.ttl <= 0) continue;
        if (rectsOverlap(expandRect(this.playerRect(), 18, 18), dropRect(drop))) {
          if (drop.kind === "scrap") this.player.scrap += drop.amount;
          if (drop.kind === "life") this.player.hp = Math.min(this.player.maxHp, this.player.hp + 25 * drop.amount);
          if (drop.kind === "special") this.player.specialCharges += drop.amount;
          this.spawnParticles(drop.pos.x, drop.pos.y, [255, 230, 120], 8, 20);
          continue;
        }
        remaining.push(drop);
      }
      this.drops = remaining;
    }

    updateParticles(dt) {
      const remaining = [];
      for (const particle of this.particles) {
        particle.life -= dt;
        particle.pos.add(particle.vel.copy().mul(dt));
        particle.vel.mul(0.94);
        if (particle.life > 0) {
          remaining.push(particle);
        }
      }
      this.particles = remaining;
    }

    updateTurrets(dt) {
      const remaining = [];
      for (const turret of this.turrets) {
        turret.life -= dt;
        turret.fireTimer = Math.max(0, turret.fireTimer - dt);
        const target = this.findTurretTarget(turret);
        if (target && turret.fireTimer <= 0) {
          const direction = target.pos.copy().sub(turret.pos.copy());
          if (direction.lengthSq() > 0) {
            direction.normalize();
            this.bullets.push({
              pos: turret.pos.copy().add(direction.copy().mul(20)),
              vel: direction.copy().mul(520),
              damage: turret.damage,
              friendly: true,
              life: 1.2,
              radius: 4,
            });
            turret.fireTimer = turret.fireDelay;
            this.spawnParticles(turret.pos.x, turret.pos.y, [120, 220, 255], 4, 24);
          }
        }
        if (turret.life > 0) {
          remaining.push(turret);
        }
      }
      this.turrets = remaining;
    }

    findTurretTarget(turret) {
      let best = null;
      let bestDist = turret.range;
      for (const enemy of this.enemies) {
        if (enemy.hp <= 0) continue;
        const dist = distance(turret.pos, enemy.pos);
        if (dist < bestDist) {
          best = enemy;
          bestDist = dist;
        }
      }
      if (this.bossSpawned && this.boss.hp > 0) {
        const bossDist = distance(turret.pos, this.boss.pos);
        if (bossDist < bestDist) {
          return this.boss;
        }
      }
      return best;
    }

    updateMines(dt) {
      const remaining = [];
      for (const mine of this.mines) {
        mine.life -= dt;
        if (mine.life <= 0) {
          continue;
        }
        if (mine.armed) {
          let hit = false;
          for (const enemy of this.enemies) {
            if (enemy.hp <= 0) continue;
            if (distance(mine.pos, enemy.pos) <= mine.radius + enemy.radius) {
              enemy.hp -= mine.damage;
              hit = true;
              if (enemy.hp <= 0) {
                this.killEnemy(enemy);
              }
              break;
            }
          }
          if (!hit && this.bossSpawned && this.boss.hp > 0 && distance(mine.pos, this.boss.pos) <= mine.radius + this.boss.radius) {
            this.boss.hp -= mine.damage;
            hit = true;
            if (this.boss.hp <= 0) {
              this.killBoss();
            }
          }
          if (hit) {
            mine.life = 0;
            this.spawnParticles(mine.pos.x, mine.pos.y, [255, 200, 80], 18, 55);
            continue;
          }
        }
        remaining.push(mine);
      }
      this.mines = remaining;
    }

    spawnParticles(x, y, color, amount, strength) {
      const origin = new Vec2(x, y);
      for (let i = 0; i < amount; i += 1) {
        const angle = Math.random() * Math.PI * 2;
        const speed = randRange(strength * 0.35, strength);
        this.particles.push({
          pos: origin.copy(),
          vel: new Vec2(Math.cos(angle), Math.sin(angle)).mul(speed),
          color,
          life: randRange(0.25, 0.85),
          radius: randInt(2, 5),
        });
      }
    }

    updateReactors(dt) {
      for (const reactor of this.reactors) {
        reactor.pulse = Math.max(0, reactor.pulse - dt);
        if (reactor.active && distance(this.player.pos, rectCenter(reactor.rect)) < 54) {
          reactor.pulse = Math.max(reactor.pulse, 0.15);
        }
      }
    }

    updateSpawns(dt) {
      this.waveTimer -= dt;
      this.dropTimer -= dt;

      if (this.waveTimer <= 0) {
        this.waveTimer = 12;
        if (this.enemies.filter((enemy) => enemy.hp > 0).length < 16) {
          this.spawnWave();
        }
      }

      if (this.dropTimer <= 0) {
        this.dropTimer = randRange(18, 26);
        this.spawnEventDrop();
      }
    }

    spawnWave() {
      const activeReactors = this.reactors.filter((r) => r.active);
      let district;
      let center;
      if (activeReactors.length) {
        const chosen = randomChoice(activeReactors);
        district = chosen.district;
        center = rectCenter(chosen.rect);
      } else {
        district = randInt(0, 3);
        center = { x: WORLD_WIDTH / 2, y: WORLD_HEIGHT / 2 };
      }

      for (let i = 0; i < randInt(2, 4); i += 1) {
        const offset = new Vec2(randInt(-140, 140), randInt(-140, 140));
        const pos = this.findOpenPoint(center.x + offset.x, center.y + offset.y, 24);
        const kind = randomChoice(["patrol", "shooter", "guardian"]);
        const d = this.districtIndexFor(pos);
        this.enemies.push(this.createEnemy(kind, pos.x, pos.y, d));
      }
      this.setMessage("Ataque mecanico detectado.", 2.5);
    }

    spawnEventDrop() {
      const base = new Vec2(
        clamp(this.player.pos.x + randInt(-220, 220), 120, WORLD_WIDTH - 120),
        clamp(this.player.pos.y + randInt(-220, 220), 120, WORLD_HEIGHT - 120),
      );
      const kind = randomChoice(["scrap", "life", "special"], [70, 20, 10]);
      this.spawnDrop(kind, base, 1);
    }

    districtIndexFor(pos) {
      if (pos.x < WORLD_WIDTH / 2 && pos.y < WORLD_HEIGHT / 2) return this.districtLiberated[0] ? 1 : 2;
      if (pos.x >= WORLD_WIDTH / 2 && pos.y < WORLD_HEIGHT / 2) return this.districtLiberated[1] ? 1 : 2;
      if (pos.x < WORLD_WIDTH / 2 && pos.y >= WORLD_HEIGHT / 2) return this.districtLiberated[2] ? 1 : 2;
      return this.districtLiberated[3] ? 1 : 2;
    }

    updateCamera(dt) {
      const targetX = this.player.pos.x - this.viewW / 2;
      const targetY = this.player.pos.y - this.viewH / 2;
      const t = Math.min(1, 5.5 * dt);
      this.camera.x = lerp(this.camera.x, targetX, t);
      this.camera.y = lerp(this.camera.y, targetY, t);
      this.camera.x = clamp(this.camera.x, 0, Math.max(0, WORLD_WIDTH - this.viewW));
      this.camera.y = clamp(this.camera.y, 0, Math.max(0, WORLD_HEIGHT - this.viewH));
    }

    checkVictory() {
      if (this.bossDefeated && this.extractorActive && rectsOverlap(this.playerRect(), this.extractor)) {
        this.victory = true;
        this.state = "victory";
        this.setMessage("A cidade foi recuperada.", 999);
      }
    }

    checkGameOver() {
      if (this.player.hp <= 0 && this.state === "play") {
        this.gameOver = true;
        this.state = "game_over";
        if (!this.message) {
          this.setMessage("Fim de jogo. Pressione R para tentar novamente.", 999);
        }
      }
    }

    draw() {
      const ctx = this.ctx;
      ctx.clearRect(0, 0, this.viewW, this.viewH);

      if (this.state === "menu") {
        this.drawMenu();
        return;
      }

      this.drawWorld();
      this.drawEntities();
      this.drawHud();
      this.drawOverlays();

      if (this.craftingOpen) {
        this.drawCraftingPanel();
      }
    }

    drawMenu() {
      const ctx = this.ctx;
      if (this.imageReady("cover")) {
        ctx.drawImage(this.assets.cover.image, 0, 0, this.viewW, this.viewH);
      } else if (this.imageReady("background")) {
        ctx.drawImage(this.assets.background.image, 0, 0, this.viewW, this.viewH);
      } else {
        const grad = ctx.createLinearGradient(0, 0, 0, this.viewH);
        grad.addColorStop(0, "#0d1324");
        grad.addColorStop(1, "#05070d");
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, this.viewW, this.viewH);
      }

      this.drawCyberCityOverlay(true);

      ctx.fillStyle = "rgba(8, 10, 16, 0.45)";
      ctx.fillRect(0, 0, this.viewW, this.viewH);

      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillStyle = "#78dcff";
      ctx.font = "bold 52px Consolas, monospace";
      ctx.fillText("Cidade Sob Invasao", this.viewW / 2, 88);
      ctx.fillStyle = "#f2f7ff";
      ctx.font = "bold 22px Consolas, monospace";
      ctx.fillText("Exploracao, combate e crafting", this.viewW / 2, 138);

      const lines = [
        "WASD ou setas para mover",
        "Mouse ou ESPACO para disparar",
        "E para especial, C perto da oficina para craftar",
        "SHIFT ativa impulso se tiver carga",
        "Z para torreta e X para mina",
        "Destrua os 4 reatores, derrube o boss e alcance a saida",
        "Pressione ENTER ou clique para comecar",
      ];
      ctx.font = "18px Consolas, monospace";
      let y = 264;
      lines.forEach((line) => {
        ctx.fillStyle = "#e8edf5";
        ctx.fillText(line, this.viewW / 2, y);
        y += 34;
      });

      if (this.imageReady("objective")) {
        ctx.drawImage(this.assets.objective.image, this.viewW / 2 - 27, 520, 54, 54);
      }

      if (!this.assetsReady) {
        ctx.fillStyle = "#8db4ff";
        ctx.font = "16px Consolas, monospace";
        ctx.fillText("A carregar recursos...", this.viewW / 2, this.viewH - 44);
      }
    }

    drawWorld() {
      const ctx = this.ctx;
      if (this.imageReady("background")) {
        ctx.drawImage(
          this.assets.background.image,
          -this.camera.x * 0.12,
          -this.camera.y * 0.08,
          this.viewW,
          this.viewH,
        );
      } else {
        ctx.fillStyle = "#1e2a1d";
        ctx.fillRect(0, 0, this.viewW, this.viewH);
      }

      this.drawCyberCityOverlay(false);

      ctx.fillStyle = "rgba(10, 14, 18, 0.16)";
      ctx.fillRect(0, 0, this.viewW, this.viewH);

      this.drawTileLayer();
      this.drawWalls();
      this.drawMapBounds();
      this.drawWorkbench();
      this.drawReactors();
      this.drawExtractor();
    }

    drawCyberCityOverlay(menuMode) {
      const ctx = this.ctx;
      const skylineScroll = this.camera.x * 0.35;
      const horizon = this.viewH - 220;
      const buildings = [
        [0.00, 0.12, 170, 85, [34, 42, 58]],
        [0.08, 0.18, 220, 120, [28, 38, 54]],
        [0.19, 0.10, 150, 100, [42, 50, 68]],
        [0.33, 0.22, 260, 145, [31, 44, 66]],
        [0.52, 0.14, 190, 110, [44, 52, 74]],
        [0.68, 0.20, 240, 140, [29, 36, 52]],
        [0.83, 0.12, 180, 95, [39, 46, 62]],
      ];

      for (let index = 0; index < buildings.length; index += 1) {
        const [xFactor, widthFactor, widthPx, heightPx, color] = buildings[index];
        const x = Math.floor(((this.viewW * xFactor + skylineScroll * widthFactor) % (this.viewW + 240)) - 120);
        const y = horizon - heightPx;
        ctx.fillStyle = rgb(color);
        ctx.fillRect(x, y, widthPx, heightPx);
        ctx.strokeStyle = "rgba(10, 12, 18, 0.95)";
        ctx.lineWidth = 2;
        ctx.strokeRect(x, y, widthPx, heightPx);
        const windowColor = index % 2 === 0 ? "rgba(70, 220, 255, 0.95)" : "rgba(255, 110, 220, 0.95)";
        for (let wy = y + 16; wy < y + heightPx - 10; wy += 18) {
          for (let wx = x + 12; wx < x + widthPx - 10; wx += 22) {
            if ((Math.floor(wx / 22) + Math.floor(wy / 18) + index) % 3 !== 0) {
              ctx.fillStyle = windowColor;
              ctx.fillRect(wx, wy, 8, 10);
            }
          }
        }
        const antennaX = x + Math.floor(widthPx / 2);
        ctx.strokeStyle = "#6edcff";
        ctx.beginPath();
        ctx.moveTo(antennaX, y);
        ctx.lineTo(antennaX, y - 18 - index * 2);
        ctx.stroke();
        ctx.fillStyle = "#ff5ab4";
        ctx.beginPath();
        ctx.arc(antennaX, y - 18 - index * 2, 3, 0, Math.PI * 2);
        ctx.fill();
      }

      const road = { x: 0, y: this.viewH - 160, w: this.viewW, h: 160 };
      ctx.fillStyle = "#121218";
      ctx.fillRect(road.x, road.y, road.w, road.h);
      ctx.fillStyle = "#ff5ab4";
      ctx.fillRect(0, this.viewH - 162, this.viewW, 2);
      for (let i = 0; i < this.viewW; i += 60) {
        ctx.fillStyle = "#373c48";
        ctx.fillRect(i, this.viewH - 85, 34, 6);
      }

      const fog = ctx.createLinearGradient(0, this.viewH - 260, 0, this.viewH);
      fog.addColorStop(0, "rgba(70, 190, 255, 0.08)");
      fog.addColorStop(1, "rgba(70, 190, 255, 0)");
      ctx.fillStyle = fog;
      ctx.fillRect(0, this.viewH - 280, this.viewW, 280);

      if (menuMode) {
        ctx.fillStyle = "rgba(0, 0, 0, 0.15)";
        ctx.fillRect(0, 0, this.viewW, this.viewH);
      }
    }

    drawTileLayer() {
      if (!this.imageReady("tileMid")) {
        return;
      }

      const startX = Math.max(0, Math.floor(this.camera.x / TILE) - 1);
      const endX = Math.min(WORLD_WIDTH / TILE + 1, Math.floor((this.camera.x + this.viewW) / TILE) + 2);
      const startY = Math.max(0, Math.floor(this.camera.y / TILE) - 1);
      const endY = Math.min(WORLD_HEIGHT / TILE + 1, Math.floor((this.camera.y + this.viewH) / TILE) + 2);

      for (let ty = startY; ty < endY; ty += 1) {
        for (let tx = startX; tx < endX; tx += 1) {
          const image = ty === 0 ? this.assets.tileTop.image : this.assets.tileMid.image;
          if (!image) {
            continue;
          }
          this.ctx.drawImage(image, tx * TILE - this.camera.x, ty * TILE - this.camera.y, TILE, TILE);
        }
      }
    }

    drawWalls() {
      const ctx = this.ctx;
      for (const wall of this.walls.slice(4)) {
        const x = wall.x - this.camera.x;
        const y = wall.y - this.camera.y;
        ctx.fillStyle = "#373c46";
        ctx.fillRect(x, y, wall.w, wall.h);
        ctx.strokeStyle = "#191c23";
        ctx.lineWidth = 2;
        ctx.strokeRect(x, y, wall.w, wall.h);
      }
    }

    drawMapBounds() {
      const ctx = this.ctx;
      ctx.strokeStyle = "#3b93ff";
      ctx.lineWidth = 4;
      ctx.strokeRect(-this.camera.x, -this.camera.y, WORLD_WIDTH, WORLD_HEIGHT);
    }

    drawWorkbench() {
      const ctx = this.ctx;
      const x = this.workbench.x - this.camera.x;
      const y = this.workbench.y - this.camera.y;
      if (this.imageReady("workbench")) {
        ctx.drawImage(this.assets.workbench.image, x, y, this.workbench.w, this.workbench.h);
      } else {
        ctx.fillStyle = "#523616";
        ctx.fillRect(x, y, this.workbench.w, this.workbench.h);
        ctx.strokeStyle = "#ffd264";
        ctx.lineWidth = 2;
        ctx.strokeRect(x, y, this.workbench.w, this.workbench.h);
      }
      ctx.fillStyle = "#fff0a0";
      ctx.font = "15px Consolas, monospace";
      ctx.textAlign = "center";
      ctx.fillText("OFICINA", x + this.workbench.w / 2, y - 10);
    }

    drawReactors() {
      const ctx = this.ctx;
      for (const reactor of this.reactors) {
        const center = {
          x: reactor.rect.x + reactor.rect.w / 2 - this.camera.x,
          y: reactor.rect.y + reactor.rect.h / 2 - this.camera.y,
        };
        const pulse = reactor.pulse > 0 ? Math.sin(reactor.pulse * 18) * 4 : 0;
        if (reactor.active) {
          const glow = reactor.hp < reactor.maxHp * 0.4 ? "#ff5a5a" : "#ffb43c";
          ctx.strokeStyle = glow;
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.arc(center.x, center.y, 34 + pulse, 0, Math.PI * 2);
          ctx.stroke();
          ctx.fillStyle = "#c85050";
          ctx.fillRect(reactor.rect.x - this.camera.x, reactor.rect.y - this.camera.y, reactor.rect.w, reactor.rect.h);
          this.drawObjectiveMarker(center.x, center.y);
          const barW = 64;
          const barH = 7;
          const barX = center.x - barW / 2;
          const barY = center.y - 48;
          ctx.fillStyle = "#141414";
          ctx.fillRect(barX, barY, barW, barH);
          ctx.fillStyle = "#ff5a5a";
          ctx.fillRect(barX, barY, barW * (reactor.hp / reactor.maxHp), barH);
        } else {
          ctx.fillStyle = "#5a1414";
          ctx.beginPath();
          ctx.arc(center.x, center.y, 20, 0, Math.PI * 2);
          ctx.fill();
        }
      }
    }

    drawExtractor() {
      if (!this.extractorActive) {
        return;
      }
      const ctx = this.ctx;
      const x = this.extractor.x - this.camera.x;
      const y = this.extractor.y - this.camera.y;
      ctx.fillStyle = "#4697f0";
      ctx.fillRect(x, y, this.extractor.w, this.extractor.h);
      ctx.strokeStyle = "#def8ff";
      ctx.lineWidth = 2;
      ctx.strokeRect(x, y, this.extractor.w, this.extractor.h);
      this.drawObjectiveMarker(x + this.extractor.w / 2, y + this.extractor.h / 2);
      ctx.fillStyle = "#e6f7ff";
      ctx.font = "15px Consolas, monospace";
      ctx.textAlign = "center";
      ctx.fillText("SAIDA", x + this.extractor.w / 2, y + this.extractor.h + 18);
    }

    drawObjectiveMarker(x, y) {
      const ctx = this.ctx;
      if (this.imageReady("objective")) {
        ctx.drawImage(this.assets.objective.image, x - 27, y - 27, 54, 54);
      } else {
        ctx.fillStyle = "#ffd645";
        ctx.beginPath();
        ctx.arc(x, y, 18, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    drawEntities() {
      const entities = [];
      this.drops.forEach((drop) => entities.push(["drop", drop]));
      this.bullets.forEach((bullet) => entities.push(["bullet", bullet]));
      this.particles.forEach((particle) => entities.push(["particle", particle]));
      this.mines.forEach((mine) => entities.push(["mine", mine]));
      this.turrets.forEach((turret) => entities.push(["turret", turret]));
      this.enemies.forEach((enemy) => entities.push(["enemy", enemy]));
      if (this.bossSpawned) {
        entities.push(["boss", this.boss]);
      }
      entities.push(["player", this.player]);

      for (const [kind, obj] of entities) {
        if (kind === "drop") this.drawDrop(obj);
        if (kind === "bullet") this.drawBullet(obj);
        if (kind === "particle") this.drawParticle(obj);
        if (kind === "mine") this.drawMine(obj);
        if (kind === "turret") this.drawTurret(obj);
        if (kind === "enemy") this.drawEnemy(obj);
        if (kind === "boss") this.drawBoss(obj);
        if (kind === "player") this.drawPlayer(obj);
      }
    }

    drawDrop(drop) {
      const ctx = this.ctx;
      const pos = { x: drop.pos.x - this.camera.x, y: drop.pos.y - this.camera.y };
      const pulse = Math.sin(drop.pulse * 5) * 2;
      const img = drop.kind === "scrap" ? this.assets.scrap.image : drop.kind === "life" ? this.assets.life.image : this.assets.special.image;
      if (this.imageReady(drop.kind === "scrap" ? "scrap" : drop.kind === "life" ? "life" : "special")) {
        const size = drop.kind === "scrap" ? 24 : 24;
        ctx.drawImage(img, pos.x - size / 2, pos.y - size / 2 - pulse, size, size);
      } else {
        ctx.fillStyle = drop.kind === "scrap" ? "#d9b15c" : drop.kind === "life" ? "#ff8f9f" : "#6fffdc";
        ctx.beginPath();
        ctx.arc(pos.x, pos.y - pulse, 10, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    drawBullet(bullet) {
      const ctx = this.ctx;
      const pos = { x: bullet.pos.x - this.camera.x, y: bullet.pos.y - this.camera.y };
      ctx.fillStyle = bullet.friendly ? "#ffc64d" : "#ff7a45";
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, bullet.radius, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "#ffffff";
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, Math.max(1, Math.floor(bullet.radius / 3)), 0, Math.PI * 2);
      ctx.fill();
    }

    drawParticle(particle) {
      const ctx = this.ctx;
      const pos = { x: particle.pos.x - this.camera.x, y: particle.pos.y - this.camera.y };
      const alpha = clamp(particle.life / 0.85, 0, 1);
      ctx.fillStyle = `rgba(${particle.color[0]}, ${particle.color[1]}, ${particle.color[2]}, ${alpha})`;
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, particle.radius, 0, Math.PI * 2);
      ctx.fill();
    }

    drawMine(mine) {
      const ctx = this.ctx;
      const pos = { x: mine.pos.x - this.camera.x, y: mine.pos.y - this.camera.y };
      ctx.fillStyle = "#5a5a5a";
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, mine.radius, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = "#ffc850";
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    drawTurret(turret) {
      const ctx = this.ctx;
      const pos = { x: turret.pos.x - this.camera.x, y: turret.pos.y - this.camera.y };
      ctx.fillStyle = "#284f74";
      ctx.fillRect(pos.x - 9, pos.y - 9, 18, 18);
      ctx.strokeStyle = "#78dcff";
      ctx.lineWidth = 2;
      ctx.strokeRect(pos.x - 9, pos.y - 9, 18, 18);
    }

    drawEnemy(enemy) {
      if (enemy.hp <= 0) return;
      const ctx = this.ctx;
      const pos = { x: enemy.pos.x - this.camera.x, y: enemy.pos.y - this.camera.y };
      const size = enemy.radius * 2;
      const body = { x: pos.x - enemy.radius, y: pos.y - enemy.radius, w: size, h: size };
      const chassisColor = "#343a48";
      const trimColor = "#aeb9c6";
      const accentColor = enemy.kind === "shooter" ? "#ffaf46" : "#5cdcff";

      ctx.fillStyle = chassisColor;
      ctx.fillRect(body.x, body.y, body.w, body.h);
      ctx.strokeStyle = trimColor;
      ctx.lineWidth = 2;
      ctx.strokeRect(body.x, body.y, body.w, body.h);
      ctx.fillStyle = "#4e5565";
      ctx.fillRect(body.x + 4, body.y + 6, body.w - 8, 8);

      ctx.fillStyle = "#ff4646";
      ctx.beginPath();
      ctx.arc(body.x + body.w / 2 - 7, body.y + body.h / 2 - 4, 3, 0, Math.PI * 2);
      ctx.fill();
      ctx.beginPath();
      ctx.arc(body.x + body.w / 2 + 7, body.y + body.h / 2 - 4, 3, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = accentColor;
      ctx.fillRect(body.x + body.w / 2 - 5, body.y + 9, 10, 4);

      ctx.strokeStyle = trimColor;
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(body.x - 5, body.y + body.h / 2 - 2);
      ctx.lineTo(body.x - 14, body.y + body.h / 2 - 8);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(body.x + body.w + 5, body.y + body.h / 2 - 2);
      ctx.lineTo(body.x + body.w + 14, body.y + body.h / 2 - 8);
      ctx.stroke();
      ctx.strokeStyle = "#262b33";
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.moveTo(body.x + 8, body.y + body.h - 1);
      ctx.lineTo(body.x + 6, body.y + body.h + 12);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(body.x + body.w - 8, body.y + body.h - 1);
      ctx.lineTo(body.x + body.w - 6, body.y + body.h + 12);
      ctx.stroke();
      ctx.fillStyle = accentColor;
      ctx.beginPath();
      ctx.arc(body.x + 5, body.y + body.h + 10, 3, 0, Math.PI * 2);
      ctx.fill();
      ctx.beginPath();
      ctx.arc(body.x + body.w - 5, body.y + body.h + 10, 3, 0, Math.PI * 2);
      ctx.fill();

      if (enemy.kind === "shooter") {
        ctx.fillStyle = accentColor;
        ctx.fillRect(body.x + body.w / 2 - 3, body.y + body.h - 10, 6, 10);
        ctx.strokeStyle = accentColor;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(body.x + body.w / 2, body.y - 6);
        ctx.lineTo(body.x + body.w / 2, body.y - 18);
        ctx.stroke();
      } else if (enemy.kind === "guardian") {
        ctx.strokeStyle = "#76808f";
        ctx.lineWidth = 2;
        ctx.strokeRect(body.x + 2, body.y + 2, body.w - 4, body.h - 4);
        ctx.fillStyle = "#50dcff";
        ctx.beginPath();
        ctx.arc(body.x + body.w / 2, body.y + body.h / 2 + 5, 5, 0, Math.PI * 2);
        ctx.fill();
        ctx.beginPath();
        ctx.arc(body.x + body.w / 2, body.y + body.h / 2 - 10, 4, 0, Math.PI * 2);
        ctx.fill();
      } else {
        ctx.strokeStyle = trimColor;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(body.x - 4, body.y + body.h / 2);
        ctx.lineTo(body.x - 10, body.y + body.h / 2 - 2);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(body.x + body.w + 4, body.y + body.h / 2);
        ctx.lineTo(body.x + body.w + 10, body.y + body.h / 2 - 2);
        ctx.stroke();
      }
      this.drawLifeBar(pos.x, pos.y, enemy.hp, enemy.maxHp, enemy.radius, "#ff5050");
    }

    drawBoss(boss) {
      if (!this.bossSpawned || boss.hp <= 0) return;
      const ctx = this.ctx;
      const pos = { x: boss.pos.x - this.camera.x, y: boss.pos.y - this.camera.y };
      const body = { x: pos.x - boss.radius, y: pos.y - boss.radius, w: boss.radius * 2, h: boss.radius * 2 };
      ctx.fillStyle = "#2a183d";
      ctx.fillRect(body.x, body.y, body.w, body.h);
      ctx.strokeStyle = "#dc6eff";
      ctx.lineWidth = 3;
      ctx.strokeRect(body.x, body.y, body.w, body.h);
      ctx.fillStyle = "#5a347d";
      ctx.fillRect(body.x + 8, body.y + 10, body.w - 16, 14);
      ctx.fillStyle = "#727a90";
      ctx.fillRect(body.x + 14, body.y + 36, body.w - 28, body.h - 48);
      ctx.fillStyle = "#ff78ff";
      ctx.beginPath();
      ctx.arc(body.x + body.w / 2, body.y + body.h / 2 - 8, 8, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "#50dcff";
      ctx.beginPath();
      ctx.arc(body.x + body.w / 2, body.y + body.h / 2 - 8, 3, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "#7846a0";
      ctx.fillRect(body.x + body.w / 2 - 6, body.y + body.h - 18, 12, 18);
      ctx.strokeStyle = "#dc6eff";
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.moveTo(body.x - 10, body.y + body.h / 2);
      ctx.lineTo(body.x - 26, body.y + body.h / 2 - 8);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(body.x + body.w + 10, body.y + body.h / 2);
      ctx.lineTo(body.x + body.w + 26, body.y + body.h / 2 - 8);
      ctx.stroke();
      ctx.fillStyle = "#ff78ff";
      ctx.beginPath();
      ctx.arc(body.x + 8, body.y - 6, 4, 0, Math.PI * 2);
      ctx.fill();
      ctx.beginPath();
      ctx.arc(body.x + body.w - 8, body.y - 6, 4, 0, Math.PI * 2);
      ctx.fill();
      this.drawLifeBar(pos.x, pos.y, boss.hp, boss.maxHp, boss.radius, "#ff7aff", 110, -62);
    }

    drawPlayer(player) {
      const ctx = this.ctx;
      const pos = { x: player.pos.x - this.camera.x, y: player.pos.y - this.camera.y };
      const px = pos.x;
      const py = pos.y;
      const skin = "#eec184";
      const shirt = "#2878d2";
      const pants = "#22222a";

      if (player.invuln > 0 && Math.floor(player.invuln * 20) % 2 === 0) {
        ctx.globalAlpha = 0.5;
      }

      ctx.fillStyle = skin;
      ctx.beginPath();
      ctx.ellipse(px, py - 25, 10, 10, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = shirt;
      ctx.fillRect(px - 12, py - 5, 24, 27);
      ctx.fillStyle = skin;
      ctx.fillRect(px - 12, py + 2, 4, 12);
      ctx.fillRect(px + 8, py + 2, 4, 12);
      ctx.beginPath();
      ctx.moveTo(px - 12, py + 2);
      ctx.lineTo(px - 26, py + 11);
      ctx.lineWidth = 4;
      ctx.strokeStyle = skin;
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(px + 12, py + 2);
      ctx.lineTo(px + 26, py + 11);
      ctx.stroke();
      ctx.fillStyle = pants;
      ctx.beginPath();
      ctx.moveTo(px - 8, py + 21);
      ctx.lineTo(px - 10, py + 35);
      ctx.strokeStyle = pants;
      ctx.lineWidth = 6;
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(px + 8, py + 21);
      ctx.lineTo(px + 10, py + 35);
      ctx.stroke();
      ctx.globalAlpha = 1;
      ctx.fillStyle = "#2a2323";
      ctx.beginPath();
      ctx.arc(px - 4, py - 17, 2, 0, Math.PI * 2);
      ctx.fill();
      ctx.beginPath();
      ctx.arc(px + 4, py - 17, 2, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = "#a04646";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(px, py - 10, 5, Math.PI * 0.1, Math.PI - 0.1);
      ctx.stroke();

      if (player.techLevel > 0) {
        for (let i = 0; i < player.techLevel; i += 1) {
          const off = 18 + i * 5;
          ctx.fillStyle = "#78dcff";
          ctx.beginPath();
          ctx.arc(px + off, py - 12, 3, 0, Math.PI * 2);
          ctx.fill();
          ctx.beginPath();
          ctx.arc(px - off, py - 12, 3, 0, Math.PI * 2);
          ctx.fill();
        }
      }

      if (this.imageReady("weapon")) {
        const angle = Math.atan2(player.facing.y, player.facing.x);
        ctx.save();
        ctx.translate(px, py);
        ctx.rotate(angle);
        ctx.drawImage(this.assets.weapon.image, 16, -14, 28, 28);
        ctx.restore();
      }

      if (player.invuln > 0 && Math.floor(player.invuln * 20) % 2 === 0) {
        ctx.strokeStyle = "rgba(160, 220, 255, 0.9)";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(px, py, player.radius + 8, 0, Math.PI * 2);
        ctx.stroke();
      }
      this.drawLifeBar(px, py, player.hp, player.maxHp, player.radius, "#50aaff");
    }

    drawLifeBar(x, y, hp, maxHp, radius, color, width = 64, offset = -46) {
      const ctx = this.ctx;
      const barX = x - width / 2;
      const barY = y + offset;
      ctx.fillStyle = "#141414";
      ctx.fillRect(barX, barY, width, 7);
      ctx.fillStyle = color;
      ctx.fillRect(barX, barY, width * clamp(hp / maxHp, 0, 1), 7);
    }

    drawHud() {
      const ctx = this.ctx;
      ctx.textAlign = "left";
      ctx.textBaseline = "top";

      ctx.fillStyle = "rgba(10, 14, 22, 0.78)";
      ctx.fillRect(14, 12, 410, 100);

      ctx.fillStyle = "#78dcff";
      ctx.font = "bold 22px Consolas, monospace";
      ctx.fillText("Cidade Sob Invasao", 18, 16);

      ctx.fillStyle = "#e8edf5";
      ctx.font = "16px Consolas, monospace";
      const liberated = this.reactors.filter((r) => !r.active).length;
      ctx.fillText(`Bairros libertados: ${liberated}/4   Vida: ${this.player.hp}/${this.player.maxHp}   Dano: ${this.player.damage}`, 18, 50);
      ctx.fillText(`Sucata: ${this.player.scrap}   Especial: ${this.player.specialCharges}   Dash: ${this.player.dashCharges}   Torretas: ${this.player.turretCharges}   Minas: ${this.player.mineCharges}`, 18, 76);

      if (this.playerInWorkbenchRange()) {
        ctx.fillStyle = "#ffe18f";
        ctx.fillText("Pressione C para abrir a oficina", this.viewW - 330, 16);
      }

      if (this.messageTimer > 0 && this.message) {
        ctx.fillStyle = "rgba(10, 14, 22, 0.85)";
        ctx.fillRect(0, this.viewH - 80, this.viewW, 80);
        ctx.fillStyle = "#f2f7ff";
        ctx.textAlign = "center";
        ctx.font = "19px Consolas, monospace";
        ctx.fillText(this.message, this.viewW / 2, this.viewH - 52);
      }
    }

    drawOverlays() {
      const ctx = this.ctx;
      if (this.state === "game_over") {
        this.drawCenterBanner("Fim de jogo", "Pressione R para reiniciar");
      } else if (this.state === "victory") {
        this.drawCenterBanner("Vitoria", "Pressione R para jogar outra vez");
      }
    }

    drawCenterBanner(title, subtitle) {
      const ctx = this.ctx;
      ctx.fillStyle = "rgba(10, 14, 22, 0.65)";
      ctx.fillRect(0, 0, this.viewW, this.viewH);
      const panelW = Math.min(640, this.viewW - 120);
      const panelH = 240;
      const panelX = (this.viewW - panelW) / 2;
      const panelY = (this.viewH - panelH) / 2;
      ctx.fillStyle = "#121826";
      ctx.fillRect(panelX, panelY, panelW, panelH);
      ctx.strokeStyle = "#78dcff";
      ctx.lineWidth = 2;
      ctx.strokeRect(panelX, panelY, panelW, panelH);
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillStyle = "#78dcff";
      ctx.font = "bold 48px Consolas, monospace";
      ctx.fillText(title, this.viewW / 2, panelY + 70);
      ctx.fillStyle = "#e8edf5";
      ctx.font = "20px Consolas, monospace";
      ctx.fillText(subtitle, this.viewW / 2, panelY + 140);
    }

    drawCraftingPanel() {
      const ctx = this.ctx;
      const panelW = Math.min(720, this.viewW - 100);
      const panelH = 360;
      const x = (this.viewW - panelW) / 2;
      const y = (this.viewH - panelH) / 2;
      ctx.fillStyle = "rgba(10, 14, 22, 0.92)";
      ctx.fillRect(0, 0, this.viewW, this.viewH);
      ctx.fillStyle = "#121826";
      ctx.fillRect(x, y, panelW, panelH);
      ctx.strokeStyle = "#78dcff";
      ctx.lineWidth = 2;
      ctx.strokeRect(x, y, panelW, panelH);

      ctx.textAlign = "left";
      ctx.textBaseline = "top";
      ctx.fillStyle = "#78dcff";
      ctx.font = "bold 28px Consolas, monospace";
      ctx.fillText("OFICINA", x + 26, y + 22);
      ctx.fillStyle = "#e8edf5";
      ctx.font = "18px Consolas, monospace";
      ctx.fillText("1 Dano +6       custo 8", x + 34, y + 80);
      ctx.fillText("2 Cadencia      custo 8", x + 34, y + 116);
      ctx.fillText("3 Vida maxima   custo 6", x + 34, y + 152);
      ctx.fillText("4 Carga especial custo 10", x + 34, y + 188);
      ctx.fillText("5 Dash extra    custo 10", x + 34, y + 224);
      ctx.fillText("6 Torreta extra custo 12", x + 34, y + 260);
      ctx.fillText("7 Mina extra    custo 8", x + 34, y + 296);

      ctx.fillStyle = "#ffe18f";
      ctx.fillText(`Sucata disponivel: ${this.player.scrap}`, x + panelW - 250, y + 80);
      ctx.fillStyle = "#a8ffef";
      ctx.fillText("Pressione C ou ESC para fechar", x + panelW - 300, y + panelH - 48);
    }

    imageReady(key) {
      const entry = this.assets[key];
      return Boolean(entry && entry.image && entry.image.complete && entry.image.naturalWidth > 0);
    }

    loop(now) {
      if (!this.lastTime) {
        this.lastTime = now;
      }
      const dt = Math.min(0.05, (now - this.lastTime) / 1000);
      this.lastTime = now;
      if (this.running) {
        this.update(dt);
        this.draw();
      }
      requestAnimationFrame(this.loop);
    }
  }

  function expandRect(rect, extraW, extraH) {
    return {
      x: rect.x - extraW / 2,
      y: rect.y - extraH / 2,
      w: rect.w + extraW,
      h: rect.h + extraH,
    };
  }

  function bulletRect(bullet) {
    return {
      x: bullet.pos.x - bullet.radius,
      y: bullet.pos.y - bullet.radius,
      w: bullet.radius * 2,
      h: bullet.radius * 2,
    };
  }

  function enemyRect(enemy) {
    return {
      x: enemy.pos.x - enemy.radius,
      y: enemy.pos.y - enemy.radius,
      w: enemy.radius * 2,
      h: enemy.radius * 2,
    };
  }

  function dropRect(drop) {
    return {
      x: drop.pos.x - 12,
      y: drop.pos.y - 12,
      w: 24,
      h: 24,
    };
  }

  function randomChoice(values, weights = null) {
    if (!weights) {
      return values[Math.floor(Math.random() * values.length)];
    }
    const total = weights.reduce((sum, value) => sum + value, 0);
    let roll = Math.random() * total;
    for (let i = 0; i < values.length; i += 1) {
      roll -= weights[i];
      if (roll <= 0) {
        return values[i];
      }
    }
    return values[values.length - 1];
  }

  function randInt(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
  }

  function randRange(min, max) {
    return Math.random() * (max - min) + min;
  }

  function rgb(color) {
    return `rgb(${color[0]}, ${color[1]}, ${color[2]})`;
  }

  const canvas = document.getElementById("game");
  new Game(canvas);
})();
