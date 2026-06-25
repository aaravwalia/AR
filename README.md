# Wall AR — “See it on your wall” for canvas & poster prints

AR product previews that let shoppers place a print on their real wall at true
size, in the browser and on phones (iOS Quick Look + Android Scene Viewer).

## What’s here
```
print_to_ar.py      one image + a size -> .glb + .usdz (true scale, auto-crop)
batch_build.py      folder of prints -> every product/size + catalog.json
sizes.json          your product + size config (edit this)
build.sh            one command to regenerate everything
prints/             put your source images here (samples included)
web/
  index.html        customer page: artwork + format + size + AR
  vercel.json       correct MIME/CORS for .glb/.usdz on Vercel
  _headers          same for Netlify / Cloudflare Pages
  models/           generated .glb/.usdz/thumbnails + catalog.json
```

## Quick start
```bash
# 1. drop your print images into ./prints  (replace the samples)
# 2. build
./build.sh
# 3. preview
cd web && python3 -m http.server 8000   # open http://localhost:8000
```

## Sizes (edit sizes.json)
Currently configured:
- **Canvas** (oak frame): 12×18, 18×24, 24×36, 30×48, 36×60 in
- **Poster** (unframed): A4, A3

Each size is `["label", width, height, "in"|"mm"]`. Images are **center-cropped**
to each size’s aspect ratio, so one master works across every size.

## Why one model per size
iOS Quick Look and Android Scene Viewer place a model at its authored size — they
can’t rescale at launch. So every size is its own ~9 KB file and the size selector
swaps to the matching one. True-size AR on every platform.

## Deploy
Host the `web/` folder. On Vercel (set the project root to `web/`), `vercel.json`
sets the right content-type and CORS so AR loads correctly. Cloudflare Pages /
Netlify use `_headers`. Avoid plain GitHub Pages for the models — it won’t serve
`.usdz` with the content-type iOS needs.
