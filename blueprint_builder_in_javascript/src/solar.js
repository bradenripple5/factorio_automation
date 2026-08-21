const PANEL_SIZE = 3;
const SUPPLY_DIAMETER = 18;
const OUTPUT_KW = 60;

function validate(columns, rows) {
  if (!Number.isInteger(columns) || !Number.isInteger(rows) || columns < 1 || rows < 1) {
    throw new Error("Columns and rows must be positive integers");
  }
}

function axisPositions(length) {
  const count = Math.max(1, Math.ceil(length / SUPPLY_DIAMETER));
  if (count === 1) return [Math.floor(length / 2 + 0.5)];
  const first = SUPPLY_DIAMETER / 2;
  const last = length - SUPPLY_DIAMETER / 2;
  return Array.from({ length: count }, (_, index) =>
    Math.round(first + (index * (last - first)) / (count - 1)),
  );
}

function layout(columns, rows) {
  validate(columns, rows);
  const xs = axisPositions(columns * PANEL_SIZE);
  const ys = axisPositions(rows * PANEL_SIZE);
  const poles = ys.flatMap((y) => xs.map((x) => [x, y]));
  const blocked = new Set();
  for (const [x, y] of poles) {
    const approximateColumn = Math.floor(x / PANEL_SIZE);
    const approximateRow = Math.floor(y / PANEL_SIZE);
    for (let row = Math.max(0, approximateRow - 2); row < Math.min(rows, approximateRow + 3); row += 1) {
      for (let column = Math.max(0, approximateColumn - 2); column < Math.min(columns, approximateColumn + 3); column += 1) {
        const panelX = column * PANEL_SIZE + 1.5;
        const panelY = row * PANEL_SIZE + 1.5;
        if (Math.abs(panelX - x) < 2.5 && Math.abs(panelY - y) < 2.5) blocked.add(`${column},${row}`);
      }
    }
  }
  return { xs, ys, poles, blocked };
}

export function solarStats(columns, rows) {
  const { poles, blocked } = layout(columns, rows);
  const solarPanels = columns * rows - blocked.size;
  return { solarPanels, substations: poles.length, peakOutputMw: (solarPanels * OUTPUT_KW) / 1000 };
}

export function makeSolarArray(columns, rows) {
  const { xs, ys, blocked } = layout(columns, rows);
  const stats = solarStats(columns, rows);
  const entities = [];
  for (let row = 0; row < rows; row += 1) {
    for (let column = 0; column < columns; column += 1) {
      if (!blocked.has(`${column},${row}`)) {
        entities.push({ entity_number: entities.length + 1, name: "solar-panel", position: { x: column * 3 + 1.5, y: row * 3 + 1.5 } });
      }
    }
  }
  const firstPole = entities.length + 1;
  ys.forEach((y, row) => xs.forEach((x, column) => {
    const number = firstPole + row * xs.length + column;
    const neighbours = [];
    if (column > 0) neighbours.push(number - 1);
    if (column + 1 < xs.length) neighbours.push(number + 1);
    if (row > 0) neighbours.push(number - xs.length);
    if (row + 1 < ys.length) neighbours.push(number + xs.length);
    entities.push({ entity_number: number, name: "substation", position: { x, y }, ...(neighbours.length ? { neighbours } : {}) });
  }));
  return { blueprint: { item: "blueprint", label: `Solar array ${columns}x${rows} - ${stats.peakOutputMw} MW`, version: 562949955780608, icons: [
    { signal: { type: "item", name: "solar-panel" }, index: 1 },
    { signal: { type: "item", name: "substation" }, index: 2 },
  ], entities } };
}
