"""Batch queue of chapters. Pure state; the GUI drives transitions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class BatchItem:
    chapter: int
    url: str
    status: str = "pending"  # pending | ready | recording | done | failed | skipped
    output: str = ""
    error: str = ""


class BatchManager:
    def __init__(self) -> None:
        self.items: list[BatchItem] = []
        self.index: int = -1
        self.active = False

    def set_items(self, items: list[BatchItem]) -> None:
        if self.active:
            raise RuntimeError("Cannot change the batch while it is running")
        self.items = items
        self.index = -1

    def add_range(self, chapters: list[int], url_template: str) -> None:
        existing = {i.chapter for i in self.items}
        for c in chapters:
            if c not in existing:
                self.items.append(BatchItem(c, url_template.format(chapter=c)))
        self.items.sort(key=lambda i: i.chapter)

    def start(self) -> Optional[BatchItem]:
        if not self.items:
            raise RuntimeError("Batch is empty")
        self.active = True
        self.index = -1
        return self.advance()

    @property
    def current(self) -> Optional[BatchItem]:
        if 0 <= self.index < len(self.items):
            return self.items[self.index]
        return None

    def advance(self) -> Optional[BatchItem]:
        """Move to the next pending item; returns None (and deactivates) when finished."""
        for i in range(self.index + 1, len(self.items)):
            if self.items[i].status in ("pending", "failed", "ready"):
                self.index = i
                return self.items[i]
        self.index = len(self.items)
        self.active = False
        return None

    def mark(self, status: str, output: str = "", error: str = "") -> None:
        item = self.current
        if item:
            item.status, item.output, item.error = status, output or item.output, error

    def cancel(self) -> None:
        self.active = False

    def summary(self) -> str:
        done = sum(i.status == "done" for i in self.items)
        failed = sum(i.status == "failed" for i in self.items)
        return f"{done}/{len(self.items)} done, {failed} failed"
