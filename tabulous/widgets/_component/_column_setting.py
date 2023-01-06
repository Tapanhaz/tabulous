from __future__ import annotations
from abc import abstractmethod
from typing import (
    Hashable,
    TYPE_CHECKING,
    TypeVar,
    Any,
    Union,
    MutableMapping,
    Iterator,
    Callable,
    Mapping,
    Sequence,
)
from functools import wraps

import numpy as np

from tabulous.types import ColorMapping, ColorType
from tabulous.color import normalize_color
from tabulous._dtype import get_converter, get_converter_from_type, isna
from ._base import Component, TableComponent

if TYPE_CHECKING:
    from pandas.core.dtypes.dtypes import ExtensionDtype
    from tabulous.widgets._table import TableBase, SpreadSheet  # noqa: F401

    _DtypeLike = Union[ExtensionDtype, np.dtype]

    from typing_extensions import TypeGuard
    import pandas as pd

    _Formatter = Union[Callable[[Any], str], str, None]
    _Validator = Callable[[Any], None]
    _TimeType = Union[pd.Timestamp, pd.Timedelta]
    _NumberLike = Union[int, float, _TimeType]
    _Interpolatable = Union[
        Mapping[_NumberLike, ColorType],
        Sequence[tuple[_NumberLike, ColorType]],
        tuple[ColorType, ColorType],  # linear interpolation with limits
    ]

T = TypeVar("T")
_F = TypeVar("_F", bound=Callable)
_Void = object()


class _DictPropertyInterface(TableComponent, MutableMapping[str, _F]):
    @abstractmethod
    def _get_dict(self) -> dict[str, ColorMapping]:
        """Get dict of colormaps."""

    @abstractmethod
    def _set_value(self, key: str, cmap: ColorMapping):
        """Set colormap at key."""

    def __getitem__(self, key: str) -> ColorMapping | None:
        return self._get_dict()[key]

    def __setitem__(self, key: str, cmap: ColorMapping) -> None:
        self.set(key, cmap)
        return None

    def __delitem__(self, key: str) -> None:
        return self._set_value(key, None)

    def __repr__(self) -> str:
        clsname = type(self).__name__
        _dict = self._get_dict()
        if _dict:
            _args = ",\n\t".join(f"{k!r}: {v}" for k, v in _dict.items())
            return f"{clsname}(\n\t{_args}\n)"
        return f"{clsname}()"

    def __len__(self) -> str:
        return len(self._get_dict())

    def __iter__(self) -> Iterator[str]:
        return iter(self._get_dict())

    def set(self, column_name: str, func: _F = _Void):
        def _wrapper(f: _F) -> _F:
            self._set_value(column_name, f)
            return f

        return _wrapper(func) if func is not _Void else _wrapper

    def __call__(self, *args, **kwargs):
        # backwards compatibility
        return self.set(*args, **kwargs)


class _ColormapInterface(_DictPropertyInterface[ColorMapping]):
    """Abstract interface to the column colormap."""

    def set(
        self,
        column_name: str,
        colormap: ColorMapping = _Void,
        *,
        interpolate_from: _Interpolatable | None = None,
        infer_parser: bool = True,
    ):
        def _wrapper(f: ColorMapping) -> ColorMapping:
            if infer_parser:
                parser = self._get_converter(f, column_name)
                self._set_value(column_name, wraps(f)(lambda x: f(parser(x))))
            else:
                self._set_value(column_name, f)
            return f

        if isinstance(colormap, Mapping):
            return _wrapper(lambda x: colormap.get(x, None))
        elif colormap is _Void:
            if interpolate_from is None:
                return _wrapper
            else:
                return _wrapper(
                    self._from_interpolatable(interpolate_from, column_name)
                )
        elif isinstance(colormap, str):
            colormap = self._from_colormap_name(column_name, colormap)
            return _wrapper(colormap)
        else:
            return _wrapper(colormap)

    def _from_interpolatable(
        self, seq: _Interpolatable, column_name: str
    ) -> ColorMapping:
        if isinstance(seq, Mapping):
            raise NotImplementedError("Mapping interpolation not yet implemented.")
        else:
            if isinstance(seq[0], tuple) and len(seq[0]) == 2:
                # list[tuple[number, ColorType]]
                raise NotImplementedError("Mapping interpolation not yet implemented.")
            else:
                seq: tuple[ColorType, ColorType]
                vmin, vmax = (np.array(normalize_color(v)) for v in seq)

                def _cmap(x):
                    return vmin * (1 - x) + vmax * x

                return self._cmap_for_column(column_name, _cmap)

    def _from_colormap_name(self, column_name: str, colormap: str) -> ColorMapping:
        from matplotlib.cm import get_cmap

        mpl_cmap = get_cmap(colormap)

        def _cmap(x):
            return np.asarray(mpl_cmap(int(x * 255))) * 255

        return self._cmap_for_column(column_name, _cmap)

    def _cmap_for_column(self, column_name: str, cmap: ColorMapping):
        """
        Create a colormap for a column, with min/max as the color limits.

        Parameters
        ----------
        column_name : str
            Name of the column.
        cmap : [0, 1] -> ColorType
            Colormap function

        Returns
        -------
        _type_
            _description_

        Raises
        ------
        TypeError
            _description_
        """
        ds = self.parent.native._get_sub_frame(column_name)
        vmin, vmax = ds.min(), ds.max()
        if ds.dtype.kind in "uif":

            def _cmap(x) -> ColorType:
                x = float(x)
                if isna(x):
                    return None
                ratio = (x - vmin) / (vmax - vmin)
                ratio = max(0.0, min(1.0, ratio))
                return cmap(ratio)

        elif ds.dtype.kind in "mM":
            vmin: _TimeType
            vmax: _TimeType
            vmin, vmax = vmin.value, vmax.value
            converter = get_converter(ds.dtype.kind)

            def _cmap(x):
                x = converter(x).value
                ratio = (x - vmin) / (vmax - vmin)
                ratio = max(0.0, min(1.0, ratio))
                return cmap(ratio)

        elif ds.dtype.kind == "b":
            _cmap = cmap
        else:
            raise TypeError(f"Cannot infer colormap for dtype {ds.dtype}")
        return _cmap

    def _get_converter(self, f: ColorMapping, column_name: str):
        table = self.parent
        parser = None

        # try to infer parser from function annotations
        _ann = f.__annotations__
        if (key := next(iter(_ann.keys()), None)) and key != "return":
            arg_type = _ann[key]
            parser = get_converter_from_type(arg_type)
            if parser is get_converter("O"):
                raise TypeError(f"Cannot infer parser from {arg_type}")

        elif _is_spreadsheet(table) and (dtype := table.dtypes.get(column_name, None)):
            # try to infer parser from table column dtype
            parser = get_converter(dtype.kind)

        else:
            dtype = table.data[column_name].dtype
            parser = get_converter(dtype.kind)

        return parser


class TextColormapInterface(_ColormapInterface):
    """Interface to the column text colormap."""

    def _get_dict(self) -> dict[str, ColorMapping]:
        return self.parent._qwidget.model()._foreground_colormap

    def _set_value(self, key: str, cmap: ColorMapping):
        return self.parent.native.setForegroundColormap(key, cmap)


class BackgroundColormapInterface(_ColormapInterface):
    """Interface to the column background colormap."""

    def _get_dict(self) -> dict[str, ColorMapping]:
        return self.parent._qwidget.model()._background_colormap

    def _set_value(self, key: str, cmap: ColorMapping):
        return self.parent.native.setBackgroundColormap(key, cmap)


class TextFormatterInterface(_DictPropertyInterface["_Formatter"]):
    """Interface to the column background colormap."""

    def _get_dict(self) -> dict[str, _Formatter]:
        return self.parent._qwidget.model()._text_formatter

    def _set_value(self, key: str, cmap: _Formatter):
        return self.parent.native.setTextFormatter(key, cmap)


class ValidatorInterface(_DictPropertyInterface["_Validator"]):
    """Interface to the column validator."""

    def _get_dict(self) -> dict[str, _Validator]:
        return self.parent._qwidget.model()._text_formatter

    def _set_value(self, key: str, cmap: _Validator):
        return self.parent.native.setTextFormatter(key, cmap)


def _is_spreadsheet(table: TableBase) -> TypeGuard[SpreadSheet]:
    return table.table_type == "SpreadSheet"


class ColumnDtypeInterface(Component["SpreadSheet"], MutableMapping[str, "_DtypeLike"]):
    """Interface to the column dtype of spreadsheet."""

    def __getitem__(self, key: str) -> _DtypeLike | None:
        """Get the dtype of the given column name."""
        return self.parent._qwidget._columns_dtype.get(key, None)

    def __setitem__(self, key: str, dtype: Any) -> None:
        """Set a dtype to the given column name."""
        return self.parent._qwidget.setColumnDtype(key, dtype)

    def __delitem__(self, key: str) -> None:
        """Reset the dtype to the given column name."""
        return self.parent._qwidget.setColumnDtype(key, None)

    def __repr__(self) -> str:
        clsname = type(self).__name__
        dict = self.parent._qwidget._columns_dtype
        return f"{clsname}({dict!r})"

    def __len__(self) -> str:
        return len(self.parent._qwidget._columns_dtype)

    def __iter__(self) -> Iterator[Hashable]:
        return iter(self.parent._qwidget._columns_dtype)

    def set_dtype(
        self,
        name: Hashable,
        dtype: Any,
        *,
        validation: bool = True,
        formatting: bool = True,
    ) -> None:
        """Set dtype and optionally default validator and formatter."""
        self.parent._qwidget.setColumnDtype(name, dtype)
        if validation:
            self.parent._qwidget._set_default_data_validator(name)
        if formatting:
            self.parent._qwidget._set_default_text_formatter(name)
        return None
