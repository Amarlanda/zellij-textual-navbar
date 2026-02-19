"""End-to-end tests for the pane system.

Tests vertical/horizontal splits, pane focus navigation, and
pane closing — all using Textual's Pilot API.

Zellij keybindings tested:
    d = split horizontal (new pane below)
    v = split vertical (new pane right)
    x = close focused pane
    Click = focus pane

Run visible (watch the UI being driven):
    ATT_HEADLESS=0 pytest tests/test_panes_e2e.py -v -s

Run headless (fast, for CI):
    pytest tests/test_panes_e2e.py -v
"""

from __future__ import annotations

import os

import pytest

from navbar.app import NavbarApp
from navbar.panes import Pane, PaneContainer


# Use headless=False when ATT_HEADLESS=0 (visible mode for VNC)
HEADLESS = os.environ.get("ATT_HEADLESS", "1") != "0"
VISIBLE_PAUSE = 0.0 if HEADLESS else 1.0
SIZE = (100, 40)  # Wider to accommodate sidebar + pane area


class TestPaneStartup:
    """Test that the pane area initializes correctly."""

    async def test_pane_container_exists(self):
        """Pane container should be mounted."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)
            pc = app.query_one("#pane-container", PaneContainer)
            assert pc is not None

    async def test_initial_single_pane(self):
        """Should start with exactly 1 pane."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)
            pc = app.query_one("#pane-container", PaneContainer)
            assert pc.pane_count == 1

    async def test_initial_pane_is_focused(self):
        """The initial pane should be focused."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)
            pc = app.query_one("#pane-container", PaneContainer)
            pane = pc.get_pane(pc.focused_pane_id)
            assert pane is not None
            assert pane.is_focused_pane is True

    async def test_pane_has_name(self):
        """The initial pane should have a name."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)
            pc = app.query_one("#pane-container", PaneContainer)
            pane = pc.get_pane(pc.focused_pane_id)
            assert pane is not None
            assert "Pane" in pane.pane_name

    async def test_sidebar_and_panes_coexist(self):
        """Sidebar and pane area should both be visible."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)
            # Sidebar elements
            assert app.query_one("#nav-header") is not None
            assert app.query_one("#tab-list") is not None
            # Pane area
            assert app.query_one("#pane-container") is not None


class TestHorizontalSplit:
    """Test horizontal splits (new pane below). Zellij: Ctrl+p → d"""

    async def test_split_horizontal_creates_two_panes(self):
        """Pressing 'd' should split into 2 panes."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)
            assert pc.pane_count == 1

            await pilot.press("d")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            assert pc.pane_count == 2

    async def test_split_horizontal_focuses_new_pane(self):
        """After horizontal split, the new pane should be focused."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)
            old_id = pc.focused_pane_id

            await pilot.press("d")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            assert pc.focused_pane_id != old_id
            new_pane = pc.get_pane(pc.focused_pane_id)
            assert new_pane is not None
            assert new_pane.is_focused_pane is True

    async def test_multiple_horizontal_splits(self):
        """Multiple 'd' presses should create multiple panes."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)

            await pilot.press("d")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)
            assert pc.pane_count == 2

            await pilot.press("d")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)
            assert pc.pane_count == 3


class TestVerticalSplit:
    """Test vertical splits (new pane right). Zellij: Ctrl+p → r/v"""

    async def test_split_vertical_creates_two_panes(self):
        """Pressing 'v' should split into 2 panes."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)
            assert pc.pane_count == 1

            await pilot.press("v")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            assert pc.pane_count == 2

    async def test_split_vertical_focuses_new_pane(self):
        """After vertical split, the new pane should be focused."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)
            old_id = pc.focused_pane_id

            await pilot.press("v")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            assert pc.focused_pane_id != old_id

    async def test_mixed_splits(self):
        """Vertical then horizontal splits should create 3 panes."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)

            await pilot.press("v")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)
            assert pc.pane_count == 2

            await pilot.press("d")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)
            assert pc.pane_count == 3


class TestPaneFocus:
    """Test pane focus navigation."""

    async def test_click_to_focus_pane(self):
        """Clicking a pane should focus it."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)

            # Split to get two panes
            await pilot.press("v")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            ids = pc.all_pane_ids
            assert len(ids) == 2

            # Focus should be on the new pane (second)
            new_focused = pc.focused_pane_id
            old_id = [pid for pid in ids if pid != new_focused][0]

            # Click the first pane to focus it
            await pilot.click(f"#{old_id}")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            assert pc.focused_pane_id == old_id

    async def test_focus_cycles_through_panes(self):
        """Focus should cycle when navigating past the last pane."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)

            # Create 3 panes
            await pilot.press("v")
            await pilot.pause()
            await pilot.press("v")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            assert pc.pane_count == 3
            ids = pc.all_pane_ids

            # Focus the first pane
            await pc.focus_pane(ids[0])
            await pilot.pause(VISIBLE_PAUSE)
            assert pc.focused_pane_id == ids[0]

            # Navigate right twice to get to third
            await pc.focus_direction("right")
            await pilot.pause(VISIBLE_PAUSE)
            assert pc.focused_pane_id == ids[1]

            await pc.focus_direction("right")
            await pilot.pause(VISIBLE_PAUSE)
            assert pc.focused_pane_id == ids[2]

            # Navigate right again should cycle to first
            await pc.focus_direction("right")
            await pilot.pause(VISIBLE_PAUSE)
            assert pc.focused_pane_id == ids[0]


class TestClosePane:
    """Test closing panes. Zellij: Ctrl+p → x"""

    async def test_close_pane_reduces_count(self):
        """Closing a pane should reduce the pane count."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)

            # Split first
            await pilot.press("v")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)
            assert pc.pane_count == 2

            # Close
            await pilot.press("x")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)
            assert pc.pane_count == 1

    async def test_cannot_close_last_pane(self):
        """Should not be able to close the last remaining pane."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)
            assert pc.pane_count == 1

            await pilot.press("x")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            # Still 1 pane
            assert pc.pane_count == 1

    async def test_close_moves_focus_to_sibling(self):
        """After closing, focus should move to a remaining pane."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)

            # Split
            await pilot.press("v")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)
            assert pc.pane_count == 2

            closed_id = pc.focused_pane_id

            # Close
            await pilot.press("x")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            assert pc.pane_count == 1
            assert pc.focused_pane_id != closed_id
            # Remaining pane should be focused
            remaining_pane = pc.get_pane(pc.focused_pane_id)
            assert remaining_pane is not None
            assert remaining_pane.is_focused_pane is True

    async def test_split_close_split_cycle(self):
        """Split, close, split again should work correctly."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)

            # Split
            await pilot.press("d")
            await pilot.pause()
            assert pc.pane_count == 2

            # Close
            await pilot.press("x")
            await pilot.pause()
            assert pc.pane_count == 1

            # Split again
            await pilot.press("v")
            await pilot.pause()
            assert pc.pane_count == 2

            await pilot.pause(VISIBLE_PAUSE)


class TestPaneTabIntegration:
    """Test that pane system integrates with the tab sidebar."""

    async def test_pane_count_updates_tab_display(self):
        """Splitting panes should update the active tab's pane count."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)
            from navbar.widgets import TabList
            tab_list = app.query_one("#tab-list", TabList)

            initial_pane_count = tab_list.tab_items[0].pane_count

            await pilot.press("d")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            # Tab should show updated pane count
            assert tab_list.tab_items[0].pane_count == pc.pane_count

    async def test_activity_bar_shows_pane_info(self):
        """Activity bar should update when pane focus changes."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            from navbar.widgets import ActivityBar
            activity = app.query_one("#activity-bar", ActivityBar)

            # Split to get two panes
            await pilot.press("v")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            # Activity bar should contain pane info
            assert "Pane" in activity.activity_text
