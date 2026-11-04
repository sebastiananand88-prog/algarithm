/* Algarithm landing page behaviour: GHL calendar embed, Meta events, video facades, sticky CTA. */
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

  // ---- GoHighLevel calendar ----
  // UTMs and fbclid from the Meta ad URL are passed into the booking widget so GHL
  // records the campaign / ad set / ad on the contact.
  var frame = document.querySelector('.ghl-calendar');
  var calUrl = frame && frame.getAttribute('data-src');
  if (!frame) {
    // Thank-you page: no calendar.
  } else if (!calUrl || calUrl.indexOf('REPLACE') !== -1) {
    frame.hidden = true;
    document.querySelector('.calendar-missing').hidden = false;
  } else {
    var pass = new URLSearchParams();
    ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term', 'fbclid'].forEach(function (k) {
      if (params.get(k)) pass.set(k, params.get(k));
    });
    if (!pass.has('utm_source')) pass.set('utm_source', 'meta');
    if (!pass.has('utm_campaign')) pass.set('utm_campaign', cfg.page);
    // GHL's resize script matches iframes by an id of the form <calendarId>_<timestamp>.
    frame.id = calUrl.replace(/\/+$/, '').split('/').pop() + '_' + Date.now();
    frame.src = calUrl + (calUrl.indexOf('?') === -1 ? '?' : '&') + pass.toString();
    var embed = document.createElement('script');
    embed.src = 'https://link.msgsndr.com/js/form_embed.js';
    document.body.appendChild(embed);
    // form_embed.js hides the iframe until the widget reports it has loaded. Keep the
    // space reserved until then; if that message never arrives, show the calendar anyway.
    var book = document.getElementById('book');
    var started = Date.now();
    (function waitForCalendar() {
      if (frame.style.visibility !== 'hidden' && frame.style.height) {
        book.classList.remove('loading');
      } else if (Date.now() - started > 4000) {
        ['opacity', 'visibility', 'pointer-events', 'left', 'position'].forEach(function (p) {
          frame.style.removeProperty(p);
        });
        book.classList.remove('loading');
      } else {
        setTimeout(waitForCalendar, 150);
      }
    })();
  }

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

  // ---- Video facades: load the player only when clicked ----
  document.querySelectorAll('.video[data-embed]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var iframe = document.createElement('iframe');
      iframe.src = btn.getAttribute('data-embed');
      iframe.allow = 'autoplay; fullscreen; picture-in-picture';
      iframe.allowFullscreen = true;
      btn.innerHTML = '';
      btn.appendChild(iframe);
      trackCustom('VideoPlay', { video: btn.getAttribute('data-name') });
    }, { once: true });
  });

  // ---- Sticky mobile CTA: visible once the calendar is scrolled past ----
  var sticky = document.querySelector('.sticky-cta');
  var book = document.getElementById('book');
  if (sticky && book && 'IntersectionObserver' in window) {
    new IntersectionObserver(function (en) {
      var e0 = en[0];
      sticky.classList.toggle('show', !e0.isIntersecting && e0.boundingClientRect.top < 0);
    }).observe(book);
  }
})();
