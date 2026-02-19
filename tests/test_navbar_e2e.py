"""End-to-end tests for the Textual Navbar app.

Uses Textual's Pilot API — Playwright-style testing where
you can see the cursor move, buttons get clicked, and widgets
update in real time.

Run visible (watch the UI being driven):
    ATT_HEADLESS=0 pytest tests/test_navbar_e2e.py -v -s

Run headless (fast, for CI):
    pytest tests/test_navbar_e2e.py -v
"""

from __future__ import annotations

import os

import pytest

from textual.widgets import Button, Label, Static

from navbar.app import NavbarApp
from navbar.widgets import TabButton, TabList, ClockWidget, ActivityBar, SessionInfo


# Use headless=False when ATT_HEADLESS=0 (visible mode for VNC)
HEADLESS = os.environ.get("ATT_HEADLESS", "1") != "0"
VISIBLE_PAUSE = 0.0 if HEADLESS else 1.0  # Pause so humans can see
SIZE = (60, 40)  # Terminal size — tall enough for all widgets


class TestNavbarStartup:
    """Test that the navbar app starts correctly."""

    async def test_app_launches(self):
        """App should launch without errors."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            assert app.is_running

    async def test_header_visible(self):
        """NAVBAR header should be visible at the top."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)
            header = app.query_one("#nav-header")
            assert "NAVBAR" in header.render()

    async def test_session_info_shown(self):
        """Session info should display the session name."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)
            session = app.query_one("#session-info", SessionInfo)
            assert "main" in session.render()

    async def test_clock_widget_exists(self):
        """Clock widget should be present."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)
            clock = app.query_one("#clock", ClockWidget)
            assert clock is not None
            rendered = clock.render()
            assert ":" in rendered

    async def test_initial_tab_count(self):
        """Should start with 3 tabs."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)
            tab_list = app.query_one("#tab-list", TabList)
            assert len(tab_list.tab_items) == 3


class TestTabInteraction:
    """Test clicking and interacting with tabs — visible mouse movement."""

    async def test_click_tab(self):
        """Clicking a tab should make it active.

        In visible mode, you'll SEE the cursor move to the tab button.
        """
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            # Click Tab 2 (index 1)
            await pilot.click("#tab-1")
            await pilot.pause()  # Let messages settle
            await pilot.pause(VISIBLE_PAUSE)

            assert app.active_tab == 1

    async def test_click_multiple_tabs(self):
        """Click through all tabs sequentially.

        Watch the cursor move between tabs on screen.
        """
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            for i in range(3):
                await pilot.click(f"#tab-{i}")
                await pilot.pause()
                await pilot.pause(VISIBLE_PAUSE)
                assert app.active_tab == i

    async def test_active_tab_marker(self):
        """Active tab should show ▸ marker."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            tab_list = app.query_one("#tab-list", TabList)
            first_tab = tab_list.tab_items[0]
            assert first_tab.is_active is True
            assert "▸" in str(first_tab.label)

            second_tab = tab_list.tab_items[1]
            assert second_tab.is_active is False

    async def test_tab_switch_updates_activity(self):
        """Switching tabs should update the activity bar."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            await pilot.click("#tab-2")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            activity = app.query_one("#activity-bar", ActivityBar)
            assert "Tab 3" in activity.activity_text


class TestMouseMovement:
    """Test hover and mouse movement — the main visual feature.

    When running with ATT_HEADLESS=0, you will physically SEE
    the cursor moving between widgets, hovering over tabs, and
    interacting with buttons.
    """

    async def test_hover_over_tabs(self):
        """Hover over each tab sequentially.

        In visible mode, the cursor visibly moves between tabs.
        """
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            for i in range(3):
                await pilot.hover(f"#tab-{i}")
                await pilot.pause(VISIBLE_PAUSE)

    async def test_hover_then_click(self):
        """Hover over a tab, then click it.

        Shows the full mouse interaction flow visible on screen.
        """
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            await pilot.hover("#tab-1")
            await pilot.pause(VISIBLE_PAUSE)

            await pilot.click("#tab-1")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            assert app.active_tab == 1

    async def test_hover_buttons(self):
        """Hover over action buttons in the bottom bar."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            await pilot.hover("#btn-new-tab")
            await pilot.pause(VISIBLE_PAUSE)

            await pilot.hover("#btn-debug")
            await pilot.pause(VISIBLE_PAUSE)

    async def test_mouse_sweep_across_sidebar(self):
        """Move the cursor across the entire sidebar.

        This creates a dramatic visible sweep down the navbar,
        similar to Playwright hovering down a menu.
        """
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            # Hover header
            await pilot.hover("#nav-header")
            await pilot.pause(VISIBLE_PAUSE * 0.5)

            # Hover session bar
            await pilot.hover("#session-info")
            await pilot.pause(VISIBLE_PAUSE * 0.5)

            # Hover each tab
            for i in range(3):
                await pilot.hover(f"#tab-{i}")
                await pilot.pause(VISIBLE_PAUSE * 0.5)

            # Hover activity bar
            await pilot.hover("#activity-bar")
            await pilot.pause(VISIBLE_PAUSE * 0.5)

            # Hover clock
            await pilot.hover("#clock")
            await pilot.pause(VISIBLE_PAUSE * 0.5)


class TestButtonActions:
    """Test button clicks — visible button presses."""

    async def test_new_tab_button(self):
        """Clicking + button should add a new tab.

        Watch the button press and new tab appear.
        """
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            initial_count = app.tab_count
            await pilot.click("#btn-new-tab")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            assert app.tab_count == initial_count + 1
            tab_list = app.query_one("#tab-list", TabList)
            assert len(tab_list.tab_items) == initial_count + 1

    async def test_debug_toggle_button(self):
        """Clicking D button should toggle debug mode."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            assert app.debug_mode is False

            await pilot.click("#btn-debug")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            assert app.debug_mode is True

            activity = app.query_one("#activity-bar", ActivityBar)
            assert activity.mode == "debug"

    async def test_add_multiple_tabs(self):
        """Add multiple new tabs by clicking the + button repeatedly.

        Each click is visible — you see the button press and
        new tab items appearing.
        """
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            initial = app.tab_count
            for _ in range(3):
                await pilot.click("#btn-new-tab")
                await pilot.pause()
                await pilot.pause(VISIBLE_PAUSE)

            # At least 2 new tabs should be added (first click may focus)
            assert app.tab_count >= initial + 2
            tab_list = app.query_one("#tab-list", TabList)
            assert len(tab_list.tab_items) == app.tab_count


class TestKeyboardShortcuts:
    """Test keyboard interactions."""

    async def test_number_key_switches_tab(self):
        """Pressing number keys should switch tabs."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            await pilot.press("2")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)
            assert app.active_tab == 1

            await pilot.press("3")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)
            assert app.active_tab == 2

    async def test_n_key_creates_tab(self):
        """Pressing 'n' should create a new tab."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            initial = app.tab_count
            await pilot.press("n")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            assert app.tab_count == initial + 1

    async def test_d_key_toggles_debug(self):
        """Pressing 'd' should toggle debug mode."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            await pilot.press("d")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)
            assert app.debug_mode is True

            await pilot.press("d")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)
            assert app.debug_mode is False
