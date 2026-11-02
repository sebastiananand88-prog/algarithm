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


def build_page(template, booked, shared, page):
    slug = page["slug"]
    if "REPLACE" in page["calendar_url"]:
        warnings.append(f"[{slug}] calendar_url is still a placeholder (GHL calendar → Embed → booking widget URL)")

    if page.get("claims_placeholder"):
        warnings.append(f"[{slug}] $ ranges in subhead / proof_title are placeholders — set them from real client results")

    config = {"page": slug, "pixelId": shared["meta_pixel_id"]}
    vsl = f'<section class="vsl">{render_video(page["vsl"], "VSL")}</section>' if page.get("vsl") else ""

    tokens = {
        "lang": shared["lang"],
        "brand": esc(shared["brand"]),
        "assets": "../assets",
        "config_json": json.dumps(config),
        "slug": slug,
        "calendar_url": esc(page["calendar_url"]),
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
        "year": "2026",
    }

    page_dir = DIST / slug
    page_dir.mkdir(parents=True, exist_ok=True)
    (page_dir / "index.html").write_text(fill(template, tokens, slug), encoding="utf-8")

    # Thank-you page: set it as the calendar's redirect URL in GHL so bookings fire Schedule.
    booked_dir = page_dir / "booked"
    booked_dir.mkdir()
    (booked_dir / "index.html").write_text(
        fill(booked, dict(tokens, assets="../../assets"), f"{slug}/booked"), encoding="utf-8")
    return f"dist/{slug}/index.html  +  dist/{slug}/booked/"


def main():
    shared = json.loads((CONTENT / "shared.json").read_text())
    template = (SRC / "template.html").read_text()
    booked = (SRC / "booked.html").read_text()

    if not shared["meta_pixel_id"]:
        warnings.append("[all] meta_pixel_id is empty — the pixel won't load")
    if shared["privacy_url"] in ("", "#"):
        warnings.append("[all] privacy_url not set — Meta requires a privacy policy when you use the pixel")

    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST / "assets").mkdir(parents=True)
    for asset in ("styles.css", "main.js"):
        shutil.copy(SRC / asset, DIST / "assets" / asset)
    shutil.copytree(SRC / "img", DIST / "assets" / "img")

    built = []
    for path in sorted(CONTENT.glob("*.json")):
        if path.name != "shared.json":
            built.append(build_page(template, booked, shared, json.loads(path.read_text())))

    print("Built:")
    for line in built:
        print(f"  {line}")
    if warnings:
        print("\nBefore you launch ads:")
        for w in warnings:
            print(f"  ! {w}")


if __name__ == "__main__":
    main()
