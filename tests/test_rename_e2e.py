"""End-to-end tests for renaming tabs and panes.

Tests tab rename (Zellij: Ctrl+t → r) and pane rename
(Zellij: Ctrl+p → c) functionality.

Run visible:
    ATT_HEADLESS=0 pytest tests/test_rename_e2e.py -v -s

Run headless:
    pytest tests/test_rename_e2e.py -v
"""

from __future__ import annotations

import os

import pytest

from navbar.app import NavbarApp
from navbar.panes import PaneContainer
from navbar.widgets import TabList


HEADLESS = os.environ.get("ATT_HEADLESS", "1") != "0"
VISIBLE_PAUSE = 0.0 if HEADLESS else 1.0
SIZE = (100, 40)


class TestRenameTab:
    """Test tab renaming. Zellij: Ctrl+t → r."""

    async def test_rename_active_tab(self):
        """Should be able to rename the active tab."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            tab_list = app.query_one("#tab-list", TabList)
            assert tab_list.tab_items[0].tab_name == "Tab 1"

            result = app.rename_active_tab("My Project")
            assert result is True

            await pilot.pause(VISIBLE_PAUSE)

            assert tab_list.tab_items[0].tab_name == "My Project"
            assert "My Project" in str(tab_list.tab_items[0].label)

    async def test_rename_different_tabs(self):
        """Should be able to rename different tabs independently."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            tab_list = app.query_one("#tab-list", TabList)

            # Rename tab 0
            app.rename_active_tab("Alpha")
            assert tab_list.tab_items[0].tab_name == "Alpha"

            # Switch to tab 1 and rename
            await pilot.click("#tab-1")
            await pilot.pause()
            app.rename_active_tab("Bravo")
            assert tab_list.tab_items[1].tab_name == "Bravo"

            # Switch to tab 2 and rename
            await pilot.click("#tab-2")
            await pilot.pause()
            app.rename_active_tab("Charlie")
            assert tab_list.tab_items[2].tab_name == "Charlie"

            await pilot.pause(VISIBLE_PAUSE)

            # Verify all names are preserved
            assert tab_list.tab_items[0].tab_name == "Alpha"
            assert tab_list.tab_items[1].tab_name == "Bravo"
            assert tab_list.tab_items[2].tab_name == "Charlie"

    async def test_renamed_tab_shows_in_sidebar(self):
        """The renamed tab should update its label in the sidebar."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            tab_list = app.query_one("#tab-list", TabList)
            app.rename_active_tab("Editor")

            await pilot.pause(VISIBLE_PAUSE)

            label_str = str(tab_list.tab_items[0].label)
            assert "Editor" in label_str

    async def test_rename_preserves_active_state(self):
        """Renaming should not change the active/inactive state."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            tab_list = app.query_one("#tab-list", TabList)
            assert tab_list.tab_items[0].is_active is True

            app.rename_active_tab("Renamed")

            assert tab_list.tab_items[0].is_active is True
            assert tab_list.tab_items[0].tab_name == "Renamed"


class TestRenamePane:
    """Test pane renaming. Zellij: Ctrl+p → c."""

    async def test_rename_focused_pane(self):
        """Should be able to rename the focused pane."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)
            pane = pc.get_pane(pc.focused_pane_id)
            assert pane is not None

            result = app.rename_focused_pane("Main Editor")
            assert result is True

            await pilot.pause(VISIBLE_PAUSE)

            assert pane.pane_name == "Main Editor"
            rendered = pane.render()
            assert "Main Editor" in rendered

    async def test_rename_multiple_panes(self):
        """Should be able to rename different panes independently."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)
            first_id = pc.focused_pane_id

            # Rename first pane
            pc.rename_pane(first_id, "Left Panel")

            # Split
            await pilot.press("v")
            await pilot.pause()

            second_id = pc.focused_pane_id

            # Rename second pane
            pc.rename_pane(second_id, "Right Panel")

            await pilot.pause(VISIBLE_PAUSE)

            first_pane = pc.get_pane(first_id)
            second_pane = pc.get_pane(second_id)
            assert first_pane is not None
            assert second_pane is not None
            assert first_pane.pane_name == "Left Panel"
            assert second_pane.pane_name == "Right Panel"

    async def test_rename_pane_survives_sibling_operations(self):
        """A renamed pane should keep its name after sibling operations."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)
            first_id = pc.focused_pane_id

            # Rename
            pc.rename_pane(first_id, "Persistent Name")

            # Split (triggers rebuild)
            await pilot.press("v")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            # First pane should still have its name
            first_pane = pc.get_pane(first_id)
            assert first_pane is not None
            assert first_pane.pane_name == "Persistent Name"

    async def test_rename_pane_survives_tab_switch(self):
        """A renamed pane should keep its name after tab switching."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)
            pane_id = pc.focused_pane_id
            pc.rename_pane(pane_id, "Renamed Pane")

            # Switch away and back
            await pilot.click("#tab-1")
            await pilot.pause()
            await pilot.click("#tab-0")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            restored_pane = pc.get_pane(pane_id)
            assert restored_pane is not None
            assert restored_pane.pane_name == "Renamed Pane"


class TestRenameEdgeCases:
    """Test edge cases for renaming."""

    async def test_rename_invalid_pane(self):
        """Renaming a non-existent pane should return False."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)
            result = pc.rename_pane("pane-nonexistent", "Nope")
            assert result is False

    async def test_rename_tab_empty_string(self):
        """Renaming a tab with empty string should work (edge case)."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            result = app.rename_active_tab("")
            assert result is True

            tab_list = app.query_one("#tab-list", TabList)
            assert tab_list.tab_items[0].tab_name == ""
