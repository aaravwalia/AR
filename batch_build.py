#!/usr/bin/env python3
"""
batch_build.py — Suite folders → full AR catalog (all products x all sizes).

Processes nested folder structure:
  all_prints/
    After Hours Suite/
      Electric Shout.png
      The Double Pour.jpg
      ...
    Celestial Frontier/
      ...

Generates .glb + .usdz per artwork/size, thumbnails, and catalog.json.
"""
import argparse, os, glob, json, re
from pathlib import Path
from PIL import Image
import print_to_ar as p2a

EXTS = (".jpg", ".jpeg", ".png", ".webp")
slug = lambda s: re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", help="root folder containing suite folders")
    ap.add_argument("--config", default="sizes.json")
    ap.add_argument("--out", default="./web/models")
    a = ap.parse_args()

    products = json.load(open(a.config))["products"]
    os.makedirs(a.out, exist_ok=True)

    catalog = []
    suite_folders = sorted([d for d in Path(a.folder).iterdir() if d.is_dir()])

    for suite_dir in suite_folders:
        imgs = sorted([f for f in suite_dir.iterdir() 
                      if f.suffix.lower() in EXTS])
        if not imgs:
            continue

        suite_name = suite_dir.name
        for img_path in imgs:
            src = Image.open(img_path).convert("RGB")
            base = slug(img_path.stem)
            name = img_path.stem.replace("_", " ").title()

            # Thumbnail
            thumb = src.copy(); thumb.thumbnail((400, 400))
            thumb_name = f"{base}_thumb.jpg"
            thumb.save(os.path.join(a.out, thumb_name), quality=82)

            prod_entries = []
            for prod in products:
                sizes_out = []
                for label, w, h, unit in prod["sizes"]:
                    cropped = p2a.center_crop_to_ratio(src, w, h)
                    w_m, h_m = w * p2a.UNIT_M[unit], h * p2a.UNIT_M[unit]
                    tag = f"{base}_{prod['id']}_{slug(label)}"
                    tex = os.path.join(a.out, tag + "_tex.png")
                    cropped.save(tex)
                    scene, _, _ = p2a.build(cropped, w_m, h_m, prod["frame"], prod["kind"])
                    scene.export(os.path.join(a.out, tag + ".glb"))
                    p2a.export_usdz(tex, os.path.join(a.out, tag + ".usdz"), 
                                   w_m, h_m, prod["frame"], prod["kind"])
                    os.remove(tex)
                    sizes_out.append({
                        "label": label, "w": w, "h": h, "unit": unit,
                        "glb": tag + ".glb", "usdz": tag + ".usdz"
                    })
                    print(f"  ✓ {name} · {prod['name']} · {label}")
                prod_entries.append({
                    "id": prod["id"], "name": prod["name"],
                    "frame": prod["frame"], "sizes": sizes_out
                })
            catalog.append({
                "id": base, "name": name, "suite": suite_name, 
                "thumb": thumb_name, "products": prod_entries
            })

    json.dump({"artworks": catalog}, 
              open(os.path.join(a.out, "catalog.json"), "w"), indent=2)
    n = sum(len(p["sizes"]) for art in catalog for p in art["products"])
    print(f"\n✓ {len(catalog)} artwork(s) → {n} models → {a.out}/catalog.json")


if __name__ == "__main__":
    main()
