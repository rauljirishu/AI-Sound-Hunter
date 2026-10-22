# ============================================================
#  AI Sound Hunter – monster.py
#  AI enemy using Finite State Machine + A* pathfinding
# ============================================================

import pygame
import math
import random
from settings import *
from pathfinding import AStarPathfinder, smooth_path


# ---------------------------------------------------------------
# Monster AI – Finite State Machine
# ---------------------------------------------------------------
class Monster:
    """
    Enemy entity with a 5-state FSM:
      IDLE        – resting at a patrol node
      PATROL      – following patrol route
      INVESTIGATE – moving to a detected noise location
      SEARCH      – randomly searching near noise location
      CHASE       – pursuing visible player
      RETURN      – going back to patrol route

    Uses A* pathfinding to navigate around walls.
    """

    def __init__(self, patrol_nodes: list, level, difficulty: int = 0):
        # Starting position
        sc, sr = patrol_nodes[0]
        self.x = sc * TILE_SIZE + TILE_SIZE // 2
        self.y = sr * TILE_SIZE + TILE_SIZE // 2

        self.level   = level
        self.grid    = level.grid

        # Patrol
        self.patrol_nodes = [
            (c * TILE_SIZE + TILE_SIZE // 2,
             r * TILE_SIZE + TILE_SIZE // 2)
            for c, r in patrol_nodes
        ]
        self.patrol_idx  = 0
        self.patrol_wait = 0

        # A* pathfinder
        self.pathfinder = AStarPathfinder(self.grid)
        self.path: list = []
        self._path_cooldown = 0

        # FSM state
        self.state = STATE_PATROL
        self._state_timer = 0

        # Speeds (modified by difficulty)
        dmult = DIFFICULTY_SPEED_MULT[min(difficulty, 3)]
        hmult = DIFFICULTY_HEAR_MULT[min(difficulty, 3)]
        self.speed_patrol     = MONSTER_SPEED_PATROL      * dmult
        self.speed_investigate= MONSTER_SPEED_INVESTIGATE * dmult
        self.speed_chase      = MONSTER_SPEED_CHASE       * dmult
        self.speed_search     = MONSTER_SPEED_SEARCH      * dmult
        self.hear_range       = MONSTER_HEAR_RANGE        * hmult

        # Memory
        self.last_sound_pos  = None   # (x, y) of last heard sound
        self.last_player_pos = None   # last known player pos
        self.player_visible  = False

        # Search wander
        self._search_target = None
        self._search_timer  = 0

        # Attack
        self._attack_cd     = 0

        # Animation
        self._facing        = 0.0
        self._anim_frame    = 0
        self._anim_timer    = 0
        self._bob_angle     = 0.0
        self._bob           = 0.0
        self._step_timer    = 0

        # Alert indicator
        self._alert_flash   = 0

        # Sprite
        self._sprites = self._build_sprites()

    # ----------------------------------------------------------
    def _build_sprites(self) -> dict:
        size = 32
        sprites = {}

        for state_key, body_col, eye_col in [
            ("idle",       (80, 20, 120),   (180, 0, 0)),
            ("patrol",     (70, 15, 110),   (150, 0, 0)),
            ("investigate",(120, 30, 60),   (220, 100, 0)),
            ("search",     (100, 25, 80),   (200, 80, 0)),
            ("chase",      (180, 10, 10),   (255, 50, 50)),
            ("return",     (60,  10, 100),  (100, 0, 180)),
        ]:
            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            cx = cy = size // 2
            r = 14

            # Body (irregular blob)
            pygame.draw.ellipse(surf, body_col, (cx-r, cy-r+2, r*2, r*2-4))
            # Head bumps
            pygame.draw.circle(surf, body_col, (cx-5, cy-r+2), 6)
            pygame.draw.circle(surf, body_col, (cx+5, cy-r+2), 6)
            # Eyes
            pygame.draw.circle(surf, eye_col, (cx-5, cy-4), 4)
            pygame.draw.circle(surf, eye_col, (cx+5, cy-4), 4)
            # Pupils (darker)
            pygame.draw.circle(surf, (20,0,0), (cx-5, cy-4), 2)
            pygame.draw.circle(surf, (20,0,0), (cx+5, cy-4), 2)
            # Teeth
            for tx in range(cx-6, cx+8, 4):
                pygame.draw.polygon(surf, (220,220,220),
                    [(tx, cy+2), (tx+3, cy+2), (tx+1, cy+6)])
            # Outline glow
            pygame.draw.ellipse(surf, (*eye_col[:3], 120),
                                (cx-r-2, cy-r, r*2+4, r*2), 2)
            sprites[state_key] = surf

        return sprites

    # ----------------------------------------------------------
    def _state_key(self) -> str:
        return {
            STATE_IDLE:        "idle",
            STATE_PATROL:      "patrol",
            STATE_INVESTIGATE: "investigate",
            STATE_SEARCH:      "search",
            STATE_CHASE:       "chase",
            STATE_RETURN:      "return",
        }.get(self.state, "patrol")

    # ----------------------------------------------------------
    # ── UTILITY / PERCEPTION ──────────────────────────────────
    # ----------------------------------------------------------
    def can_see_player(self, player_x: float, player_y: float) -> bool:
        """Vision cone + LOS check."""
        dx = player_x - self.x
        dy = player_y - self.y
        dist = math.hypot(dx, dy)
        if dist > MONSTER_VISION_RANGE:
            return False
        angle_to = math.atan2(dy, dx)
        angle_diff = abs(math.atan2(
            math.sin(angle_to - self._facing),
            math.cos(angle_to - self._facing)))
        if angle_diff > math.radians(MONSTER_VISION_ANGLE):
            return False
        # Line-of-sight
        return self._has_los(self.x, self.y, player_x, player_y)

    def _has_los(self, ax, ay, bx, by) -> bool:
        ac = int(ax // TILE_SIZE); ar = int(ay // TILE_SIZE)
        bc = int(bx // TILE_SIZE); br = int(by // TILE_SIZE)
        dx = abs(bc - ac); sx = 1 if ac < bc else -1
        dy = abs(br - ar); sy = 1 if ar < br else -1
        err = dx - dy
        cx, cy = ac, ar
        rows = len(self.grid); cols = len(self.grid[0])
        for _ in range(300):
            if cx == bc and cy == br:
                return True
            if 0 <= cy < rows and 0 <= cx < cols:
                if self.grid[cy][cx] == TILE_WALL:
                    return False
            e2 = 2 * err
            if e2 > -dy: err -= dy; cx += sx
            if e2 <  dx: err += dx; cy += sy
        return False

    def can_hear(self, intensity: float, source_x: float, source_y: float) -> bool:
        dist = math.hypot(self.x - source_x, self.y - source_y)
        threshold = self.hear_range * (intensity / NOISE_MAX)
        return dist <= threshold

    # ----------------------------------------------------------
    # ── PATHFINDING HELPERS ───────────────────────────────────
    # ----------------------------------------------------------
    def _request_path(self, goal_x: float, goal_y: float):
        if self._path_cooldown > 0:
            return
        raw = self.pathfinder.find_path((self.x, self.y), (goal_x, goal_y))
        if raw:
            self.path = smooth_path(raw, self.grid)
        else:
            self.path = []
        self._path_cooldown = 20   # re-plan at most every 20 frames

    def _move_along_path(self, speed: float):
        if not self.path:
            return
        tx, ty = self.path[0]
        dx = tx - self.x
        dy = ty - self.y
        dist = math.hypot(dx, dy)
        if dist < speed + 2:
            self.path.pop(0)
            return
        self._facing = math.atan2(dy, dx)
        self.x += (dx / dist) * speed
        self.y += (dy / dist) * speed

    def _move_toward(self, tx: float, ty: float, speed: float):
        dx = tx - self.x
        dy = ty - self.y
        dist = math.hypot(dx, dy)
        if dist < 1:
            return
        self._facing = math.atan2(dy, dx)
        self.x += (dx / dist) * speed
        self.y += (dy / dist) * speed

    # ----------------------------------------------------------
    # ── FINITE STATE MACHINE ──────────────────────────────────
    # ----------------------------------------------------------
    def update(self, player_x: float, player_y: float,
               noise_sys, dt: float = 1.0) -> bool:
        """
        Main FSM update.
        Returns True if the monster attacks the player this frame.
        """
        self._path_cooldown  = max(0, self._path_cooldown - 1)
        self._attack_cd      = max(0, self._attack_cd - 1)
        self._state_timer   += 1
        self._alert_flash    = max(0, self._alert_flash - 1)

        # Bob
        self._bob_angle += 0.15
        self._bob = math.sin(self._bob_angle) * 2

        # Update pathfinder if grid changed
        self.pathfinder.update_grid(self.level.grid)

        # ── PERCEPTION ───────────────────────────────────────
        self.player_visible = self.can_see_player(player_x, player_y)

        # Check noise events
        noise_intensity, best_ev = noise_sys.perceived_at(
            self.x, self.y, self.grid)
        heard_sound = (best_ev is not None and
                       self.can_hear(best_ev.intensity,
                                     best_ev.x, best_ev.y))

        # ── TRANSITIONS ──────────────────────────────────────
        attacked = False

        if self.state == STATE_IDLE:
            attacked = self._state_idle(player_x, player_y, heard_sound, best_ev)

        elif self.state == STATE_PATROL:
            attacked = self._state_patrol(player_x, player_y, heard_sound, best_ev)

        elif self.state == STATE_INVESTIGATE:
            attacked = self._state_investigate(player_x, player_y, heard_sound, best_ev)

        elif self.state == STATE_SEARCH:
            attacked = self._state_search(player_x, player_y, heard_sound, best_ev)

        elif self.state == STATE_CHASE:
            attacked = self._state_chase(player_x, player_y, heard_sound, best_ev)

        elif self.state == STATE_RETURN:
            attacked = self._state_return(player_x, player_y, heard_sound, best_ev)

        return attacked

    # ── Individual state handlers ─────────────────────────────

    def _transition(self, new_state: str):
        self.state = new_state
        self._state_timer = 0
        self.path = []

    def _state_idle(self, px, py, heard, ev) -> bool:
        if self.player_visible:
            self._transition(STATE_CHASE)
            self._alert_flash = 60
            self.last_player_pos = (px, py)
        elif heard and ev:
            self.last_sound_pos = (ev.x, ev.y)
            self._transition(STATE_INVESTIGATE)
            self._alert_flash = 30
        elif self._state_timer > MONSTER_PATROL_WAIT:
            self._transition(STATE_PATROL)
        return False

    def _state_patrol(self, px, py, heard, ev) -> bool:
        if self.player_visible:
            self._transition(STATE_CHASE)
            self._alert_flash = 60
            self.last_player_pos = (px, py)
            return False
        if heard and ev:
            self.last_sound_pos = (ev.x, ev.y)
            self._transition(STATE_INVESTIGATE)
            self._alert_flash = 30
            return False

        # Follow patrol route
        target = self.patrol_nodes[self.patrol_idx]
        dist   = math.hypot(target[0]-self.x, target[1]-self.y)

        if dist < self.speed_patrol * 3:
            # Reached node
            if self.patrol_wait < MONSTER_PATROL_WAIT:
                self.patrol_wait += 1
            else:
                self.patrol_wait = 0
                self.patrol_idx  = (self.patrol_idx + 1) % len(self.patrol_nodes)
        else:
            self._request_path(target[0], target[1])
            if self.path:
                self._move_along_path(self.speed_patrol)
            else:
                self._move_toward(target[0], target[1], self.speed_patrol)

        return False

    def _state_investigate(self, px, py, heard, ev) -> bool:
        if self.player_visible:
            self._transition(STATE_CHASE)
            self._alert_flash = 60
            self.last_player_pos = (px, py)
            return False

        # Update sound target if louder event found
        if heard and ev and ev.intensity > 10:
            self.last_sound_pos = (ev.x, ev.y)

        if self.last_sound_pos is None:
            self._transition(STATE_RETURN)
            return False

        tx, ty = self.last_sound_pos
        dist   = math.hypot(tx - self.x, ty - self.y)

        if dist < 24:
            # Arrived at sound loc → search
            self._transition(STATE_SEARCH)
            self._search_timer  = MONSTER_SEARCH_TIME
            self._search_target = None
        else:
            self._request_path(tx, ty)
            if self.path:
                self._move_along_path(self.speed_investigate)
            else:
                self._move_toward(tx, ty, self.speed_investigate)

        return False

    def _state_search(self, px, py, heard, ev) -> bool:
        if self.player_visible:
            self._transition(STATE_CHASE)
            self._alert_flash = 60
            self.last_player_pos = (px, py)
            return False
        if heard and ev and ev.intensity > 15:
            self.last_sound_pos = (ev.x, ev.y)
            self._transition(STATE_INVESTIGATE)
            return False

        self._search_timer -= 1
        if self._search_timer <= 0:
            self._transition(STATE_RETURN)
            return False

        # Wander randomly near last sound pos
        if (self._search_target is None or
                math.hypot(self._search_target[0]-self.x,
                           self._search_target[1]-self.y) < 20):
            if self.last_sound_pos:
                rx = self.last_sound_pos[0] + random.uniform(
                    -MONSTER_SEARCH_RADIUS, MONSTER_SEARCH_RADIUS)
                ry = self.last_sound_pos[1] + random.uniform(
                    -MONSTER_SEARCH_RADIUS, MONSTER_SEARCH_RADIUS)
                self._search_target = (rx, ry)

        if self._search_target:
            self._request_path(self._search_target[0], self._search_target[1])
            if self.path:
                self._move_along_path(self.speed_search)
            else:
                self._move_toward(self._search_target[0],
                                  self._search_target[1], self.speed_search)

        return False

    def _state_chase(self, px, py, heard, ev) -> bool:
        self.last_player_pos = (px, py)

        if not self.player_visible:
            # Lost sight – go to last known position
            dist = math.hypot(px - self.x, py - self.y)
            if dist > MONSTER_VISION_RANGE * 1.5:
                self._transition(STATE_INVESTIGATE)
                self.last_sound_pos = self.last_player_pos
                return False

        # Attack check
        dist = math.hypot(px - self.x, py - self.y)
        if dist <= MONSTER_CAPTURE_RADIUS:
            if self._attack_cd <= 0:
                self._attack_cd = MONSTER_ATTACK_COOLDOWN
                return True   # HIT
        else:
            self._request_path(px, py)
            if self.path:
                self._move_along_path(self.speed_chase)
            else:
                self._move_toward(px, py, self.speed_chase)

        return False

    def _state_return(self, px, py, heard, ev) -> bool:
        if self.player_visible:
            self._transition(STATE_CHASE)
            self._alert_flash = 60
            self.last_player_pos = (px, py)
            return False
        if heard and ev and ev.intensity > 20:
            self.last_sound_pos = (ev.x, ev.y)
            self._transition(STATE_INVESTIGATE)
            return False

        target = self.patrol_nodes[self.patrol_idx]
        dist   = math.hypot(target[0]-self.x, target[1]-self.y)
        if dist < 24:
            self._transition(STATE_IDLE)
        else:
            self._request_path(target[0], target[1])
            if self.path:
                self._move_along_path(self.speed_patrol)
            else:
                self._move_toward(target[0], target[1], self.speed_patrol)

        return False

    # ----------------------------------------------------------
    # ── DRAWING ───────────────────────────────────────────────
    # ----------------------------------------------------------
    def draw(self, surface: pygame.Surface, camera_x: float, camera_y: float,
             debug: bool = False):
        sx = int(self.x - camera_x)
        sy = int(self.y - camera_y + self._bob)

        # Only draw if on-screen (with margin)
        w, h = surface.get_size()
        if sx < -60 or sx > w + 60 or sy < -60 or sy > h + 60:
            return

        # Glow
        state_glow = {
            STATE_IDLE:        (100, 0, 150, 30),
            STATE_PATROL:      (80,  0, 120, 30),
            STATE_INVESTIGATE: (200, 80, 0, 50),
            STATE_SEARCH:      (180, 60, 0, 40),
            STATE_CHASE:       (220, 0, 0,  70),
            STATE_RETURN:      (60,  0, 150, 30),
        }
        g_col = state_glow.get(self.state, (80, 0, 120, 30))
        for r in range(32, 0, -4):
            gsurf = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
            pygame.draw.circle(gsurf, g_col, (r, r), r)
            surface.blit(gsurf, (sx - r, sy - r))

        # Alert ! indicator
        if self._alert_flash > 0 and (self._alert_flash // 4) % 2 == 0:
            font = pygame.font.SysFont("Arial", 18, bold=True)
            col  = (255, 50, 50) if self.state == STATE_CHASE else (255, 180, 0)
            txt  = font.render("!", True, col)
            surface.blit(txt, (sx + 10, sy - 34))

        # Sprite
        spr = self._sprites.get(self._state_key(), self._sprites["patrol"])
        surface.blit(spr, (sx - 16, sy - 16))

        # Debug overlay
        if debug:
            self._draw_debug(surface, sx, sy, camera_x, camera_y)

    def _draw_debug(self, surface, sx, sy, camera_x, camera_y):
        # Vision cone
        half_a = math.radians(MONSTER_VISION_ANGLE)
        n = 16
        pts = [(sx, sy)]
        for i in range(n + 1):
            a = self._facing - half_a + (2 * half_a * i / n)
            r = MONSTER_VISION_RANGE
            pts.append((sx + math.cos(a) * r, sy + math.sin(a) * r))
        vsurf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        if len(pts) >= 3:
            pygame.draw.polygon(vsurf, (255, 255, 0, 30), pts)
            pygame.draw.polygon(vsurf, (255, 255, 0, 80), pts, 1)
        surface.blit(vsurf, (0, 0))

        # Hear range circle
        pygame.draw.circle(surface, (0, 180, 255), (sx, sy),
                           int(self.hear_range), 1)

        # Path
        prev = (sx, sy)
        for wp in self.path:
            wx = int(wp[0] - camera_x)
            wy = int(wp[1] - camera_y)
            pygame.draw.line(surface, (255, 80, 80), prev, (wx, wy), 1)
            pygame.draw.circle(surface, (255, 80, 80), (wx, wy), 3)
            prev = (wx, wy)

        # State label
        font = pygame.font.SysFont("Consolas", 11)
        txt  = font.render(f"[{self.state}]", True, (0, 255, 200))
        surface.blit(txt, (sx - 20, sy + 20))

        # Last sound pos
        if self.last_sound_pos:
            lx = int(self.last_sound_pos[0] - camera_x)
            ly = int(self.last_sound_pos[1] - camera_y)
            pygame.draw.circle(surface, (255, 140, 0), (lx, ly), 6, 2)

    # ----------------------------------------------------------
    def update_difficulty(self, level: int):
        dmult = DIFFICULTY_SPEED_MULT[min(level, 3)]
        hmult = DIFFICULTY_HEAR_MULT[min(level, 3)]
        self.speed_patrol      = MONSTER_SPEED_PATROL      * dmult
        self.speed_investigate = MONSTER_SPEED_INVESTIGATE * dmult
        self.speed_chase       = MONSTER_SPEED_CHASE       * dmult
        self.speed_search      = MONSTER_SPEED_SEARCH      * dmult
        self.hear_range        = MONSTER_HEAR_RANGE        * hmult
