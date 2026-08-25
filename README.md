# ClearTax France e-Invoicing — Product Guide

Source for the customer-facing product guide published on Documentation.AI.

## Layout

```
documentation.json      site config — name, colours, navigation groups
docs/                   11 MDX pages
images/                 66 screenshots
scripts/                regeneration from the Word source
```

## Editing

Two ways, and they don't mix well — pick one per revision.

**Edit the MDX directly.** Change files under `docs/`, commit, push. Documentation.AI
picks up the change and rebuilds. Every pull request gets its own preview build.

**Re-export from Word.** The guide is authored in Word. When a new version is
exported, regenerate the whole site:

```bash
./scripts/convert.sh "~/Downloads/ClearTax France e-Invoicing - Product Guide - v2.docx"
git diff          # review before committing — the conversion is wholesale
```

This overwrites everything in `docs/` and `images/`. Any hand-edits made to the
MDX since the last conversion are lost. If you have hand-edits worth keeping,
fold them back into the Word source first.

## What the conversion does

1. `pandoc` converts the `.docx` to GitHub-flavoured Markdown, extracting media
2. Splits on `H1` into one page per chapter
3. Demotes all headings one level — the frontmatter `title` becomes the page H1
4. Rewrites `<img>` tags to Markdown images; the figure caption becomes both the
   alt text and a visible italic caption
5. Resizes screenshots to 1600px wide and optimises them (~74% smaller)
6. Derives `title` and `description` frontmatter per page
7. Regenerates `documentation.json` navigation

Requires `pandoc` and Python with `Pillow`.

## Navigation

Navigation lives in `documentation.json`. Page order within a group is the array
order. Adding a chapter to the Word source means adding its slug to the right
group in `scripts/build-from-docx.py` (the `GROUPS` list) — otherwise it lands in
an `Other` group and the script warns.

## Publishing

Connected to Documentation.AI via Git sync. Pushes to the default branch deploy
to the live site.

## Conventions

- Heading numbers from the Word source (`3.4.2 …`) are kept deliberately, so the
  site cross-references against the circulated PDF. To drop them, strip the
  numeric prefix in `transform()`.
- Figure IDs (`[F01]`, `[F02]` …) come from the Word source and are
  customer-visible. Keep them unique.
