import "./style.css";
import { encodeBlueprint } from "./codec.js";
import { makeSolarArray, solarStats } from "./solar.js";

document.querySelector("#app").innerHTML = `
  <section class="card">
    <p class="eyebrow">Factorio automation</p>
    <h1>Blueprint Builder</h1>
    <label>Generation mode
      <select id="mode"><option value="solar">Standalone solar array</option></select>
    </label>
    <div class="dimensions">
      <label>Panel columns <input id="columns" type="number" min="1" max="1000" value="20"></label>
      <label>Panel rows <input id="rows" type="number" min="1" max="1000" value="10"></label>
    </div>
    <output id="stats"></output>
    <button id="generate">Generate and copy blueprint</button>
    <p id="status" role="status">Ready</p>
    <details><summary>Blueprint string</summary><textarea id="result" readonly></textarea></details>
  </section>`;

const columns = document.querySelector("#columns");
const rows = document.querySelector("#rows");
const statsOutput = document.querySelector("#stats");
const status = document.querySelector("#status");
const result = document.querySelector("#result");

function dimensions() {
  return [Number.parseInt(columns.value, 10), Number.parseInt(rows.value, 10)];
}

function refresh() {
  try {
    const stats = solarStats(...dimensions());
    statsOutput.textContent = `${stats.solarPanels.toLocaleString()} panels · ${stats.substations.toLocaleString()} substations · ${stats.peakOutputMw.toLocaleString()} MW peak`;
    status.textContent = "Ready";
  } catch (error) {
    statsOutput.textContent = error.message;
  }
}

columns.addEventListener("input", refresh);
rows.addEventListener("input", refresh);
document.querySelector("#generate").addEventListener("click", async () => {
  try {
    status.textContent = "Generating…";
    const encoded = await encodeBlueprint(makeSolarArray(...dimensions()));
    result.value = encoded;
    await navigator.clipboard.writeText(encoded);
    status.textContent = "Generated and copied to clipboard";
  } catch (error) {
    status.textContent = `Generation failed: ${error.message}`;
  }
});

refresh();
