/* Mochimail front end: inbox sidebar, reader drawer, and chat with the agent. */
(() => {
  "use strict";

  const $ = (sel) => document.querySelector(sel);
  const state = { emails: [], me: "", folder: "inbox", selected: null, busy: false };

  /* ───────────── helpers ───────────── */
  const esc = (s) =>
    String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  function hue(str) {
    let h = 0;
    for (const ch of str) h = (h * 31 + ch.charCodeAt(0)) % 360;
    return h;
  }
  function avatar(addr) {
    const h = hue(addr);
    return `<div class="avatar" style="background:linear-gradient(135deg,hsl(${h} 90% 80%),hsl(${(h + 40) % 360} 85% 70%))">${esc(addr[0].toUpperCase())}</div>`;
  }
  function when(ts) {
    const d = new Date(ts);
    const now = new Date();
    if (d.toDateString() === now.toDateString()) return d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
    const opts = { month: "short", day: "numeric" };
    if (d.getFullYear() !== now.getFullYear()) opts.year = "numeric";
    return d.toLocaleDateString([], opts);
  }
  function fullWhen(ts) {
    return new Date(ts).toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
  }

  let toastTimer;
  function toast(msg) {
    const t = $("#toast");
    t.textContent = msg;
    t.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove("show"), 2200);
  }

  async function api(path, opts = {}) {
    const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
    if (!res.ok) {
      let detail = res.statusText;
      try { detail = (await res.json()).detail || detail; } catch { /* ignore */ }
      throw new Error(detail);
    }
    return res.json();
  }

  /* Tiny, safe markdown renderer for the model's replies (escapes first). */
  function inline(s) {
    return esc(s)
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/(^|[^*])\*([^*\n]+)\*/g, "$1<em>$2</em>");
  }
  function table(rows) {
    const cells = (r) => r.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
    const body = rows.filter((r) => !/^[\s|:-]+$/.test(r));
    if (!body.length) return "";
    const [head, ...rest] = body;
    return `<table><thead><tr>${cells(head).map((c) => `<th>${inline(c)}</th>`).join("")}</tr></thead><tbody>${rest
      .map((r) => `<tr>${cells(r).map((c) => `<td>${inline(c)}</td>`).join("")}</tr>`)
      .join("")}</tbody></table>`;
  }
  function md(src) {
    const lines = String(src || "").replace(/\r/g, "").split("\n");
    const out = [];
    const isList = (l) => /^\s*([-*•]|\d+\.)\s+/.test(l);
    const isTable = (l) => /^\s*\|.*\|\s*$/.test(l);
    const isSpecial = (l) => /^```/.test(l) || isTable(l) || isList(l) || /^#{1,6}\s/.test(l);
    let i = 0;
    while (i < lines.length) {
      const l = lines[i];
      if (/^```/.test(l)) {
        const buf = [];
        i++;
        while (i < lines.length && !/^```/.test(lines[i])) buf.push(lines[i++]);
        i++;
        out.push(`<pre>${esc(buf.join("\n"))}</pre>`);
      } else if (isTable(l)) {
        const rows = [];
        while (i < lines.length && isTable(lines[i])) rows.push(lines[i++]);
        out.push(table(rows));
      } else if (isList(l)) {
        const ordered = /^\s*\d+\./.test(l);
        const items = [];
        while (i < lines.length && isList(lines[i])) items.push(lines[i++].replace(/^\s*([-*•]|\d+\.)\s+/, ""));
        const tag = ordered ? "ol" : "ul";
        out.push(`<${tag}>${items.map((x) => `<li>${inline(x)}</li>`).join("")}</${tag}>`);
      } else if (/^#{1,6}\s/.test(l)) {
        out.push(`<p class="h">${inline(l.replace(/^#+\s/, ""))}</p>`);
        i++;
      } else if (!l.trim()) {
        i++;
      } else {
        const para = [];
        while (i < lines.length && lines[i].trim() && !isSpecial(lines[i])) para.push(lines[i++]);
        out.push(`<p>${para.map(inline).join("<br>")}</p>`);
      }
    }
    return out.join("");
  }

  /* ───────────── inbox ───────────── */
  function folderEmails(folder) {
    const me = state.me.toLowerCase();
    const inbox = state.emails.filter((e) => e.recipient.toLowerCase() === me);
    if (folder === "sent") return state.emails.filter((e) => e.sender.toLowerCase() === me);
    if (folder === "unread") return inbox.filter((e) => !e.read);
    return inbox;
  }

  function applyInbox(data, { flashIds = [] } = {}) {
    state.emails = data.emails;
    state.me = data.me;
    $("#me").textContent = data.me;
    $("#modelPill").textContent = data.model;
    $("#modelPill").title = `Together AI · ${data.model}`;
    for (const f of ["inbox", "unread", "sent"]) {
      const n = folderEmails(f).length;
      const el = $(`#c-${f}`);
      el.textContent = n;
      el.toggleAttribute("data-zero", n === 0);
    }
    renderList(flashIds);
    if (state.selected != null) {
      const still = state.emails.find((e) => e.id === state.selected);
      still ? openReader(still.id) : closeReader();
    }
  }

  function renderList(flashIds = []) {
    const list = $("#mailList");
    const items = folderEmails(state.folder);
    if (!items.length) {
      const msg = { inbox: "Inbox zero! Mochi is proud of you.", unread: "All caught up ✨", sent: "Nothing sent yet." }[state.folder];
      list.innerHTML = `<div class="empty"><b>🌙</b>${msg}</div>`;
      return;
    }
    list.innerHTML = items
      .map((e, i) => {
        const other = state.folder === "sent" ? `to ${e.recipient}` : e.sender;
        const cls = ["mail", e.read ? "" : "unread", e.id === state.selected ? "selected" : "", flashIds.includes(e.id) ? "flash" : ""].join(" ");
        return `<button class="${cls}" data-id="${e.id}" style="animation-delay:${Math.min(i * 30, 300)}ms">
          ${avatar(state.folder === "sent" ? e.recipient : e.sender)}
          <div style="min-width:0">
            <div class="mail-top"><span class="who">${esc(other)}</span><span class="when">${when(e.timestamp)}</span></div>
            <div class="subj">${esc(e.subject)}</div>
            <div class="snippet">${esc(e.body)}</div>
          </div>
        </button>`;
      })
      .join("");
  }

  function openReader(id) {
    const e = state.emails.find((x) => x.id === id);
    if (!e) return;
    state.selected = id;
    const mine = e.sender.toLowerCase() === state.me.toLowerCase();
    $("#readerBody").innerHTML = `
      <div class="r-subject">${esc(e.subject)}</div>
      <div class="r-meta">
        ${avatar(mine ? e.recipient : e.sender)}
        <div>
          <div class="r-from">${esc(e.sender)}<span class="r-tag ${e.read ? "read" : ""}">${e.read ? "read" : "unread"}</span></div>
          <div class="r-sub">to ${esc(e.recipient)} · ${fullWhen(e.timestamp)} · #${e.id}</div>
        </div>
      </div>
      <div class="r-body">${esc(e.body)}</div>
      <div class="r-actions">
        ${mine ? "" : `<button class="primary" data-act="reply">💌 Ask Mochi to reply</button>`}
        <button data-act="${e.read ? "unread" : "read"}">${e.read ? "🔵 Mark unread" : "✅ Mark read"}</button>
        <button class="danger" data-act="delete">🗑️ Delete</button>
      </div>`;
    $("#reader").classList.add("open");
    $("#reader").setAttribute("aria-hidden", "false");
    document.querySelectorAll(".mail").forEach((m) => m.classList.toggle("selected", Number(m.dataset.id) === id));
  }

  function closeReader() {
    state.selected = null;
    $("#reader").classList.remove("open");
    $("#reader").setAttribute("aria-hidden", "true");
    document.querySelectorAll(".mail.selected").forEach((m) => m.classList.remove("selected"));
  }

  async function readerAction(act) {
    const id = state.selected;
    const e = state.emails.find((x) => x.id === id);
    if (!e) return;
    try {
      if (act === "reply") {
        closeReader();
        setInput(`Reply to email #${e.id} from ${e.sender} ("${e.subject}") with a friendly answer.`);
        return;
      }
      if (act === "delete") {
        applyInbox(await api(`/api/emails/${id}`, { method: "DELETE" }));
        closeReader();
        toast("🗑️ Email deleted");
      } else {
        applyInbox(await api(`/api/emails/${id}/${act}`, { method: "POST" }));
        toast(act === "read" ? "✅ Marked as read" : "🔵 Marked as unread");
      }
    } catch (err) {
      toast(`⚠️ ${err.message}`);
    }
  }

  /* ───────────── chat ───────────── */
  const TOOL_ICONS = {
    list_all_emails: "📬", list_unread_emails: "📩", search_emails: "🔍", filter_emails: "🧹",
    search_unread_from_sender: "👀", get_email: "📖", mark_email_as_read: "✅",
    mark_email_as_unread: "🔵", send_email: "💌", delete_email: "🗑️",
  };

  function argSummary(args) {
    const entries = Object.entries(args || {});
    if (!entries.length) return "";
    return entries.map(([k, v]) => `${k}: ${typeof v === "string" ? v : JSON.stringify(v)}`).join(" · ");
  }

  function renderSteps(steps) {
    if (!steps.length) return "";
    return `<div class="steps">
      <div class="steps-title">🧭 ${steps.length} tool step${steps.length > 1 ? "s" : ""} · ${steps.map((s) => esc(s.name)).join(" → ")}</div>
      ${steps
        .map(
          (s, i) => `<details class="step">
            <summary>
              <span class="step-num">${i + 1}</span>
              <span>${TOOL_ICONS[s.name] || "🔧"}</span>
              <span class="step-name">${esc(s.name)}</span>
              <span class="step-args">${esc(argSummary(s.args))}</span>
              <span class="step-caret">›</span>
            </summary>
            <div class="step-body">
              <label>Arguments</label><pre>${esc(JSON.stringify(s.args, null, 2))}</pre>
              <label>Result</label><pre>${esc(JSON.stringify(s.result, null, 2))}</pre>
            </div>
          </details>`
        )
        .join("")}
    </div>`;
  }

  const thread = $("#thread");
  const BOT_FACE = `<svg class="bot-face"><use href="#mochi"/></svg>`;

  function addMessage(html, who, extraClass = "") {
    const div = document.createElement("div");
    div.className = `msg ${who} ${extraClass}`;
    div.innerHTML = who === "bot" ? `${BOT_FACE}<div class="bubble">${html}</div>` : `<div class="bubble">${html}</div>`;
    thread.appendChild(div);
    thread.scrollTop = thread.scrollHeight;
    return div;
  }

  const THINKING = [
    "Mochi is sniffing through your inbox…",
    "Fluffing up the tools…",
    "Sorting letters with tiny paws…",
    "Asking the moon for advice…",
  ];

  async function send(text) {
    text = text.trim();
    if (!text || state.busy) return;
    state.busy = true;
    document.body.classList.add("chatting", "busy");
    $("#sendBtn").disabled = true;
    setInput("");

    addMessage(esc(text), "user");
    const pending = addMessage(
      `<div class="thinking"><span class="dots"><span></span><span></span><span></span></span><span>${THINKING[Math.floor(Math.random() * THINKING.length)]}</span></div>`,
      "bot"
    );

    const before = new Map(state.emails.map((e) => [e.id, e.read]));
    try {
      const data = await api("/api/agent", { method: "POST", body: JSON.stringify({ message: text }) });
      pending.remove();
      if (data.error) {
        addMessage(`<p><strong>Oh no, Mochi tripped 🥺</strong></p><p>${esc(data.error)}</p>`, "bot", "error");
      } else {
        addMessage(md(data.reply || "_(no reply)_") + renderSteps(data.steps || []), "bot");
      }
      // Highlight anything the agent created or changed.
      const changed = data.emails.filter((e) => !before.has(e.id) || before.get(e.id) !== e.read).map((e) => e.id);
      applyInbox(data, { flashIds: changed });
    } catch (err) {
      pending.remove();
      addMessage(`<p><strong>Couldn't reach the server.</strong></p><p>${esc(err.message)}</p>`, "bot", "error");
    } finally {
      state.busy = false;
      document.body.classList.remove("busy");
      $("#sendBtn").disabled = false;
      $("#input").focus();
    }
  }

  /* ───────────── composer ───────────── */
  const input = $("#input");
  function autosize() {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 160) + "px";
  }
  function setInput(text) {
    input.value = text;
    autosize();
    input.focus();
    input.setSelectionRange(text.length, text.length);
  }

  /* ───────────── night garden ───────────── */
  function seeded(seed) {
    return () => {
      seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
      let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function buildGarden() {
    const rnd = seeded(42);
    const pick = (arr) => arr[Math.floor(rnd() * arr.length)];
    const W = 1600, H = 900;
    const BLOOMS = ["#5fb4ff", "#7fd0ff", "#3f86ff", "#ff8fc0", "#ff6fa8", "#ffb3d1", "#a78bfa", "#c8b4ff", "#8fe3ff"];
    const LEAVES = ["#24358f", "#2c43a8", "#3550c4", "#3a3aa6", "#2a4fb0", "#4a3fb8", "#1f2e7e"];

    // Keep the middle clear for the mascot and composer.
    const inClearing = (x, y) => x > 470 && x < 1130 && y < 780;
    const spot = (minY) => {
      for (let tries = 0; tries < 30; tries++) {
        const x = rnd() * W;
        const y = minY + rnd() * (H - minY);
        const sideBand = x < 380 || x > 1220;
        if ((sideBand || y > 640) && !inClearing(x, y)) return [x, y];
      }
      return [rnd() < 0.5 ? rnd() * 300 : W - rnd() * 300, H - rnd() * 150];
    };

    let leaves = "", flowers = "";
    for (let i = 0; i < 260; i++) {
      const [x, y] = spot(330);
      const len = 45 + rnd() * 120 * (y / H);
      const w = len * (0.18 + rnd() * 0.12);
      const ang = -35 + rnd() * 70;
      // Position lives on the <g>; the CSS sway animation lives on the <path>
      // (a CSS transform would otherwise override the SVG transform attribute).
      leaves += `<g transform="translate(${x.toFixed(0)} ${y.toFixed(0)}) rotate(${ang.toFixed(0)})"><path class="sway" style="animation-delay:${(-rnd() * 6).toFixed(2)}s"
        d="M0 0 Q${w.toFixed(1)} ${(-len / 2).toFixed(1)} 0 ${(-len).toFixed(1)} Q${(-w).toFixed(1)} ${(-len / 2).toFixed(1)} 0 0Z"
        fill="${pick(LEAVES)}" opacity="${(0.55 + rnd() * 0.4).toFixed(2)}"/></g>`;
    }
    for (let i = 0; i < 95; i++) {
      const [x, y] = spot(300);
      const r = (10 + rnd() * 16) * (0.6 + (y / H) * 0.8);
      const color = pick(BLOOMS);
      const n = rnd() < 0.7 ? 5 : 6;
      const rot = rnd() * 360;
      let petals = "";
      for (let p = 0; p < n; p++) {
        petals += `<ellipse cx="${(r * 0.55).toFixed(1)}" cy="0" rx="${(r * 0.55).toFixed(1)}" ry="${(r * 0.33).toFixed(1)}" transform="rotate(${((360 / n) * p).toFixed(0)})" fill="${color}"/>`;
      }
      flowers += `<g transform="translate(${x.toFixed(0)} ${y.toFixed(0)}) rotate(${rot.toFixed(0)})" opacity="${(0.75 + rnd() * 0.25).toFixed(2)}">
        ${petals}<circle r="${(r * 0.3).toFixed(1)}" fill="#fff6d6"/><circle r="${(r * 0.15).toFixed(1)}" fill="#ffd27a"/></g>`;
    }
    $("#garden").innerHTML = `<g>${leaves}</g><g filter="url(#glow)">${flowers}</g>`;

    // Stars
    const sky = $("#sky");
    let stars = "";
    for (let i = 0; i < 110; i++) {
      const s = rnd() < 0.85 ? 1.5 + rnd() * 1.5 : 3 + rnd() * 2;
      stars += `<span class="star" style="left:${(rnd() * 100).toFixed(2)}%;top:${(rnd() * 60).toFixed(2)}%;width:${s.toFixed(1)}px;height:${s.toFixed(1)}px;animation-delay:${(-rnd() * 4).toFixed(2)}s;animation-duration:${(2.5 + rnd() * 3).toFixed(2)}s${s > 3 ? ";box-shadow:0 0 6px #fff" : ""}"></span>`;
    }
    sky.innerHTML = stars;

    // Falling petals
    let petalsHtml = "";
    for (let i = 0; i < 12; i++) {
      petalsHtml += `<span class="petal" style="left:${(rnd() * 100).toFixed(1)}%;animation-duration:${(11 + rnd() * 10).toFixed(1)}s;animation-delay:${(-rnd() * 20).toFixed(1)}s;transform:scale(${(0.6 + rnd() * 0.7).toFixed(2)})"></span>`;
    }
    $("#petals").innerHTML = petalsHtml;
  }

  /* ───────────── wire up ───────────── */
  $("#composer").addEventListener("submit", (e) => { e.preventDefault(); send(input.value); });
  input.addEventListener("input", autosize);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); send(input.value); }
  });
  $("#chips").addEventListener("click", (e) => {
    const chip = e.target.closest(".chip");
    if (chip) send(chip.textContent.replace(/^\S+\s/, ""));
  });
  $("#newBtn").addEventListener("click", () => { closeReader(); setInput(""); });

  document.querySelectorAll(".folder").forEach((btn) =>
    btn.addEventListener("click", () => {
      document.querySelectorAll(".folder").forEach((b) => b.classList.toggle("active", b === btn));
      state.folder = btn.dataset.folder;
      renderList();
    })
  );
  $("#mailList").addEventListener("click", (e) => {
    const item = e.target.closest(".mail");
    if (!item) return;
    const id = Number(item.dataset.id);
    state.selected === id ? closeReader() : openReader(id);
  });
  $("#readerClose").addEventListener("click", closeReader);
  $("#readerBody").addEventListener("click", (e) => {
    const b = e.target.closest("[data-act]");
    if (b) readerAction(b.dataset.act);
  });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeReader(); });

  $("#resetBtn").addEventListener("click", async () => {
    try {
      applyInbox(await api("/api/reset", { method: "POST" }));
      thread.innerHTML = "";
      document.body.classList.remove("chatting");
      toast("🌱 Inbox restored");
    } catch (err) {
      toast(`⚠️ ${err.message}`);
    }
  });

  buildGarden();
  api("/api/emails").then((d) => applyInbox(d)).catch((err) => toast(`⚠️ ${err.message}`));
  input.focus();
})();
