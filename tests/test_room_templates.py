"""Tests for room template validation."""

import numpy as np
import pytest
from dungeon.dungeon_gen import ROOM_TEMPLATES, RoomTemplate
from dungeon.metal_labyrinth_sprites import (
    check_valid_tiling,
    fix_tiling_to_valid,
    METAL_ASCII_TO_TILE,
    MetalTile,
    apply_patterns,
    ROOM_REPAIR_PATTERNS,
)


class TestRoomTemplateValidation:
    """Validate that all room templates have properly formed doors."""

    def test_all_templates_have_at_least_one_door(self):
        """Every room template must have at least one door."""
        for template in ROOM_TEMPLATES:
            has_door = (
                template.has_north_door
                or template.has_south_door
                or template.has_east_door
                or template.has_west_door
            )
            assert has_door, f"Template '{template.name}' has no doors"

    @pytest.mark.parametrize("template", ROOM_TEMPLATES, ids=lambda t: t.name)
    def test_north_doors_are_well_formed(self, template: RoomTemplate):
        """North doors must be a pair 'nN' (lowercase n followed by uppercase N)."""
        for row_idx, line in enumerate(template.ascii_art):
            for col_idx, char in enumerate(line):
                if char == "n":
                    # Must have 'N' immediately to the right
                    assert col_idx + 1 < len(
                        line
                    ), f"Template '{template.name}' row {row_idx}: 'n' at end of line, missing 'N'"
                    next_char = line[col_idx + 1]
                    assert next_char == "N", (
                        f"Template '{template.name}' row {row_idx}: 'n' must be followed by 'N', "
                        f"found '{next_char}'"
                    )
                elif char == "N":
                    # Must have 'n' immediately to the left
                    assert (
                        col_idx > 0
                    ), f"Template '{template.name}' row {row_idx}: 'N' at start of line, missing 'n'"
                    prev_char = line[col_idx - 1]
                    assert prev_char == "n", (
                        f"Template '{template.name}' row {row_idx}: 'N' must be preceded by 'n', "
                        f"found '{prev_char}'"
                    )

    @pytest.mark.parametrize("template", ROOM_TEMPLATES, ids=lambda t: t.name)
    def test_south_doors_are_well_formed(self, template: RoomTemplate):
        """South doors must be a pair 'sS' (lowercase s followed by uppercase S)."""
        for row_idx, line in enumerate(template.ascii_art):
            for col_idx, char in enumerate(line):
                if char == "s":
                    # Must have 'S' immediately to the right
                    assert col_idx + 1 < len(
                        line
                    ), f"Template '{template.name}' row {row_idx}: 's' at end of line, missing 'S'"
                    next_char = line[col_idx + 1]
                    assert next_char == "S", (
                        f"Template '{template.name}' row {row_idx}: 's' must be followed by 'S', "
                        f"found '{next_char}'"
                    )
                elif char == "S":
                    # Must have 's' immediately to the left
                    assert (
                        col_idx > 0
                    ), f"Template '{template.name}' row {row_idx}: 'S' at start of line, missing 's'"
                    prev_char = line[col_idx - 1]
                    assert prev_char == "s", (
                        f"Template '{template.name}' row {row_idx}: 'S' must be preceded by 's', "
                        f"found '{prev_char}'"
                    )

    @pytest.mark.parametrize("template", ROOM_TEMPLATES, ids=lambda t: t.name)
    def test_west_doors_are_well_formed(self, template: RoomTemplate):
        """West doors must be 'w' above 'W' (w on top, W below)."""
        lines = template.ascii_art
        for row_idx, line in enumerate(lines):
            for col_idx, char in enumerate(line):
                if char == "w":
                    # Must have 'W' immediately below
                    assert row_idx + 1 < len(
                        lines
                    ), f"Template '{template.name}' row {row_idx}: 'w' on last row, missing 'W' below"
                    next_line = lines[row_idx + 1]
                    assert col_idx < len(
                        next_line
                    ), f"Template '{template.name}' row {row_idx}: 'w' has no character below"
                    below_char = next_line[col_idx]
                    assert below_char == "W", (
                        f"Template '{template.name}' row {row_idx}: 'w' must have 'W' below, "
                        f"found '{below_char}'"
                    )
                elif char == "W":
                    # Must have 'w' immediately above
                    assert (
                        row_idx > 0
                    ), f"Template '{template.name}' row {row_idx}: 'W' on first row, missing 'w' above"
                    prev_line = lines[row_idx - 1]
                    assert col_idx < len(
                        prev_line
                    ), f"Template '{template.name}' row {row_idx}: 'W' has no character above"
                    above_char = prev_line[col_idx]
                    assert above_char == "w", (
                        f"Template '{template.name}' row {row_idx}: 'W' must have 'w' above, "
                        f"found '{above_char}'"
                    )

    @pytest.mark.parametrize("template", ROOM_TEMPLATES, ids=lambda t: t.name)
    def test_east_doors_are_well_formed(self, template: RoomTemplate):
        """East doors must be 'e' above 'E' (e on top, E below)."""
        lines = template.ascii_art
        for row_idx, line in enumerate(lines):
            for col_idx, char in enumerate(line):
                if char == "e":
                    # Must have 'E' immediately below
                    assert row_idx + 1 < len(
                        lines
                    ), f"Template '{template.name}' row {row_idx}: 'e' on last row, missing 'E' below"
                    next_line = lines[row_idx + 1]
                    assert col_idx < len(
                        next_line
                    ), f"Template '{template.name}' row {row_idx}: 'e' has no character below"
                    below_char = next_line[col_idx]
                    assert below_char == "E", (
                        f"Template '{template.name}' row {row_idx}: 'e' must have 'E' below, "
                        f"found '{below_char}'"
                    )
                elif char == "E":
                    # Must have 'e' immediately above
                    assert (
                        row_idx > 0
                    ), f"Template '{template.name}' row {row_idx}: 'E' on first row, missing 'e' above"
                    prev_line = lines[row_idx - 1]
                    assert col_idx < len(
                        prev_line
                    ), f"Template '{template.name}' row {row_idx}: 'E' has no character above"
                    above_char = prev_line[col_idx]
                    assert above_char == "e", (
                        f"Template '{template.name}' row {row_idx}: 'E' must have 'e' above, "
                        f"found '{above_char}'"
                    )

    @pytest.mark.parametrize("template", ROOM_TEMPLATES, ids=lambda t: t.name)
    def test_template_has_valid_tiling(self, template: RoomTemplate):
        """Room template must satisfy all tiling rules (base tiles, convex corners, etc.)."""
        # Parse ASCII art into tiles
        width = max(len(line) for line in template.ascii_art)
        height = len(template.ascii_art)

        tiles = []
        for line in template.ascii_art:
            row = [METAL_ASCII_TO_TILE[char] for char in line]
            # Pad row to width
            while len(row) < width:
                row.append(0)  # NOTHING
            tiles.append(row)

        tiles_array = np.array(tiles, dtype=int)

        # Check for tiling errors
        errors = check_valid_tiling(tiles_array)

        # Filter out door adjacency errors - those are expected for room templates
        # since doors are designed to connect to other rooms
        non_door_errors = [e for e in errors if "DOOR" not in e.message]

        assert (
            len(non_door_errors) == 0
        ), f"Template '{template.name}' has tiling errors:\n" + "\n".join(
            f"  Row {e.row}, Col {e.column}: {e.message}" for e in non_door_errors
        )

    @pytest.mark.parametrize("template", ROOM_TEMPLATES, ids=lambda t: t.name)
    def test_template_valid_after_all_doors_replaced(self, template: RoomTemplate):
        """Room template must have valid tiling after all doors are replaced with walls."""
        # Mapping from door tiles to their corresponding wall tiles
        door_to_wall = {
            MetalTile.NORTH_DOOR_WEST: MetalTile.NORTH_WALL,
            MetalTile.NORTH_DOOR_EAST: MetalTile.NORTH_WALL,
            MetalTile.SOUTH_DOOR_WEST: MetalTile.SOUTH_WALL,
            MetalTile.SOUTH_DOOR_EAST: MetalTile.SOUTH_WALL,
            MetalTile.WEST_DOOR_NORTH: MetalTile.WEST_WALL,
            MetalTile.WEST_DOOR_SOUTH: MetalTile.WEST_WALL,
            MetalTile.EAST_DOOR_NORTH: MetalTile.EAST_WALL,
            MetalTile.EAST_DOOR_SOUTH: MetalTile.EAST_WALL,
        }

        # TODO: I wonder if we can use the dungeon logic for unconnected doors
        # on a one-door dungeon to replace the doors rather than writing the
        # logic in this test directly.

        # Parse ASCII art into tiles
        width = max(len(line) for line in template.ascii_art)

        tiles = []
        for line in template.ascii_art:
            row = [METAL_ASCII_TO_TILE[char] for char in line]
            # Pad row to width
            while len(row) < width:
                row.append(0)  # NOTHING
            tiles.append(row)

        tiles_array = np.array(tiles, dtype=int)

        # Replace all door tiles with wall tiles
        for row_idx in range(tiles_array.shape[0]):
            for col_idx in range(tiles_array.shape[1]):
                tile = MetalTile(tiles_array[row_idx, col_idx])
                if tile in door_to_wall:
                    tiles_array[row_idx, col_idx] = door_to_wall[tile]

        # Apply fix_tiling_to_valid to heal issues we introduced removing the doors
        fix_tiling_to_valid(tiles_array)

        # Check for tiling errors
        errors = check_valid_tiling(tiles_array)

        # Filter out door adjacency errors (there shouldn't be any since we replaced all doors)
        non_door_errors = [e for e in errors if "DOOR" not in e.message]

        assert len(non_door_errors) == 0, (
            f"Template '{template.name}' has tiling errors after door replacement:\n"
            + "\n".join(
                f"  Row {e.row}, Col {e.column}: {e.message}" for e in non_door_errors
            )
        )


class TestTilePatterns:
    """Tests for ROOM_REPAIR_PATTERNS tile pattern matching and replacement."""

    def test_straight_east_wall_pattern_fixes_middle_tile(self):
        """
        Test that the "ensure straight east wall" pattern correctly replaces
        the middle tile in a vertical run of east walls.

        Before:              After:
        ]  (EAST_WALL)       ]  (EAST_WALL)
        -  (NORTH_WALL)  ->  ]  (EAST_WALL)
        ]  (EAST_WALL)       ]  (EAST_WALL)

        The pattern should replace a misplaced horizontal wall between
        two vertically adjacent east walls with an east wall.
        """
        # Create a 3x1 tile array with east walls and a north wall in the middle
        # Using: ] = EAST_WALL, - = NORTH_WALL
        tiles = np.array(
            [
                [MetalTile.EAST_WALL],  # row 0: ]
                [MetalTile.NORTH_WALL],  # row 1: - (wrong, should be ])
                [MetalTile.EAST_WALL],  # row 2: ]
            ],
            dtype=int,
        )

        # Apply patterns
        replacements = apply_patterns(tiles, ROOM_REPAIR_PATTERNS)

        # The middle tile should now be EAST_WALL
        assert tiles[1, 0] == MetalTile.EAST_WALL, (
            f"Expected EAST_WALL at (1,0), got {MetalTile(tiles[1, 0]).name}"
        )
        assert replacements > 0, "Expected at least one replacement"

    def test_north_door_halves_are_horizontally_adjacent(self):
        """
        Test that north door patterns look for halves side-by-side (same row).

        A north door consists of NORTH_DOOR_WEST and NORTH_DOOR_EAST
        which are horizontally adjacent (west half on left, east half on right).

        Before:           After:
        n .  (nN pair)    n N
        col0 col1         col0 col1

        Where n=NORTH_DOOR_WEST, N=NORTH_DOOR_EAST, .=FLOOR
        """
        # Create a 1x2 tile array: NORTH_DOOR_WEST at (0,0), FLOOR at (0,1)
        tiles = np.array(
            [[MetalTile.NORTH_DOOR_WEST, MetalTile.FLOOR]],
            dtype=int,
        )

        replacements = apply_patterns(tiles, ROOM_REPAIR_PATTERNS)

        # The pattern should add NORTH_DOOR_EAST to the right of NORTH_DOOR_WEST
        assert tiles[0, 1] == MetalTile.NORTH_DOOR_EAST, (
            f"Expected NORTH_DOOR_EAST at (0,1), got {MetalTile(tiles[0, 1]).name}"
        )
        assert replacements > 0, "Expected at least one replacement"

    def test_west_door_halves_are_vertically_adjacent(self):
        """
        Test that west door patterns look for halves stacked (same column).

        A west door consists of WEST_DOOR_NORTH and WEST_DOOR_SOUTH
        which are vertically adjacent (north half on top, south half below).

        Before:       After:
        w  (row 0)    w
        .  (row 1)    W

        Where w=WEST_DOOR_NORTH, W=WEST_DOOR_SOUTH, .=FLOOR
        """
        # Create a 2x1 tile array: WEST_DOOR_NORTH at (0,0), FLOOR at (1,0)
        tiles = np.array(
            [
                [MetalTile.WEST_DOOR_NORTH],
                [MetalTile.FLOOR],
            ],
            dtype=int,
        )

        replacements = apply_patterns(tiles, ROOM_REPAIR_PATTERNS)

        # The pattern should add WEST_DOOR_SOUTH below WEST_DOOR_NORTH
        assert tiles[1, 0] == MetalTile.WEST_DOOR_SOUTH, (
            f"Expected WEST_DOOR_SOUTH at (1,0), got {MetalTile(tiles[1, 0]).name}"
        )
        assert replacements > 0, "Expected at least one replacement"

    def test_north_door_walkable_checks_south(self):
        """
        Test that north door walkability is checked to the SOUTH (into the room).

        A north door is on the north wall, so the room interior is to the south.

        Before:           After:
        n N  (row 0)      n N
        # #  (row 1)      . .

        Where n=NORTH_DOOR_WEST, N=NORTH_DOOR_EAST, #=NORTH_WALL, .=FLOOR
        The walkable check should look at (1, 0) - south of the door.
        """
        tiles = np.array(
            [
                [MetalTile.NORTH_DOOR_WEST, MetalTile.NORTH_DOOR_EAST],
                [MetalTile.NORTH_WALL, MetalTile.NORTH_WALL],  # Non-walkable below
            ],
            dtype=int,
        )

        replacements = apply_patterns(tiles, ROOM_REPAIR_PATTERNS)

        # Both tiles below the door should become FLOOR
        assert tiles[1, 0] == MetalTile.FLOOR, (
            f"Expected FLOOR at (1,0), got {MetalTile(tiles[1, 0]).name}"
        )
        assert replacements > 0, "Expected at least one replacement"

    def test_west_door_walkable_checks_east(self):
        """
        Test that west door walkability is checked to the EAST (into the room).

        A west door is on the west wall, so the room interior is to the east.

        Before:       After:
        w #  (row 0)  w .
        W #  (row 1)  W .

        Where w=WEST_DOOR_NORTH, W=WEST_DOOR_SOUTH, #=WEST_WALL, .=FLOOR
        The walkable check should look at (0, 1) - east of the door.
        """
        tiles = np.array(
            [
                [MetalTile.WEST_DOOR_NORTH, MetalTile.WEST_WALL],
                [MetalTile.WEST_DOOR_SOUTH, MetalTile.WEST_WALL],
            ],
            dtype=int,
        )

        replacements = apply_patterns(tiles, ROOM_REPAIR_PATTERNS)

        # Both tiles to the right of the door should become FLOOR
        assert tiles[0, 1] == MetalTile.FLOOR, (
            f"Expected FLOOR at (0,1), got {MetalTile(tiles[0, 1]).name}"
        )
        assert replacements > 0, "Expected at least one replacement"

    def test_east_door_walkable_checks_west(self):
        """
        Test that east door walkability is checked to the WEST (into the room).

        An east door is on the east wall, so the room interior is to the west.

        Before:       After:
        # e  (row 0)  . e
        # E  (row 1)  . E

        Where e=EAST_DOOR_NORTH, E=EAST_DOOR_SOUTH, #=EAST_WALL, .=FLOOR
        The walkable check should look at (0, -1) - west of the door.
        """
        tiles = np.array(
            [
                [MetalTile.EAST_WALL, MetalTile.EAST_DOOR_NORTH],
                [MetalTile.EAST_WALL, MetalTile.EAST_DOOR_SOUTH],
            ],
            dtype=int,
        )

        replacements = apply_patterns(tiles, ROOM_REPAIR_PATTERNS)

        # Both tiles to the left of the door should become FLOOR
        assert tiles[0, 0] == MetalTile.FLOOR, (
            f"Expected FLOOR at (0,0), got {MetalTile(tiles[0, 0]).name}"
        )
        assert replacements > 0, "Expected at least one replacement"
