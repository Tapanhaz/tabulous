from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Generic, TypeVar
from abc import ABC, abstractmethod
from contextlib import contextmanager
from tabulous._utils import get_config
from tabulous._range import MultiRectRange, RectRange

from qtpy import QtCore, QtWidgets as QtW

if TYPE_CHECKING:
    from ._base import QBaseTable
    from ._base._item_model import AbstractDataFrameModel

_Q = TypeVar("_Q", bound=QtCore.QObject)


class _Animation(ABC, Generic[_Q]):
    DURATION = 60

    def __init__(self, parent: _Q):
        self._parent = parent
        self._anim = QtCore.QVariantAnimation(parent)
        self._anim.setDuration(self.DURATION)
        self._anim.valueChanged.connect(self._on_animate)
        self._is_running = False
        self._use_anim = True

    @property
    def should_animate(self) -> bool:
        return self._use_anim and not self._is_running

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def value(self) -> float:
        """Current value of the animation in range [0, 1]."""
        return self._anim.currentValue()

    @abstractmethod
    def _on_animate(self, ratio: float):
        """Animation callback"""

    def set_animate(self, animate: bool):
        self._use_anim = animate
        return self

    @contextmanager
    def using_animation(self, use_anim: bool = True):
        """Context manager to enable/disable animation."""
        _old = self._use_anim
        self._use_anim = use_anim
        try:
            yield None
        finally:
            self._use_anim = _old


class _CellAnimation(_Animation["AbstractDataFrameModel"]):
    def __init__(self, parent: AbstractDataFrameModel):
        super().__init__(parent)
        self._ranges: MultiRectRange = MultiRectRange([])
        self._anim.finished.connect(self._finished)

    def _on_animate(self, ratio: float):
        self._parent.parent().update()

    def _finished(self):
        pass


class CellColorAnimation(_CellAnimation):
    DURATION = 300

    def start(self, r: slice, c: slice):
        if not (isinstance(r, slice) and isinstance(c, slice)):
            return
        if self._use_anim:
            self._ranges = self._ranges.with_slices(r, c)
            self._is_running = True
            self._anim.setStartValue(0.0)
            self._anim.setEndValue(1.0)
            self._anim.start()
        return None

    def _finished(self):
        self._is_running = False
        self._ranges = MultiRectRange([])

    def contains(self, index: QtCore.QModelIndex) -> bool:
        nr, nc = self._parent.df.shape
        rng = self._ranges.intersection(RectRange(slice(0, nr), slice(0, nc)))
        return (index.row(), index.column()) in rng


class _RowColumnAnimation(_Animation["QBaseTable"]):
    def __init__(self, parent: QBaseTable):
        super().__init__(parent)
        self._anim.setEasingCurve(QtCore.QEasingCurve.Type.InCubic)
        self._index = 0
        self._count = 1

    @abstractmethod
    def _get_header(self) -> QtW.QHeaderView:
        """Get the header object."""

    @abstractmethod
    def _get_span(self, count: int) -> list[int]:
        """Get the span of the section."""

    def run_insert(self, idx: int, count: int, span: int | list[int] | None = None):
        if not self.should_animate:
            return None
        self._is_running = True
        self._index = idx
        self._count = count
        if span is None:
            span = self._get_span(self._count)
        elif not hasattr(span, "__iter__"):
            span = [span] * self._count

        self._init_spans = span
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()

    def run_remove(self, idx: int, count: int):
        if not self.should_animate:
            return None
        self._is_running = True
        self._index = idx
        self._count = count
        self._init_spans = [
            self._get_header().sectionSize(i)
            for i in range(self._index, self._index + self._count)
        ]
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.start()

    def _on_animate(self, ratio: float):
        header = self._get_header()
        for i, span in enumerate(self._init_spans):
            header.resizeSection(self._index + i, int(span * ratio))

    def connect(self, fn: Callable[[], None]):
        """Connect to the finished event of the animation."""
        if not self.should_animate:
            return fn()

        @self._anim.finished.connect
        def _f():
            try:
                with self._parent._mgr.blocked():
                    fn()
            finally:
                self._anim.finished.disconnect(_f)
                self._is_running = False

        return _f


class ColumnAnimation(_RowColumnAnimation):
    def _get_header(self):
        return self._parent._qtable_view.horizontalHeader()

    def _get_span(self, count: int) -> list[int]:
        return [get_config().table.column_size] * count


class RowAnimation(_RowColumnAnimation):
    def _get_header(self):
        return self._parent._qtable_view.verticalHeader()

    def _get_span(self, count: int) -> list[int]:
        return [get_config().table.row_size] * count
