# Factorio Automation

Utilities for generating Factorio blueprints and related automation scripts.

## `run_program.py`

Generates arrays of assembling machines and can also apply modules to an existing blueprint.

### Usage

```bash
python run_program.py [--with-deps|--deps|-d] <item> <count> [<item> <count> ...] <columns>
python run_program.py --modules <module>=<count|max>
```

### Default Behavior

Creates an array of assembling machines for the provided items. The last numeric argument is the number of columns.

Example:

```bash
python run_program.py iron-plate 5 electronic-circuit 5 3
```

### Dependencies (`--deps`)

Add `--deps` to include **balanced** dependency machines so inputs keep up with the requested outputs. Counts are rounded up.

Example:

```bash
python run_program.py --deps iron-plate 5 electronic-circuit 5 3
```

### Modules (`--modules`)

Apply modules to a blueprint from the clipboard by default. Use `max` to fill all module slots. You can also read from a file using `file=<path>`.

Example:

```bash
python run_program.py --modules speed-module-1=max
python run_program.py --modules speed-module-1=max file=blueprint
```

### Help

```bash
python run_program.py --help
```
