# ============================================================
#  AI Sound Hunter – game_stats.py
#  Score tracking, high score persistence, session stats
# ============================================================

import json
import os
import time
from settings import *


class GameStats:
    """
    Tracks current session statistics and manages persistent
    high-score storage in data/highscores.json.
    """

    def __init__(self):
        self.reset()
        os.makedirs(DATA_DIR, exist_ok=True)
        self.high_scores: list = self._load_scores()

    # ----------------------------------------------------------
    def reset(self):
        self.start_time     = time.time()
        self.elapsed        = 0.0        # seconds survived
        self.keys_collected = 0
        self.total_keys     = 3
        self.health_lost    = 0
        self.difficulty_lvl = 0
        self.score          = 0
        self.game_won       = False
        self.game_over      = False
        self.noise_events   = 0
        self.max_noise_seen = 0.0
        self._running       = False

    # ----------------------------------------------------------
    def start(self):
        self.start_time = time.time()
        self._running   = True

    def stop(self):
        self._running = False

    def update(self, noise_level: float, keys_collected: int,
               health: int, difficulty: int):
        if self._running:
            self.elapsed = time.time() - self.start_time
        self.keys_collected = keys_collected
        self.health_lost    = PLAYER_MAX_HEALTH - health
        self.difficulty_lvl = difficulty
        if noise_level > self.max_noise_seen:
            self.max_noise_seen = noise_level

    # ----------------------------------------------------------
    def compute_score(self) -> int:
        score = 0
        score += self.keys_collected * SCORE_KEY_COLLECT
        if self.game_won:
            score += SCORE_EXIT
            remaining = max(0, 300 - self.elapsed)
            score += int(remaining * SCORE_TIME_BONUS)
            hp_left = max(0, PLAYER_MAX_HEALTH - self.health_lost)
            score += hp_left * SCORE_HEALTH_BONUS
        # Difficulty bonus
        score = int(score * (1 + self.difficulty_lvl * 0.2))
        self.score = score
        return score

    # ----------------------------------------------------------
    def _load_scores(self) -> list:
        if not os.path.exists(SCORES_FILE):
            return []
        try:
            with open(SCORES_FILE, "r") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data[:10]
        except Exception:
            pass
        return []

    def save_score(self, player_name: str = "Player"):
        self.compute_score()
        entry = {
            "name":    player_name,
            "score":   self.score,
            "time":    round(self.elapsed, 1),
            "keys":    self.keys_collected,
            "won":     self.game_won,
            "difficulty": self.difficulty_lvl,
        }
        self.high_scores.append(entry)
        self.high_scores.sort(key=lambda x: x["score"], reverse=True)
        self.high_scores = self.high_scores[:10]
        try:
            with open(SCORES_FILE, "w") as f:
                json.dump(self.high_scores, f, indent=2)
        except Exception as e:
            print(f"[Stats] Could not save scores: {e}")

    # ----------------------------------------------------------
    def format_time(self, seconds: float = None) -> str:
        if seconds is None:
            seconds = self.elapsed
        m = int(seconds) // 60
        s = int(seconds) % 60
        return f"{m:02d}:{s:02d}"

    def get_top_scores(self, n: int = 5) -> list:
        return self.high_scores[:n]

    # ----------------------------------------------------------
    def __repr__(self):
        return (f"GameStats(score={self.score}, time={self.format_time()}, "
                f"keys={self.keys_collected}/{self.total_keys}, won={self.game_won})")
