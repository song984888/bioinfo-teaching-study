(function () {
  "use strict";

  var BASES = ["A", "C", "G", "T"];
  var COMP = { A: "T", T: "A", C: "G", G: "C" };
  var COLOR = { A: "#4ade80", C: "#60a5fa", G: "#facc15", T: "#f87171" };
  var TXT = { A: "#052e16", C: "#172554", G: "#422006", T: "#450a0a" };

  var state = { level: 1, score: 0, best: 0, ref: "", reads: [], readIdx: 0, pos: 0, flipped: false, cell: 24, busy: false };
  try { state.best = parseInt(localStorage.getItem("alignomatic_best") || "0", 10) || 0; } catch (e) {}

  function rnd(n) { return Math.floor(Math.random() * n); }
  function randBase() { return BASES[rnd(4)]; }
  function revComp(s) { var o = ""; for (var i = s.length - 1; i >= 0; i--) o += COMP[s[i]]; return o; }
  function clampPos(p, len) {
    var min = -(len - 2), max = state.ref.length - 2;
    return Math.max(min, Math.min(max, p));
  }

  var audioCtx = null;
  function beep(freq, dur, type) {
    try {
      audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
      var o = audioCtx.createOscillator(), g = audioCtx.createGain();
      o.type = type || "sine"; o.frequency.value = freq;
      g.gain.value = 0.05;
      g.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + dur);
      o.connect(g); g.connect(audioCtx.destination);
      o.start(); o.stop(audioCtx.currentTime + dur);
    } catch (e) {}
  }

  // ---- level generation ----
  function genLevel(lv) {
    var refLen = Math.min(22 + lv * 3, 48);
    var ref = "";
    for (var i = 0; i < refLen; i++) ref += randBase();
    var nReads = Math.min(2 + lv, 6);
    var reads = [], allowFlip = lv >= 3;
    for (var r = 0; r < nReads; r++) {
      var len = Math.min(7 + rnd(5), refLen - 4);
      var truePos = rnd(refLen - len + 1);
      var arr = ref.slice(truePos, truePos + len).split("");
      var muts = Math.min(1 + Math.floor(lv / 2), 3);
      for (var m = 0; m < muts; m++) {
        var p = rnd(arr.length);
        var alt = BASES.filter(function (b) { return b !== arr[p]; });
        arr[p] = alt[rnd(alt.length)];
      }
      reads.push({ seq: arr.join(""), startFlipped: allowFlip && Math.random() < 0.4 });
    }
    state.ref = ref;
    state.reads = reads;
    state.readIdx = 0;
  }

  function currentSeq() {
    var s = state.reads[state.readIdx].seq;
    return state.flipped ? revComp(s) : s;
  }
  function scoreAt(seq, pos) {
    var sc = 0;
    for (var i = 0; i < seq.length; i++) {
      var j = pos + i;
      if (j < 0 || j >= state.ref.length) { sc -= 5; continue; }
      sc += (state.ref[j] === seq[i]) ? 10 : -5;
    }
    return sc;
  }
  function bestPossible(seq) {
    var best = -Infinity;
    for (var p = 0; p <= state.ref.length - seq.length; p++) {
      best = Math.max(best, scoreAt(seq, p), scoreAt(revComp(seq), p));
    }
    return best;
  }

  // ---- DOM ----
  var $ = function (id) { return document.getElementById(id); };
  var elRef = $("refRow"), elLane = $("readLane"), elWrap = $("readWrap"),
      elMatch = $("matchRow"), elPreview = $("preview"), elFlipTag = $("flipTag"),
      elToast = $("toast"), elModal = $("modal"), elModalBox = $("modalBox");

  function setCellSize() {
    var avail = Math.min(window.innerWidth * 0.96, 900) - 60;
    var c = Math.floor(avail / state.ref.length) - 2;
    state.cell = Math.max(14, Math.min(c, 30));
    document.documentElement.style.setProperty("--cell", state.cell + "px");
    var w = state.ref.length * (state.cell + 2) + "px";
    elLane.style.width = w; elRef.style.width = w; elMatch.style.width = w;
  }

  function renderRef() {
    elRef.innerHTML = "";
    for (var i = 0; i < state.ref.length; i++) {
      var d = document.createElement("div");
      d.className = "cell refcell";
      d.textContent = state.ref[i];
      d.style.color = COLOR[state.ref[i]];
      elRef.appendChild(d);
    }
  }

  function renderRead() {
    var seq = currentSeq();
    elWrap.innerHTML = "";
    for (var i = 0; i < seq.length; i++) {
      var d = document.createElement("div");
      d.className = "cell readcell";
      d.textContent = seq[i];
      d.style.background = COLOR[seq[i]];
      d.style.color = TXT[seq[i]];
      elWrap.appendChild(d);
    }
    elFlipTag.textContent = state.flipped ? "(reverse complement)" : "";
    positionRead();
    renderMatches();
  }

  function positionRead() {
    elWrap.style.transform = "translateX(" + (state.pos * (state.cell + 2)) + "px)";
  }

  function renderMatches() {
    var seq = currentSeq();
    var marks = [];
    for (var i = 0; i < state.ref.length; i++) marks.push("");
    for (var k = 0; k < seq.length; k++) {
      var j = state.pos + k;
      if (j >= 0 && j < state.ref.length) marks[j] = (state.ref[j] === seq[k]) ? "yes" : "no";
    }
    elMatch.innerHTML = "";
    for (var m = 0; m < marks.length; m++) {
      var d = document.createElement("div");
      d.className = "matchmark " + marks[m];
      d.textContent = marks[m] === "yes" ? "\u2713" : (marks[m] === "no" ? "\u2717" : "");
      elMatch.appendChild(d);
    }
    var sc = scoreAt(seq, state.pos);
    elPreview.innerHTML = "current alignment: <b>" + sc + "</b> pts";
  }

  function updateHud() {
    $("hudLevel").textContent = state.level;
    $("hudRead").textContent = (state.readIdx + 1) + "/" + state.reads.length;
    $("hudScore").textContent = state.score;
    $("hudBest").textContent = state.best;
  }

  var toastTimer = null;
  function toast(msg, ms) {
    elToast.textContent = msg;
    elToast.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { elToast.classList.remove("show"); }, ms || 1600);
  }

  // ---- actions ----
  function nudge(d) {
    if (state.busy) return;
    state.pos = clampPos(state.pos + d, currentSeq().length);
    positionRead();
    renderMatches();
  }

  function flipRead() {
    if (state.busy) return;
    if (state.level < 3) { toast("reverse-complement reads appear from level 3"); return; }
    state.flipped = !state.flipped;
    state.pos = clampPos(state.pos, currentSeq().length);
    renderRead();
    beep(state.flipped ? 330 : 440, 0.08, "triangle");
  }

  function resetRead() {
    if (state.busy) return;
    loadReadPosition();
    renderRead();
  }

  function loadReadPosition() {
    var rd = state.reads[state.readIdx];
    state.flipped = rd.startFlipped;
    var len = currentSeq().length;
    state.pos = clampPos(Math.floor((state.ref.length - len) / 2), len);
  }

  function confirmAlignment() {
    if (state.busy) return;
    var seq = currentSeq();
    var gained = scoreAt(seq, state.pos);
    var best = bestPossible(seq);
    state.score += gained;
    if (state.score > state.best) {
      state.best = state.score;
      try { localStorage.setItem("alignomatic_best", String(state.best)); } catch (e) {}
    }
    updateHud();

    var perfect = gained >= best;
    elWrap.classList.remove("locked");
    void elWrap.offsetWidth;
    elWrap.classList.add("locked");
    state.busy = true;
    beep(perfect ? 660 : 392, 0.12);
    if (perfect) setTimeout(function () { beep(880, 0.15); }, 120);
    toast((perfect ? "\u2728 optimal alignment! " : "aligned ") + "+" + gained + " pts", 1500);

    setTimeout(function () {
      state.busy = false;
      state.readIdx++;
      if (state.readIdx >= state.reads.length) {
        showLevelComplete();
      } else {
        loadReadPosition();
        renderRead();
        updateHud();
      }
    }, 900);
  }

  function showLevelComplete() {
    var stars = state.level >= 5 ? 3 : (state.level >= 2 ? 2 : 1);
    var starStr = "";
    for (var i = 0; i < 3; i++) starStr += i < stars ? "\u2605" : "\u2606";
    elModalBox.innerHTML =
      "<h2>Level " + state.level + " assembled!</h2>" +
      "<div class=\"stars\">" + starStr + "</div>" +
      "<p>total score: <b style=\"color:var(--gold)\">" + state.score + "</b></p>" +
      "<p>next: longer reference, " + Math.min(3 + state.level, 6) + " reads" +
      (state.level + 1 >= 3 ? ", watch for reverse-complement reads" : "") + "</p>" +
      "<button class=\"primary\" id=\"btnNext\">next level &#9654;</button>" +
      "<button id=\"btnRestart\">restart</button>";
    elModal.classList.add("show");
    $("btnNext").onclick = function () {
      elModal.classList.remove("show");
      state.level++;
      startLevel();
    };
    $("btnRestart").onclick = function () {
      elModal.classList.remove("show");
      state.level = 1; state.score = 0;
      startLevel();
    };
    beep(523, 0.15); setTimeout(function () { beep(659, 0.15); }, 150);
    setTimeout(function () { beep(784, 0.25); }, 300);
  }

  function startLevel() {
    genLevel(state.level);
    setCellSize();
    renderRef();
    loadReadPosition();
    renderRead();
    updateHud();
  }

  // ---- drag ----
  var drag = null;
  elWrap.addEventListener("pointerdown", function (e) {
    if (state.busy) return;
    drag = { startX: e.clientX, startPos: state.pos };
    elWrap.setPointerCapture(e.pointerId);
    elWrap.classList.add("dragging");
    e.preventDefault();
  });
  elWrap.addEventListener("pointermove", function (e) {
    if (!drag) return;
    var dx = e.clientX - drag.startX;
    var cellStep = state.cell + 2;
    state.pos = clampPos(drag.startPos + Math.round(dx / cellStep), currentSeq().length);
    positionRead();
    renderMatches();
  });
  function endDrag() { drag = null; elWrap.classList.remove("dragging"); }
  elWrap.addEventListener("pointerup", endDrag);
  elWrap.addEventListener("pointercancel", endDrag);

  // ---- buttons & keys ----
  $("btnLeft").onclick = function () { nudge(-1); };
  $("btnRight").onclick = function () { nudge(1); };
  $("btnFlip").onclick = flipRead;
  $("btnReset").onclick = resetRead;
  $("btnCommit").onclick = confirmAlignment;

  document.addEventListener("keydown", function (e) {
    if (elModal.classList.contains("show")) return;
    if (e.key === "ArrowLeft") { nudge(-1); e.preventDefault(); }
    else if (e.key === "ArrowRight") { nudge(1); e.preventDefault(); }
    else if (e.key === "f" || e.key === "F") flipRead();
    else if (e.key === "Enter") confirmAlignment();
    else if (e.key === "r" || e.key === "R") resetRead();
  });

  window.addEventListener("resize", function () {
    setCellSize();
    positionRead();
  });

  startLevel();
})();
