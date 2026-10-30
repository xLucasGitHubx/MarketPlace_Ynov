# Itération 7 — Le Grand Saut : déploiement Azure Container Apps

> Statut : chaîne prête (CI + script). L'URL publique sera ajoutée ici après le premier déploiement.

## Architecture de déploiement

```
git push main ──► GitHub Actions ──► tests pytest
                                  └► docker build (runtime-onnx) ──► ghcr.io/xlucasgithubx/marketplace_ynov:latest
                                                                     └► smoke test : 401 sans token, 200 avec
Azure Cloud Shell ──► scripts/deploy_azure.sh ──► Azure Container Apps (France Central)
                                                   image tirée de GHCR, HTTPS public,
                                                   API_TOKEN en secret, scale 0 → 3 répliques
```

## Choix et justifications

| Choix | Pourquoi |
| --- | --- |
| **Azure Container Apps**, plan Consommation | Conteneur serverless : HTTPS fourni, scale à zéro, offre gratuite mensuelle (180 000 vCPU-s, 2 M requêtes). Couvert par le crédit Azure for Students de 100 $. |
| **Image construite par GitHub Actions** et publiée sur **GHCR** | Les abonnements étudiants ne peuvent pas utiliser ACR Tasks (`az acr build` → `TasksOperationsNotAllowed`). Un registre ACR Basic coûterait ~5 $/mois, GHCR est gratuit. La CI teste aussi l'image avant de la publier. |
| **1 vCPU / 2 Gio** | Configuration mesurée à l'it. 5 : ≈ 23 req/s par réplique, p50 68 ms. |
| **Scale HTTP à 4 requêtes simultanées**, max 3 répliques | Au-delà de 4 requêtes simultanées, la p95 dépasse ~300 ms sur 1 vCPU. Le plafond de 3 répliques limite la dépense. |
| **`API_TOKEN` en secret Container Apps** (`secretref:`) | Le token n'est ni dans l'image, ni dans le dépôt, ni affiché dans la configuration. |
| **`min-replicas=0`** par défaut, 1 le jour J | 0 $ hors usage ; 0,78 $/jour pour supprimer le démarrage à froid pendant la soutenance (voir [FINOPS.md](../../FINOPS.md)). |

## Procédure

1. Pousser sur `main` : l'onglet **Actions** du dépôt doit passer au vert (job `image`).
2. Rendre le paquet **public**, une seule fois : GitHub → profil → *Packages* → `marketplace_ynov` → *Package settings* → *Change visibility* → Public. L'image ne contient aucun secret (code public, modèle public). Si le paquet reste privé, passer `GHCR_USER` et `GHCR_TOKEN` (token GitHub avec `read:packages`) au script.
3. Ouvrir [Azure Cloud Shell](https://shell.azure.com) en mode Bash :

```bash
git clone https://github.com/xLucasGitHubx/MarketPlace_Ynov.git && cd MarketPlace_Ynov
export API_TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
echo "$API_TOKEN"                 # à garder pour la démo
./scripts/deploy_azure.sh
```

4. Si la création du groupe de ressources échoue avec `RequestDisallowedByPolicy`, la région n'est pas autorisée par l'abonnement étudiant. Le script affiche les régions permises ; relancer avec `LOCATION=<région> ./scripts/deploy_azure.sh`.

## Preuves à capturer après déploiement

```bash
URL=https://<fqdn affiché par le script>
curl -s $URL/health
curl -s -o /dev/null -w "%{http_code}\n" -F file=@velo.jpg $URL/predict                                   # 401
curl -s -H "Authorization: Bearer $API_TOKEN" -F file=@velo.jpg $URL/predict                             # 200 + JSON
python scripts/load_test.py --url $URL --token $API_TOKEN --mode rate --rate 5 --duration 60 --label azure
```

## Fin de projet

```bash
az group delete --name rg-marketplace-ynov --yes --no-wait     # supprime tout, plus aucune facturation
```
