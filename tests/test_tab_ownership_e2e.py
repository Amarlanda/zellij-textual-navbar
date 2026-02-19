"""End-to-end tests for tab ownership of pane layouts.

Tests that each tab owns its own pane tree and switching tabs
swaps the visible pane layout. Zellij: Ctrl+t mode.

Run visible:
    ATT_HEADLESS=0 pytest tests/test_tab_ownership_e2e.py -v -s

Run headless:
    pytest tests/test_tab_ownership_e2e.py -v
"""

from __future__ import annotations

import os

import pytest

from navbar.app import NavbarApp
from navbar.panes import Pane, PaneContainer
from navbar.widgets import TabList


HEADLESS = os.environ.get("ATT_HEADLESS", "1") != "0"
VISIBLE_PAUSE = 0.0 if HEADLESS else 1.0
SIZE = (100, 40)


class TestTabPaneOwnership:
    """Test that each tab owns its own pane tree."""

    async def test_new_tab_starts_with_one_pane(self):
        """Switching to a new tab should show 1 pane."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)

            # Start at tab 0 with 1 pane
            assert pc.pane_count == 1

            # Switch to tab 1 (first visit)
            await pilot.click("#tab-1")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            assert app.active_tab == 1
            assert pc.pane_count == 1

    async def test_split_panes_stay_with_tab(self):
        """Panes split in tab 0 should stay in tab 0 when switching away."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)

            # Split panes in tab 0
            await pilot.press("v")
            await pilot.pause()
            await pilot.press("d")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)
            assert pc.pane_count == 3

            # Switch to tab 1
            await pilot.click("#tab-1")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)
            assert pc.pane_count == 1  # Tab 1 has fresh pane

            # Switch back to tab 0
            await pilot.click("#tab-0")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)
            assert pc.pane_count == 3  # Tab 0 still has 3 panes

    async def test_independent_pane_layouts(self):
        """Tab 0 and tab 1 should have independent pane layouts."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)

            # Tab 0: split into 2 panes
            await pilot.press("v")
            await pilot.pause()
            assert pc.pane_count == 2

            # Switch to tab 1
            await pilot.click("#tab-1")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            # Tab 1: split into 3 panes
            await pilot.press("d")
            await pilot.pause()
            await pilot.press("d")
            await pilot.pause()
            assert pc.pane_count == 3

            # Switch back to tab 0 — should be 2
            await pilot.click("#tab-0")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)
            assert pc.pane_count == 2

            # Switch back to tab 1 — should be 3
            await pilot.click("#tab-1")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)
            assert pc.pane_count == 3

    async def test_tab_pane_count_updates_sidebar(self):
        """The sidebar tab should show correct pane count after split."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)
            tab_list = app.query_one("#tab-list", TabList)

            # Split in tab 0
            await pilot.press("v")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            # Tab 0 should show pane count of 2
            assert tab_list.tab_items[0].pane_count == 2


class TestTabPaneCommandPersistence:
    """Test that pane commands persist across tab switches."""

    async def test_command_output_survives_tab_switch(self):
        """Command output in tab 0 should persist after switching away and back."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)

            # Run a command in tab 0's pane
            pane_id = pc.focused_pane_id
            await pc.run_command_in_focused('echo "tab0-data"')
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            pane = pc.get_pane(pane_id)
            assert pane is not None
            assert "tab0-data" in pane.command_output

            # Switch to tab 1
            await pilot.click("#tab-1")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            # Switch back to tab 0
            await pilot.click("#tab-0")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            # Command output should still be there
            restored_pane = pc.get_pane(pane_id)
            assert restored_pane is not None
            assert "tab0-data" in restored_pane.command_output

    async def test_different_commands_in_different_tabs(self):
        """Each tab should have its own command state."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)

            # Tab 0: run command
            tab0_pane_id = pc.focused_pane_id
            await pc.run_command_in_focused('echo "TAB-ZERO"')
            await pilot.pause()

            # Switch to tab 1: run different command
            await pilot.click("#tab-1")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            tab1_pane_id = pc.focused_pane_id
            await pc.run_command_in_focused('echo "TAB-ONE"')
            await pilot.pause()

            # Verify tab 1 has TAB-ONE
            tab1_pane = pc.get_pane(tab1_pane_id)
            assert tab1_pane is not None
            assert "TAB-ONE" in tab1_pane.command_output

            # Switch back to tab 0
            await pilot.click("#tab-0")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            # Verify tab 0 has TAB-ZERO (not TAB-ONE)
            tab0_pane = pc.get_pane(tab0_pane_id)
            assert tab0_pane is not None
            assert "TAB-ZERO" in tab0_pane.command_output


class TestTabSwitchingWithKeyboard:
    """Test tab switching via number keys."""

    async def test_number_keys_switch_pane_layout(self):
        """Pressing number keys should switch both tab and pane layout."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)

            # Split in tab 0
            await pilot.press("v")
            await pilot.pause()
            assert pc.pane_count == 2

            # Press "2" to switch to tab 1
            await pilot.press("2")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)
            assert app.active_tab == 1
            assert pc.pane_count == 1

            # Press "1" to go back to tab 0
            await pilot.press("1")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)
            assert app.active_tab == 0
            assert pc.pane_count == 2


class TestTabFocusPersistence:
    """Test that pane focus is preserved across tab switches."""

    async def test_focus_preserved_on_switch(self):
        """The focused pane should be remembered per tab."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)

            # Tab 0: split and focus first pane
            await pilot.press("v")
            await pilot.pause()
            ids = pc.all_pane_ids
            assert len(ids) == 2

            # Focus the first pane (split focuses the new one)
            await pc.focus_pane(ids[0])
            await pilot.pause()
            assert pc.focused_pane_id == ids[0]

            # Switch to tab 1
            await pilot.click("#tab-1")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            # Switch back to tab 0
            await pilot.click("#tab-0")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            # Focus should be restored to the first pane
            assert pc.focused_pane_id == ids[0]
