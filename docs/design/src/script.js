(function () {
  "use strict";
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  function el(tag, attrs, html) {
    var e = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    if (html != null) e.innerHTML = html;
    return e;
  }
  function esc(s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;"); }
  function icon(id, w, h) { return '<svg viewBox="0 0 ' + w + ' ' + h + '" aria-hidden="true"><use href="#i-' + id + '"/></svg>'; }

  /* ------------------------------------------------------------ maps */
  var LAYERS = [["labels", "Labels"], ["pois", "Points"], ["missions", "Missions"], ["routes", "Routes"],
                ["security", "Security"], ["elevated", "Upper levels"], ["restricted", "Restricted"]];
  $$(".mapview").forEach(function (mv) {
    var svg = $("svg", mv), frame = $(".mapframe", mv), info = $(".mapinfo", mv), tools = $(".maptools", mv);
    if (!svg) return;
    var vb0 = svg.getAttribute("viewBox").split(/\s+/).map(Number);
    var vb = vb0.slice();
    function apply() { svg.setAttribute("viewBox", vb.map(function (v) { return v.toFixed(1); }).join(" ")); }
    function zoom(f, cx, cy) {
      var w = Math.min(vb0[2], Math.max(vb0[2] / 8, vb[2] / f)), h = w * vb0[3] / vb0[2];
      if (cx == null) { cx = vb[0] + vb[2] / 2; cy = vb[1] + vb[3] / 2; }
      var rx = (cx - vb[0]) / vb[2], ry = (cy - vb[1]) / vb[3];
      vb = [cx - rx * w, cy - ry * h, w, h]; clamp(); apply();
    }
    function clamp() {
      vb[0] = Math.max(vb0[0], Math.min(vb0[0] + vb0[2] - vb[2], vb[0]));
      vb[1] = Math.max(vb0[1], Math.min(vb0[1] + vb0[3] - vb[3], vb[1]));
    }
    [["+", function () { zoom(1.5); }, "Zoom in"], ["−", function () { zoom(1 / 1.5); }, "Zoom out"],
     ["Fit", function () { vb = vb0.slice(); apply(); }, "Show the whole map"]].forEach(function (b) {
      var bt = el("button", { type: "button", "aria-label": b[2] }, b[0]); bt.addEventListener("click", b[1]); tools.appendChild(bt);
    });
    tools.appendChild(el("span", { "class": "sep" }));
    LAYERS.forEach(function (L) {
      var g = $$('g[data-layer="' + L[0] + '"]', svg);
      if (!g.length) return;
      var id = mv.dataset.map + "-ly-" + L[0];
      var lab = el("label", { "class": "layer", "for": id });
      var cb = el("input", { type: "checkbox", id: id }); cb.checked = true;
      cb.addEventListener("change", function () { g.forEach(function (x) { x.setAttribute("display", cb.checked ? "inline" : "none"); }); });
      lab.appendChild(cb); lab.appendChild(document.createTextNode(L[1])); tools.appendChild(lab);
    });
    // drag to pan, pinch and ctrl+wheel to zoom
    var pts = {}, last = null, pinch = null, down = [0, 0];
    function toSvg(e) {
      var r = svg.getBoundingClientRect();
      return [vb[0] + (e.clientX - r.left) / r.width * vb[2], vb[1] + (e.clientY - r.top) / r.height * vb[3]];
    }
    frame.addEventListener("pointerdown", function (e) {
      pts[e.pointerId] = [e.clientX, e.clientY]; down = [e.clientX, e.clientY];
      last = [e.clientX, e.clientY];
      var ids = Object.keys(pts); if (ids.length === 2) { var a = pts[ids[0]], b = pts[ids[1]]; pinch = Math.hypot(a[0] - b[0], a[1] - b[1]); }
    });
    frame.addEventListener("pointermove", function (e) {
      if (!pts[e.pointerId]) return;
      pts[e.pointerId] = [e.clientX, e.clientY];
      if (!frame.hasPointerCapture(e.pointerId) && Math.hypot(e.clientX - down[0], e.clientY - down[1]) > 4) {
        try { frame.setPointerCapture(e.pointerId); } catch (err) { /* capture is optional */ }
        frame.classList.add("drag");
      }
      var ids = Object.keys(pts), r = svg.getBoundingClientRect();
      if (ids.length === 2 && pinch) {
        var a = pts[ids[0]], b = pts[ids[1]], d = Math.hypot(a[0] - b[0], a[1] - b[1]);
        var c = toSvg({ clientX: (a[0] + b[0]) / 2, clientY: (a[1] + b[1]) / 2 });
        zoom(d / pinch, c[0], c[1]); pinch = d; return;
      }
      if (vb[2] >= vb0[2] - 0.5) { last = [e.clientX, e.clientY]; return; }
      vb[0] -= (e.clientX - last[0]) / r.width * vb[2]; vb[1] -= (e.clientY - last[1]) / r.height * vb[3];
      last = [e.clientX, e.clientY]; clamp(); apply();
    });
    function up(e) { delete pts[e.pointerId]; pinch = null; if (!Object.keys(pts).length) frame.classList.remove("drag"); }
    frame.addEventListener("pointerup", up); frame.addEventListener("pointercancel", up);
    frame.addEventListener("wheel", function (e) {
      if (!e.ctrlKey && !e.metaKey) return;
      e.preventDefault(); var c = toSvg(e); zoom(e.deltaY < 0 ? 1.25 : 0.8, c[0], c[1]);
    }, { passive: false });
    frame.addEventListener("dblclick", function (e) { var c = toSvg(e); zoom(1.8, c[0], c[1]); });
    // legend hover finds the marker; clicking either shows its note
    function target(ref) { return $('[data-poi="' + ref + '"]', svg); }
    function show(node) {
      var t = node && $("title", node);
      if (!t) return;
      var txt = t.textContent, i = txt.indexOf(":");
      info.innerHTML = i > 0 ? "<b>" + esc(txt.slice(0, i)) + "</b>  " + esc(txt.slice(i + 1)) : "<b>" + esc(txt) + "</b>";
    }
    $$("[data-poi-ref]", svg).forEach(function (lg) {
      var ref = lg.getAttribute("data-poi-ref");
      lg.addEventListener("mouseenter", function () { var t = target(ref); if (t) t.classList.add("hl"); });
      lg.addEventListener("mouseleave", function () { var t = target(ref); if (t) t.classList.remove("hl"); });
      lg.addEventListener("click", function () { show(target(ref)); });
      lg.style.cursor = "pointer";
    });
    $$("[data-poi], .enemy", svg).forEach(function (m) {
      m.addEventListener("click", function (e) { e.stopPropagation(); show(m); });
    });
  });

  /* ------------------------------------------------------------ skills */
  var SKILLS = [
    { id: "firearms", n: "Firearms", p: [["Steady Hands", "spread -20 %"], ["Quick Reload", "reload -25 %"], ["Headhunter", "headshots x3.0"], ["Recoil Control", "recoil -40 %"], ["Deadeye", "still 1 s: zero spread, x1.5", ["stealth", 1]]] },
    { id: "melee", n: "Melee", p: [["Clubber", "melee +25 %"], ["Silent Takedown", "takedowns silent"], ["Quick Hands", "takedowns -50 % time"], ["Heavy Hitter", "take down heavies"], ["One-Punch", "frontal KO, I <= 3", ["stealth", 2]]] },
    { id: "stealth", n: "Stealth", p: [["Soft Steps", "footsteps -30 %"], ["Low Profile", "crouch 3.0 m/s, x0.45"], ["Shadow", "x0.5 in the dark"], ["Ghost", "silent sprint"], ["Vanish", "searches end 2x sooner"]] },
    { id: "hacking", n: "Hacking", p: [["Script Kiddie", "tier 1 devices"], ["Operator", "tier 2, -20 % time"], ["Turret Control", "turn turrets, loop cams"], ["Root Access", "tier 3"], ["Ghost Login", "keep multitools; 6 m"]] },
    { id: "lockpicking", n: "Lockpicking", p: [["Rake", "tier 1 locks"], ["Tension", "tier 2"], ["Fast Picks", "-50 % time"], ["Master Picks", "tier 3"], ["Safecracker", "keep picks; safes x0.5"]] },
    { id: "deception", n: "Deception", p: [["Passing Glance", "disguises work"], ["Fast Talk", "talk down a blown cover"], ["Master of Disguise", "weapon grace 2 s", ["stealth", 2]], ["Silver Tongue", "suspicion -25 %"], ["Doppelganger", "scrutiny halved"]] },
    { id: "persuasion", n: "Persuasion", p: [["Friendly", "rumours; rep +25 %"], ["Haggler", "buy -15 %, sell +15 %"], ["Intimidate", "threats; surrenders"], ["Negotiator", "bribes -40 %"], ["Kingmaker", "turn lieutenants", ["deception", 3]]] }
  ];
  var START = { firearms: 0, melee: 0, stealth: 0, hacking: 0, lockpicking: 0, deception: 1, persuasion: 0 };
  var EXAMPLE = { firearms: 0, melee: 1, stealth: 2, hacking: 1, lockpicking: 2, deception: 3, persuasion: 1 };
  var ranks = Object.assign({}, EXAMPLE);
  function costTo(r) { var c = 0; for (var k = 1; k <= r; k++) c += k <= 2 ? 1 : 2; return c; }
  function spent() { var s = 0; SKILLS.forEach(function (sk) { s += costTo(ranks[sk.id]); }); return s - 1; }
  function total() { return 4 + 2 * (+$("#lvl").value - 1) + (+$("#chips").value); }
  function reqFor(sk, r) { return sk.p[r - 1][2]; }
  function whyNot(sk, r) {
    var req = reqFor(sk, r);
    if (req && ranks[req[0]] < req[1]) return "needs " + SKILLS.filter(function (s) { return s.id === req[0]; })[0].n + " " + req[1];
    var need = r <= 2 ? 1 : 2;
    if (total() - spent() < need) return "needs " + need + " point" + (need > 1 ? "s" : "");
    return null;
  }
  function blocksSell(skId, newRank) {
    for (var i = 0; i < SKILLS.length; i++) {
      var s = SKILLS[i];
      for (var r = 1; r <= ranks[s.id]; r++) { var q = reqFor(s, r); if (q && q[0] === skId && newRank < q[1]) return s.n + " " + r + " needs it"; }
    }
    return null;
  }
  function renderTrees() {
    var host = $("#trees"); host.innerHTML = "";
    SKILLS.forEach(function (sk) {
      var t = el("div", { "class": "tree" });
      t.appendChild(el("h4", null, esc(sk.n) + '<span class="num">' + ranks[sk.id] + "</span>"));
      sk.p.forEach(function (p, i) {
        var r = i + 1, own = r <= ranks[sk.id], next = r === ranks[sk.id] + 1;
        var why = next ? whyNot(sk, r) : null;
        var cls = "node" + (own ? " own" : "") + (next ? " next" : "") + (!own && (!next || why) ? " lock" : "");
        var b = el("button", { type: "button", "class": cls, title: (p[2] ? "Also needs " + p[2][0] + " " + p[2][1] + ". " : "") + "Cost " + (r <= 2 ? 1 : 2) },
          "<i>" + r + "</i><span><b>" + esc(p[0]) + "</b>" + esc(p[1]) + "</span>");
        b.addEventListener("click", function () { clickNode(sk, r); });
        t.appendChild(b);
      });
      host.appendChild(t);
    });
    $("#left").textContent = total() - spent();
    var c = function (id) { return ranks[id]; };
    var rows = [
      ["Max health", 100 + 10 * (+$("#lvl").value - 1)],
      ["Points spent", spent() + " / " + total()],
      ["Cover, Rat jacket", c("deception") ? c("deception") + 2 : "no disguise"],
      ["Cover, full outfit", c("deception") ? c("deception") + 4 : "no disguise"],
      ["Fools up to (full outfit)", c("deception") ? "I " + Math.min(5, c("deception") + 4) : "nobody"],
      ["Locks", c("lockpicking") ? "tier " + Math.min(3, [0, 1, 2, 2, 3, 3][c("lockpicking")]) : "keys only"],
      ["Devices", c("hacking") ? "tier " + Math.min(3, [0, 1, 2, 2, 3, 3][c("hacking")]) : "none"],
      ["Dialog checks", "Dec " + c("deception") + " · Per " + c("persuasion")]
    ];
    $("#bsum").innerHTML = rows.map(function (r) { return '<div class="row"><span>' + r[0] + "</span><span>" + r[1] + "</span></div>"; }).join("");
  }
  function clickNode(sk, r) {
    var msg = $("#pmsg");
    if (r === ranks[sk.id] + 1) {
      var why = whyNot(sk, r);
      if (why) { msg.textContent = sk.n + " " + r + ": " + why; return; }
      ranks[sk.id] = r; msg.textContent = "";
    } else if (r === ranks[sk.id]) {
      var floor = sk.id === "deception" ? 1 : 0;
      if (r - 1 < floor) { msg.textContent = "Deception 1 is the runner's trade: it can't be sold."; return; }
      var bl = blocksSell(sk.id, r - 1);
      if (bl) { msg.textContent = "Can't sell " + sk.n + " " + r + ": " + bl; return; }
      ranks[sk.id] = r - 1; msg.textContent = "";
    } else if (r > ranks[sk.id]) { msg.textContent = sk.n + " " + r + ": buy rank " + (ranks[sk.id] + 1) + " first"; return; }
    renderTrees();
  }
  function refit() {
    $("#lvlv").textContent = $("#lvl").value; $("#chipsv").textContent = $("#chips").value;
    while (spent() > total()) {
      var best = null; SKILLS.forEach(function (s) { var fl = s.id === "deception" ? 1 : 0; if (ranks[s.id] > fl && !blocksSell(s.id, ranks[s.id] - 1)) best = s; });
      if (!best) break; ranks[best.id]--;
    }
    renderTrees();
  }
  $("#lvl").addEventListener("input", refit); $("#chips").addEventListener("input", refit);
  $("#resetb").addEventListener("click", function () { ranks = Object.assign({}, START); renderTrees(); $("#pmsg").textContent = "Reset to a new runner: Deception 1."; });
  refit();

  /* ------------------------------------------------------------ XP chart */
  (function () {
    var W = 560, H = 260, L = 58, R = 16, T = 14, B = 34, maxY = 100000;
    var x = function (lv) { return L + (lv - 1) / 19 * (W - L - R); };
    var y = function (v) { return T + (1 - v / maxY) * (H - T - B); };
    var s = '<svg viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="Total XP to reach each level, 1 to 20">';
    s += '<rect x="' + L + '" y="' + y(8000) + '" width="' + (W - L - R) + '" height="' + (y(6000) - y(8000)) + '" fill="#f2b33d" fill-opacity=".14"/>';
    s += '<text x="' + (L + 8) + '" y="' + (y(8000) - 8) + '" text-anchor="start" style="fill:#f2b33d">first slice: 6,000 to 8,000 XP</text>';
    [0, 25000, 50000, 75000, 100000].forEach(function (v) {
      s += '<line class="gl" x1="' + L + '" x2="' + (W - R) + '" y1="' + y(v) + '" y2="' + y(v) + '"/>';
      s += '<text x="' + (L - 8) + '" y="' + (y(v) + 4) + '" text-anchor="end">' + (v / 1000) + "k</text>";
    });
    [1, 5, 10, 15, 20].forEach(function (lv) { s += '<text x="' + x(lv) + '" y="' + (H - 12) + '" text-anchor="middle">' + lv + "</text>"; });
    s += '<line class="ax" x1="' + L + '" x2="' + (W - R) + '" y1="' + y(0) + '" y2="' + y(0) + '"/>';
    var pts = [], bars = "";
    for (var lv = 1; lv <= 20; lv++) {
      var v = 250 * lv * (lv - 1); pts.push(x(lv).toFixed(1) + "," + y(v).toFixed(1));
      bars += '<rect x="' + (x(lv) - 7) + '" y="' + y(v) + '" width="14" height="' + (y(0) - y(v)) + '" fill="#2c3c49"/>';
    }
    s += bars + '<polyline points="' + pts.join(" ") + '" fill="none" stroke="#f2b33d" stroke-width="2"/>';
    s += '<circle cx="' + x(20) + '" cy="' + y(95000) + '" r="4" fill="#f2b33d"/><text x="' + (x(20) - 8) + '" y="' + (y(95000) + 16) + '" text-anchor="end" style="fill:#d9e2e9">95,000 at level 20</text>';
    s += '<text x="12" y="' + (T + 4) + '" text-anchor="start" transform="rotate(-90 12 ' + (T + 4) + ')"> </text></svg>';
    $("#xpchart").innerHTML = s;
  })();

  /* ------------------------------------------------------------ items */
  var ITEMS = [
    ["stun_baton", "Stun baton", "weapon", 1, 3, 1, 120, "melee, 35 stun, non-lethal", "baton"],
    ["combat_knife", "Combat knife", "weapon", 1, 2, 1, 80, "melee, 40 lethal", "knife"],
    ["pistol", "Kestrel 10mm", "weapon", 2, 2, 1, 300, "22 dmg, mag 12, noise 20 m", "pistol"],
    ["whisper", "Whisper 10mm", "weapon", 3, 2, 1, 650, "suppressed: 18 dmg, mag 10, noise 5 m", "smg"],
    ["dart_pistol", "Sandman dart pistol", "weapon", 2, 2, 1, 450, "tranq: sleeps in 4 s, mag 4, noise 3 m", "dart"],
    ["smg", "Rattler SMG", "weapon", 3, 2, 1, 700, "12 dmg, 10/s, mag 30, noise 25 m", "smg"],
    ["shotgun", "Scattergun", "weapon", 4, 2, 1, 800, "9 x 8 dmg, mag 6, noise 30 m", "shotgun"],
    ["ammo_10mm", "10mm rounds", "ammo", 1, 1, 60, 2, "Kestrel, Whisper, Rattler", "ammo"],
    ["ammo_shells", "Shotgun shells", "ammo", 1, 1, 24, 4, "Scattergun", "ammo"],
    ["ammo_darts", "Tranq darts", "ammo", 1, 1, 20, 12, "Sandman", "darts"],
    ["frag_grenade", "Frag grenade", "gadget", 1, 1, 5, 120, "120 blast, 5 m, noise 35 m", "frag"],
    ["emp_grenade", "EMP grenade", "gadget", 1, 1, 5, 150, "robots 20 s, turrets 30 s, cameras 60 s, exo 8 s", "emp"],
    ["gas_grenade", "Knockout gas", "gadget", 1, 1, 5, 140, "KO in 3 s, 4 m, 8 s; respirators immune", "gas"],
    ["noise_maker", "Noise maker", "gadget", 1, 1, 5, 40, "15 m noise after 3 s; lures dogs", "noise"],
    ["lockpick", "Lockpick", "tool", 1, 1, 20, 30, "one lock", "lockpick"],
    ["multitool", "Multitool", "tool", 1, 1, 20, 50, "one hack", "multitool"],
    ["medkit", "Medkit", "consumable", 1, 1, 5, 100, "+40 health over 1 s", "medkit"],
    ["stim", "Stim", "consumable", 1, 1, 5, 70, "+25 health, +20 % speed 10 s", "stim"],
    ["noodles", "Noodle cup", "consumable", 1, 1, 10, 8, "+10 health", "noodles"],
    ["synth_whisky", "Synth-whisky", "consumable", 1, 2, 3, 25, "+5 health, blur 20 s, +1 Persuasion 60 s", "whisky"],
    ["neural_chip", "Neural chip", "consumable", 1, 1, 5, 0, "+1 skill point", "chip"],
    ["street_jacket", "Street jacket", "clothing", 2, 2, 1, 40, "BODY, no faction", "jacket"],
    ["rat_jacket", "Patchwork hood", "clothing", 2, 2, 1, 60, "BODY, Drain Rats, Q 2", "ratjacket"],
    ["rat_goggles", "Scavenger goggles", "clothing", 2, 1, 1, 30, "HEAD, Drain Rats, Q 1; low light", "goggles"],
    ["rat_respirator", "Rat respirator", "clothing", 2, 1, 1, 40, "FACE, Drain Rats, Q 1; gas immunity", "respirator"],
    ["kings_vest", "Kings vest", "clothing", 2, 2, 1, 90, "BODY, Scrap Kings, Q 2", "jacket"],
    ["kings_goggles", "Welder's goggles", "clothing", 2, 1, 1, 35, "HEAD, Scrap Kings, Q 1", "goggles"],
    ["kings_mask", "Welding mask", "clothing", 2, 1, 1, 45, "FACE, Scrap Kings, Q 1; flash immunity", "respirator"],
    ["sanitation_overalls", "Sanitation overalls", "clothing", 2, 2, 1, 30, "BODY, City Sanitation, Q 2", "jacket"],
    ["sanitation_cap", "Sanitation cap", "clothing", 1, 1, 1, 10, "HEAD, City Sanitation, Q 1", "jacket"],
    ["sanitation_mask", "Filter mask", "clothing", 1, 1, 1, 15, "FACE, City Sanitation, Q 1; gas immunity", "respirator"],
    ["kevlar_vest", "Kevlar vest", "armor", 2, 2, 1, 400, "ballistic 30 %, blunt 10 %; clashes", "jacket"],
    ["rat_plates", "Rat plates", "armor", 2, 2, 1, 150, "ballistic 15 %; Drain Rats gear", "jacket"],
    ["soft_soles", "Soft soles", "boots", 2, 1, 1, 200, "footsteps -40 %", "goggles"],
    ["steel_toes", "Steel toes", "boots", 2, 1, 1, 90, "kick +50 %, footsteps +20 %", "goggles"],
    ["silver_lighter", "Silver lighter", "trinket", 1, 1, 1, 250, "+1 Persuasion while carried", "key"],
    ["sewer_service_key", "Sewer service key", "key", 1, 1, 1, 0, "Drains service door", "key"],
    ["pump_room_key", "Pump room key", "key", 1, 1, 1, 0, "hostage cage", "key"],
    ["gang_pass", "Scrap Kings pass", "key", 1, 1, 1, 0, "Yard gate, no questions", "shard"],
    ["nav_core", "Prototype nav core", "quest", 2, 2, 1, 0, "M2 objective", "multitool"],
    ["kings_ledger", "The Kings' ledger", "quest", 1, 2, 1, 0, "S2 objective", "shard"],
    ["mersec_badge", "Dented MerSec badge", "quest", 1, 1, 1, 0, "S3 evidence", "key"],
    ["whisky_crate", "Case of Mags' whisky", "quest", 2, 2, 1, 0, "S4 objective", "whisky"],
    ["credit_chip", "Credit chip", "valuable", 0, 0, 0, 25, "becomes credits on pickup", "chip"],
    ["scrap_electronics", "Scrap electronics", "valuable", 1, 1, 10, 15, "sell", "multitool"],
    ["data_shard", "Data shard", "valuable", 1, 1, 10, 60, "sell to the Oracle; some hold passwords", "shard"]
  ];
  var BY = {}; ITEMS.forEach(function (i) { BY[i[0]] = { id: i[0], name: i[1], cat: i[2], w: i[3], h: i[4], stack: i[5], value: i[6], eff: i[7], ic: i[8] }; });
  var CATS = ["all", "weapon", "ammo", "gadget", "tool", "consumable", "clothing", "armor", "boots", "key", "quest", "valuable"];
  var catSel = "all";
  function renderCat() {
    $("#cat tbody").innerHTML = ITEMS.filter(function (i) { return catSel === "all" || i[2] === catSel || (catSel === "key" && i[2] === "trinket"); }).map(function (i) {
      return "<tr><td><b>" + esc(i[1]) + '</b> <code>' + i[0] + "</code></td><td>" + i[2] + '</td><td class="n">' + (i[3] ? i[3] + "x" + i[4] : "-") + '</td><td class="n">' + (i[5] || "-") + '</td><td class="n">' + i[6] + " cr</td><td>" + esc(i[7]) + "</td></tr>";
    }).join("");
    $$("#catf button").forEach(function (b) { b.classList.toggle("on", b.dataset.c === catSel); });
  }
  CATS.forEach(function (c) { var b = el("button", { type: "button", "data-c": c }, c); b.addEventListener("click", function () { catSel = c; renderCat(); }); $("#catf").appendChild(b); });
  renderCat();

  /* ------------------------------------------------------------ the deck */
  var STATS = {
    stun_baton: [["Damage", "35 stun"], ["Type", "shock"], ["Rate", "1.2 / s"], ["Stagger", "1.5 s"], ["Noise", "3 m"]],
    pistol: [["Damage", "22"], ["Type", "ballistic"], ["Rate", "3 / s"], ["Magazine", "12"], ["Reload", "1.4 s"], ["Spread", "2.0 deg"], ["Noise", "20 m"]],
    dart_pistol: [["Damage", "5 + tranq"], ["Sleep", "4 s (8 s alert)"], ["Magazine", "4"], ["Noise", "3 m"]],
    rat_jacket: [["Slot", "BODY"], ["Faction", "Drain Rats"], ["Disguise", "Q 2"]],
    rat_goggles: [["Slot", "HEAD"], ["Faction", "Drain Rats"], ["Disguise", "Q 1"], ["Vision", "low light"]],
    rat_respirator: [["Slot", "FACE"], ["Faction", "Drain Rats"], ["Disguise", "Q 1"], ["Gas", "immune"]],
    street_jacket: [["Slot", "BODY"], ["Faction", "none"]],
    emp_grenade: [["Robots", "20 s"], ["Turrets", "30 s"], ["Cameras", "60 s"], ["Radius", "6 m"], ["Noise", "12 m"]]
  };
  var PRESETS = {
    start: { cred: 150, lvl: 1, xp: "0 / 500", worn: { BODY: "street_jacket" }, cover: null,
      pack: [["stun_baton", 0, 0, 1], ["pistol", 1, 0, 1], ["ammo_10mm", 3, 0, 24], ["lockpick", 4, 0, 2], ["multitool", 3, 1, 1], ["medkit", 4, 1, 1]],
      belt: ["stun_baton", "pistol", "medkit"], sel: "pistol", on: 2 },
    drains: { cred: 94, lvl: 3, xp: "850 / 1,500", worn: { BODY: "rat_jacket", FACE: "rat_respirator", BOOTS: null }, cover: "DRAIN RATS  Q 3  <em>COVER 5</em> (Deception 2)",
      pack: [["stun_baton", 0, 0, 1], ["pistol", 1, 0, 1], ["ammo_10mm", 3, 0, 36], ["lockpick", 4, 0, 3], ["multitool", 3, 1, 1], ["medkit", 4, 1, 2],
             ["dart_pistol", 1, 2, 1], ["ammo_darts", 3, 2, 9], ["emp_grenade", 4, 2, 2], ["rat_goggles", 5, 0, 1], ["street_jacket", 5, 1, 1], ["noodles", 7, 1, 2],
             ["data_shard", 8, 1, 1], ["synth_whisky", 9, 0, 1], ["sewer_service_key", 0, 3, 1], ["pump_room_key", 0, 4, 1], ["neural_chip", 1, 4, 1]],
      belt: ["stun_baton", "pistol", "dart_pistol", "medkit", "emp_grenade", "lockpick", "multitool"], sel: "rat_respirator", on: 3 }
  };
  var preset = "start";
  function itemDetail(id) {
    var it = BY[id]; if (!it) return;
    var st = STATS[id] || [["Category", it.cat], ["Size", it.w + " x " + it.h], ["Stack", it.stack], ["Effect", it.eff]];
    st = st.concat([["Value", it.value + " cr"]]);
    var acts = it.cat === "weapon" ? ["Draw", "Belt", "Drop"] : (it.cat === "clothing" || it.cat === "armor" || it.cat === "boots") ? ["Wear", "Drop"] : it.cat === "consumable" ? ["Use", "Belt", "Drop"] : ["Drop"];
    $("#detail").innerHTML = '<div class="dh"><div class="ic">' + icon(it.ic, it.w * 48 || 48, it.h * 48 || 48) + '</div><div><h5>' + esc(it.name) + '</h5><div class="cat">' + it.cat + " · " + it.w + " x " + it.h + "</div></div></div>" +
      '<dl class="stats">' + st.map(function (r) { return "<dt>" + r[0] + "</dt><dd>" + esc(r[1]) + "</dd>"; }).join("") + "</dl>" +
      '<div class="acts">' + acts.map(function (a) { return "<span>" + a + "</span>"; }).join("") + "</div>";
  }
  function renderDeck() {
    var P = PRESETS[preset], g = $("#grid"), cell = 44;
    g.innerHTML = "";
    P.pack.forEach(function (p) {
      var it = BY[p[0]];
      var d = el("div", { "class": "item" + (it.cat === "key" || it.cat === "quest" ? " q" : ""), role: "option", tabindex: "0", "aria-label": it.name + (p[3] > 1 ? " x" + p[3] : "") });
      d.style.left = (p[1] * cell + 1) + "px"; d.style.top = (p[2] * cell + 1) + "px";
      d.style.width = (it.w * cell - 1) + "px"; d.style.height = (it.h * cell - 1) + "px";
      d.innerHTML = icon(it.ic, it.w * 48, it.h * 48) + (p[3] > 1 ? '<span class="cnt">' + p[3] + "</span>" : "");
      function pick() { $$(".item", g).forEach(function (x) { x.classList.remove("sel"); }); d.classList.add("sel"); itemDetail(it.id); }
      d.addEventListener("click", pick); d.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(); } });
      if (p[0] === P.sel) d.classList.add("sel");
      g.appendChild(d);
    });
    itemDetail(P.sel);
    $("#slots").innerHTML = ["HEAD", "FACE", "BODY", "ARMOR", "BOOTS"].map(function (s) {
      var w = P.worn[s]; return "<span>" + s + "  <em>" + (w ? esc(BY[w].name) : "-") + "</em></span>";
    }).join("");
    $("#disg").innerHTML = P.cover ? "<span>" + P.cover + "</span><span>at a glance: anyone · up close: up to I 5</span>" : "<span>NOT DISGUISED</span><span>street clothes: no faction</span>";
    var b = $("#belt"); b.innerHTML = "";
    for (var i = 0; i < 10; i++) {
      var id = P.belt[i], it = id && BY[id];
      b.appendChild(el("div", { "class": i === P.on - 1 ? "on" : "" }, "<b>" + ((i + 1) % 10) + "</b>" + (it ? icon(it.ic, it.w * 48, it.h * 48) : "")));
    }
    $("#dcred").textContent = P.cred; $("#dlvl").textContent = P.lvl; $("#dxp").textContent = P.xp;
    $$("#presets button").forEach(function (x) { x.classList.toggle("on", x.dataset.p === preset); });
  }
  $$("#presets button").forEach(function (b) { b.addEventListener("click", function () { preset = b.dataset.p; renderDeck(); }); });
  renderDeck();

  /* ------------------------------------------------------------ locks */
  function lockRule() {
    var kind = $("#lk-kind").value, tier = +$("#lk-tier").value, key = $("#lk-key").checked, code = $("#lk-code").checked;
    var lp = +$("#lk-lp").value, hk = +$("#lk-hk").value, picks = +$("#lk-picks").value, tools = +$("#lk-tools").value;
    var noun = kind === "safe" ? "safe" : "door", o = $("#lk-out");
    function out(cls, big, why) { o.className = "out " + cls; o.innerHTML = '<div class="big">' + big + '</div><div class="why">' + why + "</div>"; }
    if (key) return out("ok", "Unlock " + noun + " (key)", "instant · consumes nothing · 0 XP · noise 5 m");
    if (code) return out("ok", "Enter code (hold 1.0 s)", "consumes nothing · 0 XP · noise 1 m");
    if (lp >= tier && (picks > 0 || lp === 5)) {
      var t = 1.0 * tier * (kind === "safe" ? 2 : 1) * (lp >= 3 ? 0.5 : 1) * (kind === "safe" && lp === 5 ? 0.5 : 1);
      return out("ok", "Pick " + noun + ", tier " + tier + " (hold " + t.toFixed(1) + " s)", (lp === 5 ? "keeps the lockpick" : "uses 1 lockpick on success") + " · " + 20 * tier + " XP · noise 3 m");
    }
    if (hk >= tier && (tools > 0 || hk === 5)) {
      var h = 1.5 * tier * (hk >= 2 ? 0.8 : 1);
      return out("ok", "Hack " + noun + ", tier " + tier + " (hold " + h.toFixed(1) + " s)", (hk === 5 ? "keeps the multitool" : "uses 1 multitool on success") + " · " + 20 * tier + " XP · noise 2 m");
    }
    var needs = ["the key", "the code"];
    needs.push(lp >= tier ? "a lockpick" : "Lockpicking " + tier);
    needs.push(hk >= tier ? "a multitool" : "Hacking " + tier);
    out("bad", "Locked " + noun, "needs " + needs.join(", or "));
  }
  $$("#lockcalc select, #lockcalc input").forEach(function (i) { i.addEventListener("input", lockRule); i.addEventListener("change", lockRule); });
  lockRule();

  /* ------------------------------------------------------------ dialog */
  function renderDialog() {
    var dec = +$("#dg-dec").value, per = +$("#dg-per").value, cr = +$("#dg-cr").value, q = +$("#dg-q").value, log = $("#dg-log").checked;
    var cover = dec + q, ok = cover >= 3;
    var cv = $("#dg-cover"); cv.textContent = "COVER " + cover + " vs I 3"; cv.style.color = ok ? "var(--ok)" : "var(--danger)";
    var ch = [];
    if (!ok) {
      $(".line").textContent = "\"You ain't one of ours!\"";
      ch.push([true, "", "(He goes for his gun.)"]);
    } else {
      $(".line").textContent = "\"Mother said nobody comes down here. So what are you?\"";
      ch.push([dec >= 2, "[Deception 2]", "Mother says let them go. City paid."]);
      ch.push([per >= 3, "[Persuasion 3]", "You look tired. Go get a drink, I'll watch them."]);
      ch.push([cr >= 200, "[200 cr]", "For your trouble."]);
      if (log) ch.push([true, "", "Low tide, high rats. Mother wants you upstairs."]);
      ch.push([true, "", "Nothing. Carry on."]);
    }
    $("#dg-choices").innerHTML = ch.map(function (c, i) {
      return '<li class="' + (c[0] ? "en" : "dis") + '"><i>' + (i + 1) + '.</i><span>' + (c[1] ? '<span class="req">' + c[1] + "</span>" : "") + esc(c[2]) + "</span></li>";
    }).join("");
  }
  ["#dg-dec", "#dg-per", "#dg-cr", "#dg-q", "#dg-log"].forEach(function (s) { $(s).addEventListener("change", renderDialog); });
  renderDialog();

  /* ------------------------------------------------------------ perception */
  var OBS = [
    ["Rat scavenger", "rats", 1, 18], ["Rat gunner", "rats", 2, 22], ["Rat lookout", "rats", 1, 28], ["Twitch", "rats", 3, 22],
    ["Hatchet", "rats", 3, 20], ["Mother Rat", "rats", 4, 24], ["Kings mechanic", "kings", 2, 22], ["Kings foreman", "kings", 3, 26],
    ["Bruiser", "kings", 2, 20], ["Crusher", "kings", 5, 26], ["Robot dog", "kings", -1, 16], ["Camera", "kings", -1, 14]
  ];
  OBS.forEach(function (o, i) {
    var lbl = o[0] + (o[2] > 0 ? " (I " + o[2] + ")" : " (sensor)");
    $("#d-obs").appendChild(el("option", { value: i }, lbl));
    $("#v-obs").appendChild(el("option", { value: i }, o[0] + " (" + o[3] + " m)"));
  });
  $("#d-obs").value = "5"; $("#v-obs").value = "1";
  function verdict() {
    var fac = $("#d-fac").value, head = $("#d-head").checked, face = $("#d-face").checked, dec = +$("#d-dec").value;
    var o = OBS[+$("#d-obs").value], dist = +$("#d-dist").value, talk = $("#d-talk").checked;
    var arm = $("#d-arm").value, wpn = +$("#d-wpn").value, move = $("#d-move").value, zone = $("#d-zone").checked;
    $("#d-distv").textContent = dist + " m";
    var out = $("#d-out");
    function show(cls, big, lines) { out.className = "out " + cls; out.innerHTML = '<div class="big">' + big + "</div>" + lines.map(function (l) { return '<div class="why">' + l + "</div>"; }).join(""); }
    if (o[2] < 0) return show("bad", "Can't be fooled", [o[0] + " uses " + (o[0] === "Camera" ? "sensors" : "scent (8 m, through walls)") + ": hack, EMP or avoid it"]);
    if (fac === "none" || fac !== o[1]) return show("nd", "Not disguised", ["Not wearing " + (o[1] === "rats" ? "Drain Rats" : "Scrap Kings") + " colours: normal stealth rules"]);
    if (dec === 0) return show("nd", "Not disguised", ["Deception 0: you wear it like a costume"]);
    var Q = 2 + (head ? 1 : 0) + (face ? 1 : 0), cover = dec + Q, I = o[2];
    var S = (2 + 2 * I) * (dec >= 5 ? 0.5 : 1), close = talk || dist <= S, grace = dec >= 3 ? 2 : 0;
    var info = "Q " + Q + " · Cover " + cover + " vs I " + I + " · scrutiny " + S + " m" + (talk ? " · talking" : dist <= S ? " · inside" : " · outside");
    if (wpn > grace) return show("bad", "Blown", ["Weapon drawn " + wpn + " s, grace " + grace + " s" + (dec >= 3 ? " (Master of Disguise)" : ""), info]);
    if (close && cover < I) {
      var ft = dec >= 2 ? "Fast Talk: one retry, Cover + 1 = " + (cover + 1) + (cover + 1 >= I ? " passes: back to Suspicious" : " still short") : "Deception 2 adds Fast Talk: one retry";
      return show("bad", "Blown", ["Cover " + cover + " < I " + I + (talk ? " when talking" : " inside " + S + " m"), info, ft]);
    }
    var sus = [];
    if (zone) sus.push("restricted zone: 3 s warning, then Blown");
    if (arm === "kevlar") sus.push("foreign armour (kevlar)");
    if (move === "sneak" && close) sus.push("creeping or sprinting inside " + S + " m");
    if (sus.length) return show("warn", "Suspicious", sus.concat(["fills at 0.35/s x V" + (dec >= 4 ? " x 0.75 (Silver Tongue)" : ""), info]));
    show("ok", "Accepted", [close ? "Cover " + cover + " >= I " + I : "Outside scrutiny range: passes at a glance", info]);
  }
  $$("#perception .calc:first-child select, #perception .calc:first-child input").forEach(function (i) { i.addEventListener("input", verdict); i.addEventListener("change", verdict); });
  verdict();
  function detect() {
    var o = OBS[+$("#v-obs").value], light = +$("#v-light").value / 100, d = +$("#v-dist").value;
    var stance = +$("#v-stance").value, motion = +$("#v-move").value, cone = +$("#v-cone").value, shadow = $("#v-shadow").checked;
    $("#v-lightv").textContent = light.toFixed(2); $("#v-distv").textContent = d + " m";
    var V = light * stance * motion * (shadow && light < 0.25 ? 0.5 : 1);
    var rate = V * 1.2 * Math.max(0, 1 - d / o[3]) * cone, out = $("#v-out");
    if (rate <= 0) { out.className = "out ok"; out.innerHTML = '<div class="big">Never</div><div class="why">' + d + " m is beyond " + o[0] + "'s " + o[3] + " m range, or the light is 0</div>"; $("#v-fill").style.width = "0"; return; }
    var ts = 0.3 / rate, ta = 1 / rate;
    out.className = "out " + (ta < 3 ? "bad" : ta < 8 ? "warn" : "ok");
    out.innerHTML = '<div class="big">Alerted in ' + (ta > 99 ? ">99" : ta.toFixed(1)) + " s</div><div class=\"why\">V " + V.toFixed(2) + " · D +" + rate.toFixed(3) + "/s · Suspicious at " + ts.toFixed(1) + " s</div>";
    var m = $("#v-meter"); $$("i", m).forEach(function (x) { x.remove(); });
    [[ts, "var(--tech)"], [ta, "var(--danger)"]].forEach(function (p) { if (p[0] <= 10) { var i = el("i"); i.style.left = (p[0] * 10) + "%"; i.style.background = p[1]; m.appendChild(i); } });
    $("#v-fill").style.width = Math.min(100, ta * 10) + "%";
  }
  $$("#perception .calc:nth-child(2) select, #perception .calc:nth-child(2) input").forEach(function (i) { i.addEventListener("input", detect); i.addEventListener("change", detect); });
  detect();
  var NOISE = [["Crouch walk", 1], ["Hacking", 2], ["Lockpicking", 3], ["Dart pistol", 3], ["Walk", 4], ["Whisper 10mm", 5], ["Door", 5], ["Body drop", 5],
               ["Takedown", 6], ["Landing 2 m+", 6], ["Wading", 8], ["Sprint", 10], ["EMP grenade", 12], ["Glass, a lamp", 12], ["Noise maker", 15],
               ["Can rattle", 18], ["Kestrel 10mm", 20], ["Rattler SMG", 25], ["Scattergun", 30], ["Frag grenade", 35]];
  $("#noise").innerHTML = NOISE.map(function (n) {
    var c = n[1] >= 20 ? "var(--danger)" : n[1] >= 10 ? "var(--tech)" : "var(--dim)";
    return '<div class="hb"><span>' + n[0] + '</span><div><i style="width:' + (n[1] / 35 * 100) + "%;--c:" + c + '"></i></div><em>' + n[1] + " m</em></div>";
  }).join("");

  /* ------------------------------------------------------------ combat */
  var ARCH = [
    ["Rat scavenger", "Drain Rats", 60, "-", 1, "Flees at 25 % to warn the others.", ["takedown", "darts", "disguise", "Intimidate: drops his weapon"]],
    ["Rat gunner", "Drain Rats", 70, "ballistic 10 %", 2, "Respirator: immune to gas.", ["takedown", "darts", "disguise", "turn the scrap turret on them"]],
    ["Rat lookout", "Drain Rats", 50, "-", "1-2", "Whistle raises the alarm in 30 m.", ["stay out of his 28 m cone", "darts from range", "noise maker to turn him"]],
    ["Twitch", "Drain Rats", 90, "ballistic 10 %", 3, "Executes a hostage 8 s after he's Alerted.", ["silent takedown from the vent", "[Deception 2] at Cover 3", "200 cr"]],
    ["Hatchet", "Drain Rats", 140, "ballistic 20 %, blunt 30 %", 3, "Heavy: no takedown without Melee 4.", ["darts (8 s)", "gas via the nest vents (Hacking 2)", "go around"]],
    ["Mother Rat", "Drain Rats", 160, "ballistic 20 %", 4, "Throws gas; her crew is immune, you aren't.", ["wear a respirator", "talk at Cover 5", "parley", "500 cr"]],
    ["Kings mechanic", "Scrap Kings", 80, "ballistic 15 %", 2, "Repairs turrets and dogs in 20 s.", ["gas (no respirators)", "takedown", "disguise"]],
    ["Kings foreman", "Scrap Kings", 110, "ballistic 25 %", 3, "Radio: alarm in 2 s.", ["take him first", "EMP kills the radio 20 s", "lure him to the generator"]],
    ["Bruiser", "Scrap Kings", 180, "ballistic 40 %", 2, "Exo-arm charge, 12 m; hits walls.", ["EMP: armour 0 for 8 s", "sidestep into a wall", "gas"]],
    ["Robot dog", "Scrap Kings", 90, "ballistic 50 %, EMP x3", "-", "Scent 8 m through walls; ignores disguises.", ["EMP 20 s", "noise maker lure", "kennel hack keeps it docked", "climb"]],
    ["Turret", "any", 150, "ballistic 70 %", "-", "120 deg arc; wakes on the alarm.", ["hack: disable at 2, turn at 3", "EMP 30 s", "flank", "power off"]],
    ["Crusher", "Scrap Kings", 260, "ballistic 40 %, blunt 50 %", 5, "Plated arm blocks frontal fire; no takedowns.", ["EMP the arm", "talk: Cover 6 + [Deception 4]", "expose Jax", "thinner in his whisky"]],
    ["MerSec trooper", "MerSec", 120, "ballistic 35 %", "2-3", "Warns once in the hub; backup in 60 s.", ["keep weapons holstered", "bribe", "don't start it"]]
  ];
  $("#arch").innerHTML = ARCH.map(function (a) {
    return '<article class="card"><header><h4>' + a[0] + '</h4><span class="fac">' + a[1] + '</span></header><div class="st"><span>HP <b>' + a[2] + "</b></span><span>I <b>" + a[4] + "</b></span><span>" + a[3] + "</span></div><p>" + a[5] + "</p><ul>" + a[6].map(function (c) { return "<li>" + esc(c) + "</li>"; }).join("") + "</ul></article>";
  }).join("");
  var WPN = [["Stun baton", "35 stun", "shock", "1.2/s", "-", "3 m", "non-lethal, 1.5 s stagger"], ["Combat knife", "40", "lethal", "1.6/s", "-", "2 m", ""],
             ["Kestrel 10mm", "22", "ballistic", "3/s", "12", "20 m", "reload 1.4 s"], ["Whisper 10mm", "18", "ballistic", "2.5/s", "10", "5 m", "suppressed"],
             ["Sandman", "5 + tranq", "tranq", "1/s", "4", "3 m", "sleep in 4 s (8 s alert)"], ["Rattler SMG", "12", "ballistic", "10/s", "30", "25 m", "spread 4.5 deg"],
             ["Scattergun", "9 x 8", "ballistic", "1.1/s", "6", "30 m", "reload per shell"], ["Frag grenade", "120", "explosive", "-", "-", "35 m", "5 m radius"],
             ["EMP grenade", "-", "EMP", "-", "-", "12 m", "6 m radius"], ["Knockout gas", "-", "gas", "-", "-", "6 m", "4 m cloud, 8 s"], ["Noise maker", "-", "-", "-", "-", "15 m", "3 s delay, lures"]];
  $("#wpn tbody").innerHTML = WPN.map(function (w) { return "<tr><td><b>" + w[0] + '</b></td><td class="n">' + w[1] + "</td><td>" + w[2] + '</td><td class="n">' + w[3] + '</td><td class="n">' + w[4] + '</td><td class="n">' + w[5] + "</td><td>" + w[6] + "</td></tr>"; }).join("");

  /* ------------------------------------------------------------ rail */
  var links = $$(".rail a"), secs = links.map(function (a) { return $(a.getAttribute("href")); });
  function spy() {
    var y = window.scrollY + 120, cur = 0;
    secs.forEach(function (s, i) { if (s && s.offsetTop <= y) cur = i; });
    links.forEach(function (a, i) { a.classList.toggle("on", i === cur); });
  }
  window.addEventListener("scroll", spy, { passive: true }); spy();
})();
