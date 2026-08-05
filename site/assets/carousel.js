/* Review carousels. Accessible, dependency-free. Auto-advance ~6s, manual
   arrows + dots, pause on hover/focus, respects prefers-reduced-motion.
   Slides are rendered server-side and fully readable with no JS (the track just
   wraps and the arrows/dots are inert until this upgrades it). */
(function () {
  "use strict";
  var INTERVAL = 6000;
  var reduce = window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function setup(root) {
    var track = root.querySelector(".carousel-track");
    var slides = Array.prototype.slice.call(root.querySelectorAll(".carousel-slide"));
    var dots = Array.prototype.slice.call(root.querySelectorAll(".carousel-dot"));
    var prev = root.querySelector(".carousel-arrow.prev");
    var next = root.querySelector(".carousel-arrow.next");
    if (!track || slides.length <= 1) {
      if (prev) prev.style.display = "none";
      if (next) next.style.display = "none";
      root.classList.add("is-ready");
      return;
    }
    var i = 0, timer = null, paused = false;

    function render() {
      track.style.transform = "translateX(" + (-i * 100) + "%)";
      slides.forEach(function (s, n) {
        s.setAttribute("aria-hidden", n === i ? "false" : "true");
      });
      dots.forEach(function (d, n) {
        var on = n === i;
        d.setAttribute("aria-selected", on ? "true" : "false");
        d.classList.toggle("is-active", on);
        d.tabIndex = on ? 0 : -1;
      });
    }
    function go(n) { i = (n + slides.length) % slides.length; render(); }
    function advance() { if (!paused) go(i + 1); }

    function start() {
      if (reduce || timer) return;
      timer = window.setInterval(advance, INTERVAL);
    }
    function stop() { if (timer) { window.clearInterval(timer); timer = null; } }

    if (prev) prev.addEventListener("click", function () { go(i - 1); });
    if (next) next.addEventListener("click", function () { go(i + 1); });
    dots.forEach(function (d) {
      d.addEventListener("click", function () { go(parseInt(d.dataset.i, 10)); });
    });

    root.addEventListener("mouseenter", function () { paused = true; });
    root.addEventListener("mouseleave", function () { paused = false; });
    root.addEventListener("focusin", function () { paused = true; });
    root.addEventListener("focusout", function () { paused = false; });
    root.addEventListener("keydown", function (e) {
      if (e.key === "ArrowLeft") { go(i - 1); e.preventDefault(); }
      else if (e.key === "ArrowRight") { go(i + 1); e.preventDefault(); }
    });

    render();
    root.classList.add("is-ready");
    start();
  }

  var roots = document.querySelectorAll("[data-carousel]");
  Array.prototype.forEach.call(roots, setup);
})();
