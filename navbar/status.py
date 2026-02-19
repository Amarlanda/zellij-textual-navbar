"""Status tab — overview of all tabs and panes.

A special pane widget that displays a dashboard view of all tabs
and their panes, with quick rename capability.

Zellij equivalent: Ctrl+o → session manager
Custom: Alt+s or 's' to toggle status view
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.reactive import reactive
from textual.widgets import Static

if TYPE_CHECKING:
    from navbar.panes import PaneContainer
    from navbar.widgets import TabList


class StatusView(Static):
    """Status overview showing all tabs and their panes.

    Renders a tree view:
        📋 Status Overview
        ─────────────────
        ▸ Tab 1 (active) — 3 panes
          ├─ Pane 1 [focused] $ echo hello
          ├─ Pane 2           $ ls -la
          └─ Pane 3           (empty)
        Tab 2 — 1 pane
          └─ Pane 4           (empty)
    """

    status_text: reactive[str] = reactive("Loading...")

    def render(self) -> str:
        return self.status_text

    def refresh_status(
        self,
        tab_list: TabList,
        pane_container: PaneContainer,
        active_tab: int,
    ) -> None:
        """Rebuild the status overview from current state."""
        lines = [
            "📋 Status Overview",
            "─" * 40,
            "",
        ]

        tabs = tab_list.tab_items
        for i, tab in enumerate(tabs):
            is_active = (i == active_tab)
            marker = "▸" if is_active else " "
            active_label = " (active)" if is_active else ""
            pane_count = pane_container.get_tab_pane_count(i)
            pane_word = "pane" if pane_count == 1 else "panes"

            lines.append(
                f"{marker} {tab.tab_name}{active_label} — {pane_count} {pane_word}"
            )

            # Show pane details for the active tab
            if is_active:
                pane_ids = pane_container.all_pane_ids
                for j, pid in enumerate(pane_ids):
                    pane = pane_container.get_pane(pid)
                    if pane is None:
                        continue

                    is_last = (j == len(pane_ids) - 1)
                    connector = "└─" if is_last else "├─"
                    focus = "[focused]" if pane.is_focused_pane else "         "
                    cmd = f"$ {pane.command}" if pane.command else "(empty)"

                    lines.append(
                        f"  {connector} {pane.pane_name} {focus} {cmd}"
                    )
            else:
                # For inactive tabs, show summary from saved state
                saved_count = pane_container.get_tab_pane_count(i)
                lines.append(f"  └─ ({saved_count} pane{'s' if saved_count != 1 else ''})")

            lines.append("")

        # Footer
        lines.append("─" * 40)
        lines.append(f"Total: {len(tabs)} tabs")
        lines.append("")
        lines.append("Keys: s=close status, r=rename, 1-9=jump to tab")

        self.status_text = "\n".join(lines)
