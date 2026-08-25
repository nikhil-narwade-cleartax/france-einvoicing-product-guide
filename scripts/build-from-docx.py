#!/usr/bin/env python3
"""Convert the pandoc output of the France Product Guide into a
Documentation.AI-shaped MDX site.

  _raw/guide.md + _raw/media/  ->  docs/*.mdx + images/ + documentation.json
"""

import json
import os
import re
import shutil
from pathlib import Path

from PIL import Image

BUILD = Path.home() / "Downloads" / "cleartax-france-docs"
RAW = BUILD / "_raw"
DOCS = BUILD / "docs"
IMG = BUILD / "images"

MAX_W = 1600  # screenshots are rendered ~6.5in wide; 1600px is plenty

# ------------------------------------------------------------------ images --
IMG.mkdir(parents=True, exist_ok=True)
before = after = 0
for src in sorted((RAW / "media").iterdir()):
    if src.suffix.lower() not in (".png", ".jpg", ".jpeg"):
        continue
    before += src.stat().st_size
    im = Image.open(src)
    if im.width > MAX_W:
        im = im.resize((MAX_W, round(im.height * MAX_W / im.width)), Image.LANCZOS)
    dst = IMG / src.name
    if src.suffix.lower() == ".png":
        rgb = im.convert("RGB") if im.mode not in ("RGB", "RGBA", "P") else im
        # screenshots quantise well; keep whichever is smaller
        cand = dst.with_suffix(".q.png")
        rgb.convert("RGB").quantize(colors=256, method=Image.MEDIANCUT).save(
            cand, optimize=True)
        rgb.save(dst, optimize=True)
        if cand.stat().st_size < dst.stat().st_size:
            shutil.move(cand, dst)
        else:
            cand.unlink()
    else:
        im.convert("RGB").save(dst, quality=82, optimize=True, progressive=True)
    after += dst.stat().st_size

print(f"images: {before/1e6:.1f} MB -> {after/1e6:.1f} MB "
      f"({100 * (1 - after / before):.0f}% smaller)")

# --------------------------------------------------------------- transform --
text = (RAW / "guide.md").read_text(encoding="utf-8")

CAPTION = re.compile(r"^\*\*\*\\\[(?P<id>[^\]]+)\\\]\*\*\s*(?P<txt>.*?)\*\s*$")
IMGTAG = re.compile(r'<img\s+src="\./media/(?P<f>[^"]+)"[^>]*/>')


def clean_caption(line):
    m = CAPTION.match(line.strip())
    if not m:
        return None
    return f"[{m.group('id')}] {m.group('txt')}".strip()


def transform(body):
    """Demote headings one level, turn <img> + caption into markdown."""
    out, lines, i = [], body.split("\n"), 0
    while i < len(lines):
        line = lines[i]
        m = IMGTAG.search(line)
        if m:
            fname = m.group("f")
            cap = None
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines):
                cap = clean_caption(lines[j])
            alt = cap or Path(fname).stem
            out.append(f"![{alt}](/images/{fname})")
            if cap:
                out.append("")
                out.append(f"*{cap}*")
                i = j + 1
            else:
                i += 1
            continue
        if line.startswith("#"):
            h = len(line) - len(line.lstrip("#"))
            line = "#" * max(1, h - 1) + line[h:]
        out.append(line)
        i += 1

    txt = "\n".join(out)
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    return txt.strip() + "\n"


def slugify(s):
    s = re.sub(r"^\s*\d+\.\s*", "", s).strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def first_sentence(body, limit=160):
    for para in body.split("\n\n"):
        p = para.strip()
        if not p or p.startswith(("#", "|", "!", "*", "<", "-")):
            continue
        p = re.sub(r"[*_`\\]", "", p).replace("\n", " ").strip()
        if len(p) < 25:
            continue
        s = re.split(r"(?<=\.)\s", p)[0]
        return (s[: limit - 1] + "…") if len(s) > limit else s
    return ""


# split on H1
parts = re.split(r"^# (.+)$", text, flags=re.M)
preamble, sections = parts[0], list(zip(parts[1::2], parts[2::2]))
print(f"sections: {len(sections)}")

DOCS.mkdir(parents=True, exist_ok=True)

# --- introduction page, built from the cover + version history -------------
vh = re.search(r"\*\*Version history\*\*\s*\n\n(\|.*?)(?:\n\n|\Z)", preamble, re.S)
intro = [
    "---",
    'title: "Introduction"',
    'description: "Product guide for ClearTax France e-Invoicing — dashboard, '
    'importing, sales and purchase documents, exceptions, payment reporting '
    'and self-billing."',
    "---",
    "",
    "This guide covers ClearTax France e-Invoicing end to end: the dashboard, "
    "importing documents, sending and receiving invoices, handling exceptions, "
    "reporting payment, and self-billed invoices in both directions.",
    "",
    "## Version history",
    "",
    (vh.group(1).strip() if vh else "_Not available._"),
    "",
]
(DOCS / "introduction.mdx").write_text("\n".join(intro), encoding="utf-8")

pages = [{"file": "introduction", "title": "Introduction"}]
for title, body in sections:
    title = title.strip()
    slug = slugify(title)
    clean_title = re.sub(r"^\s*\d+\.\s*", "", title).strip()
    body_md = transform(body)
    desc = first_sentence(body_md)
    fm = ["---", f'title: "{clean_title}"']
    if desc:
        fm.append(f'description: "{desc}"')
    fm += ["---", "", body_md]
    (DOCS / f"{slug}.mdx").write_text("\n".join(fm), encoding="utf-8")
    pages.append({"file": slug, "title": clean_title})
    print(f"  {slug}.mdx  ({len(body_md.splitlines())} lines)")

# ------------------------------------------------------- documentation.json --
by_slug = {p["file"]: p for p in pages}
GROUPS = [
    ("Getting started", ["introduction", "dashboard-walkthrough",
                         "importing-documents"]),
    ("Selling",         ["sales-documents", "sending-an-invoice",
                         "when-something-goes-wrong", "reporting-payment"]),
    ("Buying",          ["purchase-documents", "reviewing-a-purchase-invoice"]),
    ("Self-billing",    ["self-billed-invoices-you-issue",
                         "self-billed-invoices-you-receive"]),
]

placed = {s for _, ss in GROUPS for s in ss}
missing = [p["file"] for p in pages if p["file"] not in placed]
if missing:
    GROUPS.append(("Other", missing))
    print("!! ungrouped pages added to 'Other':", missing)
unknown = [s for _, ss in GROUPS for s in ss if s not in by_slug]
if unknown:
    print("!! nav references missing pages:", unknown)

config = {
    "$schema": "https://documentation.ai/schema.json",
    "name": "ClearTax France e-Invoicing",
    "description": "Product guide for ClearTax France e-Invoicing.",
    "colors": {"primary": "#2D5BE3", "light": "#5B82EA", "dark": "#1E3F9E"},
    "favicon": "/images/favicon.png",
    "navigation": {
        "groups": [
            {"group": g, "pages": [f"docs/{s}" for s in ss if s in by_slug]}
            for g, ss in GROUPS
        ]
    },
    "footer": {"links": []},
}
(BUILD / "documentation.json").write_text(
    json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

# ------------------------------------------------------------------ tidy up --
shutil.rmtree(RAW)

(BUILD / ".gitignore").write_text("_raw/\n.DS_Store\nnode_modules/\n", encoding="utf-8")

total_img = sum(f.stat().st_size for f in IMG.iterdir())
total_mdx = sum(f.stat().st_size for f in DOCS.iterdir())
print(f"\nbuilt at {BUILD}")
print(f"  docs/  {len(list(DOCS.iterdir()))} pages, {total_mdx/1024:.0f} KB")
print(f"  images/ {len(list(IMG.iterdir()))} files, {total_img/1e6:.1f} MB")
