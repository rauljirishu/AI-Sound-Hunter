<<<<<<< HEAD
<div align="center">

<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />

  <h1>Built with AI Studio</h2>

  <p>The fastest path from prompt to production with Gemini.</p>

  <a href="https://aistudio.google.com/apps">Start building</a>

</div>
=======
# AI Sound Hunter 🎮👾

> A 2D top-down horror escape game built with Python + Pygame for a college AI subject project.

## Quick Start

```powershell
# From the AI_Sound_Hunter directory:
uv venv --python 3.12 venv
uv pip install pygame numpy scikit-learn --python venv\Scripts\python.exe
venv\Scripts\activate
python main.py
```

## Controls

| Key | Action |
|-----|--------|
| WASD / Arrow Keys | Move |
| Shift | Run (loud!) |
| E | Open door / Interact |
| F | Toggle flashlight |
| F1 | Debug mode (shows AI state, vision cone, path) |
| ESC | Pause |

## Objective

1. Collect all **3 keys** scattered in the facility
2. Reach the **EXIT** (green portal)
3. Do it **quietly** — the monster hunts by sound!

## AI Concepts Demonstrated

| Concept | File | Description |
|---------|------|-------------|
| Finite State Machine | `monster.py` | 6-state enemy AI |
| A\* Pathfinding | `pathfinding.py` | Obstacle-aware navigation |
| Noise Propagation | `sound_system.py` | Distance + wall attenuation |
| Utility Decisions | `monster.py` | Priority-based state transitions |
| SVM Classifier | `sound_system.py` | ML sound categorisation |

## Project Structure

```
AI_Sound_Hunter/
├── main.py          ← Game loop + state machine
├── settings.py      ← All constants
├── level.py         ← Map, tiles, keys, doors
├── player.py        ← Player movement + flashlight
├── monster.py       ← AI enemy (FSM + A*)
├── pathfinding.py   ← A* search algorithm
├── sound_system.py  ← Noise model + SVM classifier
├── ui.py            ← All screens and HUD
├── game_stats.py    ← Score + persistence
└── train_svm.py     ← Standalone ML training script
```

## Optional: Train SVM Separately

```powershell
python train_svm.py
```

Prints accuracy, per-class precision/recall, and saves model to `models/svm_classifier.pkl`.

## Sound Files (Optional)

Place `.wav` or `.ogg` files in `assets/sounds/`:

```
footstep_walk.wav   footstep_run.wav
door_open.wav       key_collect.wav
monster_roar.wav    player_hurt.wav
game_over.wav       victory.wav
ambient_horror.ogg
```

The game runs fully without sound files (procedural graphics only).

---

*College AI Project — Demonstrates FSM, A\*, noise propagation, and SVM.*
>>>>>>> 5cccccf (Initial commit - AI Sound Hunter game)
