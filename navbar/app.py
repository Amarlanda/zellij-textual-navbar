"""Zellij Navbar — Textual TUI application.

A vertical sidebar navbar for Zellij terminal multiplexer, built with
Textual. Provides tab management, pane splitting (horizontal/vertical),
session controls, and a live clock.

Zellij keybindings:
    Ctrl+p → pane mode:  d=split-h, v=split-v, h/j/k/l=focus, x=close
    Ctrl+t → tab mode:   n=new, x=close, r=rename, 1-9=jump
    q = quit

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

from navbar.panes import Pane, PaneContainer
from navbar.status import StatusView
from navbar.widgets import (
    NavHeader,
    TabButton,
    TabList,
    SessionInfo,
    ClockWidget,
    ActivityBar,
)


class NavbarApp(App):
    """Zellij sidebar navbar application with split panes.

    Layout: sidebar (left) | pane area (right)
    The sidebar has tabs, session info, clock, and controls.
    The pane area supports vertical/horizontal splits.
    """

    CSS_PATH = "navbar.tcss"

    TITLE = "Navbar"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("n", "new_tab", "New Tab"),
        Binding("r", "rename_tab", "Rename"),
        Binding("d", "split_horizontal", "Split ─"),
        Binding("v", "split_vertical", "Split │"),
        Binding("x", "close_pane", "Close Pane"),
        Binding("t", "toggle_debug", "Debug"),
        Binding("b", "toggle_sidebar", "Toggle Sidebar"),
        Binding("plus_sign", "resize_grow", "Grow Pane"),
        Binding("equals_sign", "resize_grow", "Grow Pane", show=False),
        Binding("minus", "resize_shrink", "Shrink Pane"),
        Binding("s", "toggle_status", "Status"),
    ]

    tab_count: reactive[int] = reactive(3)
    active_tab: reactive[int] = reactive(0)
    session_name: reactive[str] = reactive("main")
    debug_mode: reactive[bool] = reactive(False)
    clock_time: reactive[str] = reactive("")
    sidebar_visible: reactive[bool] = reactive(True)
    status_visible: reactive[bool] = reactive(False)

    def compose(self) -> ComposeResult:
        with Horizontal(id="main-layout"):
            # Left sidebar
            with self.sidebar():
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
            # Right pane area
            yield PaneContainer(id="pane-container")
            # Status overlay (hidden by default)
            yield StatusView(id="status-view")

    @staticmethod
    def sidebar():
        """Create the sidebar container."""
        from textual.containers import Vertical
        return Vertical(id="sidebar")

    def on_mount(self) -> None:
        """Initialize the app state after mounting."""
        self._clock_timer: Timer = self.set_interval(1.0, self._update_clock)
        self._update_clock()
        self._build_tabs()
        # Hide status view on startup
        self.query_one("#status-view").display = False

    def _update_clock(self) -> None:
        """Update the clock display."""
        self.clock_time = datetime.now().strftime("%H:%M:%S")
        clock = self.query_one("#clock", ClockWidget)
        clock.update_time(self.clock_time)

    def _build_tabs(self) -> None:
        """Build the initial tab list.

        Each tab starts with 1 pane. Pane counts update dynamically
        as panes are split/closed.
        """
        tab_list = self.query_one("#tab-list", TabList)
        tab_list.clear_tabs()
        for i in range(self.tab_count):
            tab_list.add_tab(
                name=f"Tab {i + 1}",
                is_active=(i == self.active_tab),
                pane_count=1,
            )

    def watch_active_tab(self, old: int, new: int) -> None:
        """React to active tab changes — switch pane layout too."""
        tab_list = self.query_one("#tab-list", TabList)
        tab_list.set_active(new)
        activity = self.query_one("#activity-bar", ActivityBar)
        activity.update_activity(f"Tab {new + 1}", "bash")

        # Switch the pane container to this tab's pane tree
        pc = self.query_one("#pane-container", PaneContainer)
        self.call_later(pc.switch_tab, new)

    # --- Tab actions ---

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
        """Rename the active tab. Zellij: Ctrl+t → r.

        For programmatic/test use, call rename_active_tab(name) directly.
        """
        pass

    def rename_active_tab(self, new_name: str) -> bool:
        """Rename the currently active tab programmatically."""
        tab_list = self.query_one("#tab-list", TabList)
        return tab_list.rename_tab(self.active_tab, new_name)

    def rename_focused_pane(self, new_name: str) -> bool:
        """Rename the currently focused pane programmatically."""
        pc = self.query_one("#pane-container", PaneContainer)
        return pc.rename_focused_pane(new_name)

    def action_toggle_debug(self) -> None:
        """Toggle debug mode."""
        self.debug_mode = not self.debug_mode
        activity = self.query_one("#activity-bar", ActivityBar)
        if self.debug_mode:
            activity.show_debug("Debug mode enabled")
        else:
            activity.update_activity(f"Tab {self.active_tab + 1}", "bash")

    # --- Sidebar toggle ---

    def action_toggle_sidebar(self) -> None:
        """Toggle sidebar visibility. Zellij: Alt+b (custom)."""
        self.sidebar_visible = not self.sidebar_visible

    def watch_sidebar_visible(self, value: bool) -> None:
        """Show/hide the sidebar."""
        sidebar = self.query_one("#sidebar")
        sidebar.display = value

    # --- Status tab ---

    def action_toggle_status(self) -> None:
        """Toggle status overview. Zellij: Ctrl+o → session manager."""
        self.status_visible = not self.status_visible

    def watch_status_visible(self, value: bool) -> None:
        """Show/hide the status view, hiding/showing panes."""
        status = self.query_one("#status-view", StatusView)
        pc = self.query_one("#pane-container", PaneContainer)

        if value:
            # Refresh status data and show
            tab_list = self.query_one("#tab-list", TabList)
            status.refresh_status(tab_list, pc, self.active_tab)
            status.display = True
            pc.display = False
        else:
            status.display = False
            pc.display = True

    # --- Pane actions (Zellij pane mode) ---

    async def action_split_horizontal(self) -> None:
        """Split focused pane horizontally (new pane below). Zellij: Ctrl+p → d"""
        pc = self.query_one("#pane-container", PaneContainer)
        new_id = await pc.split_horizontal()
        if new_id:
            self._update_pane_counts()

    async def action_split_vertical(self) -> None:
        """Split focused pane vertically (new pane right). Zellij: Ctrl+p → r/v"""
        pc = self.query_one("#pane-container", PaneContainer)
        new_id = await pc.split_vertical()
        if new_id:
            self._update_pane_counts()

    async def action_close_pane(self) -> None:
        """Close the focused pane. Zellij: Ctrl+p → x"""
        pc = self.query_one("#pane-container", PaneContainer)
        closed = await pc.close_pane()
        if closed:
            self._update_pane_counts()

    async def action_resize_grow(self) -> None:
        """Grow the focused pane. Zellij: Ctrl+n → +/="""
        pc = self.query_one("#pane-container", PaneContainer)
        await pc.resize_focused(grow=True)

    async def action_resize_shrink(self) -> None:
        """Shrink the focused pane. Zellij: Ctrl+n → -"""
        pc = self.query_one("#pane-container", PaneContainer)
        await pc.resize_focused(grow=False)

    async def action_focus_left(self) -> None:
        """Move focus left. Zellij: Ctrl+p → h / Alt+h"""
        pc = self.query_one("#pane-container", PaneContainer)
        await pc.focus_direction("left")

    async def action_focus_right(self) -> None:
        """Move focus right. Zellij: Ctrl+p → l / Alt+l"""
        pc = self.query_one("#pane-container", PaneContainer)
        await pc.focus_direction("right")

    async def action_focus_up(self) -> None:
        """Move focus up. Zellij: Ctrl+p → k / Alt+k"""
        pc = self.query_one("#pane-container", PaneContainer)
        await pc.focus_direction("up")

    async def action_focus_down(self) -> None:
        """Move focus down. Zellij: Ctrl+p → j / Alt+j"""
        pc = self.query_one("#pane-container", PaneContainer)
        await pc.focus_direction("down")

    def _update_pane_counts(self) -> None:
        """Update the active tab's pane count display."""
        pc = self.query_one("#pane-container", PaneContainer)
        tab_list = self.query_one("#tab-list", TabList)
        tabs = tab_list.tab_items
        if 0 <= self.active_tab < len(tabs):
            tabs[self.active_tab].pane_count = pc.pane_count

    # --- Event handlers ---

    def on_key(self, event) -> None:
        """Handle number key presses for tab switching and arrow focus."""
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

    def on_pane_container_focus_changed(
        self, event: PaneContainer.FocusChanged
    ) -> None:
        """Update activity bar when pane focus changes."""
        activity = self.query_one("#activity-bar", ActivityBar)
        activity.update_activity(
            f"Tab {self.active_tab + 1}", event.pane_name
        )

    def on_pane_container_pane_count_changed(
        self, event: PaneContainer.PaneCountChanged
    ) -> None:
        """Update tab's pane count when panes are added/removed."""
        self._update_pane_counts()


def main():
    """Entry point for the navbar app."""
    app = NavbarApp()
    app.run()


if __name__ == "__main__":
    main()
