/* Plan library filtering. Cards are rendered server-side (all visible with no JS);
   this only shows/hides them by the filter controls. No framework, no build step. */
(function () {
  "use strict";
  var grid = document.getElementById("plan-grid");
  if (!grid) return;
  var cards = Array.prototype.slice.call(grid.querySelectorAll(".plan-card"));
  var fSport = document.getElementById("f-sport");
  var fCat = document.getElementById("f-category");
  var fTier = document.getElementById("f-tier");
  var fWeeks = document.getElementById("f-weeks");
  var fHours = document.getElementById("f-hours");
  var fSearch = document.getElementById("f-search");
  var count = document.getElementById("result-count");
  var empty = document.getElementById("no-results");

  function weekBucket(w) {
    if (w <= 12) return "short";
    if (w <= 18) return "mid";
    return "long";
  }
  function hourBucket(h) {
    if (h < 7) return "low";
    if (h <= 11) return "mid";
    return "high";
  }

  function apply() {
    var s = fSport.value, c = fCat.value, t = fTier.value,
        w = fWeeks.value, h = fHours.value,
        q = (fSearch.value || "").trim().toLowerCase();
    var shown = 0;
    cards.forEach(function (card) {
      var ok = true;
      if (s && card.dataset.sport !== s) ok = false;
      if (c && card.dataset.category !== c) ok = false;
      if (t && card.dataset.tier !== t) ok = false;
      if (w && weekBucket(parseInt(card.dataset.weeks, 10)) !== w) ok = false;
      if (h && hourBucket(parseFloat(card.dataset.hours)) !== h) ok = false;
      if (q && card.dataset.title.indexOf(q) === -1) ok = false;
      card.style.display = ok ? "" : "none";
      if (ok) shown++;
    });
    if (count) count.textContent = String(shown);
    if (empty) empty.style.display = shown ? "none" : "block";
  }

  [fSport, fCat, fTier, fWeeks, fHours].forEach(function (el) {
    if (el) el.addEventListener("change", apply);
  });
  if (fSearch) fSearch.addEventListener("input", apply);
  apply();
})();
