from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template_string, request, send_file, url_for
from werkzeug.utils import secure_filename

from .config import DEFAULT_EQUIPMENT, make_settings
from .engine import run_analysis, summarize_counts
from .models import ForecastRow, RefuelPlanRow, RunResult, SourceStatus
from .storage import Storage
from .utils import dt_iso


def create_app(project_root: Path | None = None) -> Flask:
    settings = make_settings(project_root=project_root)
    settings.runtime_dir.mkdir(parents=True, exist_ok=True)
    (settings.runtime_dir / "uploads").mkdir(parents=True, exist_ok=True)
    (settings.runtime_dir / "outputs").mkdir(parents=True, exist_ok=True)
    storage = Storage(settings.runtime_dir / "fuel_alert.db")

    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024

    def current_settings():
        return make_settings(
            project_root=settings.project_root,
            fuel_workbook=storage.get_source("fuel"),
            n4_txt=storage.get_source("n4"),
            dashboard_output=settings.runtime_dir / "outputs" / "fuel_dashboard.xlsx",
        )

    def current_result(write_excel: bool = False) -> RunResult:
        schedules, mappings = storage.schedules_and_mappings()
        return run_analysis(current_settings(), schedules, mappings, write_excel=write_excel)

    @app.get("/")
    def index():
        return render_template_string(INDEX_HTML, rtgs=DEFAULT_EQUIPMENT)

    @app.post("/api/upload/<kind>")
    def upload(kind: str):
        if kind not in {"fuel", "n4"}:
            return jsonify({"error": "kind must be fuel or n4"}), 400
        uploaded = request.files.get("file")
        if not uploaded:
            return jsonify({"error": "No file uploaded"}), 400
        filename = secure_filename(uploaded.filename or f"{kind}.dat")
        if not filename:
            filename = f"{kind}.dat"
        target = settings.runtime_dir / "uploads" / f"{kind}_{filename}"
        uploaded.save(target)
        storage.set_source(kind, target)
        return jsonify({"ok": True, "path": str(target), "state": build_state(current_result(), storage)})

    @app.get("/api/state")
    def state():
        return jsonify(build_state(current_result(), storage))

    @app.post("/api/schedules")
    def create_schedule():
        schedule_id = storage.create_schedule()
        return jsonify({"ok": True, "schedule": storage.get_schedule(schedule_id), "state": build_state(current_result(), storage)})

    @app.put("/api/schedules/<int:schedule_id>")
    def update_schedule(schedule_id: int):
        payload = request.get_json(force=True, silent=True) or {}
        schedule = storage.update_schedule(schedule_id, payload)
        return jsonify({"ok": True, "schedule": schedule, "state": build_state(current_result(), storage)})

    @app.delete("/api/schedules/<int:schedule_id>")
    def delete_schedule(schedule_id: int):
        storage.delete_schedule(schedule_id)
        return jsonify({"ok": True, "state": build_state(current_result(), storage)})

    @app.post("/api/run")
    def run_dashboard():
        result = current_result(write_excel=True)
        return jsonify(build_state(result, storage))

    @app.get("/download/dashboard")
    def download_dashboard():
        output = current_settings().dashboard_output
        if not output.exists():
            result = current_result(write_excel=True)
            output = result.output_path or output
        if not output.exists():
            return redirect(url_for("index"))
        return send_file(output, as_attachment=True, download_name="fuel_dashboard.xlsx")

    return app


def build_state(result: RunResult, storage: Storage) -> dict:
    return {
        "run_at": result.run_at.isoformat(timespec="seconds"),
        "counts": summarize_counts(result),
        "schedules": storage.list_schedule_dicts(),
        "sources": [source_to_dict(item) for item in result.statuses],
        "warnings": result.warnings,
        "forecast": [forecast_to_dict(item) for item in result.forecasts],
        "plan": [plan_to_dict(item) for item in result.plan[:15]],
        "dashboard_ready": bool(result.output_path and result.output_path.exists()),
    }


def source_to_dict(item: SourceStatus) -> dict:
    return {
        "source": item.source,
        "path": str(item.path or ""),
        "exists": item.exists,
        "rows": item.rows,
        "status": item.status,
        "message": item.message,
        "last_modified": dt_iso(item.last_modified),
    }


def forecast_to_dict(item: ForecastRow) -> dict:
    return {
        "equipment": item.equipment,
        "status": item.status,
        "current_pct": item.current_pct,
        "current_liters": item.current_liters,
        "time_to_stop": dt_iso(item.time_to_stop),
        "time_to_warning": dt_iso(item.time_to_warning),
        "last_check": dt_iso(item.last_check),
        "note": item.note,
    }


def plan_to_dict(item: RefuelPlanRow) -> dict:
    return {
        "rank": item.rank,
        "equipment": item.equipment,
        "status": item.status,
        "current_pct": item.current_pct,
        "current_liters": item.current_liters,
        "liters_to_full": item.liters_to_full,
        "time_to_stop": dt_iso(item.time_to_stop),
        "linked_visit": item.linked_visit,
        "vessel_name": item.vessel_name,
        "etb": dt_iso(item.etb),
        "etd": dt_iso(item.etd),
        "workload_containers": item.workload_containers,
        "reason": item.reason,
    }


INDEX_HTML = """
<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Fuel RTG Alert</title>
  <style>
    :root { --ink:#17202a; --muted:#667085; --line:#d0d5dd; --blue:#1f4e78; --bg:#f7f9fb; --warn:#fdb022; --bad:#c00000; --ok:#12b76a; }
    * { box-sizing:border-box; }
    body { margin:0; font-family:Segoe UI, Arial, sans-serif; background:var(--bg); color:var(--ink); }
    header { padding:14px 20px; background:#fff; border-bottom:1px solid var(--line); display:flex; align-items:center; justify-content:space-between; }
    h1 { margin:0; font-size:20px; }
    main { padding:16px 20px 28px; display:grid; gap:14px; }
    section { background:#fff; border:1px solid var(--line); border-radius:8px; padding:14px; }
    h2 { margin:0 0 10px; font-size:16px; }
    .grid { display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:10px; }
    .source-grid { display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:10px; }
    .card { border:1px solid var(--line); border-radius:8px; padding:10px; }
    .kpi { color:#fff; border:0; }
    .CRITICAL { background:var(--bad); }
    .WARNING { background:var(--warn); color:#111; }
    .OK { background:var(--ok); }
    .NO_DATA { background:#98a2b3; }
    .kpi b { display:block; font-size:24px; margin-top:4px; }
    button, .button { border:1px solid var(--blue); background:var(--blue); color:#fff; border-radius:6px; padding:8px 10px; cursor:pointer; text-decoration:none; display:inline-block; font-size:14px; }
    button.secondary { background:#fff; color:var(--blue); }
    button.danger { background:#fff; color:var(--bad); border-color:var(--bad); }
    input, select, textarea { width:100%; border:1px solid var(--line); border-radius:6px; padding:7px; font:inherit; background:#fff; }
    input[type="checkbox"] { width:auto; }
    table { width:100%; border-collapse:collapse; }
    th, td { border-bottom:1px solid #eef2f6; padding:7px; text-align:left; vertical-align:top; font-size:13px; }
    th { color:#344054; background:#f8fafc; }
    .rtgs { display:grid; grid-template-columns:repeat(5, minmax(70px, 1fr)); gap:4px; }
    .muted { color:var(--muted); font-size:12px; }
    .status-pill { border-radius:999px; padding:2px 7px; font-weight:600; display:inline-block; }
    .toolbar { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
    .save { min-width:130px; color:var(--muted); }
    .field-title { display:inline-flex; align-items:center; gap:5px; font-weight:600; }
    .help { position:relative; display:inline-flex; align-items:center; justify-content:center; width:18px; height:18px; border-radius:999px; border:1px solid var(--line); color:var(--blue); background:#fff; font-size:12px; cursor:help; }
    .help::after { content:attr(data-tip); position:absolute; left:50%; bottom:125%; transform:translateX(-50%); z-index:10; display:none; min-width:220px; max-width:320px; padding:8px 10px; border-radius:7px; background:#17202a; color:#fff; font-size:12px; font-weight:400; line-height:1.35; box-shadow:0 8px 24px rgba(16,24,40,.18); white-space:normal; }
    .help:hover::after, .help:focus::after, .help:active::after { display:block; }
    .legend { display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:8px; margin:10px 0 12px; }
    .legend-item { border:1px solid var(--line); border-radius:8px; padding:8px; display:grid; gap:4px; }
    .legend-swatch { width:22px; height:12px; border-radius:999px; display:inline-block; margin-right:6px; vertical-align:middle; }
    .rtg-actions { margin:8px 0; display:flex; gap:8px; flex-wrap:wrap; }
    @media (max-width: 900px) { .grid, .source-grid { grid-template-columns:1fr; } .rtgs { grid-template-columns:repeat(3, 1fr); } }
  </style>
</head>
<body>
  <header>
    <h1>Fuel RTG Alert</h1>
    <div class="toolbar">
      <button onclick="runDashboard()">Run Dashboard</button>
      <a class="button" href="/download/dashboard">Download Excel</a>
      <span id="saveState" class="save">Ready</span>
    </div>
  </header>
  <main>
    <section>
      <h2>Upload data</h2>
      <div class="source-grid">
        <div class="card">
          <label>Fuel level .xlsx</label>
          <input type="file" id="fuelFile" accept=".xlsx,.xlsm">
          <button class="secondary" onclick="uploadFile('fuel','fuelFile')">Upload fuel</button>
          <p id="fuelSource" class="muted"></p>
        </div>
        <div class="card">
          <label>N4 TXT</label>
          <input type="file" id="n4File" accept=".txt,.tsv,.csv">
          <button class="secondary" onclick="uploadFile('n4','n4File')">Upload N4</button>
          <p id="n4Source" class="muted"></p>
        </div>
      </div>
    </section>
    <section>
      <div class="toolbar" style="justify-content:space-between">
        <h2>Lich tau va RTG lien quan</h2>
        <button onclick="createSchedule()">Them tau</button>
      </div>
      <div id="scheduleList"></div>
    </section>
    <section>
      <h2>Dashboard <span class="help" tabindex="0" data-tip="Mau sac the hien muc do canh bao RTG: do la gap, vang la can chu y, xanh la on, xam la thieu du lieu.">?</span></h2>
      <div class="grid" id="kpis"></div>
      <div class="legend">
        <div class="legend-item"><div><span class="legend-swatch CRITICAL"></span><b>CRITICAL</b></div><span class="muted">Da bang/duoi nguong 15%, can xu ly gap.</span></div>
        <div class="legend-item"><div><span class="legend-swatch WARNING"></span><b>WARNING</b></div><span class="muted">Duoi 25% hoac se cham 25% trong 24 gio.</span></div>
        <div class="legend-item"><div><span class="legend-swatch OK"></span><b>OK</b></div><span class="muted">Chua can do dau gap theo du bao hien tai.</span></div>
        <div class="legend-item"><div><span class="legend-swatch NO_DATA"></span><b>NO DATA</b></div><span class="muted">Chua co checklist hop le cho RTG.</span></div>
      </div>
      <p id="runAt" class="muted"></p>
      <h2>Canh bao do dau</h2>
      <table>
        <thead><tr><th>#</th><th>RTG</th><th>Status</th><th>Muc dau</th><th>Can bom</th><th>Tau</th><th>ETB</th><th>Ly do</th></tr></thead>
        <tbody id="planRows"></tbody>
      </table>
      <h2>Nguon du lieu</h2>
      <table>
        <thead><tr><th>Nguon</th><th>Status</th><th>Rows</th><th>Message</th><th>Path</th></tr></thead>
        <tbody id="sourceRows"></tbody>
      </table>
      <h2>Warnings</h2>
      <ul id="warningRows"></ul>
    </section>
  </main>
  <script>
    const RTGS = {{ rtgs|tojson }};
    let saveTimers = {};

    async function api(url, options={}) {
      const res = await fetch(url, options);
      if (!res.ok) throw new Error(await res.text());
      return await res.json();
    }

    async function refresh() {
      const state = await api('/api/state');
      render(state);
    }

    async function uploadFile(kind, inputId) {
      const input = document.getElementById(inputId);
      if (!input.files.length) return;
      setSave('Uploading...');
      const form = new FormData();
      form.append('file', input.files[0]);
      const data = await api(`/api/upload/${kind}`, {method:'POST', body:form});
      render(data.state);
      setSave('Uploaded');
    }

    async function createSchedule() {
      setSave('Creating...');
      const data = await api('/api/schedules', {method:'POST'});
      render(data.state);
      setSave('Saved');
    }

    function scheduleChanged(id) {
      clearTimeout(saveTimers[id]);
      setSave('Saving...');
      saveTimers[id] = setTimeout(() => saveSchedule(id), 350);
    }

    async function saveSchedule(id) {
      const box = document.querySelector(`[data-schedule="${id}"]`);
      const payload = {
        active: box.querySelector('[name="active"]').checked,
        vessel_name: box.querySelector('[name="vessel_name"]').value,
        visit_code: box.querySelector('[name="visit_code"]').value,
        etb: box.querySelector('[name="etb"]').value,
        etd: box.querySelector('[name="etd"]').value,
        berth_area: box.querySelector('[name="berth_area"]').value,
        priority: box.querySelector('[name="priority"]').value,
        notes: box.querySelector('[name="notes"]').value,
        rtgs: [...box.querySelectorAll('[name="rtg"]:checked')].map(item => item.value)
      };
      const data = await api(`/api/schedules/${id}`, {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
      render(data.state);
      setSave('Saved');
    }

    async function deleteSchedule(id) {
      if (!confirm('Xoa lich tau nay?')) return;
      const data = await api(`/api/schedules/${id}`, {method:'DELETE'});
      render(data.state);
      setSave('Deleted');
    }

    function setAllRtgs(id, checked) {
      const box = document.querySelector(`[data-schedule="${id}"]`);
      box.querySelectorAll('[name="rtg"]').forEach(item => item.checked = checked);
      scheduleChanged(id);
    }

    async function runDashboard() {
      setSave('Running...');
      const state = await api('/api/run', {method:'POST'});
      render(state);
      setSave('Dashboard ready');
    }

    function render(state) {
      renderSources(state.sources);
      renderSchedules(state.schedules);
      renderKpis(state.counts);
      document.getElementById('runAt').textContent = `Last run: ${state.run_at}`;
      document.getElementById('planRows').innerHTML = state.plan.map(row => `
        <tr>
          <td>${row.rank}</td><td>${row.equipment}</td><td>${pill(row.status)}</td>
          <td>${fmt(row.current_pct, 1)}%</td><td>${fmt(row.liters_to_full, 0)}L</td>
          <td>${esc(row.vessel_name || row.linked_visit || '')}</td><td>${esc(row.etb || '')}</td><td>${esc(row.reason)}</td>
        </tr>`).join('');
      document.getElementById('warningRows').innerHTML = (state.warnings.length ? state.warnings : ['Khong co warning']).map(item => `<li>${esc(item)}</li>`).join('');
    }

    function renderSources(sources) {
      const fuel = sources.find(item => item.source === 'Fuel workbook');
      const n4 = sources.find(item => item.source === 'N4 TXT');
      document.getElementById('fuelSource').textContent = fuel ? `${fuel.status}: ${fuel.message} ${fuel.path}` : '';
      document.getElementById('n4Source').textContent = n4 ? `${n4.status}: ${n4.message} ${n4.path}` : '';
      document.getElementById('sourceRows').innerHTML = sources.map(row => `<tr><td>${esc(row.source)}</td><td>${esc(row.status)}</td><td>${row.rows}</td><td>${esc(row.message)}</td><td>${esc(row.path)}</td></tr>`).join('');
    }

    function renderSchedules(rows) {
      document.getElementById('scheduleList').innerHTML = rows.map(row => `
        <div class="card" data-schedule="${row.id}">
          <div class="grid">
            <label>${help('Active','Bat/tat dong lich tau nay. Tat active thi web khong dung dong nay de uu tien RTG.')}<br><input name="active" type="checkbox" ${row.active ? 'checked' : ''} onchange="scheduleChanged(${row.id})"></label>
            <label>${help('Ten tau','Ten tau de hien thi tren dashboard va ke hoach do dau.')}<br><input name="vessel_name" value="${esc(row.vessel_name)}" oninput="scheduleChanged(${row.id})"></label>
            <label>${help('Visit code','Ma chuyen/tau trong N4, vi du USL614W. Neu co, web lien ket them workload N4.')}<br><input name="visit_code" value="${esc(row.visit_code)}" oninput="scheduleChanged(${row.id})"></label>
            <label>${help('Priority','So cang nho cang uu tien cao. 1 la tau gap/quan trong; 3 la mac dinh; 9 la thap.')}<br><input name="priority" type="number" min="1" max="9" value="${row.priority}" oninput="scheduleChanged(${row.id})"></label>
            <label>${help('ETB','Thoi gian du kien tau vao/lam hang. RTG duoc chon se duoc uu tien truoc moc nay.')}<br><input name="etb" type="datetime-local" value="${toInputTime(row.etb)}" oninput="scheduleChanged(${row.id})"></label>
            <label>${help('ETD','Thoi gian du kien tau roi/ket thuc. Web xem RTG la dang lien quan trong khoang ETB den ETD.')}<br><input name="etd" type="datetime-local" value="${toInputTime(row.etd)}" oninput="scheduleChanged(${row.id})"></label>
            <label>${help('Berth area','Khu cau/ben hoac khu vuc lam hang, dung de nguoi van hanh xem lai.')}<br><input name="berth_area" value="${esc(row.berth_area)}" oninput="scheduleChanged(${row.id})"></label>
            <label>${help('Notes','Ghi chu noi bo, vi du tau gap, doi ETB, block lam hang. Hien chu yeu de xem lai.')}<br><input name="notes" value="${esc(row.notes)}" oninput="scheduleChanged(${row.id})"></label>
          </div>
          <p class="muted">Chon RTG lien quan de dashboard uu tien canh bao theo ETB/ETD.</p>
          <div class="rtg-actions">
            <button class="secondary" onclick="setAllRtgs(${row.id}, true)">Chon tat ca RTG</button>
            <button class="secondary" onclick="setAllRtgs(${row.id}, false)">Bo chon tat ca</button>
          </div>
          <div class="rtgs">${RTGS.map(rtg => `<label><input name="rtg" type="checkbox" value="${rtg}" ${row.rtgs.includes(rtg) ? 'checked' : ''} onchange="scheduleChanged(${row.id})"> ${rtg}</label>`).join('')}</div>
          <p><button class="danger" onclick="deleteSchedule(${row.id})">Xoa</button></p>
        </div>`).join('');
    }

    function renderKpis(counts) {
      document.getElementById('kpis').innerHTML = ['CRITICAL','WARNING','OK','NO_DATA'].map(status => `
        <div class="card kpi ${status}">${status}<b>${counts[status] || 0}</b></div>`).join('');
    }

    function pill(status) { return `<span class="status-pill ${status}">${status}</span>`; }
    function help(label, tip) { return `<span class="field-title">${esc(label)} <span class="help" tabindex="0" data-tip="${esc(tip)}">?</span></span>`; }
    function fmt(value, digits) { return value === null || value === undefined || value === '' ? '' : Number(value).toFixed(digits); }
    function esc(value) { return String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch])); }
    function toInputTime(value) { return value ? String(value).slice(0,16) : ''; }
    function setSave(text) { document.getElementById('saveState').textContent = text; }
    refresh().catch(err => setSave(err.message));
  </script>
</body>
</html>
"""


def main() -> None:
    host = os.environ.get("FUEL_ALERT_HOST", "127.0.0.1")
    port = int(os.environ.get("FUEL_ALERT_PORT", "8000"))
    app = create_app()
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
