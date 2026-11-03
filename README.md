# Algarithm landing pages

One simple page per niche. The structure is: logo → headline → one-line sub → GoHighLevel calendar → video testimonials → "Become our next success story" button.
Each niche also gets a thank-you page at `/<slug>/booked/`.

    python3 build.py                     # writes dist/<slug>/index.html and dist/<slug>/booked/
    cd dist && python3 -m http.server 8765   # preview at http://localhost:8765/<slug>/

Pages: `dental`, `aesthetic-clinics`, `hair-loss-clinics`. To deploy, upload `dist/` to Netlify, Vercel or Cloudflare Pages.

## Editing
- `content/shared.json`: brand, pixel ID, privacy URL
- `content/<slug>.json`: headline, sub, `calendar_url`, optional `vsl` video, case studies
  - `calendar_url` is the `src` from GHL → Calendars → your calendar → Share / Embed code,
    e.g. `https://api.leadconnectorhq.com/widget/booking/<calendarId>`. Use a separate calendar per niche.
  - In `headline`, `*text*` shows in brand blue.
  - Case study `video` and `vsl` take YouTube, Loom or Vimeo links. A YouTube thumbnail is used automatically.
  - Remove `"placeholder": true` once a case study is real.
- A/B test: copy a content file, change `slug` (e.g. `dental-vsl`), edit, rebuild, and point an ad set at it.

## Tracking
- The Meta Pixel loads when `meta_pixel_id` is set. The landing page fires `PageView`, `CTAClick` and `VideoPlay`.
- **Booking (`Schedule`)** fires on the thank-you page. In each GHL calendar, go to Calendar settings → Forms / Confirmation →
  "Redirect to URL" and set it to `https://<your-domain>/<slug>/booked/`. If you can append the appointment or contact ID
  (`?appointment_id=...` or `?contact_id=...`), the page uses it as the `eventID`. Send the server-side CAPI `Schedule` with
  `event_id = schedule_<same id>` and Meta will deduplicate the two.
- Only one system should send server-side `Schedule` events. If you send them yourself, leave GHL's built-in
  Facebook Conversions API off for that event, or bookings will be double-counted.
- UTMs and `fbclid` on the ad URL are passed into the GHL widget so they're recorded on the contact. Suggested params:
  `utm_source=meta&utm_medium=paid_social&utm_campaign={{campaign.name}}&utm_content={{ad.name}}&utm_term={{adset.name}}`

`build.py` prints a launch checklist of anything still set to placeholder content.
