# Owner: look inside CC5's open Qt dialogs (titles, tables, combo boxes) and, when asked, pick a
# combo-box entry in a table row by row name. Synthetic mouse clicks do not open CC5's combo boxes,
# so this sets them from inside CC5. Run with Script > Load Python; settings below.
import json
from PySide2.QtWidgets import QApplication, QComboBox, QTableWidget, QTableView

WINDOW = "Asset Import Status Report"
SET_ROW_STARTS = "beyon_boot"     # row whose first column starts with this
SET_COLUMN = 1                    # Type column
SET_TEXT = "Shoes"
OUT = r"D:\OTOLUME\beyon_cc5\parts\v29_boot\qt_probe.json"

report = {"windows": [], "set": None}
for w in QApplication.instance().topLevelWidgets():
    if not w.isVisible():
        continue
    report["windows"].append(w.windowTitle())
    if w.windowTitle() != WINDOW:
        continue
    for t in w.findChildren(QTableWidget):
        rows = []
        for r in range(t.rowCount()):
            cells = []
            for c in range(t.columnCount()):
                cw = t.cellWidget(r, c)
                if isinstance(cw, QComboBox):
                    cells.append({"combo": cw.currentText(), "items": [cw.itemText(i) for i in range(cw.count())]})
                else:
                    it = t.item(r, c)
                    cells.append(it.text() if it else (cw.findChild(QComboBox).currentText() if cw and cw.findChild(QComboBox) else None))
            rows.append(cells)
            name = cells[0] if isinstance(cells[0], str) else ""
            if SET_TEXT and name and name.startswith(SET_ROW_STARTS):
                cw = t.cellWidget(r, SET_COLUMN)
                combo = cw if isinstance(cw, QComboBox) else (cw.findChild(QComboBox) if cw else None)
                if combo is not None:
                    i = combo.findText(SET_TEXT)
                    if i >= 0:
                        combo.setCurrentIndex(i)
                        report["set"] = [name, combo.currentText()]
        report.setdefault("tables", []).append(rows)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=1)
