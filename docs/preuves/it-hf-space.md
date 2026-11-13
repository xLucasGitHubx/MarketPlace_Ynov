# Hugging Face Space `Lulu18/MarketPlaceYnov` — ZeroGPU (distillation)

Preuve / mode d'emploi pour la distillation teacher→student hors Azure.  
Le runtime **prod Azure reste ONNX-only / CPU** ; le Space porte uniquement les jobs GPU (KD + éventuellement CLIP lourd).

**Pas besoin de tester l'app en local** : création + push HF + premier run dans l'UI du Space suffisent.

## Contexte

| Élément | Valeur |
| --- | --- |
| Space | **`Lulu18/MarketPlaceYnov`** (compte Hugging Face **Lulu18**, Academia Ynov) |
| SDK | **Gradio** (Blank) — **pas Docker** (Docker Space = payant ; ZeroGPU = Gradio only) |
| Hardware | **ZeroGPU** (GPU à la demande) |
| Budget | **≈ 40 minutes GPU / jour** (quota Academia / PRO) |
| Package repo | `spaces/marketplace-ynov/` |
| Teacher | `microsoft/resnet-50` (logits ImageNet, gelé) |
| Student | `facebook/mobilenet_v3_small` |
| Artefact catalogue | ID API `student-kd-mobilenet-int8` → `student-kd-mobilenet-int8-static.onnx` |

Azure Container Apps ne charge **jamais** PyTorch / transformers pour la prod. Les poids distillés sont exportés en ONNX int8 puis embarqués dans l'image slim.

## Checklist — création Space sans local

### A. Formulaire « Create a new Space » (confirmation)

| Champ | Valeur recommandée |
| --- | --- |
| Owner | **Lulu18** |
| Space name | **MarketPlaceYnov** |
| License | **mit** |
| Select the Space SDK | **Gradio** |
| Space template | **Blank** |
| Space hardware | **ZeroGPU** (Free) — *ne pas* choisir Docker / GPU dédié payant |
| Visibility | Public (ou Private si le formateur le demande) |
| Short description | `KD ResNet→MobileNet ZeroGPU (Ynov marketplace)` |

Après **Create Space**, l'URL attendue est :  
`https://huggingface.co/spaces/Lulu18/MarketPlaceYnov`

### B. Après Create — uploader les fichiers (sans test local)

Le package prêt à pousser est dans le dépôt Ynov : **`spaces/marketplace-ynov/`**.

Fichiers à avoir à la racine du Space :

- `app.py`
- `requirements.txt`
- `README.md` (carte Space avec frontmatter YAML)
- `distill_student.py`
- `preprocessing.py`
- `data/test_set/manifest.csv`
- `.gitignore` (optionnel mais recommandé)

#### Option 1 — UI web Hugging Face (le plus simple)

1. Ouvrir le Space → onglet **Files**.
2. **Add file** → **Upload files** (ou créer fichiers un par un).
3. Déposer tout le contenu de `spaces/marketplace-ynov/` (garder la structure `data/test_set/manifest.csv`).
4. Commit message suggéré : `feat(space): Gradio KD ZeroGPU MarketPlace Ynov`.
5. Attendre le **Building** → **Running** (logs : onglet **Logs**).

#### Option 2 — `git clone` + `git push` (Cloud Shell / autre machine OK)

Le push git vers HF est OK même si on refuse de tester l'app en local.

```bash
# 1. Token write : https://huggingface.co/settings/tokens
# 2. Cloner le Space vide
git clone https://huggingface.co/spaces/Lulu18/MarketPlaceYnov
cd MarketPlaceYnov

# 3. Copier le package depuis le dépôt Ynov (ajuster le chemin source)
cp -r /chemin/vers/MarketPlace_Ynov/spaces/marketplace-ynov/* .
# sous Windows (Git Bash) : cp -r "/c/Users/.../MarketPlace_Ynov/spaces/marketplace-ynov/." .

git add app.py requirements.txt README.md distill_student.py preprocessing.py \
        data .gitignore
git status   # vérifier : PAS de .env, PAS de secrets, PAS de gros .onnx/.pt
git commit -m "feat(space): Gradio KD ZeroGPU MarketPlace Ynov"
git push
```

Alternative CLI HF (si `hf` installé) :

```bash
hf upload Lulu18/MarketPlaceYnov spaces/marketplace-ynov . --repo-type=space
```

### C. Settings Space (après le premier build)

1. **Hardware** = **ZeroGPU** (si le formulaire ne l'a pas déjà fixé).
2. Secrets (optionnel) : `HF_TOKEN` seulement si modèles privés — ResNet / MobileNet publics → inutile.
3. Ne pas coller de token Azure / `API_TOKEN` dans le Space (inutile pour la KD).

### D. Premier run dans l'UI du Space

1. Ouvrir l'onglet **App**.
2. Cliquer **Dry-run (sans GPU)** → doit afficher le plan JSON + `distill_meta.json` **sans** consommer le quota.
3. Laisser les défauts sûrs : epochs **2**, images **2000**, max minutes **35**, batch **32**, reprise **vide**.
4. Cliquer **Lancer la distillation (ZeroGPU)** — le statut doit passer *file ZeroGPU → GPU alloué → logs* (jamais silencieux) ; compter **jusqu'à ~35 min**.
5. Si le log indique un arrêt sur budget (`timed_out`) : le lendemain, renseigner `models/distill/last.pt` et relancer.
6. Quand un `best.pt` existe : cocher export + quantize, ou utiliser **Export seul (CPU)**.
7. Télécharger les fichiers listés sous **Artefacts téléchargeables**.

### E. Budget GPU (minutes)

| Règle | Détail |
| --- | --- |
| Quota journalier | ≈ **40 min** (Academia / PRO) |
| Session UI | **≤ 35 min** (`max_minutes`, défaut) |
| Dry-run | **0 min GPU** |
| Export / quantize CPU | hors décorateur ZeroGPU (négligeable) |
| Reprise | `--resume` / champ « Reprise checkpoint » le jour suivant |

Ne pas lancer CLIP bench + distillation le même jour sans surveiller le compteur ZeroGPU.

### F. Récupérer le student ONNX pour Azure

1. Dans l'UI Space, télécharger :
   - `student-kd-mobilenet-int8-static.onnx` (principal)
   - `student-kd-mobilenet-int8.onnx` (alias, si présent)
2. Dans le dépôt MarketPlace_Ynov, copier vers **`artifacts/onnx/`** (build Docker) ou `models/onnx/` (run local).
3. Rebuild image Azure ONNX-only (`docker build --target runtime-onnx …`) puis redeploy si besoin.
4. Vérifier le catalogue API : modèle **`student-kd-mobilenet-int8`** en statut `ready`.
5. Évaluation CPU (hors Space, optionnel) :

```bash
python scripts/evaluate.py --backend onnx \
  --onnx-path models/onnx/student-kd-mobilenet-int8-static.onnx
```

Les `.onnx` restent **gitignorés** : ne pas les committer ; stocker via release / copie manuelle dans le build.

## Pourquoi Gradio (pas Docker)

| | Gradio + ZeroGPU | Docker Space |
| --- | --- | --- |
| Coût Academia | Free (ZeroGPU) | Souvent **Paid** |
| ZeroGPU | **Oui** (Gradio only) | **Non** |
| Package | `spaces/marketplace-ynov/` | `spaces/distill/` (legacy) |

## Contenu du package `spaces/marketplace-ynov/`

| Fichier | Rôle |
| --- | --- |
| `app.py` | UI Gradio : dry-run, train `@spaces.GPU`, export |
| `distill_student.py` | Script KD vendored (même logique que `scripts/distill_student.py`) |
| `preprocessing.py` | `to_model_input` minimal (ImageNet) |
| `data/test_set/manifest.csv` | Exclusion Caltech déjà dans le jeu de test |
| `requirements.txt` | torch, torchvision, transformers, … (**sans** pinner `gradio` / `spaces`) |
| `README.md` | Carte HF (`sdk: gradio`, `app_file: app.py`, `python_version: "3.12"`) |

Le script vendored fixe `ROOT` sur la racine du Space (plus `parents[1]` du monorepo).

## Lancer la distillation (référence CLI)

Depuis la racine du **Space** (terminal HF, optionnel — l'UI couvre le même flux) :

```bash
python distill_student.py --dry-run

python distill_student.py \
  --epochs 2 \
  --max-images 3000 \
  --batch-size 32 \
  --max-minutes 35 \
  --checkpoint-dir models/distill \
  --cache-dir /data/hf

python distill_student.py \
  --resume models/distill/last.pt \
  --max-minutes 35 \
  --checkpoint-dir models/distill

python distill_student.py \
  --resume models/distill/best.pt \
  --skip-train \
  --export-onnx \
  --quantize \
  --onnx-dir models/onnx
```

| Flag | Rôle |
| --- | --- |
| `--max-minutes 35` | Stop propre + checkpoint avant fin de quota |
| `--resume …/last.pt` | Reprend epoch / optimizer / `global_step` |
| `--export-onnx --quantize` | Produit `student-kd-mobilenet-int8-static.onnx` (+ alias) |

## Artefacts attendus

| Fichier | Rôle |
| --- | --- |
| `models/distill/last.pt` | Dernier checkpoint (reprise) |
| `models/distill/best.pt` | Meilleure loss moyenne d'epoch |
| `models/distill/distill_meta.json` | Config, steps, temps, hint de reprise |
| `models/onnx/student-kd-mobilenet-fp32.onnx` | Export fp32 du student |
| `models/onnx/student-kd-mobilenet-int8-static.onnx` | Prod catalogue (QDQ) |
| `models/onnx/student-kd-mobilenet-int8.onnx` | Alias accepté par `app/registry.py` |

## Handoff vers le catalogue

1. Distiller (+ reprendre) sur Space jusqu'à 1–3 epochs complètes.
2. Export + quantize → fichiers int8 ci-dessus.
3. Copier les int8 dans `artifacts/onnx/` pour le `COPY` Docker Azure.
4. Commit **uniquement** preuve / métriques (pas les `.onnx`).

## Ce qui n'est pas fait ici

- Pas de fine-tuning ImageNet complet ni dataset propriétaire massif.
- Pas de modification de l'image Docker Azure (prod reste slim ONNX).
- Pas de test local Docker / pytest de toute l'API pour valider le Space.
- CLIP `space_only` : job séparé possible plus tard (`scripts/benchmark_clip.py`).
