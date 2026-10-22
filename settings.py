# ============================================================
#  AI Sound Hunter – settings.py
#  Central configuration for all game constants & parameters
# ============================================================

import os

# --------------- Window ---------------
SCREEN_WIDTH  = 1280
SCREEN_HEIGHT = 720
FPS           = 60
TITLE         = "AI Sound Hunter"

# --------------- Colours (horror palette) ---------------
BLACK       = (0,   0,   0)
WHITE       = (255, 255, 255)
DARK_BLUE   = (10,  10,  35)
MID_BLUE    = (20,  20,  60)
PURPLE      = (80,  0,   120)
DARK_PURPLE = (40,  0,   70)
RED         = (180, 20,  20)
BRIGHT_RED  = (255, 50,  50)
DARK_RED    = (100, 0,   0)
GREEN       = (0,   200, 80)
YELLOW      = (255, 220, 0)
ORANGE      = (255, 140, 0)
GREY        = (80,  80,  80)
DARK_GREY   = (40,  40,  40)
LIGHT_GREY  = (160, 160, 160)
TEAL        = (0,   180, 180)
BLOOD_RED   = (140, 0,   0)

# HUD colours
HUD_BG      = (10,  8,   20, 200)
HUD_BORDER  = (80,  0,   120)
HUD_TEXT    = (220, 210, 255)
NOISE_LOW   = (0,   200, 80)
NOISE_MED   = (255, 180, 0)
NOISE_HIGH  = (255, 40,  40)

# --------------- Tile / Map ---------------
TILE_SIZE   = 32          # pixels per tile
MAP_COLS    = 50
MAP_ROWS    = 35

# Tile type IDs
TILE_FLOOR      = 0
TILE_WALL       = 1
TILE_DOOR       = 2
TILE_KEY        = 3
TILE_EXIT       = 4
TILE_DECORATION = 5

# --------------- Player ---------------
PLAYER_SPEED_WALK = 2.5    # pixels per frame
PLAYER_SPEED_RUN  = 5.0
PLAYER_RADIUS     = 12
PLAYER_MAX_HEALTH = 3      # hit-points (hearts)
FLASHLIGHT_RADIUS = 200    # lighting circle px
FLASHLIGHT_MAX    = 100.0  # battery %
FLASHLIGHT_DRAIN  = 0.03   # % per frame when on
FLASHLIGHT_RECHARGE = 0.01 # % per frame when off

# --------------- Noise ---------------
NOISE_WALK      = 8.0
NOISE_RUN       = 25.0
NOISE_DOOR      = 40.0
NOISE_KEY       = 15.0
NOISE_DECAY     = 0.92     # multiplier per frame
NOISE_MAX       = 100.0

# --------------- Monster ---------------
MONSTER_SPEED_PATROL     = 1.2
MONSTER_SPEED_INVESTIGATE= 1.8
MONSTER_SPEED_CHASE      = 3.4
MONSTER_SPEED_SEARCH     = 1.5
MONSTER_VISION_RANGE     = 220  # px
MONSTER_VISION_ANGLE     = 70   # degrees each side
MONSTER_HEAR_RANGE       = 400  # px at full noise
MONSTER_CAPTURE_RADIUS   = 24   # px → game over
MONSTER_SEARCH_RADIUS    = 96   # wander radius when searching
MONSTER_SEARCH_TIME      = 300  # frames to search before returning
MONSTER_PATROL_WAIT      = 120  # frames to wait at each patrol node
MONSTER_ATTACK_COOLDOWN  = 90   # frames between attacks

# FSM States
STATE_IDLE        = "IDLE"
STATE_PATROL      = "PATROL"
STATE_INVESTIGATE = "INVESTIGATE"
STATE_SEARCH      = "SEARCH"
STATE_CHASE       = "CHASE"
STATE_RETURN      = "RETURN"

# --------------- Difficulty ---------------
DIFFICULTY_INTERVALS  = [600, 1200, 1800]  # frames → difficulty steps
DIFFICULTY_SPEED_MULT = [1.0, 1.15, 1.30, 1.50]
DIFFICULTY_HEAR_MULT  = [1.0, 1.10, 1.25, 1.40]

# --------------- Scoring ---------------
SCORE_KEY_COLLECT   = 500
SCORE_EXIT          = 2000
SCORE_TIME_BONUS    = 10   # per second remaining out of 300s
SCORE_HEALTH_BONUS  = 300  # per remaining health point

# --------------- Paths ---------------
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR  = os.path.join(BASE_DIR, "assets")
IMAGES_DIR  = os.path.join(ASSETS_DIR, "images")
SOUNDS_DIR  = os.path.join(ASSETS_DIR, "sounds")
MODELS_DIR  = os.path.join(BASE_DIR, "models")
DATA_DIR    = os.path.join(BASE_DIR, "data")
SCORES_FILE = os.path.join(DATA_DIR, "highscores.json")

# --------------- Debug ---------------
DEBUG_MODE  = False        # toggle with F1 in-game
SHOW_PATH   = False        # toggle with F2
SHOW_GRID   = False        # toggle with F3
