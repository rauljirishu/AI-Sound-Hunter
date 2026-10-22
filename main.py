# ============================================================
#  AI Sound Hunter – main.py
#  Entry point: game loop, state management, camera
# ============================================================

import pygame
import sys
import math
import random
import os

# ── Project imports ──────────────────────────────────────────
import settings as cfg
from settings import *
from level       import Level, PLAYER_SPAWN, MONSTER_PATROL
from player      import Player
from monster     import Monster
from sound_system import NoisePropagation, SoundManager, SVMAudioClassifier
from game_stats  import GameStats
from ui          import (HUD, StartMenu, InstructionsScreen, HighScoreScreen,
                         PauseMenu, GameOverScreen, VictoryScreen)


# ---------------------------------------------------------------
# Game states
# ---------------------------------------------------------------
ST_MENU         = "menu"
ST_INSTRUCTIONS = "instructions"
ST_SCORES       = "scores"
ST_PLAYING      = "playing"
ST_PAUSED       = "paused"
ST_GAME_OVER    = "game_over"
ST_VICTORY      = "victory"


# ---------------------------------------------------------------
# Fog-of-War / Lighting surface builder
# ---------------------------------------------------------------
def make_darkness(w: int, h: int, alpha: int = 200) -> pygame.Surface:
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    s.fill((0, 0, 10, alpha))
    return s


# ---------------------------------------------------------------
# Main Game class
# ---------------------------------------------------------------
class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.screen = pygame.display.set_mode(
            (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.DOUBLEBUF)
        self.clock  = pygame.time.Clock()

        # Ensure asset dirs exist
        for d in (ASSETS_DIR, IMAGES_DIR, SOUNDS_DIR, MODELS_DIR, DATA_DIR):
            os.makedirs(d, exist_ok=True)

        # Core systems
        self.sound_mgr  = SoundManager()
        self.svm        = SVMAudioClassifier()
        self.stats      = GameStats()

        # UI screens (created once, reused)
        self.start_menu   = StartMenu(self.screen)
        self.instr_screen = InstructionsScreen(self.screen)
        self.score_screen = None   # refreshed each time
        self.pause_menu   = PauseMenu(self.screen)
        self.gameover_scr = GameOverScreen(self.screen)
        self.victory_scr  = VictoryScreen(self.screen)

        # Game objects (created on play)
        self.level   = None
        self.player  = None
        self.monster = None
        self.noise   = None
        self.hud     = HUD(self.screen)

        # State
        self.state       = ST_MENU
        self.debug_mode  = DEBUG_MODE
        self.show_path   = SHOW_PATH
        self.camera_x    = 0.0
        self.camera_y    = 0.0

        # Difficulty ramp
        self._frames     = 0
        self._difficulty = 0

        # SVM prediction cache
        self._svm_label  = ""
        self._svm_timer  = 0

        # Train SVM in background (non-blocking: just trains once at start)
        if not self.svm.trained and self.svm.available:
            print("[SVM] Training classifier (first run)…")
            self.svm.train(n_samples=1500)

        # Ambient atmosphere particles for menu
        self.sound_mgr.play_music("ambient_horror.ogg", volume=0.3)

    # ----------------------------------------------------------
    def _new_game(self):
        """Create fresh game objects and start a new session."""
        self.level   = Level(self.screen)
        self.player  = Player(PLAYER_SPAWN[0], PLAYER_SPAWN[1],
                              self.level, self.sound_mgr)
        self.monster = Monster(MONSTER_PATROL, self.level, self._difficulty)
        self.noise   = NoisePropagation()
        self.stats.reset()
        self.stats.total_keys = len(self.level.key_positions)
        self.stats.start()
        self._frames     = 0
        self._difficulty = 0
        self._svm_label  = ""

        # Camera
        self.camera_x = self.player.x - SCREEN_WIDTH  // 2
        self.camera_y = self.player.y - SCREEN_HEIGHT // 2

    # ----------------------------------------------------------
    def _update_camera(self):
        """Smooth camera following the player."""
        target_x = self.player.x - SCREEN_WIDTH  // 2
        target_y = self.player.y - SCREEN_HEIGHT // 2

        # Clamp to map bounds
        max_cx = self.level.cols * TILE_SIZE - SCREEN_WIDTH
        max_cy = self.level.rows * TILE_SIZE - SCREEN_HEIGHT
        target_x = max(0, min(target_x, max_cx))
        target_y = max(0, min(target_y, max_cy))

        # Lerp
        self.camera_x += (target_x - self.camera_x) * 0.12
        self.camera_y += (target_y - self.camera_y) * 0.12

    # ----------------------------------------------------------
    def _handle_events(self) -> list:
        events = pygame.event.get()
        for ev in events:
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_F1:
                    self.debug_mode = not self.debug_mode
                if ev.key == pygame.K_F2:
                    self.show_path = not self.show_path
                if ev.key == pygame.K_ESCAPE:
                    if self.state == ST_PLAYING:
                        self.state = ST_PAUSED
                    elif self.state == ST_PAUSED:
                        self.state = ST_PLAYING
        return events

    # ----------------------------------------------------------
    def _update_gameplay(self, events, keys):
        if not self.player.alive:
            self.stats.game_over = True
            self.stats.stop()
            self.stats.compute_score()
            self.stats.save_score()
            self.gameover_scr = GameOverScreen(self.screen)
            self.state = ST_GAME_OVER
            self.sound_mgr.play("game_over", volume=0.8)
            return

        self._frames += 1

        # Difficulty ramp
        for i, threshold in enumerate(DIFFICULTY_INTERVALS):
            if self._frames >= threshold and self._difficulty < i + 1:
                self._difficulty = i + 1
                self.monster.update_difficulty(self._difficulty)

        # Player input
        self.player.handle_input(keys)

        # Interact (E key)
        for ev in events:
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_e:
                    self.player.interact(self.noise)
                if ev.key == pygame.K_f:
                    self.player.toggle_flashlight()

        # Player update
        self.player.update(self.noise, dt=1.0)

        # Auto-collect keys
        if self.player.auto_collect_key(self.noise):
            self.stats.keys_collected += 1

        # Check exit
        if self.level.check_exit(self.player.x, self.player.y):
            self.stats.game_won = True
            self.stats.stop()
            self.stats.compute_score()
            self.stats.save_score()
            self.victory_scr = VictoryScreen(self.screen)
            self.state = ST_VICTORY
            self.sound_mgr.play("victory", volume=0.8)
            return

        # Noise system update
        self.noise.update()

        # SVM classification (every 20 frames)
        self._svm_timer += 1
        if self._svm_timer >= 20:
            self._svm_timer = 0
            _, best_ev = self.noise.perceived_at(
                self.monster.x, self.monster.y, self.level.grid)
            if best_ev:
                self._svm_label = self.svm.predict(
                    best_ev.intensity, best_ev.source,
                    self.player.noise_level, best_ev.age)
            else:
                self._svm_label = "silence"

        # Monster update
        attacked = self.monster.update(
            self.player.x, self.player.y, self.noise)

        if attacked:
            self.player.take_damage(self.sound_mgr)
            self.sound_mgr.play("monster_roar", volume=0.9)

        # Level update
        self.level.update(dt=1.0)

        # Camera
        self._update_camera()

        # Stats
        self.stats.update(self.player.noise_level,
                          self.level.keys_collected,
                          self.player.health,
                          self._difficulty)

    # ----------------------------------------------------------
    def _draw_gameplay(self):
        # World
        self.level.draw(self.camera_x, self.camera_y)

        # Player
        self.player.draw(self.screen, self.camera_x, self.camera_y)

        # Monster
        self.monster.draw(self.screen, self.camera_x, self.camera_y,
                          debug=self.debug_mode)

        # Flashlight overlay
        self.player.draw_flashlight_fast(self.screen,
                                         self.camera_x, self.camera_y)

        # HUD
        self.hud.draw(
            health         = self.player.health,
            keys_collected = self.level.keys_collected,
            total_keys     = len(self.level.key_positions),
            noise          = self.player.noise_level,
            flashlight_bat = self.player.flashlight_bat,
            elapsed        = self.stats.elapsed,
            difficulty     = self._difficulty,
            monster_state  = self.monster.state,
            debug          = self.debug_mode,
            svm_label      = self._svm_label,
        )

        # Minimap
        mm_rect = pygame.Rect(SCREEN_WIDTH - 170, 60, 160, 110)
        self.level.draw_minimap(self.screen, mm_rect,
                                (self.player.x, self.player.y),
                                (self.monster.x, self.monster.y),
                                self.camera_x, self.camera_y)

        # Debug overlay texts
        if self.debug_mode:
            from ui import draw_text
            draw_text(self.screen,
                      f"Pos: ({int(self.player.x)}, {int(self.player.y)})",
                      4, SCREEN_HEIGHT - 60, size=12, colour=(0,255,200))
            draw_text(self.screen,
                      f"Noise: {self.player.noise_level:.1f}",
                      4, SCREEN_HEIGHT - 46, size=12, colour=(0,255,200))
            draw_text(self.screen,
                      f"Monster: ({int(self.monster.x)},{int(self.monster.y)}) State:{self.monster.state}",
                      4, SCREEN_HEIGHT - 32, size=12, colour=(255,100,100))
            draw_text(self.screen,
                      f"FPS: {int(self.clock.get_fps())}  Diff: {self._difficulty}",
                      4, SCREEN_HEIGHT - 18, size=12, colour=(200,200,100))

    # ----------------------------------------------------------
    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            events   = self._handle_events()
            keys     = pygame.key.get_pressed()
            mouse    = pygame.mouse.get_pos()

            # ── STATE MACHINE ────────────────────────────────
            if self.state == ST_MENU:
                self.start_menu.update(events, mouse)
                self.start_menu.draw()
                if self.start_menu.play_clicked:
                    self._new_game()
                    self.state = ST_PLAYING
                elif self.start_menu.instructions_clicked:
                    self.state = ST_INSTRUCTIONS
                elif self.start_menu.scores_clicked:
                    self.score_screen = HighScoreScreen(
                        self.screen, self.stats.high_scores)
                    self.state = ST_SCORES
                elif self.start_menu.quit_clicked:
                    pygame.quit()
                    sys.exit()

            elif self.state == ST_INSTRUCTIONS:
                self.screen.fill(DARK_BLUE)
                self.instr_screen.update(events, mouse)
                self.instr_screen.draw()
                if self.instr_screen.back_clicked:
                    self.state = ST_MENU

            elif self.state == ST_SCORES:
                self.screen.fill(DARK_BLUE)
                self.score_screen.update(events, mouse)
                self.score_screen.draw()
                if self.score_screen.back_clicked:
                    self.state = ST_MENU

            elif self.state == ST_PLAYING:
                self._update_gameplay(events, keys)
                self.screen.fill(DARK_BLUE)
                if self.level:
                    self._draw_gameplay()

            elif self.state == ST_PAUSED:
                # Re-draw game underneath
                self.screen.fill(DARK_BLUE)
                if self.level:
                    self._draw_gameplay()
                self.pause_menu.update(events, mouse)
                self.pause_menu.draw()
                if self.pause_menu.resume_clicked:
                    self.state = ST_PLAYING
                elif self.pause_menu.menu_clicked:
                    self.stats.stop()
                    self.state = ST_MENU

            elif self.state == ST_GAME_OVER:
                self.screen.fill(DARK_BLUE)
                if self.level:
                    self._draw_gameplay()
                self.gameover_scr.update(events, mouse)
                self.gameover_scr.draw(self.stats)
                if self.gameover_scr.restart_clicked:
                    self._new_game()
                    self.state = ST_PLAYING
                elif self.gameover_scr.menu_clicked:
                    self.state = ST_MENU

            elif self.state == ST_VICTORY:
                self.screen.fill(DARK_BLUE)
                if self.level:
                    self._draw_gameplay()
                self.victory_scr.update(events, mouse)
                self.victory_scr.draw(self.stats)
                if self.victory_scr.restart_clicked:
                    self._new_game()
                    self.state = ST_PLAYING
                elif self.victory_scr.menu_clicked:
                    self.state = ST_MENU

            pygame.display.flip()


# ---------------------------------------------------------------
if __name__ == "__main__":
    Game().run()
