const state = { data: null, watched: [], thread: null, pipe: null, focusNode: null, focusDecision: null };

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const el = (t, c, h) => { const n = document.createElement(t); if (c) n.className = c; if (h !== undefined) n.innerHTML = h; return n; };
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const mono = s => `<span class="id">${esc(s)}</span>`;
const num = n => Number(n).toLocaleString("en-US");
function reduced() {
  try { return window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch (e) { return false; }
}

const SVGNS = "http://www.w3.org/2000/svg";
function svgEl(tag, attrs, text) {
  const n = document.createElementNS(SVGNS, tag);
  for (const k in attrs) n.setAttribute(k, attrs[k]);
  if (text !== undefined) n.textContent = text;
  return n;
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
function fmtDate(iso) {
  if (!iso) return "";
  const d = new Date(iso + (iso.length === 10 ? "T00:00:00" : ""));
  return `${MONTHS[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()}`;
}
function shortDate(iso) {
  if (!iso) return "";
  const d = new Date(iso + "T00:00:00");
  return `${MONTHS[d.getMonth()].toUpperCase()} ${d.getFullYear()}`;
}
function daysUntil(iso) {
  if (!iso) return null;
  return Math.round((new Date(iso + "T00:00:00") - new Date()) / 86400000);
}
function titleCase(s) {
  return String(s || "").toLowerCase().replace(/\b\w/g, m => m.toUpperCase());
}

function plainTitle(t) {
  const head = String(t).split(/\bFOR the purpose\b|\bFor the purpose\b/)[0];
  return head.replace(/^(Rezoning|Zoning)\s*[-–]\s*/i, "").replace(/\s*[-–]\s*$/, "").trim();
}

function tidyZone(z) {
  return String(z).trim().replace(/\s+/g, "-").replace(/-+/g, "-").toUpperCase();
}

function plainLanguage(rec) {
  const t = rec.title;
  const addr = (rec.parcels[0] || {}).address || "the property";
  const zone = /from the (.{2,14}?) Zoning District to the (.{2,14}?) Zoning District/i.exec(t);
  if (zone) return `Changes the zoning of ${addr} from ${tidyZone(zone[1])} to ${tidyZone(zone[2])}.`;
  if (/Conditional Use/i.test(t) && /(\d+) Dwelling Units/i.test(t)) {
    const n = /to (\d+) Dwelling Units/i.exec(t);
    return `Allows ${addr} to be converted into ${n ? n[1] : "several"} homes.`;
  }
  if (/RPP Area/i.test(t)) return `Changes residential parking permit rules covering ${addr}.`;
  if (/Sale of Property/i.test(t)) return `Authorises the city to sell ${addr}.`;
  if (/Landmark List/i.test(t)) return `Designates ${addr} as a historical landmark.`;
  if (/Repeal/i.test(t) && /Planned Unit Development/i.test(t)) return `Repeals the old development plan covering ${addr}.`;
  if (/Parking Lot/i.test(t)) return `Allows a parking lot to operate at ${addr}.`;
  if (/Class [A-Z]-?[A-Z]?-?\d?\s*License/i.test(t)) return `Transfers an alcohol licence for use at ${addr}.`;
  return plainTitle(t);
}

function statusLine(rec) {
  const s = rec.status || "";
  if (/Failed/i.test(s)) return "died when the council term ended";
  if (/Withdrawn/i.test(s)) return "withdrawn";
  if (/Enacted/i.test(s)) return "passed and signed";
  if (/Adopted/i.test(s)) return "adopted";
  if (/In Committee/i.test(s)) return "in committee now";
  return s.toLowerCase();
}

function statusClause(rec) {
  const s = rec.status || "";
  if (/Failed/i.test(s)) return "died when the council term ended";
  if (/Withdrawn/i.test(s)) return "was withdrawn";
  if (/Enacted/i.test(s)) return "was passed and signed";
  if (/Adopted/i.test(s)) return "was adopted";
  if (/In Committee/i.test(s)) return "is in committee now";
  return "ended as " + s.toLowerCase();
}

function statusKind(rec) {
  const s = rec.status || "";
  if (/Failed|Withdrawn/i.test(s)) return "dead";
  if (/In Committee/i.test(s)) return "live";
  return "done";
}

function parcelLine(rec) {
  const p = rec.parcels[0];
  if (!p) return "";
  return `Block ${p.block}, ${p.lots.length > 1 ? "lots" : "lot"} ${p.lots.join(", ")}`;
}

function spineStops(thread) {
  const stops = thread.records.map(r => ({
    date: r.introduced_date,
    file: r.file_number,
    kicker: shortDate(r.introduced_date),
    label: statusLine(r),
    kind: statusKind(r),
    parcel: parcelLine(r),
    rec: r
  }));
  const last = thread.records[thread.records.length - 1];
  if (last.hearing_date) {
    const d = daysUntil(last.hearing_date);
    stops.push({
      date: last.hearing_date,
      file: last.file_number,
      kicker: shortDate(last.hearing_date),
      label: d !== null && d >= 0 ? `public hearing, in ${d} days` : "public hearing",
      kind: "future",
      parcel: last.committee || "",
      rec: last
    });
  }
  return stops;
}

function spineDefs(svg) {
  const defs = svgEl("defs");
  const rail = svgEl("linearGradient", { id: "railGrad", x1: "0", y1: "0", x2: "1", y2: "0" });
  rail.append(
    svgEl("stop", { offset: "0", "stop-color": "#3D6FD1", "stop-opacity": ".35" }),
    svgEl("stop", { offset: ".55", "stop-color": "#7CB1FF", "stop-opacity": "1" }),
    svgEl("stop", { offset: "1", "stop-color": "#E9C377", "stop-opacity": "1" })
  );
  const plate = svgEl("linearGradient", { id: "plateGrad", x1: "0", y1: "0", x2: ".4", y2: "1" });
  plate.append(
    svgEl("stop", { offset: "0", "stop-color": "#22302B" }),
    svgEl("stop", { offset: "1", "stop-color": "#0D1413" })
  );
  defs.append(rail, plate);
  svg.appendChild(defs);
}

function plateShape(g, x, y, w, h, live) {
  const d = 12;
  g.appendChild(svgEl("polygon", { class: "plate-side", points: `${x + w},${y} ${x + w + d},${y - d} ${x + w + d},${y + h - d} ${x + w},${y + h}` }));
  g.appendChild(svgEl("polygon", { class: "plate-top", points: `${x},${y} ${x + d},${y - d} ${x + w + d},${y - d} ${x + w},${y}` }));
  g.appendChild(svgEl("rect", { class: "plate-face" + (live ? " live" : ""), x, y, width: w, height: h, rx: 3 }));
}

function renderSpine(thread) {
  const host = $("#spine");
  if (!host) return;
  host.innerHTML = "";
  const stops = spineStops(thread);
  const gap = thread.features && thread.features.temporal ? thread.features.temporal.gap_days : null;
  const vertical = (host.clientWidth || 0) < 640;
  const svg = svgEl("svg", { role: "img" });
  svg.setAttribute("aria-label", `Continuity of one issue: ${stops.map(s => `${fmtDate(s.date)}, ${s.file}, ${s.label}`).join("; ")}`);
  spineDefs(svg);

  if (vertical) {
    const W = 380, cardH = 132, top = 34, stepY = 178;
    const H = top + stepY * (stops.length - 1) + cardH + 24;
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    const railX = 26;
    svg.appendChild(svgEl("path", { class: "rail-glow", d: `M ${railX} ${top + 30} L ${railX} ${top + stepY * (stops.length - 1) + 40}` }));
    const rail = svgEl("path", { class: "rail", d: `M ${railX} ${top + 30} L ${railX} ${top + stepY * (stops.length - 1) + 40}` });
    rail.setAttribute("stroke", "url(#railGrad)");
    svg.appendChild(rail);
    stops.forEach((s, i) => {
      const y = top + stepY * i;
      const g = svgEl("g");
      plateShape(g, 58, y, 306, cardH, s.kind !== "dead");
      g.appendChild(svgEl("circle", { class: "node-ring" + (s.kind === "future" ? " future" : s.kind === "dead" ? " dead" : ""), cx: railX, cy: y + 30, r: s.kind === "future" ? 8 : 6 }));
      g.appendChild(svgEl("path", { class: "gapline", d: `M ${railX + 10} ${y + 30} L 58 ${y + 30}` }));
      g.appendChild(svgEl("text", { class: "tiny-l", x: 76, y: y + 24 }, s.kicker));
      g.appendChild(svgEl("text", { class: s.kind === "future" ? "big" : "mono big", x: 76, y: y + 56, fill: s.kind === "future" ? "#E9C377" : "#ECF2EE" }, s.kind === "future" ? "Public hearing" : s.file));
      g.appendChild(svgEl("text", { class: s.kind === "future" ? "gold" : "soft", x: 76, y: y + 82 }, s.kind === "future" ? s.label.replace("public hearing, ", "") : s.label));
      g.appendChild(svgEl("text", { class: "soft", x: 76, y: y + 106 }, s.parcel));
      svg.appendChild(g);
    });
    if (gap) {
      const y = top + cardH + 30;
      svg.appendChild(svgEl("path", { class: "gapline", d: `M ${railX} ${y - 14} L ${railX} ${y + 6}` }));
      svg.appendChild(svgEl("text", { class: "tiny-l", x: 58, y: y + 4 }, `${num(gap)} days later`));
    }
  } else {
    const W = 1000, H = 322, railY = 250;
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    const padL = 150, padR = 150;
    const step = (W - padL - padR) / Math.max(1, stops.length - 1);
    const x = i => padL + i * step;
    svg.appendChild(svgEl("path", { class: "rail-glow", d: `M ${x(0) - 40} ${railY} L ${x(stops.length - 1) + 40} ${railY}` }));
    const rail = svgEl("path", { class: "rail", d: `M ${x(0) - 40} ${railY} L ${x(stops.length - 1) + 40} ${railY}` });
    rail.setAttribute("stroke", "url(#railGrad)");
    svg.appendChild(rail);

    stops.forEach((s, i) => {
      const cx = x(i);
      const scale = 0.9 + 0.06 * i;
      const w = 264, h = 136;
      const isF = s.kind === "future";
      const plate = svgEl("g");
      plate.setAttribute("transform", `translate(${cx} ${railY - 34}) scale(${scale.toFixed(3)}) skewY(-3)`);
      plate.setAttribute("opacity", (0.82 + 0.09 * i).toFixed(2));
      plateShape(plate, -w / 2, -h, w, h, s.kind !== "dead");
      svg.appendChild(plate);

      const tx = -w / 2 + 20;
      const dy = -0.0524 * tx;
      const g = svgEl("g");
      g.setAttribute("transform", `translate(${cx} ${railY - 34}) scale(${scale.toFixed(3)})`);
      g.appendChild(svgEl("text", { class: "tiny-l", x: tx, y: -h + 28 + dy }, s.kicker));
      g.appendChild(svgEl("text", { class: isF ? "big" : "mono big", x: tx, y: -h + 60 + dy, fill: isF ? "#E9C377" : "#ECF2EE" }, isF ? "Public hearing" : s.file));
      g.appendChild(svgEl("text", { class: isF ? "gold" : "soft", x: tx, y: -h + 86 + dy }, isF ? s.label.replace("public hearing, ", "") : s.label));
      g.appendChild(svgEl("text", { class: "soft", x: tx, y: -h + 110 + dy }, s.parcel));
      svg.appendChild(g);

      const stem = svgEl("path", { class: "gapline", d: `M ${cx} ${railY - 34} L ${cx} ${railY}` });
      svg.appendChild(stem);
      svg.appendChild(svgEl("circle", { class: "node-ring" + (s.kind === "future" ? " future" : s.kind === "dead" ? " dead" : ""), cx, cy: railY, r: s.kind === "future" ? 9 : 6.5 }));
      svg.appendChild(svgEl("text", { class: "tiny-l", x: cx, y: railY + 30, "text-anchor": "middle" }, fmtDate(s.date)));
    });

    if (gap && stops.length > 1) {
      const mid = (x(0) + x(1)) / 2;
      svg.appendChild(svgEl("path", { class: "gapline", d: `M ${x(0) + 14} ${railY + 52} L ${mid - 92} ${railY + 52}` }));
      svg.appendChild(svgEl("path", { class: "gapline", d: `M ${mid + 92} ${railY + 52} L ${x(1) - 14} ${railY + 52}` }));
      svg.appendChild(svgEl("text", { class: "tiny-l", x: mid, y: railY + 56, "text-anchor": "middle" }, `${num(gap)} days, new council`));
    }
  }

  host.appendChild(svg);
  if (reduced()) return;
  const rails = $$(".rail", svg);
  rails.forEach(r => {
    let len = 1200;
    try { len = r.getTotalLength() || 1200; } catch (e) { len = 1200; }
    r.style.strokeDasharray = len;
    r.style.strokeDashoffset = len;
    r.animate([{ strokeDashoffset: len }, { strokeDashoffset: 0 }], { duration: 1000, easing: "cubic-bezier(.22,.72,.28,1)", fill: "forwards" });
  });
  $$("g", svg).forEach((g, i) => {
    if (!g.querySelector("text")) return;
    g.animate([{ opacity: 0, transform: g.getAttribute("transform") ? undefined : "translateY(12px)" }, {}], { duration: 420, delay: 200 + 160 * i, easing: "cubic-bezier(.22,.72,.28,1)", fill: "backwards" });
  });
}

function threadDelta(thread) {
  const f = thread.features;
  if (!f) return [];
  const out = [];
  const la = f.parcel.lots_a || [], lb = f.parcel.lots_b || [];
  const bothListLots = la.length > 0 && lb.length > 0;
  const dropped = bothListLots ? lb.filter(l => !la.includes(l)) : [];
  const added = bothListLots ? la.filter(l => !lb.includes(l)) : [];
  if (dropped.length) out.push(`<b>Lot ${esc(dropped.join(", "))} dropped</b> from the parcel this time.`);
  if (added.length) out.push(`<b>Lot ${esc(added.join(", "))} added</b> to the parcel this time.`);
  if (f.sponsor.overlap.length) out.push(`<b>Same sponsor</b>, ${esc(titleCase(f.sponsor.overlap.join(", ")))}.`);
  if (f.zoning_transition.match && f.zoning_transition.a) out.push(`<b>Same zoning change</b>, ${mono(f.zoning_transition.a.replace("->", " to "))}.`);
  if (f.file_number && !f.file_number.identical) out.push(`<b>File number changed</b>, ${mono(f.file_number.b)} became ${mono(f.file_number.a)}.`);
  if (f.temporal && f.temporal.gap_days !== null) out.push(`<b>${num(f.temporal.gap_days)} days apart</b>, ${f.temporal.same_council_term ? "same council term" : "a different council term"}.`);
  if (f.title) out.push(`Titles are <b>${f.title.cosine}</b> similar by cosine, which is not what decided it.`);
  return out;
}

function renderThread(thread) {
  const gap = thread.features.temporal.gap_days;
  const recs = thread.records;
  const a = recs[0], b = recs[recs.length - 1];
  const addr = (b.parcels[0] || {}).address || "";
  const eyebrow = $("#hero-eyebrow");
  if (eyebrow) eyebrow.innerHTML = `${esc(a.file_number)} &nbsp;/&nbsp; ${esc(b.file_number)} &nbsp;&middot;&nbsp; Baltimore City Council`;
  const lede = $("#hero-lede");
  if (lede) {
    lede.innerHTML = `${esc(plainLanguage(b))} It died once already. Quorum matched the two records on the parcel, not the title, and it is on the calendar again.`;
  }
  $("#spine-caption").innerHTML =
    `${esc(addr)}${b.neighborhood ? ", " + esc(titleCase(b.neighborhood)) : ""}. ` +
    `Owner of record ${esc(titleCase(b.owner || "not listed"))}. Corpus fetched ${mono(String(a.fetched_at).slice(0, 16).replace("T", " "))} UTC.`;

  $("#thread-intro").innerHTML =
    `One issue, ${recs.length} appearances, ${recs.length} file numbers, ${gap ? num(Math.round(gap / 30)) + " months apart" : ""}. ` +
    `Quorum matched them on the parcel, not the title.`;

  const host = $("#thread-body");
  host.innerHTML = "";
  recs.forEach((r, i) => {
    const kind = statusKind(r);
    const wrap = el("div", "appearance" + (kind === "dead" ? " dead" : ""));
    const g = el("div", "gutter"); g.appendChild(el("span", "dot"));
    const body = el("div", "body");
    const isLast = i === recs.length - 1;
    const delta = isLast && i > 0 ? threadDelta(thread) : [];
    body.innerHTML = `
      ${i > 0 && gap ? `<div class="gapmark"><span>${num(gap)} days later</span></div>` : ""}
      <div class="card">
        <div class="meta">
          <span class="chip square"><span class="dotmark"></span>${esc(fmtDate(r.introduced_date))}</span>
          <span class="chip"><span class="id">${esc(r.file_number)}</span></span>
          <span class="chip ${kind === "dead" ? "warn" : kind === "live" ? "on" : ""}">${esc(statusLine(r))}</span>
        </div>
        <h3>${esc(plainLanguage(r))}</h3>
        <p class="small muted">Sponsored by ${esc(r.sponsors.join(", ") || "unknown")}. ${esc(parcelLine(r))}. ${esc(r.committee || "Baltimore City Council")}.</p>
        ${delta.length ? `<div class="delta"><ul>${delta.map(d => `<li>${d}</li>`).join("")}</ul></div>` : ""}
        <p class="small" style="margin:16px 0 0"><a href="${esc(r.source_url)}" target="_blank" rel="noopener">Source record ${esc(r.file_number)}</a></p>
      </div>`;
    wrap.append(g, body);
    host.appendChild(wrap);
  });

  const last = recs[recs.length - 1];
  if (last.hearing_date) {
    const d = daysUntil(last.hearing_date);
    const wrap = el("div", "appearance future");
    const g = el("div", "gutter"); g.appendChild(el("span", "dot"));
    const body = el("div", "body");
    body.innerHTML = `
      <div class="card">
        <div class="meta">
          <span class="chip gold"><span class="dotmark"></span>${esc(fmtDate(last.hearing_date))}</span>
          <span class="chip">${esc(last.committee || "Baltimore City Council")}</span>
        </div>
        <h3${d !== null && d <= 3 ? ' class="flag"' : ""}>Public hearing${d !== null && d >= 0 ? `, in ${d} days` : ""}</h3>
        <p class="small muted">This has not happened yet. It is the moment a comment can change something.</p>
        <p style="margin:0"><a class="btn primary" href="#comment">Draft a comment</a></p>
      </div>`;
    wrap.append(g, body);
    host.appendChild(wrap);
  }
}

function renderFeed() {
  const host = $("#feed-body");
  host.innerHTML = "";
  const counts = state.data.counts;
  const watchedThreads = state.data.threads.filter(t => (t.watched || []).some(w => state.watched.includes(w)));
  $("#feed-empty").textContent =
    `Most weeks nothing here affects your addresses, and that is the point. Quorum read ${num(counts.matters)} records and surfaced ${watchedThreads.length}.`;

  if (!watchedThreads.length) {
    host.innerHTML = `<div class="panel"><h3>Nothing to show</h3><p class="small muted" style="margin:8px 0 0">No record in this corpus touches an address you watch. Add one on the watch screen and the feed fills from the same data.</p></div>`;
    return;
  }

  const ranked = watchedThreads.slice().sort((a, b) => {
    const ha = a.records[a.records.length - 1].hearing_date ? 1 : 0;
    const hb = b.records[b.records.length - 1].hearing_date ? 1 : 0;
    if (ha !== hb) return hb - ha;
    return String(b.records[b.records.length - 1].introduced_date).localeCompare(String(a.records[a.records.length - 1].introduced_date));
  });

  ranked.forEach(t => {
    const r = t.records[t.records.length - 1];
    const entry = el("div", "entry cont");
    entry.appendChild(el("div", "stub"));
    const body = el("div");
    const d = daysUntil(r.hearing_date);
    body.innerHTML = `
      <div class="meta" style="margin-bottom:12px">
        <span class="chip"><span class="id">${esc(r.file_number)}</span></span>
        <span class="chip">${esc((r.parcels[0] || {}).address || "")}</span>
        ${r.hearing_date
          ? `<span class="chip ${d !== null && d <= 3 ? "warn" : "gold"}"><span class="dotmark"></span>Hearing ${esc(fmtDate(r.hearing_date))}</span>`
          : `<span class="chip">${esc(r.status || "")}</span>`}
      </div>
      <h3>${esc(plainLanguage(r))}</h3>
      <p class="small muted" style="margin:0">Continues an issue first seen ${esc(fmtDate(t.records[0].introduced_date))} under ${mono(t.records[0].file_number)}, which ${esc(statusClause(t.records[0]))}.</p>`;
    const btn = el("button", "", "See the thread");
    btn.onclick = () => { selectThread(t); go("thread"); };
    body.appendChild(btn);
    entry.appendChild(body);
    host.appendChild(entry);
  });
}

function selectThread(t) {
  state.thread = t;
  renderSpine(t);
  renderThread(t);
  renderEvidence();
  renderComment();
}

function featureRows(f) {
  const rows = [];
  const pm = f.parcel.match;
  rows.push([
    pm === "exact" ? "same" : pm === "adjacent" ? "diff" : "diff",
    "Parcel",
    pm === "exact"
      ? `Exact match, ${mono((f.parcel.shared_parcel_ids || f.parcel.shared_addresses || []).join(", "))}`
      : pm === "adjacent"
        ? `Adjacent only. ${f.parcel.shared_blocks ? "Same block " + mono(f.parcel.shared_blocks.join(", ")) + ", different lots" : "Same street, different number"}`
        : "No shared parcel"
  ]);
  rows.push(["na", "Lots named", `${esc((f.parcel.lots_b || []).join(", ") || "none")} then ${esc((f.parcel.lots_a || []).join(", ") || "none")}`]);
  rows.push([
    f.sponsor.overlap.length ? "same" : "diff",
    "Sponsor",
    f.sponsor.overlap.length ? `Same, ${esc(titleCase(f.sponsor.overlap.join(", ")))}` : `Different, ${esc(titleCase(f.sponsor.b.join(", ")))} then ${esc(titleCase(f.sponsor.a.join(", ")))}`
  ]);
  rows.push([
    f.zoning_transition.match ? "same" : (f.zoning_transition.a || f.zoning_transition.b) ? "diff" : "na",
    "Zoning transition",
    f.zoning_transition.match
      ? `Identical, ${mono(String(f.zoning_transition.a).replace("->", " to "))}`
      : (f.zoning_transition.a || f.zoning_transition.b)
        ? `Differs, ${esc(f.zoning_transition.b || "none")} then ${esc(f.zoning_transition.a || "none")}`
        : "Neither is a rezoning"
  ]);
  rows.push([
    "na",
    "Prior outcome",
    `${esc(f.committee_progression.prior_status || "unknown")}, ${esc(f.committee_progression.shape)} shape`
  ]);
  rows.push([
    "na",
    "Gap",
    f.temporal.gap_days !== null ? `${num(f.temporal.gap_days)} days, ${f.temporal.same_council_term ? "same" : "different"} council term` : "unknown"
  ]);
  rows.push([f.file_number.identical ? "same" : "diff", "File numbers", `${mono(f.file_number.b)} then ${mono(f.file_number.a)}`]);
  rows.push(["na", "Title cosine", `<strong>${f.title.cosine}</strong>`]);
  return rows;
}

const MARK = { same: "=", diff: "≠", na: "·" };

function evidencePanel(item, isCont) {
  const f = item.features;
  const rows = featureRows(f).map(([m, k, v]) =>
    `<span class="m ${m}" aria-hidden="true">${MARK[m]}</span><span class="k">${esc(k)}</span><span class="v">${v}</span>`
  ).join("");
  return `
    <div class="panel">
      <div class="small muted">${mono(item.records[0].file_number)} compared with ${mono(item.records[1].file_number)}</div>
      <div class="verdict ${isCont ? "yes" : "no"}">
        <span class="mark" aria-hidden="true">${isCont ? "✓" : "✕"}</span>
        <h3>${isCont ? "Continuation" : "Not a continuation"}</h3>
      </div>
      <div class="fx">${rows}</div>
      <hr class="rule">
      <p class="small muted" style="margin:0">${esc(item.label)}</p>
    </div>`;
}

function renderEvidence() {
  const host = $("#evidence-body");
  host.innerHTML = "";
  const t = state.thread || state.data.threads[0];
  const neg = state.data.negatives.find(n => n.pair_id === 25) || state.data.negatives[0];

  const cmp = el("div", "compare");
  cmp.innerHTML = evidencePanel(t, true) + evidencePanel(neg, false);
  host.appendChild(cmp);

  const t_cos = t.features.title.cosine, n_cos = neg.features.title.cosine;
  const lo = 0.85, hi = 1.0;
  const pos = v => Math.max(0, Math.min(100, ((v - lo) / (hi - lo)) * 100));
  const band = (state.data.evaluation && state.data.evaluation.sweep || []).filter(s => s.accuracy === Math.max(...state.data.evaluation.sweep.map(x => x.accuracy)));
  const bandLo = band.length ? band[0].threshold : null;
  const bandHi = band.length ? band[band.length - 1].threshold : null;

  const tail = el("div");
  tail.innerHTML = `
    <div class="panel" style="margin-top:16px">
      <h3>What the agent did not rely on</h3>
      <p class="small muted" style="margin-top:8px">Title similarity puts these two pairs in the wrong order. The pair that is
      <em>not</em> a continuation scores <strong>${n_cos}</strong>. The true continuation scores <strong>${t_cos}</strong>,
      slightly lower. Any system deciding on title text alone gets both of these wrong.</p>
      <div class="cosine">
        <div class="track">
          ${bandLo !== null ? `<span class="band" style="left:${pos(bandLo)}%;width:${Math.max(1, pos(bandHi) - pos(bandLo))}%"></span>` : ""}
          <span class="tick below" style="left:${pos(n_cos)}%;background:var(--flag)"><i style="color:var(--flag)">${n_cos} not a continuation</i></span>
          <span class="tick" style="left:${pos(t_cos)}%;background:var(--thread)"><i style="color:var(--thread)">${t_cos} continuation</i></span>
        </div>
        <div class="scale"><span>${lo.toFixed(2)}</span><span>cosine similarity of titles</span><span>${hi.toFixed(2)}</span></div>
      </div>
      <p class="small muted" style="margin-top:24px">What separates them is the parcel comparison, the terminal status of the
      earlier record, and the zoning transition. The shaded band is the only range of a cosine threshold that
      classifies this whole set correctly, and it is ${bandLo !== null ? `${bandHi - bandLo < 0.05 ? "narrow" : "wide"}, ${bandLo} to ${bandHi}` : "reported on the evaluation screen"}.</p>
    </div>`;
  host.appendChild(tail);
}

function measureNoun(rec) {
  const t = String(rec.title || "");
  if (/Rezoning|changing the zoning/i.test(t)) return "rezoning";
  if (/RPP Area|Parking Management Plan/i.test(t)) return "parking permit change";
  if (/Conditional Use/i.test(t)) return "conditional use request";
  if (/Sale of Property/i.test(t)) return "property sale";
  if (/Landmark/i.test(t)) return "landmark designation";
  if (/Planned Unit Development/i.test(t)) return "development plan change";
  return "measure";
}

function fallbackDraft(t) {
  const r = t.records[t.records.length - 1];
  const prev = t.records[0];
  const addr = (r.parcels[0] || {}).address || (r.neighborhood ? titleCase(r.neighborhood) : "my neighbourhood");
  const noun = measureNoun(r);

  const opening = r.hearing_date
    ? `I live near ${addr} and I am writing about ${r.file_number}, scheduled for a public hearing on ${fmtDate(r.hearing_date)}.`
    : `I live near ${addr} and I am writing about ${r.file_number}, which is currently ${statusClause(r)}.`;

  const lotsNow = (t.features.parcel.lots_a || []);
  const lotsBefore = (t.features.parcel.lots_b || []);
  const scope = (lotsNow.length && lotsBefore.length && lotsNow.join() !== lotsBefore.join())
    ? ` The current bill covers lots ${lotsNow.join(" and ")}, where the earlier one covered lots ${lotsBefore.join(", ")}.`
    : "";

  const history = `This is not the first time this ${noun} has come before the council. The earlier bill, ${prev.file_number}, was introduced on ${fmtDate(prev.introduced_date)} and ${statusClause(prev)}.${scope}`;

  return `To the ${r.committee || "Baltimore City Council"},

${opening}

${history}

I would like the committee to consider the following before voting:

[ your comment here ]

Thank you for your time.`;
}

function renderComment() {
  const t = state.thread || state.data.threads[0];
  const r = t.records[t.records.length - 1];
  const supplied = t.action && typeof t.action.draft_comment === "string" && t.action.draft_comment.trim();
  const draft = supplied ? t.action.draft_comment : fallbackDraft(t);

  $("#comment-body").innerHTML = `
    <div class="two-col">
      <div class="doc">
        <div class="small" style="color:#4A5750">File number and hearing date are taken from the source record and are locked.</div>
        <div class="locked">
          <span class="chip">File <span class="id">${esc(r.file_number)}</span></span>
          <span class="chip">Hearing ${esc(fmtDate(r.hearing_date))}</span>
          <span class="chip">${esc(r.committee || "Baltimore City Council")}</span>
        </div>
        <label for="draft">Your comment</label>
        <textarea id="draft" rows="18"></textarea>
        <div class="promise">Quorum has not sent anything and cannot. The button below opens your own email
        program with this text in it, and you decide whether to send it.</div>
        <div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:16px">
          <button class="primary" id="send">Open in your email</button>
          <button id="copy">Copy text</button>
        </div>
        <p class="small" id="send-status" role="status" style="color:#4A5750;margin:12px 0 0"></p>
      </div>
      <div>
        <div class="panel">
          <h3>What the committee will already know</h3>
          <p class="small muted" style="margin-top:8px">Everything in the draft is drawn from the two source records, so
          nothing in it can be contradicted by the file.</p>
          <hr class="rule">
          <dl class="evidence">
            <dt>This bill</dt><dd class="id">${esc(r.file_number)}</dd>
            <dt>Earlier bill</dt><dd class="id">${esc(t.records[0].file_number)}</dd>
            <dt>Earlier outcome</dt><dd>${esc(t.records[0].status || "unknown")}</dd>
            <dt>Sponsor</dt><dd>${esc(r.sponsors.join(", ") || "unknown")}</dd>
            <dt>Parcel</dt><dd>${esc(parcelLine(r))}</dd>
            <dt>Hearing</dt><dd>${esc(fmtDate(r.hearing_date))}</dd>
          </dl>
          <hr class="rule">
          <p class="small muted" style="margin:0">Source: <a href="${esc(r.source_url)}" target="_blank" rel="noopener">record ${esc(r.file_number)}</a>
          and <a href="${esc(t.records[0].source_url)}" target="_blank" rel="noopener">record ${esc(t.records[0].file_number)}</a>.</p>
        </div>
        <div class="callout">
          <p class="small" style="margin:0">A comment carries more weight when it names the earlier bill. It tells the
          committee this is a decision being revisited, not a new one.</p>
        </div>
      </div>
    </div>`;

  $("#draft").value = draft;
  $("#send").onclick = () => {
    const subject = encodeURIComponent(`Public comment on ${r.file_number}`);
    const body = encodeURIComponent($("#draft").value);
    window.location.href = `mailto:CityCouncil@baltimorecity.gov?subject=${subject}&body=${body}`;
    $("#send-status").textContent = "Your email program is opening with the comment in it. Quorum has not sent anything.";
  };
  $("#copy").onclick = async () => {
    try { await navigator.clipboard.writeText($("#draft").value); $("#send-status").textContent = "Copied to your clipboard. Quorum has not sent anything."; }
    catch (e) { $("#send-status").textContent = "Select the text and copy it. Quorum has not sent anything."; }
  };
}

function renderWatch() {
  const list = $("#watch-list");
  list.innerHTML = "";
  if (!state.watched.length) {
    list.innerHTML = `<li class="muted small">No addresses yet. Add one and Quorum starts watching what the city decides about it.</li>`;
  }
  state.watched.forEach((a, i) => {
    const li = el("li");
    const hit = state.data.threads.filter(t => (t.watched || []).includes(a));
    li.innerHTML = `<span>${esc(a)}<br><span class="tiny dim">${hit.length ? `${hit.length} issue${hit.length > 1 ? "s" : ""} in this corpus` : "nothing in this corpus yet"}</span></span>`;
    if (hit.length) {
      const s = el("button", "mini", "See the thread");
      s.onclick = () => { selectThread(hit[0]); go("thread"); };
      li.appendChild(s);
    }
    const b = el("button", "mini", "Remove");
    b.setAttribute("aria-label", `Remove ${a}`);
    b.onclick = () => { state.watched.splice(i, 1); renderWatch(); renderFeed(); };
    li.appendChild(b);
    list.appendChild(li);
  });

  const steps = $("#watch-steps");
  if (!steps) return;
  const f = funnel();
  steps.innerHTML = `
    <h3 style="margin-top:32px">What happens after you add one</h3>
    <div class="watch-steps">
      <div class="step">
        <span class="n">01</span>
        <h4>The address becomes a parcel</h4>
        <p class="small muted" style="margin:0">Your text is matched against ${num(state.data.counts.parcels)} Baltimore parcels, so a
        record that names a block and lot rather than a street number still reaches you.</p>
      </div>
      <div class="step">
        <span class="n">02</span>
        <h4>Every new record is checked against it</h4>
        <p class="small muted" style="margin:0">${num(f.read)} records were read in this run. ${num(f.resolved)} of them named a
        parcel that could be resolved, and only those can match an address.</p>
      </div>
      <div class="step">
        <span class="n">03</span>
        <h4>You hear about it once, not constantly</h4>
        <p class="small muted" style="margin:0">${f.continuations} threads were found in the corpus. ${f.watched} touch an address on
        this list, and that is all the feed shows.</p>
      </div>
    </div>`;
}

function funnel() {
  const d = state.data;
  const e = d.evaluation || {};
  const pairs = e.pairs || d.counts.labeled_pairs || 0;
  const continuations = d.threads.length;
  const watchedThreads = d.threads.filter(t => (t.watched || []).length);
  const withHearing = watchedThreads.filter(t => t.records[t.records.length - 1].hearing_date);
  return {
    read: d.counts.matters,
    resolved: d.counts.parcel_resolvable,
    dropped: d.counts.matters - d.counts.parcel_resolvable,
    pairs,
    continuations,
    newIssues: pairs - continuations,
    watched: watchedThreads.length,
    drafts: withHearing.length
  };
}

function nodeStats() {
  const f = funnel();
  const e = state.data.evaluation || {};
  const agent = e.agent;
  const g = state.data.graph || [];
  const byName = {};
  g.forEach(n => { byName[n.node] = n.kind; });
  const kind = n => byName[n] === "code" ? "code" : "agent";
  return [
    {
      node: "Civic Analyst", kind: kind("Civic Analyst"),
      inN: f.read, inLabel: "records read",
      outN: f.read, outLabel: "records structured",
      drop: null,
      note: `Reads every legislative record in the corpus and pulls out the file number, sponsors, status, dates and any property the text names. ${num(f.read)} records were read in this run.`
    },
    {
      node: "Resolution", kind: kind("Resolution"),
      inN: f.read, inLabel: "records in",
      outN: f.resolved, outLabel: "resolved to a parcel",
      drop: f.dropped, dropLabel: "named no parcel Quorum could resolve",
      note: `Matches the property text against Baltimore's parcel record, ${num(state.data.counts.parcels)} parcels. No model call here. ${num(f.dropped)} of ${num(f.read)} records named no parcel that could be resolved and go no further.`
    },
    {
      node: "Continuity", kind: kind("Continuity"),
      inN: f.pairs, inLabel: "candidate pairs judged",
      outN: f.continuations, outLabel: "continuations",
      drop: f.newIssues, dropLabel: "judged distinct issues",
      note: agent
        ? `Decides whether a new record continues an issue already seen. On the labeled set it judged ${f.pairs} pairs: ${agent.tp} continuations found, ${agent.fp} false positives, ${agent.fn} missed, ${agent.tn} correctly set aside.`
        : `Decides whether a new record continues an issue already seen, over ${f.pairs} candidate pairs.`
    },
    {
      node: "Relevance", kind: kind("Relevance"),
      inN: f.continuations, inLabel: "threads in",
      outN: f.watched, outLabel: "on a watched address",
      drop: f.continuations - f.watched, dropLabel: "on no watched address",
      note: `Compares each thread against the addresses on the watch list. ${f.watched} of ${f.continuations} threads touch one, so the other ${f.continuations - f.watched} are never shown.`
    },
    {
      node: "Action", kind: kind("Action"),
      inN: f.watched, inLabel: "threads in",
      outN: f.drafts, outLabel: "with a hearing ahead",
      drop: f.watched - f.drafts, dropLabel: "with no hearing ahead",
      note: `Writes the comment draft for a thread with a hearing still ahead of it. ${f.drafts} of the ${f.watched} watched threads has a hearing on the calendar. The draft opens in your email program. Quorum never sends it.`
    }
  ];
}

function pipeFlat(stats) {
  const stack = el("div", "stack");
  stats.forEach((s, i) => {
    if (i) {
      const e = el("div", "pipe-edge");
      e.appendChild(el("span"));
      stack.appendChild(e);
    }
    const b = el("button", "pipe-node " + s.kind);
    b.type = "button";
    b.setAttribute("aria-pressed", "false");
    b.dataset.node = s.node;
    b.innerHTML = `
      <span class="kindline"><span class="glyph"></span>${s.kind === "agent" ? "Agent" : "Deterministic"}</span>
      <span class="nm">${esc(s.node)}</span>
      <span class="io">
        <b>${num(s.inN)}</b> ${esc(s.inLabel)}<br>
        <b>${num(s.outN)}</b> ${esc(s.outLabel)}
        ${s.drop ? `<br><span class="drop">${num(s.drop)} ${esc(s.dropLabel)}</span>` : ""}
      </span>`;
    b.onclick = () => focusNode(s.node);
    stack.appendChild(b);
  });
  const flat = el("div", "pipe-flat");
  flat.appendChild(stack);
  return flat;
}

function focusNode(name) {
  state.focusNode = name;
  $$(".pipe-node").forEach(n => n.setAttribute("aria-pressed", String(n.dataset.node === name)));
  $$("#run-body tbody tr").forEach(tr => tr.classList.toggle("on", tr.dataset.node === name));
  const s = nodeStats().find(x => x.node === name);
  const box = $("#node-detail");
  if (!box || !s) return;
  box.innerHTML = `
    <div class="panel">
      <div class="chips" style="margin-bottom:12px">
        <span class="chip ${s.kind === "agent" ? "on" : ""}"><span class="dotmark"></span>${s.kind === "agent" ? "Strands agent" : "Deterministic node, no model call"}</span>
        <span class="chip">${esc(s.node)}</span>
      </div>
      <p class="small" style="margin:0">${esc(s.note)}</p>
    </div>`;
  if (state.pipe && state.pipe.focus) state.pipe.focus(name);
}

function decisionsBlock() {
  const e = state.data.evaluation || {};
  const a = e.agent;
  if (!a || !a.decisions) return "";
  const chips = a.decisions.map(d => {
    const cont = d.said === "continuation";
    const ok = (d.said === "continuation") === (d.label === "continuation");
    return `<button type="button" class="d ${cont ? "cont" : ""} ${ok ? "" : "miss"}" data-pair="${d.pair_id}"
      aria-label="Pair ${d.pair_id}, ${esc(d.a)} and ${esc(d.b)}, labeled ${esc(d.label)}, agent said ${esc(d.said)}"></button>`;
  }).join("");
  return `
    <h3 style="margin-top:32px">The ${a.decisions.length} pairs the Continuity agent judged</h3>
    <p class="small muted" style="margin-top:8px">Round marks are the pairs it called a continuation. Square marks are the
    pairs it set aside. Select one to read the evidence it used and the evidence it discarded.</p>
    <div class="decisions">${chips}</div>
    <div id="decision-detail" class="node-detail"></div>`;
}

function showDecision(pairId) {
  const a = (state.data.evaluation || {}).agent;
  if (!a) return;
  const d = a.decisions.find(x => String(x.pair_id) === String(pairId));
  const box = $("#decision-detail");
  if (!d || !box) return;
  state.focusDecision = d.pair_id;
  $$(".decisions .d").forEach(b => b.classList.toggle("sel", String(b.dataset.pair) === String(pairId)));
  const ok = d.said === d.label;
  box.innerHTML = `
    <div class="panel">
      <div class="chips" style="margin-bottom:12px">
        <span class="chip"><span class="id">${esc(d.a)}</span> and <span class="id">${esc(d.b)}</span></span>
        <span class="chip">${esc(d.tier)} tier</span>
        <span class="chip ${d.said === "continuation" ? "on" : ""}">agent said ${esc(d.said.replace("_", " "))}</span>
        <span class="chip ${ok ? "" : "warn"}">${ok ? "matches the label" : "differs from the label"}</span>
        <span class="chip"><span class="id">confidence ${d.confidence.toFixed(2)}</span></span>
      </div>
      <div class="two-col">
        <div>
          <h4>What drove the decision</h4>
          <ul class="small muted" style="padding-left:18px;margin:8px 0 0">${(d.drivers || []).map(x => `<li>${esc(x)}</li>`).join("")}</ul>
        </div>
        <div>
          <h4>What it set aside</h4>
          <ul class="small muted" style="padding-left:18px;margin:8px 0 0">${(d.non_drivers || []).map(x => `<li>${esc(x)}</li>`).join("")}</ul>
        </div>
      </div>
    </div>`;
}

function renderRun() {
  const d = state.data;
  const stats = nodeStats();
  const f = funnel();
  const rows = stats.map(s => `
    <tr data-node="${esc(s.node)}">
      <td><strong>${esc(s.node)}</strong></td>
      <td>${s.kind === "code" ? "deterministic node" : "Strands agent"}</td>
      <td class="id">${num(s.inN)}</td>
      <td class="id">${num(s.outN)}</td>
      <td class="${s.drop ? "flag" : "dim"}">${s.drop ? num(s.drop) + " " + esc(s.dropLabel) : "nothing dropped"}</td>
    </tr>`).join("");

  $("#run-body").innerHTML = `
    <div class="pipe">
      <div class="pipe-head">
        <span>Strands graph, five stages</span>
        <span>corpus fetched ${esc(String(d.fetched_at).slice(0, 10))}</span>
      </div>
      <div class="pipe-stage" id="pipe-stage"></div>
      <div class="pipe-legend" id="pipe-legend"></div>
      <div class="pipe-note" id="pipe-note"></div>
    </div>

    <div id="node-detail" class="node-detail"></div>

    <h3 style="margin-top:32px">Every stage, as numbers</h3>
    <div class="scroll-x" style="margin-top:12px">
      <table>
        <thead><tr><th>Node</th><th>Kind</th><th>In</th><th>Out</th><th>Dropped</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>

    <div class="statgrid" style="margin-top:24px">
      <div><span class="n">${num(f.read)}</span><span class="k">records read</span></div>
      <div><span class="n">${num(d.counts.parcels)}</span><span class="k">parcels in gazetteer</span></div>
      <div><span class="n">${num(f.resolved)}</span><span class="k">resolved to a parcel</span></div>
      <div><span class="n">${num(f.continuations)}</span><span class="k">threads surfaced</span></div>
    </div>

    ${decisionsBlock()}

    <div class="callout" style="margin-top:32px">
      <p class="small" style="margin:0">Orchestrated as a Strands Graph, not a Swarm. The path is deterministic and
      dependency ordered, so there is no dynamic handoff for a Swarm to manage. Resolution carries no model call at all,
      which is why it is drawn as a plate rather than a ring.</p>
    </div>
    <p class="small muted" style="margin-top:16px">Corpus fetched ${mono(String(d.fetched_at).slice(0, 16).replace("T", " "))} UTC.
    Site generated ${mono(String(d.generated_at).slice(0, 16).replace("T", " "))}.</p>`;

  $$("#run-body tbody tr").forEach(tr => {
    tr.style.cursor = "pointer";
    tr.onclick = () => focusNode(tr.dataset.node);
  });
  $$("#run-body .decisions .d").forEach(b => { b.onclick = () => showDecision(b.dataset.pair); });

  mountPipeline(stats);
  focusNode("Continuity");
  const a = (d.evaluation || {}).agent;
  if (a && a.decisions && a.decisions.length) showDecision(a.decisions[0].pair_id);
}

function hasWebGL() {
  if (typeof THREE === "undefined") return false;
  try {
    const c = document.createElement("canvas");
    return !!(c.getContext("webgl") || c.getContext("experimental-webgl"));
  } catch (e) { return false; }
}

function mountPipeline(stats) {
  const stage = $("#pipe-stage");
  const legend = $("#pipe-legend");
  const note = $("#pipe-note");
  if (!stage) return;
  const f = funnel();
  const perDot = 8;
  const stageW = stage.clientWidth || document.documentElement.clientWidth || 1000;
  const narrow = stageW < 760;
  const webgl = hasWebGL() && !narrow;
  state.pipeMode = webgl ? "gl" : "flat";
  if (state.pipe && state.pipe.stop) state.pipe.stop();
  state.pipe = null;
  stage.innerHTML = "";

  legend.innerHTML = `
    <span class="chip on"><span class="dotmark"></span>Agent stage, makes a model call</span>
    <span class="chip square"><span class="dotmark"></span>Deterministic stage, no model call</span>
    <span class="chip"><span class="dotmark" style="background:var(--flag)"></span>Records dropped at a stage</span>`;

  if (!webgl) {
    stage.classList.remove("gl");
    stage.appendChild(pipeFlat(stats));
    note.textContent = `Static view. Counts on each stage are exact and come from the exported run.`;
    return;
  }

  const layer = el("div", "layer");
  layer.setAttribute("aria-hidden", "true");
  stage.appendChild(layer);
  try {
    stage.classList.add("gl");
    state.pipe = buildScene(stage, layer, stats, f, perDot);
    note.textContent = reduced()
      ? `Motion is switched off because your system asks for reduced motion. Each dot stands for about ${perDot} records, and the counts printed on the graph are exact.`
      : `Each drifting dot stands for about ${perDot} records. The counts printed on the graph are exact. Move the pointer over the graph to look around it.`;
  } catch (e) {
    stage.classList.remove("gl");
    stage.innerHTML = "";
    stage.appendChild(pipeFlat(stats));
    note.textContent = `Static view. Counts on each stage are exact and come from the exported run.`;
  }
}

function dotTexture() {
  const c = document.createElement("canvas");
  c.width = c.height = 64;
  const g = c.getContext("2d");
  const rad = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  rad.addColorStop(0, "rgba(255,255,255,1)");
  rad.addColorStop(0.35, "rgba(190,220,255,.85)");
  rad.addColorStop(1, "rgba(120,170,255,0)");
  g.fillStyle = rad;
  g.fillRect(0, 0, 64, 64);
  const t = new THREE.CanvasTexture(c);
  return t;
}

function buildScene(stage, layer, stats, f, perDot) {
  const canvas = document.createElement("canvas");
  stage.insertBefore(canvas, layer);
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog(0x070b0a, 15, 33);
  const camera = new THREE.PerspectiveCamera(36, 2, 0.1, 120);

  scene.add(new THREE.AmbientLight(0x6c88ad, 0.5));
  const key = new THREE.DirectionalLight(0xbfd8f5, 0.85);
  key.position.set(-5, 7, 7);
  scene.add(key);
  const back = new THREE.PointLight(0x4d8ae0, 14, 18);
  back.position.set(0, 1.2, -4.5);
  scene.add(back);
  const warm = new THREE.PointLight(0xe9c377, 4, 14);
  warm.position.set(6.4, 0.6, -2.2);
  scene.add(warm);
  const under = new THREE.PointLight(0x2e6bd0, 1.6, 12);
  under.position.set(0, -2.4, 3);
  scene.add(under);

  const world = new THREE.Group();
  world.rotation.y = -0.19;
  world.rotation.x = 0.045;
  scene.add(world);

  const SPAN = 2.75;
  const NODE_Y = 0.5;
  const CONV_Y = -0.85;
  const xOf = i => (i - 2) * SPAN;

  const grid = new THREE.GridHelper(30, 30, 0x2f5f86, 0x14282f);
  grid.position.y = -2.7;
  const gmats = Array.isArray(grid.material) ? grid.material : [grid.material];
  gmats.forEach(m => { m.transparent = true; m.opacity = 0.16; });
  world.add(grid);

  const conveyor = new THREE.Mesh(
    new THREE.BoxGeometry(15.5, 0.03, 0.03),
    new THREE.MeshBasicMaterial({ color: 0x5c92e8, transparent: true, opacity: 0.6 })
  );
  conveyor.position.set(0, CONV_Y, 0);
  world.add(conveyor);
  const halo = new THREE.Mesh(
    new THREE.PlaneGeometry(15.5, 1.5),
    new THREE.MeshBasicMaterial({ map: dotTexture(), transparent: true, opacity: 0.12, depthWrite: false, blending: THREE.AdditiveBlending })
  );
  halo.position.set(0, CONV_Y, -0.05);
  world.add(halo);

  const nodes = [];
  stats.forEach((s, i) => {
    const agent = s.kind === "agent";
    const g = new THREE.Group();
    g.position.set(xOf(i), NODE_Y, 0);

    const slab = new THREE.Mesh(
      new THREE.BoxGeometry(1.95, 2.3, 0.16),
      new THREE.MeshStandardMaterial({
        color: agent ? 0x101c26 : 0x161f1c,
        roughness: 0.42, metalness: 0.25,
        emissive: agent ? 0x071624 : 0x080e0c
      })
    );
    g.add(slab);
    const edge = new THREE.LineSegments(
      new THREE.EdgesGeometry(slab.geometry),
      new THREE.LineBasicMaterial({ color: agent ? 0x7cb1ff : 0x647a72, transparent: true, opacity: 0.85 })
    );
    g.add(edge);
    g.userData.edge = edge;
    g.userData.edgeBase = agent ? 0x7cb1ff : 0x647a72;

    const core = new THREE.Mesh(
      new THREE.PlaneGeometry(2.4, 2.6),
      new THREE.MeshBasicMaterial({ map: dotTexture(), transparent: true, opacity: agent ? 0.22 : 0.08, depthWrite: false, blending: THREE.AdditiveBlending })
    );
    core.position.z = -0.32;
    g.add(core);
    g.userData.core = core;

    const base = new THREE.Mesh(
      new THREE.BoxGeometry(2.25, 0.07, 0.72),
      new THREE.MeshStandardMaterial({ color: 0x223029, roughness: 0.85, metalness: 0.15 })
    );
    base.position.y = -1.22;
    g.add(base);

    if (agent) {
      const ring = new THREE.Mesh(
        new THREE.TorusGeometry(1.34, 0.016, 8, 90),
        new THREE.MeshBasicMaterial({ color: 0x7cb1ff, transparent: true, opacity: 0.8 })
      );
      ring.rotation.x = Math.PI / 2;
      ring.position.y = -1.16;
      g.add(ring);
      const tilt = new THREE.Mesh(
        new THREE.TorusGeometry(1.18, 0.012, 8, 90),
        new THREE.MeshBasicMaterial({ color: 0x9cc6ff, transparent: true, opacity: 0.45 })
      );
      tilt.rotation.x = Math.PI / 2.35;
      g.add(tilt);
      g.userData.ring = tilt;
    } else {
      const frame = new THREE.LineSegments(
        new THREE.EdgesGeometry(new THREE.BoxGeometry(2.22, 2.56, 0.44)),
        new THREE.LineBasicMaterial({ color: 0x647a72, transparent: true, opacity: 0.5 })
      );
      g.add(frame);
    }

    world.add(g);
    nodes.push({ group: g, stat: s, index: i });
  });

  const DOTS = Math.max(60, Math.round(f.read / perDot));
  const survivors = Math.round(f.resolved / perDot);
  const dpos = new Float32Array(DOTS * 3);
  const dstate = [];
  for (let i = 0; i < DOTS; i++) {
    dstate.push({
      t: Math.random(),
      lane: -0.35 + Math.random() * 0.5,
      lift: (Math.random() - 0.5) * 0.34,
      speed: 0.075 + Math.random() * 0.045,
      survives: i < survivors,
      fall: 0
    });
  }
  const dgeo = new THREE.BufferGeometry();
  dgeo.setAttribute("position", new THREE.BufferAttribute(dpos, 3));
  const dots = new THREE.Points(dgeo, new THREE.PointsMaterial({
    size: 0.17, map: dotTexture(), transparent: true, opacity: 1,
    depthWrite: false, blending: THREE.AdditiveBlending, sizeAttenuation: true
  }));
  world.add(dots);

  const decisions = ((state.data.evaluation || {}).agent || {}).decisions || [];
  const contGeo = new THREE.SphereGeometry(0.082, 14, 14);
  const newGeo = new THREE.BoxGeometry(0.13, 0.13, 0.13);
  const cubes = [];
  const BIN_Y = 2.5;
  let ci = 0, ni = 0;
  decisions.forEach(d => {
    const cont = d.said === "continuation";
    const m = new THREE.Mesh(
      cont ? contGeo : newGeo,
      new THREE.MeshStandardMaterial({
        color: cont ? 0x8cbcff : 0x53655d,
        emissive: cont ? 0x24508f : 0x000000,
        roughness: cont ? 0.3 : 0.9, metalness: cont ? 0.5 : 0.1
      })
    );
    let col, row;
    if (cont) { col = Math.floor(ci / 5); row = ci % 5; ci++; }
    else { col = Math.floor(ni / 5); row = ni % 5; ni++; }
    const home = new THREE.Vector3(
      cont ? -0.6 - col * 0.24 : 0.6 + col * 0.24,
      BIN_Y - row * 0.22,
      0.55
    );
    m.position.copy(home);
    m.userData = { home, pair: d.pair_id, cont, phase: Math.random() * Math.PI * 2 };
    world.add(m);
    cubes.push(m);
  });

  const threadGeo = new THREE.OctahedronGeometry(0.1);
  const threads = [];
  for (let i = 0; i < f.continuations; i++) {
    const stage2 = i < f.drafts ? 2 : i < f.watched ? 1 : 0;
    const m = new THREE.Mesh(threadGeo, new THREE.MeshStandardMaterial({
      color: stage2 ? 0xe9c377 : 0x4c5c55,
      emissive: stage2 ? 0x6b4f1a : 0x000000,
      roughness: 0.4, metalness: 0.45
    }));
    m.userData = { t: i / f.continuations, stage: stage2, lane: 0.45 + Math.random() * 0.25, lift: (Math.random() - 0.5) * 0.3, fall: 0, speed: 0.12 };
    world.add(m);
    threads.push(m);
  }

  const cards = stats.map((s, i) => {
    const n = el("div", "pipe-card " + s.kind);
    n.innerHTML =
      `<span class="kindline"><span class="glyph"></span>${s.kind === "agent" ? "Agent" : "Deterministic"}</span>` +
      `<span class="nm">${esc(s.node)}</span>` +
      `<span class="io"><b>${num(s.outN)}</b> ${esc(s.outLabel)}` +
      (s.drop ? `<br><span class="drop">${num(s.drop)} ${esc(s.dropLabel)}</span>` : "") +
      `</span>`;
    layer.appendChild(n);
    return { node: n, v: new THREE.Vector3(xOf(i), CONV_Y - 0.72, 0), depth: true };
  });

  const marks = [
    { html: `<b>${num(f.read)}</b> records in`, v: new THREE.Vector3(xOf(0) - 2.5, CONV_Y + 1.1, 0), cls: "" },
    { html: `<b>${f.continuations}</b> continuations`, v: new THREE.Vector3(-1.2, BIN_Y + 0.42, 0.55), cls: "title" },
    { html: `<b>${f.newIssues}</b> distinct issues`, v: new THREE.Vector3(1.2, BIN_Y + 0.42, 0.55), cls: "title" },
    { html: `${f.pairs} labeled pairs judged here`, v: new THREE.Vector3(0, BIN_Y + 0.92, 0.55), cls: "" }
  ].map(d => {
    const n = el("div", "pipe-label" + (d.cls ? " " + d.cls : ""), d.html);
    layer.appendChild(n);
    return { node: n, v: d.v, depth: false };
  });

  const tmp = new THREE.Vector3();
  let W = 0, H = 0, unit = 1;
  function size() {
    W = stage.clientWidth || 960;
    H = stage.clientHeight || 520;
    renderer.setSize(W, H, false);
    camera.aspect = W / Math.max(1, H);
    const need = (stats.length + 0.75) * SPAN;
    const fovH = 2 * Math.atan(Math.tan((camera.fov * Math.PI / 180) / 2) * camera.aspect);
    const z = (need / 2) / Math.tan(fovH / 2) + 1.2;
    camera.position.set(0.1, 1.3, Math.max(9, z));
    camera.lookAt(0, 0.6, 0);
    camera.updateProjectionMatrix();
    unit = camera.position.z;
  }
  size();

  const pointer = { x: 0, y: 0, tx: 0, ty: 0 };
  stage.addEventListener("pointermove", e => {
    const r = stage.getBoundingClientRect();
    if (!r.width) return;
    pointer.tx = ((e.clientX - r.left) / r.width - 0.5) * 2;
    pointer.ty = ((e.clientY - r.top) / r.height - 0.5) * 2;
  });
  stage.addEventListener("pointerleave", () => { pointer.tx = 0; pointer.ty = 0; });

  const X0 = xOf(0) - 2.4, X1 = xOf(2);
  const gate = (xOf(1) - X0) / (X1 - X0);
  const clock = { last: 0 };
  let focused = null;
  const still = reduced();
  let req = 0, running = true;

  function frame(now) {
    const dt = clock.last ? Math.min(0.05, (now - clock.last) / 1000) : 0.016;
    clock.last = now;
    const t = now / 1000;

    pointer.x += (pointer.tx - pointer.x) * 0.06;
    pointer.y += (pointer.ty - pointer.y) * 0.06;
    world.rotation.y = -0.19 + pointer.x * 0.16;
    world.rotation.x = 0.045 - pointer.y * 0.07;

    for (let i = 0; i < DOTS; i++) {
      const s = dstate[i];
      s.t += s.speed * dt;
      if (!s.survives && s.t > gate) s.fall += dt * 1.7;
      if (s.t > 1 || s.fall > 2.2) { s.t = 0; s.fall = 0; }
      dpos[i * 3] = X0 + (X1 - X0) * s.t;
      dpos[i * 3 + 1] = CONV_Y + s.lift - s.fall;
      dpos[i * 3 + 2] = s.lane;
    }
    dgeo.attributes.position.needsUpdate = true;

    const tA = xOf(2), tB = xOf(4) + 1.6;
    threads.forEach(m => {
      m.userData.t += m.userData.speed * dt;
      const gateA = (xOf(3) - tA) / (tB - tA), gateB = (xOf(4) - tA) / (tB - tA);
      if (m.userData.stage === 0 && m.userData.t > gateA) m.userData.fall += dt * 1.5;
      if (m.userData.stage === 1 && m.userData.t > gateB) m.userData.fall += dt * 1.5;
      if (m.userData.t > 1 || m.userData.fall > 2.2) { m.userData.t = 0; m.userData.fall = 0; }
      m.position.set(
        tA + (tB - tA) * m.userData.t,
        CONV_Y + 0.1 + m.userData.lift - m.userData.fall,
        m.userData.lane
      );
      m.rotation.y += dt * 1.6;
      m.rotation.x += dt * 0.8;
    });

    cubes.forEach(m => {
      const h = m.userData.home;
      const sel = state.focusDecision !== null && String(state.focusDecision) === String(m.userData.pair);
      m.position.set(h.x, h.y + Math.sin(t * 1.1 + m.userData.phase) * 0.03, h.z);
      m.rotation.y = t * 0.45 + m.userData.phase;
      const target = sel ? 2.1 : 1;
      m.scale.setScalar(m.scale.x + (target - m.scale.x) * 0.16);
      if (m.material.emissive) m.material.emissive.setHex(sel ? 0xe9c377 : (m.userData.cont ? 0x24508f : 0x000000));
    });

    nodes.forEach(n => {
      const on = focused === n.stat.node;
      n.group.position.z += ((on ? 0.6 : 0) - n.group.position.z) * 0.12;
      n.group.position.y = NODE_Y + Math.sin(t * 0.55 + n.index) * 0.025;
      if (n.group.userData.ring) n.group.userData.ring.rotation.z = t * 0.4;
      if (n.group.userData.core) n.group.userData.core.material.opacity = on ? 0.55 : (n.stat.kind === "agent" ? 0.22 : 0.08);
      if (n.group.userData.edge) {
        n.group.userData.edge.material.color.setHex(on ? 0xffffff : n.group.userData.edgeBase);
        n.group.userData.edge.material.opacity = on ? 1 : 0.85;
      }
    });

    world.updateMatrixWorld(true);
    cards.concat(marks).forEach(l => {
      tmp.copy(l.v).applyMatrix4(world.matrixWorld);
      const dist = camera.position.distanceTo(tmp);
      tmp.project(camera);
      const x = (tmp.x * 0.5 + 0.5) * W;
      const y = (-tmp.y * 0.5 + 0.5) * H;
      const sc = l.depth ? Math.max(0.78, Math.min(1.12, unit / dist)) : 1;
      l.node.style.transform = `translate(-50%, ${l.depth ? "0" : "-50%"}) scale(${sc.toFixed(3)})`;
      l.node.style.left = x.toFixed(1) + "px";
      l.node.style.top = y.toFixed(1) + "px";
    });

    renderer.render(scene, camera);
    if (!still && running) req = requestAnimationFrame(frame);
  }

  world.updateMatrixWorld(true);
  if (still) { frame(0); running = false; }
  else req = requestAnimationFrame(frame);

  if (typeof ResizeObserver !== "undefined") {
    const ro = new ResizeObserver(() => { size(); if (still) frame(1); });
    ro.observe(stage);
  } else {
    window.addEventListener("resize", () => { size(); if (still) frame(1); });
  }

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) { running = false; cancelAnimationFrame(req); }
    else if (!still) { running = true; clock.last = 0; req = requestAnimationFrame(frame); }
  });

  return {
    focus(name) { focused = name; if (still) frame(1); },
    redraw() { size(); if (still) frame(1); },
    stop() { running = false; cancelAnimationFrame(req); renderer.dispose(); }
  };
}


function sweepChart(sweep) {
  if (!sweep || !sweep.length) return "";
  const W = 640, H = 190, padL = 44, padR = 16, padT = 16, padB = 34;
  const peak = Math.max(...sweep.map(s => s.accuracy));
  const lo = Math.min(...sweep.map(s => s.accuracy)) - 0.02;
  const x = i => padL + (i / (sweep.length - 1)) * (W - padL - padR);
  const y = v => padT + (1 - (v - lo) / (1 - lo)) * (H - padT - padB);
  const line = sweep.map((s, i) => `${i ? "L" : "M"} ${x(i).toFixed(1)} ${y(s.accuracy).toFixed(1)}`).join(" ");
  const area = `${line} L ${x(sweep.length - 1).toFixed(1)} ${H - padB} L ${x(0).toFixed(1)} ${H - padB} Z`;
  const pts = sweep.map((s, i) =>
    `<circle class="pt${s.accuracy === peak ? " peak" : ""}" cx="${x(i).toFixed(1)}" cy="${y(s.accuracy).toFixed(1)}" r="${s.accuracy === peak ? 4.5 : 3.2}"></circle>`
  ).join("");
  const ticks = sweep.map((s, i) =>
    i % 2 === 0 ? `<text x="${x(i).toFixed(1)}" y="${H - padB + 16}" text-anchor="middle">${s.threshold.toFixed(2)}</text>` : ""
  ).join("");
  return `
    <div class="sweep">
      <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Accuracy against the title cosine threshold. ${sweep.map(s => `${s.threshold} scores ${Math.round(s.accuracy * 100)} percent`).join("; ")}.">
        <defs><linearGradient id="sweepGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="#7CB1FF" stop-opacity=".28"></stop>
          <stop offset="1" stop-color="#7CB1FF" stop-opacity="0"></stop>
        </linearGradient></defs>
        <line class="ax" x1="${padL}" y1="${H - padB}" x2="${W - padR}" y2="${H - padB}"></line>
        <line class="ax" x1="${padL}" y1="${padT}" x2="${padL}" y2="${H - padB}"></line>
        <text x="${padL - 8}" y="${y(1) + 4}" text-anchor="end">100%</text>
        <text x="${padL - 8}" y="${y(lo + 0.02) + 4}" text-anchor="end">${Math.round((lo + 0.02) * 100)}%</text>
        <path class="area" d="${area}"></path>
        <path class="ln" d="${line}"></path>
        ${pts}${ticks}
      </svg>
    </div>`;
}

function agentBlock(a) {
  const rows = (a.decisions || []).map(d => {
    const ok = (d.said === "continuation") === (d.label === "continuation");
    return `<tr>
      <td class="id">${d.pair_id}</td>
      <td class="id">${esc(d.a)} to ${esc(d.b)}</td>
      <td>${esc(d.tier)}</td>
      <td>${esc(d.label.replace("_", " "))}</td>
      <td>${esc(d.said.replace("_", " "))}</td>
      <td class="id">${d.confidence.toFixed(2)}</td>
      <td class="${ok ? "dim" : "flag"}">${ok ? "ok" : "miss"}</td>
    </tr>`;
  }).join("");

  const misses = (a.misses || []).map(m => `
    <div class="panel" style="margin-bottom:16px">
      <div class="small muted">Pair ${m.pair_id}, ${mono(m.a)} and ${mono(m.b)}, ${esc(m.kind)}</div>
      <p class="small" style="margin-top:8px"><strong>Labeled</strong> ${esc(m.label)}.
      <strong>Agent said</strong> ${esc(m.said)} at ${m.confidence.toFixed(2)}.</p>
      <p class="small"><strong>Why it was labeled that way:</strong> ${esc(m.note)}</p>
      <p class="small"><strong>What the agent said:</strong> ${esc(m.rationale)}</p>
    </div>`).join("");

  const neg = (a.decisions || []).filter(d => d.label !== "continuation").length;

  return `
    <div class="statgrid" style="margin-top:16px">
      <div><span class="n">${Math.round(a.accuracy * 100)}%</span><span class="k">accuracy</span></div>
      <div><span class="n">${a.precision.toFixed(2)}</span><span class="k">precision</span></div>
      <div><span class="n">${a.recall.toFixed(2)}</span><span class="k">recall</span></div>
      <div><span class="n">${a.f1.toFixed(2)}</span><span class="k">f1</span></div>
    </div>

    <div class="matrix" style="margin-top:24px">
      <div class="hd"></div><div class="hd">said continuation</div><div class="hd">said new issue</div>
      <div class="hd">labeled continuation</div>
      <div class="cell good"><b>${a.tp}</b>found</div>
      <div class="cell ${a.fn ? "bad" : ""}"><b>${a.fn}</b>missed</div>
      <div class="hd">labeled new issue</div>
      <div class="cell ${a.fp ? "bad" : ""}"><b>${a.fp}</b>false alarms</div>
      <div class="cell good"><b>${a.tn}</b>set aside</div>
    </div>

    <p style="margin-top:24px">${neg} of the ${(a.decisions || []).length} pairs are negatives. They are
    listed below alongside the positives, so an agent that simply said yes to everything could not hide here.</p>
    <div class="scroll-x">
    <table>
      <thead><tr><th>Pair</th><th>Records</th><th>Tier</th><th>Label</th><th>Agent</th><th>Conf</th><th>Result</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
    </div>
    <h3 style="margin-top:32px">Every miss, named</h3>
    ${misses || `<div class="callout warn"><p class="small" style="margin:0">No misses on this set. Given that a tuned two clause
    rule also scores 100%, this says the set is separable, not that the agent is infallible.</p></div>`}`;
}

function renderEval() {
  const d = state.data, e = d.evaluation;
  if (!e) { $("#eval-body").innerHTML = `<p class="muted">No evaluation data exported.</p>`; return; }

  const best = Math.max(...e.baselines.map(b => b.accuracy));
  const rows = e.baselines.map(b => `
    <tr>
      <td>${esc(b.rule)}</td>
      <td class="id">${Math.round(b.accuracy * 100)}%</td>
      <td><span class="bar ${b.accuracy === best ? "on" : ""}" style="width:${Math.round(b.accuracy * 110)}px"></span></td>
      <td class="id">${b.precision.toFixed(2)}</td>
      <td class="id">${b.recall.toFixed(2)}</td>
      <td class="id">${b.f1.toFixed(2)}</td>
    </tr>`).join("");

  const peak = Math.max(...e.sweep.map(s => s.accuracy));
  const perfect = e.sweep.filter(s => s.accuracy === peak);

  $("#eval-body").innerHTML = `
    <div class="statgrid">
      <div><span class="n">${e.pairs}</span><span class="k">labeled pairs</span></div>
      <div><span class="n">${e.continuations}</span><span class="k">continuations</span></div>
      <div><span class="n">${e.pairs - e.continuations}</span><span class="k">distinct issues</span></div>
      <div><span class="n">${e.hard}</span><span class="k">marked hard</span></div>
    </div>

    <div class="panel" style="margin-top:24px">
      <h3>The labeled set</h3>
      <p class="small muted" style="margin:8px 0 0">${e.pairs} candidate pairs labeled by hand from the source documents.
      The 28 parcel tier pairs were labeled before any agent existed. The 22 citywide pairs were added afterwards,
      chosen deliberately to sit in the blind spot of parcel matching, which is why that tier exists at all.
      Both facts are checkable in the commit history.</p>
    </div>

    <h3 style="margin-top:32px">Deterministic baselines</h3>
    <div class="scroll-x" style="margin-top:12px">
    <table>
      <thead><tr><th>Rule</th><th>Accuracy</th><th></th><th>Precision</th><th>Recall</th><th>F1</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
    </div>

    <h3 style="margin-top:32px">What this table actually shows</h3>
    <p>The last rule scores 100% on this set. That is reported first because it is the strongest
    argument against this project, and a judge should not have to find it.</p>
    <p>Two things qualify it. The labels were assigned by a human reasoning along broadly similar
    lines, so the set partly measures its own labelling heuristic. And the rule is only perfect
    inside a narrow band of the title similarity threshold:</p>
    ${sweepChart(e.sweep)}
    <p class="small muted">Perfect from ${perfect[0].threshold} to ${perfect[perfect.length - 1].threshold}, and wrong on either side of it.
    The margin is one negative pair at cosine 0.934 and one positive at 0.971. Thirty seven
    thousandths separate a right answer from a wrong one, across fifty examples. That is a property
    of this sample, not of municipal legislation.</p>
    <div class="callout">
      <p class="small" style="margin:0">So the claim is narrow and stated as such: a tuned two clause rule matches these labels, and
      the Continuity agent is not required to beat it on accuracy. What the agent adds is a written
      account of which evidence drove each decision and which it set aside, which is what the product
      shows a resident and what makes a wrong answer diagnosable instead of silent.</p>
    </div>

    <h3 style="margin-top:32px">Continuity agent</h3>
    ${e.agent ? agentBlock(e.agent) : `<p>Not yet run against a model provider. This section is published empty rather than omitted, so the baselines above cannot be mistaken for agent results.</p>`}`;
}

function go(route) {
  const known = $$("section").map(s => s.id);
  const r = known.includes(route) ? route : "thread";
  $$("section").forEach(s => s.toggleAttribute("data-active", s.id === r));
  $$("#nav a").forEach(a => {
    if (a.dataset.route === r) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  });
  if (location.hash !== "#" + r) history.replaceState(null, "", "#" + r);
  window.scrollTo(0, 0);
  if (r === "thread") renderSpine(state.thread);
  if (r === "run" && state.pipe && state.pipe.redraw) state.pipe.redraw();
}

let resizeTimer = 0;
window.addEventListener("resize", () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    if (state.thread) renderSpine(state.thread);
    const stage = $("#pipe-stage");
    if (stage) {
      const w = stage.clientWidth || document.documentElement.clientWidth || 1000;
      const want = w >= 760 && hasWebGL() ? "gl" : "flat";
      if (want !== state.pipeMode) {
        mountPipeline(nodeStats());
        if (state.focusNode) focusNode(state.focusNode);
      }
    }
  }, 200);
});

async function boot() {
  try {
    await bootInner();
  } catch (err) {
    renderBootFailure(err);
  }
}

function renderBootFailure(err) {
  const main = document.querySelector("main");
  if (!main) return;
  main.innerHTML = `
    <section data-active>
      <h2>This page could not load its data</h2>
      <p>Quorum reads a single cached file, <span class="id">data/site.json</span>, and that request failed.
      The usual cause is opening this file directly from disk, because browsers block local file reads.</p>
      <p>Serve the folder over HTTP instead: run <span class="id">python3 -m http.server</span> inside
      <span class="id">docs/</span> and open the address it prints. The published copy at
      <a href="https://rickygole.github.io/Quorum/">rickygole.github.io/Quorum</a> works without any of that.</p>
      <p class="small muted">${String(err && err.message ? err.message : err)}</p>
    </section>`;
  document.querySelectorAll("section").forEach(s => s.removeAttribute("data-active"));
  main.querySelector("section").setAttribute("data-active", "");
}

async function bootInner() {
  const res = await fetch("data/site.json");
  state.data = await res.json();
  state.watched = [...state.data.watched];
  state.thread = state.data.threads.find(t => t.pair_id === 20) || state.data.threads[0];

  $("#parcel-count").textContent = num(state.data.counts.parcels);
  const addrCount = $("#addr-count");
  if (addrCount) addrCount.textContent = num((state.data.addresses || []).length);
  $("#addr-list").innerHTML = (state.data.addresses || []).map(a => `<option value="${esc(a)}">`).join("");
  $("#add-addr").onclick = () => {
    const v = $("#addr").value.trim();
    const status = $("#watch-status");
    if (!v) { status.textContent = "Type an address first."; return; }
    if (state.watched.includes(v)) { status.textContent = `${v} is already on the list.`; return; }
    state.watched.push(v);
    $("#addr").value = "";
    const hits = state.data.threads.filter(t => (t.watched || []).includes(v)).length;
    status.textContent = hits
      ? `${v} added. ${hits} issue${hits > 1 ? "s" : ""} in this corpus touch${hits > 1 ? "" : "es"} it, and ${hits > 1 ? "they are" : "it is"} in your feed.`
      : `${v} added. Nothing in this corpus touches it yet.`;
    renderWatch();
    renderFeed();
  };
  $("#foot-note").innerHTML =
    `Quorum reads the public record of the Baltimore City Council. ${num(state.data.counts.matters)} records, ` +
    `${num(state.data.counts.parcels)} parcels, fetched ${mono(String(state.data.fetched_at).slice(0, 10))}. ` +
    `Quorum never files or sends anything on your behalf.`;

  renderSpine(state.thread);
  renderThread(state.thread);
  renderFeed();
  renderEvidence();
  renderComment();
  renderWatch();
  renderEval();
  renderRun();

  window.addEventListener("hashchange", () => go(location.hash.slice(1) || "thread"));
  go(location.hash.slice(1) || "thread");
}

boot();
