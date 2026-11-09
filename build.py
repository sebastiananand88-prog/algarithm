#!/usr/bin/env python3
"""Build the Algarithm landing pages.

    python3 build.py

Every content/<page>.json (except shared.json) becomes dist/<slug>/index.html.
To A/B test a variant (e.g. with a VSL, or a different headline), copy a content
file, give it a new slug, and point an ad set at it.
No dependencies beyond the Python standard library.
"""
import html
import json
import pathlib
import re
import shutil
from urllib.parse import parse_qs, urlparse

ROOT = pathlib.Path(__file__).parent
SRC = ROOT / "src"
CONTENT = ROOT / "content"
DIST = ROOT / "dist"

PLAY = '<span class="play" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg></span>'

warnings = []


def esc(s):
    # Word joiners around en dashes keep ranges like "$30K–$100K+" on one line.
    return html.escape(str(s), quote=True).replace("–", "\u2060–\u2060")


def rich(s):
    """Escape text, then turn *word* into <em>word</em> (rendered in brand blue)."""
    return re.sub(r"\*(.+?)\*", r"<em>\1</em>", esc(s))


def youtube_id(url):
    u = urlparse(url)
    host = u.netloc.replace("www.", "")
    if host in ("youtube.com", "m.youtube.com"):
        return parse_qs(u.query).get("v", [""])[0]
    if host == "youtu.be":
        return u.path.strip("/")
    return ""


def embed_url(url):
    """Turn a YouTube / Loom / Vimeo share link into an autoplaying embed URL."""
    vid = youtube_id(url)
    if vid:
        return f"https://www.youtube-nocookie.com/embed/{vid}?autoplay=1&rel=0"
    u = urlparse(url)
    host = u.netloc.replace("www.", "")
    if host == "loom.com":
        return "https://www.loom.com/embed/" + u.path.rsplit("/", 1)[-1] + "?autoplay=1"
    if host == "vimeo.com":
        return "https://player.vimeo.com/video" + u.path + "?autoplay=1"
    return url


def render_video(url, name):
    if not url:
        return '<div class="video video-empty">Video coming soon</div>'
    vid = youtube_id(url)
    poster = f' style="background-image: url(https://i.ytimg.com/vi/{vid}/hqdefault.jpg)"' if vid else ""
    return (
        f'<button class="video"{poster} data-embed="{esc(embed_url(url))}" data-name="{esc(name)}" '
        f'aria-label="Play {esc(name)} video">{PLAY}</button>'
    )


def render_cases(cases, slug):
    out = []
    for c in cases:
        badge = ""
        if c.get("placeholder"):
            warnings.append(f"[{slug}] case study '{c['name']}' is still example content")
            badge = '<span class="badge-example">Example · replace</span>'
        out.append(
            f'<article class="case">{badge}{render_video(c.get("video", ""), c["name"])}'
            f'<p class="case-result"><strong>{esc(c["name"])}:</strong> {esc(c["result"])}</p></article>'
        )
    return "".join(out)


def fill(template, tokens, label):
    out = template
    for key, value in tokens.items():
        out = out.replace("{{" + key + "}}", value)
    leftover = re.findall(r"{{\s*\w+\s*}}", out)
    if leftover:
        raise SystemExit(f"[{label}] unfilled template tokens: {leftover}")
    return out


def render_faqs(faqs):
    return "".join(
        f'<details class="faq"><summary>{esc(f["q"])}</summary><div class="faq-a">{esc(f["a"])}</div></details>'
        for f in faqs
    )


GHL_FORM = """    <iframe class="ghl-embed ghl-form" data-src="{url}" id="inline-{id}" title="{name}"
      style="width:100%;border:none;border-radius:8px"
      data-layout="{{'id':'INLINE'}}" data-trigger-type="alwaysShow" data-trigger-value=""
      data-activation-type="alwaysActivated" data-activation-value=""
      data-deactivation-type="neverDeactivate" data-deactivation-value=""
      data-form-name="{name}" data-height="802" data-layout-iframe-id="inline-{id}"
      data-form-id="{id}" data-cookie-consent="true" data-cookie-consent-provider="auto"></iframe>
    <div class="embed-missing" hidden>Form goes here: set form_url in content/{slug}.json</div>"""

# Typeform live embed. URL params listed in transitive-search-params, plus `niche`, are passed into
# the Typeform's hidden fields (create hidden fields with these names in Typeform). One Typeform can
# serve every niche: set its completion redirect to https://<domain>/{{hidden:niche}}/book/?...
TYPEFORM = """    <div class="typeform-embed" data-tf-live="{id}" data-tf-hidden="niche={slug}"
      data-tf-transitive-search-params="utm_source,utm_medium,utm_campaign,utm_content,utm_term,fbclid"></div>
    <script src="https://embed.typeform.com/next/embed.js"></script>"""


def render_lead_embed(page):
    """The landing page's lead form: a Typeform if typeform_id is set, otherwise the GHL form."""
    if page.get("typeform_id"):
        return TYPEFORM.format(id=esc(page["typeform_id"]), slug=esc(page["slug"])), " typeform"
    url = page["form_url"]
    return GHL_FORM.format(url=esc(url), id=esc(url.rstrip("/").rsplit("/", 1)[-1]),
                           name=esc(page["form_name"]), slug=page["slug"]), " loading"


def build_page(template, book, booked, shared, page):
    slug = page["slug"]
    if not page.get("typeform_id") and "REPLACE" in page["form_url"]:
        warnings.append(f"[{slug}] form_url is still a placeholder (GHL form → Embed → iframe src)")

    if page.get("claims_placeholder"):
        warnings.append(f"[{slug}] $ ranges in subhead / proof_title are placeholders — set them from real client results")

    config = {"page": slug, "pixelId": shared["meta_pixel_id"]}
    vsl = f'<section class="vsl">{render_video(page["vsl"], "VSL")}</section>' if page.get("vsl") else ""

    lead_embed, book_class = render_lead_embed(page)
    tokens = {
        "lang": shared["lang"],
        "brand": esc(shared["brand"]),
        "assets": "../assets",
        "config_json": json.dumps(config),
        "slug": slug,
        "calendar_url": esc(page["calendar_url"]),
        "lead_embed": lead_embed,
        "book_class": book_class,
        "page_title": esc(page["seo_title"]),
        "page_description": esc(page["seo_description"]),
        "headline": rich(page["headline"]),
        "sub": esc(page["sub"]),
        "subhead": esc(page["subhead"]),
        "vsl": vsl,
        "proof_title": esc(page["proof_title"]),
        "cases": render_cases(page["cases"], slug),
        "cta": esc(page["cta"]),
        "privacy_url": esc(shared["privacy_url"]),
        "terms_url": esc(shared["terms_url"]),
        "pixel_script": (SRC / "pixel.html").read_text(),
        "year": "2026",
    }

    page_dir = DIST / slug
    page_dir.mkdir(parents=True, exist_ok=True)
    (page_dir / "index.html").write_text(fill(template, tokens, slug), encoding="utf-8")

    # Calendar page: set it as the form's on-submit redirect in GHL so submissions fire Lead.
    book_dir = page_dir / "book"
    book_dir.mkdir()
    (book_dir / "index.html").write_text(
        fill(book, dict(tokens, assets="../../assets"), f"{slug}/book"), encoding="utf-8")

    # Thank-you page: set it as the calendar's redirect URL in GHL so bookings fire Schedule.
    booked_dir = page_dir / "booked"
    booked_dir.mkdir()
    thanks = page["thanks"]
    if not thanks["vsl"]:
        warnings.append(f"[{slug}] thank-you page VSL not set (thanks.vsl)")
    booked_tokens = dict(
        tokens,
        assets="../../assets",
        vsl=render_video(thanks["vsl"], "VSL"),
        thanks_proof_title=esc(thanks["proof_title"]),
        thanks_cases=render_cases(page["cases"] + thanks["cases"], slug),
        faqs=render_faqs(thanks["faqs"] + shared["faqs"]),
    )
    (booked_dir / "index.html").write_text(fill(booked, booked_tokens, f"{slug}/booked"), encoding="utf-8")
    return f"dist/{slug}/index.html  +  book/  +  booked/"


def main():
    shared = json.loads((CONTENT / "shared.json").read_text())
    template = (SRC / "template.html").read_text()
    book = (SRC / "book.html").read_text()
    booked = (SRC / "booked.html").read_text()

    if not shared["meta_pixel_id"]:
        warnings.append("[all] meta_pixel_id is empty — the pixel won't load")

    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST / "assets").mkdir(parents=True)
    for asset in ("styles.css", "main.js"):
        shutil.copy(SRC / asset, DIST / "assets" / asset)
    shutil.copytree(SRC / "img", DIST / "assets" / "img")

    # Privacy policy, linked from every page footer.
    privacy_tokens = {
        "lang": shared["lang"],
        "brand": esc(shared["brand"]),
        "assets": "../assets",
        "legal_name": esc(shared["legal_name"]),
        "site_domain": esc(shared["site_domain"]),
        "privacy_email": esc(shared["privacy_email"]),
        "privacy_updated": esc(shared["privacy_updated"]),
        "privacy_url": esc(shared["privacy_url"]),
        "terms_url": esc(shared["terms_url"]),
        "year": "2026",
    }
    (DIST / "privacy").mkdir()
    (DIST / "privacy" / "index.html").write_text(
        fill((SRC / "privacy.html").read_text(), privacy_tokens, "privacy"), encoding="utf-8")

    # Terms and conditions (includes the SMS program terms used for A2P registration).
    if not shared["company_number"]:
        warnings.append("[all] terms: set company_number in shared.json once Algarithm is incorporated")
    details = f" (company number {esc(shared['company_number'])})" if shared["company_number"] else ""
    terms_tokens = dict(
        privacy_tokens,
        terms_updated=esc(shared["terms_updated"]),
        company_details=details,
    )
    (DIST / "terms").mkdir()
    (DIST / "terms" / "index.html").write_text(
        fill((SRC / "terms.html").read_text(), terms_tokens, "terms"), encoding="utf-8")

    built = ["dist/privacy/index.html", "dist/terms/index.html"]
    for path in sorted(CONTENT.glob("*.json")):
        if path.name != "shared.json":
            built.append(build_page(template, book, booked, shared, json.loads(path.read_text())))

    pages = [json.loads(p.read_text()) for p in CONTENT.glob("*.json") if p.name != "shared.json"]
    forms = [p["form_url"] for p in pages if not p.get("typeform_id")]  # a shared Typeform routes by its niche hidden field
    if len(set(forms)) < len(forms):
        warnings.append("[all] pages share one GHL form, so it can only redirect to one /book/ page — duplicate it per niche")

    print("Built:")
    for line in built:
        print(f"  {line}")
    if warnings:
        print("\nBefore you launch ads:")
        for w in dict.fromkeys(warnings):  # landing + thank-you pages share case studies
            print(f"  ! {w}")


if __name__ == "__main__":
    main()
