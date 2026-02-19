"""End-to-end tests for running commands in panes.

Tests that each pane can run an independent command and display
its output. Uses simple echo commands with unique markers.

Run visible:
    ATT_HEADLESS=0 pytest tests/test_commands_e2e.py -v -s

Run headless:
    pytest tests/test_commands_e2e.py -v
"""

from __future__ import annotations

import os

import pytest

from navbar.app import NavbarApp
from navbar.panes import Pane, PaneContainer


HEADLESS = os.environ.get("ATT_HEADLESS", "1") != "0"
VISIBLE_PAUSE = 0.0 if HEADLESS else 1.0
SIZE = (100, 40)


class TestCommandExecution:
    """Test running commands in panes."""

    async def test_run_command_in_single_pane(self):
        """A pane should be able to run a command and show output."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)
            pane = pc.get_pane(pc.focused_pane_id)
            assert pane is not None

            await pane.run_command('echo "hello-world"')
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            assert "hello-world" in pane.command_output
            assert pane.command == 'echo "hello-world"'

    async def test_run_different_commands_in_two_panes(self):
        """Two panes should run different commands with unique output."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)
            first_id = pc.focused_pane_id

            # Run command in first pane
            first_pane = pc.get_pane(first_id)
            assert first_pane is not None
            await first_pane.run_command('echo "pane-1-marker"')
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            # Split to create second pane
            await pilot.press("v")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            second_id = pc.focused_pane_id
            assert second_id != first_id

            # Run different command in second pane
            second_pane = pc.get_pane(second_id)
            assert second_pane is not None
            await second_pane.run_command('echo "pane-2-marker"')
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            # Verify each pane has its unique output
            assert "pane-1-marker" in first_pane.command_output
            assert "pane-2-marker" in second_pane.command_output
            # Cross-check: outputs should not be swapped
            assert "pane-2-marker" not in first_pane.command_output
            assert "pane-1-marker" not in second_pane.command_output

    async def test_three_panes_unique_commands(self):
        """Three panes should each show unique command output."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)

            # First pane
            pane1_id = pc.focused_pane_id
            pane1 = pc.get_pane(pane1_id)
            assert pane1 is not None
            await pane1.run_command('echo "ALPHA"')
            await pilot.pause()

            # Split vertical for second pane
            await pilot.press("v")
            await pilot.pause()
            pane2_id = pc.focused_pane_id
            pane2 = pc.get_pane(pane2_id)
            assert pane2 is not None
            await pane2.run_command('echo "BRAVO"')
            await pilot.pause()

            # Split horizontal for third pane
            await pilot.press("d")
            await pilot.pause()
            pane3_id = pc.focused_pane_id
            pane3 = pc.get_pane(pane3_id)
            assert pane3 is not None
            await pane3.run_command('echo "CHARLIE"')
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            # Verify unique outputs
            assert "ALPHA" in pane1.command_output
            assert "BRAVO" in pane2.command_output
            assert "CHARLIE" in pane3.command_output

    async def test_command_shown_in_pane_render(self):
        """The command string should appear in the pane's render output."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)
            pane = pc.get_pane(pc.focused_pane_id)
            assert pane is not None

            await pane.run_command('echo "test-cmd"')
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            rendered = pane.render()
            assert '$ echo "test-cmd"' in rendered
            assert "test-cmd" in rendered


class TestCommandWithSplit:
    """Test running commands when splitting panes."""

    async def test_split_with_command(self):
        """Splitting with a command should auto-run it in the new pane."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)

            # Split with a command
            new_id = await pc.split_vertical(command='echo "auto-cmd"')
            await pilot.pause()
            # Give the command time to run
            await pilot.pause(1.0)
            await pilot.pause(VISIBLE_PAUSE)

            new_pane = pc.get_pane(new_id)
            assert new_pane is not None
            assert new_pane.command == 'echo "auto-cmd"'
            assert "auto-cmd" in new_pane.command_output

    async def test_split_horizontal_with_command(self):
        """Horizontal split with command should work."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)
            new_id = await pc.split_horizontal(command='echo "h-split-cmd"')
            await pilot.pause()
            await pilot.pause(1.0)
            await pilot.pause(VISIBLE_PAUSE)

            new_pane = pc.get_pane(new_id)
            assert new_pane is not None
            assert "h-split-cmd" in new_pane.command_output


class TestCommandPersistence:
    """Test that command state survives layout operations."""

    async def test_command_survives_sibling_split(self):
        """A pane's command output should survive when a sibling is split."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)
            first_id = pc.focused_pane_id

            # Run command in first pane
            first_pane = pc.get_pane(first_id)
            assert first_pane is not None
            await first_pane.run_command('echo "persist-me"')
            await pilot.pause()

            # Split — this triggers a full rebuild
            await pilot.press("v")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            # First pane should still have its output after rebuild
            rebuilt_pane = pc.get_pane(first_id)
            assert rebuilt_pane is not None
            assert "persist-me" in rebuilt_pane.command_output

    async def test_command_survives_sibling_close(self):
        """A pane's command output should survive when a sibling is closed."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)
            first_id = pc.focused_pane_id

            # Run command in first pane
            first_pane = pc.get_pane(first_id)
            assert first_pane is not None
            await first_pane.run_command('echo "survive-close"')
            await pilot.pause()

            # Split to create a sibling
            await pilot.press("v")
            await pilot.pause()

            # Close the new pane (which is focused)
            await pilot.press("x")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            # First pane should still have its output
            rebuilt_pane = pc.get_pane(first_id)
            assert rebuilt_pane is not None
            assert "survive-close" in rebuilt_pane.command_output


class TestRunCommandAPI:
    """Test the run_command_in_pane and run_command_in_focused APIs."""

    async def test_run_command_in_focused(self):
        """run_command_in_focused should run in the active pane."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)
            result = await pc.run_command_in_focused('echo "focused-cmd"')
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            assert result is True
            pane = pc.get_pane(pc.focused_pane_id)
            assert pane is not None
            assert "focused-cmd" in pane.command_output

    async def test_run_command_in_specific_pane(self):
        """run_command_in_pane should target a specific pane by ID."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)
            first_id = pc.focused_pane_id

            # Split to create second pane
            await pilot.press("v")
            await pilot.pause()

            # Run command specifically in the first pane (not focused)
            result = await pc.run_command_in_pane(first_id, 'echo "targeted"')
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            assert result is True
            first_pane = pc.get_pane(first_id)
            assert first_pane is not None
            assert "targeted" in first_pane.command_output

    async def test_run_command_invalid_pane(self):
        """run_command_in_pane with invalid ID should return False."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)
            result = await pc.run_command_in_pane("pane-nonexistent", 'echo "nope"')
            assert result is False
