"""End-to-end tests for the toggleable left sidebar.

Tests that the sidebar can be hidden/shown with 'b' keybind,
and that panes fill the width when sidebar is hidden.

Run visible:
    ATT_HEADLESS=0 pytest tests/test_sidebar_e2e.py -v -s

Run headless:
    pytest tests/test_sidebar_e2e.py -v
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


class TestSidebarToggle:
    """Test sidebar hide/show functionality."""

    async def test_sidebar_visible_by_default(self):
        """Sidebar should be visible on startup."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            sidebar = app.query_one("#sidebar")
            assert sidebar.display is True
            assert app.sidebar_visible is True

    async def test_toggle_hides_sidebar(self):
        """Pressing 'b' should hide the sidebar."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            await pilot.press("b")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            sidebar = app.query_one("#sidebar")
            assert sidebar.display is False
            assert app.sidebar_visible is False

    async def test_toggle_restores_sidebar(self):
        """Pressing 'b' twice should hide then show the sidebar."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            # Hide
            await pilot.press("b")
            await pilot.pause()
            assert app.sidebar_visible is False

            # Show
            await pilot.press("b")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            sidebar = app.query_one("#sidebar")
            assert sidebar.display is True
            assert app.sidebar_visible is True

    async def test_sidebar_elements_hidden(self):
        """When sidebar is hidden, its children should be invisible."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            # Hide sidebar
            await pilot.press("b")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            sidebar = app.query_one("#sidebar")
            assert sidebar.display is False

            # Pane container should still be visible
            pc = app.query_one("#pane-container", PaneContainer)
            assert pc.display is True


class TestSidebarWithPanes:
    """Test sidebar toggle interaction with pane operations."""

    async def test_pane_operations_work_with_sidebar_hidden(self):
        """Pane splits and closes should work even when sidebar is hidden."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)

            # Hide sidebar
            await pilot.press("b")
            await pilot.pause()
            assert app.sidebar_visible is False

            # Split should still work
            await pilot.press("v")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)
            assert pc.pane_count == 2

            # Close should still work
            await pilot.press("x")
            await pilot.pause()
            assert pc.pane_count == 1

    async def test_tab_switching_works_after_sidebar_restore(self):
        """After hiding and showing sidebar, tabs should still work."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            # Hide
            await pilot.press("b")
            await pilot.pause()

            # Show
            await pilot.press("b")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            # Tab clicks should still work
            await pilot.click("#tab-1")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)
            assert app.active_tab == 1

    async def test_number_keys_work_with_sidebar_hidden(self):
        """Number key tab switching should work even with sidebar hidden."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            # Hide sidebar
            await pilot.press("b")
            await pilot.pause()

            # Number keys should still switch tabs
            await pilot.press("2")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)
            assert app.active_tab == 1

            await pilot.press("1")
            await pilot.pause()
            assert app.active_tab == 0

    async def test_rapid_toggles(self):
        """Rapidly toggling sidebar should not break the layout."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            for _ in range(6):
                await pilot.press("b")
                await pilot.pause()

            # After 6 toggles (even number), sidebar should be visible
            assert app.sidebar_visible is True

            sidebar = app.query_one("#sidebar")
            assert sidebar.display is True

            # Panes should still work
            pc = app.query_one("#pane-container", PaneContainer)
            assert pc.pane_count == 1
