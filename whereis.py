"""Helpers for locating production machines in Factorio blueprints."""


def whereis(blueprint, recipe, show_plot=True):
    """Return recipe-machine coordinates and the complete blueprint bounds.

    ``blueprint`` must be a decoded Factorio blueprint dictionary.  The
    ``recipe`` argument may be one recipe name or a list of names. Coordinates
    are kept in blueprint entity order. The returned ``bounds`` includes every
    positioned entity and is ``None`` only when the blueprint has no positioned
    entities. Set ``show_plot`` to ``False`` to skip the visualization.
    """
    entities = blueprint.get("blueprint", {}).get("entities", [])
    multiple_recipes = isinstance(recipe, (list, tuple))
    recipes = list(recipe) if multiple_recipes else [recipe]
    if not all(isinstance(item, str) and item for item in recipes):
        raise ValueError("recipe must be a name or a list of recipe names")

    coordinates_by_recipe = {
        recipe_name: [
            entity["position"].copy()
            for entity in entities
            if entity.get("name", "").startswith("assembling-machine-")
            and entity.get("recipe") == recipe_name
            and "position" in entity
        ]
        for recipe_name in recipes
    }

    all_positions = [
        entity["position"]
        for entity in entities
        if "position" in entity
        and "x" in entity["position"]
        and "y" in entity["position"]
    ]

    bounds = None
    if all_positions:
        x_coordinates = [position["x"] for position in all_positions]
        y_coordinates = [position["y"] for position in all_positions]
        bounds = {
            "min_x": min(x_coordinates),
            "max_x": max(x_coordinates),
            "min_y": min(y_coordinates),
            "max_y": max(y_coordinates),
        }

    coordinates = coordinates_by_recipe if multiple_recipes else coordinates_by_recipe[recipe]
    result = {"coordinates": coordinates, "bounds": bounds}
    print(f"{recipe} assembling-machine locations: {result}")

    if show_plot:
        _plot_locations(all_positions, coordinates_by_recipe)

    return result


def _plot_locations(all_positions, coordinates_by_recipe):
    """Plot the complete blueprint and highlight matching assemblers."""
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots()

    if all_positions:
        axes.scatter(
            [position["x"] for position in all_positions],
            [position["y"] for position in all_positions],
            s=8,
            color="gray",
            alpha=0.35,
            label="All blueprint entities",
        )

    color_map = plt.get_cmap("tab10")
    for index, (recipe, positions) in enumerate(coordinates_by_recipe.items()):
        if positions:
            axes.scatter(
                [position["x"] for position in positions],
                [position["y"] for position in positions],
                s=60,
                color=color_map(index % color_map.N),
                marker="x",
                linewidths=2,
                label=recipe,
            )

    axes.set_title("Blueprint recipe locations")
    axes.set_xlabel("X coordinate")
    axes.set_ylabel("Y coordinate")
    axes.set_aspect("equal", adjustable="datalim")
    axes.invert_yaxis()
    axes.grid(True, alpha=0.2)
    if all_positions or any(coordinates_by_recipe.values()):
        axes.legend()
    figure.tight_layout()
    plt.show()
