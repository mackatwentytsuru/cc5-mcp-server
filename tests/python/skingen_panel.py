"""
A fake SkinGen panel for the tests: switch, layer table (one cell widget per row), opacity box and
delete button, named like the real widgets (see cc5-plugin/cc5_skingen.py). Not a test module.
"""

from __future__ import annotations

from ui_support import cc5_ui, fake_qt  # sets up sys.path and the RLPy stand-in

import cc5_skingen  # noqa: E402


class Panel:
    """A fake SkinGen panel: switch, layer table (one cell widget per row), opacity box, delete button."""

    def __init__(self, layers=("Lips", "Eyeshadow", "Blush"), active=True, with_menu=True) -> None:
        self.root = fake_qt.Widget(name="MixSubstancePanel", visible=True)
        self.switch = fake_qt.CheckBox("Activate Editor", self.root, name=cc5_skingen.SWITCH, checked=active)
        self.table = fake_qt.Table(self.root, name=cc5_skingen.TABLE)
        for name in layers:
            self.add_row(name)
        box = fake_qt.Widget(name=cc5_skingen.OPACITY_BOX, parent=self.root)
        self.spin = fake_qt.SpinBox(box, name=cc5_skingen.SPIN, value=100)
        self.delete_button = fake_qt.ToolButton("", self.root, name=cc5_skingen.DELETE_BUTTON)
        self.deleted: list[str] = []
        if with_menu:
            self.delete_button._menu = fake_qt.ActionMenu([
                fake_qt.Action("Selected Layer", on_trigger=self.delete_selected),
                fake_qt.Action("Current Material", on_trigger=lambda: self.deleted.append("current_material")),
                fake_qt.Action("All Material", on_trigger=lambda: self.deleted.append("all_material")),
            ])

    def add_row(self, name: str) -> None:
        cell = fake_qt.Widget(visible=True)
        eye = fake_qt.ToolButton("", cell, name=cc5_skingen.ROW_ENABLE, checked=False)
        eye.on_click = lambda b=eye: b.setChecked(not b.isChecked())
        fake_qt.Label(name, cell, name=cc5_skingen.ROW_NAME)
        fake_qt.Label(str(len(self.table.cells) + 1), cell, name=cc5_skingen.ROW_INDEX)
        self.table.cells.append(cell)

    def eye(self, row: int):
        return self.table.cells[row].findChildren(fake_qt.ToolButton)[0]

    def delete_selected(self) -> None:
        row = self.table.currentRow()
        self.deleted.append(f"selected:{row}")
        if row >= 0:
            self.table.cells.pop(row)
            self.table.selected = []
