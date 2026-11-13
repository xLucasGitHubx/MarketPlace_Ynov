---
title: MarketPlace Ynov — Distillation KD
emoji: 🧪
colorFrom: gray
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# Space distillation — user `Lulu18` (legacy Docker)

**Ce dossier n'est pas l'image Azure de production.**  
Prod = `Dockerfile` à la racine du repo (`onnxruntime` CPU, slim).

> **Recommandé (gratuit ZeroGPU)** : package Gradio sous  
> [`spaces/marketplace-ynov/`](../marketplace-ynov/) → Space `Lulu18/MarketPlaceYnov`.  
> Les Spaces **Docker** ne supportent **pas** ZeroGPU (et le SDK Docker est souvent payant).  
> Garder ce dossier uniquement comme référence historique / job Docker dédié.

Doc complète : [`docs/preuves/it-hf-space.md`](../../docs/preuves/it-hf-space.md).

## Réglages Space (legacy Docker)

1. Compte / org : **Lulu18** (Academia Ynov).
2. Hardware : GPU dédié facturé (pas ZeroGPU) si SDK Docker.
3. SDK : **Docker**, build context = **racine du dépôt** :
   - Fichier Docker : `spaces/distill/Dockerfile`
   - Ou dupliquer ce README + Dockerfile à la racine du Space et monter le repo.

## Commandes

```bash
# Smoke (pas de téléchargement modèle)
python scripts/distill_student.py --dry-run

# Entraînement (tenir ≤ 35 min)
python scripts/distill_student.py \
  --epochs 2 --max-images 3000 --max-minutes 35 \
  --checkpoint-dir models/distill --cache-dir /data/hf

# Reprise + export int8 catalogue
python scripts/distill_student.py --resume models/distill/best.pt \
  --skip-train --export-onnx --quantize --onnx-dir models/onnx
```

Artefact catalogue : `student-kd-mobilenet-int8`  
→ `models/onnx/student-kd-mobilenet-int8-static.onnx`

## Budget

Laisser une marge (`--max-minutes 35`) : le script checkpoint et s'arrête proprement ; reprendre le lendemain avec `--resume models/distill/last.pt`.
