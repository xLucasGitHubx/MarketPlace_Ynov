# Itération 4 — L'Optimisation : preuves

## Ce qui a été fait

1. **Export ONNX** de ResNet-50 (`scripts/export_onnx.py`, opset 17, batch dynamique).
2. **Deux quantizations int8** comparées :
   - *dynamique* (poids int8, activations quantifiées à la volée) ;
   - *statique QDQ* (poids **et** activations int8, par canal), calibrée sur 64 images Caltech-256 **exclues du jeu de test**.
3. **Prétraitement réécrit en numpy** (`app/preprocessing.to_model_input`) : identique à l'`AutoImageProcessor` (écart max 0,0 vérifié par un test), ce qui permet de **retirer PyTorch et transformers de l'image de production**.
4. **Bascule par variable d'environnement** : `MODEL_BACKEND=pytorch|onnx`, `ONNX_MODEL_PATH=...`. Une seule interface `Predictor`, la logique métier ne change pas.
5. **Dockerfile à deux cibles** : `runtime-pytorch` (référence) et `runtime-onnx` (défaut). L'export et la calibration tournent dans une étape de build ; l'image finale n'a que ONNX Runtime.

## Résultats (même jeu de 200 photos, même machine : 2 vCPU, CPU only)

| Variante | Taille du modèle | Accuracy catégorie | Latence p50 | Latence p95 |
| --- | --- | --- | --- | --- |
| PyTorch fp32 (référence) | 97,7 Mo | 69,0 % | 105 ms | 142 ms |
| ONNX fp32 | 97,4 Mo | 69,0 % | 56 ms | 73 ms |
| ONNX int8 dynamique | 24,6 Mo | 62,0 % | 359 ms | 443 ms |
| **ONNX int8 statique (retenu)** | **24,9 Mo** | **68,5 %** | **21,5 ms** | **28,6 ms** |

| Image Docker | Taille | RAM au repos | Démarrage | `--read-only` sans tmpfs |
| --- | --- | --- | --- | --- |
| `marketplace-api:pytorch` | 2,04 Go | 276 Mo | ~7 s | non (PyTorch écrit dans /tmp) |
| **`marketplace-api:onnx`** | **551 Mo** | **157 Mo** | **1,6 s** | **oui** |

## Critères de la spec

| Critère | Cible | Mesuré | |
| --- | --- | --- | --- |
| Taille du modèle | ÷ 3 ou plus | ÷ 3,9 (97,7 → 24,9 Mo) | ✅ |
| Latence CPU | −40 % ou plus | −80 % p50 (105 → 21,5 ms), −80 % p95 | ✅ |
| Perte d'accuracy | ≤ 2 points | −0,5 point (69,0 → 68,5 %) | ✅ |
| Image Docker | légère | ÷ 3,7 (2,04 Go → 551 Mo) | ✅ |

## Ce qu'on en retient

- **L'export ONNX seul** divise déjà la latence par 2 (graphe optimisé, pas de surcoût Python/PyTorch), sans perte.
- **La quantization dynamique est un piège pour un CNN** : ONNX Runtime remplace les convolutions par `ConvInteger`, peu optimisé sur CPU, et requantifie les activations à chaque couche. Résultat : 3× plus lent que PyTorch et −7 points d'accuracy. Elle est faite pour les Transformers (couches `MatMul`).
- **La quantization statique** calibre les plages d'activation une fois pour toutes : convolutions en int8 de bout en bout, d'où le gain ×5 en latence pour une perte négligeable.
- Repli prévu par la spec : si la quantization dégradait trop, `resnet50-fp32.onnx` reste disponible (`ONNX_MODEL_PATH`).

Fichiers de mesure : `docs/preuves/eval/` (`eval-onnx-*.json`, `onnx-export-report.json`).

```bash
python scripts/export_onnx.py                      # génère models/onnx/*.onnx
python scripts/evaluate.py --backend onnx --onnx-path models/onnx/resnet50-int8-static.onnx
docker build --target runtime-onnx -t marketplace-api:onnx .
```
