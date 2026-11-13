---
title: MarketPlace Ynov — Distillation KD
emoji: 🧪
colorFrom: gray
colorTo: blue
sdk: gradio
sdk_version: 5.50.0
app_file: app.py
python_version: "3.12"
short_description: KD ResNet→MobileNet ZeroGPU (Ynov)
pinned: false
license: mit
---

# MarketPlace Ynov — Distillation ZeroGPU

Space **Gradio + ZeroGPU** (compte **Lulu18**, Academia Ynov).

Ce Space **n'est pas** l'API Azure de production.  
Prod = image slim `onnxruntime` CPU :  
`https://marketplace-api.whitepond-81c2f971.swedencentral.azurecontainerapps.io`

Ici = job GPU pour distiller **ResNet-50 → MobileNetV3-Small** (Knowledge Distillation), puis exporter un student ONNX int8 pour le catalogue API.

## Hardware

Dans **Settings → Hardware** du Space : choisir **ZeroGPU**.  
(Le champ `hardware:` dans le YAML est ignoré par HF — régler via l'UI ou `hf spaces settings`.)

Quota Academia / PRO : **≈ 40 min GPU / jour**. Viser **≤ 35 min** par session.

## Contenu du dépôt Space

| Fichier | Rôle |
| --- | --- |
| `app.py` | UI Gradio (dry-run, train, export) |
| `distill_student.py` | Script KD (vendored depuis le repo Ynov) |
| `preprocessing.py` | Prétraitement ImageNet minimal |
| `data/test_set/manifest.csv` | Indices Caltech exclus (hors jeu de test) |
| `requirements.txt` | Dépendances (sans pinner `gradio` / `spaces`) |

## Usage UI

1. **Dry-run** — plan + chemins d'artefacts, **sans GPU** ni téléchargement.
2. **Lancer la distillation** — défauts sûrs : 2 epochs, 3000 images, **max 35 min**.
3. Si timeout : relancer avec reprise `models/distill/last.pt` le lendemain.
4. **Export ONNX + int8** — produit `student-kd-mobilenet-int8-static.onnx`.
5. Télécharger l'artefact depuis l'UI → copier dans le build Azure / `artifacts/onnx/`.

## CLI (terminal Space, optionnel)

```bash
python distill_student.py --dry-run

python distill_student.py \
  --epochs 2 --max-images 3000 --max-minutes 35 \
  --checkpoint-dir models/distill --cache-dir /data/hf

python distill_student.py --resume models/distill/best.pt \
  --skip-train --export-onnx --quantize --onnx-dir models/onnx
```

## Doc complète (repo)

Voir `docs/preuves/it-hf-space.md` dans le dépôt MarketPlace_Ynov.
