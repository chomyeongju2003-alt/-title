const FILE_MAP = {
  major: "data/(표)(2023연장)투입산출표_생산자가격_통합대분류.xlsx",
  medium: "data/(표)(2023연장)투입산출표_생산자가격_통합중분류.xlsx",
  minor: "data/(표)(2023연장)투입산출표_생산자가격_통합소분류.xlsx",
  basic: "data/(표)(2023연장)투입산출표_생산자가격_기본부문.xlsx"
};

const worker = new Worker("worker.js");
let msgId = 0;
const pending = new Map();

worker.onmessage = (e) => {
  const { id, result, error } = e.data;
  if (!pending.has(id)) return;
  const { resolve, reject } = pending.get(id);
  pending.delete(id);
  if (error) reject(new Error(error));
  else resolve(result);
};

function callWorker(action, payload = {}) {
  return new Promise((resolve, reject) => {
    const id = ++msgId;
    pending.set(id, { resolve, reject });
    worker.postMessage({ id, action, payload });
  });
}

let allRows = [];
let currentRowItems = [];
let currentUnit = "";
let allSectors = [];
let scenarios = [];

const statusText = document.getElementById("statusText");
const loadBtn = document.getElementById("loadBtn");
const levelSelect = document.getElementById("levelSelect");

const sheetSelect = document.getElementById("sheetSelect");
const rowSearch = document.getElementById("rowSearch");
const rowSelect = document.getElementById("rowSelect");
const colSearch = document.getElementById("colSearch");
const rawTableBody = document.querySelector("#rawTable tbody");

const indSearch = document.getElementById("indSearch");
const indSelect = document.getElementById("indSelect");
const indicatorResult = document.getElementById("indicatorResult");

const simIndSearch = document.getElementById("simIndSearch");
const simIndSelect = document.getElementById("simIndSelect");
const shockAmount = document.getElementById("shockAmount");
const addScenarioBtn = document.getElementById("addScenarioBtn");
const runSimBtn = document.getElementById("runSimBtn");
const clearSimBtn = document.getElementById("clearSimBtn");
const scenarioList = document.getElementById("scenarioList");
const simSummary = document.getElementById("simSummary");
const simTableBody = document.querySelector("#simTable tbody");

loadBtn.addEventListener("click", async () => {
  const key = levelSelect.value;
  const url = encodeURI(FILE_MAP[key]);
  loadBtn.disabled = true;
  statusText.textContent = "데이터를 불러오고 Python 분석 환경을 초기화하는 중입니다...";
  try {
    const data = await callWorker("load_excel", { url });
    allSectors = data.sectors;

    sheetSelect.innerHTML = data.sheet_names.map(s => `<option value="${s}">${s}</option>`).join("");
    [sheetSelect, rowSearch, rowSelect, colSearch, indSearch, indSelect, simIndSearch, simIndSelect, shockAmount, addScenarioBtn, runSimBtn, clearSimBtn]
      .forEach(el => el.disabled = false);

    renderSectorOptions(indSelect, allSectors, "");
    renderSectorOptions(simIndSelect, allSectors, "");
    scenarios = [];
    renderScenarios();
    simSummary.innerHTML = "";
    simTableBody.innerHTML = '<tr><td colspan="5" class="empty">시나리오를 추가한 뒤 파급효과 계산을 누르세요.</td></tr>';

    await onSheetChange();
    await onIndicatorIndustryChange();
    statusText.textContent = `로딩 완료: ${levelSelect.options[levelSelect.selectedIndex].text} (총 ${allSectors.length}개 산업부문)`;
  } catch (err) {
    statusText.textContent = "오류 발생: " + err.message;
  } finally {
    loadBtn.disabled = false;
  }
});

async function onSheetChange() {
  const sheetName = sheetSelect.value;
  const data = await callWorker("get_sheet_rows", { sheetName });
  allRows = data.rows;
  currentUnit = data.unit;
  rowSearch.value = "";
  renderRowOptions("");
  await onRowChange();
}

function renderRowOptions(keyword) {
  const kw = keyword.trim().toLowerCase();
  const filtered = allRows.filter(r => r.code.toLowerCase().includes(kw) || r.name.toLowerCase().includes(kw));
  rowSelect.innerHTML = filtered.map(r => `<option value="${r.idx}">[${r.code}] ${r.name}</option>`).join("");
}

async function onRowChange() {
  if (!rowSelect.value) return;
  const data = await callWorker("get_row_values", { sheetName: sheetSelect.value, rowIdx: rowSelect.value });
  currentRowItems = data.items;
  currentUnit = data.unit;
  renderRawTable();
}

function renderRawTable() {
  const kw = colSearch.value.trim().toLowerCase();
  const filtered = currentRowItems.filter(it => it.code.toLowerCase().includes(kw) || it.name.toLowerCase().includes(kw));
  const isCoeff = currentUnit.includes("계수");
  rawTableBody.innerHTML = filtered.map(it => `
    <tr>
      <td>${it.code}</td>
      <td>${it.name}</td>
      <td class="num">${isCoeff ? it.value.toFixed(6) : Math.round(it.value).toLocaleString()}</td>
      <td>${currentUnit}</td>
    </tr>
  `).join("");
}

function renderSectorOptions(selectEl, sectors, keyword) {
  const kw = keyword.trim().toLowerCase();
  const filtered = sectors
    .map((s, idx) => ({ ...s, idx }))
    .filter(s => s.code.toLowerCase().includes(kw) || s.name.toLowerCase().includes(kw));
  selectEl.innerHTML = filtered.map(s => `<option value="${s.idx}">[${s.code}] ${s.name}</option>`).join("");
}

async function onIndicatorIndustryChange() {
  if (!indSelect.value) return;
  const res = await callWorker("get_indicators", { secIdx: indSelect.value });
  indicatorResult.innerHTML = Object.entries(res).map(([k, v]) => `
    <div class="kpi-box">
      <div class="kpi-title">${k}</div>
      <div class="kpi-val">${v}</div>
    </div>
  `).join("");
}

sheetSelect.addEventListener("change", onSheetChange);
rowSearch.addEventListener("input", async () => { renderRowOptions(rowSearch.value); await onRowChange(); });
rowSelect.addEventListener("change", onRowChange);
colSearch.addEventListener("input", renderRawTable);

indSearch.addEventListener("input", async () => { renderSectorOptions(indSelect, allSectors, indSearch.value); await onIndicatorIndustryChange(); });
indSelect.addEventListener("change", onIndicatorIndustryChange);

simIndSearch.addEventListener("input", () => renderSectorOptions(simIndSelect, allSectors, simIndSearch.value));

addScenarioBtn.addEventListener("click", () => {
  const idx = parseInt(simIndSelect.value, 10);
  const amount = parseFloat(shockAmount.value);
  if (isNaN(idx) || isNaN(amount) || amount <= 0) return;
  const sec = allSectors[idx];
  scenarios.push({ idx, code: sec.code, name: sec.name, amount });
  renderScenarios();
});

clearSimBtn.addEventListener("click", () => {
  scenarios = [];
  renderScenarios();
  simSummary.innerHTML = "";
  simTableBody.innerHTML = '<tr><td colspan="5" class="empty">시나리오를 추가한 뒤 파급효과 계산을 누르세요.</td></tr>';
});

function renderScenarios() {
  if (scenarios.length === 0) {
    scenarioList.innerHTML = "<span style='color:#6b7280'>추가된 시나리오가 없습니다.</span>";
    return;
  }
  scenarioList.innerHTML = scenarios.map(s =>
    `<span class="tag">[${s.code}] ${s.name}: +${s.amount.toLocaleString()} 백만원</span>`
  ).join("");
}

runSimBtn.addEventListener("click", async () => {
  if (scenarios.length === 0) {
    alert("먼저 '시나리오에 추가' 버튼을 눌러 산업과 증가액을 추가하세요.");
    return;
  }
  const res = await callWorker("simulate", { shocks: scenarios });
  simSummary.innerHTML = `
    <div class="kpi-box"><div class="kpi-title">총 최종수요 투입액</div><div class="kpi-val">${Math.round(res.total_shock).toLocaleString()} 백만원</div></div>
    <div class="kpi-box"><div class="kpi-title">총 생산유발액</div><div class="kpi-val">${Math.round(res.total_prod).toLocaleString()} 백만원</div></div>
    <div class="kpi-box"><div class="kpi-title">총 부가가치유발액</div><div class="kpi-val">${Math.round(res.total_va).toLocaleString()} 백만원</div></div>
    <div class="kpi-box"><div class="kpi-title">총 수입유발액</div><div class="kpi-val">${Math.round(res.total_imp).toLocaleString()} 백만원</div></div>
  `;
  simTableBody.innerHTML = res.rows.map(r => `
    <tr>
      <td>${r.code}</td>
      <td>${r.name}</td>
      <td class="num">${r.prod.toFixed(1)}</td>
      <td class="num">${r.va.toFixed(1)}</td>
      <td class="num">${r.imp.toFixed(1)}</td>
    </tr>
  `).join("");
});
