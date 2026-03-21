import heapq
import random
from dataclasses import dataclass

from scipy.spatial import KDTree

from domain.entities import Geometry, Castle
from domain.enums import COLLISIONS, STATE

from tiledpy import TileMap, Parser, OFFSET


@dataclass
class SimpleRect:
    """Rect de colisión independiente de pygame."""
    x: float
    y: float
    width: float
    height: float

    @property
    def left(self):
        return self.x

    @property
    def right(self):
        return self.x + self.width

    @property
    def top(self):
        return self.y

    @property
    def bottom(self):
        return self.y + self.height


class MapData:
    COMMON_COLLISIONS = {"tree", "building", "cliff", "castle", "river"}
    COLLISION_TILES = {
        COLLISIONS.PLAYER: {"deep_water", *COMMON_COLLISIONS},
        COLLISIONS.BULLET: {"tree", "building", "deep_water", "castle"},
        COLLISIONS.SHIP: {"ground", *COMMON_COLLISIONS},
        COLLISIONS.ENEMY: {"deep_water", *COMMON_COLLISIONS},
    }

    PLAYER_SPAWN_CODES = {"player_spawn"}
    SHIP_SPAWN_CODES = {"deep_water"}
    SHIP_DISEMBARK_CODES = {"beach"}
    ENEMY_TARGET_CODES = {"beach", "castle"}

    def __init__(self, data: str, scale: int = 1) -> None:
        self.map: TileMap = Parser.load(data)
        self.scale = scale

        self._collision_shapes_by_tile_pos: dict[tuple, list[SimpleRect]] = {}
        self.enemy_target_tiles: set[tuple[int, int]] = set()

        self.__set_collision_tiles()
        self.__set_player_spawn_positions()
        self.__set_ship_spawn_positions()
        self.__set_blocked_tiles()
        self.__set_disembark_positions()
        self.__set_castles()
        self.__set_enemy_target_positions()

    def _visible_tile_layers(self):
        return [l for l in self.map.get_tile_layers() if l.visible]

    @property
    def collision_shapes(self) -> dict[tuple, list[SimpleRect]]:
        return self._collision_shapes_by_tile_pos

    @property
    def width(self):
        return self.map.width * self.map.tile_width * self.scale

    @property
    def height(self):
        return self.map.height * self.map.tile_height * self.scale

    @property
    def castles(self):
        return self._castles

    def __set_collision_tiles(self):
        self.solid_tree_by_collision: dict[COLLISIONS, KDTree] = {}
        self.solid_positions_by_collision: dict[COLLISIONS, list] = {}

        all_positions: set[tuple] = set()
        for collision in COLLISIONS:
            positions = []
            self.__set_collision_pos(collision, positions)

            self.solid_tree_by_collision[collision] = (
                KDTree(positions) if positions else None
            )
            self.solid_positions_by_collision[collision] = positions
            all_positions.update(map(tuple, positions))

        self.__create_collision_rectangles(all_positions)

    def __create_collision_rectangles(self, all_positions):
        tw = self.map.tile_width * self.scale
        th = self.map.tile_height * self.scale

        for tx, ty in all_positions:
            for layer in self._visible_tile_layers():
                tile_data = layer.get_tile(tx, ty)

                if not tile_data or not tile_data.collision_objects:
                    continue

                wx = tx * tw
                wy = ty * th

                for col in tile_data.collision_objects:
                    origin_x = wx
                    tile_h = tile_data.height() or self.map.tile_height
                    origin_y = wy - (tile_h - self.map.tile_height) * self.scale
                    rect = SimpleRect(
                        origin_x + col["x"] * self.scale,
                        origin_y + col["y"] * self.scale,
                        col["width"] * self.scale,
                        col["height"] * self.scale,
                    )
                    self._collision_shapes_by_tile_pos.setdefault((tx, ty), []).append(
                        rect
                    )

    def __set_collision_pos(self, collision, positions):
        for collision_id in self.COLLISION_TILES[collision]:
            for layer in self._visible_tile_layers():
                positions.extend(
                    (td.tx, td.ty) for td in layer.get_tiles_by_class(collision_id)
                )

    def __set_player_spawn_positions(self):
        self.player_spawn_tiles = []
        for layer in self._visible_tile_layers():
            for code in self.PLAYER_SPAWN_CODES:
                self.player_spawn_tiles.extend(
                    (td.tx, td.ty) for td in layer.get_tiles_by_class(code)
                )

    def __set_ship_spawn_positions(self):
        self.ship_spawn_tiles = []
        for layer in self._visible_tile_layers():
            for code in self.SHIP_SPAWN_CODES:
                self.ship_spawn_tiles.extend(
                    (td.tx, td.ty) for td in layer.get_tiles_by_class(code)
                )

    def __set_blocked_tiles(self):
        self._blocked_by_collision: dict[COLLISIONS, set] = {}
        for collision in COLLISIONS:
            blocked: list[tuple[int, int]] = []
            self.__collect_blocked(collision, blocked)
            self._blocked_by_collision[collision] = set(blocked)

    def __collect_blocked(
        self, collision: COLLISIONS, blocked: list[tuple[int, int]]
    ) -> None:
        for layer in self._visible_tile_layers():
            for code in self.COLLISION_TILES[collision]:
                blocked.extend(
                    (td.tx, td.ty) for td in layer.get_tiles_by_class(code)
                )

    def __get_neightboors(self, x, y) -> list[tuple]:
        result = []
        cols = self.map.width
        rows = self.map.height

        for di, dj in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = x + di, y + dj
            if 0 <= nx < cols and 0 <= ny < rows:
                result.append((nx, ny))

        return result

    def __set_disembark_positions(self):
        blocked = self._blocked_by_collision[COLLISIONS.SHIP]

        tiles = []
        for layer in self._visible_tile_layers():
            for code in self.SHIP_DISEMBARK_CODES:
                res = [(td.tx, td.ty) for td in layer.get_tiles_by_class(code)]

                for x, y in res.copy():
                    res.extend(self.__get_neightboors(x, y))

                tiles.extend(res)
        else:
            tiles = set(tiles)

        tiles.difference_update(blocked)
        self.disembark_tiles = list(tiles)

    def __set_enemy_target_positions(self):
        blocked = self._blocked_by_collision[COLLISIONS.ENEMY]

        tiles = []
        for layer in self._visible_tile_layers():
            for code in self.ENEMY_TARGET_CODES:
                res = [(td.tx, td.ty) for td in layer.get_tiles_by_class(code)]

                for x, y in res.copy():
                    res.extend(self.__get_neightboors(x, y))

                tiles.extend(res)
        else:
            tiles = set(tiles)

        tiles.difference_update(blocked)
        self.enemy_target_tiles.update(tiles)

    def __set_castles(self):
        self._castles: dict[int, Castle] = {}

        for layer in self.map.get_object_layers():
            for castle in layer.get_objects_by_class("castle"):
                x, y = castle.x, castle.y
                tx, ty = self.map.world_to_tile(x, y, offset=OFFSET.RIGHT_TOP)
                x, y = self.map.tile_to_world(tx, ty, self.scale, offset=OFFSET.CENTER)
                self.castles[castle.id] = Castle(int(x), int(y))
                self.enemy_target_tiles.add((tx, ty))

    def remove_castle(self, castle_id: int):
        castle = self._castles.pop(castle_id)
        tx, ty = self.pixel_to_tile(castle.x, castle.y)
        self.enemy_target_tiles.discard((tx, ty))

    def tile_center(self, col: int, row: int) -> tuple[int, int]:
        x, y = self.map.tile_to_world(col, row, self.scale, OFFSET.CENTER)
        return int(x), int(y)

    def pixel_to_tile(self, x: float, y: float) -> tuple[int, int]:
        col, row = self.map.world_to_tile(x, y, self.scale)
        return int(col), int(row)

    def find_path(
        self,
        scol: int,
        srow: int,
        tcol: int,
        trow: int,
        collision: COLLISIONS = COLLISIONS.PLAYER,
    ) -> list[STATE]:
        cols = self.map.width
        rows = self.map.height
        blocked = self._blocked_by_collision[collision]

        start = (scol, srow)
        goal = (tcol, trow)

        if start == goal:
            return []

        _DIRS = [
            (STATE.UP, (0, -1)),
            (STATE.DOWN, (0, 1)),
            (STATE.LEFT, (-1, 0)),
            (STATE.RIGHT, (1, 0)),
        ]

        open_heap: list[tuple] = []
        heapq.heappush(open_heap, (0, 0, start))
        came_from: dict[tuple, tuple] = {}
        g_score: dict[tuple, int] = {start: 0}

        while open_heap:
            _, g, current = heapq.heappop(open_heap)

            if current == goal:
                path: list[STATE] = []
                node = current
                while node in came_from:
                    prev, direction = came_from[node]
                    path.append(direction)
                    node = prev
                path.reverse()
                return path

            if g > g_score.get(current, float("inf")):
                continue

            cx, cy = current
            for state, (dx, dy) in _DIRS:
                neighbor = (cx + dx, cy + dy)
                nc, nr = neighbor
                if nc < 0 or nc >= cols or nr < 0 or nr >= rows:
                    continue
                if neighbor in blocked:
                    continue
                new_g = g + 1
                if new_g < g_score.get(neighbor, float("inf")):
                    g_score[neighbor] = new_g
                    h = abs(nc - goal[0]) + abs(nr - goal[1])
                    heapq.heappush(open_heap, (new_g + h, new_g, neighbor))
                    came_from[neighbor] = (current, state)

        return []

    def spawn(self, is_player=True) -> tuple[int | float, int | float]:
        if is_player:
            j, i = random.choice(self.player_spawn_tiles)
        else:
            j, i = random.choice(self.ship_spawn_tiles)

        return self.map.tile_to_world(j, i, self.scale, OFFSET.CENTER)

    def is_collision(self, pos: Geometry, collision: COLLISIONS):
        if self.solid_tree_by_collision[collision] is None:
            return False

        tx_f, ty_f = self.map.world_to_tile(pos.x, pos.y, self.scale, OFFSET.CENTER)
        nearby_indices = self.solid_tree_by_collision[collision].query_ball_point(
            [tx_f, ty_f], 2
        )

        tw = self.map.tile_width * self.scale
        th = self.map.tile_height * self.scale

        for idx in nearby_indices:
            tx, ty = self.solid_positions_by_collision[collision][idx]

            shapes = self._collision_shapes_by_tile_pos.get((tx, ty))
            if shapes:
                for shape in shapes:
                    cx = max(shape.left, min(pos.x, shape.right))
                    cy = max(shape.top, min(pos.y, shape.bottom))
                    if (pos.x - cx) ** 2 + (pos.y - cy) ** 2 < pos.radius**2:
                        return True
            else:
                cx = max(tx * tw, min(pos.x, (tx + 1) * tw))
                cy = max(ty * th, min(pos.y, (ty + 1) * th))
                if (pos.x - cx) ** 2 + (pos.y - cy) ** 2 < pos.radius**2:
                    return True

        return False