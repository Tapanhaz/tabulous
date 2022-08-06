from typing import List
import numpy as np
import pandas as pd
from ..._magicgui import dialog_factory, Axes
from ...types import TableData


@dialog_factory
def summarize_table(df: TableData, methods: List[str]):
    return df.agg(methods)


@dialog_factory
def groupby(df: TableData, by: List[str]):
    return df.groupby(by)


@dialog_factory
def hconcat(viewer, names: List[str]):
    dfs = [viewer.tables[name].data for name in names]
    return pd.concat(dfs, axis=0)


@dialog_factory
def vconcat(viewer, names: List[str]):
    dfs = [viewer.tables[name].data for name in names]
    return pd.concat(dfs, axis=1)


@dialog_factory
def pivot(df: TableData, index: str, columns: str, values: str) -> TableData:
    return df.pivot(index=index, columns=columns, values=values)


@dialog_factory
def melt(df: TableData, id_vars: List[str]) -> TableData:
    return pd.melt(df, id_vars)


@dialog_factory
def sort(df: TableData, by: List[str], ascending: bool = True) -> TableData:
    return df.sort_values(by=by, ascending=ascending)


@dialog_factory
def plot(ax: Axes, x, y, alpha: float = 1.0):
    for _y in y:
        if x is None:
            _x = np.arange(len(_y))
        else:
            _x = x
        ax.plot(_x, _y, alpha=alpha)


@dialog_factory
def scatter(ax: Axes, x, y, alpha: float = 1.0):
    for _y in y:
        if x is None:
            _x = np.arange(len(_y))
        else:
            _x = x
        ax.scatter(_x, _y, alpha=alpha)


@dialog_factory
def hist(ax: Axes, y, bins: int = 10, alpha: float = 1.0, density: bool = False):
    for _y in y:
        ax.hist(_y, bins=bins, alpha=alpha, density=density)
    ax.axhline(0, color="gray", lw=0.5, alpha=0.5, zorder=-1)


@dialog_factory
def swarmplot(
    ax: Axes,
    x: str,
    y: str,
    data,
    hue: str = None,
    dodge: bool = False,
    alpha: float = 1.0,
):
    import seaborn as sns

    sns.swarmplot(x=x, y=y, data=data, hue=hue, dodge=dodge, alpha=alpha, ax=ax)


@dialog_factory
def barplot(
    ax: Axes,
    x: str,
    y: str,
    data,
    hue: str = None,
    dodge: bool = False,
    alpha: float = 1.0,
):
    import seaborn as sns

    sns.barplot(x=x, y=y, data=data, hue=hue, dodge=dodge, alpha=alpha, ax=ax)
    ax.axhline(0, color="gray", lw=0.5, alpha=0.5, zorder=-1)


@dialog_factory
def boxplot(
    ax: Axes,
    x: str,
    y: str,
    data,
    hue: str = None,
    dodge: bool = False,
    alpha: float = 1.0,
):
    import seaborn as sns

    sns.boxplot(x=x, y=y, data=data, hue=hue, dodge=dodge, alpha=alpha, ax=ax)


@dialog_factory
def boxenplot(
    ax: Axes,
    x: str,
    y: str,
    data,
    hue: str = None,
    dodge: bool = False,
    alpha: float = 1.0,
):
    import seaborn as sns

    sns.boxenplot(x=x, y=y, data=data, hue=hue, dodge=dodge, alpha=alpha, ax=ax)
