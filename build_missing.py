#!/usr/bin/env python3
"""
build_missing.py — generate AR models for store products that don't have them.

Compares the live AR catalog against the store's product list, then builds
.glb + .usdz (every format x size) for whatever is missing, straight from each
product's Cloudinary master image.

Catalog entries are keyed by the product's real `slug`, which is what the app
matches on — so a product's AR turns on the moment its models are deployed.

  python build_missing.py                 # build everything missing
  python build_missing.py --limit 2       # smoke-test on two products
  python build_missing.py --out web/models
"""
import argparse, io, json, os, re, sys, urllib.request
from PIL import Image
import print_to_ar as p2a

API = "https://gpsfdkrefresh.onrender.com/api/products?categorySlug=wall-canvas&limit=300"
LIVE_CATALOG = "https://ar-sage-eight.vercel.app/models/catalog.json"
slugify = lambda s: re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def fetch_json(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="sizes.json")
    ap.add_argument("--out", default="./web/models")
    ap.add_argument("--limit", type=int, default=0, help="only build N products")
    ap.add_argument("--tex", type=int, default=1600, help="max texture px on the long edge")
    ap.add_argument("--jpeg", action="store_true",
                    help="embed JPEG textures instead of PNG (much smaller, same look)")
    ap.add_argument("--merge", action="store_true", help="merge into the live catalog")
    a = ap.parse_args()

    # encoding="utf-8" matters: Windows defaults to cp1252, which mangles the
    # "×" in the size labels into "Ã—".
    products_cfg = json.load(open(a.config, encoding="utf-8"))["products"]
    os.makedirs(a.out, exist_ok=True)

    store = fetch_json(API)["products"]
    try:
        live = fetch_json(LIVE_CATALOG)["artworks"]
    except Exception as e:
        print(f"! couldn't read live catalog ({e}); assuming nothing exists yet")
        live = []
    have = {x["id"] for x in live}

    missing = [p for p in store if p["slug"] not in have and (p.get("images") or [])]
    skipped = [p["slug"] for p in store if p["slug"] not in have and not (p.get("images") or [])]
    if a.limit:
        missing = missing[: a.limit]

    print(f"store: {len(store)} | live AR: {len(have)} | to build: {len(missing)}")
    if skipped:
        print(f"! {len(skipped)} skipped (no image): {skipped[:5]}")

    built = []
    for n, prod in enumerate(missing, 1):
        base = prod["slug"]                      # key on the REAL store slug
        name = prod["name"]
        url = prod["images"][0]["url"]
        print(f"[{n}/{len(missing)}] {name}  ({base})")
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                src = Image.open(io.BytesIO(r.read())).convert("RGB")
        except Exception as e:
            print(f"   ! image failed, skipping: {e}")
            continue

        thumb = src.copy()
        thumb.thumbnail((400, 400))
        thumb_name = f"{base}_thumb.jpg"
        thumb.save(os.path.join(a.out, thumb_name), quality=82)

        prod_entries = []
        for cfg in products_cfg:
            sizes_out = []
            for label, w, h, unit in cfg["sizes"]:
                cropped = p2a.center_crop_to_ratio(src, w, h).copy()
                cropped.thumbnail((a.tex, a.tex))
                w_m, h_m = w * p2a.UNIT_M[unit], h * p2a.UNIT_M[unit]
                tag = f"{base}_{cfg['id']}_{slugify(label)}"
                tex = os.path.join(a.out, tag + ("_tex.jpg" if a.jpeg else "_tex.png"))
                cropped.save(tex, quality=88) if a.jpeg else cropped.save(tex)
                scene, _, _ = p2a.build(cropped, w_m, h_m, cfg["frame"], cfg["kind"])
                scene.export(os.path.join(a.out, tag + ".glb"))
                p2a.export_usdz(tex, os.path.join(a.out, tag + ".usdz"), w_m, h_m, cfg["frame"], cfg["kind"])
                os.remove(tex)
                sizes_out.append({"label": label, "w": w, "h": h, "unit": unit,
                                  "glb": tag + ".glb", "usdz": tag + ".usdz"})
            prod_entries.append({"id": cfg["id"], "name": cfg["name"],
                                 "frame": cfg["frame"], "sizes": sizes_out})
        built.append({"id": base, "name": name, "suite": prod.get("subCategory", ""),
                      "thumb": thumb_name, "products": prod_entries})

    out_catalog = (live + built) if a.merge else built
    path = os.path.join(a.out, "catalog.json" if a.merge else "catalog.new.json")
    # ensure_ascii keeps the catalog pure ASCII so it can't be mis-decoded by
    # a browser when the server omits charset=utf-8.
    json.dump({"artworks": out_catalog}, open(path, "w", encoding="utf-8"),
              indent=2, ensure_ascii=True)
    print(f"\nbuilt {len(built)} products -> {path} ({len(out_catalog)} total entries)")


if __name__ == "__main__":
    sys.exit(main())
