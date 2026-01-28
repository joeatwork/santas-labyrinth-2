"""Tests for room template validation."""

import pytest
from dungeon.dungeon_gen import ROOM_TEMPLATES, RoomTemplate, ASCII_TO_TILE, Tile


class TestRoomTemplateValidation:
    """Validate that all room templates have properly formed doors."""

    # TODO: add a test that checks for NORTH_WALL_LUMP and NORTH_WALL_LUMP_BASE

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
    def test_north_wall_tiles_have_base_below(self, template: RoomTemplate):
        """North wall tiles must have NORTH_WALL_BASE tiles directly below them."""
        lines = template.ascii_art
        north_wall_tiles = {"-"}  # NORTH_WALL

        for row_idx, line in enumerate(lines):
            for col_idx, char in enumerate(line):
                if char in north_wall_tiles:
                    # Must have a row below
                    assert row_idx + 1 < len(lines), (
                        f"Template '{template.name}' row {row_idx}: "
                        f"'{char}' on last row, missing base tile below"
                    )
                    next_line = lines[row_idx + 1]
                    assert col_idx < len(next_line), (
                        f"Template '{template.name}' row {row_idx}: "
                        f"'{char}' has no character below"
                    )
                    below_char = next_line[col_idx]

                    # The tile below must be a NORTH_WALL_BASE (,)
                    tile_below = ASCII_TO_TILE.get(below_char)
                    assert tile_below == Tile.NORTH_WALL_BASE, (
                        f"Template '{template.name}' row {row_idx}, col {col_idx}: "
                        f"'{char}' must have ',' (NORTH_WALL_BASE) below, found '{below_char}'"
                    )

    @pytest.mark.parametrize("template", ROOM_TEMPLATES, ids=lambda t: t.name)
    def test_pillar_tiles_have_base_below(self, template: RoomTemplate):
        """PILLAR tiles must have PILLAR_BASE tiles directly below them."""
        lines = template.ascii_art

        for row_idx, line in enumerate(lines):
            for col_idx, char in enumerate(line):
                if char == "P":  # PILLAR
                    # Must have a row below
                    assert row_idx + 1 < len(lines), (
                        f"Template '{template.name}' row {row_idx}: "
                        f"'P' (PILLAR) on last row, missing base tile below"
                    )
                    next_line = lines[row_idx + 1]
                    assert col_idx < len(next_line), (
                        f"Template '{template.name}' row {row_idx}: "
                        f"'P' (PILLAR) has no character below"
                    )
                    below_char = next_line[col_idx]

                    # The tile below must be a PILLAR_BASE (;)
                    tile_below = ASCII_TO_TILE.get(below_char)
                    assert tile_below == Tile.PILLAR_BASE, (
                        f"Template '{template.name}' row {row_idx}, col {col_idx}: "
                        f"'P' (PILLAR) must have ';' (PILLAR_BASE) below, found '{below_char}'"
                    )

    @pytest.mark.parametrize("template", ROOM_TEMPLATES, ids=lambda t: t.name)
    def test_convex_se_tiles_have_base_below(self, template: RoomTemplate):
        """CONVEX_SE tiles must have CONVEX_SE_BASE tiles directly below them."""
        lines = template.ascii_art

        for row_idx, line in enumerate(lines):
            for col_idx, char in enumerate(line):
                if char == "`":  # CONVEX_SE
                    # Must have a row below
                    assert row_idx + 1 < len(lines), (
                        f"Template '{template.name}' row {row_idx}: "
                        f"'`' (CONVEX_SE) on last row, missing base tile below"
                    )
                    next_line = lines[row_idx + 1]
                    assert col_idx < len(next_line), (
                        f"Template '{template.name}' row {row_idx}: "
                        f"'`' (CONVEX_SE) has no character below"
                    )
                    below_char = next_line[col_idx]

                    # The tile below must be a CONVEX_SE_BASE (>)
                    tile_below = ASCII_TO_TILE.get(below_char)
                    assert tile_below in [Tile.CONVEX_SE_BASE, Tile.WEST_DOOR_NORTH], (
                        f"Template '{template.name}' row {row_idx}, col {col_idx}: "
                        f"'`' (CONVEX_SE) must have '>' (CONVEX_SE_BASE) below, found '{below_char}'"
                    )

    @pytest.mark.parametrize("template", ROOM_TEMPLATES, ids=lambda t: t.name)
    def test_convex_sw_tiles_have_base_below(self, template: RoomTemplate):
        """CONVEX_SW tiles must have CONVEX_SW_BASE tiles directly below them."""
        lines = template.ascii_art

        for row_idx, line in enumerate(lines):
            for col_idx, char in enumerate(line):
                if char == "~":  # CONVEX_SW
                    # Must have a row below
                    assert row_idx + 1 < len(lines), (
                        f"Template '{template.name}' row {row_idx}: "
                        f"'~' (CONVEX_SW) on last row, missing base tile below"
                    )
                    next_line = lines[row_idx + 1]
                    assert col_idx < len(next_line), (
                        f"Template '{template.name}' row {row_idx}: "
                        f"'~' (CONVEX_SW) has no character below"
                    )
                    below_char = next_line[col_idx]

                    # The tile below must be a CONVEX_SW_BASE (<)
                    tile_below = ASCII_TO_TILE.get(below_char)
                    assert tile_below in [Tile.CONVEX_SW_BASE, Tile.EAST_DOOR_NORTH], (
                        f"Template '{template.name}' row {row_idx}, col {col_idx}: "
                        f"'~' (CONVEX_SW) must have '<' (CONVEX_SW_BASE) below, found '{below_char}'"
                    )
