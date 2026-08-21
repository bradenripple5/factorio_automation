"""Interactive search viewer for the Factorio blueprint on the clipboard."""

from collections import Counter
from dataclasses import dataclass
import math

from convert_json_to_blueprint_string import convertoToJson


@dataclass(frozen=True, order=True)
class SearchOption:
    """One searchable entity, recipe, requested item, or train route."""

    kind: str
    name: str
    count: int

    @property
    def key(self):
        return self.kind, self.name


class BlueprintSearchIndex:
    """Searchable, GUI-independent index of a decoded blueprint."""

    def __init__(self, blueprint):
        self.blueprint = blueprint
        self.entities = blueprint.get("blueprint", {}).get("entities", [])
        self.positioned_entities = [
            entity
            for entity in self.entities
            if isinstance(entity.get("position"), dict)
            and "x" in entity["position"]
            and "y" in entity["position"]
        ]
        self.entities_by_number = {
            entity["entity_number"]: entity
            for entity in self.positioned_entities
            if "entity_number" in entity
        }
        self.route_entities = {}
        route_counts = Counter()
        for schedule in blueprint.get("blueprint", {}).get("schedules", []):
            value = schedule.get("schedule", {})
            records = value.get("records", []) if isinstance(value, dict) else value
            stops = []
            for record in records:
                station = record.get("station", "").removesuffix(" midpoint")
                if station and (not stops or station != stops[-1]):
                    stops.append(station)
            if len(stops) < 2:
                continue
            route_name = f"{stops[0]} -> {stops[-1]}"
            route_counts[route_name] += 1
            locomotives = [
                self.entities_by_number[number]
                for number in schedule.get("locomotives", [])
                if number in self.entities_by_number
            ]
            self.route_entities.setdefault(route_name, []).extend(locomotives)

        entity_counts = Counter(
            entity["name"] for entity in self.entities if entity.get("name")
        )
        recipe_counts = Counter(
            entity["recipe"] for entity in self.entities if entity.get("recipe")
        )
        request_counts = Counter(
            requested_item
            for entity in self.entities
            for requested_item in self.requested_items(entity)
        )
        self.options = sorted(
            [SearchOption("entity", name, count) for name, count in entity_counts.items()]
            + [SearchOption("recipe", name, count) for name, count in recipe_counts.items()]
            + [SearchOption("request", name, count) for name, count in request_counts.items()]
            + [SearchOption("route", name, count) for name, count in route_counts.items()],
            key=lambda option: (option.name.casefold(), option.kind),
        )
        self._option_by_key = {option.key: option for option in self.options}

    @staticmethod
    def requested_items(entity):
        """Return the distinct item names requested by one logistics chest."""
        request_filters = entity.get("request_filters")
        if not isinstance(request_filters, dict):
            return []

        filters = list(request_filters.get("filters", []))
        for section in request_filters.get("sections", []):
            if isinstance(section, dict):
                filters.extend(section.get("filters", []))
        return sorted(
            {
                item_filter["name"]
                for item_filter in filters
                if isinstance(item_filter, dict) and item_filter.get("name")
            }
        )

    @property
    def bounds(self):
        if not self.positioned_entities:
            return None
        x_values = [entity["position"]["x"] for entity in self.positioned_entities]
        y_values = [entity["position"]["y"] for entity in self.positioned_entities]
        return {
            "min_x": min(x_values),
            "max_x": max(x_values),
            "min_y": min(y_values),
            "max_y": max(y_values),
        }

    def search(self, query):
        """Return catalog options matching every whitespace-separated term."""
        terms = query.casefold().split()
        if not terms:
            return self.options.copy()

        matches = [
            option
            for option in self.options
            if all(term in f"{option.kind} {option.name}".casefold() for term in terms)
        ]
        return sorted(
            matches,
            key=lambda option: (
                not option.name.casefold().startswith(terms[0]),
                option.name.casefold(),
                option.kind,
            ),
        )

    def entities_for(self, option_or_key):
        """Return positioned entities matching a search option."""
        option = (
            self._option_by_key[option_or_key]
            if isinstance(option_or_key, tuple)
            else option_or_key
        )
        if option.kind == "request":
            return [
                entity
                for entity in self.positioned_entities
                if option.name in self.requested_items(entity)
            ]
        if option.kind == "route":
            return self.route_entities.get(option.name, []).copy()
        field = "name" if option.kind == "entity" else "recipe"
        return [
            entity
            for entity in self.positioned_entities
            if entity.get(field) == option.name
        ]


class PaginatedOptions:
    """Small pagination model used by the live-search results."""

    def __init__(self, page_size=20):
        self.page_size = page_size
        self.items = []
        self.page = 0

    @property
    def page_count(self):
        return max(1, math.ceil(len(self.items) / self.page_size))

    @property
    def page_items(self):
        start = self.page * self.page_size
        return self.items[start:start + self.page_size]

    def set_items(self, items):
        self.items = list(items)
        self.page = 0

    def move(self, amount):
        self.page = min(max(self.page + amount, 0), self.page_count - 1)


class WhereisApp:
    """Tkinter application that searches and plots clipboard blueprints."""

    PAGE_SIZE = 20

    def __init__(self, root, blueprint=None):
        import tkinter as tk
        from tkinter import ttk
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
        from matplotlib.figure import Figure

        self.root = root
        self.root.title("Factorio Blueprint Whereis")
        self.root.geometry("1250x800")
        self.index = None
        self.pages = PaginatedOptions(self.PAGE_SIZE)
        self.selected = {}
        self.current_page_options = []
        self.plot_entities = {}

        outer = ttk.Frame(root, padding=8)
        outer.pack(fill=tk.BOTH, expand=True)
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(0, weight=1)

        sidebar = ttk.Frame(outer, width=360)
        sidebar.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        sidebar.grid_propagate(False)
        sidebar.columnconfigure(0, weight=1)
        sidebar.rowconfigure(4, weight=1)

        controls = ttk.Frame(sidebar)
        controls.grid(row=0, column=0, sticky="ew")
        ttk.Button(controls, text="Reload clipboard", command=self.load_clipboard).pack(
            side=tk.LEFT
        )
        ttk.Button(controls, text="Open file", command=self.load_file).pack(
            side=tk.LEFT, padx=(6, 0)
        )

        self.status = tk.StringVar(value="Copy a blueprint in Factorio, then reload.")
        ttk.Label(sidebar, textvariable=self.status, wraplength=345).grid(
            row=1, column=0, sticky="ew", pady=(8, 8)
        )

        self.query = tk.StringVar()
        ttk.Label(sidebar, text="Search entities or recipes:").grid(
            row=2, column=0, sticky="w", pady=(0, 3)
        )
        search_entry = ttk.Entry(sidebar, textvariable=self.query)
        search_entry.grid(row=3, column=0, sticky="ew", pady=(0, 6), ipady=4)
        search_entry.bind("<KeyRelease>", self._search_changed)
        search_entry.bind("<Return>", self._toggle_focused)
        search_entry.bind("<Next>", lambda _event: self._change_page(1))
        search_entry.bind("<Prior>", lambda _event: self._change_page(-1))

        results_frame = ttk.LabelFrame(
            sidebar, text="Search options — double-click or press Enter to plot"
        )
        results_frame.grid(row=4, column=0, sticky="nsew")
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        self.results = tk.Listbox(results_frame, exportselection=False)
        self.results.grid(row=0, column=0, sticky="nsew")
        result_scroll = ttk.Scrollbar(
            results_frame, orient=tk.VERTICAL, command=self.results.yview
        )
        result_scroll.grid(row=0, column=1, sticky="ns")
        self.results.configure(yscrollcommand=result_scroll.set)
        self.results.bind("<Double-Button-1>", self._toggle_focused)
        self.results.bind("<Return>", self._toggle_focused)

        pagination = ttk.Frame(sidebar)
        pagination.grid(row=5, column=0, sticky="ew", pady=6)
        ttk.Button(pagination, text="Previous", command=lambda: self._change_page(-1)).pack(
            side=tk.LEFT
        )
        self.page_label = tk.StringVar(value="Page 1 of 1")
        ttk.Label(pagination, textvariable=self.page_label).pack(
            side=tk.LEFT, expand=True
        )
        ttk.Button(pagination, text="Next", command=lambda: self._change_page(1)).pack(
            side=tk.RIGHT
        )

        selected_frame = ttk.LabelFrame(sidebar, text="Plotted searches")
        selected_frame.grid(row=6, column=0, sticky="ew")
        selected_frame.columnconfigure(0, weight=1)
        self.selected_list = tk.Listbox(selected_frame, height=6, exportselection=False)
        self.selected_list.grid(row=0, column=0, columnspan=2, sticky="ew")
        ttk.Button(selected_frame, text="Remove", command=self._remove_selected).grid(
            row=1, column=0, sticky="ew", pady=(4, 0)
        )
        ttk.Button(selected_frame, text="Clear", command=self._clear_selected).grid(
            row=1, column=1, sticky="ew", pady=(4, 0)
        )

        self.details = tk.StringVar(value="Click a plotted marker to inspect it.")
        ttk.Label(sidebar, textvariable=self.details, wraplength=345).grid(
            row=7, column=0, sticky="ew", pady=(8, 0)
        )

        map_frame = ttk.Frame(outer)
        map_frame.grid(row=0, column=1, sticky="nsew")
        self.figure = Figure(figsize=(9, 7), dpi=100)
        self.axes = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=map_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        toolbar = NavigationToolbar2Tk(self.canvas, map_frame, pack_toolbar=False)
        toolbar.update()
        toolbar.pack(fill=tk.X)
        self.canvas.mpl_connect("pick_event", self._marker_picked)
        self._draw_plot()
        search_entry.focus_set()
        if blueprint is None:
            root.after(150, self.load_clipboard)
        else:
            root.after(150, lambda: self._load_blueprint(blueprint, "run_program.py"))

    def load_clipboard(self):
        try:
            encoded = self.root.clipboard_get().strip()
            self._load_encoded(encoded, "clipboard")
        except Exception as error:
            self.status.set(f"Could not load clipboard blueprint: {error}")

    def load_file(self):
        from tkinter import filedialog

        filename = filedialog.askopenfilename(
            title="Open Factorio blueprint string",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not filename:
            return
        try:
            with open(filename, encoding="utf-8") as blueprint_file:
                self._load_encoded(blueprint_file.read().strip(), filename)
        except Exception as error:
            self.status.set(f"Could not load blueprint file: {error}")

    def _load_encoded(self, encoded, source):
        if not encoded.startswith("0"):
            raise ValueError("clipboard does not contain a Factorio blueprint string")
        blueprint = convertoToJson(encoded)
        self._load_blueprint(blueprint, source)

    def _load_blueprint(self, blueprint, source):
        if not isinstance(blueprint.get("blueprint"), dict):
            raise ValueError("only a single blueprint is currently supported")
        self.index = BlueprintSearchIndex(blueprint)
        self.selected.clear()
        self.query.set("")
        self.pages.set_items(self.index.options)
        self._render_page()
        self._render_selected()
        bounds = self.index.bounds
        bounds_text = "no positioned entities" if bounds is None else (
            f"X {bounds['min_x']}..{bounds['max_x']}, "
            f"Y {bounds['min_y']}..{bounds['max_y']}"
        )
        self.status.set(
            f"Loaded {len(self.index.entities):,} entities from {source}; "
            f"{len(self.index.options):,} searchable options; {bounds_text}."
        )
        self._draw_plot()

    def _search_changed(self, _event=None):
        if self.index is None:
            return
        self.pages.set_items(self.index.search(self.query.get()))
        self._render_page()

    def _render_page(self):
        self.results.delete(0, "end")
        self.current_page_options = self.pages.page_items
        for option in self.current_page_options:
            marker = "●" if option.key in self.selected else " "
            self.results.insert(
                "end",
                f"[{marker}] {option.name}  —  {option.kind}, {option.count:,}",
            )
        self.page_label.set(
            f"Page {self.pages.page + 1} of {self.pages.page_count} "
            f"({len(self.pages.items):,} options)"
        )

    def _change_page(self, amount):
        self.pages.move(amount)
        self._render_page()

    def _toggle_focused(self, _event=None):
        selection = self.results.curselection()
        if not selection:
            return "break"
        option = self.current_page_options[selection[0]]
        if option.key in self.selected:
            del self.selected[option.key]
        else:
            self.selected[option.key] = option
        self._render_page()
        self.results.selection_set(selection[0])
        self._render_selected()
        self._draw_plot()
        return "break"

    def _render_selected(self):
        self.selected_list.delete(0, "end")
        for option in self.selected.values():
            self.selected_list.insert(
                "end", f"{option.name} ({option.kind}, {option.count:,})"
            )

    def _remove_selected(self):
        selection = self.selected_list.curselection()
        if not selection:
            return
        key = list(self.selected)[selection[0]]
        del self.selected[key]
        self._render_selected()
        self._render_page()
        self._draw_plot()

    def _clear_selected(self):
        self.selected.clear()
        self._render_selected()
        self._render_page()
        self._draw_plot()

    def _draw_plot(self):
        from matplotlib import colormaps

        self.axes.clear()
        self.plot_entities.clear()
        if self.index and self.index.positioned_entities:
            positions = [entity["position"] for entity in self.index.positioned_entities]
            self.axes.scatter(
                [position["x"] for position in positions],
                [position["y"] for position in positions],
                s=3,
                color="#808080",
                alpha=0.18,
                label="All entities",
                rasterized=True,
            )

            color_map = colormaps["tab20"]
            for index, option in enumerate(self.selected.values()):
                entities = self.index.entities_for(option)
                if not entities:
                    continue
                collection = self.axes.scatter(
                    [entity["position"]["x"] for entity in entities],
                    [entity["position"]["y"] for entity in entities],
                    s=45,
                    color=color_map(index % color_map.N),
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

    def _marker_picked(self, event):
        entities = self.plot_entities.get(event.artist)
        if not entities or not event.ind:
            return
        entity = entities[event.ind[0]]
        position = entity["position"]
        details = [
            f"Entity #{entity.get('entity_number', '?')}: {entity.get('name', '?')}",
            f"Position: ({position['x']}, {position['y']})",
        ]
        if entity.get("recipe"):
            details.append(f"Recipe: {entity['recipe']}")
        if entity.get("items"):
            details.append(f"Items/modules: {entity['items']}")
        self.details.set("\n".join(details))


def main(blueprint=None):
    import tkinter as tk

    root = tk.Tk()
    WhereisApp(root, blueprint=blueprint)
    root.lift()
    root.focus_force()
    root.attributes("-topmost", True)
    root.after(800, lambda: root.attributes("-topmost", False))
    root.mainloop()


if __name__ == "__main__":
    main()
