# ============================================================
#  AI Sound Hunter – ui.py
#  HUD, menus, overlays, particles, fonts
# ============================================================

import pygame
import math
import random
from settings import *


# ---------------------------------------------------------------
# Font registry – load once, share everywhere
# ---------------------------------------------------------------
_FONTS: dict = {}

def get_font(size: int, bold: bool = False, name: str = "Segoe UI") -> pygame.font.Font:
    key = (name, size, bold)
    if key not in _FONTS:
        try:
            _FONTS[key] = pygame.font.SysFont(name, size, bold=bold)
        except Exception:
            _FONTS[key] = pygame.font.Font(None, size)
    return _FONTS[key]


# ---------------------------------------------------------------
# Utility draw helpers
# ---------------------------------------------------------------
def draw_text(surf: pygame.Surface, text: str, x: int, y: int,
              size: int = 24, colour=WHITE, bold: bool = False,
              centre: bool = False, shadow: bool = True):
    font = get_font(size, bold)
    if shadow:
        stxt = font.render(text, True, (0, 0, 0))
        r = stxt.get_rect()
        if centre:
            r.centerx = x
            r.top = y
        else:
            r.topleft = (x, y)
        surf.blit(stxt, (r.x + 2, r.y + 2))
    txt = font.render(text, True, colour)
    r2 = txt.get_rect()
    if centre:
        r2.centerx = x
        r2.top = y
    else:
        r2.topleft = (x, y)
    surf.blit(txt, r2)
    return r2


def draw_panel(surf: pygame.Surface, rect: pygame.Rect,
               bg=(10, 8, 20, 200), border=PURPLE, radius: int = 12):
    panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(panel, bg, (0, 0, rect.width, rect.height), border_radius=radius)
    surf.blit(panel, rect.topleft)
    pygame.draw.rect(surf, border, rect, 2, border_radius=radius)


# ---------------------------------------------------------------
# Button
# ---------------------------------------------------------------
class Button:
    def __init__(self, rect: pygame.Rect, text: str,
                 font_size: int = 26,
                 idle_col=(60, 20, 100),
                 hover_col=(120, 40, 200),
                 text_col=WHITE,
                 border_col=PURPLE,
                 icon: str = ""):
        self.rect      = rect
        self.text      = text
        self.font_size = font_size
        self.idle_col  = idle_col
        self.hover_col = hover_col
        self.text_col  = text_col
        self.border_col= border_col
        self.icon      = icon
        self._hovered  = False
        self._clicked  = False
        self._scale    = 1.0

    def update(self, events, mouse_pos):
        self._hovered = self.rect.collidepoint(mouse_pos)
        self._clicked = False
        for ev in events:
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if self._hovered:
                    self._clicked = True

    @property
    def clicked(self) -> bool:
        return self._clicked

    def draw(self, surf: pygame.Surface):
        colour = self.hover_col if self._hovered else self.idle_col
        scale  = 1.04 if self._hovered else 1.0
        rw = int(self.rect.width  * scale)
        rh = int(self.rect.height * scale)
        rx = self.rect.centerx - rw // 2
        ry = self.rect.centery - rh // 2

        # Shadow
        pygame.draw.rect(surf, (0, 0, 0, 120),
                         (rx+4, ry+4, rw, rh), border_radius=10)
        # Body
        btn = pygame.Surface((rw, rh), pygame.SRCALPHA)
        pygame.draw.rect(btn, (*colour, 230), (0, 0, rw, rh), border_radius=10)
        # Gradient sheen
        for i in range(rh // 2):
            a = int(60 * (1 - i / (rh / 2)))
            pygame.draw.rect(btn, (255, 255, 255, a),
                             (2, 2 + i, rw - 4, 1))
        surf.blit(btn, (rx, ry))
        pygame.draw.rect(surf, self.border_col, (rx, ry, rw, rh),
                         2, border_radius=10)

        # Text
        font = get_font(self.font_size, bold=True)
        label = (self.icon + " " + self.text).strip()
        txt = font.render(label, True, self.text_col)
        tr  = txt.get_rect(center=(rx + rw // 2, ry + rh // 2))
        surf.blit(txt, tr)


# ---------------------------------------------------------------
# HUD
# ---------------------------------------------------------------
class HUD:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.w, self.h = screen.get_size()
        self._heartbeat_anim = 0.0

    # ----------------------------------------------------------
    def draw(self, health: int, keys_collected: int, total_keys: int,
             noise: float, flashlight_bat: float, elapsed: float,
             difficulty: int, monster_state: str, debug: bool,
             svm_label: str = ""):
        self._heartbeat_anim = (self._heartbeat_anim + 0.05) % (2 * math.pi)
        self._draw_health(health)
        self._draw_keys(keys_collected, total_keys)
        self._draw_noise(noise)
        self._draw_flashlight(flashlight_bat)
        self._draw_timer(elapsed)
        self._draw_difficulty(difficulty)
        if debug:
            self._draw_debug_info(monster_state, svm_label)
        self._draw_interaction_hint()

    # ----------------------------------------------------------
    def _draw_health(self, health: int):
        draw_panel(self.screen, pygame.Rect(10, 10, 130, 44),
                   bg=(15, 5, 25, 210))
        draw_text(self.screen, "HEALTH", 16, 14, size=11,
                  colour=(180, 150, 220))
        for i in range(PLAYER_MAX_HEALTH):
            hx = 18 + i * 34
            hy = 26
            if i < health:
                # Beating heart
                pulse = 1.0 + 0.08 * math.sin(self._heartbeat_anim * 3 + i)
                r = int(11 * pulse)
                # Draw heart shape
                self._draw_heart(self.screen, hx, hy, r, (220, 30, 60))
            else:
                self._draw_heart(self.screen, hx, hy, 11, (50, 20, 35))

    def _draw_heart(self, surf, cx, cy, r, colour):
        # Simple heart using circles + polygon
        hr = max(3, r // 2)
        pygame.draw.circle(surf, colour, (cx - hr + 1, cy - hr + 4), hr)
        pygame.draw.circle(surf, colour, (cx + hr - 1, cy - hr + 4), hr)
        pts = [
            (cx - r + 2, cy - hr + 6),
            (cx,         cy + r),
            (cx + r - 2, cy - hr + 6),
        ]
        pygame.draw.polygon(surf, colour, pts)

    # ----------------------------------------------------------
    def _draw_keys(self, collected: int, total: int):
        draw_panel(self.screen, pygame.Rect(150, 10, 130, 44),
                   bg=(15, 5, 25, 210))
        draw_text(self.screen, "KEYS", 158, 14, size=11,
                  colour=(180, 150, 220))
        for i in range(total):
            kx = 163 + i * 36
            ky = 30
            col = KEY_COLOUR if i < collected else (50, 40, 20)
            # Key icon
            pygame.draw.circle(self.screen, col, (kx, ky), 7)
            pygame.draw.rect(self.screen, col, (kx + 2, ky - 2, 12, 4))
            pygame.draw.rect(self.screen, col, (kx + 8, ky,  3,  5))

    # ----------------------------------------------------------
    def _draw_noise(self, noise: float):
        draw_panel(self.screen, pygame.Rect(10, 62, 270, 38),
                   bg=(15, 5, 25, 210))
        draw_text(self.screen, "NOISE", 16, 66, size=11,
                  colour=(180, 150, 220))
        bar_x, bar_y = 60, 71
        bar_w, bar_h = 208, 20
        # Background
        pygame.draw.rect(self.screen, (30, 15, 50),
                         (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        # Fill
        ratio  = noise / NOISE_MAX
        fill_w = int(bar_w * ratio)
        if ratio < 0.4:
            col = NOISE_LOW
        elif ratio < 0.75:
            col = NOISE_MED
        else:
            col = NOISE_HIGH
        if fill_w > 0:
            pygame.draw.rect(self.screen, col,
                             (bar_x, bar_y, fill_w, bar_h), border_radius=4)
        # Flicker at high noise
        if ratio > 0.8:
            flick = pygame.Surface((fill_w, bar_h), pygame.SRCALPHA)
            a = int(80 * math.sin(pygame.time.get_ticks() * 0.01))
            flick.fill((255, 255, 255, max(0, a)))
            self.screen.blit(flick, (bar_x, bar_y))
        pygame.draw.rect(self.screen, PURPLE,
                         (bar_x, bar_y, bar_w, bar_h), 1, border_radius=4)
        pct = int(ratio * 100)
        draw_text(self.screen, f"{pct}%", bar_x + bar_w + 4, bar_y + 2,
                  size=13, colour=col)

    # ----------------------------------------------------------
    def _draw_flashlight(self, bat: float):
        draw_panel(self.screen, pygame.Rect(10, 108, 270, 38),
                   bg=(15, 5, 25, 210))
        draw_text(self.screen, "LIGHT", 16, 112, size=11,
                  colour=(180, 150, 220))
        bar_x, bar_y = 60, 117
        bar_w, bar_h = 208, 20
        pygame.draw.rect(self.screen, (30, 15, 50),
                         (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        ratio  = bat / FLASHLIGHT_MAX
        fill_w = int(bar_w * ratio)
        col = (255, 255, 100) if ratio > 0.3 else (200, 100, 0)
        if fill_w > 0:
            pygame.draw.rect(self.screen, col,
                             (bar_x, bar_y, fill_w, bar_h), border_radius=4)
        pygame.draw.rect(self.screen, PURPLE,
                         (bar_x, bar_y, bar_w, bar_h), 1, border_radius=4)
        pct = int(ratio * 100)
        draw_text(self.screen, f"{pct}%", bar_x + bar_w + 4, bar_y + 2,
                  size=13, colour=col)

    # ----------------------------------------------------------
    def _draw_timer(self, elapsed: float):
        draw_panel(self.screen, pygame.Rect(self.w - 150, 10, 140, 44),
                   bg=(15, 5, 25, 210))
        draw_text(self.screen, "TIME", self.w - 144, 14, size=11,
                  colour=(180, 150, 220))
        m = int(elapsed) // 60
        s = int(elapsed) % 60
        timer_str = f"{m:02d}:{s:02d}"
        draw_text(self.screen, timer_str, self.w - 144, 26,
                  size=20, colour=(220, 210, 255), bold=True)

    # ----------------------------------------------------------
    def _draw_difficulty(self, level: int):
        labels = ["Easy", "Normal", "Hard", "Expert"]
        cols   = [GREEN, YELLOW, ORANGE, BRIGHT_RED]
        lbl = labels[min(level, 3)]
        col = cols[min(level, 3)]
        draw_text(self.screen, f"Lvl {lbl}", self.w - 148, 60,
                  size=13, colour=col)

    # ----------------------------------------------------------
    def _draw_debug_info(self, monster_state: str, svm_label: str):
        panel = pygame.Rect(self.w // 2 - 140, 10, 280, 50)
        draw_panel(self.screen, panel, bg=(5, 2, 15, 210))
        draw_text(self.screen, "[DEBUG F1]", panel.x + 6, panel.y + 4,
                  size=11, colour=(100, 255, 200))
        draw_text(self.screen, f"Monster: {monster_state}",
                  panel.x + 6, panel.y + 18, size=14, colour=BRIGHT_RED)
        if svm_label:
            draw_text(self.screen, f"SVM: {svm_label}",
                      panel.x + 160, panel.y + 18, size=14,
                      colour=(0, 200, 255))

    # ----------------------------------------------------------
    def _draw_interaction_hint(self):
        draw_text(self.screen, "[E] Open Door  [F] Flashlight  [Shift] Run",
                  self.w // 2, self.h - 26, size=13,
                  colour=(120, 100, 160), centre=True, shadow=False)


# ---------------------------------------------------------------
# Background Particles (menu / screen atmosphere)
# ---------------------------------------------------------------
class AtmosphereParticles:
    def __init__(self, count: int = 80):
        self.particles = []
        for _ in range(count):
            self._spawn()

    def _spawn(self, x=None):
        self.particles.append({
            'x':     random.uniform(0, SCREEN_WIDTH),
            'y':     random.uniform(0, SCREEN_HEIGHT),
            'vx':    random.uniform(-0.3, 0.3),
            'vy':    random.uniform(-0.6, -0.1),
            'r':     random.uniform(1, 3),
            'a':     random.randint(20, 80),
            'col':   random.choice([(80,0,120),(120,0,80),(50,20,150),(100,0,60)]),
        })

    def update(self):
        for p in self.particles:
            p['x'] += p['vx']
            p['y'] += p['vy']
            if p['y'] < -10:
                p['y'] = SCREEN_HEIGHT + 10
                p['x'] = random.uniform(0, SCREEN_WIDTH)

    def draw(self, surf: pygame.Surface):
        for p in self.particles:
            ps = pygame.Surface((int(p['r']*2+1), int(p['r']*2+1)), pygame.SRCALPHA)
            pygame.draw.circle(ps, (*p['col'], p['a']),
                               (int(p['r']), int(p['r'])), int(p['r']))
            surf.blit(ps, (int(p['x'] - p['r']), int(p['y'] - p['r'])))


# ---------------------------------------------------------------
# Start Menu
# ---------------------------------------------------------------
class StartMenu:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.w, self.h = screen.get_size()
        self.particles = AtmosphereParticles(100)

        cx = self.w // 2
        self.btn_play = Button(
            pygame.Rect(cx - 110, self.h // 2 - 10, 220, 52),
            "PLAY GAME", font_size=28, icon="▶",
            idle_col=(80, 0, 160), hover_col=(130, 0, 220))
        self.btn_instructions = Button(
            pygame.Rect(cx - 110, self.h // 2 + 60, 220, 46),
            "HOW TO PLAY", font_size=22, icon="?",
            idle_col=(50, 0, 100), hover_col=(90, 0, 160))
        self.btn_scores = Button(
            pygame.Rect(cx - 110, self.h // 2 + 116, 220, 46),
            "HIGH SCORES", font_size=22, icon="★",
            idle_col=(50, 0, 100), hover_col=(90, 0, 160))
        self.btn_quit = Button(
            pygame.Rect(cx - 110, self.h // 2 + 172, 220, 46),
            "QUIT", font_size=22, icon="✕",
            idle_col=(80, 0, 20), hover_col=(160, 0, 40))

        self._title_anim = 0.0
        self._scanline_offset = 0

    def update(self, events, mouse_pos):
        self.particles.update()
        self._title_anim += 0.03
        self._scanline_offset = (self._scanline_offset + 1) % 4
        for btn in (self.btn_play, self.btn_instructions,
                    self.btn_scores, self.btn_quit):
            btn.update(events, mouse_pos)

    def draw(self):
        # Gradient background
        bg = pygame.Surface((self.w, self.h))
        for y in range(self.h):
            t = y / self.h
            r = int(5  + t * 15)
            g = int(0  + t * 5)
            b = int(20 + t * 30)
            pygame.draw.line(bg, (r, g, b), (0, y), (self.w, y))
        self.screen.blit(bg, (0, 0))

        self.particles.draw(self.screen)

        # Scanlines
        for y in range(self._scanline_offset, self.h, 4):
            pygame.draw.line(self.screen, (0, 0, 0), (0, y), (self.w, y))

        # Title glow
        pulse = 0.5 + 0.5 * math.sin(self._title_anim)
        for r in range(80, 0, -10):
            a = int(30 * pulse * (1 - r/80))
            gs = pygame.Surface((r*4, r*2), pygame.SRCALPHA)
            pygame.draw.ellipse(gs, (120, 0, 200, a), (0, 0, r*4, r*2))
            self.screen.blit(gs, (self.w//2 - r*2, self.h//4 - r))

        # Title text (layered for glow effect)
        for offset, col in [(3,(60,0,100)), (2,(100,0,160)), (0,(230,200,255))]:
            draw_text(self.screen, "AI SOUND HUNTER",
                      self.w // 2, self.h // 4 - 40 - offset,
                      size=64, colour=col, bold=True, centre=True, shadow=False)

        draw_text(self.screen, "HORROR ESCAPE",
                  self.w // 2, self.h // 4 + 28,
                  size=22, colour=(180, 120, 255), centre=True)

        # Subtitle flicker
        if int(self._title_anim * 10) % 3 != 0:
            draw_text(self.screen,
                      "Escape the research facility... if you can stay silent",
                      self.w // 2, self.h // 4 + 58,
                      size=14, colour=(120, 90, 160), centre=True, shadow=False)

        for btn in (self.btn_play, self.btn_instructions,
                    self.btn_scores, self.btn_quit):
            btn.draw(self.screen)

        # Footer
        draw_text(self.screen, "AI Subject Project  |  F1: Debug  |  F2: Path",
                  self.w // 2, self.h - 20, size=12,
                  colour=(60, 50, 100), centre=True, shadow=False)

    @property
    def play_clicked(self):
        return self.btn_play.clicked

    @property
    def instructions_clicked(self):
        return self.btn_instructions.clicked

    @property
    def scores_clicked(self):
        return self.btn_scores.clicked

    @property
    def quit_clicked(self):
        return self.btn_quit.clicked


# ---------------------------------------------------------------
# Instructions Screen
# ---------------------------------------------------------------
class InstructionsScreen:
    LINES = [
        ("CONTROLS", (200, 160, 255), 22, True),
        ("WASD / Arrow Keys  →  Move", (200, 200, 255), 17, False),
        ("Shift  →  Run (loud!)", (200, 200, 255), 17, False),
        ("E  →  Interact / Open Door", (200, 200, 255), 17, False),
        ("F  →  Toggle Flashlight", (200, 200, 255), 17, False),
        ("F1  →  Debug Mode  |  ESC  →  Menu", (150, 130, 200), 14, False),
        ("", None, 12, False),
        ("OBJECTIVE", (255, 200, 100), 22, True),
        ("Collect all 3 KEYS, then reach the EXIT.", (220,200,255), 17, False),
        ("The monster hunts by SOUND — stay quiet!", (220,200,255), 17, False),
        ("Walking is quiet. Running is very loud.", (220,200,255), 17, False),
        ("Opening doors creates noise events.", (220,200,255), 17, False),
        ("", None, 12, False),
        ("MONSTER AI", (255, 120, 120), 22, True),
        ("IDLE / PATROL → INVESTIGATE → SEARCH → CHASE", (255,180,180), 16, False),
        ("Uses A* pathfinding — it CANNOT be lost in walls!", (255,180,180), 16, False),
        ("Difficulty increases every 10 minutes.", (200,150,150), 14, False),
    ]

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.w, self.h = screen.get_size()
        cx = self.w // 2
        self.btn_back = Button(
            pygame.Rect(cx - 80, self.h - 70, 160, 44),
            "BACK", font_size=22, icon="←",
            idle_col=(50, 0, 100), hover_col=(90, 0, 160))

    def update(self, events, mouse_pos):
        self.btn_back.update(events, mouse_pos)

    def draw(self):
        self.screen.fill(DARK_BLUE)
        draw_text(self.screen, "HOW TO PLAY",
                  self.w // 2, 20, size=36, colour=PURPLE,
                  bold=True, centre=True)
        y = 70
        for text, col, size, bold in self.LINES:
            if text == "":
                y += size
                continue
            draw_text(self.screen, text, self.w // 2, y,
                      size=size, colour=col, bold=bold, centre=True)
            y += size + 6
        self.btn_back.draw(self.screen)

    @property
    def back_clicked(self):
        return self.btn_back.clicked


# ---------------------------------------------------------------
# High Score Screen
# ---------------------------------------------------------------
class HighScoreScreen:
    def __init__(self, screen: pygame.Surface, scores: list):
        self.screen = screen
        self.w, self.h = screen.get_size()
        self.scores = scores
        cx = self.w // 2
        self.btn_back = Button(
            pygame.Rect(cx - 80, self.h - 70, 160, 44),
            "BACK", font_size=22, icon="←",
            idle_col=(50, 0, 100), hover_col=(90, 0, 160))

    def update(self, events, mouse_pos):
        self.btn_back.update(events, mouse_pos)

    def draw(self):
        self.screen.fill(DARK_BLUE)
        draw_text(self.screen, "HIGH SCORES",
                  self.w // 2, 20, size=36, colour=KEY_COLOUR,
                  bold=True, centre=True)

        headers = ["#", "Name", "Score", "Time", "Keys", "Won"]
        col_x   = [100, 200, 400, 560, 700, 800]
        y = 80
        for i, hdr in enumerate(headers):
            draw_text(self.screen, hdr, col_x[i], y, size=16,
                      colour=PURPLE, bold=True)
        pygame.draw.line(self.screen, PURPLE,
                         (80, y + 24), (self.w - 80, y + 24), 1)
        y += 30

        if not self.scores:
            draw_text(self.screen, "No scores yet. Play to get on the board!",
                      self.w // 2, y + 40, size=18,
                      colour=(150, 120, 200), centre=True)
        else:
            for rank, entry in enumerate(self.scores[:8]):
                row_col = (220, 200, 255) if rank == 0 else (180, 160, 220)
                if rank == 0:
                    row_col = KEY_COLOUR
                vals = [
                    str(rank + 1),
                    entry.get("name", "Player"),
                    str(entry.get("score", 0)),
                    f"{entry.get('time', 0):.0f}s",
                    str(entry.get("keys", 0)),
                    "WIN" if entry.get("won") else "LOSS",
                ]
                won_col = GREEN if entry.get("won") else BRIGHT_RED
                for i, val in enumerate(vals):
                    col = won_col if i == 5 else row_col
                    draw_text(self.screen, val, col_x[i], y, size=15, colour=col)
                y += 28

        self.btn_back.draw(self.screen)

    @property
    def back_clicked(self):
        return self.btn_back.clicked


# ---------------------------------------------------------------
# Pause Menu
# ---------------------------------------------------------------
class PauseMenu:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.w, self.h = screen.get_size()
        cx = self.w // 2
        self.btn_resume = Button(
            pygame.Rect(cx - 110, self.h // 2 - 40, 220, 48),
            "RESUME", font_size=26, icon="▶",
            idle_col=(60, 0, 120), hover_col=(100, 0, 200))
        self.btn_menu = Button(
            pygame.Rect(cx - 110, self.h // 2 + 20, 220, 48),
            "MAIN MENU", font_size=24, icon="⌂",
            idle_col=(60, 0, 40), hover_col=(120, 0, 80))

    def update(self, events, mouse_pos):
        for btn in (self.btn_resume, self.btn_menu):
            btn.update(events, mouse_pos)

    def draw(self):
        overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))
        draw_text(self.screen, "PAUSED",
                  self.w // 2, self.h // 2 - 110,
                  size=52, colour=PURPLE, bold=True, centre=True)
        for btn in (self.btn_resume, self.btn_menu):
            btn.draw(self.screen)

    @property
    def resume_clicked(self):
        return self.btn_resume.clicked

    @property
    def menu_clicked(self):
        return self.btn_menu.clicked


# ---------------------------------------------------------------
# Game Over Screen
# ---------------------------------------------------------------
class GameOverScreen:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.w, self.h = screen.get_size()
        cx = self.w // 2
        self.btn_restart = Button(
            pygame.Rect(cx - 120, self.h // 2 + 80, 240, 50),
            "TRY AGAIN", font_size=26, icon="↺",
            idle_col=(80, 0, 0), hover_col=(160, 0, 0))
        self.btn_menu = Button(
            pygame.Rect(cx - 120, self.h // 2 + 142, 240, 46),
            "MAIN MENU", font_size=22, icon="⌂",
            idle_col=(50, 0, 100), hover_col=(90, 0, 160))
        self._anim = 0.0

    def update(self, events, mouse_pos):
        self._anim += 0.04
        for btn in (self.btn_restart, self.btn_menu):
            btn.update(events, mouse_pos)

    def draw(self, stats):
        overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        self.screen.blit(overlay, (0, 0))

        pulse = 0.5 + 0.5 * math.sin(self._anim)
        r_col = tuple(int(c * (0.6 + 0.4 * pulse)) for c in (200, 20, 20))
        draw_text(self.screen, "YOU WERE CAUGHT",
                  self.w // 2, self.h // 2 - 140,
                  size=56, colour=r_col, bold=True, centre=True)

        panel = pygame.Rect(self.w // 2 - 200, self.h // 2 - 80, 400, 150)
        draw_panel(self.screen, panel, bg=(20, 5, 30, 220))

        lines = [
            (f"Survived:  {stats.format_time()}", (200, 200, 255)),
            (f"Keys Found:  {stats.keys_collected} / {stats.total_keys}", KEY_COLOUR),
            (f"Score:  {stats.score:,}", (220, 200, 255)),
        ]
        for i, (txt, col) in enumerate(lines):
            draw_text(self.screen, txt, self.w // 2, panel.y + 18 + i * 38,
                      size=20, colour=col, centre=True)

        for btn in (self.btn_restart, self.btn_menu):
            btn.draw(self.screen)

    @property
    def restart_clicked(self):
        return self.btn_restart.clicked

    @property
    def menu_clicked(self):
        return self.btn_menu.clicked


# ---------------------------------------------------------------
# Victory Screen
# ---------------------------------------------------------------
class VictoryScreen:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.w, self.h = screen.get_size()
        cx = self.w // 2
        self.btn_restart = Button(
            pygame.Rect(cx - 120, self.h // 2 + 110, 240, 50),
            "PLAY AGAIN", font_size=26, icon="↺",
            idle_col=(0, 80, 40), hover_col=(0, 150, 80))
        self.btn_menu = Button(
            pygame.Rect(cx - 120, self.h // 2 + 172, 240, 46),
            "MAIN MENU", font_size=22, icon="⌂",
            idle_col=(50, 0, 100), hover_col=(90, 0, 160))
        self._anim = 0.0
        self._particles = []
        for _ in range(60):
            self._particles.append({
                'x': random.uniform(0, self.w),
                'y': random.uniform(self.h, self.h + 100),
                'vx': random.uniform(-1, 1),
                'vy': random.uniform(-4, -1),
                'col': random.choice([(0,220,120),(255,200,0),(100,200,255),(200,0,255)]),
                'r':  random.uniform(2, 6),
            })

    def update(self, events, mouse_pos):
        self._anim += 0.04
        for btn in (self.btn_restart, self.btn_menu):
            btn.update(events, mouse_pos)
        for p in self._particles:
            p['x'] += p['vx']
            p['y'] += p['vy']
            if p['y'] < -20:
                p['y'] = self.h + 10
                p['x'] = random.uniform(0, self.w)

    def draw(self, stats):
        overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        self.screen.blit(overlay, (0, 0))

        # Confetti
        for p in self._particles:
            ps = pygame.Surface((int(p['r']*2), int(p['r']*2)), pygame.SRCALPHA)
            pygame.draw.circle(ps, (*p['col'], 200),
                               (int(p['r']), int(p['r'])), int(p['r']))
            self.screen.blit(ps, (int(p['x'] - p['r']), int(p['y'] - p['r'])))

        pulse = 0.5 + 0.5 * math.sin(self._anim)
        g_col = tuple(int(c * (0.7 + 0.3 * pulse)) for c in (0, 220, 100))
        draw_text(self.screen, "YOU ESCAPED!",
                  self.w // 2, self.h // 2 - 150,
                  size=60, colour=g_col, bold=True, centre=True)
        draw_text(self.screen, "The facility is behind you.",
                  self.w // 2, self.h // 2 - 90,
                  size=20, colour=(180, 255, 200), centre=True)

        panel = pygame.Rect(self.w // 2 - 220, self.h // 2 - 60, 440, 158)
        draw_panel(self.screen, panel, bg=(5, 30, 20, 220), border=EXIT_COLOUR)

        stats.compute_score()
        lines = [
            (f"Survived:  {stats.format_time()}", (200, 255, 220)),
            (f"Keys Found:  {stats.keys_collected} / {stats.total_keys}", KEY_COLOUR),
            (f"Health Remaining:  {max(0, PLAYER_MAX_HEALTH-stats.health_lost)} ❤", BRIGHT_RED),
            (f"Final Score:  {stats.score:,}", (255, 220, 100)),
        ]
        for i, (txt, col) in enumerate(lines):
            draw_text(self.screen, txt, self.w // 2, panel.y + 12 + i * 34,
                      size=19, colour=col, centre=True)

        for btn in (self.btn_restart, self.btn_menu):
            btn.draw(self.screen)

    @property
    def restart_clicked(self):
        return self.btn_restart.clicked

    @property
    def menu_clicked(self):
        return self.btn_menu.clicked
