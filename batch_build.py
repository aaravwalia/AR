#!/usr/bin/env python3
"""
batch_build.py — Folder of prints -> full AR catalog (all products x all sizes).

Reads sizes.json (the product/size config) and, for every image, builds a
.glb + .usdz per product per size, plus a thumbnail, then writes catalog.json
that the web page reads to drive its product + size selectors.

  python3 batch_build.py ./prints --config sizes.json --out ./web/models
"""
import argparse, os, glob, json, re
from PIL import Image
import print_to_ar as p2a

EXTS = (".jpg", ".jpeg", ".png", ".webp")
slug = lambda s: re.sub(r"[^a-z0-9]+", "", s.lower())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--config", default="sizes.json")
    ap.add_argument("--out", default="./web/models")
    a = ap.parse_args()

    products = json.load(open(a.config))["products"]
    os.makedirs(a.out, exist_ok=True)
    imgs = [f for f in sorted(glob.glob(os.path.join(a.folder, "*"))) if f.lower().endswith(EXTS)]
    if not imgs:
        print("No images in", a.folder); return

    catalog = []
    for path in imgs:
        src = Image.open(path).convert("RGB")
        base = slug(os.path.splitext(os.path.basename(path))[0])
        name = os.path.splitext(os.path.basename(path))[0].replace("_", " ").replace("-", " ").title()

        thumb = src.copy(); thumb.thumbnail((400, 400))
        thumb_name = f"{base}_thumb.jpg"; thumb.save(os.path.join(a.out, thumb_name), quality=82)

        prod_entries = []
        for prod in products:
            sizes_out = []
            for label, w, h, unit in prod["sizes"]:
                cropped = p2a.center_crop_to_ratio(src, w, h)
                w_m, h_m = w * p2a.UNIT_M[unit], h * p2a.UNIT_M[unit]
                tag = f"{base}_{prod['id']}_{slug(label)}"
                tex = os.path.join(a.out, tag + "_tex.png"); cropped.save(tex)
                scene, _, _ = p2a.build(cropped, w_m, h_m, prod["frame"], prod["kind"])
                scene.export(os.path.join(a.out, tag + ".glb"))
                p2a.export_usdz(tex, os.path.join(a.out, tag + ".usdz"), w_m, h_m, prod["frame"], prod["kind"])
                os.remove(tex)
                sizes_out.append({"label": label, "w": w, "h": h, "unit": unit,
                                  "glb": tag + ".glb", "usdz": tag + ".usdz"})
                print(f"  ✓ {name} · {prod['name']} · {label}")
            prod_entries.append({"id": prod["id"], "name": prod["name"],
                                 "frame": prod["frame"], "sizes": sizes_out})
        catalog.append({"id": base, "name": name, "thumb": thumb_name, "products": prod_entries})

    json.dump({"artworks": catalog}, open(os.path.join(a.out, "catalog.json"), "w"), indent=2)
    n = sum(len(p["sizes"]) for art in catalog for p in art["products"])
    print(f"\n✓ {len(imgs)} artwork(s) → {n} models → {a.out}/catalog.json")


if __name__ == "__main__":
    main()
