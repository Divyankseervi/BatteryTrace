'use strict';
/* BatteryTrace front-end. No inline handlers (strict CSP). All dynamic text goes through esc(). */
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const S = { user: 'U-SVC', users: [], meta: null, aq: { q: '', status: '', type: '', sort: 'type', offset: 0 }, lastRecall: null };
const PAGE = 50;

const ROUTES = {
  overview: ['Fleet Dashboard', 'Role-tailored overview of electric vehicles, battery health diagnostics, and blockchain-style ledger integrity.'],
  assets: ['Assets & Vehicles', 'Search, filter, and inspect every tracked battery pack, EV vehicle, module, cell, and solar energy storage system.'],
  lineage: ['Battery & Lineage', 'Inspect an individual battery: digital passport certificate, host vehicle, bill-of-materials tree, and lifecycle events.'],
  recall: ['Recall Simulation', 'Trace which vehicles and battery packs contain a defective component or manufacturing batch across the recursive graph.'],
  ledger: ['Event Ledger', 'Append-only, tamper-proof lifecycle event ledger protected by cryptographic SHA-256 hash chaining.'],
  quality: ['Data Quality', 'Rule-based database integrity findings. Flags anomalies like active passports on recycled batteries.'],
  lab: ['System Architecture Lab', 'System architecture, live relational processing, query runner, ACID concurrency, and benchmarks.'],
};

/* ---------- Friendly Catalogs (Generalised, Non-Technical Product & Location Maps) ---------- */
const VEHICLE_CATALOG = {
  'VEH-NEXON-EV': { name: 'Tata Nexon EV Max', type: 'Electric SUV', reg: 'KA-01-EQ-5521', icon: '🚗', badgeClass: 'nexon', desc: 'India’s #1 Electric SUV (40.5 kWh LFP Pack)' },
  'VEH-ATHER-450X': { name: 'Ather 450X Gen 3', type: 'Smart Electric Scooter', reg: 'KA-03-ES-9100', icon: '🛵', badgeClass: 'ather', desc: 'High-Performance Connected 2-Wheeler (3.7 kWh NMC Pack)' },
  'VEH-XUV400': { name: 'Mahindra XUV400 EV', type: 'Electric Performance SUV', reg: 'MH-12-EV-8840', icon: '🚙', badgeClass: 'xuv', desc: 'All-Electric Family SUV (39.4 kWh NMC Pack)' },
  'VEH-2048': { name: 'Aster Fleet Commercial Shuttle', type: 'Electric Shuttle Van', reg: 'KA-05-EV-1024', icon: '🚐', badgeClass: '', desc: 'Passenger & Delivery Commercial Shuttle (60 kWh Pack)' },
  'STORE-2001': { name: 'Indiranagar Solar BESS', type: 'Second-Life Energy Storage', reg: 'BESS-BLR-01', icon: '⚡', badgeClass: 'storage', desc: 'Repurposed Clean Solar Backup System (48 kWh)' },
  'STORE-SOLAR-02': { name: 'Peenya Industrial Solar Farm', type: 'Microgrid Energy Storage', reg: 'BESS-PEENYA-02', icon: '⚡', badgeClass: 'storage', desc: 'Second-Life Clean Energy Storage Bank (50 kWh)' },
  'STORE-101': { name: 'Koramangala Substation BESS', type: 'Grid Stabilization Storage', reg: 'BESS-KOR-03', icon: '⚡', badgeClass: 'storage', desc: 'Stationary Peak-Shaving Battery Bank' }
};

const LOCATION_CATALOG = {
  'Indiranagar Depot, Bengaluru': { label: 'Indiranagar Depot, Bengaluru', zone: 'South EV Hub', icon: '📍' },
  'Koramangala Hub, Bengaluru': { label: 'Koramangala Fast-Charge Hub, Bengaluru', zone: 'South EV Hub', icon: '📍' },
  'Bandra-Kurla Depot, Mumbai': { label: 'Bandra-Kurla EV Depot, Mumbai', zone: 'Western Depot', icon: '📍' },
  'Peenya Industrial Microgrid, Bengaluru': { label: 'Peenya Solar Farm BESS, Bengaluru', zone: 'Microgrid Solar', icon: '📍' },
  'Chennai, India': { label: 'Aster Gigafactory, Chennai', zone: 'Manufacturing Plant', icon: '🏭' },
  'Pune, India': { label: 'GridNest Energy Facility, Pune', zone: 'BESS Assembly', icon: '🏢' },
  'Nashik, India': { label: 'CycleLoop Recycling Facility, Nashik', zone: 'Recycling Facility', icon: '♻️' },
  'Hyderabad, India': { label: 'VoltPath EV Service Centre, Hyderabad', zone: 'Authorized Service', icon: '🔧' },
  'Coimbatore, India': { label: 'VoltPath Assembly Plant, Coimbatore', zone: 'Cell Manufacturing', icon: '🏭' },
  'Bengaluru, India': { label: 'Aster EV Service Centre, Bengaluru', zone: 'Service Station', icon: '🔧' }
};

const PERSONA_CONFIGS = {
  'U-MFG': {
    role: 'MANUFACTURER',
    title: 'Battery Cell & Pack Gigafactory',
    org: 'Apex Energy Solutions / Bharat Cell',
    badge: '🏭 Manufacturer Persona',
    roleClass: 'mfg',
    accentColor: '#059669',
    bgColor: '#ecfdf5',
    borderColor: '#a7f3d0',
    summary: 'You build high-voltage battery packs, assemble cell batches into modules, run factory quality control tests, and issue the initial Digital Battery Passport (Article 77) before shipping to vehicle manufacturers.',
    quickActions: [
      { label: '➕ Assemble & Link Battery Pack', act: 'move', cls: 'primary', icon: '⚡' },
      { label: '📋 Record Production Lifecycle Event', act: 'event', cls: '', icon: '📋' },
      { label: '🔬 Log Factory Health Diagnostic', act: 'diagnostic', cls: '', icon: '🧪' },
      { label: '🔍 Trace Production Component Batch', href: '#/recall', cls: '', icon: '🔎' }
    ]
  },
  'U-SVC': {
    role: 'SERVICE',
    title: 'Authorized EV Service & Fleet Diagnostic Hub',
    org: 'Greaves EV Fleet Services & Diagnostics',
    badge: '🔧 Service & Diagnostics Persona',
    roleClass: 'svc',
    accentColor: '#2563eb',
    bgColor: '#eff6ff',
    borderColor: '#bfdbfe',
    summary: 'You service electric vehicles on the road, conduct periodic State of Health (SoH %) battery diagnostic checks, detect degraded cells, and perform pack replacements for commercial & personal EV fleets.',
    quickActions: [
      { label: '🩺 Log Battery Health Test (SoH %)', act: 'diagnostic', cls: 'primary', icon: '📊' },
      { label: '🛠️ Record Vehicle Maintenance Event', act: 'event', cls: '', icon: '🔧' },
      { label: '🔁 Transfer / Swap Battery in Car', act: 'move', cls: '', icon: '🔄' },
      { label: '🚘 View Fleet Vehicles', href: '#/assets?type=VEHICLE', cls: '', icon: '🚗' }
    ]
  },
  'U-REC': {
    role: 'RECYCLER',
    title: 'Certified Second-Life & Mineral Recycling Facility',
    org: 'EcoRevive Metals & Circular Energy',
    badge: '♻️ Recycler & Second-Life Persona',
    roleClass: 'rec',
    accentColor: '#d97706',
    bgColor: '#fffbeb',
    borderColor: '#fde68a',
    summary: 'You repurpose retired EV batteries into clean solar microgrid energy storage systems (Second Life), or safely decommission and recycle end-of-life packs to recover critical raw materials (Lithium, Nickel, Cobalt).',
    quickActions: [
      { label: '🔒 Decommission & Close Passport (Recycle)', act: 'event', cls: 'danger', icon: '♻️' },
      { label: '⚡ Repurpose Battery to Solar Storage', act: 'event', cls: 'primary', icon: '☀️' },
      { label: '📦 Link to Microgrid Energy Storage', act: 'move', cls: '', icon: '🏭' },
      { label: '📜 Review Circularity & Recycling Policy', href: '#/lab/policy', cls: '', icon: '📑' }
    ]
  },
  'U-REG': {
    role: 'REGULATOR',
    title: 'National Battery Safety & Compliance Authority',
    org: 'Ministry of Road Transport & Environmental Auditor',
    badge: '🛡️ Compliance Auditor Persona',
    roleClass: 'reg',
    accentColor: '#7c3aed',
    bgColor: '#f5f3ff',
    borderColor: '#ddd6fe',
    summary: 'You enforce government battery safety standards (EU 2023/1542 & India BWMR 2022), audit the SHA-256 cryptographic ledger for illegal tampering, and coordinate emergency defect recall investigations.',
    quickActions: [
      { label: '🛡️ Verify Ledger SHA-256 Chain', act: 'verify', cls: 'primary', icon: '🔐' },
      { label: '🚨 Simulate Defective Batch Recall', href: '#/recall', cls: '', icon: '⚠️' },
      { label: '🔍 Inspect Data Quality Anomalies', href: '#/quality', cls: '', icon: '📑' },
      { label: '📖 Open Cloud & Data Architecture Guide', href: '#/lab/map', cls: '', icon: '☁️' }
    ]
  }
};

/* ---------- Formatter Helpers ---------- */
function formatHostProduct(code) {
  if (!code) return '<span class="veh-tag unassigned">🏭 Warehouse Stock <span class="muted">(Ready for EV)</span></span>';
  const v = VEHICLE_CATALOG[code];
  if (v) {
    return `<a href="#/lineage/${encodeURIComponent(code)}" class="veh-tag ${v.badgeClass || ''}" title="${esc(v.desc)}">
      <span>${v.icon}</span> <b>${esc(v.name)}</b> <span class="small muted">(${esc(v.type)})</span>
    </a>`;
  }
  return `<a href="#/lineage/${encodeURIComponent(code)}" class="veh-tag">📦 <b>${esc(code)}</b></a>`;
}

function formatLocation(loc) {
  if (!loc) return '<span class="loc-tag">Hosur Assembly Plant</span>';
  const l = LOCATION_CATALOG[loc];
  return `<span class="loc-tag" title="${l ? esc(l.zone) : ''}">${esc(l ? l.label : loc)}</span>`;
}

function formatSoh(pct, cycles) {
  if (pct == null) return `<span class="health-pill pending"><span class="small muted">Pending test</span></span>`;
  const val = Number(pct);
  let cls = 'ok', label = 'Excellent (Like New)', dot = '🟢';
  if (val < 75) { cls = 'bad'; label = 'End of Life'; dot = '🔴'; }
  else if (val < 83) { cls = 'warn'; label = 'Second-Life Candidate'; dot = '🟠'; }
  else if (val < 90) { cls = 'info'; label = 'Good (Normal Fleet Use)'; dot = '🟡'; }
  
  return `<div class="health-pill ${cls}" title="${val}% State of Health (${cycles != null ? cycles.toLocaleString() + ' charge cycles' : 'initial cycle'})">
    <div class="hp-top">
      <span>${dot} <b>${val.toFixed(1)}% SoH</b></span>
      <span class="sub small muted">${label}</span>
    </div>
    <div class="soh-bar"><div class="soh-fill ${cls}" style="width:${Math.min(100, Math.max(12, val))}%"></div></div>
  </div>`;
}

function formatChem(chem) {
  if (!chem) return '<span class="faint">—</span>';
  const c = chem.toUpperCase();
  if (c === 'LFP') {
    return `<span class="chem-badge lfp" title="Lithium Iron Phosphate: Ultra-safe, 3000+ cycle life, ideal for hot climates">⚡ LFP (Safe, Long Life)</span>`;
  }
  if (c === 'NMC') {
    return `<span class="chem-badge nmc" title="Nickel Manganese Cobalt: High energy density, maximum driving range">🚀 NMC (High Range)</span>`;
  }
  return `<span class="chem-badge">${esc(chem)}</span>`;
}

function formatCapacity(kwh) {
  if (kwh == null) return '<span class="faint">—</span>';
  const k = Number(kwh);
  let est = '';
  if (k >= 38 && k <= 42) est = '~312 km range';
  else if (k >= 45 && k <= 65) est = '~450 km range';
  else if (k >= 3 && k <= 4.5) est = '~110 km range';
  else if (k >= 48) est = 'Solar Storage BESS';
  return `<b>${k} kWh</b>${est ? `<div class="small faint">${est}</div>` : ''}`;
}

function friendlyStatus(s) {
  const map = {
    'ACTIVE': '<span class="st ok">🟢 Active on Road</span>',
    'SECOND_LIFE': '<span class="st info">⚡ Second Life (Solar BESS)</span>',
    'IN_REPAIR': '<span class="st warn">⚠️ Under Service / Repair</span>',
    'RECYCLED': '<span class="st bad">♻️ Recycled (Closed)</span>',
    'RETIRED': '<span class="st">Retired</span>'
  };
  return map[s] || st(s);
}

/* ---------- Network API Client ---------- */
async function api(path, opts = {}) {
  const o = { ...opts, headers: { ...(opts.headers || {}) } };
  if (o.body !== undefined) { o.method = 'POST'; o.headers['Content-Type'] = 'application/json'; o.headers['X-Demo-User'] = S.user; o.body = JSON.stringify(o.body); }
  const baseUrl = (window.__BATTERYTRACE_CONFIG__ && window.__BATTERYTRACE_CONFIG__.apiUrl) || '';
  const url = (baseUrl && path.startsWith('/api/')) ? baseUrl.replace(/\/$/, '') + path : path;
  let r;
  try { r = await fetch(url, o); } catch { throw Object.assign(new Error('Cannot reach the server. Is `python server.py` still running?'), { code: 'NETWORK' }); }
  let d = null; try { d = await r.json(); } catch { /* non-JSON */ }
  if (!r.ok) throw Object.assign(new Error((d && d.error) || `Request failed (${r.status})`), { code: d && d.code, status: r.status });
  return d;
}

function flash(msg, kind = 'ok') {
  const f = $('#flash');
  f.innerHTML = `<div class="notice ${kind}">${esc(msg)}</div>`;
  clearTimeout(flash.t);
  flash.t = setTimeout(() => f.innerHTML = '', 7000);
}

const stCls = s => ({ ACTIVE: 'ok', SECOND_LIFE: 'info', IN_REPAIR: 'warn', VERIFIED: 'ok', UNKNOWN: 'warn', SUPERSEDED: '', CLOSED: '', RECYCLED: '', RETIRED: '', SELF_REPORTED: '' }[s] || '');
const st = s => `<span class="st ${stCls(s)}">${esc(String(s || '—').replaceAll('_', ' ').toLowerCase())}</span>`;
const typeName = t => ({ BATTERY_PACK: 'Battery pack', STORAGE_SYSTEM: 'Solar storage BESS', VEHICLE: 'Electric vehicle', MODULE: 'Module', CELL: 'Cell' }[t] || t || '—');
const d10 = d => esc(d ? String(d).slice(0, 10) : '—');
const loading = (t = 'Loading…') => `<div class="state" role="status">${esc(t)}</div>`;
const errState = (e, retry) => `<div class="state error" role="alert">${esc(e.message)}${retry ? ' <button class="link" data-act="retry">Retry</button>' : ''}</div>`;
const uuid = () => (crypto.randomUUID ? crypto.randomUUID() : 'k-' + Date.now() + '-' + Math.random().toString(16).slice(2));
const shortHash = h => h ? esc(h.slice(0, 10)) + '…' : '—';
const assetLink = c => `<a href="#/lineage/${encodeURIComponent(c)}" class="mono"><b>${esc(c)}</b></a>`;

function table(cols, rows, { stack = true, empty = 'No records.' } = {}) {
  if (!rows.length) return `<div class="state">${esc(empty)}</div>`;
  return `<div class="scroll"><table class="${stack ? 'stack' : ''}"><thead><tr>${cols.map(c => `<th scope="col" class="${c.num ? 'num' : ''}">${esc(c.h)}</th>`).join('')}</tr></thead><tbody>` +
    rows.map(r => `<tr>${cols.map((c, i) => `<td data-label="${esc(c.h)}" class="${c.num ? 'num' : ''} ${c.wrap ? 'wrap' : ''}">${r[i]}</td>`).join('')}</tr>`).join('') + '</tbody></table></div>';
}

/* ---------- Router ---------- */
function parseHash() {
  const [path, qs] = location.hash.replace(/^#\/?/, '').split('?');
  const [name, arg] = path.split('/');
  return { name: ROUTES[name] ? name : 'overview', arg: arg ? decodeURIComponent(arg) : '', qs: new URLSearchParams(qs || '') };
}

let routing = false, rerun = false;
async function route() {
  if (routing) { rerun = true; return; }
  routing = true;
  try { do { rerun = false; await routeOnce(); } while (rerun); } finally { routing = false; }
}

async function routeOnce() {
  const { name, arg, qs } = parseHash();
  $$('.nav a').forEach(a => { if (a.dataset.route === name) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); });
  $('#title').textContent = ROUTES[name][0];
  $('#purpose').textContent = ROUTES[name][1];
  document.title = `${ROUTES[name][0]} · BatteryTrace`;
  const page = $('#page'); page.innerHTML = loading();
  try { await PAGES[name](page, arg, qs); } catch (e) { page.innerHTML = errState(e, true); }
  refreshNavCount();
}

async function refreshNavCount() {
  try { const s = await api('/api/summary'); $('#navCount').textContent = s.issues || ''; } catch { /* ignore */ }
}

/* ---------- Pages ---------- */
const PAGES = {};

PAGES.overview = async page => {
  const [s, ev, packsRes] = await Promise.all([
    api('/api/summary'),
    api('/api/events?limit=8'),
    api('/api/assets?type=BATTERY_PACK&limit=50')
  ]);

  const persona = PERSONA_CONFIGS[S.user] || PERSONA_CONFIGS['U-SVC'];
  const packs = packsRes.items || [];
  const c = s.circularity || {};
  const a = s.audit || {};

  // Custom KPI generator
  const renderKpis = () => {
    if (persona.role === 'MANUFACTURER') {
      return `
      <div class="kpis">
        <div class="kpi"><div class="v">${packs.length}</div><div class="k">Battery Packs Built</div><div class="d">High-voltage packs assembled</div></div>
        <div class="kpi"><div class="v">${s.active_passports}</div><div class="k">Active Passports</div><div class="d">Digitally certified passports</div></div>
        <div class="kpi"><div class="v">${packs.filter(p => !p.host_product && p.status === 'ACTIVE').length}</div><div class="k">Unassigned Inventory</div><div class="d">Ready for car integration</div></div>
        <div class="kpi"><div class="v">${s.issues === 0 ? '100%' : '2 Alerts'}</div><div class="k">Production Batch Check</div><div class="d">Classroom seeded test anomalies</div></div>
      </div>`;
    } else if (persona.role === 'SERVICE') {
      return `
      <div class="kpis">
        <div class="kpi"><div class="v">${c.active_mobility || 4}</div><div class="k">Active Fleet on Road</div><div class="d">Tata Nexon, Ather, Mahindra XUV</div></div>
        <div class="kpi"><div class="v">${c.avg_fleet_soh ? c.avg_fleet_soh + '%' : '94.8%'}</div><div class="k">Fleet Average Health</div><div class="d">Measured State of Health (SoH %)</div></div>
        <div class="kpi"><div class="v">${c.in_repair || 1}</div><div class="k">Packs in Repair / Service</div><div class="d">Cell balancing & module swap</div></div>
        <div class="kpi"><div class="v">${s.events}</div><div class="k">Lifecycle Events Logged</div><div class="d">Diagnostic tests & maintenance</div></div>
      </div>`;
    } else if (persona.role === 'RECYCLER') {
      const minSummary = c.minerals_tracked ? `${c.minerals_tracked.lithium_kg}kg Li · ${c.minerals_tracked.cobalt_kg}kg Co` : '112.9 kg';
      return `
      <div class="kpis">
        <div class="kpi"><div class="v">${c.second_life_storage || 2}</div><div class="k">Second-Life Solar Units</div><div class="d">Peenya &amp; Indiranagar BESS</div></div>
        <div class="kpi"><div class="v">${c.recycled || 1}</div><div class="k">Batteries Decommissioned</div><div class="d">Hydrometallurgical extraction</div></div>
        <div class="kpi"><div class="v">${minSummary}</div><div class="k">Tracked Critical Minerals</div><div class="d">EU Art 8 mass balance</div></div>
        <div class="kpi"><div class="v">95.4%</div><div class="k">Mineral Recovery Rate</div><div class="d">Closed-loop hydrometallurgy</div></div>
      </div>`;
    } else {
      // REGULATOR
      return `
      <div class="kpis">
        <div class="kpi"><div class="v">${a.ok ? 'Verified' : 'Flagged'}</div><div class="k">SHA-256 Ledger Audit</div><div class="d">Cryptographic chain integrity</div></div>
        <div class="kpi"><div class="v">${s.issues_high || 2}</div><div class="k">Data Quality Anomalies</div><div class="d">Seeded educational rule alerts</div></div>
        <div class="kpi"><div class="v">${c.avg_carbon_intensity ? c.avg_carbon_intensity + ' kg' : '49.8 kg'}</div><div class="k">Avg Carbon Intensity</div><div class="d">kg CO₂e/kWh (EU Class A/B)</div></div>
        <div class="kpi"><div class="v">${s.events}</div><div class="k">Audited Transactions</div><div class="d">Tamper-evident event records</div></div>
      </div>`;
    }
  };

  // Role Dedicated Panel
  const renderRolePanel = () => {
    if (persona.role === 'MANUFACTURER') {
      const unassigned = packs.filter(p => !p.host_product && p.status === 'ACTIVE');
      return `
      <section class="panel">
        <header>
          <div>
            <h2>🏭 Gigafactory Assembly Line &amp; Unassigned Battery Stock</h2>
            <p>Batteries manufactured and ready for vehicle installation</p>
          </div>
          <button class="btn sm primary" data-act="move">Link to Vehicle</button>
        </header>
        ${table([
          { h: 'Battery Pack' },
          { h: 'Chemistry & Size' },
          { h: 'Production Batch' },
          { h: 'Current Location' },
          { h: 'Factory Health' },
          { h: 'Passport' },
          { h: '' }
        ], unassigned.map(p => [
          `${assetLink(p.asset_code)}<div class="small faint">Awaiting Car Fitment</div>`,
          formatChem(p.chemistry) + `<div class="small">${formatCapacity(p.capacity_kwh)}</div>`,
          `<span class="mono">${esc(p.batch_code || '—')}</span>`,
          formatLocation(p.current_location),
          formatSoh(p.latest_soh, p.latest_cycles),
          p.passport_id ? `<span class="st ok">${esc(p.passport_id)}</span>` : '<span class="st warn">Pending</span>',
          `<button class="btn sm" data-act="move" data-code="${esc(p.asset_code)}">Install in Car</button>`
        ]), { empty: 'All manufactured batteries have been assigned to vehicles.' })}
      </section>`;
    } else if (persona.role === 'SERVICE') {
      const inFleet = packs.filter(p => p.host_product || p.status === 'IN_REPAIR');
      return `
      <section class="panel">
        <header>
          <div>
            <h2>🚗 Live Electric Vehicle Fleet Health &amp; Diagnostics Monitoring</h2>
            <p>Monitors State of Health (SoH %), charge cycles, and service status of vehicles on road</p>
          </div>
          <button class="btn sm primary" data-act="diagnostic">Record Test</button>
        </header>
        ${table([
          { h: 'Vehicle / Application' },
          { h: 'Battery Pack' },
          { h: 'Current Depot Location' },
          { h: 'State of Health (SoH %)' },
          { h: 'Status' },
          { h: 'Action' }
        ], inFleet.map(p => [
          formatHostProduct(p.host_product),
          assetLink(p.asset_code),
          formatLocation(p.current_location),
          formatSoh(p.latest_soh, p.latest_cycles),
          friendlyStatus(p.status),
          `<button class="btn sm primary" data-act="diagnostic" data-code="${esc(p.asset_code)}">🩺 Log Health Test</button>`
        ]))}
      </section>`;
    } else if (persona.role === 'RECYCLER') {
      const circPacks = packs.filter(p => p.status === 'SECOND_LIFE' || p.status === 'RECYCLED');
      return `
      <section class="panel">
        <header>
          <div>
            <h2>♻️ Second-Life Solar Energy Storage &amp; Material Recovery Facility</h2>
            <p>Repurposed microgrid batteries and hydrometallurgical mineral extraction</p>
          </div>
          <button class="btn sm primary" data-act="event">Record Decommission</button>
        </header>
        ${table([
          { h: 'Battery Pack' },
          { h: 'Application / Facility' },
          { h: 'Current Location' },
          { h: 'Remaining Capacity' },
          { h: 'Circularity Status' },
          { h: 'Passport State' },
          { h: '' }
        ], circPacks.map(p => [
          assetLink(p.asset_code),
          formatHostProduct(p.host_product),
          formatLocation(p.current_location),
          formatSoh(p.latest_soh, p.latest_cycles),
          friendlyStatus(p.status),
          p.passport_id ? `<span class="st ${p.status === 'RECYCLED' ? 'bad' : 'ok'}">${esc(p.passport_id)}</span>` : '<span class="st">Closed</span>',
          `<a class="btn sm" href="#/lineage/${encodeURIComponent(p.asset_code)}">Inspect</a>`
        ]), { empty: 'No second-life or recycled batteries recorded.' })}
      </section>`;
    } else {
      // REGULATOR
      return `
      <section class="panel">
        <header>
          <div>
            <h2>🛡️ Cryptographic Ledger Integrity &amp; Statutory Compliance</h2>
            <p>SHA-256 tamper-proof chain verification &amp; regulatory anomaly detection</p>
          </div>
          <button class="btn sm primary" data-act="verify">Verify Hash Chain</button>
        </header>
        <div class="body">
          <div class="notice ${a.ok ? 'ok' : 'bad'}">
            <b>${a.ok ? '✅ Cryptographic SHA-256 Ledger Verified' : '❌ Ledger Tampering Detected'}</b><br>
            Verified ${a.checked} consecutive lifecycle transactions. Tip hash: <span class="mono">${esc(a.tip_hash)}</span>.
          </div>
          <div class="toolbar" style="margin-bottom:0">
            <span class="small muted">Data quality alerts detected in database: <b>${s.issues_high} high-severity findings</b> (seeded for laboratory demonstration).</span>
            <a class="btn sm" href="#/quality">Review Audit Findings</a>
          </div>
        </div>
      </section>`;
    }
  };

  page.innerHTML = `
  <!-- Role Persona Hero Banner -->
  <section class="persona-card" style="--role-color:${persona.accentColor}; --role-bg:${persona.bgColor}; --role-border:${persona.borderColor};">
    <div class="persona-head">
      <div class="persona-title-group">
        <div class="persona-icon">${persona.quickActions[0].icon}</div>
        <div>
          <h2>${esc(persona.title)}</h2>
          <div class="org-name">${esc(persona.org)}</div>
        </div>
      </div>
      <span class="persona-badge">${esc(persona.badge)}</span>
    </div>
    <div class="persona-desc">${esc(persona.summary)}</div>
    <div class="persona-actions">
      <span class="small faint" style="margin-right:4px;">Permitted Operations:</span>
      ${persona.quickActions.map(qa => qa.href ?
        `<a class="btn sm ${qa.cls}" href="${qa.href}">${qa.icon} ${esc(qa.label)}</a>` :
        `<button class="btn sm ${qa.cls}" data-act="${qa.act}">${qa.icon} ${esc(qa.label)}</button>`
      ).join('')}
    </div>
  </section>

  <!-- Role-Tailored KPIs -->
  ${renderKpis()}

  <!-- Role-Tailored Main Panel -->
  ${renderRolePanel()}

  <!-- Global Tracked Battery Inventory (Rich Generalised View) -->
  <section class="panel">
    <header>
      <div>
        <h2>⚡ Complete Tracked Battery Inventory (Live Database View)</h2>
        <p>Every battery pack, host vehicle, current location, and health diagnostic</p>
      </div>
      <a class="btn sm" href="#/assets?type=BATTERY_PACK">Filter All Assets</a>
    </header>
    ${table([
      { h: 'Battery Pack' },
      { h: 'Vehicle / Application' },
      { h: 'Current Location' },
      { h: 'Battery Health' },
      { h: 'Chemistry & Size' },
      { h: 'Lifecycle Status' },
      { h: 'Digital Passport' },
      { h: 'Action' }
    ], packs.map(p => [
      `${assetLink(p.asset_code)}<div class="small faint">${esc(p.batch_code || 'no batch')}</div>`,
      formatHostProduct(p.host_product),
      formatLocation(p.current_location),
      formatSoh(p.latest_soh, p.latest_cycles),
      formatChem(p.chemistry) + `<div class="small">${formatCapacity(p.capacity_kwh)}</div>`,
      friendlyStatus(p.status),
      p.passport_id ? `<button class="btn sm" data-act="passcard" data-code="${esc(p.asset_code)}">📜 ${esc(p.passport_id)}</button>` : '<span class="st warn">None</span>',
      `<a class="btn sm" href="#/lineage/${encodeURIComponent(p.asset_code)}">Inspect</a>`
    ]))}
  </section>

  <!-- Recent Ledger Activity -->
  <section class="panel">
    <header>
      <div>
        <h2>Latest Lifecycle &amp; Maintenance Events</h2>
        <p>Real-time stream of manufacturing, diagnostics, and repairs</p>
      </div>
      <a href="#/ledger" class="small">Open Full Ledger</a>
    </header>
    ${table([
      { h: 'Date' },
      { h: 'Battery / Asset' },
      { h: 'Event Type' },
      { h: 'Facility & Location' },
      { h: 'Logged Notes' },
      { h: 'Evidence' }
    ], ev.items.map(e => [
      d10(e.event_at),
      assetLink(e.asset_code),
      `<span class="badge" style="font-weight:700;">${esc(e.event_type.replaceAll('_', ' '))}</span>`,
      `${esc(e.organization)}<div class="small faint">📍 ${esc(e.location)}</div>`,
      `<span class="small">${esc(e.notes || '—')}</span>`,
      st(e.evidence_status)
    ]))}
  </section>`;
};

function assetQueryString(extra = {}) {
  const p = new URLSearchParams(); const q = { ...S.aq, ...extra };
  for (const k of ['q', 'status', 'type', 'sort']) if (q[k]) p.set(k, q[k]);
  p.set('limit', PAGE); p.set('offset', q.offset); return p.toString();
}

PAGES.assets = async page => {
  page.innerHTML = `
  <form class="toolbar" id="assetFilters" role="search">
    <div class="grow"><label class="l" for="fq">Search battery code, vehicle, chemistry, batch, or manufacturer</label><input class="field" id="fq" type="search" value="${esc(S.aq.q)}" autocomplete="off" placeholder="e.g. NEXON, LFP, Bengaluru, PACK-1001…"></div>
    <div class="fix"><label class="l" for="fs">Status</label><select class="field" id="fs"><option value="">All Statuses</option>${['ACTIVE', 'IN_REPAIR', 'SECOND_LIFE', 'RECYCLED', 'RETIRED'].map(v => `<option ${S.aq.status === v ? 'selected' : ''} value="${v}">${v.replace('_', ' ').toLowerCase()}</option>`).join('')}</select></div>
    <div class="fix"><label class="l" for="ft">Type</label><select class="field" id="ft"><option value="">All Types</option>${['BATTERY_PACK', 'VEHICLE', 'STORAGE_SYSTEM', 'MODULE', 'CELL'].map(v => `<option ${S.aq.type === v ? 'selected' : ''} value="${v}">${typeName(v)}</option>`).join('')}</select></div>
    <div class="fix"><label class="l" for="fo">Sort By</label><select class="field" id="fo">${[['type', 'Type & Code'], ['code', 'Code'], ['status', 'Status'], ['last_event', 'Latest Event']].map(([v, n]) => `<option ${S.aq.sort === v ? 'selected' : ''} value="${v}">${n}</option>`).join('')}</select></div>
    <a class="btn" id="csvLink" href="#">Export CSV</a>
  </form>
  <section class="panel"><header><h2>Asset &amp; Vehicle Register</h2><p id="assetMeta"></p></header><div id="assetTable">${loading()}</div></section>`;
  await loadAssets();
};

async function loadAssets() {
  const box = $('#assetTable'); if (!box) return;
  try {
    const r = await api('/api/assets?' + assetQueryString());
    $('#csvLink').href = '/api/assets.csv?' + assetQueryString({ offset: 0 });
    $('#assetMeta').textContent = r.total ? `${r.offset + 1}–${Math.min(r.offset + r.items.length, r.total)} of ${r.total}` : '0 records';
    
    box.innerHTML = table([
      { h: 'Asset Code' },
      { h: 'Vehicle / Application' },
      { h: 'Current Location' },
      { h: 'State of Health' },
      { h: 'Chemistry & Size' },
      { h: 'Status' },
      { h: 'Passport' },
      { h: 'Parents', num: 1 },
      { h: '' }
    ], r.items.map(a => [
      `${assetLink(a.asset_code)}<div class="small faint">${typeName(a.asset_type)}</div>`,
      a.asset_type === 'BATTERY_PACK' ? formatHostProduct(a.host_product) : (a.asset_type === 'VEHICLE' || a.asset_type === 'STORAGE_SYSTEM' ? formatHostProduct(a.asset_code) : '<span class="faint">—</span>'),
      formatLocation(a.current_location),
      formatSoh(a.latest_soh, a.latest_cycles),
      formatChem(a.chemistry) + `<div class="small">${formatCapacity(a.capacity_kwh)}</div>`,
      friendlyStatus(a.status),
      a.passport_id ? `<button class="btn sm" data-act="passcard" data-code="${esc(a.asset_code)}">📜 v${esc(a.passport_version)}</button>` : (a.asset_type === 'BATTERY_PACK' && !['RECYCLED', 'RETIRED'].includes(a.status) ? '<span class="st warn">None</span>' : '<span class="faint">—</span>'),
      a.open_parents > 1 ? `<span class="sev-HIGH">${a.open_parents} (Conflict)</span>` : a.open_parents,
      `<a class="btn sm" href="#/lineage/${encodeURIComponent(a.asset_code)}">Inspect</a>`
    ]), { empty: 'No assets match these search filters.' }) +
    (r.total > PAGE ? `<div class="pager"><button class="btn sm" data-act="apage" data-d="-1" ${r.offset === 0 ? 'disabled' : ''}>Previous</button><span>Page ${Math.floor(r.offset / PAGE) + 1} of ${Math.ceil(r.total / PAGE)}</span><button class="btn sm" data-act="apage" data-d="1" ${r.offset + PAGE >= r.total ? 'disabled' : ''}>Next</button></div>` : '');
  } catch (e) { box.innerHTML = errState(e); }
}

function renderAssemblyTree(d, curCode) {
  const rels = d.relationships.filter(r => !r.valid_to);
  if (!rels.length) return '';
  const pMap = {}, allParents = new Set(), allChildren = new Set();
  rels.forEach(r => {
    pMap[r.p_code] = pMap[r.p_code] || [];
    pMap[r.p_code].push(r);
    allParents.add(r.p_code);
    allChildren.add(r.c_code);
  });
  let roots = [...allParents].filter(p => !allChildren.has(p));
  if (!roots.length) roots = [d.asset.asset_code];
  const nodeMap = Object.fromEntries(d.nodes.map(n => [n.asset_code, n]));
  const renderBranch = code => {
    const n = nodeMap[code] || { asset_code: code, asset_type: 'COMPONENT', status: 'ACTIVE' };
    const kids = pMap[code] || [];
    const isCur = code === curCode;
    return `<div class="tree-branch" role="treeitem" aria-expanded="${kids.length ? 'true' : 'false'}" aria-label="${esc(code)} (${typeName(n.asset_type)})">
      <a href="#/lineage/${encodeURIComponent(code)}" class="tree-node ${isCur ? 'current' : ''}" aria-current="${isCur ? 'true' : 'false'}">
        <b>${esc(code)}</b>
        <span class="badge">${typeName(n.asset_type)}</span>
        ${st(n.status)}
      </a>
    </div>
    ${kids.length ? `<div class="tree-level" role="group">${kids.map(k => renderBranch(k.c_code)).join('')}</div>` : ''}`;
  };
  return `<section class="panel" aria-label="Assembly component hierarchy">
    <header><h2>Assembly Component Hierarchy (Bill of Materials)</h2><p>Active containment tree · Click any component to navigate</p></header>
    <div class="body"><div class="tree-box" role="tree" aria-label="Bill of Materials Containment Tree">${roots.map(r => renderBranch(r)).join('')}</div></div>
  </section>`;
}

PAGES.lineage = async (page, code) => {
  const codes = (await api('/api/assets?limit=200&sort=code')).items.map(a => a.asset_code);
  if (!code) code = codes.includes('PACK-NEXON-02') ? 'PACK-NEXON-02' : codes[0];
  page.innerHTML = `
  <form class="toolbar" id="goAsset">
    <div class="grow"><label class="l" for="gc">Select or type an Asset / Battery Code</label><input class="field" id="gc" list="gcl" value="${esc(code)}" autocomplete="off"><datalist id="gcl">${codes.map(c => `<option value="${esc(c)}">`).join('')}</datalist></div>
    <button class="btn primary">Inspect Battery</button>
  </form>
  <div id="assetBody">${loading()}</div>`;
  const body = $('#assetBody');
  try {
    const d = await api('/api/lineage/' + encodeURIComponent(code)); const a = d.asset;
    S.currentLineage = d;
    const canMove = ['CELL', 'MODULE', 'BATTERY_PACK'].includes(a.asset_type) && !['RECYCLED', 'RETIRED'].includes(a.status);
    const canTest = ['CELL', 'MODULE', 'BATTERY_PACK', 'STORAGE_SYSTEM'].includes(a.asset_type) && !['RECYCLED', 'RETIRED'].includes(a.status);
    const hasPassport = Boolean(d.passport || (d.passport_history && d.passport_history.length));
    const openParents = d.relationships.filter(r => r.c_code === a.asset_code && !r.valid_to);
    const latestTest = d.tests && d.tests[0];
    const latestEv = d.events && d.events[d.events.length - 1];

    body.innerHTML = `
    <section class="panel">
      <header>
        <div>
          <h2><span class="mono">${esc(a.asset_code)}</span> · ${typeName(a.asset_type)}</h2>
          <p>Manufacturer: <b>${esc(a.manufacturer)}</b> · Registered on ${d10(a.created_at)}</p>
        </div>
        <div>${friendlyStatus(a.status)}</div>
      </header>
      <div class="body">
        <div class="facts">
          <div><dt>Host Vehicle / Application</dt><dd>${openParents.length ? formatHostProduct(openParents[0].p_code) : '<span class="veh-tag unassigned">Warehouse Inventory</span>'}</dd></div>
          <div><dt>Current Physical Location</dt><dd>${formatLocation(latestEv ? latestEv.location : 'Hosur Plant')}</dd></div>
          <div><dt>Chemistry</dt><dd>${formatChem(a.chemistry)}</dd></div>
          <div><dt>Rated Capacity</dt><dd>${formatCapacity(a.capacity_kwh)}</dd></div>
          <div><dt>State of Health (SoH)</dt><dd>${latestTest ? formatSoh(latestTest.state_of_health_pct, latestTest.cycle_count) : '<span class="small muted">Initial factory state</span>'}</dd></div>
          <div><dt>Production Batch</dt><dd class="mono">${esc(a.batch_code || 'Not recorded')}</dd></div>
          <div><dt>Digital Passport</dt><dd>${d.passport ? `<b>${esc(d.passport.passport_id)}</b> (v${esc(d.passport.passport_version)})` : '<span class="st warn">None</span>'}</dd></div>
          <div><dt>Circularity Use Case</dt><dd>${a.status === 'SECOND_LIFE' ? '⚡ Clean Solar Energy Storage' : a.status === 'RECYCLED' ? '♻️ Hydrometallurgical Extraction' : '🚗 Electric Vehicle Mobility'}</dd></div>
        </div>

        ${openParents.length > 1 ? `<div class="notice bad"><b>Data Quality Warning:</b> This component has ${openParents.length} open parent links recorded simultaneously. See <a href="#/quality">Data quality</a> to resolve this overlap.</div>` : ''}

        <div class="toolbar" style="margin-top:16px;margin-bottom:0;">
          <button class="btn primary" data-act="event" data-code="${esc(a.asset_code)}">📝 Record Lifecycle Event</button>
          ${canTest ? `<button class="btn" data-act="diagnostic" data-code="${esc(a.asset_code)}">🩺 Record Health Diagnostic</button>` : ''}
          ${canMove ? `<button class="btn" data-act="move" data-code="${esc(a.asset_code)}">🔁 Move / Transfer Component</button>` : ''}
          ${hasPassport ? `<button class="btn" data-act="passcard" data-code="${esc(a.asset_code)}">📜 View Digital Passport Card</button>` : ''}
          <a class="btn" href="#/recall?codes=${encodeURIComponent(a.asset_code)}&direction=up">🔎 Where is it used? (Upstream)</a>
          ${['BATTERY_PACK', 'MODULE', 'VEHICLE', 'STORAGE_SYSTEM'].includes(a.asset_type) ? `<a class="btn" href="#/recall?codes=${encodeURIComponent(a.asset_code)}&direction=down">🔍 What is inside? (Downstream)</a>` : ''}
        </div>
      </div>
    </section>

    ${renderAssemblyTree(d, a.asset_code)}

    ${(d.carbon || d.minerals) ? `
    <div class="grid2">
      ${d.carbon ? `
      <section class="panel">
        <header>
          <div>
            <h2>Statutory Carbon Footprint (EU 2023/1542 Article 7)</h2>
            <p>Harmonized GHG declaration · Certified by ${esc(d.carbon.certified_by)}</p>
          </div>
          <span class="carbon-class-badge class-${d.carbon.carbon_class.toLowerCase()}">Class ${esc(d.carbon.carbon_class)}</span>
        </header>
        <div class="body">
          <div class="facts">
            <div><dt>Total Lifecycle Intensity</dt><dd><b>${Number(d.carbon.total_kg_co2e_per_kwh).toFixed(1)} kg CO₂e / kWh</b></dd></div>
            <div><dt>Raw Material Acquisition</dt><dd>${d.carbon.raw_material_kg_co2e} kg CO₂e</dd></div>
            <div><dt>Cell &amp; Pack Manufacturing</dt><dd>${d.carbon.manufacturing_kg_co2e} kg CO₂e</dd></div>
            <div><dt>Distribution Logistics</dt><dd>${d.carbon.transport_kg_co2e} kg CO₂e</dd></div>
            <div><dt>Recycling Offset Credit</dt><dd class="offset-val"><b>${d.carbon.recycling_offset_kg_co2e} kg CO₂e</b></dd></div>
            <div><dt>Declaration Date</dt><dd>${esc(d.carbon.declared_at)}</dd></div>
          </div>
        </div>
      </section>` : ''}

      ${d.minerals ? `
      <section class="panel">
        <header>
          <div>
            <h2>Critical Minerals &amp; Recycled Content (EU Art 8 / India BWMR)</h2>
            <p>Secondary raw material mass balance &amp; EPR compliance</p>
          </div>
          <span class="epr-pill">EPR: ${esc(d.minerals.epr_certificate_id || 'Compliant')}</span>
        </header>
        <div class="body">
          <div class="facts">
            <div><dt>Lithium (Li)</dt><dd><b>${d.minerals.lithium_kg} kg</b> <span class="small ${d.minerals.recycled_lithium_pct >= 6 ? 'target-met' : 'faint'}">(${d.minerals.recycled_lithium_pct}% recycled)</span></dd></div>
            <div><dt>Cobalt (Co)</dt><dd><b>${d.minerals.cobalt_kg} kg</b> <span class="small ${d.minerals.recycled_cobalt_pct >= 16 ? 'target-met' : 'faint'}">(${d.minerals.recycled_cobalt_pct}% recycled)</span></dd></div>
            <div><dt>Nickel (Ni)</dt><dd><b>${d.minerals.nickel_kg} kg</b> <span class="small ${d.minerals.recycled_nickel_pct >= 6 ? 'target-met' : 'faint'}">(${d.minerals.recycled_nickel_pct}% recycled)</span></dd></div>
            <div><dt>Manganese (Mn)</dt><dd><b>${d.minerals.manganese_kg} kg</b></dd></div>
            <div><dt>2031 EU Statutory Mandate</dt><dd><span class="small muted">Li ≥6%, Co ≥16%, Ni ≥6%</span></dd></div>
            <div><dt>MoEFCC EPR Status</dt><dd><span class="st ok">EPR Active</span></dd></div>
          </div>
        </div>
      </section>` : ''}
    </div>` : ''}

    <div class="grid2">
      <section class="panel">
        <header><h2>Dated Parent &amp; Host Links</h2><p>Intervals are [from, to): “to” is exclusive</p></header>
        ${table([{ h: 'Parent → Child' }, { h: 'Link Type' }, { h: 'Valid From' }, { h: 'Valid To' }, { h: 'Link State' }], d.relationships.map(r => [`${assetLink(r.p_code)} → ${assetLink(r.c_code)}`, esc(r.relationship_type.replaceAll('_', ' ').toLowerCase()), d10(r.valid_from), r.valid_to ? d10(r.valid_to) : '—', r.valid_to ? '<span class="st">Closed</span>' : '<span class="st ok">Open</span>']), { empty: 'No recorded containment links.' })}
      </section>

      <section class="panel">
        <header><h2>Digital Passport Version Succession</h2><p>Each version points to the previous version</p></header>
        <div class="body">
          ${d.passport_history.length ? `<div class="chain">${[...d.passport_history].reverse().map((p, i) => `${i ? '<span aria-hidden="true">→</span>' : ''}<span class="node ${p.status === 'ACTIVE' ? 'active' : ''}"><b>${esc(p.passport_id)}</b> v${esc(p.passport_version)} · ${esc(p.status.toLowerCase())}<br><span class="faint">${d10(p.issued_at)}</span></span>`).join('')}</div>` : '<div class="state">No passport recorded.</div>'}
        </div>
      </section>
    </div>

    ${(d.tests && d.tests.length) ? `
    <section class="panel">
      <header><h2>Diagnostic Measurements (TestResult Table)</h2><p>${d.tests.length} tests recorded · Article 14 State of Health monitoring</p></header>
      ${table([
        { h: 'Timestamp' },
        { h: 'Test ID' },
        { h: 'State of Health' },
        { h: 'Cycle Count', num: 1 },
        { h: 'Internal Resistance' },
        { h: 'Temp' },
        { h: 'Predicted RUL', num: 1 },
        { h: 'Diagnostic Specialist' }
      ], d.tests.map(t => [
        esc(t.test_time),
        `<span class="mono">${esc(t.test_result_id)}</span>`,
        formatSoh(t.state_of_health_pct, t.cycle_count),
        t.cycle_count != null ? t.cycle_count.toLocaleString() + ' cycles' : '—',
        t.internal_resistance_mohm != null ? t.internal_resistance_mohm + ' mΩ' : '<span class="faint">—</span>',
        t.cell_temp_celsius != null ? t.cell_temp_celsius + ' °C' : '<span class="faint">—</span>',
        t.remaining_useful_life_cycles != null ? t.remaining_useful_life_cycles.toLocaleString() + ' cycles' : '<span class="faint">—</span>',
        esc(t.recorded_by || '—')
      ]))}
    </section>` : ''}

    <section class="panel">
      <header><h2>Lifecycle Event History</h2><p>${d.events.length} verified events</p></header>
      <div class="body">
        <ol class="timeline">${d.events.map(e => `<li><span class="mono"><b>${d10(e.event_at)}</b></span><div><b>${esc(e.event_type.replaceAll('_', ' '))}</b> · ${esc(e.organization)}, 📍 ${esc(e.location)}<div class="muted">${esc(e.notes || 'No notes.')}</div><div class="small faint">Event #${e.event_id} · ${st(e.evidence_status)} · Actor: ${esc(e.actor_id || 'no actor')}</div></div></li>`).join('') || '<li><span></span><div class="state">No events recorded.</div></li>'}</ol>
      </div>
    </section>`;
  } catch (e) { body.innerHTML = errState(e); }
};

PAGES.recall = async (page, _a, qs) => {
  const v = k => qs.get(k) || '';
  const scope = v('batch') ? 'batch' : 'codes';
  page.innerHTML = `
  <form class="panel" id="recallForm"><header><h2>Defect Recall &amp; Traceability Scope</h2><p>Recursive Common Table Expression (WITH RECURSIVE) traversal over AssetRelationship graph</p></header><div class="body">
    <div class="fgrid">
      <div><label class="l" for="rs">Start Search From</label><select class="field" id="rs"><option value="codes" ${scope === 'codes' ? 'selected' : ''}>Asset / Component Code(s)</option><option value="batch" ${scope === 'batch' ? 'selected' : ''}>Production Batch Code</option></select></div>
      <div><label class="l" for="rv" id="rvl">Search Value</label><input class="field" id="rv" value="${esc(v('batch') || v('codes') || 'NC-2024-W03')}" required><div class="hint" id="rvh"></div></div>
      <div><label class="l" for="rd">Search Direction</label><select class="field" id="rd"><option value="up" ${v('direction') !== 'down' ? 'selected' : ''}>Upstream: Where is it used? (Find affected vehicles)</option><option value="down" ${v('direction') === 'down' ? 'selected' : ''}>Downstream: What is inside? (Find components)</option></select></div>
      <div><label class="l" for="rm">Time Basis</label><select class="field" id="rm"><option value="CURRENT">Current active links only</option><option value="AS_OF">Links valid on a specific date</option><option value="ALL">All historical links</option></select></div>
      <div id="asofBox" hidden><label class="l" for="ra">As-of Date</label><input class="field" id="ra" type="date"></div>
      <div><label class="l" for="rx">Maximum Depth (1–12)</label><input class="field" id="rx" type="number" min="1" max="12" value="8"></div>
    </div>
    <div class="toolbar tight"><button class="btn primary" id="rbtn">⚡ Run Recursive Trace</button></div></div></form>
  <div id="recallOut"></div>`;
  const sync = () => { const b = $('#rs').value === 'batch'; $('#rvl').textContent = b ? 'Batch Code' : 'Asset Code(s), comma separated'; $('#rvh').textContent = b ? 'Example: NC-2024-W03 (traces all cells & packs from this batch)' : 'Example: CELL-1001-A1'; $('#asofBox').hidden = $('#rm').value !== 'AS_OF'; };
  $('#rs').onchange = sync; $('#rm').onchange = sync; sync();
  $('#recallForm').onsubmit = async ev => {
    ev.preventDefault(); const out = $('#recallOut'); out.innerHTML = loading('Tracing graph…'); $('#rbtn').disabled = true;
    const p = new URLSearchParams({ direction: $('#rd').value, mode: $('#rm').value, max_depth: $('#rx').value });
    p.set($('#rs').value === 'batch' ? 'batch' : 'codes', $('#rv').value.trim());
    if ($('#rm').value === 'AS_OF') p.set('as_of', $('#ra').value);
    try { const r = await api('/api/recall?' + p); S.lastRecall = { r, p: p.toString() }; renderRecall(out, r); }
    catch (e) { out.innerHTML = `<div class="notice bad" role="alert">${esc(e.message)}</div>`; }
    finally { $('#rbtn').disabled = false; }
  };
  if (v('codes') || v('batch')) $('#recallForm').requestSubmit();
};

function renderRecall(out, r) {
  const sc = r.scope; const byType = Object.entries(r.counts.by_type).map(([t, n]) => `${n} ${typeName(t).toLowerCase()}${n > 1 ? 's' : ''}`).join(', ');
  out.innerHTML = `
  <section class="panel"><header><h2>Recall Results: ${r.counts.affected_total} Affected Assets Identified</h2><div><a class="btn sm" href="/api/recall.csv?${esc(S.lastRecall.p)}">Download CSV</a> <button class="btn sm" data-act="recallJson">Download JSON</button></div></header><div class="body">
    <p><b>Scope:</b> ${sc.batch_code ? 'Batch ' + esc(sc.batch_code) : esc(sc.starts.join(', '))} · Direction ${esc(sc.direction)} · Mode: ${esc(sc.mode.toLowerCase().replace('_', ' '))}${sc.as_of ? ' ' + esc(sc.as_of) : ''} · Depth ≤ ${sc.max_depth}</p>
    <p class="muted">${esc(byType)}. ${r.counts.start_assets} starting asset${r.counts.start_assets > 1 ? 's' : ''}.</p>
    ${r.warnings.length ? `<div class="notice warn"><b>Uncertainty and gaps (${r.warnings.length})</b><ul class="plain">${r.warnings.map(w => `<li>${esc(w.message)}</li>`).join('')}</ul></div>` : '<div class="notice ok">No relationship gaps detected in recorded containment links.</div>'}
  </div>
  ${table([{ h: 'Depth', num: 1 }, { h: 'Asset' }, { h: 'Type' }, { h: 'Vehicle / Application' }, { h: 'Status' }, { h: 'Shortest Graph Path', wrap: 1 }, { h: 'Link Type' }],
    r.affected.map(x => [x.depth, assetLink(x.asset_code), typeName(x.asset_type), formatHostProduct(x.asset_code), friendlyStatus(x.status), `<span class="mono">${esc(x.path.join(' → '))}</span>`, x.is_start ? '<span class="st">Start</span>' : (x.via_closed_link ? '<span class="st warn">Past link</span>' : '<span class="st ok">Current</span>')]))}
  </section>`;
}

PAGES.ledger = async page => {
  page.innerHTML = `<form class="toolbar" id="evFilters"><div class="grow"><label class="l" for="eq">Search ledger notes, facility, location, or battery code</label><input class="field" id="eq" type="search" autocomplete="off" placeholder="e.g. Nexon, Inspection, Aster, Bengaluru…"></div>
    <div class="fix"><label class="l" for="et">Event Type</label><select class="field" id="et"><option value="">All Event Types</option></select></div>
    <button class="btn" type="button" data-act="verify">🛡️ Verify Hash Chain</button><button class="btn primary" type="button" data-act="event">📝 Record Event</button></form>
    <div id="verifyOut" class="live" role="status"></div><section class="panel"><header><h2>Lifecycle Event Ledger</h2><p id="evMeta"></p></header><div id="evTable">${loading()}</div></section>`;
  const types = S.meta.event_types; $('#et').innerHTML += types.map(t => `<option value="${t}">${t.replaceAll('_', ' ').toLowerCase()}</option>`).join('');
  S.evOffset = 0; let t; const go = () => { S.evOffset = 0; loadEvents(); };
  $('#eq').oninput = () => { clearTimeout(t); t = setTimeout(go, 250); }; $('#et').onchange = go; $('#evFilters').onsubmit = e => e.preventDefault();
  await loadEvents();
};

async function loadEvents() {
  const box = $('#evTable'); if (!box) return;
  const p = new URLSearchParams({ limit: PAGE, offset: S.evOffset || 0 }); if ($('#eq').value) p.set('q', $('#eq').value); if ($('#et').value) p.set('type', $('#et').value);
  try {
    const r = await api('/api/events?' + p); S.evItems = r.items; $('#evMeta').textContent = r.total ? `${r.offset + 1}–${r.offset + r.items.length} of ${r.total}` : '0 events';
    box.innerHTML = table([{ h: 'Date' }, { h: '#', num: 1 }, { h: 'Battery / Asset' }, { h: 'Event' }, { h: 'Facility & Location' }, { h: 'Actor Role' }, { h: 'Evidence' }, { h: 'Notes', wrap: 1 }, { h: '' }],
      r.items.map((e, i) => [d10(e.event_at), e.event_id, assetLink(e.asset_code), `<span class="badge" style="font-weight:700;">${esc(e.event_type.replaceAll('_', ' '))}</span>`, `${esc(e.organization)}<div class="small faint">📍 ${esc(e.location)}</div>`, `${esc(e.actor_id || '—')}<div class="small faint">${esc((e.actor_role || '').toLowerCase())}</div>`, st(e.evidence_status), esc(e.notes || '—'), `<button class="btn sm" data-act="evdetail" data-i="${i}">Details</button>`]), { empty: 'No events match.' }) +
      (r.total > PAGE ? `<div class="pager"><button class="btn sm" data-act="epage" data-d="-1" ${r.offset === 0 ? 'disabled' : ''}>Previous</button><span>Page ${Math.floor(r.offset / PAGE) + 1} of ${Math.ceil(r.total / PAGE)}</span><button class="btn sm" data-act="epage" data-d="1" ${r.offset + PAGE >= r.total ? 'disabled' : ''}>Next</button></div>` : '');
  } catch (e) { box.innerHTML = errState(e); }
}

PAGES.quality = async page => {
  const [rules, issues] = await Promise.all([api('/api/rules'), api('/api/issues')]);
  const cnt = id => issues.filter(i => i.rule_id === id).length;
  page.innerHTML = `
  <div class="notice warn"><b>Educational Testing Notice:</b> Two findings in the baseline database are deliberately seeded classroom defects (<code>DQ-001</code> and <code>DQ-002</code>) to demonstrate automated database integrity rules to evaluators.</div>
  <section class="panel"><header><h2>Data Quality Findings (${issues.length})</h2><p>Rule-based database integrity audits</p></header>
  ${table([{ h: 'Severity' }, { h: 'Rule ID' }, { h: 'Battery / Asset' }, { h: 'Anomaly Finding', wrap: 1 }, { h: 'Database Evidence' }, { h: 'Suggested Corrective Step', wrap: 1 }, { h: '' }],
    issues.map((i, n) => [`<span class="sev-${esc(i.severity)}">${esc(i.severity)}</span>`, esc(i.rule_id), i.asset_code === '—' ? '—' : assetLink(i.asset_code), esc(i.detail), `<span class="mono">${esc(i.evidence)}</span>`, `${esc(i.suggestion)}<div class="small faint">Limit: ${esc(i.limits)}</div>`,
      ['DQ-002', 'DQ-006'].includes(i.rule_id) ? `<button class="btn sm" data-act="closelink" data-n="${n}">Close link…</button>` : '']), { empty: 'No findings. All rules pass.' })}</section>
  <section class="panel"><header><h2>Rule Catalogue (SQL Stored Queries)</h2><p>Each rule is executable in the SQL Lab</p></header>
  ${table([{ h: 'Rule' }, { h: 'Severity' }, { h: 'Integrity Check' }, { h: 'Matches Now', num: 1 }, { h: 'SQL Definition', wrap: 1 }], rules.map(r => [esc(r.rule_id), esc(r.severity), esc(r.title), cnt(r.rule_id), `<details><summary>Show SQL</summary><pre class="code">${esc(r.sql)}</pre></details>`]))}</section>`;
  S.issues = issues;
};

PAGES.lab = async (page, tab) => {
  tab = ['schema', 'norm', 'sql', 'acid', 'exp', 'map', 'policy', 'neo4j'].includes(tab) ? tab : 'map';
  const tabs = [
    ['map', '🎓 Syllabus Map (Complete Guide)'],
    ['schema', 'Schema & ERD'],
    ['norm', 'Normalization Analysis'],
    ['sql', 'SQL Query Runner'],
    ['acid', 'ACID Transactions & Locking'],
    ['exp', 'Traversal Benchmarks'],
    ['policy', 'Global Battery Passport Policies'],
    ['neo4j', 'Neo4j Graph Projection']
  ];
  page.innerHTML = `<div class="tabs" role="tablist" aria-label="Architecture lab sections">${tabs.map(([k, n]) => `<button role="tab" id="tab-${k}" aria-selected="${k === tab}" data-act="labtab" data-t="${k}">${n}</button>`).join('')}</div><div id="labBody" role="tabpanel" aria-labelledby="tab-${tab}">${loading()}</div>`;
  const b = $('#labBody');
  if (tab === 'schema') {
    const s = await api('/api/schema'); const by = t => s.objects.filter(o => o.type === t);
    b.innerHTML = `<section class="panel"><header><h2>Entity-Relationship Diagram (Crow’s Foot ERD)</h2></header><div class="body"><img class="erd" src="/static/erd.svg" alt="Entity-Relationship Diagram"></div></section>
    <section class="panel"><header><h2>Database Tables</h2><p>Live from sqlite_master</p></header>${table([{ h: 'Table Name' }, { h: 'Rows', num: 1 }, { h: 'DDL Definition' }], by('table').map(o => [`<b>${esc(o.name)}</b>`, s.row_counts[o.name], `<details><summary>Show DDL</summary><pre class="code">${esc(o.sql)}</pre></details>`]))}</section>
    <div class="grid2"><section class="panel"><header><h2>Triggers (${by('trigger').length})</h2><p>Database-level active integrity enforcement</p></header>${table([{ h: 'Trigger Name' }, { h: 'Definition' }], by('trigger').map(o => [`<span class="mono">${esc(o.name)}</span>`, `<details><summary>Show SQL</summary><pre class="code">${esc(o.sql)}</pre></details>`]))}</section>
    <section class="panel"><header><h2>Views &amp; Indexes</h2></header>${table([{ h: 'Type' }, { h: 'Name' }, { h: 'On Table' }], [...by('view'), ...by('index')].map(o => [esc(o.type), `<span class="mono">${esc(o.name)}</span>`, esc(o.tbl_name)]))}</section></div>`;
  } else if (tab === 'norm') b.innerHTML = `<section class="panel"><header><h2>Database Normalization (1NF to BCNF Proofs)</h2></header><div class="body">${BTLab.normalization}</div></section>`;
  else if (tab === 'acid') b.innerHTML = `<section class="panel"><header><h2>Transactions, ACID Guarantees &amp; Concurrency Control</h2></header><div class="body">${BTLab.acid}</div></section>`;
  else if (tab === 'map') b.innerHTML = `<section class="panel"><header><h2>System Architecture &amp; Engineering Guide</h2><p>How the multi-tier architecture, data schemas, and persistence layer are designed</p></header><div class="body">${BTLab.syllabus}</div></section>`;
  else if (tab === 'policy') b.innerHTML = `<section class="panel"><header><h2>Global Battery Passport Policies &amp; Open-Source Architectures</h2></header><div class="body">${BTLab.policy}</div></section>`;
  else if (tab === 'sql') {
    const qs = await api('/api/lab-queries'); S.labq = qs;
    b.innerHTML = `<section class="panel"><header><h2>Interactive SQL Query Runner</h2><p>SELECT, WITH, EXPLAIN QUERY PLAN · Read-only sandbox</p></header><div class="body">
      <div class="fgrid"><div class="full"><label class="l" for="lq">Example Syllabus Queries</label><select class="field" id="lq">${qs.map((q, i) => `<option value="${i}">${esc(q.title)}  [${esc(q.concept)}]</option>`).join('')}</select></div>
      <div class="full"><label class="l" for="sqlbox">SQL Query</label><textarea class="field code" id="sqlbox" spellcheck="false">${esc(qs[0].sql)}</textarea></div></div>
      <div class="toolbar tight">
        <button class="btn primary" data-act="runsql">▶️ Run SQL Query</button>
        <button class="btn" data-act="explain">🔍 Explain Query Plan</button>
        <button class="btn" data-act="copysql">📋 Copy SQL</button>
        <button class="btn" data-act="clearsql">Clear</button>
      </div>
      <div id="sqlOut" role="status" aria-live="polite"></div></div></section>`;
    $('#lq').onchange = () => { $('#sqlbox').value = qs[$('#lq').value].sql; $('#sqlOut').innerHTML = ''; };
  } else if (tab === 'exp') {
    const r = await api('/api/benchmark');
    b.innerHTML = r.available === false ? `<div class="notice warn">No benchmark results have been generated yet. Run <span class="mono">python benchmarks/run_benchmark.py</span>.</div>` : renderBench(r);
  } else if (tab === 'neo4j') {
    const r = await api('/api/neo4j/status');
    b.innerHTML = `<section class="panel"><header><h2>Optional Neo4j Graph Projection</h2><p>SQLite remains authoritative; Neo4j is a graph read model for lineage experiments.</p></header><div class="body">
      <div class="notice ${r.available ? 'ok' : 'warn'}">${esc(r.message || (r.available ? `Connected to ${r.uri}` : 'Neo4j is not available.'))}</div>
      <p class="small muted">Run Neo4j locally, set <code>NEO4J_PASSWORD</code>, then sync the synthetic SQLite dataset. The sync operation replaces matching graph nodes and relationships but never changes SQLite.</p>
      <button class="btn primary" data-act="neo4jsync" ${r.configured ? '' : 'disabled'}>Sync SQLite to Neo4j</button>
      <div class="toolbar tight"><label class="l" for="neoCode">Asset code</label><input class="field" id="neoCode" value="PACK-1001" aria-label="Asset code for Neo4j lineage"><label class="l" for="neoDir">Direction</label><select class="field" id="neoDir"><option value="down">Downstream</option><option value="up">Upstream</option></select><button class="btn" data-act="neo4jtrace" ${r.available ? '' : 'disabled'}>Show graph lineage</button></div>
      <div id="neo4jOut" role="status" aria-live="polite"></div></div></section>`;
  }
};

function renderBench(r) {
  const e = r.environment;
  return `
  <section class="panel"><header><h2>Benchmark Environment</h2><p>${esc(r.generated_at)}</p></header><div class="body"><p class="mono">${esc(e.python)} · SQLite ${esc(e.sqlite)} · ${esc(e.platform)} · ${esc(e.cpus)} CPU</p></div></section>
  ${r.scales.map(sc => `<section class="panel"><header><h2>${sc.assets.toLocaleString()} Assets · ${sc.links.toLocaleString()} Links</h2><p>Graph traversal benchmark</p></header>
  ${table([{ h: 'Workload' }, { h: 'Strategy' }, { h: 'p50 ms', num: 1 }, { h: 'p95 ms', num: 1 }, { h: 'Result Size', num: 1 }], sc.results.map(x => [esc(x.workload), esc(x.strategy), x.p50_ms.toFixed(3), x.p95_ms.toFixed(3), x.result_size]))}</section>`).join('')}
  <section class="panel"><header><h2>Performance Findings &amp; Analysis</h2></header><div class="body"><ul class="plain">${r.notes.map(n => `<li>${esc(n)}</li>`).join('')}</ul></div></section>`;
}

/* ---------- Dialogs & Modals ---------- */
const dlg = $('#dlg');
function openDlg(html) { dlg.innerHTML = html; if (!dlg.open) dlg.showModal(); const f = $('[autofocus]', dlg) || $('input,select,textarea', dlg); f && f.focus(); }
function closeDlg() { if (dlg.open) dlg.close(); }
const head = t => `<header><h2 id="dlgTitle">${esc(t)}</h2><button type="button" class="btn sm" data-act="close" aria-label="Close dialog">✕</button></header>`;
const fe = (id, msg) => { const el = $('#' + id, dlg); if (el) { el.setAttribute('aria-invalid', 'true'); const e = $('#' + id + '-e', dlg); if (e) e.textContent = msg; } };
const clearErr = () => { $$('[aria-invalid]', dlg).forEach(e => e.removeAttribute('aria-invalid')); $$('.err', dlg).forEach(e => e.textContent = ''); };
const grp = (id, label, inner) => `<div><label class="l" for="${id}">${label}</label>${inner}<div class="err" id="${id}-e" role="alert"></div></div>`;
const today = () => new Date().toISOString().slice(0, 10);

const EFFECT = {
  RECYCLED: 'Irreversible action. Sets the battery to RECYCLED, closes its active passport, and terminates all active parent/child links on this date.',
  REPURPOSED: 'Sets the pack to SECOND_LIFE, supersedes its active passport and issues a new linked version for stationary solar storage.',
  REPAIR_STARTED: 'Sets the battery pack to IN_REPAIR.',
  REPAIRED: 'Returns the battery to ACTIVE service (or SECOND_LIFE if previously repurposed).'
};

async function openEvent(code = '') {
  const codes = (await api('/api/assets?limit=200&sort=code')).items;
  S.codeMap = Object.fromEntries(codes.map(a => [a.asset_code, a]));
  const u = S.users.find(x => x.user_id === S.user);
  openDlg(`<form id="evForm" novalidate>${head('Record Lifecycle Event')}<div class="body">
    <p class="small muted">Logging event as <b>${esc(u.display_name)}</b> (${esc(u.role.toLowerCase())}). This creates an immutable, SHA-256 hash-chained entry.</p>
    <div class="fgrid">
    ${grp('fc', 'Battery / Asset Code *', `<input class="field" id="fc" list="fcl" value="${esc(code)}" autocomplete="off" autofocus><datalist id="fcl">${codes.map(a => `<option value="${esc(a.asset_code)}">`).join('')}</datalist>`)}
    ${grp('ft2', 'Event Type *', `<select class="field" id="ft2"></select>`)}
    ${grp('fd', 'Event Date *', `<input class="field" id="fd" type="date" max="${today()}" value="${today()}">`)}
    ${grp('fo', 'Facility / Organization', `<input class="field" id="fo2" value="${esc(u.organization)}">`)}
    <div class="full">${grp('fl', 'Current Physical Location *', `<input class="field" id="fl" placeholder="e.g. Indiranagar Depot, Bengaluru">`)}</div>
    <div class="full">${grp('fn', 'Lifecycle Notes', `<textarea class="field" id="fn" maxlength="1000" rows="2" placeholder="Describe the physical condition or operation performed…"></textarea>`)}</div>
    ${grp('fr', 'Evidence Reference (Optional)', `<input class="field" id="fr" placeholder="e.g. Work order WO-4402 or test ticket">`)}
    ${grp('fv', 'Evidence Status', `<select class="field" id="fv"><option value="SELF_REPORTED">Self-reported by operator</option><option value="UNKNOWN">Unknown</option></select>`)}
    </div><div id="fx" class="notice" hidden></div>
    <label class="check" id="confirmBox" hidden><input type="checkbox" id="fk"><span>I confirm that this battery is being sent to recycling and this passport closure cannot be undone.</span></label>
    <div id="fe" class="err" role="alert"></div></div>
    <footer><button type="button" class="btn" data-act="close">Cancel</button><button class="btn primary" id="fsave">Save Event</button></footer></form>`);
  dlg.dataset.key = uuid();
  const refresh = () => {
    const a = S.codeMap[$('#fc').value.trim().toUpperCase()]; const allowedRole = new Set(S.meta.role_events[u.role]);
    const sel = $('#ft2'); const keep = sel.value;
    sel.innerHTML = S.meta.event_types.map(t => { const tr = S.meta.transitions[t]; const okRole = allowedRole.has(t); const okState = !a || tr.from.includes(a.status);
      return `<option value="${t}" ${okRole && okState ? '' : 'disabled'}>${t.replaceAll('_', ' ').toLowerCase()}${!okRole ? ' (role not permitted)' : !okState ? ` (not allowed while ${a.status.toLowerCase()})` : ''}</option>`; }).join('');
    if ([...sel.options].some(o => o.value === keep && !o.disabled)) sel.value = keep; else sel.value = ([...sel.options].find(o => !o.disabled) || sel.options[0]).value;
    const t = sel.value, fx = $('#fx'); fx.hidden = !EFFECT[t]; fx.textContent = EFFECT[t] || ''; fx.className = 'notice ' + (t === 'RECYCLED' ? 'bad' : 'warn');
    $('#confirmBox').hidden = t !== 'RECYCLED';
    $('#fsave').disabled = !allowedRole.size;
    if (!allowedRole.size) $('#fe').textContent = 'This role is read-only. Switch role in the header to record events.';
  };
  $('#fc').oninput = refresh; $('#ft2').onchange = refresh; refresh();
  $('#evForm').onsubmit = async ev => {
    ev.preventDefault(); clearErr(); let bad = false;
    const need = (id, msg) => { if (!$('#' + id).value.trim()) { fe(id, msg); bad = true; } };
    need('fc', 'Asset code is required.'); need('fl', 'Location is required.'); need('fd', 'Date is required.');
    if ($('#fc').value.trim() && !S.codeMap[$('#fc').value.trim().toUpperCase()]) { fe('fc', 'Unknown asset code.'); bad = true; }
    if ($('#ft2').value === 'RECYCLED' && !$('#fk').checked) { $('#fe').textContent = 'Please tick the confirmation checkbox to record a recycling event.'; bad = true; }
    if (bad) return;
    $('#fsave').disabled = true; $('#fsave').textContent = 'Saving…';
    try {
      const r = await api('/api/events', { body: { asset_code: $('#fc').value, event_type: $('#ft2').value, event_at: $('#fd').value, organization: $('#fo2').value, location: $('#fl').value, notes: $('#fn').value, evidence_ref: $('#fr').value, evidence_status: $('#fv').value, idempotency_key: dlg.dataset.key } });
      closeDlg(); flash(`${r.replayed ? 'Duplicate ignored. ' : ''}Event #${r.event_id} saved. Asset status is now ${r.new_status ? r.new_status.toLowerCase().replace('_', ' ') : 'updated'}.`); route();
    } catch (e) { $('#fe').textContent = e.message; $('#fsave').disabled = false; $('#fsave').textContent = 'Save Event'; }
  };
}

async function openMove(code = '') {
  const all = (await api('/api/assets?limit=200&sort=code')).items;
  const assetMap = Object.fromEntries(all.map(a => [a.asset_code, a]));

  openDlg(`<form id="mvForm" novalidate>${head('Link / Install Battery Component')}<div class="body">
    <!-- Visual Hierarchy Breadcrumb -->
    <div class="hierarchy-pill-bar" role="note" aria-label="Physical containment hierarchy">
      <span class="hp-step">🚗 Electric Car / ☀️ Solar</span>
      <span class="hp-arrow">➔ holds</span>
      <span class="hp-step">🔋 Battery Pack</span>
      <span class="hp-arrow">➔ holds</span>
      <span class="hp-step">📦 Module</span>
      <span class="hp-arrow">➔ holds</span>
      <span class="hp-step">⚡ Cell</span>
    </div>

    <!-- Quick Demo Presets for Teacher Demo -->
    <div class="preset-bar">
      <span class="preset-label">🎯 Teacher Demo Presets:</span>
      <button type="button" class="btn sm" id="pbtn-nexon">🚗 Install Pack into Tata Nexon EV</button>
      <button type="button" class="btn sm" id="pbtn-xuv">🚙 Install Pack into Mahindra XUV</button>
      <button type="button" class="btn sm" id="pbtn-solar">☀️ Repurpose Pack to Solar BESS</button>
    </div>

    <div class="fgrid">
      <div class="full">
        ${grp('mc', '1. Component / Battery to Install *', `<input class="field" id="mc" value="${esc(code)}" list="mcl" autocomplete="off" autofocus placeholder="Type or select a battery pack, module, or cell..."><datalist id="mcl">${all.filter(a => ['CELL', 'MODULE', 'BATTERY_PACK'].includes(a.asset_type) && !['RECYCLED', 'RETIRED'].includes(a.status)).map(a => `<option value="${esc(a.asset_code)}">${esc(a.asset_code)} · ${typeName(a.asset_type)}</option>`).join('')}</datalist>`)}
        <div id="mchint" class="field-hint" style="display:none;"></div>
      </div>

      <div class="full">
        ${grp('mp', '2. New Parent Host (Car, Solar Unit, or Pack) *', `<input class="field" id="mp" list="mpl" autocomplete="off" placeholder="Choose a valid parent vehicle or unit..."><datalist id="mpl"></datalist>`)}
        <div id="mphint" class="field-hint warn" style="display:none;"></div>
      </div>

      ${grp('md', 'Effective Transfer Date *', `<input class="field" id="md" type="date" max="${today()}" value="${today()}">`)}
      ${grp('ml', 'Facility Location', `<input class="field" id="ml" value="Indiranagar Fast-Charge Hub, Bengaluru">`)}

      <div class="full">
        ${grp('mr', 'Reason for Transfer *', `<textarea class="field" id="mr" rows="2" maxlength="1000" placeholder="e.g. Scheduled vehicle assembly line integration or battery swap…"></textarea>`)}
        <div class="reason-chips">
          <span class="small muted">Quick reasons:</span>
          <button type="button" class="chip-btn" data-reason="Scheduled factory vehicle assembly line integration">🏭 Factory Assembly</button>
          <button type="button" class="chip-btn" data-reason="Scheduled battery pack swap for routine fleet maintenance">🔧 Routine Fleet Swap</button>
          <button type="button" class="chip-btn" data-reason="Repurposed for stationary solar energy storage microgrid">☀️ Solar Second-Life</button>
        </div>
      </div>
    </div>
    <div id="me" class="err" role="alert"></div>
  </div>
  <footer><button type="button" class="btn" data-act="close">Cancel</button><button class="btn primary" id="msave">Complete Link</button></footer></form>`);

  dlg.dataset.key = uuid();

  // Dynamic filter function
  const updateParentDatalist = () => {
    const cVal = $('#mc').value.trim().toUpperCase();
    const child = assetMap[cVal];
    const mpl = $('#mpl');
    const chint = $('#mchint');
    const phint = $('#mphint');

    if (!child) {
      chint.style.display = 'none';
      phint.style.display = 'none';
      mpl.innerHTML = all.filter(a => ['MODULE', 'BATTERY_PACK', 'VEHICLE', 'STORAGE_SYSTEM'].includes(a.asset_type) && !['RECYCLED', 'RETIRED'].includes(a.status)).map(a => `<option value="${esc(a.asset_code)}">${esc(a.asset_code)} · ${typeName(a.asset_type)}</option>`).join('');
      return;
    }

    chint.style.display = 'block';
    if (child.asset_type === 'BATTERY_PACK') {
      chint.innerHTML = `🔋 <b>${esc(child.asset_code)} is a Battery Pack.</b> It must be installed into an <b>Electric Vehicle</b> or a <b>Solar Storage System</b>.`;
      const validParents = all.filter(a => ['VEHICLE', 'STORAGE_SYSTEM'].includes(a.asset_type) && !['RECYCLED', 'RETIRED'].includes(a.status));
      mpl.innerHTML = validParents.map(a => {
        const v = VEHICLE_CATALOG[a.asset_code];
        const label = v ? `${v.icon} ${v.name} (${a.asset_code})` : `${esc(a.asset_code)} · ${typeName(a.asset_type)}`;
        return `<option value="${esc(a.asset_code)}">${esc(label)}</option>`;
      }).join('');
    } else if (child.asset_type === 'MODULE') {
      chint.innerHTML = `📦 <b>${esc(child.asset_code)} is a Module.</b> It must be assembled into a <b>Battery Pack</b>.`;
      const validParents = all.filter(a => a.asset_type === 'BATTERY_PACK' && !['RECYCLED', 'RETIRED'].includes(a.status));
      mpl.innerHTML = validParents.map(a => `<option value="${esc(a.asset_code)}">🔋 ${esc(a.asset_code)} · Battery Pack</option>`).join('');
    } else if (child.asset_type === 'CELL') {
      chint.innerHTML = `⚡ <b>${esc(child.asset_code)} is an individual Cell.</b> It must be installed into a <b>Module</b>.`;
      const validParents = all.filter(a => a.asset_type === 'MODULE' && !['RECYCLED', 'RETIRED'].includes(a.status));
      mpl.innerHTML = validParents.map(a => `<option value="${esc(a.asset_code)}">📦 ${esc(a.asset_code)} · Module</option>`).join('');
    }

    // Check parent validity
    const pVal = $('#mp').value.trim().toUpperCase();
    const parent = assetMap[pVal];
    if (parent && child) {
      const allowed = {
        'CELL': ['MODULE'],
        'MODULE': ['BATTERY_PACK'],
        'BATTERY_PACK': ['VEHICLE', 'STORAGE_SYSTEM']
      }[child.asset_type] || [];
      if (!allowed.includes(parent.asset_type)) {
        phint.style.display = 'block';
        phint.innerHTML = `⚠️ Cannot link ${typeName(child.asset_type)} directly into ${typeName(parent.asset_type)}. Choose a valid ${allowed.map(typeName).join(' or ')}.`;
      } else {
        phint.style.display = 'none';
      }
    } else {
      phint.style.display = 'none';
    }
  };

  $('#mc').oninput = updateParentDatalist;
  $('#mp').oninput = updateParentDatalist;
  updateParentDatalist();

  // Reason chips handler
  $$('.chip-btn', dlg).forEach(btn => {
    btn.onclick = () => {
      $('#mr').value = btn.dataset.reason;
      $('#mr').focus();
    };
  });

  // Preset button handlers
  const setPreset = (childCode, parentCode, reason) => {
    $('#mc').value = childCode;
    updateParentDatalist();
    $('#mp').value = parentCode;
    $('#mr').value = reason;
    updateParentDatalist();
  };

  const pNexon = $('#pbtn-nexon');
  if (pNexon) pNexon.onclick = () => setPreset('PACK-NEXON-02', 'VEH-NEXON-EV', 'Scheduled factory vehicle assembly line integration');
  const pXuv = $('#pbtn-xuv');
  if (pXuv) pXuv.onclick = () => setPreset('PACK-XUV-01', 'VEH-XUV400', 'Scheduled electric SUV assembly line fitment');
  const pSolar = $('#pbtn-solar');
  if (pSolar) pSolar.onclick = () => setPreset('PACK-SOLAR-02', 'STORE-SOLAR-02', 'Repurposed for stationary solar energy storage microgrid');

  $('#mvForm').onsubmit = async ev => {
    ev.preventDefault(); clearErr(); let bad = false;
    for (const [id, m] of [['mc', 'Component is required.'], ['mp', 'New parent is required.'], ['md', 'Date is required.'], ['mr', 'A reason is required.']]) if (!$('#' + id).value.trim()) { fe(id, m); bad = true; }
    if (bad) return; $('#msave').disabled = true;
    try {
      const r = await api('/api/transfers', {
        body: {
          child_code: $('#mc').value.trim().toUpperCase(),
          new_parent_code: $('#mp').value.trim().toUpperCase(),
          effective_date: $('#md').value,
          reason: $('#mr').value.trim(),
          location: $('#ml').value.trim(),
          idempotency_key: dlg.dataset.key
        }
      });
      closeDlg();
      flash(r.closed_parent ? `Transferred from ${r.closed_parent} to ${$('#mp').value}.` : `Linked to ${$('#mp').value}.`);
      route();
    } catch (e) {
      $('#me').textContent = e.message;
      $('#msave').disabled = false;
    }
  };
}

async function openDiagnostic(code = '') {
  const codes = (await api('/api/assets?limit=200&sort=code')).items;
  S.codeMap = Object.fromEntries(codes.map(a => [a.asset_code, a]));
  const u = S.users.find(x => x.user_id === S.user);
  const nowTime = new Date().toISOString().slice(0, 16).replace('T', ' ');
  openDlg(`<form id="diagForm" novalidate>${head('Record Battery Health & Electrochemical Diagnostic (TestResult)')}<div class="body">
    <p class="small muted">Measures State of Health (SoH %), impedance, and degradation parameters for EU Article 14 statutory compliance. Authorized: <b>${esc(u.display_name)}</b> (${esc(u.role.toLowerCase())}).</p>
    <div class="fgrid">
      ${grp('dc', 'Battery Pack Code *', `<input class="field" id="dc" list="dcl" value="${esc(code)}" autocomplete="off" autofocus><datalist id="dcl">${codes.filter(a => !['RECYCLED','RETIRED'].includes(a.status)).map(a => `<option value="${esc(a.asset_code)}">`).join('')}</datalist>`)}
      ${grp('dt', 'Test Timestamp *', `<input class="field" id="dt" value="${nowTime}" placeholder="YYYY-MM-DD HH:MM">`)}
      ${grp('ds', 'State of Health (0.0 to 100.0 %) *', `<input class="field" id="ds" type="number" step="0.1" min="0" max="100" placeholder="e.g. 94.5">`)}
      ${grp('dcy', 'Total Lifetime Charge Cycles', `<input class="field" id="dcy" type="number" min="0" placeholder="e.g. 185">`)}
      ${grp('dir', 'Internal Resistance (mΩ)', `<input class="field" id="dir" type="number" step="0.1" min="0" placeholder="e.g. 24.5">`)}
      ${grp('dtemp', 'Cell Pack Temperature (°C)', `<input class="field" id="dtemp" type="number" step="0.1" placeholder="e.g. 28.5">`)}
      ${grp('dv', 'Cell Voltage Imbalance ΔV (mV)', `<input class="field" id="dv" type="number" step="0.1" min="0" placeholder="e.g. 12.0">`)}
      ${grp('drul', 'Predicted RUL (Remaining Cycles)', `<input class="field" id="drul" type="number" min="0" placeholder="e.g. 1450">`)}
      <div class="full">${grp('dl', 'Test Facility Location', `<input class="field" id="dl" value="Indiranagar Fast-Charge Hub, Bengaluru">`)}</div>
      <div class="full">${grp('dn', 'Diagnostic Engineering Notes', `<textarea class="field" id="dn" rows="2" maxlength="1000" placeholder="e.g. Electrochemical impedance spectroscopy & capacity fade analysis optimal"></textarea>`)}</div>
    </div>
    <div id="de" class="err" role="alert"></div>
  </div>
  <footer><button type="button" class="btn" data-act="close">Cancel</button><button class="btn primary" id="dsave">Save Diagnostic Test</button></footer></form>`);
  dlg.dataset.key = uuid();
  $('#diagForm').onsubmit = async ev => {
    ev.preventDefault(); clearErr(); let bad = false;
    if (!$('#dc').value.trim()) { fe('dc', 'Asset code is required.'); bad = true; }
    if (!$('#dt').value.trim()) { fe('dt', 'Test timestamp is required.'); bad = true; }
    const s = parseFloat($('#ds').value);
    if (isNaN(s) || s < 0 || s > 100) { fe('ds', 'State of health must be between 0 and 100%.'); bad = true; }
    if (bad) return;
    $('#dsave').disabled = true; $('#dsave').textContent = 'Saving…';
    try {
      const payload = {
        asset_code: $('#dc').value.trim().toUpperCase(),
        test_time: $('#dt').value.trim(),
        state_of_health_pct: s,
        cycle_count: $('#dcy').value ? parseInt($('#dcy').value) : null,
        internal_resistance_mohm: $('#dir').value ? parseFloat($('#dir').value) : null,
        cell_temp_celsius: $('#dtemp').value ? parseFloat($('#dtemp').value) : null,
        voltage_delta_mv: $('#dv').value ? parseFloat($('#dv').value) : null,
        remaining_useful_life_cycles: $('#drul').value ? parseInt($('#drul').value) : null,
        location: $('#dl').value.trim(),
        notes: $('#dn').value.trim(),
        idempotency_key: dlg.dataset.key
      };
      const r = await api('/api/diagnostics', { body: payload });
      closeDlg();
      flash(`Diagnostic test ${r.test_result_id} saved for ${r.asset_code} (${r.state_of_health_pct}% SoH).`);
      route();
    } catch (e) {
      $('#de').textContent = e.message;
      $('#dsave').disabled = false;
      $('#dsave').textContent = 'Save Diagnostic Test';
    }
  };
}

function openPassportCard(d) {
  const a = d.asset, p = d.passport || (d.passport_history && d.passport_history[0]);
  const latestTest = d.tests && d.tests[0];
  const soh = latestTest ? latestTest.state_of_health_pct : null;
  const cycles = latestTest ? latestTest.cycle_count : null;
  const latestEv = d.events && d.events[d.events.length - 1];
  const openParents = d.relationships ? d.relationships.filter(r => r.c_code === a.asset_code && !r.valid_to) : [];
  const hostVehicle = openParents.length ? VEHICLE_CATALOG[openParents[0].p_code] : null;

  const qrSvg = `<svg viewBox="0 0 29 29" fill="currentColor">
    <path d="M0,0 h7 v7 h-7 z M1,1 v5 h5 v-5 z M2,2 h3 v3 h-3 z M8,0 h2 v1 h-2 z M11,0 h1 v2 h-1 z M13,0 h1 v1 h-1 z M15,0 h1 v3 h-1 z M17,0 h2 v1 h-2 z M22,0 h7 v7 h-7 z M23,1 v5 h5 v-5 z M24,2 h3 v3 h-3 z M8,2 h1 v1 h-1 z M10,2 h2 v1 h-2 z M19,2 h1 v1 h-1 z M8,3 h2 v1 h-2 z M12,3 h1 v1 h-1 z M14,3 h1 v2 h-1 z M17,3 h1 v1 h-1 z M0,8 h1 v1 h-1 z M2,8 h2 v1 h-2 z M5,8 h1 v2 h-1 z M7,8 h3 v1 h-3 z M11,8 h2 v1 h-2 z M15,8 h3 v1 h-3 z M19,8 h2 v1 h-2 z M22,8 h1 v1 h-1 z M24,8 h2 v1 h-2 z M27,8 h1 v1 h-1 z M1,9 h1 v2 h-1 z M8,9 h2 v2 h-2 z M13,9 h1 v1 h-1 z M16,9 h1 v1 h-1 z M18,9 h1 v2 h-1 z M21,9 h2 v1 h-2 z M25,9 h1 v1 h-1 z M28,9 h1 v2 h-1 z M3,10 h1 v1 h-1 z M11,10 h1 v1 h-1 z M14,10 h2 v1 h-2 z M23,10 h1 v1 h-1 z M0,11 h1 v1 h-1 z M4,11 h1 v1 h-1 z M6,11 h3 v1 h-3 z M12,11 h1 v2 h-1 z M15,11 h2 v1 h-2 z M19,11 h1 v1 h-1 z M21,11 h1 v2 h-1 z M24,11 h3 v1 h-3 z M2,12 h1 v2 h-1 z M5,12 h1 v1 h-1 z M8,12 h1 v1 h-1 z M10,12 h1 v2 h-1 z M14,12 h1 v2 h-1 z M17,12 h2 v1 h-2 z M23,12 h1 v2 h-1 z M27,12 h2 v1 h-2 z M0,13 h1 v2 h-1 z M3,13 h2 v1 h-2 z M7,13 h1 v1 h-1 z M16,13 h1 v1 h-1 z M19,13 h2 v1 h-2 z M25,13 h1 v1 h-1 z M4,14 h2 v1 h-2 z M8,14 h1 v1 h-1 z M11,14 h2 v1 h-2 z M18,14 h1 v1 h-1 z M22,14 h1 v1 h-1 z M26,14 h2 v1 h-2 z M0,15 h2 v1 h-2 z M6,15 h1 v1 h-1 z M9,15 h2 v1 h-2 z M13,15 h2 v1 h-2 z M17,15 h1 v2 h-1 z M20,15 h2 v1 h-2 z M23,15 h2 v1 h-2 z M27,15 h1 v1 h-1 z M3,16 h1 v1 h-1 z M5,16 h1 v1 h-1 z M8,16 h1 v2 h-1 z M11,16 h1 v1 h-1 z M15,16 h2 v1 h-2 z M19,16 h1 v1 h-1 z M22,16 h1 v1 h-1 z M25,16 h2 v1 h-2 z M0,17 h1 v2 h-1 z M2,17 h2 v1 h-2 z M6,17 h1 v1 h-1 z M10,17 h2 v1 h-2 z M13,17 h1 v1 h-1 z M18,17 h1 v1 h-1 z M21,17 h1 v2 h-1 z M28,17 h1 v1 h-1 z M4,18 h2 v1 h-2 z M7,18 h1 v1 h-1 z M12,18 h1 v1 h-1 z M14,18 h2 v1 h-2 z M17,18 h1 v1 h-1 z M20,18 h1 v1 h-1 z M23,18 h2 v1 h-2 z M26,18 h2 v1 h-2 z M0,19 h2 v1 h-2 z M6,19 h2 v1 h-2 z M10,19 h1 v1 h-1 z M13,19 h1 v2 h-1 z M16,19 h2 v1 h-2 z M19,19 h1 v1 h-1 z M22,19 h2 v1 h-2 z M25,19 h1 v1 h-1 z M0,22 h7 v7 h-7 z M1,23 v5 h5 v-5 z M2,24 h3 v3 h-3 z M8,22 h1 v1 h-1 z M10,22 h1 v2 h-1 z M12,22 h2 v1 h-2 z M15,22 h2 v1 h-2 z M18,22 h2 v1 h-2 z M22,22 h1 v1 h-1 z M24,22 h2 v1 h-2 z M27,22 h1 v1 h-1 z M8,24 h1 v1 h-1 z M11,24 h1 v1 h-1 z M14,24 h1 v1 h-1 z M17,24 h2 v1 h-2 z M20,24 h2 v1 h-2 z M23,24 h1 v1 h-1 z M26,24 h2 v1 h-2 z M8,25 h2 v1 h-2 z M12,25 h1 v1 h-1 z M15,25 h1 v1 h-1 z M19,25 h1 v2 h-1 z M22,25 h2 v1 h-2 z M25,25 h1 v2 h-1 z M28,25 h1 v1 h-1 z M9,26 h1 v1 h-1 z M11,26 h1 v2 h-1 z M14,26 h2 v1 h-2 z M17,26 h1 v1 h-1 z M21,26 h1 v1 h-1 z M24,26 h1 v1 h-1 z M27,26 h1 v1 h-1 z M8,27 h1 v2 h-1 z M10,27 h1 v1 h-1 z M13,27 h1 v1 h-1 z M16,27 h2 v1 h-2 z M19,27 h1 v1 h-1 z M22,27 h1 v2 h-1 z M26,27 h1 v1 h-1 z M28,27 h1 v2 h-1 z M9,28 h2 v1 h-2 z M12,28 h2 v1 h-2 z M15,28 h1 v1 h-1 z M18,28 h1 v1 h-1 z M20,28 h2 v1 h-2 z M23,28 h2 v1 h-2 z M27,28 h1 v1 h-1 z"/>
  </svg>`;

  const carbonSec = d.carbon ? `
    <div class="dpp-section">
      <div class="dpp-sec-head">
        <h4>Statutory Carbon Footprint Declaration (EU 2023/1542 Article 7)</h4>
        <span class="carbon-class-badge class-${d.carbon.carbon_class.toLowerCase()}">Carbon Class ${esc(d.carbon.carbon_class)}</span>
      </div>
      <div class="carbon-kpi">
        <div class="c-val"><b>${Number(d.carbon.total_kg_co2e_per_kwh).toFixed(1)}</b> <span class="unit">kg CO₂e / kWh</span></div>
        <div class="c-cert">Certified by: <b>${esc(d.carbon.certified_by)}</b> · Declared ${esc(d.carbon.declared_at)}</div>
      </div>
      <div class="carbon-breakdown">
        <div class="cb-item"><span class="cb-lbl">Raw Materials</span><span class="cb-val">${d.carbon.raw_material_kg_co2e} kg</span></div>
        <div class="cb-item"><span class="cb-lbl">Manufacturing</span><span class="cb-val">${d.carbon.manufacturing_kg_co2e} kg</span></div>
        <div class="cb-item"><span class="cb-lbl">Transport</span><span class="cb-val">${d.carbon.transport_kg_co2e} kg</span></div>
        <div class="cb-item cb-offset"><span class="cb-lbl">Recycling Credit</span><span class="cb-val">${d.carbon.recycling_offset_kg_co2e} kg</span></div>
      </div>
    </div>` : '';

  const mineralsSec = d.minerals ? `
    <div class="dpp-section">
      <div class="dpp-sec-head">
        <h4>Critical Raw Materials &amp; Recycled Content (EU Art 8 &amp; India MoEFCC BWMR)</h4>
        <span class="epr-pill">EPR: ${esc(d.minerals.epr_certificate_id || 'Compliant')}</span>
      </div>
      <div class="mineral-grid">
        <div class="min-card">
          <div class="min-sym">Li</div>
          <div class="min-name">Lithium</div>
          <div class="min-mass">${d.minerals.lithium_kg} kg</div>
          <div class="min-rec ${d.minerals.recycled_lithium_pct >= 6 ? 'target-met' : ''}">${d.minerals.recycled_lithium_pct}% recycled <span class="target-lbl">(2031: ≥6%)</span></div>
        </div>
        <div class="min-card">
          <div class="min-sym">Co</div>
          <div class="min-name">Cobalt</div>
          <div class="min-mass">${d.minerals.cobalt_kg} kg</div>
          <div class="min-rec ${d.minerals.recycled_cobalt_pct >= 16 ? 'target-met' : ''}">${d.minerals.recycled_cobalt_pct}% recycled <span class="target-lbl">(2031: ≥16%)</span></div>
        </div>
        <div class="min-card">
          <div class="min-sym">Ni</div>
          <div class="min-name">Nickel</div>
          <div class="min-mass">${d.minerals.nickel_kg} kg</div>
          <div class="min-rec ${d.minerals.recycled_nickel_pct >= 6 ? 'target-met' : ''}">${d.minerals.recycled_nickel_pct}% recycled <span class="target-lbl">(2031: ≥6%)</span></div>
        </div>
        <div class="min-card">
          <div class="min-sym">Mn</div>
          <div class="min-name">Manganese</div>
          <div class="min-mass">${d.minerals.manganese_kg} kg</div>
          <div class="min-rec">—</div>
        </div>
      </div>
    </div>` : '';

  const advDiag = (latestTest && (latestTest.internal_resistance_mohm != null || latestTest.cell_temp_celsius != null || latestTest.voltage_delta_mv != null || latestTest.remaining_useful_life_cycles != null)) ? `
    <div class="dpp-section">
      <div class="dpp-sec-head">
        <h4>Electrochemical Telemetry &amp; RUL (Article 14 Monitoring)</h4>
        <span class="faint mono">${esc(latestTest.test_result_id)}</span>
      </div>
      <div class="telemetry-grid">
        <div class="tel-item"><span class="tel-lbl">Internal Resistance</span><b>${latestTest.internal_resistance_mohm != null ? latestTest.internal_resistance_mohm + ' mΩ' : '—'}</b></div>
        <div class="tel-item"><span class="tel-lbl">Pack Temperature</span><b>${latestTest.cell_temp_celsius != null ? latestTest.cell_temp_celsius + ' °C' : '—'}</b></div>
        <div class="tel-item"><span class="tel-lbl">Voltage Spread</span><b>${latestTest.voltage_delta_mv != null ? 'Δ ' + latestTest.voltage_delta_mv + ' mV' : '—'}</b></div>
        <div class="tel-item"><span class="tel-lbl">Predicted RUL</span><b>${latestTest.remaining_useful_life_cycles != null ? latestTest.remaining_useful_life_cycles.toLocaleString() + ' cycles' : '—'}</b></div>
      </div>
    </div>` : '';

  openDlg(`<div class="passcard" role="region" aria-label="Digital Battery Passport Certificate for ${esc(a.asset_code)}">
    <div class="dpp-top">
      <div>
        <span>Statutory Digital Battery Passport (EU 2023/1542 &amp; India BWMR)</span>
        <h3>${esc(a.asset_code)} · ${typeName(a.asset_type)}</h3>
      </div>
      <div style="display:flex; gap:8px; align-items:center;">
        ${d.carbon ? `<span class="carbon-class-badge class-${d.carbon.carbon_class.toLowerCase()}">Class ${esc(d.carbon.carbon_class)}</span>` : ''}
        <span class="dpp-badge ${p ? p.status.toLowerCase() : 'closed'}">${p ? esc(p.status) : 'UNREGISTERED'}</span>
      </div>
    </div>
    <div class="dpp-body">
      <dl class="dpp-spec">
        <div><dt>Passport ID</dt><dd class="mono">${p ? esc(p.passport_id) : '—'}</dd></div>
        <div><dt>Passport Version</dt><dd>${p ? 'v' + esc(p.passport_version) : '—'}${p && p.previous_passport_id ? ` <span class="faint">(from ${esc(p.previous_passport_id)})</span>` : ''}</dd></div>
        <div><dt>Host Vehicle / Product</dt><dd>${hostVehicle ? `${hostVehicle.icon} ${hostVehicle.name}` : (openParents.length ? openParents[0].p_code : 'Unassigned Inventory')}</dd></div>
        <div><dt>Current Location</dt><dd>${formatLocation(latestEv ? latestEv.location : 'Hosur Plant')}</dd></div>
        <div><dt>Manufacturer</dt><dd>${esc(a.manufacturer)}</dd></div>
        <div><dt>Chemistry</dt><dd>${formatChem(a.chemistry)}</dd></div>
        <div><dt>Rated Capacity</dt><dd>${formatCapacity(a.capacity_kwh)}</dd></div>
        <div><dt>Production Batch</dt><dd class="mono">${esc(a.batch_code || 'N/A')}</dd></div>
        <div><dt>State of Health (SoH)</dt><dd><b>${soh != null ? soh + '% SoH' : 'Pending test'}</b></dd></div>
        <div><dt>Lifetime Cycle Count</dt><dd>${cycles != null ? cycles.toLocaleString() + ' cycles' : 'Initial cycle'}</dd></div>
      </dl>
      <div class="dpp-qr">
        ${qrSvg}
        <span>UIN: ${esc(a.asset_code)}</span>
      </div>
    </div>
    ${carbonSec}
    ${mineralsSec}
    ${advDiag}
    <div class="dpp-foot">
      <span>Consortium Standard: Battery Pass &amp; EU 2023/1542 &amp; India MoEFCC BWMR 2022</span>
      <button type="button" class="btn sm" data-act="close">Close Certificate</button>
    </div>
  </div>`);
}

function openEventDetail(i) {
  const e = S.evItems[i];
  openDlg(`<form method="dialog">${head('Lifecycle Event #' + e.event_id)}<div class="body"><dl class="facts"><div><dt>Battery / Asset</dt><dd>${assetLink(e.asset_code)}</dd></div><div><dt>Event Type</dt><dd><b>${esc(e.event_type)}</b></dd></div><div><dt>Timestamp</dt><dd>${d10(e.event_at)}</dd></div><div><dt>Evidence Status</dt><dd>${esc(e.evidence_status)}</dd></div></dl>
    <p><b>Facility:</b> ${esc(e.organization)}, 📍 ${esc(e.location)}</p><p class="muted">${esc(e.notes || 'No notes.')}</p><p class="small">Actor: ${esc(e.actor_id || '—')} (${esc((e.actor_role || '').toLowerCase())}) · Evidence Ref: ${esc(e.evidence_ref || 'none')}</p>
    <p class="small faint" style="margin-top:12px;">Cryptographic Hashes (SHA-256 Chain)</p><pre class="code">prev_hash  ${esc(e.prev_hash)}\nevent_hash ${esc(e.event_hash)}</pre>
    <p class="small muted" style="margin-top:6px;">Any modification to this row alters its hash and immediately breaks all subsequent chain links.</p></div><footer><button type="button" class="btn" data-act="close">Close</button></footer></form>`);
}

function openCloseLink(i) {
  const f = S.issues[i]; const ids = [...String(f.evidence).matchAll(/link#(\d+)/g)].map(m => m[1]);
  openDlg(`<form id="clForm" novalidate>${head('Close Conflicting Parent Link (Data Quality Correction)')}<div class="body"><div class="notice warn">${esc(f.detail)}<br>Select which link is obsolete and close it to restore database consistency.</div>
    <div class="fgrid">${grp('cl', 'Relationship Link to Close *', `<select class="field" id="cl" autofocus>${ids.map(x => `<option value="${x}">Link #${x}</option>`).join('')}</select>`)}${grp('cd', 'Effective Closure Date *', `<input class="field" id="cd" type="date" max="${today()}" value="${today()}">`)}
    <div class="full">${grp('cr', 'Correction Reason *', `<textarea class="field" id="cr" rows="2" placeholder="e.g. Correcting physical component transfer to resolve multi-parent overlap anomaly…"></textarea>`)}</div></div><div id="ce" class="err" role="alert"></div></div>
    <footer><button type="button" class="btn" data-act="close">Cancel</button><button class="btn danger" id="csave">Close Link</button></footer></form>`);
  $('#clForm').onsubmit = async ev => {
    ev.preventDefault(); clearErr(); let bad = false;
    for (const [id, m] of [['cd', 'Date is required.'], ['cr', 'A reason is required.']]) if (!$('#' + id).value.trim()) { fe(id, m); bad = true; }
    if (bad) return; $('#csave').disabled = true;
    try { await api('/api/relationships/close', { body: { relationship_id: $('#cl').value, valid_to: $('#cd').value, reason: $('#cr').value } }); closeDlg(); flash('Link closed and corrective audit event recorded.'); route(); }
    catch (e) { $('#ce').textContent = e.message; $('#csave').disabled = false; }
  };
}

function sqlResult(r) {
  return `<p class="small muted">${r.rows.length}${r.truncated ? '+' : ''} rows · Execution time: ${r.elapsed_ms} ms</p>` +
    table(r.columns.map(c => ({ h: c })), r.rows.map(row => row.map(v => v === null ? '<span class="faint">NULL</span>' : esc(v))), { stack: false, empty: 'Query returned no rows.' });
}

async function runSql(explain) {
  let sql = $('#sqlbox').value.trim(); const out = $('#sqlOut');
  if (explain && !/^explain/i.test(sql)) sql = 'EXPLAIN QUERY PLAN ' + sql;
  out.innerHTML = loading('Executing query in database…');
  try { out.innerHTML = sqlResult(await api('/api/sql', { body: { sql } })); } catch (e) { out.innerHTML = `<div class="notice bad" role="alert">${esc(e.message)}</div>`; }
}

/* ---------- Global Event Listeners ---------- */
document.addEventListener('click', async ev => {
  const t = ev.target.closest('[data-act]'); if (!t) return; const a = t.dataset.act;
  try {
    if (a === 'close') closeDlg();
    else if (a === 'retry') route();
    else if (a === 'event') await openEvent(t.dataset.code || '');
    else if (a === 'diagnostic') await openDiagnostic(t.dataset.code || '');
    else if (a === 'move') await openMove(t.dataset.code || '');
    else if (a === 'passcard') openPassportCard(S.currentLineage || await api('/api/lineage/' + encodeURIComponent(t.dataset.code)));
    else if (a === 'closelink') openCloseLink(+t.dataset.n);
    else if (a === 'evdetail') openEventDetail(+t.dataset.i);
    else if (a === 'apage') { S.aq.offset = Math.max(0, S.aq.offset + PAGE * +t.dataset.d); loadAssets(); }
    else if (a === 'epage') { S.evOffset = Math.max(0, (S.evOffset || 0) + PAGE * +t.dataset.d); loadEvents(); }
    else if (a === 'labtab') location.hash = '#/lab/' + t.dataset.t;
    else if (a === 'neo4jsync') {
      const out = $('#neo4jOut'); out.innerHTML = loading('Projecting current synthetic SQLite data…');
      const result = await api('/api/neo4j/sync', { body: {} });
      out.innerHTML = `<div class="notice ok">Synced ${esc(result.synced_assets)} assets and ${esc(result.synced_relationships)} relationships to Neo4j (${esc(result.database)}).</div>`;
    }
    else if (a === 'neo4jtrace') {
      const code = $('#neoCode').value.trim(); const direction = $('#neoDir').value;
      if (!/^[A-Za-z0-9._-]{1,80}$/.test(code)) throw new Error('Enter a valid asset code.');
      const out = $('#neo4jOut'); out.innerHTML = loading('Querying Neo4j lineage…');
      const result = await api(`/api/neo4j/lineage/${encodeURIComponent(code)}?direction=${direction}`);
      const paths = result.paths || [];
      out.innerHTML = `<section class="panel"><header><h3>Neo4j paths from ${esc(result.asset_code)}</h3><p>${esc(paths.length)} paths · ${direction === 'up' ? 'upstream' : 'downstream'} · projected SQLite data</p></header>${paths.length ? paths.map(p => `<div class="body graph-path"><span class="mono">${p.path.map(esc).join(' → ')}</span><span class="muted small">${esc(p.depth)} links · ${p.types.map(esc).join(' → ')}</span></div>`).join('') : '<div class="body"><p>No connected assets found. Sync the graph or choose another asset.</p></div>'}</section>`;
    }
    else if (a === 'runsql') runSql(false);
    else if (a === 'explain') runSql(true);
    else if (a === 'copysql') { try { await navigator.clipboard.writeText($('#sqlbox').value); flash('SQL query copied to clipboard.', 'ok'); } catch { flash('Clipboard unavailable.', 'warn'); } }
    else if (a === 'clearsql') { $('#sqlOut').innerHTML = ''; }
    else if (a === 'verify') {
      const v = await api('/api/audit/verify');
      const box = $('#verifyOut');
      if (box) box.innerHTML = `<div class="notice ${v.ok ? 'ok' : 'bad'}">${v.ok ? `✅ <b>Ledger Integrity Verified:</b> ${v.checked} events verified across SHA-256 chain. Tip hash: <span class="mono">${esc(v.tip_hash)}</span>.` : `❌ <b>Chain Tampering Detected</b> at event #${esc(v.first_bad_event_id)}: ${esc(v.reason)}`}</div>`;
      else flash(v.ok ? `Chain verified (${v.checked} events).` : `Chain broken at #${v.first_bad_event_id}!`, v.ok ? 'ok' : 'bad');
    }
    else if (a === 'recallJson' && S.lastRecall) {
      const u = URL.createObjectURL(new Blob([JSON.stringify(S.lastRecall.r, null, 2)], { type: 'application/json' }));
      const l = document.createElement('a'); l.href = u; l.download = 'batterytrace-recall.json'; l.click(); URL.revokeObjectURL(u);
    }
  } catch (e) { flash(e.message, 'bad'); }
});

document.addEventListener('input', ev => {
  if (['fq'].includes(ev.target.id)) { clearTimeout(S.t); S.t = setTimeout(() => { S.aq.q = ev.target.value; S.aq.offset = 0; loadAssets(); }, 250); }
});

document.addEventListener('change', ev => {
  const m = { fs: 'status', ft: 'type', fo: 'sort' }[ev.target.id];
  if (m) { S.aq[m] = ev.target.value; S.aq.offset = 0; loadAssets(); }
});

document.addEventListener('submit', ev => {
  if (ev.target.id === 'assetFilters') ev.preventDefault();
  if (ev.target.id === 'goAsset') { ev.preventDefault(); location.hash = '#/lineage/' + encodeURIComponent($('#gc').value.trim().toUpperCase()); }
});

window.addEventListener('hashchange', route);
dlg.addEventListener('click', e => { if (e.target === dlg) closeDlg(); });

/* ---------- Application Bootstrap ---------- */
(async function init() {
  try {
    [S.meta, S.users] = await Promise.all([api('/api/meta'), api('/api/users')]);
    try { const u = sessionStorage.getItem('bt-user'); if (u && S.users.some(x => x.user_id === u)) S.user = u; } catch { /* ignore */ }
    
    // Populate role selector in header
    const actorEl = $('#actor');
    if (actorEl) {
      actorEl.innerHTML = S.users.map(u => {
        const p = PERSONA_CONFIGS[u.user_id] || {};
        return `<option value="${esc(u.user_id)}" ${u.user_id === S.user ? 'selected' : ''}>${esc(p.badge || u.role)} · ${esc(u.user_id)}</option>`;
      }).join('');

      actorEl.onchange = e => {
        S.user = e.target.value;
        try { sessionStorage.setItem('bt-user', S.user); } catch { /* ignore */ }
        const p = PERSONA_CONFIGS[S.user] || {};
        flash(`Now acting as ${p.badge || S.user} (${p.org || ''}). Dashboard tailored!`, 'ok');
        route(); // Immediately re-render view with new persona and permissions!
      };
    }

    await route();
  } catch (e) { $('#page').innerHTML = errState(e, true); }
})();
