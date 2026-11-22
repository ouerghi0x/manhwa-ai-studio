"""Dialog to add chapters to the batch, by range or by explicit URLs."""
from __future__ import annotations

from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit,
                               QMessageBox, QPlainTextEdit, QVBoxLayout)

from ..core.batch_manager import BatchItem
from ..utils.validators import parse_chapter_range, validate_url


class ChapterDialog(QDialog):
    def __init__(self, url_template: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add chapters to batch")
        self.setMinimumWidth(560)
        self.items: list[BatchItem] = []
        lay = QVBoxLayout(self)
        f = QFormLayout()
        self.template = QLineEdit(url_template)
        f.addRow("URL template", self.template)
        self.range = QLineEdit()
        self.range.setPlaceholderText("e.g. 45-48, 50")
        f.addRow("Chapter numbers", self.range)
        lay.addLayout(f)
        hint = QLabel("…or paste explicit lines as  <chapter number> <url>  (one per line):")
        hint.setObjectName("hint")
        lay.addWidget(hint)
        self.lines = QPlainTextEdit()
        self.lines.setPlaceholderText("45 https://example.com/chapter/45")
        lay.addWidget(self.lines)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self._accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _accept(self) -> None:
        items: list[BatchItem] = []
        try:
            if self.range.text().strip():
                tpl = self.template.text().strip()
                if "{chapter}" not in tpl:
                    raise ValueError("URL template must contain {chapter}")
                items += [BatchItem(c, tpl.format(chapter=c)) for c in parse_chapter_range(self.range.text())]
            for n, line in enumerate(self.lines.toPlainText().splitlines(), 1):
                if not line.strip():
                    continue
                num, _, url = line.strip().partition(" ")
                err = validate_url(url.strip())
                if err:
                    raise ValueError(f"Line {n}: {err}")
                items.append(BatchItem(int(num), url.strip()))
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid input", str(exc))
            return
        if not items:
            QMessageBox.warning(self, "Nothing to add", "Enter a chapter range or explicit lines.")
            return
        self.items = items
        self.accept()
