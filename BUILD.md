# Building all AR models

The `web/models/` folder currently has a sample of 8 artworks (56 models). To build the FULL catalog from all 78 artworks:

```bash
python3 batch_build.py prints_source --config sizes.json --out web/models
```

This will generate **546 models** (~1.5GB) and update `web/models/catalog.json`.

If you have Python installed locally, this takes 30-40 min. On a server, you can run it in the background with:
```bash
nohup python3 batch_build.py prints_source --config sizes.json --out web/models > build.log 2>&1 &
tail -f build.log
```

Once done, commit and push:
```bash
git add web/models
git commit -m "chore: all 546 AR models for 78 artworks"
git push
```
