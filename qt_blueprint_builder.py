"""PySide6 UI for the production-station generator."""

import json
import math
import sys

import pyperclip
from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractSpinBox, QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout,
    QDialog, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton,
    QScrollArea, QSizePolicy, QSpinBox, QTextEdit, QVBoxLayout, QWidget,
)

from blueprint_builder import (
    SOLID_ORE_RESOURCES,
    build_dropoff_circuit_test,
    build_ore_pickup,
    build_product_station_array,
    build_train_depot,
    build_single_production_machine,
    build_train,
    build_repeated_blueprint,
    plan_product_stations,
)
from convert_json_to_blueprint_string import convertoToBlueprint
from make_solar_array import (
    make_solar_array,
    solar_array_dimension_stats,
    solar_array_stats,
)
from qt_whereis import launch_detached as launch_whereis
from recipe_extraction import recipes_dict, raw_materials


class BlueprintBuilderWindow(QMainWindow):
    PRODUCT_ALIASES = {
        "personal-roboport-mk2": "personal-roboport-mk2-equipment",
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Factorio Production Blueprint Builder")
        self.resize(760, 820)
        self.blueprint = None
        self.settings = QSettings(
            "factorio-software-automation", "blueprint-builder"
        )
        self._settings_save_timer = QTimer(self)
        self._settings_save_timer.setSingleShot(True)
        self._settings_save_timer.setInterval(300)
        self._settings_save_timer.timeout.connect(self._save_settings)
        self._build_ui()
        self._load_settings()
        self._connect_settings_persistence()
        self.refresh_preview()

    def _build_ui(self):
        root = QWidget()
        root.setMinimumWidth(680)
        layout = QVBoxLayout(root)

        heading = QLabel("Production station array")
        heading.setStyleSheet("font-size: 20px; font-weight: 700;")
        layout.addWidget(heading)
        description = QLabel(
            "Choose a final product, review its expanded production chain, then copy "
            "the blueprint or open it in the searchable map."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        buttons = QHBoxLayout()
        self.map_button = QPushButton("Generate and copy blueprint")
        self.copy_button = QPushButton("Copy blueprint")
        self.preview_button = QPushButton("Preview blueprint")
        self.json_button = QPushButton("View JSON")
        self.copy_button.setEnabled(False)
        self.preview_button.setEnabled(False)
        self.json_button.setEnabled(False)
        buttons.addWidget(self.map_button)
        buttons.addWidget(self.preview_button)
        buttons.addWidget(self.json_button)
        layout.addLayout(buttons)

        product_group = QGroupBox("Product")
        product_form = QFormLayout(product_group)
        product_form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.mode = QComboBox()
        self.mode.addItem("Full production station array", "production")
        self.mode.addItem("Standalone solar array", "solar-array")
        self.mode.addItem("Ore pickup only", "ore-pickup")
        self.mode.addItem("Single production machine", "single-machine")
        self.mode.addItem("Train only", "train")
        self.mode.addItem("Train depot only", "train-depot")
        self.mode.addItem("Dropoff circuit test", "dropoff-circuit-test")
        self.mode.addItem("Repeat pasted blueprint", "repeat-blueprint")
        product_form.addRow("Generation mode", self.mode)
        self.product = QComboBox()
        self.product.setEditable(True)
        products = sorted(
            {name for name in recipes_dict if name not in set(raw_materials)}
            | set(self.PRODUCT_ALIASES)
        )
        self.product.addItems(products)
        self.product.setCurrentText("advanced-circuit")
        product_form.addRow("Final product", self.product)
        self.solar_columns = self._integer(20, 1, 1000)
        self.solar_rows = self._integer(10, 1, 1000)
        product_form.addRow("Solar panel columns", self.solar_columns)
        product_form.addRow("Solar panel rows", self.solar_rows)
        self.ore_resource = QComboBox()
        self.ore_resource.addItems(SOLID_ORE_RESOURCES)
        product_form.addRow("Pickup resource", self.ore_resource)
        self.include_final = QCheckBox("Create the final-product station")
        self.include_final.setChecked(True)
        product_form.addRow("", self.include_final)
        layout.addWidget(product_group)

        options_group = QGroupBox("Station options")
        form = QFormLayout(options_group)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.roboports = self._checkbox(True)
        self.roboports_in_squares = self._checkbox(True)
        self.roboports_between_stations = self._checkbox(True)
        self.intersections = self._checkbox(True)
        self.separate_depot = QCheckBox("Put trains in separate depot")
        self.depot_only = QCheckBox("Make depot only")
        self.empty_chests = self._checkbox(True)
        self.include_trains = self._checkbox(True)
        self.trains = self._integer(1, 1, 100)
        self.rail_x_offset = self._integer(-50, -10000, 10000)
        self.mining_copies = self._integer(1, 1, 100)
        self.rail_y_offset = self._integer(0, -10000, 10000)
        self.wagon_count = self._integer(4, 1, 100)
        self.fluid_wagons = QCheckBox("Use fluid wagons instead of cargo wagons")
        self.double_ended_train = QCheckBox("Put a locomotive on both ends")
        self.x_offset = self._number(-4)
        self.y_offset = self._number(-6)
        self.signal_y_offset = self._number(1)
        self.horizontal_spacing = self._number(6, minimum=0)
        self.vertical_spacing = self._number(7, minimum=0)
        form.addRow("Include roboports", self.roboports)
        form.addRow("Place roboports in roboport squares", self.roboports_in_squares)
        form.addRow(
            "Place roboports between stations",
            self.roboports_between_stations,
        )
        form.addRow("Include rail intersections", self.intersections)
        depot_options = QWidget()
        depot_options_layout = QHBoxLayout(depot_options)
        depot_options_layout.setContentsMargins(0, 0, 0, 0)
        depot_options_layout.addWidget(self.separate_depot)
        depot_options_layout.addWidget(self.depot_only)
        depot_options_layout.addStretch()
        form.addRow("Depot output", depot_options)
        form.addRow("Empty requester chests", self.empty_chests)
        form.addRow("Include trains", self.include_trains)
        form.addRow("Trains per stop", self.trains)
        form.addRow("Rail X offset", self.rail_x_offset)
        form.addRow("Mining drill copies", self.mining_copies)
        form.addRow("Rail Y offset", self.rail_y_offset)
        form.addRow("Number of wagons", self.wagon_count)
        form.addRow("", self.fluid_wagons)
        form.addRow("", self.double_ended_train)
        form.addRow("Intersection X offset", self.x_offset)
        form.addRow("Intersection Y offset", self.y_offset)
        form.addRow("Signal Y offset", self.signal_y_offset)
        form.addRow("Horizontal spacing", self.horizontal_spacing)
        form.addRow("Vertical spacing", self.vertical_spacing)
        layout.addWidget(options_group)

        self.schedule_label = QLabel(
            "Train schedule — one line per stop: Stop name | condition | seconds"
        )
        layout.addWidget(self.schedule_label)
        self.schedule = QTextEdit()
        self.schedule.setMaximumHeight(95)
        self.schedule.setPlainText("Stop 1 | time | 5\nStop 2 | time | 5")
        self.schedule.setToolTip(
            "Conditions: time, inactivity, full, empty. Seconds default to 5."
        )
        layout.addWidget(self.schedule)

        self.pasted_label = QLabel("Factorio blueprint string to repeat")
        layout.addWidget(self.pasted_label)
        self.pasted_blueprint = QTextEdit()
        self.pasted_blueprint.setMaximumHeight(80)
        self.pasted_blueprint.setPlaceholderText("Paste a blueprint string beginning with 0…")
        layout.addWidget(self.pasted_blueprint)
        self.layout_blueprint_label = QLabel("Final product station array blueprint (layout reference)")
        layout.addWidget(self.layout_blueprint_label)
        self.layout_blueprint = QTextEdit()
        self.layout_blueprint.setMaximumHeight(80)
        self.layout_blueprint.setPlaceholderText(
            "Paste the generated final product array; its train stops set count and spacing"
        )
        layout.addWidget(self.layout_blueprint)
        self.pasted_copies = self._integer(1, 1, 100)
        self.repeat_cell_type = QComboBox()
        self.repeat_cell_type.addItem("Product/train-station slots", "product-station")
        self.repeat_cell_type.addItem("Extra-roboport slots", "roboport-station")
        self.pasted_copies_label = QLabel("Blueprint copies")
        pasted_row = QHBoxLayout()
        pasted_row.addWidget(self.pasted_copies_label)
        pasted_row.addWidget(self.pasted_copies)
        pasted_row.addWidget(self.repeat_cell_type)
        layout.addLayout(pasted_row)

        layout.addWidget(QLabel("Stations that will be generated"))
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setMinimumHeight(220)
        self.preview.setMaximumHeight(360)
        layout.addWidget(self.preview)

        self.generated_schedules_label = QLabel("Generated train schedules (JSON)")
        self.generated_schedules = QTextEdit()
        self.generated_schedules.setReadOnly(True)
        self.generated_schedules.setLineWrapMode(QTextEdit.NoWrap)
        self.generated_schedules.setMinimumHeight(180)
        self.generated_schedules.setMaximumHeight(320)
        self.generated_schedules_label.setVisible(False)
        self.generated_schedules.setVisible(False)
        layout.addWidget(self.generated_schedules_label)
        layout.addWidget(self.generated_schedules)

        self.status = QLabel("Ready")
        self.status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.status)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setWidget(root)
        scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setCentralWidget(scroll)

        self.product.currentTextChanged.connect(self.refresh_preview)
        self.mode.currentIndexChanged.connect(self.mode_changed)
        self.ore_resource.currentTextChanged.connect(self.refresh_preview)
        self.rail_x_offset.valueChanged.connect(self.refresh_preview)
        self.mining_copies.valueChanged.connect(self.refresh_preview)
        self.rail_y_offset.valueChanged.connect(self.refresh_preview)
        self.wagon_count.valueChanged.connect(self.refresh_preview)
        self.fluid_wagons.toggled.connect(self.refresh_preview)
        self.double_ended_train.toggled.connect(self.refresh_preview)
        self.schedule.textChanged.connect(self.refresh_preview)
        self.pasted_blueprint.textChanged.connect(self.refresh_preview)
        self.layout_blueprint.textChanged.connect(self.refresh_preview)
        self.pasted_copies.valueChanged.connect(self.refresh_preview)
        self.repeat_cell_type.currentIndexChanged.connect(self.refresh_preview)
        self.include_final.toggled.connect(self.refresh_preview)
        self.solar_columns.valueChanged.connect(self.refresh_preview)
        self.solar_rows.valueChanged.connect(self.refresh_preview)
        for widget in (
            self.roboports,
            self.roboports_in_squares,
            self.roboports_between_stations,
            self.intersections,
            self.separate_depot,
            self.depot_only,
            self.empty_chests,
            self.include_trains,
        ):
            widget.toggled.connect(self.refresh_preview)
        self.roboports.toggled.connect(
            lambda checked: self.roboports_in_squares.setEnabled(
                checked and self.mode.currentData() == "production"
            )
        )
        self.separate_depot.toggled.connect(self._depot_option_changed)
        self.include_trains.toggled.connect(self._train_option_changed)
        for widget in (
            self.trains,
            self.x_offset,
            self.y_offset,
            self.signal_y_offset,
            self.horizontal_spacing,
            self.vertical_spacing,
        ):
            widget.valueChanged.connect(self.refresh_preview)
        self.copy_button.clicked.connect(self.generate_and_copy)
        self.map_button.clicked.connect(self.generate_and_copy_now)
        self.preview_button.clicked.connect(self.preview_blueprint)
        self.json_button.clicked.connect(self.view_json)
        self.mode_changed()

    def _setting_widgets(self):
        return {
            "mode": self.mode,
            "product": self.product,
            "ore_resource": self.ore_resource,
            "include_final": self.include_final,
            "roboports": self.roboports,
            "roboports_in_squares": self.roboports_in_squares,
            "roboports_between_stations": self.roboports_between_stations,
            "intersections": self.intersections,
            "separate_depot": self.separate_depot,
            "depot_only": self.depot_only,
            "empty_chests": self.empty_chests,
            "include_trains": self.include_trains,
            "trains": self.trains,
            "rail_x_offset": self.rail_x_offset,
            "mining_copies": self.mining_copies,
            "rail_y_offset": self.rail_y_offset,
            "wagon_count": self.wagon_count,
            "fluid_wagons": self.fluid_wagons,
            "double_ended_train": self.double_ended_train,
            "x_offset": self.x_offset,
            "y_offset": self.y_offset,
            "signal_y_offset": self.signal_y_offset,
            "horizontal_spacing": self.horizontal_spacing,
            "vertical_spacing": self.vertical_spacing,
            "solar_columns": self.solar_columns,
            "solar_rows": self.solar_rows,
            "schedule": self.schedule,
            "pasted_blueprint": self.pasted_blueprint,
            "layout_blueprint": self.layout_blueprint,
            "pasted_copies": self.pasted_copies,
            "repeat_cell_type": self.repeat_cell_type,
        }

    def _depot_option_changed(self, checked):
        if not checked:
            self.depot_only.setChecked(False)
        self.depot_only.setEnabled(
            checked
            and self.include_trains.isChecked()
            and self.mode.currentData() == "production"
        )

    def _train_option_changed(self, checked):
        if not checked:
            self.separate_depot.setChecked(False)
        self.separate_depot.setEnabled(
            checked and self.mode.currentData() == "production"
        )
        self.depot_only.setEnabled(
            checked
            and self.separate_depot.isChecked()
            and self.mode.currentData() == "production"
        )
        if self.mode.currentData() == "production":
            self.trains.setEnabled(checked)

    def _load_settings(self):
        geometry = self.settings.value("window_geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        for name, widget in self._setting_widgets().items():
            value = self.settings.value(f"controls/{name}")
            if value is None:
                continue
            if isinstance(widget, QCheckBox):
                widget.setChecked(str(value).lower() in ("true", "1"))
            elif isinstance(widget, QSpinBox):
                widget.setValue(int(float(value)))
            elif isinstance(widget, QDoubleSpinBox):
                widget.setValue(float(value))
            elif isinstance(widget, QTextEdit):
                widget.setPlainText(str(value))
            elif isinstance(widget, QComboBox):
                index = widget.findData(value)
                if index < 0:
                    index = widget.findText(str(value))
                if index >= 0:
                    widget.setCurrentIndex(index)
                elif widget.isEditable():
                    widget.setCurrentText(str(value))

        # Apply the requested station grid once even when older spacing values
        # were restored from persistent settings.
        spacing_revision_key = "migrations/station_spacing_6_by_7"
        if not self.settings.value(spacing_revision_key, False, type=bool):
            self.horizontal_spacing.setValue(6)
            self.vertical_spacing.setValue(7)
            self.settings.setValue(spacing_revision_key, True)
            self.settings.sync()
        self.mode_changed()

    def _connect_settings_persistence(self):
        """Save changed controls even when the development reloader exits Qt."""
        schedule_save = lambda *args: self._settings_save_timer.start()
        for widget in self._setting_widgets().values():
            if isinstance(widget, QCheckBox):
                widget.toggled.connect(schedule_save)
            elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                widget.valueChanged.connect(schedule_save)
            elif isinstance(widget, QTextEdit):
                widget.textChanged.connect(schedule_save)
            elif isinstance(widget, QComboBox):
                widget.currentTextChanged.connect(schedule_save)

    def _save_settings(self):
        self.settings.setValue("window_geometry", self.saveGeometry())
        for name, widget in self._setting_widgets().items():
            if isinstance(widget, QCheckBox):
                value = widget.isChecked()
            elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                value = widget.value()
            elif isinstance(widget, QTextEdit):
                value = widget.toPlainText()
            elif isinstance(widget, QComboBox):
                value = widget.currentData()
                if value is None or widget.isEditable():
                    value = widget.currentText()
            self.settings.setValue(f"controls/{name}", value)
        self.settings.sync()

    def closeEvent(self, event):
        self._save_settings()
        super().closeEvent(event)

    @staticmethod
    def _checkbox(checked):
        widget = QCheckBox()
        widget.setChecked(checked)
        return widget

    def _selected_product(self):
        """Return the Factorio recipe ID for the editable product selection."""
        entered = self.product.currentText().strip()
        normalized = entered.casefold().replace(" ", "-")
        return self.PRODUCT_ALIASES.get(normalized, entered)

    @staticmethod
    def _make_spinbox_editable(widget):
        widget.setReadOnly(False)
        widget.lineEdit().setReadOnly(False)
        widget.setKeyboardTracking(True)
        widget.setAccelerated(True)
        widget.setCorrectionMode(
            QAbstractSpinBox.CorrectionMode.CorrectToNearestValue
        )
        widget.setToolTip(
            "Type a value and press Enter, or use the up/down arrow buttons."
        )
        return widget

    @classmethod
    def _integer(cls, value, minimum, maximum):
        widget = QSpinBox()
        widget.setRange(minimum, maximum)
        widget.setValue(value)
        return cls._make_spinbox_editable(widget)

    @classmethod
    def _number(cls, value, minimum=-10000):
        widget = QDoubleSpinBox()
        widget.setRange(minimum, 10000)
        widget.setDecimals(1)
        widget.setValue(value)
        return cls._make_spinbox_editable(widget)

    def refresh_preview(self):
        self.blueprint = None
        self.copy_button.setEnabled(False)
        self.preview_button.setEnabled(False)
        self.json_button.setEnabled(False)
        self.generated_schedules.clear()
        self.generated_schedules_label.setVisible(False)
        self.generated_schedules.setVisible(False)
        try:
            if self.mode.currentData() == "solar-array":
                stats = solar_array_dimension_stats(
                    self.solar_columns.value(), self.solar_rows.value()
                )
                self.preview.setPlainText(
                    f'{stats["solar_panels"]} solar panels\n'
                    f'{stats["substations"]} substations\n'
                    f'{stats["peak_output_mw"]:g} MW peak output'
                )
                self.status.setText("Standalone solar array ready to generate")
                return
            if self.mode.currentData() == "ore-pickup":
                resource = self.ore_resource.currentText()
                self.preview.setPlainText(
                    f"Standalone {resource} pickup\n"
                    f"{self.mining_copies.value()} mining module(s) in a square grid, "
                    f"Rail X offset: {self.rail_x_offset.value()} tiles\n"
                    f"Rail Y offset: {self.rail_y_offset.value()} tiles\n"
                    "Powered roboport corridor · 24 requester chests · 1 train stop"
                )
                self.status.setText(f"{resource} pickup ready to generate")
                return
            if self.mode.currentData() == "single-machine":
                recipe = self._selected_product()
                if recipe not in recipes_dict:
                    raise ValueError(f"Unknown recipe: {recipe}")
                self.preview.setPlainText(
                    f"One production machine for {recipe}\n"
                    "Includes requester/provider chests, inserters, modules, and power."
                )
                self.status.setText(f"Single {recipe} machine ready to generate")
                return
            if self.mode.currentData() == "train":
                wagon_type = "fluid" if self.fluid_wagons.isChecked() else "cargo"
                locomotive_count = 2 if self.double_ended_train.isChecked() else 1
                self.preview.setPlainText(
                    f"{locomotive_count} locomotive(s) with "
                    f"{self.wagon_count.value()} {wagon_type} wagon(s)\n"
                    "Schedule conditions: time, inactivity, full, or empty"
                )
                self.status.setText("Train ready to generate and preview")
                return
            if self.mode.currentData() == "train-depot":
                self.preview.setPlainText(
                    "Standalone square train depot\n"
                    "14 fueled trains in 14 rail bays"
                )
                self.status.setText("Square train depot ready to generate")
                return
            if self.mode.currentData() == "dropoff-circuit-test":
                self.preview.setPlainText(
                    "One drop-off train stop on six straight rails\n"
                    "One bulk inserter unloading into an active-provider chest\n"
                    "Red circuit wire: train stop signal T > 0 enables inserter\n"
                    "The inserter remains disabled until a train is stopped"
                )
                self.status.setText("Dropoff circuit test ready to generate")
                return
            if self.mode.currentData() == "repeat-blueprint":
                using_array = bool(self.layout_blueprint.toPlainText().strip())
                self.pasted_copies.setEnabled(not using_array)
                self.horizontal_spacing.setEnabled(not using_array)
                self.vertical_spacing.setEnabled(not using_array)
                repeat_summary = (
                    "One copy at every train stop in the pasted final product array\n"
                    if using_array
                    else f"{self.pasted_copies.value()} pasted blueprint copy/copies in a square grid\n"
                )
                self.preview.setPlainText(
                    repeat_summary
                    + ("Count and coordinates come directly from its train stops"
                       if using_array else
                       f"Final-array target: {self.repeat_cell_type.currentText()}\n"
                       f"Roboport rows: {'included' if self.roboports.isChecked() else 'not included'}\n"
                       f"Spacing: X {self.horizontal_spacing.value()}, Y {self.vertical_spacing.value()}")
                )
                self.status.setText("Paste a blueprint, then generate and preview")
                return
            stations = plan_product_stations(
                self._selected_product(),
                self.include_final.isChecked(),
                self.trains.value(),
            )
            columns = math.ceil(math.sqrt(len(stations)))
            numbered = []
            for index, station in enumerate(stations):
                logical_row, column = divmod(index, columns)
                grid_row = logical_row * 2 + 2 if self.roboports.isChecked() else logical_row + 1
                endpoint_names = ", ".join(
                    endpoint.station_name for endpoint in station.endpoints.values()
                )
                numbered.append(
                    f"Grid row {grid_row}, column {column + 1}: {station.id}\n"
                    f"  {endpoint_names}"
                )
            if self.depot_only.isChecked():
                numbered.insert(
                    0,
                    "Depot-only output: scheduled trains with upward-running rails\n",
                )
            self.preview.setPlainText("\n".join(numbered))
            self.status.setText(f"{len(stations)} stations ready to generate")
        except Exception as error:
            self.preview.setPlainText(str(error))
            self.status.setText("Choose a valid recipe")

    def mode_changed(self):
        production_mode = self.mode.currentData() == "production"
        solar_mode = self.mode.currentData() == "solar-array"
        single_mode = self.mode.currentData() == "single-machine"
        train_mode = self.mode.currentData() == "train"
        repeat_mode = self.mode.currentData() == "repeat-blueprint"
        self.product.setEnabled(production_mode or single_mode)
        self.include_final.setEnabled(production_mode)
        self.include_trains.setEnabled(production_mode)
        self.separate_depot.setEnabled(
            production_mode and self.include_trains.isChecked()
        )
        self.depot_only.setEnabled(
            production_mode
            and self.include_trains.isChecked()
            and self.separate_depot.isChecked()
        )
        self.ore_resource.setEnabled(not production_mode)
        self.ore_resource.setEnabled(self.mode.currentData() == "ore-pickup")
        self.trains.setEnabled(
            (production_mode and self.include_trains.isChecked())
            or self.mode.currentData() == "ore-pickup"
        )
        self.rail_x_offset.setEnabled(self.mode.currentData() == "ore-pickup")
        self.mining_copies.setEnabled(self.mode.currentData() == "ore-pickup")
        self.rail_y_offset.setEnabled(self.mode.currentData() == "ore-pickup")
        self.wagon_count.setEnabled(train_mode)
        self.fluid_wagons.setEnabled(train_mode)
        self.double_ended_train.setEnabled(train_mode)
        self.schedule_label.setVisible(train_mode)
        self.schedule.setVisible(train_mode)
        self.pasted_label.setVisible(repeat_mode)
        self.pasted_blueprint.setVisible(repeat_mode)
        self.layout_blueprint_label.setVisible(repeat_mode)
        self.layout_blueprint.setVisible(repeat_mode)
        self.pasted_copies_label.setVisible(repeat_mode)
        self.pasted_copies.setVisible(repeat_mode)
        self.repeat_cell_type.setVisible(repeat_mode)
        for widget in (
            self.intersections,
            self.empty_chests,
            self.x_offset,
            self.y_offset,
            self.signal_y_offset,
            self.horizontal_spacing,
            self.vertical_spacing,
        ):
            widget.setEnabled(production_mode or (
                repeat_mode and widget in (self.horizontal_spacing, self.vertical_spacing)
            ))
        self.roboports.setEnabled(production_mode or repeat_mode)
        self.roboports_in_squares.setEnabled(
            production_mode and self.roboports.isChecked()
        )
        self.roboports_between_stations.setEnabled(production_mode)
        self.solar_columns.setEnabled(solar_mode)
        self.solar_rows.setEnabled(solar_mode)
        self.refresh_preview()

    def _generate(self):
        self.status.setText("Generating blueprint…")
        QApplication.processEvents()
        if self.mode.currentData() == "solar-array":
            self.blueprint = make_solar_array(
                self.solar_columns.value(), self.solar_rows.value()
            )
            return ["solar array"]
        if self.mode.currentData() == "ore-pickup":
            resource = self.ore_resource.currentText()
            self.blueprint = build_ore_pickup(
                resource,
                trains_per_stop=self.trains.value(),
                rail_x_offset=self.rail_x_offset.value(),
                mining_copies=self.mining_copies.value(),
                rail_y_offset=self.rail_y_offset.value(),
            )
            return [resource]
        if self.mode.currentData() == "single-machine":
            recipe = self._selected_product()
            self.blueprint = build_single_production_machine(recipe)
            return [recipe]
        if self.mode.currentData() == "train":
            self.blueprint = build_train(
                self.wagon_count.value(),
                fluid_wagons=self.fluid_wagons.isChecked(),
                double_ended=self.double_ended_train.isChecked(),
                schedule_text=self.schedule.toPlainText(),
            )
            return ["train"]
        if self.mode.currentData() == "train-depot":
            self.blueprint = build_train_depot()
            return ["train depot"]
        if self.mode.currentData() == "dropoff-circuit-test":
            self.blueprint = build_dropoff_circuit_test()
            return ["dropoff circuit test"]
        if self.mode.currentData() == "repeat-blueprint":
            self.blueprint = build_repeated_blueprint(
                self.pasted_blueprint.toPlainText(),
                self.pasted_copies.value(),
                layout_blueprint_string=self.layout_blueprint.toPlainText(),
                horizontal_spacing=self.horizontal_spacing.value(),
                vertical_spacing=self.vertical_spacing.value(),
                cell_type=self.repeat_cell_type.currentData(),
                include_roboports=self.roboports.isChecked(),
            )
            return ["pasted blueprint"]
        self.blueprint, ingredients = build_product_station_array(
            self._selected_product(),
            include_final_product=self.include_final.isChecked(),
            include_roboports=self.roboports.isChecked(),
            place_roboports_in_squares=self.roboports_in_squares.isChecked(),
            place_roboports_between_stations=(
                self.roboports_between_stations.isChecked()
            ),
            include_intersections=self.intersections.isChecked(),
            intersection_x_offset=self.x_offset.value(),
            intersection_y_offset=self.y_offset.value(),
            intersection_signal_y_offset=self.signal_y_offset.value(),
            empty_requester_chests=self.empty_chests.isChecked(),
            include_trains=self.include_trains.isChecked(),
            trains_per_stop=self.trains.value(),
            horizontal_spacing=self.horizontal_spacing.value(),
            vertical_spacing=self.vertical_spacing.value(),
            separate_train_depot=self.separate_depot.isChecked(),
            depot_only=self.depot_only.isChecked(),
        )
        return ingredients

    def generate_and_copy(self):
        try:
            if self.blueprint is None:
                raise ValueError("Generate the blueprint first")
            pyperclip.copy(convertoToBlueprint(self.blueprint))
            self.status.setText("Copied the generated blueprint")
        except Exception as error:
            QMessageBox.warning(self, "Blueprint required", str(error))
            self.status.setText("Generate the blueprint before copying")

    def generate_and_copy_now(self):
        """Generate the current selection and immediately copy its blueprint string."""
        self.generate_only()
        if self.blueprint is None:
            return
        pyperclip.copy(convertoToBlueprint(self.blueprint))
        self.status.setText(f"{self.status.text()}; copied to clipboard")

    def generate_only(self):
        self.blueprint = None
        try:
            ingredients = self._generate()
            self._show_generated_schedules()
            self.copy_button.setEnabled(True)
            self.preview_button.setEnabled(True)
            self.json_button.setEnabled(True)
            if self.mode.currentData() == "solar-array":
                stats = solar_array_stats(self.blueprint)
                self.status.setText(
                    f'Generated standalone solar array — '
                    f'{stats["peak_output_mw"]:g} MW peak; ready to copy or preview'
                )
            elif self.mode.currentData() != "production":
                self.status.setText(
                    f"Generated {ingredients[0]} {self.mode.currentText().lower()} — ready to copy or preview"
                )
            else:
                self._show_generated_station_locations()
                self.status.setText(
                    f"Generated {len(ingredients)} stations — ready to copy or preview"
                )
        except Exception as error:
            QMessageBox.critical(self, "Could not generate blueprint", str(error))
            self.status.setText("Generation failed")

    def _show_generated_schedules(self):
        schedules = self.blueprint.get("blueprint", {}).get("schedules", [])
        self.generated_schedules.setPlainText(
            json.dumps(schedules, indent=2, sort_keys=True)
        )
        has_schedules = bool(schedules)
        self.generated_schedules_label.setVisible(has_schedules)
        self.generated_schedules.setVisible(has_schedules)

    def _show_generated_station_locations(self):
        """List generated train-stop names at their exact blueprint positions."""
        stops = sorted(
            (
                entity
                for entity in self.blueprint.get("blueprint", {}).get("entities", [])
                if entity.get("name") == "train-stop" and entity.get("station")
            ),
            key=lambda entity: (
                entity["position"]["y"],
                entity["position"]["x"],
                entity["station"],
            ),
        )
        lines = []
        for stop in stops:
            position = stop["position"]
            kind = "midpoint" if stop["station"].endswith(" midpoint") else "stop"
            lines.append(
                f'{stop["station"]} — {kind} at '
                f'({position["x"]:g}, {position["y"]:g})'
            )
        self.preview.setPlainText("\n".join(lines) if lines else "No train stops generated")

    def preview_blueprint(self):
        try:
            if self.blueprint is None:
                raise ValueError("Generate the blueprint first")
            launch_whereis(self.blueprint)
            self.status.setText("Previewing the generated blueprint")
        except Exception as error:
            QMessageBox.warning(self, "Blueprint required", str(error))
            self.status.setText("Generate the blueprint before previewing")

    def view_json(self):
        try:
            if self.blueprint is None:
                raise ValueError("Generate the blueprint first")
            dialog = QDialog(self)
            dialog.setWindowTitle("Generated blueprint JSON")
            dialog.resize(1000, 760)
            layout = QVBoxLayout(dialog)
            viewer = QTextEdit()
            viewer.setReadOnly(True)
            viewer.setLineWrapMode(QTextEdit.NoWrap)
            viewer.setPlainText(json.dumps(self.blueprint, indent=2, sort_keys=True))
            search_row = QHBoxLayout()
            search_box = QLineEdit()
            search_box.setPlaceholderText("Find station, entity, or value...")
            find_next = QPushButton("Find next")
            find_next.clicked.connect(lambda: viewer.find(search_box.text()))
            search_box.returnPressed.connect(find_next.click)
            search_row.addWidget(search_box)
            search_row.addWidget(find_next)
            layout.addLayout(search_row)
            layout.addWidget(viewer)
            close_button = QPushButton("Close")
            close_button.clicked.connect(dialog.accept)
            layout.addWidget(close_button)
            dialog.exec()
        except Exception as error:
            QMessageBox.warning(self, "Blueprint required", str(error))
            self.status.setText("Generate the blueprint before viewing JSON")


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    window = BlueprintBuilderWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
