# ============================================================
#  AI Sound Hunter – level.py
#  Map definition, tile rendering, door/key/exit logic
# ============================================================

import pygame
import random
import math
from settings import *


# ---------------------------------------------------------------
# Procedural level layout  (50 × 35 tiles)
# ---------------------------------------------------------------
# Legend used below:
#   W = TILE_WALL (1)
#   . = TILE_FLOOR (0)
#   D = TILE_DOOR (2)
#   K = TILE_KEY (3)
#   E = TILE_EXIT (4)
#   X = TILE_DECORATION (5)
# ---------------------------------------------------------------
RAW_MAP = [
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
    "W........W.......W.......W.......W.......W.........W",
    "W........W.......W.......W.......W.......W.........W",
    "W........D.......D.......D.......D.......D.........W",
    "W........W.......W.......W.......W.......W.........W",
    "W........W.......W...X...W.......W.......W.........W",
    "WWWWWWWWWW.......WWWWWWWWW.......WWWWWWWW.........W",
    "W.......W.........W.......W.......W.......WWWWWWWWWW",
    "W.......W.........W.......W.......W.......W........W",
    "W...K...D.........D.......D.......D.......D........W",
    "W.......W.........W.......W.......W.......W........W",
    "W.......W.........W...X...W.......W.......W........W",
    "WWWWWWWWWWWWWWWWWWW.......WWWWWWWWWWWWWWWWWWWWWWWW",
    "W..........W.......W.......W.......W...............W",
    "W..........W.......W.......W.......W...............W",
    "W..........D.......D...K...D.......D...............W",
    "W..........W.......W.......W.......W...............W",
    "W....X.....W.......W.......W.......W...............W",
    "WWWWWWWWWWWW.......WWWWWWWWW.......WWWWWWWWWWWWWWWW",
    "W..........W.......W.......W.......W...............W",
    "W..........W.......W.......W.......W...............W",
    "W..........D.......D.......D...K...D...............W",
    "W..........W.......W.......W.......W...............W",
    "W..........W.......W...X...W.......W...............W",
    "WWWWWWWWWWWWWWWWWWWW.......WWWWWWWWW.......WWWWWWWW",
    "W.........W..........W.......W.......W.............W",
    "W.........W..........W.......W.......W.............W",
    "W.........D..........D.......D.......D.............W",
    "W.........W..........W.......W.......W.............W",
    "W.........W..........W.......W.......W.....X.......W",
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWW.......WWWWWWWWWWWWWW",
    "W.............................................E.....W",
    "W..................................................W",
    "W..................................................W",
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
]

CHAR_MAP = {'W': TILE_WALL, '.': TILE_FLOOR, 'D': TILE_DOOR,
            'K': TILE_KEY,  'E': TILE_EXIT,  'X': TILE_DECORATION}

# Player spawn (col, row) in tile coords
PLAYER_SPAWN = (2, 2)
# Monster patrol nodes (tile coords)
MONSTER_PATROL = [
    (45, 2), (45, 16), (45, 30), (25, 30),
    (25, 16), (25, 2),  (10, 2),  (10, 16),
]


# ---------------------------------------------------------------
# Colour palettes for procedural tile drawing
# ---------------------------------------------------------------
FLOOR_COLOURS  = [(18, 16, 30), (22, 20, 38), (16, 15, 28)]
WALL_COLOURS   = [(50, 30, 80), (60, 35, 95), (45, 25, 70)]
DOOR_COLOUR    = (120, 60, 0)
DOOR_OPEN_COL  = (80, 40, 0)
KEY_COLOUR     = (255, 200, 0)
EXIT_COLOUR    = (0, 220, 120)
DECO_COLOURS   = [(55, 30, 90), (45, 20, 75)]


# ---------------------------------------------------------------
class Level:
    """Manages the map grid, tile drawing, interactive objects."""

    def __init__(self, screen: pygame.Surface):
        self.screen = screen

        # Build numeric grid from RAW_MAP
        self.grid = []           # list[list[int]]
        self.key_positions  = []
        self.door_positions = []
        self.exit_position  = None
        self.decoration_positions = []

        for row_idx, row_str in enumerate(RAW_MAP):
            row = []
            for col_idx, ch in enumerate(row_str):
                tile = CHAR_MAP.get(ch, TILE_FLOOR)
                if tile == TILE_KEY:
                    self.key_positions.append((col_idx, row_idx))
                    tile = TILE_FLOOR   # key floats above floor
                elif tile == TILE_EXIT:
                    self.exit_position = (col_idx, row_idx)
                    tile = TILE_FLOOR
                elif tile == TILE_DOOR:
                    self.door_positions.append([col_idx, row_idx, False])  # [c,r,open?]
                elif tile == TILE_DECORATION:
                    self.decoration_positions.append((col_idx, row_idx))
                    tile = TILE_FLOOR
                row.append(tile)
            self.grid.append(row)

        self.rows = len(self.grid)
        self.cols = len(self.grid[0]) if self.rows else 0

        # Keys still on the map
        self.keys_remaining = list(self.key_positions)
        # Collected key count
        self.keys_collected = 0
        # Doors that have been opened
        self.open_doors = set()

        # Pre-render tile cache (surface per tile type)
        self._tile_cache = {}
        self._build_tile_cache()

        # Particle effects
        self.particles = []

        # Key bob animation
        self._key_anim = 0

        # Exit glow animation
        self._exit_anim = 0

    # ----------------------------------------------------------
    def _build_tile_cache(self):
        T = TILE_SIZE
        rng = random.Random(42)

        def noise_surface(base_cols, size=(T, T)):
            surf = pygame.Surface(size)
            base = rng.choice(base_cols)
            surf.fill(base)
            # subtle noise
            for _ in range(size[0] * size[1] // 8):
                x = rng.randint(0, size[0]-1)
                y = rng.randint(0, size[1]-1)
                v = rng.randint(-10, 10)
                c = tuple(max(0, min(255, base[i] + v)) for i in range(3))
                surf.set_at((x, y), c)
            return surf

        # Floor
        self._tile_cache[TILE_FLOOR] = noise_surface(FLOOR_COLOURS)

        # Wall
        wsurf = noise_surface(WALL_COLOURS)
        # brick lines
        pygame.draw.line(wsurf, (30,15,50), (0, T//2), (T, T//2), 1)
        pygame.draw.line(wsurf, (30,15,50), (T//2, 0), (T//2, T//2), 1)
        pygame.draw.line(wsurf, (30,15,50), (0, T-1), (T, T-1), 1)
        self._tile_cache[TILE_WALL] = wsurf

        # Door (closed)
        dsurf = pygame.Surface((T, T))
        dsurf.fill(DOOR_COLOUR)
        pygame.draw.rect(dsurf, (80, 40, 0), (2, 2, T-4, T-4), 2)
        pygame.draw.circle(dsurf, (200,180,0), (T-6, T//2), 3)
        self._tile_cache['door_closed'] = dsurf

        # Door (open)
        osurf = noise_surface(FLOOR_COLOURS)
        pygame.draw.rect(osurf, DOOR_OPEN_COL, (0, 0, 4, T))
        self._tile_cache['door_open'] = osurf

        # Decoration (barrel / crate look)
        xsurf = noise_surface(DECO_COLOURS)
        pygame.draw.rect(xsurf, (80,50,100), (4, 4, T-8, T-8))
        pygame.draw.rect(xsurf, (60,35,80),  (4, 4, T-8, T-8), 2)
        self._tile_cache[TILE_DECORATION] = xsurf

    # ----------------------------------------------------------
    def pixel_to_tile(self, px: float, py: float) -> tuple:
        return (int(px // TILE_SIZE), int(py // TILE_SIZE))

    def tile_to_pixel_center(self, col: int, row: int) -> tuple:
        return (col * TILE_SIZE + TILE_SIZE // 2,
                row * TILE_SIZE + TILE_SIZE // 2)

    def is_wall(self, col: int, row: int) -> bool:
        if col < 0 or col >= self.cols or row < 0 or row >= self.rows:
            return True
        return self.grid[row][col] == TILE_WALL

    def is_solid(self, col: int, row: int) -> bool:
        """Walls AND closed doors block movement."""
        if col < 0 or col >= self.cols or row < 0 or row >= self.rows:
            return True
        tile = self.grid[row][col]
        if tile == TILE_WALL:
            return True
        if tile == TILE_DOOR:
            idx = self._door_index(col, row)
            if idx >= 0 and not self.door_positions[idx][2]:
                return True
        return False

    def _door_index(self, col: int, row: int) -> int:
        for i, (dc, dr, _) in enumerate(self.door_positions):
            if dc == col and dr == row:
                return i
        return -1

    # ----------------------------------------------------------
    def try_open_door(self, px: float, py: float, interact_radius: float = 40.0):
        """Open nearest door if within range. Returns True if opened."""
        for door in self.door_positions:
            if door[2]:
                continue
            dc, dr = door[0], door[1]
            dpx = dc * TILE_SIZE + TILE_SIZE // 2
            dpy = dr * TILE_SIZE + TILE_SIZE // 2
            dist = math.hypot(px - dpx, py - dpy)
            if dist <= interact_radius:
                door[2] = True
                self.grid[dr][dc] = TILE_FLOOR
                self.open_doors.add((dc, dr))
                # Spawn particles
                for _ in range(8):
                    self.particles.append({
                        'x': dpx + random.randint(-10, 10),
                        'y': dpy + random.randint(-10, 10),
                        'vx': random.uniform(-1.5, 1.5),
                        'vy': random.uniform(-2, -0.5),
                        'life': 30,
                        'col': DOOR_COLOUR,
                    })
                return True
        return False

    def try_collect_key(self, px: float, py: float, collect_radius: float = 24.0):
        """Collect nearest key if in range. Returns True if collected."""
        for pos in list(self.keys_remaining):
            kc, kr = pos
            kpx = kc * TILE_SIZE + TILE_SIZE // 2
            kpy = kr * TILE_SIZE + TILE_SIZE // 2
            dist = math.hypot(px - kpx, py - kpy)
            if dist <= collect_radius:
                self.keys_remaining.remove(pos)
                self.keys_collected += 1
                # Gold sparkle
                for _ in range(15):
                    self.particles.append({
                        'x': kpx, 'y': kpy,
                        'vx': random.uniform(-2, 2),
                        'vy': random.uniform(-3, 0),
                        'life': 40,
                        'col': KEY_COLOUR,
                    })
                return True
        return False

    def check_exit(self, px: float, py: float, radius: float = 28.0) -> bool:
        """Returns True if player is at the exit AND all keys collected."""
        if self.keys_collected < len(self.key_positions):
            return False
        if self.exit_position is None:
            return False
        ec, er = self.exit_position
        epx = ec * TILE_SIZE + TILE_SIZE // 2
        epy = er * TILE_SIZE + TILE_SIZE // 2
        return math.hypot(px - epx, py - epy) <= radius

    # ----------------------------------------------------------
    def update(self, dt: float):
        self._key_anim  = (self._key_anim  + 0.08) % (2 * math.pi)
        self._exit_anim = (self._exit_anim + 0.05) % (2 * math.pi)

        # Update particles
        for p in self.particles[:]:
            p['x']   += p['vx']
            p['y']   += p['vy']
            p['life'] -= 1
            if p['life'] <= 0:
                self.particles.remove(p)

    # ----------------------------------------------------------
    def draw(self, camera_x: float, camera_y: float):
        """Draw visible tiles. camera_x/y are world pixel offsets."""
        sw, sh = self.screen.get_size()

        start_col = max(0, int(camera_x // TILE_SIZE))
        start_row = max(0, int(camera_y // TILE_SIZE))
        end_col   = min(self.cols, start_col + sw // TILE_SIZE + 2)
        end_row   = min(self.rows, start_row + sh // TILE_SIZE + 2)

        T = TILE_SIZE

        for row in range(start_row, end_row):
            for col in range(start_col, end_col):
                sx = col * T - camera_x
                sy = row * T - camera_y
                tile = self.grid[row][col]

                if tile == TILE_WALL:
                    self.screen.blit(self._tile_cache[TILE_WALL], (sx, sy))
                elif tile == TILE_DOOR:
                    idx = self._door_index(col, row)
                    if idx >= 0 and self.door_positions[idx][2]:
                        self.screen.blit(self._tile_cache['door_open'], (sx, sy))
                    else:
                        self.screen.blit(self._tile_cache['door_closed'], (sx, sy))
                else:
                    self.screen.blit(self._tile_cache[TILE_FLOOR], (sx, sy))

        # Decorations
        for dc, dr in self.decoration_positions:
            sx = dc * T - camera_x
            sy = dr * T - camera_y
            if -T < sx < sw and -T < sy < sh:
                self.screen.blit(self._tile_cache[TILE_DECORATION], (sx, sy))

        # Keys (bobbing)
        bob = int(math.sin(self._key_anim) * 3)
        for kc, kr in self.keys_remaining:
            sx = kc * T - camera_x + T // 2
            sy = kr * T - camera_y + T // 2 + bob
            if -T < sx < sw and -T < sy < sh:
                self._draw_key(sx, sy)

        # Exit
        if self.exit_position:
            ec, er = self.exit_position
            sx = ec * T - camera_x + T // 2
            sy = er * T - camera_y + T // 2
            if -T < sx < sw and -T < sy < sh:
                self._draw_exit(sx, sy)

        # Particles
        for p in self.particles:
            sx = int(p['x'] - camera_x)
            sy = int(p['y'] - camera_y)
            alpha = int(255 * (p['life'] / 40))
            col = (*p['col'], alpha)
            psurf = pygame.Surface((4, 4), pygame.SRCALPHA)
            psurf.fill(col)
            self.screen.blit(psurf, (sx - 2, sy - 2))

    # ----------------------------------------------------------
    def _draw_key(self, sx: int, sy: int):
        # Glow
        glow = pygame.Surface((40, 40), pygame.SRCALPHA)
        for r in range(20, 0, -2):
            a = int(80 * (1 - r / 20))
            pygame.draw.circle(glow, (255, 200, 0, a), (20, 20), r)
        self.screen.blit(glow, (sx - 20, sy - 20))
        # Key body
        pygame.draw.circle(self.screen, KEY_COLOUR, (sx - 4, sy), 7)
        pygame.draw.circle(self.screen, (200, 150, 0), (sx - 4, sy), 7, 2)
        pygame.draw.rect(self.screen, KEY_COLOUR, (sx - 2, sy - 2, 12, 4))
        pygame.draw.rect(self.screen, KEY_COLOUR, (sx + 4, sy,  3,  5))
        pygame.draw.rect(self.screen, KEY_COLOUR, (sx + 8, sy,  3,  4))

    def _draw_exit(self, sx: int, sy: int):
        # Pulsing glow
        pulse = 0.5 + 0.5 * math.sin(self._exit_anim)
        for r in range(36, 0, -3):
            a = int(120 * pulse * (1 - r / 36))
            gsurf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(gsurf, (0, 220, 120, a), (r, r), r)
            self.screen.blit(gsurf, (sx - r, sy - r))
        pygame.draw.circle(self.screen, EXIT_COLOUR, (sx, sy), 16)
        # Arrow
        pts = [(sx - 6, sy - 8), (sx + 6, sy), (sx - 6, sy + 8)]
        pygame.draw.polygon(self.screen, WHITE, pts)

    # ----------------------------------------------------------
    def draw_minimap(self, surface: pygame.Surface, rect: pygame.Rect,
                     player_px: tuple, monster_px: tuple, camera_x: float, camera_y: float):
        """Tiny overview minimap in top-right corner."""
        mm = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        mm.fill((0, 0, 0, 180))

        scale_x = rect.width  / (self.cols * TILE_SIZE)
        scale_y = rect.height / (self.rows * TILE_SIZE)
        tw = max(1, int(TILE_SIZE * scale_x))
        th = max(1, int(TILE_SIZE * scale_y))

        for row in range(self.rows):
            for col in range(self.cols):
                tile = self.grid[row][col]
                if tile == TILE_WALL:
                    col_c = (60, 30, 90)
                elif tile == TILE_DOOR:
                    col_c = (140, 80, 0)
                else:
                    col_c = (25, 20, 40)
                mx = int(col * TILE_SIZE * scale_x)
                my = int(row * TILE_SIZE * scale_y)
                pygame.draw.rect(mm, col_c, (mx, my, max(1,tw-1), max(1,th-1)))

        # Keys
        for kc, kr in self.keys_remaining:
            mx = int(kc * TILE_SIZE * scale_x)
            my = int(kr * TILE_SIZE * scale_y)
            pygame.draw.circle(mm, KEY_COLOUR, (mx, my), 2)

        # Exit
        if self.exit_position:
            ec, er = self.exit_position
            mx = int(ec * TILE_SIZE * scale_x)
            my = int(er * TILE_SIZE * scale_y)
            pygame.draw.circle(mm, EXIT_COLOUR, (mx, my), 3)

        # Player dot
        pmx = int(player_px[0] * scale_x)
        pmy = int(player_px[1] * scale_y)
        pygame.draw.circle(mm, (100, 200, 255), (pmx, pmy), 3)

        # Monster dot
        if monster_px:
            mmx = int(monster_px[0] * scale_x)
            mmy = int(monster_px[1] * scale_y)
            pygame.draw.circle(mm, BRIGHT_RED, (mmx, mmy), 3)

        pygame.draw.rect(mm, PURPLE, (0, 0, rect.width, rect.height), 1)
        surface.blit(mm, rect.topleft)
