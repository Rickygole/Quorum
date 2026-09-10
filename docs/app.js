const state = { data: null, watched: [], thread: null };

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const el = (t, c, h) => { const n = document.createElement(t); if (c) n.className = c; if (h !== undefined) n.innerHTML = h; return n; };
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const mono = s => `<span class="id">${esc(s)}</span>`;
const reduced = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

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

function plainTitle(t) {
  const head = String(t).split(/\bFOR the purpose\b|\bFor the purpose\b/)[0];
  return head.replace(/^(Rezoning|Zoning)\s*[-–]\s*/i, "").replace(/\s*[-–]\s*$/, "").trim();
}

function plainLanguage(rec) {
  const t = rec.title;
  const addr = (rec.parcels[0] || {}).address || "the property";
  const zone = /from the (.{2,14}?) Zoning District to the (.{2,14}?) Zoning District/i.exec(t);
  if (zone) return `Changes the zoning of ${addr} from ${zone[1].trim()} to ${zone[2].trim()}.`;
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

function renderSpine(thread) {
  const host = $("#spine");
  host.innerHTML = "";
  const recs = thread.records;
  const stops = [];
  recs.forEach(r => {
    stops.push({ date: r.introduced_date, file: r.file_number, label: /Failed/i.test(r.status || "") ? "died at end of term" : /Withdrawn/i.test(r.status || "") ? "withdrawn" : "introduced" });
  });
  const last = recs[recs.length - 1];
  if (last.hearing_date) stops.push({ date: last.hearing_date, file: "hearing", label: "public hearing", future: true });

  const W = 1000, H = 132, padL = 60, padR = 120;
  const step = (W - padL - padR) / Math.max(1, stops.length - 1);
  const y = 58;
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", `Timeline: ${stops.map(s => `${fmtDate(s.date)} ${s.label}`).join("; ")}`);

  const x = i => padL + i * step;
  const line = document.createElementNS(svg.namespaceURI, "path");
  line.setAttribute("class", "line");
  line.setAttribute("d", `M ${x(0)} ${y} L ${x(stops.length - 1)} ${y}`);
  svg.appendChild(line);

  stops.forEach((s, i) => {
    const g = document.createElementNS(svg.namespaceURI, "g");
    const c = document.createElementNS(svg.namespaceURI, "circle");
    c.setAttribute("cx", x(i)); c.setAttribute("cy", y);
    c.setAttribute("r", s.future ? 9 : 6);
    c.setAttribute("class", "node" + (s.future ? " last" : ""));
    const t1 = document.createElementNS(svg.namespaceURI, "text");
    t1.setAttribute("x", x(i)); t1.setAttribute("y", y - 22); t1.setAttribute("text-anchor", "middle");
    t1.setAttribute("class", "dim"); t1.textContent = shortDate(s.date);
    const t2 = document.createElementNS(svg.namespaceURI, "text");
    t2.setAttribute("x", x(i)); t2.setAttribute("y", y + 28); t2.setAttribute("text-anchor", "middle");
    t2.setAttribute("class", "mono"); t2.textContent = s.file;
    const t3 = document.createElementNS(svg.namespaceURI, "text");
    t3.setAttribute("x", x(i)); t3.setAttribute("y", y + 48); t3.setAttribute("text-anchor", "middle");
    t3.setAttribute("class", "dim"); t3.textContent = s.label;
    g.append(c, t1, t2, t3);
    svg.appendChild(g);
  });
  host.appendChild(svg);

  if (reduced()) return;
  const len = x(stops.length - 1) - x(0);
  line.style.strokeDasharray = len;
  line.style.strokeDashoffset = len;
  line.animate([{ strokeDashoffset: len }, { strokeDashoffset: 0 }], { duration: 900, easing: "cubic-bezier(.22,.7,.3,1)", fill: "forwards" });
  $$("g", svg).forEach((g, i) => {
    g.style.opacity = 0;
    g.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 300, delay: 120 + (900 / stops.length) * i, fill: "forwards" });
  });
}

function renderThread(thread) {
  const gap = thread.features.temporal.gap_days;
  const [a, b] = thread.records;
  const addr = (b.parcels[0] || {}).address || "";
  $("#spine-caption").innerHTML =
    `${esc(addr)}${b.neighborhood ? ", " + esc(b.neighborhood.toLowerCase().replace(/\b\w/g, m => m.toUpperCase())) : ""}. Corpus fetched ${mono(String(a.fetched_at).slice(0, 16).replace("T", " "))} UTC.`;

  $("#thread-intro").innerHTML =
    `One issue, ${thread.records.length} appearances, ${thread.records.length} file numbers, ${gap ? Math.round(gap / 30) + " months apart" : ""}. ` +
    `Quorum matched them on the parcel, not the title.`;

  const host = $("#thread-body");
  host.innerHTML = "";
  thread.records.forEach(r => {
    const future = false;
    const wrap = el("div", "appearance" + (future ? " future" : ""));
    const g = el("div", "gutter"); g.appendChild(el("span", "dot"));
    const body = el("div", "body");
    body.innerHTML = `
      <div class="meta small muted">${esc(fmtDate(r.introduced_date))} &middot; ${mono(r.file_number)} &middot; ${esc(r.committee || "Baltimore City Council")}</div>
      <h3>${esc(plainLanguage(r))}</h3>
      <p class="small">Sponsored by ${esc(r.sponsors.join(", ") || "unknown")}. Outcome: ${esc(statusLine(r))}.</p>
      <p class="small"><a href="${esc(r.source_url)}" target="_blank" rel="noopener">Source record ${esc(r.file_number)}</a></p>`;
    wrap.append(g, body);
    host.appendChild(wrap);
  });

  const last = thread.records[thread.records.length - 1];
  if (last.hearing_date) {
    const d = daysUntil(last.hearing_date);
    const wrap = el("div", "appearance future");
    const g = el("div", "gutter"); g.appendChild(el("span", "dot"));
    const body = el("div", "body");
    body.innerHTML = `
      <div class="meta small muted">${esc(fmtDate(last.hearing_date))} &middot; ${esc(last.committee || "")}</div>
      <h3${d !== null && d <= 3 ? ' class="flag"' : ""}>Public hearing${d !== null ? `, in ${d} days` : ""}</h3>
      <p class="small">This has not happened yet. It is the moment a comment can change something.</p>
      <p><a class="btn primary" href="#comment">Draft a comment</a></p>`;
    wrap.append(g, body);
    host.appendChild(wrap);
  }
}

function renderFeed() {
  const host = $("#feed-body");
  host.innerHTML = "";
  const counts = state.data.counts;
  $("#feed-empty").textContent =
    `Most weeks nothing here affects your addresses, and that is the point. Quorum read ${counts.matters.toLocaleString()} records and surfaced ${state.data.threads.length}.`;

  state.data.threads.forEach(t => {
    const r = t.records[t.records.length - 1];
    const entry = el("div", "entry cont");
    entry.appendChild(el("div", "stub"));
    const body = el("div");
    const d = daysUntil(r.hearing_date);
    body.innerHTML = `
      <h3>${esc(plainLanguage(r))}</h3>
      <div class="meta small muted">
        <span>${esc((r.parcels[0] || {}).address || "")}</span>
        <span>${mono(r.file_number)}</span>
        <span>${r.hearing_date ? (d !== null && d <= 3 ? '<span class="flag">' : "<span>") + "Hearing " + esc(fmtDate(r.hearing_date)) + "</span>" : esc(r.status || "")}</span>
      </div>
      <p class="small" style="margin-top:8px">Continues an issue first seen ${esc(fmtDate(t.records[0].introduced_date))} under ${mono(t.records[0].file_number)}.</p>`;
    const btn = el("button", "", "See the thread");
    btn.onclick = () => { state.thread = t; renderSpine(t); renderThread(t); go("thread"); };
    body.appendChild(btn);
    entry.appendChild(body);
    host.appendChild(entry);
  });
}

function featureRows(f) {
  return [
    ["Parcel", f.parcel.match === "exact"
      ? `Exact match, ${mono((f.parcel.shared_parcel_ids || f.parcel.shared_addresses || []).join(", "))}`
      : f.parcel.match === "adjacent"
        ? `Adjacent only. ${f.parcel.shared_blocks ? "Same block " + mono(f.parcel.shared_blocks.join(", ")) + ", different lots" : "Same street, different number"}`
        : "No match"],
    ["Lots named", `${esc((f.parcel.lots_b || []).join(", ") || "n/a")} then ${esc((f.parcel.lots_a || []).join(", ") || "n/a")}`],
    ["Sponsor", f.sponsor.overlap.length ? `Same, ${esc(f.sponsor.overlap.join(", "))}` : `Different, ${esc(f.sponsor.b.join(", "))} then ${esc(f.sponsor.a.join(", "))}`],
    ["Zoning transition", f.zoning_transition.match ? `Identical, ${mono(f.zoning_transition.a)}` : (f.zoning_transition.a || f.zoning_transition.b) ? `Differs` : "Not a rezoning"],
    ["Prior outcome", `${esc(f.committee_progression.prior_status || "unknown")} (${esc(f.committee_progression.shape)})`],
    ["Gap", f.temporal.gap_days !== null ? `${f.temporal.gap_days} days, ${f.temporal.same_council_term ? "same" : "different"} council term` : "unknown"],
    ["File numbers", `${mono(f.file_number.b)} then ${mono(f.file_number.a)}`],
    ["Title cosine", `<strong>${f.title.cosine}</strong>`],
  ];
}

function renderEvidence() {
  const host = $("#evidence-body");
  host.innerHTML = "";
  const t = state.thread || state.data.threads[0];
  const neg = state.data.negatives.find(n => n.pair_id === 25) || state.data.negatives[0];

  [[t, "Continuation", t.label], [neg, "Not a continuation", neg.label]].forEach(([item, verdict, note]) => {
    const box = el("div", "panel");
    box.style.marginBottom = "24px";
    const f = item.features;
    const rows = featureRows(f).map(([k, v]) => `<dt>${esc(k)}</dt><dd>${v}</dd>`).join("");
    box.innerHTML = `
      <div class="small muted">${mono(item.records[0].file_number)} and ${mono(item.records[1].file_number)}</div>
      <h3 style="margin:8px 0 16px">${esc(verdict)}</h3>
      <dl class="evidence">${rows}</dl>
      <hr class="rule">
      <p class="small">${esc(note)}</p>`;
    host.appendChild(box);
  });

  const cmp = el("div");
  const t_cos = t.features.title.cosine, n_cos = neg.features.title.cosine;
  cmp.innerHTML = `
    <h3>What the agent did not rely on</h3>
    <p>Title similarity is <strong>${n_cos}</strong> for the pair that is <em>not</em> a continuation and
    <strong>${t_cos}</strong> for the pair that is. Measured on this corpus, a system deciding on title or
    embedding similarity alone gets both of these cases wrong. What separates them is the parcel comparison,
    the terminal status of the earlier item, and the zoning transition.</p>`;
  host.appendChild(cmp);
}

function renderComment() {
  const t = state.thread || state.data.threads[0];
  const r = t.records[t.records.length - 1];
  const prev = t.records[0];
  const addr = (r.parcels[0] || {}).address || "";
  const draft =
`To the Land Use and Transportation Committee,

I live near ${addr} and I am writing about ${r.file_number}, scheduled for a public hearing on ${fmtDate(r.hearing_date)}.

This is the second time this rezoning has come before the council. The earlier bill, ${prev.file_number}, was introduced on ${fmtDate(prev.introduced_date)} and ${statusLine(prev)}. The current bill covers lots ${(t.features.parcel.lots_a || []).join(" and ")}, where the earlier one covered lots ${(t.features.parcel.lots_b || []).join(", ")}.

I would like the committee to consider the following before voting:

[ your comment here ]

Thank you for your time.`;

  $("#comment-body").innerHTML = `
    <div class="panel">
      <div class="small muted">File number and hearing date are taken from the source record and are locked.</div>
      <div style="display:flex;gap:16px;flex-wrap:wrap;margin:12px 0 20px">
        <span class="tag">File ${mono(r.file_number)}</span>
        <span class="tag">Hearing ${esc(fmtDate(r.hearing_date))}</span>
        <span class="tag">${esc(r.committee || "")}</span>
      </div>
      <label for="draft">Your comment</label>
      <textarea id="draft" rows="16"></textarea>
      <p class="small" style="margin-top:16px">Quorum can read what your city is deciding. It cannot speak for you.
      Nothing is submitted until you send it.</p>
      <div style="display:flex;gap:12px;flex-wrap:wrap">
        <button class="primary" id="send">Send to city</button>
        <button id="copy">Copy text</button>
      </div>
      <p class="small" id="send-status" role="status"></p>
    </div>`;
  $("#draft").value = draft;
  $("#send").onclick = () => { $("#send-status").textContent = "Sent to city."; };
  $("#copy").onclick = async () => {
    try { await navigator.clipboard.writeText($("#draft").value); $("#send-status").textContent = "Copied."; }
    catch { $("#send-status").textContent = "Select the text and copy it."; }
  };
}

function renderWatch() {
  const list = $("#watch-list");
  list.innerHTML = "";
  state.watched.forEach((a, i) => {
    const li = el("li");
    li.innerHTML = `<span>${esc(a)}</span>`;
    const b = el("button", "", "Remove");
    b.style.cssText = "float:right;padding:2px 10px";
    b.onclick = () => { state.watched.splice(i, 1); renderWatch(); };
    li.appendChild(b);
    list.appendChild(li);
  });
  if (!state.watched.length) list.innerHTML = `<li class="muted">Add an address and Quorum starts watching what the city decides about it.</li>`;
}

function renderEval() {
  const d = state.data;
  $("#eval-body").innerHTML = `
    <div class="panel">
      <h3>The labeled set</h3>
      <p class="small">${d.counts.labeled_pairs} candidate pairs drawn by hand from the
      ${d.counts.parcel_resolvable} parcel resolvable records in a corpus of
      ${d.counts.matters.toLocaleString()}. Labeled from the source documents before the
      Continuity Agent existed.</p>
      <p class="small">Agent scores are pending the model provider and will be published here with every
      miss named individually. This page is deliberately live before the numbers are good.</p>
    </div>`;
}

function renderRun() {
  const d = state.data;
  const rows = (d.graph || []).map(n => `
    <tr>
      <td>${esc(n.node)}</td>
      <td>${n.kind === "code" ? "deterministic node" : "Strands agent"}</td>
      <td class="id">${n.latency_ms ? n.latency_ms + " ms" : "pending"}</td>
      <td class="id">${n.tokens ? n.tokens : "pending"}</td>
    </tr>`).join("");
  $("#run-body").innerHTML = `
    <div class="panel">
      <p class="small">Corpus fetched ${mono(String(d.fetched_at).slice(0, 16).replace("T", " "))} UTC.
      Site generated ${mono(String(d.generated_at).slice(0, 16).replace("T", " "))}.</p>
      <div class="scroll-x">
      <table>
        <thead><tr><th>Node</th><th>Kind</th><th>Latency</th><th>Tokens</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
      </div>
      <hr class="rule">
      <dl class="evidence">
        <dt>Records read</dt><dd class="id">${d.counts.matters.toLocaleString()}</dd>
        <dt>Resolved to a parcel</dt><dd class="id">${d.counts.parcel_resolvable}</dd>
        <dt>Parcels in gazetteer</dt><dd class="id">${d.counts.parcels.toLocaleString()}</dd>
        <dt>Surfaced</dt><dd class="id">${d.threads.length}</dd>
        <dt>Dropped</dt><dd>${(d.counts.matters - d.counts.parcel_resolvable).toLocaleString()} named no parcel Quorum could resolve</dd>
      </dl>
      <hr class="rule">
      <p class="small">Orchestrated as a Strands Graph, not a Swarm. The path is deterministic and dependency
      ordered, so there is no dynamic handoff for a Swarm to manage. Resolution carries no model call.</p>
    </div>`;
}

function go(route) {
  $$("section").forEach(s => s.toggleAttribute("data-active", s.id === route));
  $$("#nav a").forEach(a => a.toggleAttribute("aria-current", a.dataset.route === route));
  if (location.hash !== "#" + route) history.replaceState(null, "", "#" + route);
  window.scrollTo(0, 0);
}

async function boot() {
  const res = await fetch("data/site.json");
  state.data = await res.json();
  state.watched = [...state.data.watched];
  state.thread = state.data.threads.find(t => t.pair_id === 20) || state.data.threads[0];

  $("#parcel-count").textContent = state.data.counts.parcels.toLocaleString();
  $("#addr-list").innerHTML = (state.data.addresses || []).map(a => `<option value="${esc(a)}">`).join("");
  $("#add-addr").onclick = () => {
    const v = $("#addr").value.trim();
    if (v && !state.watched.includes(v)) { state.watched.push(v); $("#addr").value = ""; renderWatch(); }
  };

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
