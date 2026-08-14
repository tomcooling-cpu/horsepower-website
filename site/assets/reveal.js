/* WS-SITE20 scroll-reveal. Progressive enhancement, no dependencies.

   The `js` class is set on <html> in the head, and every hidden-start state in
   the CSS is gated behind `html.js ...:not(.in)`. So with JS disabled, or before
   this file runs, nothing matches the hidden rule and ALL content is fully
   visible. Content never depends on JS to appear.

   This script only ADDS the `in` class to elements as they enter the viewport;
   the CSS does the fade + settle. It never writes text or numbers into the DOM.
   prefers-reduced-motion: everything is marked `in` immediately (CSS also forces
   the static, motion-free state), so there is no animation at all. */
(function () {
  "use strict";

  // The single source of truth for what reveals. Kept in step with style.css
  // (the same selector list carries the hidden-start state).
  var SELECTOR = [
    ".reveal",
    "section > .wrap > .eyebrow",
    "section > .wrap > h2",
    "section > .wrap > .section-intro",
    ".tier-card", ".which-item", ".plan-card", ".honour", ".blog-card",
    ".get-card", ".cred", ".quote-card", ".photo-fig", ".spec-box",
    ".feature-media", ".feature-copy", ".result-stats", ".raceplan",
    ".carousel", ".about-list li", ".step-list li"
  ].join(",");

  var els = document.querySelectorAll(SELECTOR);
  if (!els.length) return;
  var list = Array.prototype.slice.call(els);

  var reduce = window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  if (reduce || !("IntersectionObserver" in window)) {
    list.forEach(function (el) { el.classList.add("in"); });
    return;
  }

  function revealInView() {
    var vh = window.innerHeight || document.documentElement.clientHeight;
    list.forEach(function (el) {
      if (el.classList.contains("in")) return;
      var r = el.getBoundingClientRect();
      if (r.top < vh && r.bottom > 0) el.classList.add("in");
    });
  }

  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) {
        e.target.classList.add("in");
        io.unobserve(e.target);
      }
    });
  }, { rootMargin: "0px 0px -8% 0px", threshold: 0.1 });

  list.forEach(function (el) {
    // Anything already in view (or above the fold) reveals on the first tick.
    io.observe(el);
  });

  // Immediate above-the-fold pass, independent of the observer's first async
  // callback, so the opening screenful is never left waiting on Intersection
  // Observer timing. Runs on the next frame after layout.
  if (window.requestAnimationFrame) {
    window.requestAnimationFrame(revealInView);
  } else {
    revealInView();
  }

  // Safety nets: on load (settle) and on scroll, reveal anything now in view so
  // content can never get stuck invisible (e.g. an element that was display:none
  // when first observed, then shown).
  window.addEventListener("load", function () { window.setTimeout(revealInView, 120); });
  window.addEventListener("scroll", revealInView, { passive: true });
})();
