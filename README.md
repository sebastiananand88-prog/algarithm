# Algarithm landing pages

One simple page per niche. The structure is: logo → headline → one-line sub → GoHighLevel lead form → video testimonials → "Become our next success story" button.
Each niche has three steps:

    /<slug>/         landing page with the lead form (Typeform if `typeform_id` is set, else GHL)
    /<slug>/book/    "Last step": the niche's GHL calendar   (form redirects here, fires Lead)
    /<slug>/booked/  thank-you page with VSL, cases and FAQs (calendar redirects here, fires Schedule)

    python3 build.py                     # writes dist/<slug>/index.html and dist/<slug>/booked/
    cd dist && python3 -m http.server 8765   # preview at http://localhost:8765/<slug>/

Pages: `dental`, `aesthetic-clinics`, `hair-loss-clinics`. To deploy, upload `dist/` to Netlify, Vercel or Cloudflare Pages.

## Editing
- `content/shared.json`: brand, pixel ID, privacy URL
- `content/<slug>.json`: headline, sub, `typeform_id` (or GHL `form_url`), `calendar_url`, optional `vsl` video, case studies, thank-you page content
  - `form_url` is the iframe `src` from GHL → Sites → Forms → your form → Embed, e.g.
    `https://api.leadconnectorhq.com/widget/form/<formId>`. It's embedded inline. Use a separate form per niche so each can redirect to its own `/book/` page.
  - `calendar_url` is the booking widget URL from GHL → Calendars → Share, e.g. `https://api.leadconnectorhq.com/widget/booking/<calendarId>`.
    The `/book/` page passes `first_name`, `last_name`, `email` and `phone` from its URL into the calendar, so turn on
    "send form data as query parameters" (or add them to the redirect URL) in the form's redirect settings.
  - In `headline`, `*text*` shows in brand blue.
  - Case study `video` and `vsl` take YouTube, Loom or Vimeo links. A YouTube thumbnail is used automatically.
  - Remove `"placeholder": true` once a case study is real.
- A/B test: copy a content file, change `slug` (e.g. `dental-vsl`), edit, rebuild, and point an ad set at it.

## Tracking
- The Meta Pixel loads when `meta_pixel_id` is set. The landing page fires `PageView`, `CTAClick` and `VideoPlay`.
- **Form submit (`Lead`)** fires on `/<slug>/book/`. In each GHL form, set the on-submit action to
  "Redirect to URL" → `https://<your-domain>/<slug>/book/`.
- **Booking (`Schedule`)** fires on `/<slug>/booked/`. In each GHL calendar, set the redirect URL to
  `https://<your-domain>/<slug>/booked/`.
- If GHL appends `contact_id` (or `appointment_id`) to those redirects, the pages use it as the `eventID`. Send the
  server-side CAPI events with `event_id = lead_<id>` / `schedule_<id>` and Meta will deduplicate them.
- Only one system should send server-side `Lead` / `Schedule` events. If you send them yourself, leave GHL's built-in
  Facebook Conversions API off for that event, or bookings will be double-counted.
- UTMs and `fbclid` on the ad URL are passed into the GHL form so they're recorded on the contact. Suggested params:
  `utm_source=meta&utm_medium=paid_social&utm_campaign={{campaign.name}}&utm_content={{ad.name}}&utm_term={{adset.name}}`

`build.py` prints a launch checklist of anything still set to placeholder content.

## Typeform
All niches share one Typeform. Each page passes a hidden field `niche` (its slug) plus any UTMs / `fbclid`
from the ad URL. In Typeform, add hidden fields `niche`, `utm_source`, `utm_medium`, `utm_campaign`,
`utm_content`, `utm_term`, `fbclid`, and set the completion redirect to:

    https://us.algarithm.co.uk/{{hidden:niche}}/book/?first_name={{field:first}}&last_name={{field:last}}&email={{field:email}}

(insert the field references with Typeform's recall picker) so each lead lands on its niche's calendar.
