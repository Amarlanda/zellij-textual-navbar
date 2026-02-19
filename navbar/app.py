"""Zellij Navbar — Textual TUI application.

A vertical sidebar navbar for Zellij terminal multiplexer, built with
Textual. Provides tab management, session controls, and a live clock.

Run directly:
    python -m navbar.app
    textual run --dev navbar/app.py

E2E tests use Textual's Pilot (Playwright-style):
    pytest tests/ -v
"""

from __future__ import annotations

from datetime import datetime

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.timer import Timer
from textual.widgets import Button, Label, Static

from navbar.widgets import (
    NavHeader,
    TabButton,
    TabList,
    SessionInfo,
    ClockWidget,
    ActivityBar,
)


class NavbarApp(App):
    """Zellij sidebar navbar application.

    A vertical TUI sidebar with tab management, session info,
    and interactive controls. Designed for E2E testing with
    Textual's Pilot API.
    """

    CSS_PATH = "navbar.tcss"

    TITLE = "Navbar"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("n", "new_tab", "New Tab"),
        Binding("r", "rename_tab", "Rename"),
        Binding("d", "toggle_debug", "Debug"),
    ]

    tab_count: reactive[int] = reactive(3)
    active_tab: reactive[int] = reactive(0)
    session_name: reactive[str] = reactive("main")
    debug_mode: reactive[bool] = reactive(False)
    clock_time: reactive[str] = reactive("")

    def compose(self) -> ComposeResult:
        yield NavHeader(id="nav-header")
        yield Horizontal(
            Label("Session: ", classes="label-dim"),
            SessionInfo(id="session-info"),
            id="session-bar",
        )
        yield TabList(id="tab-list")
        yield ActivityBar(id="activity-bar")
        yield Horizontal(
            ClockWidget(id="clock"),
            Button("＋", id="btn-new-tab", classes="action-btn"),
            Button("D", id="btn-debug", classes="action-btn"),
            id="bottom-bar",
        )

    def on_mount(self) -> None:
        """Initialize the app state after mounting."""
        self._clock_timer: Timer = self.set_interval(1.0, self._update_clock)
        self._update_clock()
        self._build_tabs()

    def _update_clock(self) -> None:
        """Update the clock display."""
        self.clock_time = datetime.now().strftime("%H:%M:%S")
        clock = self.query_one("#clock", ClockWidget)
        clock.update_time(self.clock_time)

    def _build_tabs(self) -> None:
        """Build the initial tab list."""
        tab_list = self.query_one("#tab-list", TabList)
        tab_list.clear_tabs()
        for i in range(self.tab_count):
            tab_list.add_tab(
                name=f"Tab {i + 1}",
                is_active=(i == self.active_tab),
                pane_count=max(1, (i % 3) + 1),
            )

    def watch_active_tab(self, old: int, new: int) -> None:
        """React to active tab changes."""
        tab_list = self.query_one("#tab-list", TabList)
        tab_list.set_active(new)
        activity = self.query_one("#activity-bar", ActivityBar)
        activity.update_activity(f"Tab {new + 1}", "bash")

    def action_new_tab(self) -> None:
        """Add a new tab."""
        self.tab_count += 1
        tab_list = self.query_one("#tab-list", TabList)
        tab_list.add_tab(
            name=f"Tab {self.tab_count}",
            is_active=False,
            pane_count=1,
        )

    def action_rename_tab(self) -> None:
        """Rename the active tab (placeholder)."""
        pass

    def action_toggle_debug(self) -> None:
        """Toggle debug mode."""
        self.debug_mode = not self.debug_mode
        activity = self.query_one("#activity-bar", ActivityBar)
        if self.debug_mode:
            activity.show_debug("Debug mode enabled")
        else:
            activity.update_activity(f"Tab {self.active_tab + 1}", "bash")

    def on_key(self, event) -> None:
        """Handle number key presses for tab switching."""
        if event.character and event.character.isdigit():
            idx = int(event.character) - 1
            if 0 <= idx < self.tab_count:
                self.active_tab = idx

    def on_tab_list_tab_clicked(self, event: TabList.TabClicked) -> None:
        """Handle tab clicks (bubbled up from TabList)."""
        self.active_tab = event.index

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses from non-tab buttons."""
        if event.button.id == "btn-new-tab":
            self.action_new_tab()
        elif event.button.id == "btn-debug":
            self.action_toggle_debug()


def main():
    """Entry point for the navbar app."""
    app = NavbarApp()
    app.run()


if __name__ == "__main__":
    main()
