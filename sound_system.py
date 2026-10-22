# ============================================================
#  AI Sound Hunter – sound_system.py
#  Noise propagation model + optional SVM audio classifier
# ============================================================

import math
import random
import os
import json
import pygame
from settings import *


# ---------------------------------------------------------------
# SoundEvent – a noise pulse in the world
# ---------------------------------------------------------------
class SoundEvent:
    """Represents a single sound generated at a world position."""
    __slots__ = ("x", "y", "intensity", "age", "source")

    def __init__(self, x: float, y: float, intensity: float, source: str = "unknown"):
        self.x = x
        self.y = y
        self.intensity = intensity
        self.age = 0          # frames
        self.source = source  # "walk","run","door","key","ambient"

    def decay(self):
        self.intensity *= NOISE_DECAY
        self.age += 1
        return self.intensity > 0.5

    def __repr__(self):
        return f"SoundEvent({self.source}, {self.intensity:.1f} @ ({self.x:.0f},{self.y:.0f}))"


# ---------------------------------------------------------------
# NoisePropagation
# ---------------------------------------------------------------
class NoisePropagation:
    """
    Simulates how sound travels through the environment.

    The model:
      - Emitted_intensity → decays with distance (inverse-square)
      - Additional attenuation if walls are between source & listener
      - Time-based decay per frame
    """

    def __init__(self):
        self.events: list[SoundEvent] = []

    # ---- emit ------------------------------------------------
    def emit(self, x: float, y: float, intensity: float, source: str = "unknown"):
        """Add a new sound event at world position (x, y)."""
        self.events.append(SoundEvent(x, y, intensity, source))

    # ---- update ----------------------------------------------
    def update(self):
        """Decay all events and remove inaudible ones."""
        self.events = [e for e in self.events if e.decay()]

    # ---- perceived_at ----------------------------------------
    def perceived_at(self, listener_x: float, listener_y: float,
                     grid=None) -> tuple:
        """
        Returns (total_intensity, loudest_event) as perceived by a
        listener at (listener_x, listener_y).

        If grid is provided, walls reduce intensity.
        """
        best_event = None
        best_perceived = 0.0
        total = 0.0

        for ev in self.events:
            dist = math.hypot(listener_x - ev.x, listener_y - ev.y)
            if dist < 1:
                dist = 1.0
            # Inverse-distance attenuation
            perceived = ev.intensity / (1 + dist / 80.0)

            # Wall occlusion: rough ray-cast count
            if grid is not None:
                walls = self._count_walls_between(ev.x, ev.y,
                                                   listener_x, listener_y, grid)
                perceived *= (0.5 ** walls)

            total += perceived
            if perceived > best_perceived:
                best_perceived = perceived
                best_event = ev

        return min(total, NOISE_MAX), best_event

    # ---- _count_walls_between --------------------------------
    def _count_walls_between(self, ax, ay, bx, by, grid) -> int:
        """Bresenham line-of-sight wall count (tiles)."""
        rows = len(grid)
        cols = len(grid[0]) if rows else 0
        ac = int(ax // TILE_SIZE); ar = int(ay // TILE_SIZE)
        bc = int(bx // TILE_SIZE); br = int(by // TILE_SIZE)

        dx = abs(bc - ac); sx = 1 if ac < bc else -1
        dy = abs(br - ar); sy = 1 if ar < br else -1
        err = dx - dy
        cx, cy = ac, ar
        walls = 0

        for _ in range(200):
            if cx == bc and cy == br:
                break
            if 0 <= cy < rows and 0 <= cx < cols:
                if grid[cy][cx] == TILE_WALL:
                    walls += 1
            e2 = 2 * err
            if e2 > -dy:
                err -= dy; cx += sx
            if e2 <  dx:
                err += dx; cy += sy

        return walls

    # ---- get_loudest -----------------------------------------
    def get_loudest(self) -> SoundEvent:
        if not self.events:
            return None
        return max(self.events, key=lambda e: e.intensity)

    # ---- classify (rule-based fallback) ----------------------
    @staticmethod
    def classify_rule_based(intensity: float, source: str) -> str:
        """
        Simple rule-based classifier: maps intensity + source to a
        semantic category. Used as fallback when ML model unavailable.
        Returns: 'silence' | 'footstep' | 'running' | 'door' | 'alert'
        """
        if source == "door":
            return "door"
        if source in ("key", "interact"):
            return "alert"
        if intensity < 5:
            return "silence"
        if intensity < 15:
            return "footstep"
        if intensity < 30:
            return "running"
        return "alert"


# ---------------------------------------------------------------
# SVMAudioClassifier (optional ML component)
# ---------------------------------------------------------------
try:
    from sklearn.svm import SVC
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, accuracy_score
    import numpy as np
    _SKLEARN_AVAILABLE = True
except ImportError:
    _SKLEARN_AVAILABLE = False


class SVMAudioClassifier:
    """
    Optional ML component: SVM classifier for sound categories.

    Uses hand-crafted feature vectors derived from simulated game
    sound events (intensity, duration, source tag, ambient level).

    In a real application these features would come from MFCC analysis
    of actual audio clips (e.g. via librosa).  Here we simulate those
    feature values from gameplay parameters so the game runs without
    audio-processing dependencies.
    """

    LABELS = ["silence", "footstep", "running", "door", "alert"]
    MODEL_PATH = os.path.join(MODELS_DIR, "svm_classifier.json")

    def __init__(self):
        self.available = _SKLEARN_AVAILABLE
        self.trained   = False
        self.model     = None
        self.scaler    = None
        self.accuracy  = None

        if self.available:
            self._try_load()

    # ---- feature extraction ----------------------------------
    @staticmethod
    def extract_features(intensity: float, source: str,
                         ambient: float, age: int) -> list:
        """
        Simulate a feature vector.  In a real system these would be
        13-coefficient MFCCs + delta features from raw audio.

        Features (8-dim):
          0  intensity          – raw noise level
          1  norm_intensity     – intensity / NOISE_MAX
          2  is_walk            – binary
          3  is_run             – binary
          4  is_door            – binary
          5  is_interact        – binary
          6  ambient_ratio      – intensity / (ambient + 1)
          7  age_norm           – age / 60
        """
        src_map = {"walk": (1,0,0,0), "run": (0,1,0,0),
                   "door": (0,0,1,0), "key":  (0,0,0,1),
                   "interact": (0,0,0,1)}
        sw, sr, sd, si = src_map.get(source, (0,0,0,0))
        return [
            intensity,
            intensity / NOISE_MAX,
            float(sw), float(sr), float(sd), float(si),
            intensity / (ambient + 1.0),
            min(age / 60.0, 1.0),
        ]

    # ---- generate training data ------------------------------
    @staticmethod
    def generate_training_data(n_samples: int = 1000) -> tuple:
        """
        Procedurally generate labelled training examples.
        Returns (X, y) numpy arrays.
        """
        import numpy as np
        rng = np.random.default_rng(0)
        X, y = [], []

        dist = {
            "silence":  (rng, 0,   2,   "walk", 0.0),
            "footstep": (rng, 5,   14,  "walk", 2.0),
            "running":  (rng, 16,  28,  "run",  5.0),
            "door":     (rng, 35,  45,  "door", 3.0),
            "alert":    (rng, 46,  100, "key",  8.0),
        }

        for label, (rg, lo, hi, src, amb) in dist.items():
            for _ in range(n_samples // len(dist)):
                intensity = float(rg.uniform(lo, hi))
                age       = int(rg.integers(0, 60))
                ambient   = float(rg.uniform(0, amb + 1))
                feats = SVMAudioClassifier.extract_features(
                    intensity, src, ambient, age)
                X.append(feats)
                y.append(label)

        return np.array(X), np.array(y)

    # ---- train -----------------------------------------------
    def train(self, n_samples: int = 1000):
        if not self.available:
            print("[SVM] scikit-learn not available; using rule-based fallback.")
            return
        import numpy as np
        X, y = self.generate_training_data(n_samples)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.25, random_state=42, stratify=y)

        self.scaler = StandardScaler()
        X_train_s = self.scaler.fit_transform(X_train)
        X_test_s  = self.scaler.transform(X_test)

        self.model = SVC(kernel='rbf', C=10, gamma='scale',
                         class_weight='balanced')
        self.model.fit(X_train_s, y_train)

        y_pred = self.model.predict(X_test_s)
        self.accuracy = accuracy_score(y_test, y_pred)
        print(f"[SVM] Trained. Accuracy: {self.accuracy*100:.1f}%")
        print(classification_report(y_test, y_pred, zero_division=0))

        self.trained = True
        self._save()

    # ---- predict ---------------------------------------------
    def predict(self, intensity: float, source: str,
                ambient: float = 0.0, age: int = 0) -> str:
        if not self.available or not self.trained:
            return NoisePropagation.classify_rule_based(intensity, source)
        import numpy as np
        feats = self.extract_features(intensity, source, ambient, age)
        feats_s = self.scaler.transform(np.array([feats]))
        return self.model.predict(feats_s)[0]

    # ---- persistence -----------------------------------------
    def _save(self):
        os.makedirs(MODELS_DIR, exist_ok=True)
        data = {
            "accuracy": self.accuracy,
            "trained": self.trained,
            "note": "Full model requires scikit-learn pickle; accuracy stored here."
        }
        with open(self.MODEL_PATH, "w") as f:
            json.dump(data, f, indent=2)
        # Also save sklearn model via joblib if available
        try:
            import joblib
            joblib.dump({"model": self.model, "scaler": self.scaler},
                        self.MODEL_PATH.replace(".json", ".pkl"))
            print("[SVM] Model saved to models/svm_classifier.pkl")
        except Exception:
            pass

    def _try_load(self):
        pkl = self.MODEL_PATH.replace(".json", ".pkl")
        if not os.path.exists(pkl):
            return
        try:
            import joblib
            data = joblib.load(pkl)
            self.model   = data["model"]
            self.scaler  = data["scaler"]
            self.trained = True
            print("[SVM] Loaded saved model from", pkl)
        except Exception as e:
            print(f"[SVM] Could not load model: {e}")


# ---------------------------------------------------------------
# SoundManager – wraps pygame.mixer
# ---------------------------------------------------------------
class SoundManager:
    """
    Loads and plays game sounds.  Falls back gracefully when sound
    files are missing or pygame.mixer is unavailable.
    """

    def __init__(self):
        self._sounds: dict = {}
        self._music_playing = False
        self._enabled = False

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2,
                                  buffer=512)
            self._enabled = True
        except Exception as e:
            print(f"[Audio] mixer init failed: {e}")

        self._load_sounds()

    # ----------------------------------------------------------
    def _load_sounds(self):
        """Attempt to load each sound file; silently skip if missing."""
        sound_files = {
            "footstep_walk": "footstep_walk.wav",
            "footstep_run":  "footstep_run.wav",
            "door_open":     "door_open.wav",
            "key_collect":   "key_collect.wav",
            "monster_roar":  "monster_roar.wav",
            "monster_step":  "monster_step.wav",
            "player_hurt":   "player_hurt.wav",
            "game_over":     "game_over.wav",
            "victory":       "victory.wav",
            "menu_click":    "menu_click.wav",
            "heartbeat":     "heartbeat.wav",
        }
        if not self._enabled:
            return
        for key, fname in sound_files.items():
            path = os.path.join(SOUNDS_DIR, fname)
            if os.path.exists(path):
                try:
                    self._sounds[key] = pygame.mixer.Sound(path)
                except Exception:
                    pass

    def play(self, name: str, volume: float = 0.7, loops: int = 0):
        if not self._enabled or name not in self._sounds:
            return
        try:
            s = self._sounds[name]
            s.set_volume(volume)
            s.play(loops=loops)
        except Exception:
            pass

    def stop(self, name: str):
        if not self._enabled or name not in self._sounds:
            return
        try:
            self._sounds[name].stop()
        except Exception:
            pass

    def play_music(self, fname: str = "ambient_horror.ogg", volume: float = 0.35):
        if not self._enabled:
            return
        path = os.path.join(SOUNDS_DIR, fname)
        if not os.path.exists(path):
            return
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play(-1)
            self._music_playing = True
        except Exception as e:
            print(f"[Audio] music load failed: {e}")

    def stop_music(self):
        if self._enabled:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass

    def set_music_volume(self, vol: float):
        if self._enabled:
            try:
                pygame.mixer.music.set_volume(max(0.0, min(1.0, vol)))
            except Exception:
                pass
