# ============================================================
#  AI Sound Hunter – player.py
#  Player entity: movement, collision, flashlight, noise emission
# ============================================================

import pygame
import math
import random
from settings import *


class Player:
    """
    Handles player movement, collision detection, health,
    flashlight battery, and noise generation.
    """

    def __init__(self, spawn_col: int, spawn_row: int, level, sound_system):
        self.x = spawn_col * TILE_SIZE + TILE_SIZE // 2
        self.y = spawn_row * TILE_SIZE + TILE_SIZE // 2

        self.level   = level
        self.sounds  = sound_system

        # Movement
        self.speed   = PLAYER_SPEED_WALK
        self.is_running = False
        self.vx = 0.0
        self.vy = 0.0

        # Health
        self.health  = PLAYER_MAX_HEALTH
        self.alive   = True
        self.hurt_timer = 0       # invulnerability frames after being hit
        self.HURT_IFRAMES = 90

        # Flashlight
        self.flashlight_on  = True
        self.flashlight_bat = FLASHLIGHT_MAX  # %
        self.flash_radius   = FLASHLIGHT_RADIUS

        # Noise
        self.noise_level    = 0.0
        self._step_timer    = 0
        self._step_interval = 22  # frames between footstep sounds

        # Animation
        self._anim_frame  = 0
        self._anim_timer  = 0
        self._facing      = 0.0  # radians, 0 = right
        self._bob         = 0.0
        self._bob_angle   = 0.0

        # Sprite surface (procedural)
        self._sprite    = self._build_sprite()
        self._hurt_surf = self._build_hurt_sprite()

        # Footstep cooldowns
        self._walk_sound_timer = 0
        self._run_sound_timer  = 0

        # Interact cooldown
        self._interact_cd = 0

        # Trail particles (footsteps visual)
        self.trail: list = []

    # ----------------------------------------------------------
    def _build_sprite(self) -> pygame.Surface:
        size = PLAYER_RADIUS * 2 + 8
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        cx = cy = size // 2
        r = PLAYER_RADIUS
        # Body
        pygame.draw.circle(surf, (60, 120, 200), (cx, cy), r)
        pygame.draw.circle(surf, (100, 160, 255), (cx, cy - 2), r - 3)
        # Visor
        pygame.draw.ellipse(surf, (180, 230, 255), (cx - 5, cy - 5, 10, 7))
        # Outline
        pygame.draw.circle(surf, (30, 70, 150), (cx, cy), r, 2)
        return surf

    def _build_hurt_sprite(self) -> pygame.Surface:
        size = PLAYER_RADIUS * 2 + 8
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        cx = cy = size // 2
        r = PLAYER_RADIUS
        pygame.draw.circle(surf, (200, 40, 40), (cx, cy), r)
        pygame.draw.circle(surf, (255, 80, 80), (cx, cy - 2), r - 3)
        pygame.draw.ellipse(surf, (255, 180, 180), (cx - 5, cy - 5, 10, 7))
        pygame.draw.circle(surf, (150, 0, 0), (cx, cy), r, 2)
        return surf

    # ----------------------------------------------------------
    def handle_input(self, keys):
        dx = dy = 0.0

        if keys[pygame.K_a] or keys[pygame.K_LEFT]:  dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx += 1
        if keys[pygame.K_w] or keys[pygame.K_UP]:    dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:  dy += 1

        self.is_running = (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT])
        self.speed = PLAYER_SPEED_RUN if self.is_running else PLAYER_SPEED_WALK

        # Normalise diagonal
        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071

        self.vx = dx * self.speed
        self.vy = dy * self.speed

        # Facing angle
        if dx != 0 or dy != 0:
            self._facing = math.atan2(dy, dx)

    # ----------------------------------------------------------
    def _move_and_collide(self):
        """Separate x/y collision resolution."""
        r = PLAYER_RADIUS

        # Move X
        new_x = self.x + self.vx
        if not self._overlaps_wall(new_x, self.y, r):
            self.x = new_x

        # Move Y
        new_y = self.y + self.vy
        if not self._overlaps_wall(self.x, new_y, r):
            self.y = new_y

    def _overlaps_wall(self, px: float, py: float, r: float) -> bool:
        """Check 4 cardinal points around the player circle."""
        for dx, dy in [(r,0),(-r,0),(0,r),(0,-r),(r*.7,r*.7),(-r*.7,r*.7),(r*.7,-r*.7),(-r*.7,-r*.7)]:
            col = int((px + dx) // TILE_SIZE)
            row = int((py + dy) // TILE_SIZE)
            if self.level.is_solid(col, row):
                return True
        return False

    # ----------------------------------------------------------
    def update(self, noise_sys, dt: float = 1.0):
        if not self.alive:
            return

        # Hurt invulnerability timer
        if self.hurt_timer > 0:
            self.hurt_timer -= 1

        # Movement
        self._move_and_collide()

        moving = abs(self.vx) > 0.01 or abs(self.vy) > 0.01

        # Bob animation
        if moving:
            self._bob_angle += 0.25
            self._bob = math.sin(self._bob_angle) * 3
        else:
            self._bob *= 0.8

        # Noise generation
        if moving:
            if self.is_running:
                self.noise_level = min(NOISE_MAX, self.noise_level + NOISE_RUN * 0.06)
                noise_sys.emit(self.x, self.y, NOISE_RUN * 0.06, "run")
            else:
                self.noise_level = min(NOISE_MAX, self.noise_level + NOISE_WALK * 0.04)
                noise_sys.emit(self.x, self.y, NOISE_WALK * 0.04, "walk")
        else:
            self.noise_level *= NOISE_DECAY

        # Footstep trail particles
        if moving:
            self._step_timer += 1
            interval = self._step_interval // (2 if self.is_running else 1)
            if self._step_timer >= interval:
                self._step_timer = 0
                if self.is_running:
                    self.sounds.play("footstep_run", volume=0.4)
                else:
                    self.sounds.play("footstep_walk", volume=0.25)
                # Foot particle
                self.trail.append({
                    'x': self.x + random.uniform(-4, 4),
                    'y': self.y + random.uniform(-4, 4),
                    'life': 20, 'max_life': 20,
                })

        # Update trail
        for t in self.trail[:]:
            t['life'] -= 1
            if t['life'] <= 0:
                self.trail.remove(t)

        # Flashlight battery
        if self.flashlight_on:
            self.flashlight_bat = max(0, self.flashlight_bat - FLASHLIGHT_DRAIN)
            if self.flashlight_bat <= 0:
                self.flashlight_on = False
        else:
            self.flashlight_bat = min(FLASHLIGHT_MAX, self.flashlight_bat + FLASHLIGHT_RECHARGE)

        # Interact cooldown
        if self._interact_cd > 0:
            self._interact_cd -= 1

    # ----------------------------------------------------------
    def interact(self, noise_sys) -> str:
        """Try door/key interaction. Returns event type or ''."""
        if self._interact_cd > 0:
            return ''
        self._interact_cd = 30

        # Door
        if self.level.try_open_door(self.x, self.y):
            noise_sys.emit(self.x, self.y, NOISE_DOOR, "door")
            self.noise_level = min(NOISE_MAX, self.noise_level + NOISE_DOOR)
            self.sounds.play("door_open", volume=0.6)
            return 'door'

        return ''

    def auto_collect_key(self, noise_sys):
        """Auto-collect keys when walked over."""
        if self.level.try_collect_key(self.x, self.y):
            noise_sys.emit(self.x, self.y, NOISE_KEY, "key")
            self.noise_level = min(NOISE_MAX, self.noise_level + NOISE_KEY)
            self.sounds.play("key_collect", volume=0.7)
            return True
        return False

    # ----------------------------------------------------------
    def take_damage(self, sound_sys):
        if self.hurt_timer > 0 or not self.alive:
            return
        self.health -= 1
        self.hurt_timer = self.HURT_IFRAMES
        sound_sys.play("player_hurt", volume=0.8)
        if self.health <= 0:
            self.alive = False

    # ----------------------------------------------------------
    def toggle_flashlight(self):
        self.flashlight_on = not self.flashlight_on

    # ----------------------------------------------------------
    def draw(self, surface: pygame.Surface, camera_x: float, camera_y: float):
        sx = int(self.x - camera_x)
        sy = int(self.y - camera_y + self._bob)

        size = PLAYER_RADIUS * 2 + 8
        offset = size // 2

        # Blinking when hurt
        if self.hurt_timer > 0 and (self.hurt_timer // 5) % 2 == 0:
            spr = self._hurt_surf
        else:
            spr = self._sprite

        # Trail
        for t in self.trail:
            tx = int(t['x'] - camera_x)
            ty = int(t['y'] - camera_y)
            alpha = int(180 * (t['life'] / t['max_life']))
            tsurf = pygame.Surface((6, 6), pygame.SRCALPHA)
            tsurf.fill((80, 120, 200, alpha))
            surface.blit(tsurf, (tx - 3, ty - 3))

        # Player glow
        gsurf = pygame.Surface((60, 60), pygame.SRCALPHA)
        for gr in range(28, 0, -3):
            a = int(40 * (1 - gr / 28))
            pygame.draw.circle(gsurf, (100, 160, 255, a), (30, 30), gr)
        surface.blit(gsurf, (sx - 30, sy - 30))

        surface.blit(spr, (sx - offset, sy - offset))

    # ----------------------------------------------------------
    def draw_flashlight(self, surface: pygame.Surface, camera_x: float, camera_y: float):
        """
        Render the flashlight effect as a dark overlay with a cone.
        This is done AFTER the world is drawn, before the HUD.
        """
        if not self.flashlight_on and self.flashlight_bat < 5:
            # Very dark with a tiny glow
            dark = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            dark.fill((0, 0, 0, 230))
            surface.blit(dark, (0, 0))
            return

        sx = int(self.x - camera_x)
        sy = int(self.y - camera_y)

        w, h = surface.get_size()
        dark = pygame.Surface((w, h), pygame.SRCALPHA)
        dark.fill((0, 0, 10, 200))

        # Cone parameters
        bat_factor = self.flashlight_bat / FLASHLIGHT_MAX
        radius = int(self.flash_radius * (0.6 + 0.4 * bat_factor))
        half_angle = math.radians(55)

        # Build flashlight cone polygon
        n_pts = 24
        cone_pts = [(sx, sy)]
        for i in range(n_pts + 1):
            angle = self._facing - half_angle + (2 * half_angle * i / n_pts)
            px = sx + math.cos(angle) * radius
            py = sy + math.sin(angle) * radius
            cone_pts.append((px, py))

        # Cut the cone out of the dark overlay
        # Use a separate surface to define the transparent "hole"
        cone_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        cone_surf.fill((0, 0, 0, 0))
        if len(cone_pts) >= 3:
            pygame.draw.polygon(cone_surf, (255, 255, 255, 255), cone_pts)

        # Ambient glow around player (small circle)
        pygame.draw.circle(cone_surf, (255, 255, 255, 200), (sx, sy), 30)

        # Subtract cone from dark surface
        for y_px in range(0, h, 2):
            for x_px in range(0, w, 2):
                if cone_surf.get_at((x_px, y_px))[3] > 0:
                    dark.set_at((x_px, y_px), (0, 0, 0, 0))
                    if x_px + 1 < w:
                        dark.set_at((x_px+1, y_px), (0, 0, 0, 0))
                    if y_px + 1 < h:
                        dark.set_at((x_px, y_px+1), (0, 0, 0, 0))
                    if x_px + 1 < w and y_px + 1 < h:
                        dark.set_at((x_px+1, y_px+1), (0, 0, 0, 0))

        surface.blit(dark, (0, 0))

    def draw_flashlight_fast(self, surface: pygame.Surface, camera_x: float, camera_y: float):
        """
        Faster flashlight using pygame.gfxdraw + a single polygon mask.
        Replaces draw_flashlight for better performance.
        """
        sx = int(self.x - camera_x)
        sy = int(self.y - camera_y)
        w, h = surface.get_size()

        # Dark overlay
        dark = pygame.Surface((w, h), pygame.SRCALPHA)
        dark.fill((0, 0, 10, 210))

        bat_factor = max(0.1, self.flashlight_bat / FLASHLIGHT_MAX)
        radius = int(FLASHLIGHT_RADIUS * (0.5 + 0.5 * bat_factor))
        half_angle = math.radians(60)

        n_pts = 32
        cone = [(sx, sy)]
        for i in range(n_pts + 1):
            a = self._facing - half_angle + (2 * half_angle * i / n_pts)
            cone.append((sx + math.cos(a) * radius, sy + math.sin(a) * radius))

        # Punch hole in dark using destination-out blit
        hole = pygame.Surface((w, h), pygame.SRCALPHA)
        hole.fill((0, 0, 0, 0))
        # gradient-like circles inside cone  
        for step in range(radius, 0, -24):
            alpha = max(0, int(200 * (1 - step / radius)))
            pygame.draw.circle(hole, (0, 0, 0, alpha),
                               (sx, sy), step)
        # main cone cut
        pygame.draw.polygon(hole, (0, 0, 0, 180), cone)

        dark.blit(hole, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
        surface.blit(dark, (0, 0))
