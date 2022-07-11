from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Callable, overload
from functools import partial
from psygnal import SignalGroup, Signal

from .keybindings import register_shortcut
from .filtering import FilterProperty

from ..types import SelectionRanges
from .._protocols import BackendTableProtocol

if TYPE_CHECKING:
    import pandas as pd
    from .._qt import QTableLayer, QSpreadSheet


class TableSignals(SignalGroup):
    """Signal group for a Table."""
    
    data = Signal(object)
    selections = Signal(object)
    zoom = Signal(float)
    renamed = Signal(str)

class TableLayerBase(ABC):
    """The base class for a table layer."""
    
    def __init__(self, data, name=None, editable: bool = True):
        import pandas as pd
        if not isinstance(data, pd.DataFrame):
            self._data = pd.DataFrame(data)
        else:
            self._data = data
        self.events = TableSignals()
        self._name = str(name)
        self._qwidget = self._create_backend(self._data)
        self._qwidget.setEditability(editable)
        self._qwidget.connectItemChangedSignal(self.events.data.emit)
        self._qwidget.connectSelectionChangedSignal(self.events.selections.emit)
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}<{self.name!r}>"
    
    @abstractmethod
    def _create_backend(self, data: pd.DataFrame) -> BackendTableProtocol:
        """This function creates a backend widget that follows BackendTableProtocol."""

    @property
    def data(self) -> pd.DataFrame:
        """Table data."""
        return self._qwidget.getDataFrame()
    
    @data.setter
    def data(self, value):
        import pandas as pd
        if not isinstance(value, pd.DataFrame):
            value = pd.DataFrame(value)
                
        self._data = value
        self._qwidget.setDataFrame(value)
    
    @property
    def shape(self) -> tuple[int, int]:
        """Shape of data."""
        return self._qwidget.dataShape()
    
    @property
    def table_shape(self) -> tuple[int, int]:
        """Shape of table."""
        return self._qwidget.tableShape()

    @property
    def precision(self) -> int:
        """Precision (displayed digits) of table."""
        return self._qwidget.precision()
    
    @precision.setter
    def precision(self, value: int) -> None:
        self._qwidget.setPrecision(value)
    
    @property
    def zoom(self) -> float:
        """Zoom factor of table."""
        return self._qwidget.zoom()
    
    @zoom.setter
    def zoom(self, value: float):
        self._qwidget.setZoom(value)

    def _set_name(self, value: str):
        with self.events.renamed.blocked():
            self.name = value
        
    @property
    def name(self) -> str:
        """Table name."""
        return self._name
    
    @name.setter
    def name(self, value: str):
        self._name = str(value)
        self.events.renamed.emit(self._name)

    @property
    def editable(self) -> bool:
        """Editability of table."""
        return self._qwidget.editability()
    
    @editable.setter
    def editable(self, value: bool):
        self._qwidget.setEditability(value)
    
    @property
    def columns(self):
        return self._data.columns
    
    @property
    def index(self):
        return self._data.index
    
    @property
    def selections(self):
        """Get the SelectionRanges object of current table selection."""
        rngs = SelectionRanges(self._qwidget.selections())
        rngs._changed.connect(self._qwidget.setSelections)
        rngs.events.removed.connect(lambda i, value: self._qwidget.setSelections(rngs))
        return rngs
    
    @selections.setter
    def selections(self, value) -> None:
        self._qwidget.setSelections(value)
    
    @overload
    def update(self, value: dict[str, Any]) -> None:
        ...
    
    @overload
    def update(self, **kwargs: dict[str, Any]) -> None:
        ...
    
    def update(self, value=None, **kwargs) -> None:
        """Update DataFrame using a dictionary-like representation."""
        if value is not None:
            if kwargs:
                raise ValueError("Cannot specify both value and kwargs.")
            kwargs = value
        data = self.data.copy()
        for k, v in kwargs.items():
            data[k] = v
        self.data = data
        self._qwidget.refresh()
        return None
    
    def refresh(self) -> None:
        """Refresh the table view."""
        return self._qwidget.refresh()
    
    filter = FilterProperty()
    
    def bind_key(self, *seq) -> Callable[[TableLayerBase], Any | None]:
        """Bind callback function to a key sequence."""
        def register(f):
            register_shortcut(seq, self._qwidget, partial(f, self))
        return register


class TableLayer(TableLayerBase):
    def _create_backend(self, data: pd.DataFrame) -> QTableLayer:
        from .._qt import QTableLayer
        return QTableLayer(data=data)

class SpreadSheet(TableLayerBase):
    def _create_backend(self, data: pd.DataFrame) -> QSpreadSheet:
        from .._qt import QSpreadSheet
        return QSpreadSheet(data=data)