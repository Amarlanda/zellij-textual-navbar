"""Pane system for Zellij-style vertical/horizontal splits.

Implements a binary tree of panes that can be split horizontally or
vertically. Each pane is a Textual widget with a border showing its
name and focus state. Panes can run shell commands and display output.

Zellij keybindings replicated:
    Ctrl+p → pane mode:
        d = split horizontal (new pane below)
        r = split vertical (new pane right)  — NOTE: remapped to v in our app
        n = new pane (auto direction)
        x = close focused pane
        h/j/k/l = move focus left/down/up/right
        f = toggle fullscreen
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static


# ---------------------------------------------------------------------------
# Pane — the leaf widget that holds content
# ---------------------------------------------------------------------------

class Pane(Static):
    """A single pane in the split layout.

    Each pane has a unique ID, a display name, and can be focused.
    The pane renders its name and a command output area.
    """

    pane_name: reactive[str] = reactive("Pane")
    is_focused_pane: reactive[bool] = reactive(False)
    command: reactive[str] = reactive("")
    command_output: reactive[str] = reactive("")

    class Focused(Message):
        """Emitted when a pane gains focus."""
        def __init__(self, pane_id: str) -> None:
            self.pane_id = pane_id
            super().__init__()

    class CloseRequested(Message):
        """Emitted when a pane requests to be closed."""
        def __init__(self, pane_id: str) -> None:
            self.pane_id = pane_id
            super().__init__()

    def __init__(
        self,
        pane_id: str,
        pane_name: str = "Pane",
        command: str = "",
        **kwargs,
    ) -> None:
        super().__init__(id=pane_id, **kwargs)
        self.pane_name = pane_name
        self.command = command
        self.command_output = ""
        self.can_focus = True

    def render(self) -> str:
        focus_marker = "▸" if self.is_focused_pane else " "
        border_char = "━" if self.is_focused_pane else "─"
        header = f"{border_char * 2} {focus_marker} {self.pane_name} {border_char * 2}"

        lines = [header]
        if self.command:
            lines.append(f"$ {self.command}")
        if self.command_output:
            lines.append(self.command_output)
        if not self.command and not self.command_output:
            lines.append("(empty)")

        return "\n".join(lines)

    def on_click(self) -> None:
        """When clicked, emit a Focused message."""
        self.post_message(self.Focused(self.id or ""))

    def watch_is_focused_pane(self, value: bool) -> None:
        """Update styling when focus changes."""
        if value:
            self.add_class("focused-pane")
        else:
            self.remove_class("focused-pane")

    def set_output(self, output: str) -> None:
        """Set the command output text."""
        self.command_output = output

    async def run_command(self, cmd: str) -> None:
        """Run a shell command and display its output.

        The command is run via subprocess. Output is captured
        and displayed in the pane. The command is stored so it
        survives layout rebuilds.
        """
        self.command = cmd
        self.command_output = "running..."
        self.refresh()

        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10.0)
            output = stdout.decode("utf-8", errors="replace").strip() if stdout else ""
            self.command_output = output if output else "(no output)"
        except asyncio.TimeoutError:
            self.command_output = "(timeout)"
        except Exception as e:
            self.command_output = f"(error: {e})"

        self.refresh()


# ---------------------------------------------------------------------------
# PaneNode — tree structure for tracking the split layout
# ---------------------------------------------------------------------------

@dataclass
class PaneNode:
    """Binary tree node representing the pane layout.

    A leaf node holds a pane_id. A split node holds two children
    and a split direction. Each node has a size_weight controlling
    how much space it takes relative to siblings.
    """
    pane_id: Optional[str] = None         # Only for leaf nodes
    split: Optional[str] = None           # "horizontal" or "vertical"
    children: list[PaneNode] = field(default_factory=list)
    parent: Optional[PaneNode] = None
    size_weight: float = 1.0              # Relative size among siblings

    @property
    def is_leaf(self) -> bool:
        return self.pane_id is not None

    def find_leaf(self, pane_id: str) -> Optional[PaneNode]:
        """Find a leaf node by pane_id."""
        if self.is_leaf and self.pane_id == pane_id:
            return self
        for child in self.children:
            result = child.find_leaf(pane_id)
            if result is not None:
                return result
        return None

    def all_pane_ids(self) -> list[str]:
        """Return all leaf pane IDs in order."""
        if self.is_leaf:
            return [self.pane_id] if self.pane_id else []
        result = []
        for child in self.children:
            result.extend(child.all_pane_ids())
        return result

    def depth(self) -> int:
        """Return the depth of the tree."""
        if self.is_leaf:
            return 0
        return 1 + max((c.depth() for c in self.children), default=0)


# ---------------------------------------------------------------------------
# TabState — saved state for a tab's pane layout
# ---------------------------------------------------------------------------

@dataclass
class TabState:
    """Saved state for one tab's pane layout.

    Each tab owns its own pane tree and remembers focus and pane data.
    """
    tree: PaneNode
    focused_pane_id: str
    pane_counter: int
    saved_pane_data: dict = field(default_factory=dict)  # pane_id → (name, cmd, output)


# ---------------------------------------------------------------------------
# PaneContainer — manages the visual layout of panes
# ---------------------------------------------------------------------------

class PaneContainer(Container):
    """Manages a tree of split panes.

    Handles splitting, closing, and focus navigation.
    Uses Textual's Horizontal/Vertical containers to arrange
    panes according to the split tree.

    Messages:
        PaneContainer.PaneCountChanged — emitted when panes are added/removed
        PaneContainer.FocusChanged — emitted when focused pane changes
    """

    class PaneCountChanged(Message):
        """Emitted when the number of panes changes."""
        def __init__(self, count: int) -> None:
            self.count = count
            super().__init__()

    class FocusChanged(Message):
        """Emitted when the focused pane changes."""
        def __init__(self, pane_id: str, pane_name: str) -> None:
            self.pane_id = pane_id
            self.pane_name = pane_name
            super().__init__()

    class TabSwitched(Message):
        """Emitted when the active tab changes in the pane container."""
        def __init__(self, tab_index: int) -> None:
            self.tab_index = tab_index
            super().__init__()

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._pane_counter = 0
        self._tree = PaneNode(pane_id=self._next_pane_id())
        self._focused_pane_id: str = self._tree.pane_id or ""
        self._panes: dict[str, Pane] = {}
        self._pending_commands: dict[str, str] = {}  # pane_id → command to run after rebuild
        # Tab ownership
        self._active_tab: int = 0
        self._tab_states: dict[int, TabState] = {}  # tab_index → TabState

    def _next_pane_id(self) -> str:
        """Generate a unique pane ID."""
        self._pane_counter += 1
        return f"pane-{self._pane_counter}"

    @property
    def pane_count(self) -> int:
        return len(self._tree.all_pane_ids())

    @property
    def focused_pane_id(self) -> str:
        return self._focused_pane_id

    @property
    def all_pane_ids(self) -> list[str]:
        return self._tree.all_pane_ids()

    def compose(self) -> ComposeResult:
        """Build the initial single-pane layout."""
        pane = self._create_pane(self._tree.pane_id or "pane-1", "Pane 1", is_focused=True)
        yield pane

    def _create_pane(
        self, pane_id: str, name: str, command: str = "", is_focused: bool = False
    ) -> Pane:
        """Create a Pane widget and register it."""
        pane = Pane(pane_id=pane_id, pane_name=name, command=command)
        pane.is_focused_pane = is_focused
        self._panes[pane_id] = pane
        return pane

    async def rebuild_layout(self) -> None:
        """Rebuild the entire widget tree from the pane tree.

        Removes all children and reconstructs from self._tree.
        This is the nuclear option but ensures consistency.
        """
        # Save pane state
        saved_state: dict[str, tuple[str, str, str]] = {}
        for pid, pane in self._panes.items():
            saved_state[pid] = (pane.pane_name, pane.command, pane.command_output)

        # Clear existing widgets
        await self.remove_children()
        self._panes.clear()

        # Build new widget tree
        widget = self._build_widget(self._tree, saved_state)
        await self.mount(widget)

        # Restore focus
        if self._focused_pane_id in self._panes:
            self._panes[self._focused_pane_id].is_focused_pane = True

        # Run any pending commands for new panes
        for pid, cmd in list(self._pending_commands.items()):
            if pid in self._panes and cmd:
                self.call_later(self._panes[pid].run_command, cmd)
        self._pending_commands.clear()

        self.post_message(self.PaneCountChanged(self.pane_count))

    def _build_widget(
        self, node: PaneNode, saved: dict[str, tuple[str, str, str]],
        parent_split: Optional[str] = None,
    ) -> Widget:
        """Recursively build widgets from the pane tree."""
        if node.is_leaf:
            pid = node.pane_id or "unknown"
            if pid in saved:
                name, cmd, output = saved[pid]
            else:
                num = pid.split("-")[-1]
                name = f"Pane {num}"
                cmd = ""
                output = ""
            pane = self._create_pane(
                pid, name, cmd, is_focused=(pid == self._focused_pane_id)
            )
            pane.command_output = output
            # Apply size weight from parent's split direction
            self._apply_size_weight(pane, node, parent_split)
            return pane

        # Split node — build a container
        children = [
            self._build_widget(c, saved, parent_split=node.split)
            for c in node.children
        ]

        if node.split == "horizontal":
            container = Vertical(*children, classes="pane-split-h")
        else:
            container = Horizontal(*children, classes="pane-split-v")

        # Apply size weight to the container itself (if nested)
        self._apply_size_weight(container, node, parent_split)

        return container

    @staticmethod
    def _apply_size_weight(
        widget: Widget, node: PaneNode, parent_split: Optional[str]
    ) -> None:
        """Apply CSS size based on node's weight and parent's split direction."""
        if parent_split is None:
            return  # Root node — fills all space via CSS

        # Calculate percentage from weight relative to siblings
        if node.parent and node.parent.children:
            total = sum(c.size_weight for c in node.parent.children)
            pct = (node.size_weight / total) * 100 if total > 0 else 50
        else:
            pct = 100

        if parent_split == "vertical":
            widget.styles.width = f"{pct:.1f}%"
        elif parent_split == "horizontal":
            widget.styles.height = f"{pct:.1f}%"

    async def split_horizontal(self, command: str = "") -> str:
        """Split the focused pane horizontally (new pane below).

        Returns the ID of the new pane.
        """
        return await self._split("horizontal", command=command)

    async def split_vertical(self, command: str = "") -> str:
        """Split the focused pane vertically (new pane right).

        Returns the ID of the new pane.
        """
        return await self._split("vertical", command=command)

    async def _split(self, direction: str, command: str = "") -> str:
        """Split the focused pane in the given direction."""
        new_id = self._next_pane_id()
        focused_node = self._tree.find_leaf(self._focused_pane_id)

        if focused_node is None:
            return ""

        # Convert the leaf into a split node with two children
        old_id = focused_node.pane_id
        focused_node.pane_id = None
        focused_node.split = direction

        old_child = PaneNode(pane_id=old_id, parent=focused_node)
        new_child = PaneNode(pane_id=new_id, parent=focused_node)
        focused_node.children = [old_child, new_child]

        # Store command to run after rebuild
        if command:
            self._pending_commands[new_id] = command

        await self.rebuild_layout()

        # Focus the new pane
        await self.focus_pane(new_id)

        return new_id

    async def close_pane(self, pane_id: Optional[str] = None) -> bool:
        """Close a pane. If no ID given, closes the focused pane.

        Returns True if a pane was closed.
        """
        target_id = pane_id or self._focused_pane_id
        all_ids = self._tree.all_pane_ids()

        # Can't close the last pane
        if len(all_ids) <= 1:
            return False

        target_node = self._tree.find_leaf(target_id)
        if target_node is None or target_node.parent is None:
            # It's the root — replace root with its sibling
            if self._tree.is_leaf:
                return False
            # Find the sibling
            sibling = None
            for child in self._tree.children:
                leaf = child.find_leaf(target_id)
                if leaf is None:
                    sibling = child
                    break
            if sibling is None:
                return False
            # Replace the tree root with the sibling
            self._tree = sibling
            self._tree.parent = None
        else:
            parent = target_node.parent
            # Find sibling
            sibling = None
            for child in parent.children:
                if child is not target_node:
                    sibling = child
                    break
            if sibling is None:
                return False

            # Replace parent with sibling
            grandparent = parent.parent
            if grandparent is None:
                # Parent is root
                self._tree = sibling
                self._tree.parent = None
            else:
                idx = grandparent.children.index(parent)
                grandparent.children[idx] = sibling
                sibling.parent = grandparent

        # Move focus to next available pane
        remaining = self._tree.all_pane_ids()
        if target_id == self._focused_pane_id:
            self._focused_pane_id = remaining[0] if remaining else ""

        await self.rebuild_layout()
        return True

    async def focus_pane(self, pane_id: str) -> None:
        """Set focus to a specific pane."""
        if pane_id not in self._panes:
            return

        old_id = self._focused_pane_id
        if old_id in self._panes:
            self._panes[old_id].is_focused_pane = False

        self._focused_pane_id = pane_id
        self._panes[pane_id].is_focused_pane = True

        pane = self._panes[pane_id]
        self.post_message(self.FocusChanged(pane_id, pane.pane_name))

    async def focus_direction(self, direction: str) -> None:
        """Move focus in a direction: left, right, up, down.

        Uses the ordered list of pane IDs to navigate.
        For simplicity, left/up = previous, right/down = next.
        """
        ids = self._tree.all_pane_ids()
        if len(ids) <= 1:
            return

        try:
            current_idx = ids.index(self._focused_pane_id)
        except ValueError:
            return

        if direction in ("left", "up"):
            new_idx = (current_idx - 1) % len(ids)
        else:  # right, down
            new_idx = (current_idx + 1) % len(ids)

        await self.focus_pane(ids[new_idx])

    def on_pane_focused(self, event: Pane.Focused) -> None:
        """Handle pane click-to-focus."""
        event.stop()
        self.call_later(self.focus_pane, event.pane_id)

    def get_pane(self, pane_id: str) -> Optional[Pane]:
        """Get a pane widget by ID."""
        return self._panes.get(pane_id)

    async def run_command_in_pane(self, pane_id: str, command: str) -> bool:
        """Run a command in a specific pane.

        Returns True if the command was started.
        """
        pane = self._panes.get(pane_id)
        if pane is None:
            return False
        await pane.run_command(command)
        return True

    async def run_command_in_focused(self, command: str) -> bool:
        """Run a command in the currently focused pane."""
        return await self.run_command_in_pane(self._focused_pane_id, command)

    # --- Resize ---

    RESIZE_STEP = 0.2  # 20% weight change per resize action
    MIN_WEIGHT = 0.2   # Minimum weight to prevent panes from disappearing

    async def resize_focused(self, grow: bool = True) -> bool:
        """Resize the focused pane (grow or shrink).

        Adjusts the size_weight of the focused pane's node and
        its sibling proportionally. Returns True if resized.

        Zellij: Ctrl+n mode → +/= to grow, - to shrink
        """
        focused_node = self._tree.find_leaf(self._focused_pane_id)
        if focused_node is None or focused_node.parent is None:
            return False  # Root pane can't be resized

        parent = focused_node.parent
        if len(parent.children) < 2:
            return False

        # Find sibling
        sibling = None
        for child in parent.children:
            if child is not focused_node:
                sibling = child
                break
        if sibling is None:
            return False

        step = self.RESIZE_STEP
        if grow:
            # Grow focused, shrink sibling
            if sibling.size_weight - step < self.MIN_WEIGHT:
                return False
            focused_node.size_weight += step
            sibling.size_weight -= step
        else:
            # Shrink focused, grow sibling
            if focused_node.size_weight - step < self.MIN_WEIGHT:
                return False
            focused_node.size_weight -= step
            sibling.size_weight += step

        await self.rebuild_layout()
        return True

    def get_focused_weight(self) -> float:
        """Get the size weight of the focused pane."""
        node = self._tree.find_leaf(self._focused_pane_id)
        return node.size_weight if node else 1.0

    # --- Tab ownership ---

    @property
    def active_tab(self) -> int:
        """Return the currently active tab index."""
        return self._active_tab

    def _save_current_tab(self) -> None:
        """Save the current tab's pane state."""
        saved: dict[str, tuple[str, str, str]] = {}
        for pid, pane in self._panes.items():
            saved[pid] = (pane.pane_name, pane.command, pane.command_output)

        self._tab_states[self._active_tab] = TabState(
            tree=self._tree,
            focused_pane_id=self._focused_pane_id,
            pane_counter=self._pane_counter,
            saved_pane_data=saved,
        )

    async def switch_tab(self, tab_index: int) -> None:
        """Switch to a different tab's pane layout.

        Saves the current tab's state, loads the target tab's state
        (or creates a fresh single-pane layout for new tabs), and
        rebuilds the visual layout.
        """
        if tab_index == self._active_tab:
            return

        # Save current tab
        self._save_current_tab()

        # Load target tab
        self._active_tab = tab_index

        if tab_index in self._tab_states:
            # Restore saved state
            state = self._tab_states[tab_index]
            self._tree = state.tree
            self._focused_pane_id = state.focused_pane_id
            self._pane_counter = state.pane_counter

            # Rebuild with saved data
            await self.remove_children()
            self._panes.clear()
            widget = self._build_widget(self._tree, state.saved_pane_data)
            await self.mount(widget)

            if self._focused_pane_id in self._panes:
                self._panes[self._focused_pane_id].is_focused_pane = True
        else:
            # New tab — fresh single pane
            new_id = self._next_pane_id()
            self._tree = PaneNode(pane_id=new_id)
            self._focused_pane_id = new_id

            await self.remove_children()
            self._panes.clear()
            num = new_id.split("-")[-1]
            pane = self._create_pane(new_id, f"Pane {num}", is_focused=True)
            await self.mount(pane)

        self.post_message(self.PaneCountChanged(self.pane_count))
        self.post_message(self.TabSwitched(tab_index))

    def remove_tab_state(self, tab_index: int) -> None:
        """Remove saved state for a tab (when tab is closed)."""
        self._tab_states.pop(tab_index, None)

    def get_tab_pane_count(self, tab_index: int) -> int:
        """Get the pane count for a specific tab."""
        if tab_index == self._active_tab:
            return self.pane_count
        state = self._tab_states.get(tab_index)
        if state:
            return len(state.tree.all_pane_ids())
        return 1  # Default for new tabs
