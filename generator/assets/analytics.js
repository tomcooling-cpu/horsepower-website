/* WS-SITE25 event layer. Reads only the data-ga* attributes build.py emits, plan
   filter events from catalogue.js, and the page's own structure. It never reads a
   contact form field. Events queue in memory until consent.js signals hp:ga-ready
   and are sent through gtag; without consent the queue is simply dropped with the
   page, nothing is stored. */
(function () {
  "use strict";
  var root = document.documentElement;
  if (!root.getAttribute("data-ga4")) return;
  var PAGE_TYPE = root.getAttribute("data-page-type") || "page";
  var LIST_NAMES = { plan_list: "Plan Store", female_performance: "Female Performance" };
  var LEAD_KEY = "hp_lead_pending";
  var LEAD_MAX_AGE = 15 * 60 * 1000;
  var queue = [];

  function ready() { return window.__hpGaReady === true && typeof window.gtag === "function"; }

  function send(name, params) {
    if (window.__hpGaRevoked) return;
    if (ready()) gtag("event", name, params || {});
    else queue.push([name, params || {}]);
  }

  document.addEventListener("hp:ga-ready", function () {
    var q = queue;
    queue = [];
    q.forEach(function (e) { gtag("event", e[0], e[1]); });
  });
  document.addEventListener("hp:ga-revoked", function () { queue = []; });

  function itemOf(el) {
    var host = el && el.closest ? el.closest("[data-ga-item]") : null;
    if (!host) return null;
    try { return JSON.parse(host.getAttribute("data-ga-item")); } catch (e) { return null; }
  }

  function zoneOf(el) {
    if (el.closest(".site-header")) return "header";
    if (el.closest(".site-footer")) return "footer";
    if (el.closest(".reviews")) return "reviews";
    if (PAGE_TYPE === "contact") return "contact_page";
    return PAGE_TYPE;
  }

  function text60(el) {
    return (el.textContent || el.getAttribute("aria-label") || "").replace(/\s+/g, " ").trim().slice(0, 60);
  }

  document.addEventListener("click", function (e) {
    var t = e.target;
    if (!t || !t.closest) return;

    var faqSummary = t.closest("details.faq > summary");
    if (faqSummary) {
      var det = faqSummary.parentNode;
      if (!det.open) send("faq_open", { faq_question: text60(faqSummary) });
      return;
    }

    var arrow = t.closest(".carousel-arrow, .carousel-dot");
    if (arrow) {
      var car = arrow.closest("[data-carousel]");
      var action = arrow.classList.contains("carousel-dot") ? "dot"
        : (arrow.classList.contains("prev") ? "prev" : "next");
      send("carousel_interact", { carousel_action: action, carousel_id: car ? car.id : "" });
      return;
    }

    var a = t.closest("a[href]");
    if (!a) return;
    var kind = a.getAttribute("data-ga");
    var url = a.href;
    var item;
    if (kind === "nav") {
      send("nav_click", { nav_label: a.getAttribute("data-ga-label"), link_url: url });
    } else if (kind === "cta") {
      send("cta_click", { cta_label: a.getAttribute("data-ga-label"),
        cta_location: a.getAttribute("data-ga-location"), link_url: url });
    } else if (kind === "buy") {
      item = itemOf(a);
      if (item) {
        send("begin_checkout", { currency: "GBP", value: item.price, items: [item],
          item_list_name: a.getAttribute("data-ga-list"), link_url: url });
      }
    } else if (kind === "select") {
      item = itemOf(a);
      if (item) {
        send("select_item", { item_list_name: a.getAttribute("data-ga-list"), items: [item] });
      }
    } else if (kind === "contact") {
      send("contact_click", { channel: a.getAttribute("data-ga-channel"), cta_location: zoneOf(a) });
    } else if (kind === "outbound" || (!kind && /^https?:/i.test(url) && a.hostname !== location.hostname)) {
      send("outbound_click", { link_url: url, link_domain: a.hostname, link_text: text60(a) });
    }
  });

  // Plan filters (catalogue.js dispatches hp:filter after every user change).
  var searchTimer = null;
  document.addEventListener("hp:filter", function (e) {
    var d = e.detail || {};
    if (d.filter === "search") {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(function () {
        send("filter_plans", { filter_name: "search",
          filter_value: String(d.value || "").toLowerCase().slice(0, 40), results_count: d.shown });
      }, 800);
    } else {
      send("filter_plans", { filter_name: d.filter, filter_value: String(d.value || ""),
        results_count: d.shown });
    }
  });

  // Contact form: start and submit (submit fires only after constraint validation).
  var form = document.querySelector("form.contact-form");
  if (form) {
    var started = false;
    var onStart = function () {
      if (started) return;
      started = true;
      send("form_start", { form_name: "contact", form_location: "contact_page" });
    };
    form.addEventListener("focusin", onStart);
    form.addEventListener("input", onStart);
    form.addEventListener("submit", function () {
      send("contact_submit", { form_name: "contact" });
      if (ready()) {
        try { window.sessionStorage.setItem(LEAD_KEY, String(Date.now())); } catch (err) { /* blocked */ }
      }
    });
  }

  // Scroll depth 25 / 50 / 75 (enhanced measurement covers 90).
  var marks = [25, 50, 75];
  function onScroll() {
    var doc = document.documentElement;
    var h = doc.scrollHeight - window.innerHeight;
    var pct = h > 0 ? (window.scrollY / h) * 100 : 100;
    while (marks.length && pct >= marks[0]) send("scroll_depth", { scroll_percent: marks.shift() });
    if (!marks.length) window.removeEventListener("scroll", onScroll);
  }
  window.addEventListener("scroll", onScroll, { passive: true });

  // Page-load events.
  var main = document.getElementById("main");
  if (PAGE_TYPE === "plan_detail") {
    var it = itemOf(main);
    if (it) send("view_item", { currency: "GBP", value: it.price, items: [it] });
  } else if (LIST_NAMES[PAGE_TYPE]) {
    send("view_item_list", { item_list_name: LIST_NAMES[PAGE_TYPE],
      item_count: document.querySelectorAll("[data-ga-item]").length });
  } else if (PAGE_TYPE === "contact_thanks") {
    var ts = null;
    try {
      ts = window.sessionStorage.getItem(LEAD_KEY);
      window.sessionStorage.removeItem(LEAD_KEY);
    } catch (err) { ts = null; }
    var age = ts ? Date.now() - parseInt(ts, 10) : NaN;
    if (age >= 0 && age < LEAD_MAX_AGE) {
      send("generate_lead", { currency: "GBP",
        value: parseFloat(main && main.getAttribute("data-lead-value")) || 0,
        lead_source: "contact_form" });
    }
  }
})();
