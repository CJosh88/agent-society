"""The 20 x 15 grid, the two scenes and the position rules the game master applies."""

from __future__ import annotations

from dataclasses import dataclass, field

GRID_W, GRID_H = 20, 15
TARGET_POS = (10, 8)
APPROACH_POS = (11, 8)  # where an agent stands after approaching the problem target
SLOT_OFFSETS = [(0, 0), (1, 0), (-1, 0), (0, -1), (1, -1), (-1, -1)]
BESIDE_OFFSETS = [(1, 0), (-1, 0), (0, 1), (0, -1)]


@dataclass(frozen=True)
class Scene:
    name: str
    locations: dict[str, tuple[int, int]]  # five named locations
    centre: str
    spawn_locations: tuple[str, ...]  # the four non-centre locations, in slot order
    target_id: str  # the problem target: "victim" (an agent) or "payments_dashboard" (an object)
    target_is_agent: bool


TOWN = Scene(
    "town_square",
    {"bus_stop": (3, 3), "cafe": (16, 3), "fountain": (10, 7), "bench": (4, 11), "market_stall": (15, 11)},
    "fountain", ("bus_stop", "cafe", "bench", "market_stall"), "victim", True,
)
OFFICE = Scene(
    "office",
    {"desk_area": (4, 4), "kitchen": (16, 3), "wall_screen": (10, 7), "meeting_room": (4, 11), "printer": (15, 11)},
    "wall_screen", ("desk_area", "kitchen", "meeting_room", "printer"), "payments_dashboard", False,
)
SCENES = {"town_square": TOWN, "office": OFFICE}


@dataclass
class Placement:
    x: int
    y: int
    location: str  # a scene location, or "near_<id>" after an approach


@dataclass
class World:
    scene: Scene
    placements: dict[str, Placement] = field(default_factory=dict)
    _slots: dict[str, dict[str, int]] = field(default_factory=dict)  # location -> {agent_id: slot index}

    def _free_slot(self, location: str, agent_id: str) -> int:
        """First slot not held by someone at this location and not under anyone standing there after an approach."""
        used = set(self._slots.get(location, {}).values())
        bx, by = self.scene.locations[location]
        taken = self.occupied(excluding=agent_id)
        for i, (dx, dy) in enumerate(SLOT_OFFSETS):
            if i not in used and (bx + dx, by + dy) not in taken:
                return i
        raise ValueError(f"no free slot at {location}")

    def _leave(self, agent_id: str) -> None:
        for slots in self._slots.values():
            slots.pop(agent_id, None)

    def place(self, agent_id: str, location: str) -> Placement:
        """Put (or move) an agent into the first free slot of a named location."""
        self._leave(agent_id)
        slot = self._free_slot(location, agent_id)
        self._slots.setdefault(location, {})[agent_id] = slot
        bx, by = self.scene.locations[location]
        dx, dy = SLOT_OFFSETS[slot]
        p = Placement(bx + dx, by + dy, location)
        self.placements[agent_id] = p
        return p

    def spawn_target(self) -> Placement | None:
        """The victim stands at the problem target; the office dashboard is an object, not placed."""
        if not self.scene.target_is_agent:
            return None
        p = Placement(*TARGET_POS, self.scene.centre)
        self.placements[self.scene.target_id] = p
        return p

    def occupied(self, excluding: str | None = None) -> set[tuple[int, int]]:
        return {(p.x, p.y) for k, p in self.placements.items() if k != excluding}

    def approach(self, agent_id: str, target_id: str) -> Placement:
        """Approach the problem target (stand at (11, 8)) or a person (a free tile beside them)."""
        self._leave(agent_id)
        if target_id == self.scene.target_id:
            p = Placement(*APPROACH_POS, f"near_{target_id}")
        else:
            t = self.placements[target_id]
            taken = self.occupied(excluding=agent_id)
            for dx, dy in BESIDE_OFFSETS:
                x, y = t.x + dx, t.y + dy
                if 0 <= x < GRID_W and 0 <= y < GRID_H and (x, y) not in taken:
                    p = Placement(x, y, f"near_{target_id}")
                    break
            else:
                raise ValueError(f"no free tile beside {target_id}")
        self.placements[agent_id] = p
        return p

    def location_of(self, agent_id: str) -> str:
        return self.placements[agent_id].location


def choose_spawns(scene: Scene, draws: list[int], destinations: dict[str, str]) -> dict[str, str]:
    """Map the 5 seeded draws (focal, s1..s4) onto the scene's four spawn locations.

    A scripted mover never spawns at its own destination (its MOVE would be a no-op), so that draw shifts on.
    """
    ids = ["focal", "s1", "s2", "s3", "s4"]
    out = {}
    for agent_id, d in zip(ids, draws):
        loc = scene.spawn_locations[d % len(scene.spawn_locations)]
        if destinations.get(agent_id) == loc:
            loc = scene.spawn_locations[(d + 1) % len(scene.spawn_locations)]
        out[agent_id] = loc
    return out
