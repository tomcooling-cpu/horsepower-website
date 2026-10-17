/* WS-SITE25 consent banner and GA4 boot (basic Consent Mode v2).
   Nothing is requested from Google until the visitor clicks Accept. The choice
   lives in localStorage.hp_consent (strictly necessary). The measurement ID and
   page parameters come from the <html> data attributes the live build emits; the
   preview build emits no ID, so this file then only manages the banner. */
(function () {
  "use strict";
  var KEY = "hp_consent";
  var root = document.documentElement;
  var banner = document.getElementById("cookie-banner");
  if (!banner) return;
  var ID = root.getAttribute("data-ga4") || "";
  var PAGE_TYPE = root.getAttribute("data-page-type") || "page";
  var SPORT = root.getAttribute("data-sport") || "";
  var TIER = root.getAttribute("data-tier") || "";
  var ttlDays = parseInt(banner.getAttribute("data-consent-ttl"), 10) || 183;
  var acceptBtn = banner.querySelector('[data-consent="accept"]');
  var rejectBtn = banner.querySelector('[data-consent="reject"]');
  var title = document.getElementById("consent-title");
  var booted = false;
  var returnFocus = null;

  function readChoice() {
    try {
      var rec = JSON.parse(window.localStorage.getItem(KEY) || "null");
      if (!rec || rec.v !== 1 || (rec.choice !== "accept" && rec.choice !== "reject")) return null;
      if (typeof rec.ts !== "number" || Date.now() - rec.ts > ttlDays * 864e5) return null;
      return rec.choice;
    } catch (e) {
      return null;
    }
  }

  function storeChoice(choice) {
    try {
      window.localStorage.setItem(KEY, JSON.stringify({ v: 1, choice: choice, ts: Date.now() }));
    } catch (e) { /* storage blocked: the choice applies to this page only */ }
  }

  function boot() {
    if (booted || !ID || typeof window.gtag !== "function") return;
    booted = true;
    window.__hpGaRevoked = false;
    window["ga-disable-" + ID] = false;
    gtag('consent','update',{'analytics_storage':'granted','ad_storage':'granted','ad_user_data':'granted','ad_personalization':'denied'});
    gtag('js', new Date());
    var cfg = { send_page_view: true, content_group: PAGE_TYPE, page_type: PAGE_TYPE };
    if (SPORT) cfg.sport = SPORT;
    if (TIER) cfg.tier = TIER;
    var debug = false;
    try { debug = window.sessionStorage.getItem("hp_ga_debug") === "1"; } catch (e) { debug = false; }
    if (debug) cfg.debug_mode = true;
    gtag('config', ID, cfg);
    var s = document.createElement("script");
    s.async = true;
    s.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(ID);
    document.head.appendChild(s);
    window.__hpGaReady = true;
    document.dispatchEvent(new CustomEvent("hp:ga-ready"));
  }

  function expireCookie(name, domain) {
    document.cookie = name + "=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/" +
      (domain ? "; domain=" + domain : "");
  }

  function revoke() {
    window.__hpGaReady = false;
    window.__hpGaRevoked = true;
    // GA's own opt-out flag: an already-loaded gtag.js sends nothing more.
    if (ID) window["ga-disable-" + ID] = true;
    if (typeof window.gtag === "function") {
      gtag('consent','update',{'analytics_storage':'denied','ad_storage':'denied','ad_user_data':'denied','ad_personalization':'denied'});
    }
    document.dispatchEvent(new CustomEvent("hp:ga-revoked"));
    var names = [];
    document.cookie.split(";").forEach(function (c) {
      var n = c.split("=")[0].trim();
      if (n === "_ga" || n.indexOf("_ga_") === 0) names.push(n);
    });
    if (ID) names.push("_ga", "_ga_" + ID.replace(/^G-/, ""));
    var host = location.hostname;
    names.forEach(function (n) {
      expireCookie(n, "");
      expireCookie(n, host);
      expireCookie(n, "." + host);
      expireCookie(n, ".horsepowercoaching.co.uk");
    });
  }

  function syncPadding() {
    document.body.style.paddingBottom = banner.hidden ? "" : banner.offsetHeight + "px";
  }

  function reflect(choice) {
    acceptBtn.setAttribute("aria-pressed", choice === "accept" ? "true" : "false");
    rejectBtn.setAttribute("aria-pressed", choice === "reject" ? "true" : "false");
  }

  function show(fromSettings) {
    var current = readChoice();
    if (current) reflect(current);
    else { acceptBtn.removeAttribute("aria-pressed"); rejectBtn.removeAttribute("aria-pressed"); }
    banner.hidden = false;
    syncPadding();
    if (fromSettings && title) title.focus();
  }

  function hide() {
    banner.hidden = true;
    syncPadding();
    if (returnFocus) { returnFocus.focus(); returnFocus = null; }
  }

  function choose(choice) {
    var previous = readChoice();
    storeChoice(choice);
    if (choice === "accept") boot();
    else if (previous === "accept" || booted) { revoke(); booted = false; }
    hide();
  }

  acceptBtn.addEventListener("click", function () { choose("accept"); });
  rejectBtn.addEventListener("click", function () { choose("reject"); });
  document.addEventListener("click", function (e) {
    var link = e.target.closest && e.target.closest(".consent-open");
    if (!link) return;
    e.preventDefault();
    returnFocus = link;
    show(true);
  });
  window.addEventListener("resize", syncPadding);
  window.addEventListener("load", syncPadding);

  var stored = readChoice();
  if (stored === "accept") boot();
  else if (!stored) show(false);
})();
