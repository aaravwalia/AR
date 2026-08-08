#!/usr/bin/env bash
# Regenerate all AR models + catalog from the images in ./prints
set -e
pip install -r requirements.txt
python3 batch_build.py ./prints --config sizes.json --out ./web/models
echo ""
echo "Built. Preview locally:  (cd web && python3 -m http.server 8000)  ->  http://localhost:8000"
