#!/usr/bin/env bash
# Re-generate the site from a new Word export of the product guide.
#   ./scripts/convert.sh "~/Downloads/ClearTax France e-Invoicing - Product Guide - v2.docx"
set -euo pipefail
SRC="${1:?usage: convert.sh <path-to-docx>}"
BUILD="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
rm -rf "$BUILD/_raw"; mkdir -p "$BUILD/_raw"
cd "$BUILD/_raw"
pandoc "$SRC" --from=docx --to=gfm+pipe_tables --wrap=none \
  --extract-media=. --markdown-headings=atx -o guide.md
cd "$BUILD"
python3 scripts/build-from-docx.py
echo "Done. Review 'git diff', then commit and push."
