"""End-to-end tests for the status tab overview.

Tests the status view that shows all tabs and panes in a
dashboard format. Zellij: Ctrl+o → session manager.

Run visible:
    ATT_HEADLESS=0 pytest tests/test_status_e2e.py -v -s

Run headless:
    pytest tests/test_status_e2e.py -v
"""

from __future__ import annotations

import os

import pytest

from navbar.app import NavbarApp
from navbar.panes import PaneContainer
from navbar.status import StatusView
from navbar.widgets import TabList


HEADLESS = os.environ.get("ATT_HEADLESS", "1") != "0"
VISIBLE_PAUSE = 0.0 if HEADLESS else 1.0
SIZE = (100, 40)


class TestStatusToggle:
    """Test status view toggle functionality."""

    async def test_status_hidden_by_default(self):
        """Status view should be hidden on startup."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            status = app.query_one("#status-view", StatusView)
            assert status.display is False
            assert app.status_visible is False

    async def test_s_key_shows_status(self):
        """Pressing 's' should show the status view."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            await pilot.press("s")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            status = app.query_one("#status-view", StatusView)
            assert status.display is True
            assert app.status_visible is True

    async def test_s_key_hides_status(self):
        """Pressing 's' twice should hide the status view."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            # Show
            await pilot.press("s")
            await pilot.pause()
            assert app.status_visible is True

            # Hide
            await pilot.press("s")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            status = app.query_one("#status-view", StatusView)
            assert status.display is False

    async def test_status_hides_panes(self):
        """When status is shown, pane container should be hidden."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            await pilot.press("s")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)
            assert pc.display is False

    async def test_panes_restore_after_status_close(self):
        """Closing status should restore pane container."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            # Show status
            await pilot.press("s")
            await pilot.pause()

            # Hide status
            await pilot.press("s")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)
            assert pc.display is True


class TestStatusContent:
    """Test that the status view displays correct information."""

    async def test_status_shows_tab_names(self):
        """Status should list all tab names."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            # Open status
            await pilot.press("s")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            status = app.query_one("#status-view", StatusView)
            text = status.status_text

            assert "Tab 1" in text
            assert "Tab 2" in text
            assert "Tab 3" in text

    async def test_status_shows_active_tab(self):
        """Status should mark the active tab."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            await pilot.press("s")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            status = app.query_one("#status-view", StatusView)
            text = status.status_text

            assert "(active)" in text
            assert "Status Overview" in text

    async def test_status_shows_pane_count(self):
        """Status should show pane count per tab."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            # Split to get 2 panes in tab 0
            await pilot.press("v")
            await pilot.pause()

            # Open status
            await pilot.press("s")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            status = app.query_one("#status-view", StatusView)
            text = status.status_text

            assert "2 panes" in text

    async def test_status_shows_pane_details_for_active_tab(self):
        """Status should show pane names and commands for active tab."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)

            # Run a command in the pane
            await pc.run_command_in_focused('echo "status-test"')
            await pilot.pause()

            # Open status
            await pilot.press("s")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            status = app.query_one("#status-view", StatusView)
            text = status.status_text

            assert "Pane" in text
            assert "[focused]" in text
            assert "status-test" in text

    async def test_status_shows_renamed_tabs(self):
        """Status should show renamed tab names."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            app.rename_active_tab("My Editor")

            await pilot.press("s")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            status = app.query_one("#status-view", StatusView)
            text = status.status_text

            assert "My Editor" in text

    async def test_status_total_count(self):
        """Status should show total tab count."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            await pilot.press("s")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            status = app.query_one("#status-view", StatusView)
            text = status.status_text

            assert "Total: 3 tabs" in text


class TestStatusInteraction:
    """Test status view interactions with other features."""

    async def test_status_works_with_sidebar_hidden(self):
        """Status should work even when sidebar is hidden."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            # Hide sidebar
            await pilot.press("b")
            await pilot.pause()

            # Show status
            await pilot.press("s")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            status = app.query_one("#status-view", StatusView)
            assert status.display is True
            assert "Tab 1" in status.status_text

    async def test_panes_intact_after_status(self):
        """Pane state should be intact after opening and closing status."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)

            # Split
            await pilot.press("v")
            await pilot.pause()
            assert pc.pane_count == 2

            # Open/close status
            await pilot.press("s")
            await pilot.pause()
            await pilot.press("s")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            # Panes should still be there
            assert pc.pane_count == 2
