"""Zellij Navbar — Textual TUI application with modal keybindings.

A vertical sidebar navbar for Zellij terminal multiplexer, built with
Textual. Provides tab management, pane splitting (horizontal/vertical),
session controls, and a live clock.

Modal keybindings (like Zellij):
    NORMAL mode (green):  Ctrl+p → Pane, Ctrl+t → Tab, Ctrl+n → Resize, Ctrl+o → Session
    PANE mode (yellow):   d=split-h, v=split-v, x=close, h/j/k/l=focus, Esc→Normal
    TAB mode (blue):      n=new, r=rename, x=close, 1-9=jump, Esc→Normal
    RESIZE mode (magenta): +/-/= grow/shrink, h/j/k/l directional, Esc→Normal
    SESSION mode (cyan):  s=status overview, Esc→Normal

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
from textual.containers import Horizontal, Vertical
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
    ModeBar,
)


# ---------------------------------------------------------------------------
# Mode definitions — mirrors Zellij's modal system
# ---------------------------------------------------------------------------

MODES = {
    "normal":  {"label": " NORMAL ",  "color": "#89b482", "keys": "p=Pane  t=Tab  n=Resize  o=Session  q=Quit  b=Sidebar"},
    "pane":    {"label": " PANE ",    "color": "#d8a657", "keys": "d=Split↓  v=Split→  x=Close  h/j/k/l=Focus  Esc=Normal"},
    "tab":     {"label": " TAB ",     "color": "#7daea3", "keys": "n=New  r=Rename  1-9=Jump  h/l=Prev/Next  Esc=Normal"},
    "resize":  {"label": " RESIZE ",  "color": "#d3869b", "keys": "+/-=Grow/Shrink  h/j/k/l=Direction  Esc=Normal"},
    "session": {"label": " SESSION ", "color": "#a9b665", "keys": "s=Status  Esc=Normal"},
}


class NavbarApp(App):
    """Zellij sidebar navbar application with modal keybindings.

    Layout: sidebar (left) | pane area (right) | status bar (bottom)
    The sidebar has tabs, session info, clock, and controls.
    The pane area supports vertical/horizontal splits.
    A color-coded status bar at the bottom shows the current mode.
    """

    CSS_PATH = "navbar.tcss"

    TITLE = "Navbar"

    # All keys handled via on_key() modal dispatch — no BINDINGS needed.
    BINDINGS = []

    tab_count: reactive[int] = reactive(3)
    active_tab: reactive[int] = reactive(0)
    session_name: reactive[str] = reactive("main")
    debug_mode: reactive[bool] = reactive(False)
    clock_time: reactive[str] = reactive("")
    sidebar_visible: reactive[bool] = reactive(True)
    status_visible: reactive[bool] = reactive(False)
    current_mode: reactive[str] = reactive("normal")

    def compose(self) -> ComposeResult:
        with Vertical(id="app-root"):
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
            # Bottom mode bar — always visible, full width
            yield ModeBar(id="mode-bar")

    @staticmethod
    def sidebar():
        """Create the sidebar container."""
        return Vertical(id="sidebar")

    def on_mount(self) -> None:
        """Initialize the app state after mounting."""
        self._clock_timer: Timer = self.set_interval(1.0, self._update_clock)
        self._update_clock()
        self._build_tabs()
        # Hide status view on startup
        self.query_one("#status-view").display = False
        # Set initial mode bar
        self._update_mode_bar()

    def _update_clock(self) -> None:
        """Update the clock display."""
        self.clock_time = datetime.now().strftime("%H:%M:%S")
        try:
            clock = self.query_one("#clock", ClockWidget)
            clock.update_time(self.clock_time)
        except Exception:
            pass  # Clock widget may not be in DOM yet or sidebar hidden

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

    # --- Mode system ---

    def _update_mode_bar(self) -> None:
        """Update the mode bar display to match current mode."""
        mode_bar = self.query_one("#mode-bar", ModeBar)
        mode_info = MODES.get(self.current_mode, MODES["normal"])
        mode_bar.set_mode(
            mode_info["label"],
            mode_info["color"],
            mode_info["keys"],
        )

    def watch_current_mode(self, old: str, new: str) -> None:
        """React to mode changes — update the status bar."""
        try:
            self._update_mode_bar()
        except Exception:
            pass  # Ignore during mount

    def _set_mode(self, mode: str) -> None:
        """Switch to a new mode."""
        self.current_mode = mode

    # --- Modal key dispatch ---

    def on_key(self, event) -> None:
        """Handle key presses based on current mode.

        This is the heart of the modal system. Each mode has its own
        key handlers, just like Zellij's modal keybindings.
        """
        mode = self.current_mode
        key = event.key
        char = event.character

        # Escape always returns to normal mode
        if key == "escape" and mode != "normal":
            event.prevent_default()
            self._set_mode("normal")
            return

        if mode == "normal":
            self._handle_normal_key(key, char, event)
        elif mode == "pane":
            self._handle_pane_key(key, char, event)
        elif mode == "tab":
            self._handle_tab_key(key, char, event)
        elif mode == "resize":
            self._handle_resize_key(key, char, event)
        elif mode == "session":
            self._handle_session_key(key, char, event)

    def _handle_normal_key(self, key: str, char: str | None, event) -> None:
        """NORMAL mode keys — mode switching and global shortcuts.

        p = enter Pane mode
        t = enter Tab mode
        n = enter Resize mode
        o = enter Session mode
        q = quit
        b = toggle sidebar
        """
        if char == "q":
            event.prevent_default()
            self.exit()
        elif char == "p":
            event.prevent_default()
            self._set_mode("pane")
        elif char == "t":
            event.prevent_default()
            self._set_mode("tab")
        elif char == "n":
            event.prevent_default()
            self._set_mode("resize")
        elif char == "o":
            event.prevent_default()
            self._set_mode("session")
        elif char == "b":
            event.prevent_default()
            self.action_toggle_sidebar()

    def _handle_pane_key(self, key: str, char: str | None, event) -> None:
        """PANE mode keys. Zellij: Ctrl+p → d/v/x/h/j/k/l/r"""
        event.prevent_default()
        if char == "d":
            self.call_later(self._do_split_horizontal)
            self._set_mode("normal")
        elif char == "v" or char == "l":
            self.call_later(self._do_split_vertical)
            self._set_mode("normal")
        elif char == "x":
            self.call_later(self._do_close_pane)
            self._set_mode("normal")
        elif char == "h":
            self.call_later(self._do_focus_direction, "left")
        elif char == "j":
            self.call_later(self._do_focus_direction, "down")
        elif char == "k":
            self.call_later(self._do_focus_direction, "up")
        elif char == "r":
            # TODO: interactive rename pane
            pass
        elif char == "n":
            self.call_later(self._do_split_vertical)
            self._set_mode("normal")

    def _handle_tab_key(self, key: str, char: str | None, event) -> None:
        """TAB mode keys. Zellij: Ctrl+t → n/r/x/1-9/h/l"""
        event.prevent_default()
        if char == "n":
            self.action_new_tab()
            self._set_mode("normal")
        elif char == "r":
            # TODO: interactive rename tab
            pass
        elif char == "x":
            # TODO: close tab
            self._set_mode("normal")
        elif char and char.isdigit():
            idx = int(char) - 1
            if 0 <= idx < self.tab_count:
                self.active_tab = idx
            self._set_mode("normal")
        elif char == "h":
            # Previous tab
            if self.active_tab > 0:
                self.active_tab = self.active_tab - 1
        elif char == "l":
            # Next tab
            if self.active_tab < self.tab_count - 1:
                self.active_tab = self.active_tab + 1

    def _handle_resize_key(self, key: str, char: str | None, event) -> None:
        """RESIZE mode keys. Zellij: Ctrl+n → +/-/=/h/j/k/l"""
        event.prevent_default()
        if char in ("+", "="):
            self.call_later(self._do_resize_grow)
        elif char == "-":
            self.call_later(self._do_resize_shrink)
        elif char == "h":
            self.call_later(self._do_resize_shrink)
        elif char == "l":
            self.call_later(self._do_resize_grow)
        elif char == "j":
            self.call_later(self._do_resize_grow)
        elif char == "k":
            self.call_later(self._do_resize_shrink)

    def _handle_session_key(self, key: str, char: str | None, event) -> None:
        """SESSION mode keys. Zellij: Ctrl+o → s/r/w"""
        event.prevent_default()
        if char == "s":
            self.action_toggle_status()
            self._set_mode("normal")

    # --- Async action wrappers (called via call_later) ---

    async def _do_split_horizontal(self) -> None:
        pc = self.query_one("#pane-container", PaneContainer)
        new_id = await pc.split_horizontal()
        if new_id:
            self._update_pane_counts()

    async def _do_split_vertical(self) -> None:
        pc = self.query_one("#pane-container", PaneContainer)
        new_id = await pc.split_vertical()
        if new_id:
            self._update_pane_counts()

    async def _do_close_pane(self) -> None:
        pc = self.query_one("#pane-container", PaneContainer)
        closed = await pc.close_pane()
        if closed:
            self._update_pane_counts()

    async def _do_focus_direction(self, direction: str) -> None:
        pc = self.query_one("#pane-container", PaneContainer)
        await pc.focus_direction(direction)

    async def _do_resize_grow(self) -> None:
        pc = self.query_one("#pane-container", PaneContainer)
        await pc.resize_focused(grow=True)

    async def _do_resize_shrink(self) -> None:
        pc = self.query_one("#pane-container", PaneContainer)
        await pc.resize_focused(grow=False)

    # --- Tab actions ---

    def watch_active_tab(self, old: int, new: int) -> None:
        """React to active tab changes — switch pane layout too."""
        tab_list = self.query_one("#tab-list", TabList)
        tab_list.set_active(new)
        activity = self.query_one("#activity-bar", ActivityBar)
        activity.update_activity(f"Tab {new + 1}", "bash")

        # Switch the pane container to this tab's pane tree
        pc = self.query_one("#pane-container", PaneContainer)
        self.call_later(pc.switch_tab, new)

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

    # --- Pane actions (programmatic API) ---

    async def action_split_horizontal(self) -> None:
        """Split focused pane horizontally (new pane below). Zellij: Ctrl+p → d"""
        await self._do_split_horizontal()

    async def action_split_vertical(self) -> None:
        """Split focused pane vertically (new pane right). Zellij: Ctrl+p → v"""
        await self._do_split_vertical()

    async def action_close_pane(self) -> None:
        """Close the focused pane. Zellij: Ctrl+p → x"""
        await self._do_close_pane()

    async def action_resize_grow(self) -> None:
        """Grow the focused pane. Zellij: Ctrl+n → +/="""
        await self._do_resize_grow()

    async def action_resize_shrink(self) -> None:
        """Shrink the focused pane. Zellij: Ctrl+n → -"""
        await self._do_resize_shrink()

    def _update_pane_counts(self) -> None:
        """Update the active tab's pane count display."""
        pc = self.query_one("#pane-container", PaneContainer)
        tab_list = self.query_one("#tab-list", TabList)
        tabs = tab_list.tab_items
        if 0 <= self.active_tab < len(tabs):
            tabs[self.active_tab].pane_count = pc.pane_count

    # --- Event handlers ---

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
