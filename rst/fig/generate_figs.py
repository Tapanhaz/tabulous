from pathlib import Path
import numpy as np

from tabulous import TableViewer, commands as cmds
from tabulous_doc import FunctionRegistry

REG = FunctionRegistry(Path(__file__).parent)

@REG.register
def table():
    viewer = TableViewer()
    table = viewer.add_table({"A": [1, 2, 3], "B": [4, 5, 6]}, name="table name")
    viewer.native.setMinimumSize(1, 1)
    viewer.size = (120, 180)
    return table

@REG.register
def spreadsheet():
    viewer = TableViewer()
    sheet = viewer.add_spreadsheet([["2", "t"], ["3", "u"]])
    viewer.native.setMinimumSize(1, 1)
    viewer.size = (120, 180)
    return sheet

@REG.register
def edit_cell():
    viewer = TableViewer()
    sheet = viewer.add_spreadsheet({"A": [1, 2, 3, 4], "B": ["a", "b", "c", "d"]})
    viewer.size = (100, 100)
    sheet.move_iloc(2, 2)
    cmds.selection.edit_current(viewer)
    return viewer

@REG.register
def colormap():
    viewer = TableViewer()
    table = viewer.open_sample("iris")

    # set a continuous colormap to the "sepal_length" column
    lmin = table.data["sepal_length"].min()
    lmax = table.data["sepal_length"].max()
    lrange = lmax - lmin

    @table.text_color.set("sepal_length")
    def _(x: float):
        red = np.array([255, 0, 0, 255], dtype=np.uint8)
        blue = np.array([0, 0, 255, 255], dtype=np.uint8)
        return (x - lmin) / lrange * blue + (lmax - x) / lrange * red

    # set a discrete colormap to the "sepal_width" column
    @table.background_color.set("sepal_width")
    def _(x: float):
        return "green" if x < 3.2 else "violet"

    viewer.size = (100, 100)
    table.move_iloc(57, 2)
    return viewer

@REG.register
def colormap_interpolate():
    viewer = TableViewer()
    table = viewer.add_table({"value": [-3, -2, -1, 0, 1, 2, 3]})
    table.text_color.set("value", interp_from=["blue", "gray", "red"])
    viewer.size = (100, 100)
    return viewer

@REG.register
def formatter():
    viewer = TableViewer()
    table = viewer.add_table({"length": [2.1, 3.2, 1.8, 6.3]})

    @table.formatter.set("length")
    def _(x: float):
        return f"{x:.2f} cm"
    viewer.size = (100, 100)
    return viewer

@REG.register
def validator():
    viewer = TableViewer()
    table = viewer.add_table(
        {"sample": [1, 2, 3], "volume": [0., 0., 0.]},
        editable=True,
    )

    @table.validator.set("volume")
    def _(x: float):
        if x < 0:
            raise ValueError("Volume must be positive.")

    viewer.size = (100, 100)
    table.move_iloc(1, 1)
    cmds.selection.edit_current(viewer)
    table.native._qtable_view._create_eval_editor("-1")
    return viewer

@REG.register
def cell_labels():
    viewer = TableViewer()
    sheet = viewer.add_spreadsheet(np.arange(4))
    sheet.cell[1, 1] = "&=np.mean(df.iloc[:, 0])"
    sheet.cell.label[1, 1] = "mean: "
    viewer.native.setMinimumSize(1, 1)
    viewer.size = (120, 180)
    return sheet

@REG.register
def tile_tables():
    viewer = TableViewer()
    sheet0 = viewer.add_spreadsheet(name="A")
    sheet0.cell[0:5, 0:5] = "A"
    sheet1 = viewer.add_spreadsheet(name="B")
    sheet1.cell[0:5, 0:5] = "B"
    viewer.tables.tile([0, 1])
    viewer.size = (100, 100)
    return viewer

@REG.register
def dock_with_table_data_annotation():
    from tabulous.types import TableData
    from magicgui import magicgui

    viewer = TableViewer()
    rng = np.random.default_rng(0)
    viewer.add_table(
        {"value_0": rng.normal(size=20), "value_1": rng.random(20)}
    )
    @magicgui
    def f(table: TableData, mean: bool, std: bool, max: bool, min: bool) -> TableData:
        funcs = []
        for checked, f in [(mean, np.mean), (std, np.std), (max, np.max), (min, np.min)]:
            if checked:
                funcs.append(f)
        return table.apply(funcs)

    viewer.add_dock_widget(f)
    viewer.size = (120, 180)
    return viewer

@REG.register
def column_filter():
    viewer = TableViewer()
    rng = np.random.default_rng(0)
    sheet = viewer.add_spreadsheet(
        {"A": rng.integers(0, 10, size=20),
         "B": rng.random(20).round(2)}
    )
    viewer.size = (120, 180)
    sheet.proxy.filter("A > 5")
    return viewer

@REG.register
def command_palette():
    viewer = TableViewer()
    viewer.add_spreadsheet()
    viewer.size = (100, 100)
    cmds.window.show_command_palette(viewer)
    cmdp = viewer.native._command_palette.get_widget(viewer.native)
    cmdp._line.setText("cop")
    return viewer

if __name__ == "__main__":
    REG.run_all()
