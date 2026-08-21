"""PySide6 viewer for interactively searching a Factorio blueprint."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import pyperclip

from matplotlib import colormaps
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from convert_json_to_blueprint_string import convertoToBlueprint, convertoToJson
from standalone_whereis import BlueprintSearchIndex, PaginatedOptions


class WhereisWindow(QMainWindow):
    """Search and map a decoded blueprint with a responsive Qt interface."""

    PAGE_SIZE = 20

    def __init__(self, blueprint=None):
        super().__init__()
        self.setWindowTitle("Factorio Blueprint Whereis")
        self.resize(1350, 850)
        self.index = None
        self.pages = PaginatedOptions(self.PAGE_SIZE)
        self.selected = {}
        self.current_page_options = []
        self.plot_entities = {}

        self._build_ui()
        self._connect_signals()
        self._draw_plot()

        if blueprint is None:
            QTimer.singleShot(100, self.load_clipboard)
        else:
            self.load_blueprint(blueprint, "run_program.py")

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer = QHBoxLayout(central)
        outer.setContentsMargins(8, 8, 8, 8)

        splitter = QSplitter(Qt.Horizontal)
        outer.addWidget(splitter)

        sidebar = QFrame()
        sidebar.setMinimumWidth(390)
        sidebar.setMaximumWidth(500)
        sidebar_layout = QVBoxLayout(sidebar)

        button_row = QHBoxLayout()
        self.reload_button = QPushButton("Reload clipboard")
        self.open_button = QPushButton("Open file")
        button_row.addWidget(self.reload_button)
        button_row.addWidget(self.open_button)
        sidebar_layout.addLayout(button_row)

        self.status_label = QLabel(
            "Copy a blueprint in Factorio, then click Reload clipboard."
        )
        self.status_label.setWordWrap(True)
        self.status_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        sidebar_layout.addWidget(self.status_label)

        search_label = QLabel("Search entities, recipes, chest requests, or train routes")
        search_label.setStyleSheet("font-weight: 600; margin-top: 8px;")
        sidebar_layout.addWidget(search_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Try: construction-robot, substation, furnace…"
        )
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setMinimumHeight(36)
        sidebar_layout.addWidget(self.search_input)

        help_label = QLabel(
            "Results update as you type. Double-click a row or press Enter to "
            "add/remove it from the map."
        )
        help_label.setWordWrap(True)
        help_label.setStyleSheet("color: #666;")
        sidebar_layout.addWidget(help_label)

        self.results_table = QTableWidget(0, 4)
        self.results_table.setHorizontalHeaderLabels(["", "Name", "Type", "Count"])
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.setSelectionMode(QTableWidget.SingleSelection)
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.verticalHeader().setVisible(False)
        header = self.results_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        sidebar_layout.addWidget(self.results_table, stretch=1)

        page_row = QHBoxLayout()
        self.previous_button = QPushButton("Previous")
        self.page_label = QLabel("Page 1 of 1")
        self.page_label.setAlignment(Qt.AlignCenter)
        self.next_button = QPushButton("Next")
        page_row.addWidget(self.previous_button)
        page_row.addWidget(self.page_label, stretch=1)
        page_row.addWidget(self.next_button)
        sidebar_layout.addLayout(page_row)

        selected_label = QLabel("Plotted searches")
        selected_label.setStyleSheet("font-weight: 600; margin-top: 8px;")
        sidebar_layout.addWidget(selected_label)
        self.selected_list = QListWidget()
        self.selected_list.setMaximumHeight(130)
        sidebar_layout.addWidget(self.selected_list)

        selected_buttons = QHBoxLayout()
        self.remove_button = QPushButton("Remove selected")
        self.clear_button = QPushButton("Clear all")
        selected_buttons.addWidget(self.remove_button)
        selected_buttons.addWidget(self.clear_button)
        sidebar_layout.addLayout(selected_buttons)

        self.details_label = QLabel("Click a plotted marker to inspect it.")
        self.details_label.setWordWrap(True)
        self.details_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.details_label.setMinimumHeight(65)
        sidebar_layout.addWidget(self.details_label)

        map_panel = QWidget()
        map_layout = QVBoxLayout(map_panel)
        map_layout.setContentsMargins(0, 0, 0, 0)
        self.figure = Figure(figsize=(9, 7), dpi=100)
        self.axes = self.figure.add_subplot(111)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        map_layout.addWidget(self.toolbar)
        map_layout.addWidget(self.canvas, stretch=1)

        splitter.addWidget(sidebar)
        splitter.addWidget(map_panel)
        splitter.setSizes([420, 930])

        self.search_shortcut = QShortcut(QKeySequence.Find, self)
        self.next_page_shortcut = QShortcut(QKeySequence(Qt.Key_PageDown), self)
        self.previous_page_shortcut = QShortcut(QKeySequence(Qt.Key_PageUp), self)
        self.activate_result_shortcut = QShortcut(
            QKeySequence(Qt.Key_Return), self.results_table
        )

    def _connect_signals(self):
        self.reload_button.clicked.connect(self.load_clipboard)
        self.open_button.clicked.connect(self.load_file)
        self.search_input.textChanged.connect(self.search_changed)
        self.search_input.returnPressed.connect(self.toggle_current_result)
        self.results_table.cellDoubleClicked.connect(
            lambda row, _column: self.toggle_result(row)
        )
        self.previous_button.clicked.connect(lambda: self.change_page(-1))
        self.next_button.clicked.connect(lambda: self.change_page(1))
        self.remove_button.clicked.connect(self.remove_selected)
        self.clear_button.clicked.connect(self.clear_selected)
        self.selected_list.itemDoubleClicked.connect(lambda _item: self.remove_selected())
        self.search_shortcut.activated.connect(self.focus_search)
        self.next_page_shortcut.activated.connect(lambda: self.change_page(1))
        self.previous_page_shortcut.activated.connect(lambda: self.change_page(-1))
        self.activate_result_shortcut.activated.connect(self.toggle_current_result)
        self.canvas.mpl_connect("pick_event", self.marker_picked)

    def focus_search(self):
        self.search_input.setFocus()
        self.search_input.selectAll()

    def load_clipboard(self):
        try:
            encoded = QApplication.clipboard().text().strip()
            if not encoded.startswith("0"):
                raise ValueError("clipboard does not contain a Factorio blueprint string")
            self.load_blueprint(convertoToJson(encoded), "clipboard")
        except Exception as error:
            self.show_error("Could not load clipboard blueprint", error)

    def load_file(self):
        filename, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Open Factorio blueprint string",
            "",
            "Text files (*.txt);;All files (*.*)",
        )
        if not filename:
            return
        try:
            with open(filename, encoding="utf-8") as blueprint_file:
                encoded = blueprint_file.read().strip()
            self.load_blueprint(convertoToJson(encoded), filename)
        except Exception as error:
            self.show_error("Could not load blueprint file", error)

    def load_blueprint(self, blueprint, source):
        if not isinstance(blueprint, dict) or not isinstance(
            blueprint.get("blueprint"), dict
        ):
            raise ValueError("only a single blueprint is currently supported")

        self.index = BlueprintSearchIndex(blueprint)
        self.selected.clear()
        self.search_input.clear()
        self.pages.set_items(self.index.options)
        self.render_page()
        self.render_selected()

        bounds = self.index.bounds
        bounds_text = "no positioned entities" if bounds is None else (
            f"X {bounds['min_x']}..{bounds['max_x']}, "
            f"Y {bounds['min_y']}..{bounds['max_y']}"
        )
        self.status_label.setText(
            f"Loaded {len(self.index.entities):,} entities from {source}<br>"
            f"{len(self.index.options):,} searchable options · {bounds_text}"
        )
        self._draw_plot()
        self.focus_search()

    def show_error(self, title, error):
        self.status_label.setText(f"{title}: {error}")
        QMessageBox.warning(self, title, str(error))

    def search_changed(self, query):
        if self.index is None:
            return
        self.pages.set_items(self.index.search(query))
        self.render_page()

    def render_page(self):
        self.current_page_options = self.pages.page_items
        self.results_table.setRowCount(len(self.current_page_options))
        for row, option in enumerate(self.current_page_options):
            selected = option.key in self.selected
            indicator = QTableWidgetItem("●" if selected else "○")
            indicator.setTextAlignment(Qt.AlignCenter)
            if selected:
                color = self.color_for_key(option.key)
                indicator.setForeground(QColor.fromRgbF(*color[:3]))
            self.results_table.setItem(row, 0, indicator)
            self.results_table.setItem(row, 1, QTableWidgetItem(option.name))
            self.results_table.setItem(row, 2, QTableWidgetItem(option.kind))
            count_item = QTableWidgetItem(f"{option.count:,}")
            count_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.results_table.setItem(row, 3, count_item)

        self.page_label.setText(
            f"Page {self.pages.page + 1} of {self.pages.page_count} "
            f"({len(self.pages.items):,} options)"
        )
        self.previous_button.setEnabled(self.pages.page > 0)
        self.next_button.setEnabled(self.pages.page + 1 < self.pages.page_count)
        if self.current_page_options:
            self.results_table.selectRow(0)

    def change_page(self, amount):
        self.pages.move(amount)
        self.render_page()

    def toggle_current_result(self):
        row = self.results_table.currentRow()
        if row < 0 and self.current_page_options:
            row = 0
        self.toggle_result(row)

    def toggle_result(self, row):
        if row < 0 or row >= len(self.current_page_options):
            return
        option = self.current_page_options[row]
        if option.key in self.selected:
            del self.selected[option.key]
        else:
            self.selected[option.key] = option
        self.render_page()
        self.results_table.selectRow(row)
        self.render_selected()
        self._draw_plot()

    def render_selected(self):
        self.selected_list.clear()
        for option in self.selected.values():
            list_item = QListWidgetItem(
                f"●  {option.name} ({option.kind}, {option.count:,})"
            )
            color = self.color_for_key(option.key)
            list_item.setForeground(QColor.fromRgbF(*color[:3]))
            list_item.setData(Qt.UserRole, option.key)
            self.selected_list.addItem(list_item)

    def remove_selected(self):
        item = self.selected_list.currentItem()
        if item is None:
            return
        self.selected.pop(tuple(item.data(Qt.UserRole)), None)
        self.render_selected()
        self.render_page()
        self._draw_plot()

    def clear_selected(self):
        self.selected.clear()
        self.render_selected()
        self.render_page()
        self._draw_plot()

    def color_for_key(self, key):
        keys = list(self.selected)
        index = keys.index(key) if key in self.selected else 0
        color_map = colormaps["tab20"]
        return color_map(index % color_map.N)

    def _draw_plot(self):
        self.axes.clear()
        self.plot_entities.clear()

        if self.index and self.index.positioned_entities:
            positions = [entity["position"] for entity in self.index.positioned_entities]
            self.axes.scatter(
                [position["x"] for position in positions],
                [position["y"] for position in positions],
                s=3,
                color="#808080",
                alpha=0.16,
                label="All entities",
                rasterized=True,
            )

            for option in self.selected.values():
                entities = self.index.entities_for(option)
                if not entities:
                    continue
                collection = self.axes.scatter(
                    [entity["position"]["x"] for entity in entities],
                    [entity["position"]["y"] for entity in entities],
                    s=48,
                    color=self.color_for_key(option.key),
                    marker="x",
                    linewidths=1.8,
                    label=f"{option.name} ({option.kind})",
                    picker=5,
                )
                self.plot_entities[collection] = entities

        self.axes.set_title("Factorio blueprint search")
        self.axes.set_xlabel("X coordinate")
        self.axes.set_ylabel("Y coordinate")
        self.axes.set_aspect("equal", adjustable="datalim")
        self.axes.invert_yaxis()
        self.axes.grid(True, alpha=0.2)
        if self.selected:
            self.axes.legend(loc="best")
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def marker_picked(self, event):
        entities = self.plot_entities.get(event.artist)
        if not entities or not event.ind:
            return
        entity = entities[event.ind[0]]
        position = entity["position"]
        details = [
            f"<b>Entity #{entity.get('entity_number', '?')}</b>: "
            f"{entity.get('name', '?')}",
            f"Position: ({position['x']}, {position['y']})",
        ]
        if entity.get("recipe"):
            details.append(f"Recipe: {entity['recipe']}")
        if entity.get("items"):
            details.append(f"Items/modules: {entity['items']}")
        requested_items = BlueprintSearchIndex.requested_items(entity)
        if requested_items:
            details.append(f"Requests: {', '.join(requested_items)}")
        self.details_label.setText("<br>".join(details))


def main(blueprint=None):
    """Launch the Qt viewer, optionally with an already-decoded blueprint."""
    app = QApplication.instance()
    owns_application = app is None
    if owns_application:
        app = QApplication(sys.argv)
    app.setApplicationName("Factorio Blueprint Whereis")

    window = WhereisWindow(blueprint=blueprint)
    window.show()
    window.raise_()
    window.activateWindow()
    window.search_input.setFocus()

    if owns_application:
        return app.exec()
    return window


def launch_detached(blueprint=None):
    """Launch a separate viewer process and return immediately.

    Pass supplied blueprints through a temporary JSON file. This avoids races
    and clipboard-size issues while still copying the Factorio string for use
    in the game.
    """
    arguments = []
    temporary_filename = None
    if blueprint is not None:
        pyperclip.copy(convertoToBlueprint(blueprint))
        descriptor, temporary_filename = tempfile.mkstemp(
            prefix="factorio_whereis_", suffix=".json"
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as blueprint_file:
                json.dump(blueprint, blueprint_file)
        except Exception:
            try:
                os.close(descriptor)
            except OSError:
                pass
            try:
                os.unlink(temporary_filename)
            except OSError:
                pass
            raise
        arguments = ["--blueprint-json", temporary_filename]

    python_executable = Path(sys.executable)
    pythonw_executable = python_executable.with_name("pythonw.exe")
    if not pythonw_executable.exists():
        pythonw_executable = python_executable
    try:
        process = subprocess.Popen(
            [str(pythonw_executable), str(Path(__file__).resolve()), *arguments],
            close_fds=True,
            cwd=str(Path(__file__).resolve().parent),
        )
    except Exception:
        if temporary_filename:
            try:
                os.unlink(temporary_filename)
            except OSError:
                pass
        raise
    return process


def _blueprint_from_arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blueprint-json", help="Temporary decoded blueprint file")
    arguments = parser.parse_args()
    if not arguments.blueprint_json:
        return None

    filename = arguments.blueprint_json
    try:
        with open(filename, encoding="utf-8") as blueprint_file:
            return json.load(blueprint_file)
    finally:
        try:
            os.unlink(filename)
        except OSError:
            pass


if __name__ == "__main__":
    raise SystemExit(main(_blueprint_from_arguments()))
