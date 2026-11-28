/* Algarithm landing page behaviour: GHL form/calendar embeds, Meta events, video facades, sticky CTA. */
(function () {
  var cfg = window.SITE || {};
  var params = new URLSearchParams(location.search);

  function track(name, data, eventId) {
    if (window.fbq) {
      window.fbq('track', name, data || {}, eventId ? { eventID: eventId } : undefined);
    }
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push(Object.assign({ event: name, page: cfg.page, eventId: eventId }, data));
  }

  function trackCustom(name, data) {
    if (window.fbq) window.fbq('trackCustom', name, data || {});
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push(Object.assign({ event: name, page: cfg.page }, data));
  }

  // ---- GoHighLevel embeds: lead form (landing page) and calendar (/book/) ----
  // UTMs and fbclid from the ad URL are passed into the embed so GHL records the campaign /
  // ad set / ad on the contact. The calendar also receives any contact details the form's
  // redirect put on the URL, so people don't have to type them twice.
  var ATTRIBUTION = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term', 'fbclid'];
  var PREFILL = ['first_name', 'last_name', 'name', 'full_name', 'email', 'phone', 'contact_id'];

  function embedGHL(frame) {
    var url = frame.getAttribute('data-src');
    if (!url || url.indexOf('REPLACE') !== -1) {
      frame.hidden = true;
      frame.parentNode.querySelector('.embed-missing').hidden = false;
      return;
    }
    var isCalendar = url.indexOf('/widget/booking/') !== -1;
    var pass = new URLSearchParams();
    ATTRIBUTION.concat(isCalendar ? PREFILL : []).forEach(function (k) {
      if (params.get(k)) pass.set(k, params.get(k));
    });
    if (!pass.has('utm_source')) pass.set('utm_source', 'meta');
    if (!pass.has('utm_campaign')) pass.set('utm_campaign', cfg.page);
    // GHL's resize script matches calendar iframes by an id of the form <calendarId>_<timestamp>.
    if (isCalendar) frame.id = url.replace(/\/+$/, '').split('/').pop() + '_' + Date.now();
    frame.src = url + (url.indexOf('?') === -1 ? '?' : '&') + pass.toString();
    var embed = document.createElement('script');
    embed.src = 'https://link.msgsndr.com/js/form_embed.js';
    document.body.appendChild(embed);
    // form_embed.js may hide the iframe until it reports it has loaded. Keep the space
    // reserved until then; if that message never arrives, show the embed anyway.
    var box = frame.parentNode;
    var started = Date.now();
    (function waitForEmbed() {
      var hidden = frame.style.visibility === 'hidden' || frame.style.display === 'none';
      if (!hidden && frame.style.height) {
        box.classList.remove('loading');
      } else if (Date.now() - started > 4000) {
        ['opacity', 'visibility', 'pointer-events', 'left', 'position', 'display'].forEach(function (p) {
          frame.style.removeProperty(p);
        });
        box.classList.remove('loading');
      } else {
        setTimeout(waitForEmbed, 150);
      }
    })();
  }
  document.querySelectorAll('.ghl-embed').forEach(embedGHL);

  // ---- Cookie consent (UK/EEA timezones only; see the pixel snippet) ----
  if (cfg.needsConsent) {
    var bar = document.createElement('div');
    bar.className = 'consent';
    bar.innerHTML = '<p>We use cookies to measure our ads. See our <a href="/privacy/">privacy policy</a>.</p>' +
      '<div class="consent-actions"><button type="button" class="consent-no" data-choice="denied">Decline</button>' +
      '<button type="button" class="btn consent-yes" data-choice="granted">Accept</button></div>';
    bar.addEventListener('click', function (e) {
      var choice = e.target.getAttribute && e.target.getAttribute('data-choice');
      if (!choice) return;
      try { localStorage.setItem('algarithm-consent', choice); } catch (err) {}
      if (choice === 'granted') cfg.loadPixel();
      bar.remove();
    });
    document.body.appendChild(bar);
  }

  // ---- CTA clicks ----
  document.querySelectorAll('[data-cta]').forEach(function (el) {
    el.addEventListener('click', function () {
      trackCustom('CTAClick', { location: el.getAttribute('data-cta') });
    });
  });

  // ---- Videos ----
  // Desktop: a thumbnail facade that swaps in the player (and autoplays) on the first click.
  // Phones block autoplay with sound in a just-created iframe, so a facade would need two taps.
  // There we load the real player straight away (lazily, as it nears the screen) so one tap plays.
  var touch = window.matchMedia && window.matchMedia('(hover: none)').matches;

  function playerFor(btn, autoplay) {
    var iframe = document.createElement('iframe');
    var src = btn.getAttribute('data-embed');
    if (!autoplay) src = src.replace(/([?&])autoplay=1&?/, '$1').replace(/[?&]$/, '');
    iframe.src = src;
    iframe.allow = 'autoplay; fullscreen; picture-in-picture';
    iframe.allowFullscreen = true;
    iframe.title = btn.getAttribute('data-name') || 'Video';
    return iframe;
  }

  // YouTube reports player state to the page once asked to (needs enablejsapi=1 on the embed).
  // We use it to count real plays and to switch captions off when a video first starts:
  // YouTube turns them on by itself for some viewers (their account or phone accessibility
  // settings), and cc_load_policy=0 alone doesn't stop that. Viewers can still turn them back on.
  var players = [];
  function command(frame, func, args) {
    frame.el.contentWindow.postMessage(
      JSON.stringify({ event: 'command', func: func, args: args || [], id: frame.id, channel: 'widget' }), '*');
  }
  function watch(iframe, name) {
    var frame = { el: iframe, name: name };
    var id = frame.id = players.push(frame) - 1;
    // The player only talks back to a page that names its origin and says it's listening.
    iframe.src += '&origin=' + encodeURIComponent(location.origin);
    iframe.addEventListener('load', function () {
      iframe.contentWindow.postMessage(JSON.stringify({ event: 'listening', id: id, channel: 'widget' }), '*');
    });
    return iframe;
  }
  window.addEventListener('message', function (e) {
    if (!/^https:\/\/(www\.)?youtube(-nocookie)?\.com$/.test(e.origin)) return;
    var d; try { d = JSON.parse(e.data); } catch (err) { return; }
    // Match by sender, not d.id: the player doesn't always echo the id back.
    var frame = players.filter(function (f) { return f.el.contentWindow === e.source; })[0];
    if (!frame) return;
    var state = d.event === 'onStateChange' ? d.info : d.info && d.info.playerState;
    if (state !== 1 || frame.started) return;
    // First play: captions can load a moment after playback starts, so switch them off a few times.
    frame.started = true;
    [0, 1000, 3000].forEach(function (ms) {
      setTimeout(function () { command(frame, 'unloadModule', ['captions']); }, ms);
    });
    trackCustom('VideoPlay', { video: frame.name });
  });

  document.querySelectorAll('.video[data-embed]').forEach(function (btn) {
    var name = btn.getAttribute('data-name');
    if (touch) {
      var iframe = watch(playerFor(btn, false), name);
      iframe.loading = 'lazy';
      var box = document.createElement('div');
      box.className = 'video video-live';
      box.appendChild(iframe);
      btn.replaceWith(box);
      return;
    }
    btn.addEventListener('click', function () {
      btn.innerHTML = '';
      btn.appendChild(watch(playerFor(btn, true), name));
    }, { once: true });
  });

  // ---- Sticky mobile CTA: visible once the form is scrolled past ----
  var sticky = document.querySelector('.sticky-cta');
  var book = document.getElementById('book');
  if (sticky && book && 'IntersectionObserver' in window) {
    new IntersectionObserver(function (en) {
      var e0 = en[0];
      sticky.classList.toggle('show', !e0.isIntersecting && e0.boundingClientRect.top < 0);
    }).observe(book);
  }
})();
