"""End-to-end tests for pane resize functionality.

Tests growing and shrinking panes using +/- keybinds.
Zellij: Ctrl+n → resize mode.

Run visible:
    ATT_HEADLESS=0 pytest tests/test_resize_e2e.py -v -s

Run headless:
    pytest tests/test_resize_e2e.py -v
"""

from __future__ import annotations

import os

import pytest

from navbar.app import NavbarApp
from navbar.panes import PaneContainer


HEADLESS = os.environ.get("ATT_HEADLESS", "1") != "0"
VISIBLE_PAUSE = 0.0 if HEADLESS else 1.0
SIZE = (100, 40)


class TestPaneResize:
    """Test pane grow/shrink functionality."""

    async def test_cannot_resize_single_pane(self):
        """A single pane should not be resizable (no siblings)."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)
            initial_weight = pc.get_focused_weight()

            result = await pc.resize_focused(grow=True)
            assert result is False
            assert pc.get_focused_weight() == initial_weight

    async def test_grow_focused_pane(self):
        """Growing the focused pane should increase its weight."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)

            # Split to get two panes
            await pilot.press("v")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            initial_weight = pc.get_focused_weight()

            result = await pc.resize_focused(grow=True)
            await pilot.pause(VISIBLE_PAUSE)

            assert result is True
            assert pc.get_focused_weight() > initial_weight

    async def test_shrink_focused_pane(self):
        """Shrinking the focused pane should decrease its weight."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)

            # Split to get two panes
            await pilot.press("v")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            initial_weight = pc.get_focused_weight()

            result = await pc.resize_focused(grow=False)
            await pilot.pause(VISIBLE_PAUSE)

            assert result is True
            assert pc.get_focused_weight() < initial_weight

    async def test_grow_multiple_times(self):
        """Growing multiple times should keep increasing weight."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)

            await pilot.press("v")
            await pilot.pause()

            w1 = pc.get_focused_weight()
            await pc.resize_focused(grow=True)
            w2 = pc.get_focused_weight()
            await pc.resize_focused(grow=True)
            w3 = pc.get_focused_weight()

            await pilot.pause(VISIBLE_PAUSE)

            assert w1 < w2 < w3

    async def test_shrink_stops_at_minimum(self):
        """Shrinking should stop at the minimum weight."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)

            await pilot.press("v")
            await pilot.pause()

            # Shrink many times — should eventually stop
            results = []
            for _ in range(10):
                results.append(await pc.resize_focused(grow=False))

            # At least one should succeed
            assert any(results)
            # Eventually should fail (minimum reached)
            assert not all(results)
            # Weight should never go below minimum
            assert pc.get_focused_weight() >= pc.MIN_WEIGHT

    async def test_grow_stops_when_sibling_at_minimum(self):
        """Growing should stop when the sibling hits minimum weight."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)

            await pilot.press("v")
            await pilot.pause()

            # Grow many times
            results = []
            for _ in range(10):
                results.append(await pc.resize_focused(grow=True))

            # At least one should succeed
            assert any(results)
            # Eventually should fail (sibling at minimum)
            assert not all(results)


class TestResizeWithKeyboard:
    """Test resize via keyboard shortcuts."""

    async def test_plus_key_grows(self):
        """Pressing '+' should grow the focused pane."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)

            await pilot.press("v")
            await pilot.pause()

            initial = pc.get_focused_weight()

            await pilot.press("=")  # = is also grow (shift+= is +)
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            assert pc.get_focused_weight() > initial

    async def test_minus_key_shrinks(self):
        """Pressing '-' should shrink the focused pane."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)

            await pilot.press("v")
            await pilot.pause()

            initial = pc.get_focused_weight()

            await pilot.press("minus")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            assert pc.get_focused_weight() < initial


class TestResizePersistence:
    """Test that resize state persists."""

    async def test_resize_survives_tab_switch(self):
        """Pane resize should persist across tab switches."""
        app = NavbarApp()
        async with app.run_test(headless=HEADLESS, size=SIZE) as pilot:
            await pilot.pause(VISIBLE_PAUSE)

            pc = app.query_one("#pane-container", PaneContainer)

            # Split and resize in tab 0
            await pilot.press("v")
            await pilot.pause()

            await pc.resize_focused(grow=True)
            await pc.resize_focused(grow=True)
            resized_weight = pc.get_focused_weight()
            resized_pane_id = pc.focused_pane_id

            # Switch to tab 1
            await pilot.click("#tab-1")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            # Switch back to tab 0
            await pilot.click("#tab-0")
            await pilot.pause()
            await pilot.pause(VISIBLE_PAUSE)

            # Weight should be preserved
            assert pc.get_focused_weight() == pytest.approx(resized_weight, abs=0.01)
