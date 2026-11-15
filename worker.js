importScripts("https://cdn.jsdelivr.net/pyodide/v0.26.2/full/pyodide.js");

let pyodideReady = null;

async function initPyodide() {
  const pyodide = await loadPyodide();
  await pyodide.loadPackage(["numpy", "pandas", "openpyxl"]);
  const pyCode = await (await fetch("model.py")).text();
  pyodide.runPython(pyCode);
  return pyodide;
}

self.onmessage = async (event) => {
  const { id, action, payload } = event.data;
  try {
    if (!pyodideReady) {
      pyodideReady = initPyodide();
    }
    const pyodide = await pyodideReady;

    if (action === "load_excel") {
      const resp = await fetch(payload.url);
      if (!resp.ok) throw new Error("엑셀 파일을 찾을 수 없습니다: " + payload.url);
      const buf = await resp.arrayBuffer();
      pyodide.globals.set("excel_bytes", new Uint8Array(buf));
      const res = pyodide.runPython("analyzer.load_excel_bytes(bytes(excel_bytes))");
      self.postMessage({ id, result: JSON.parse(res) });
    } else if (action === "get_sheet_rows") {
      pyodide.globals.set("s_name", payload.sheetName);
      const res = pyodide.runPython("analyzer.get_sheet_rows(s_name)");
      self.postMessage({ id, result: JSON.parse(res) });
    } else if (action === "get_row_values") {
      pyodide.globals.set("s_name", payload.sheetName);
      pyodide.globals.set("r_idx", payload.rowIdx);
      const res = pyodide.runPython("analyzer.get_row_values(s_name, r_idx)");
      self.postMessage({ id, result: JSON.parse(res) });
    } else if (action === "get_indicators") {
      pyodide.globals.set("sec_idx", payload.secIdx);
      const res = pyodide.runPython("analyzer.get_industry_indicators(sec_idx)");
      self.postMessage({ id, result: JSON.parse(res) });
    } else if (action === "simulate") {
      pyodide.globals.set("shocks_str", JSON.stringify(payload.shocks));
      const res = pyodide.runPython("analyzer.simulate_demand(shocks_str)");
      self.postMessage({ id, result: JSON.parse(res) });
    }
  } catch (err) {
    self.postMessage({ id, error: err.message || String(err) });
  }
};
