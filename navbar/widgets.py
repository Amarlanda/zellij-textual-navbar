"""Custom Textual widgets for the Zellij navbar.

Each widget is a composable Textual Widget that can be queried,
clicked, and asserted on using Textual's Pilot API.
"""

from __future__ import annotations

from textual.containers import VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button, Static


class NavHeader(Static):
    """Top header bar showing NAVBAR title and render info."""

    def render(self) -> str:
        return "▌ NAVBAR ▐"


class SessionInfo(Static):
    """Displays the current session name."""

    session_name: reactive[str] = reactive("main")

    def render(self) -> str:
        return f"⚡ {self.session_name}"

    def set_session(self, name: str) -> None:
        """Update the session name."""
        self.session_name = name


class TabButton(Button):
    """A clickable tab button in the sidebar.

    Extends Button with tab-specific state (active, index, pane count).
    Designed for Pilot testing: `await pilot.click("#tab-0")`
    """

    is_active: reactive[bool] = reactive(False)
    tab_name: reactive[str] = reactive("Tab")
    pane_count: reactive[int] = reactive(1)

    def __init__(
        self,
        index: int,
        name: str = "Tab",
        is_active: bool = False,
        pane_count: int = 1,
        **kwargs,
    ) -> None:
        self.index = index
        label = self._make_label(name, is_active, pane_count)
        super().__init__(
            label,
            id=f"tab-{index}",
            classes="tab-btn active-tab" if is_active else "tab-btn",
            **kwargs,
        )
        self.tab_name = name
        self.is_active = is_active
        self.pane_count = pane_count

    @staticmethod
    def _make_label(name: str, active: bool, panes: int) -> str:
        marker = "▸" if active else " "
        return f"{marker} {name} ({panes})"

    def watch_is_active(self, value: bool) -> None:
        """Update label and styling when active state changes."""
        self.label = self._make_label(self.tab_name, value, self.pane_count)
        self.set_classes("tab-btn active-tab" if value else "tab-btn")

    def rename(self, new_name: str) -> None:
        """Rename this tab. Zellij: Ctrl+t → r."""
        self.tab_name = new_name
        self.label = self._make_label(new_name, self.is_active, self.pane_count)


class TabList(VerticalScroll):
    """Scrollable list of tab buttons in the sidebar.

    Supports adding, removing, and switching active tabs.
    Pilot can interact: `await pilot.click("#tab-0")`
    """

    class TabClicked(Message):
        """Emitted when a tab button is clicked."""

        def __init__(self, index: int) -> None:
            self.index = index
            super().__init__()

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._tabs: list[TabButton] = []

    def clear_tabs(self) -> None:
        """Remove all tab buttons."""
        self._tabs.clear()
        self.remove_children()

    def add_tab(
        self, name: str, is_active: bool = False, pane_count: int = 1
    ) -> TabButton:
        """Add a new tab button to the list."""
        idx = len(self._tabs)
        tab = TabButton(
            index=idx,
            name=name,
            is_active=is_active,
            pane_count=pane_count,
        )
        self._tabs.append(tab)
        self.mount(tab)
        return tab

    def set_active(self, index: int) -> None:
        """Set which tab is active."""
        for i, tab in enumerate(self._tabs):
            tab.is_active = (i == index)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle tab button clicks, emit TabClicked."""
        if isinstance(event.button, TabButton):
            event.stop()
            self.post_message(self.TabClicked(event.button.index))

    def rename_tab(self, index: int, new_name: str) -> bool:
        """Rename a tab by index. Returns True if successful."""
        if 0 <= index < len(self._tabs):
            self._tabs[index].rename(new_name)
            return True
        return False

    @property
    def tab_items(self) -> list[TabButton]:
        """Return all tab buttons."""
        return list(self._tabs)


class ClockWidget(Static):
    """Live clock display updated every second."""

    time_str: reactive[str] = reactive("--:--:--")

    def render(self) -> str:
        return f"🕐 {self.time_str}"

    def update_time(self, time_str: str) -> None:
        """Update the displayed time."""
        self.time_str = time_str


class ActivityBar(Static):
    """Bottom activity bar showing current pane info or debug output."""

    activity_text: reactive[str] = reactive("Ready")
    mode: reactive[str] = reactive("activity")

    def render(self) -> str:
        if self.mode == "debug":
            return f"🔧 DEBUG: {self.activity_text}"
        return f"▶ ACTIVE: {self.activity_text}"

    def update_activity(self, tab_name: str, command: str = "") -> None:
        """Update activity display."""
        self.mode = "activity"
        self.activity_text = f"{tab_name} — {command}" if command else tab_name

    def show_debug(self, message: str) -> None:
        """Switch to debug mode with a message."""
        self.mode = "debug"
        self.activity_text = message
