# ============================================================
#  AI Sound Hunter – pathfinding.py
#  A* search algorithm for monster navigation
# ============================================================

import heapq
import math
from settings import TILE_SIZE, TILE_WALL, TILE_DOOR


# ---------------------------------------------------------------
# Node used internally by A*
# ---------------------------------------------------------------
class Node:
    __slots__ = ("x", "y", "g", "h", "f", "parent")

    def __init__(self, x: int, y: int, g: float = 0.0, h: float = 0.0, parent=None):
        self.x = x
        self.y = y
        self.g = g          # cost from start
        self.h = h          # heuristic to goal
        self.f = g + h
        self.parent = parent

    # heapq comparison
    def __lt__(self, other):
        return self.f < other.f

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def __hash__(self):
        return hash((self.x, self.y))


# ---------------------------------------------------------------
# Octile distance heuristic (allows diagonal movement)
# ---------------------------------------------------------------
def _octile(ax: int, ay: int, bx: int, by: int) -> float:
    dx = abs(ax - bx)
    dy = abs(ay - by)
    return (dx + dy) + (math.sqrt(2) - 2) * min(dx, dy)


# ---------------------------------------------------------------
# AStarPathfinder
# ---------------------------------------------------------------
class AStarPathfinder:
    """
    Tile-based A* pathfinder.

    grid       – 2-D list[list[int]] of tile IDs (row-major)
    passable   – set of tile IDs the monster can walk on
    allow_diag – whether diagonal movement is permitted
    """

    def __init__(self, grid: list, passable: set = None, allow_diag: bool = True):
        self.grid      = grid
        self.rows      = len(grid)
        self.cols      = len(grid[0]) if self.rows else 0
        self.allow_diag = allow_diag
        # By default walls block; doors are passable (monster opens them)
        self.passable  = passable if passable is not None else {0, 2, 3, 4, 5}

    # ----------------------------------------------------------------
    def update_grid(self, grid: list):
        """Call when the map changes (e.g. a door is opened)."""
        self.grid = grid
        self.rows = len(grid)
        self.cols = len(grid[0]) if self.rows else 0

    # ----------------------------------------------------------------
    def _is_walkable(self, col: int, row: int) -> bool:
        if col < 0 or col >= self.cols or row < 0 or row >= self.rows:
            return False
        return self.grid[row][col] in self.passable

    # ----------------------------------------------------------------
    def _neighbours(self, node: Node):
        x, y = node.x, node.y
        cardinal = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        diag     = [(-1,-1), (1,-1), (-1, 1), (1,  1)]

        dirs = cardinal + (diag if self.allow_diag else [])

        for dx, dy in dirs:
            nx, ny = x + dx, y + dy
            if not self._is_walkable(nx, ny):
                continue
            # Diagonal: make sure both cardinal neighbours are walkable
            if dx != 0 and dy != 0:
                if not self._is_walkable(x + dx, y) or not self._is_walkable(x, y + dy):
                    continue
            cost = math.sqrt(2) if (dx != 0 and dy != 0) else 1.0
            yield nx, ny, cost

    # ----------------------------------------------------------------
    def find_path(self, start_px: tuple, goal_px: tuple) -> list:
        """
        Returns a list of (pixel_x, pixel_y) waypoints from start to
        goal (exclusive of start, inclusive of goal). Returns [] if no
        path exists.

        start_px / goal_px are pixel-space coords (centre of entity).
        """
        sc = int(start_px[0] // TILE_SIZE)
        sr = int(start_px[1] // TILE_SIZE)
        gc = int(goal_px[0]  // TILE_SIZE)
        gr = int(goal_px[1]  // TILE_SIZE)

        if not self._is_walkable(sc, sr):
            sc, sr = self._nearest_walkable(sc, sr)
        if not self._is_walkable(gc, gr):
            gc, gr = self._nearest_walkable(gc, gr)

        if (sc, sr) == (gc, gr):
            return []

        start_node = Node(sc, sr, 0.0, _octile(sc, sr, gc, gr))
        open_heap  = [start_node]
        open_dict  = {(sc, sr): start_node}
        closed     = set()

        while open_heap:
            current = heapq.heappop(open_heap)
            key = (current.x, current.y)

            if key in closed:
                continue
            closed.add(key)

            if current.x == gc and current.y == gr:
                return self._reconstruct(current)

            for nx, ny, cost in self._neighbours(current):
                nkey = (nx, ny)
                if nkey in closed:
                    continue
                g = current.g + cost
                h = _octile(nx, ny, gc, gr)
                if nkey in open_dict and open_dict[nkey].g <= g:
                    continue
                n = Node(nx, ny, g, h, current)
                open_dict[nkey] = n
                heapq.heappush(open_heap, n)

        return []   # no path found

    # ----------------------------------------------------------------
    def _reconstruct(self, node: Node) -> list:
        path = []
        while node.parent is not None:
            cx = node.x * TILE_SIZE + TILE_SIZE // 2
            cy = node.y * TILE_SIZE + TILE_SIZE // 2
            path.append((cx, cy))
            node = node.parent
        path.reverse()
        return path

    # ----------------------------------------------------------------
    def _nearest_walkable(self, col: int, row: int) -> tuple:
        """BFS to find the nearest walkable tile."""
        from collections import deque
        visited = set()
        q = deque([(col, row)])
        visited.add((col, row))
        while q:
            c, r = q.popleft()
            if self._is_walkable(c, r):
                return c, r
            for dc, dr in [(-1,0),(1,0),(0,-1),(0,1)]:
                nc, nr = c + dc, r + dr
                if (nc, nr) not in visited:
                    visited.add((nc, nr))
                    q.append((nc, nr))
        return col, row   # fallback – same tile


# ---------------------------------------------------------------
# Convenience: smooth a raw A* path (reduces zig-zag)
# ---------------------------------------------------------------
def smooth_path(path: list, grid: list, tile_size: int = TILE_SIZE,
                passable: set = None) -> list:
    """
    String-pulling (greedy line-of-sight pass) to reduce waypoints.
    """
    if passable is None:
        passable = {0, 2, 3, 4, 5}

    if len(path) <= 2:
        return path

    rows = len(grid)
    cols = len(grid[0]) if rows else 0

    def los(ax, ay, bx, by):
        """Bresenham line-of-sight between pixel points."""
        ac = int(ax // tile_size)
        ar = int(ay // tile_size)
        bc = int(bx // tile_size)
        br = int(by // tile_size)
        # Bresenham
        dx = abs(bc - ac); sx = 1 if ac < bc else -1
        dy = abs(br - ar); sy = 1 if ar < br else -1
        err = dx - dy
        cx, cy = ac, ar
        while True:
            if cx < 0 or cx >= cols or cy < 0 or cy >= rows:
                return False
            if grid[cy][cx] not in passable:
                return False
            if cx == bc and cy == br:
                return True
            e2 = 2 * err
            if e2 > -dy:
                err -= dy; cx += sx
            if e2 <  dx:
                err += dx; cy += sy

    smoothed = [path[0]]
    i = 0
    while i < len(path) - 1:
        j = len(path) - 1
        while j > i + 1:
            if los(path[i][0], path[i][1], path[j][0], path[j][1]):
                break
            j -= 1
        smoothed.append(path[j])
        i = j
    return smoothed
