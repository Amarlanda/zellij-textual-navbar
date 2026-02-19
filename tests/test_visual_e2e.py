"""Focused visual E2E tests for the Zellij Textual Navbar.

~10 high-level tests covering the complete modal workflow.
Designed for visible mode — watch via VNC on M1.

Run visible:
    ATT_HEADLESS=0 pytest tests/test_visual_e2e.py -v -s

Run headless:
    pytest tests/test_visual_e2e.py -v
"""

from __future__ import annotations

import os

import pytest

from navbar.app import NavbarApp
from navbar.panes import PaneContainer
from navbar.widgets import TabList, ModeBar


HEADLESS = os.environ.get("ATT_HEADLESS", "1") != "0"
VISIBLE_PAUSE = 0.0 if HEADLESS else 1.5
SIZE = (120, 40)


class TestModeTransitions:
    """Test the modal keybinding system and status bar color changes."""

    async def test_starts_in_normal_mode(self):
        """App should start in NORMAL mode with green status bar."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            assert app.current_mode == "normal"
            mb = app.query_one("#mode-bar", ModeBar)
            assert "NORMAL" in mb.mode_label

    async def test_mode_cycle_all_modes(self):
        """Cycle through all modes: Normal → Pane → Tab → Resize → Session → Normal.

        The status bar should change color for each mode.
        """
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)
            mb = app.query_one("#mode-bar", ModeBar)

            # Normal → Pane (p)
            await pilot.press("p")
            await pilot.pause(VISIBLE_PAUSE)
            assert app.current_mode == "pane"
            assert "PANE" in mb.mode_label

            # Pane → Normal (escape)
            await pilot.press("escape")
            await pilot.pause(VISIBLE_PAUSE)
            assert app.current_mode == "normal"

            # Normal → Insert (i)
            await pilot.press("i")
            await pilot.pause(VISIBLE_PAUSE)
            assert app.current_mode == "insert"
            assert "INSERT" in mb.mode_label

            # Insert → Normal (escape) — status bar should change back to green
            await pilot.press("escape")
            await pilot.pause(VISIBLE_PAUSE)
            assert app.current_mode == "normal"
            assert "NORMAL" in mb.mode_label

            # Normal → Tab (t)
            await pilot.press("t")
            await pilot.pause(VISIBLE_PAUSE)
            assert app.current_mode == "tab"
            assert "TAB" in mb.mode_label

            # Tab → Normal (escape)
            await pilot.press("escape")
            await pilot.pause(VISIBLE_PAUSE)
            assert app.current_mode == "normal"
            assert "NORMAL" in mb.mode_label

            # Normal → Resize (n)
            await pilot.press("n")
            await pilot.pause(VISIBLE_PAUSE)
            assert app.current_mode == "resize"
            assert "RESIZE" in mb.mode_label

            # Resize → Normal (escape)
            await pilot.press("escape")
            await pilot.pause(VISIBLE_PAUSE)
            assert app.current_mode == "normal"
            assert "NORMAL" in mb.mode_label

            # Normal → Session (o)
            await pilot.press("o")
            await pilot.pause(VISIBLE_PAUSE)
            assert app.current_mode == "session"
            assert "SESSION" in mb.mode_label

            # Session → Normal (escape)
            await pilot.press("escape")
            await pilot.pause(VISIBLE_PAUSE)
            assert app.current_mode == "normal"
            assert "NORMAL" in mb.mode_label


class TestFullWorkflow:
    """Test the complete user workflow from the user's example:
    toggle navbar → enter tab mode → create new tab → enter pane mode →
    create new pane → type a command.
    """

    async def test_complete_workflow(self):
        """Full workflow: sidebar toggle, tab creation, pane split, command execution."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)
            tab_list = app.query_one("#tab-list", TabList)
            mb = app.query_one("#mode-bar", ModeBar)

            # 1. Start in normal mode
            assert app.current_mode == "normal"
            assert app.tab_count == 3
            await pilot.pause(VISIBLE_PAUSE)

            # 2. Toggle sidebar off then on (b key in normal mode)
            await pilot.press("b")
            await pilot.pause(VISIBLE_PAUSE)
            assert app.sidebar_visible is False

            await pilot.press("b")
            await pilot.pause(VISIBLE_PAUSE)
            assert app.sidebar_visible is True

            # 3. Enter tab mode → create new tab
            await pilot.press("t")
            await pilot.pause(VISIBLE_PAUSE)
            assert app.current_mode == "tab"
            assert "TAB" in mb.mode_label

            await pilot.press("n")
            await pilot.pause(VISIBLE_PAUSE)
            assert app.tab_count == 4
            assert app.current_mode == "normal"  # Auto-returns to normal

            # 4. Enter pane mode → split vertical
            await pilot.press("p")
            await pilot.pause(VISIBLE_PAUSE)
            assert app.current_mode == "pane"
            assert "PANE" in mb.mode_label

            await pilot.press("v")
            await pilot.pause(VISIBLE_PAUSE)
            await pilot.pause()  # Extra pause for rebuild
            assert pc.pane_count == 2
            assert app.current_mode == "normal"  # Auto-returns

            # 5. Enter insert mode and type a command
            await pilot.press("i")
            await pilot.pause(VISIBLE_PAUSE)
            assert app.current_mode == "insert"
            assert "INSERT" in mb.mode_label

            # Type "echo hello" character by character
            for ch in "echo hello":
                await pilot.press(ch)
            await pilot.pause(VISIBLE_PAUSE)

            pane = pc.get_pane(pc.focused_pane_id)
            assert pane is not None
            assert pane.command == "echo hello"

            # Press Enter to execute
            await pilot.press("enter")
            await pilot.pause()
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)
            assert app.current_mode == "normal"
            assert "hello" in pane.command_output

            # 6. Split again and type another command via insert mode
            await pilot.press("p")
            await pilot.pause()
            await pilot.press("d")
            await pilot.pause(VISIBLE_PAUSE)
            await pilot.pause()
            assert pc.pane_count == 3

            await pilot.press("i")
            await pilot.pause()
            for ch in "date":
                await pilot.press(ch)
            await pilot.press("enter")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

    async def test_tab_mode_jump_and_navigate(self):
        """Tab mode: jump to tabs with 1-9, navigate with h/l."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            # Jump to tab 3 via tab mode
            await pilot.press("t")
            await pilot.pause(VISIBLE_PAUSE)
            await pilot.press("3")
            await pilot.pause(VISIBLE_PAUSE)
            assert app.active_tab == 2
            assert app.current_mode == "normal"

            # Enter tab mode, navigate with h/l
            await pilot.press("t")
            await pilot.pause(VISIBLE_PAUSE)
            await pilot.press("h")  # Previous tab
            await pilot.pause(VISIBLE_PAUSE)
            assert app.active_tab == 1

            await pilot.press("l")  # Next tab
            await pilot.pause(VISIBLE_PAUSE)
            assert app.active_tab == 2

            await pilot.press("escape")
            await pilot.pause(VISIBLE_PAUSE)
            assert app.current_mode == "normal"


class TestPaneOperations:
    """Test pane operations via the modal system."""

    async def test_pane_split_and_focus_navigation(self):
        """Split panes and navigate between them using h/j/k/l in pane mode."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)
            first_id = pc.focused_pane_id

            # Split vertical: p → v
            await pilot.press("p")
            await pilot.pause()
            await pilot.press("v")
            await pilot.pause(VISIBLE_PAUSE)
            await pilot.pause()
            assert pc.pane_count == 2
            second_id = pc.focused_pane_id
            assert second_id != first_id

            # Navigate back to first pane: p → h
            await pilot.press("p")
            await pilot.pause()
            await pilot.press("h")
            await pilot.pause(VISIBLE_PAUSE)
            assert pc.focused_pane_id == first_id

            # Navigate forward: p → l
            await pilot.press("p")
            await pilot.pause()
            await pilot.press("j")
            await pilot.pause(VISIBLE_PAUSE)
            assert pc.focused_pane_id == second_id

            # Close pane: p → x
            await pilot.press("p")
            await pilot.pause()
            await pilot.press("x")
            await pilot.pause(VISIBLE_PAUSE)
            await pilot.pause()
            assert pc.pane_count == 1

    async def test_pane_resize_mode(self):
        """Resize panes using the resize mode."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)

            # First split to get two panes
            await pilot.press("p")
            await pilot.pause()
            await pilot.press("v")
            await pilot.pause(VISIBLE_PAUSE)
            await pilot.pause()
            assert pc.pane_count == 2

            initial_weight = pc.get_focused_weight()

            # Enter resize mode and grow
            await pilot.press("n")
            await pilot.pause(VISIBLE_PAUSE)
            assert app.current_mode == "resize"

            await pilot.press("+")
            await pilot.pause(VISIBLE_PAUSE)
            assert pc.get_focused_weight() > initial_weight

            # Shrink
            await pilot.press("-")
            await pilot.pause(VISIBLE_PAUSE)

            # Escape back to normal
            await pilot.press("escape")
            await pilot.pause(VISIBLE_PAUSE)
            assert app.current_mode == "normal"


class TestSessionAndStatus:
    """Test session mode and status overview."""

    async def test_session_mode_status_toggle(self):
        """Enter session mode, toggle status overview."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            # Enter session mode → s to toggle status
            await pilot.press("o")
            await pilot.pause(VISIBLE_PAUSE)
            assert app.current_mode == "session"

            await pilot.press("s")
            await pilot.pause(VISIBLE_PAUSE)
            assert app.status_visible is True
            assert app.current_mode == "normal"

            # Status should show tab info
            from navbar.status import StatusView
            status = app.query_one("#status-view", StatusView)
            text = status.status_text
            assert "Tab 1" in text
            assert "Status Overview" in text

            # Toggle status off via session mode again
            await pilot.press("o")
            await pilot.pause()
            await pilot.press("s")
            await pilot.pause(VISIBLE_PAUSE)
            assert app.status_visible is False


class TestSidebarAndClicks:
    """Test sidebar interactions and mouse clicks."""

    async def test_sidebar_toggle_and_tab_clicks(self):
        """Toggle sidebar, click tabs, verify interactions."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            # Click tab 2
            await pilot.click("#tab-1")
            await pilot.pause(VISIBLE_PAUSE)
            assert app.active_tab == 1

            # Click tab 3
            await pilot.click("#tab-2")
            await pilot.pause(VISIBLE_PAUSE)
            assert app.active_tab == 2

            # Toggle sidebar off
            await pilot.press("b")
            await pilot.pause(VISIBLE_PAUSE)
            assert app.sidebar_visible is False

            # Sidebar off — still can enter modes
            await pilot.press("p")
            await pilot.pause()
            await pilot.press("v")
            await pilot.pause(VISIBLE_PAUSE)
            await pilot.pause()

            pc = app.query_one("#pane-container", PaneContainer)
            assert pc.pane_count == 2

            # Bring sidebar back
            await pilot.press("b")
            await pilot.pause(VISIBLE_PAUSE)
            assert app.sidebar_visible is True

    async def test_rename_tab_and_pane(self):
        """Rename tabs and panes programmatically (used by tests)."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            tab_list = app.query_one("#tab-list", TabList)

            # Rename active tab
            result = app.rename_active_tab("My Editor")
            assert result is True
            assert tab_list.tab_items[0].tab_name == "My Editor"
            await pilot.pause(VISIBLE_PAUSE)

            # Rename focused pane
            pc = app.query_one("#pane-container", PaneContainer)
            result = app.rename_focused_pane("Main Terminal")
            assert result is True
            pane = pc.get_pane(pc.focused_pane_id)
            assert pane is not None
            assert pane.pane_name == "Main Terminal"
            await pilot.pause(VISIBLE_PAUSE)
