#!/usr/bin/env python3
"""
Patch catalog.json ids to match the live GPSFDK product slugs.
Run from the AR folder:  python fix_catalog_slugs.py
Only touches the "id" field of each artwork; filenames stay the same.
"""
import json, os

CATALOG = "web/models/catalog.json"

# catalog id  ->  correct live slug
RENAMES = {
    "flora-obscura":     "flora-obscura-1",
    "the-mystic-s-mask": "the-mystics-mask",
    "the-ruby-magnate":  "the-ruby-magnet",
    "bubblegum-glow":    "bubblegum-glow-1",
    # floral-vermeer and ethereal-drift have no live match yet — left as-is,
    # AR simply won't show for them until their real slug is added here.
}

data = json.load(open(CATALOG, encoding="utf-8"))
changed = 0
for art in data["artworks"]:
    if art["id"] in RENAMES:
        old = art["id"]
        art["id"] = RENAMES[old]
        print(f"  {old}  ->  {art['id']}")
        changed += 1

json.dump(data, open(CATALOG, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"\nPatched {changed} ids in {CATALOG}. Now redeploy:  vercel --prod")
