# Itération 6 — La Barrière : preuves

## Ce qui est en place

| Règle | Implémentation |
| --- | --- |
| Authentification | Bearer token comparé à temps constant (`secrets.compare_digest`) à `API_TOKEN` (plusieurs tokens séparés par des virgules pour la rotation). Aucun token configuré → tout est refusé (*fail closed*). |
| Rejet au plus tôt | `UploadGuardMiddleware` (ASGI) vérifie le token **puis** le `Content-Length` avant de lire le corps : une requête sans token ou trop lourde ne coûte ni bande passante, ni mémoire, ni inférence (401, 411, 413). |
| Swagger | `/docs` et `/health` restent publics ; `/predict` affiche le cadenas « Authorize ». |
| Aucune image sur disque | Starlette écrit normalement les uploads > 1 Mo dans un fichier temporaire : le seuil est relevé au-dessus de la taille max acceptée, donc l'image reste en RAM. Les octets, l'image PIL et les tenseurs sont libérés après inférence (`del`, `close`). |
| Logs sans données personnelles | Seules les métadonnées sont loguées (catégorie, confiance, statut, latence, modèle). Ni l'image, ni le nom du fichier (qui peut contenir un nom de personne). |
| Secrets | `API_TOKEN` et `HF_TOKEN` en variables d'environnement (`.env` ignoré par Git, `.env.example` versionné) ; le build Docker n'a besoin d'aucun secret (modèle public). En production : secret Container Apps (`secretref:`). |

Tests : `tests/test_it6_security.py` (401 sans token / mauvais schéma / mauvais token, 401 avant 413, fail closed, rotation, **aucun `rollover` du fichier temporaire pour une image de 4,5 Mo**, logs sans nom de fichier).

## Démonstration dans le conteneur

Le conteneur tourne avec un système de fichiers **en lecture seule** (`--read-only`) ; seul `/tmp` est un tmpfs (en RAM), nécessaire au démarrage de PyTorch.

```
$ docker run -d --name mkt --read-only --tmpfs /tmp:size=16m -e API_TOKEN=*** -p 8000:8000 marketplace-api:pytorch

$ curl -s -o /dev/null -w "%{http_code}" -F file=@velo.jpg localhost:8000/predict    # sans token
401
$ curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer faux" -F file=@velo.jpg localhost:8000/predict
401
$ curl -s -H "Authorization: Bearer $API_TOKEN" -F file=@velo.jpg localhost:8000/predict
{"categorie":"Sport et loisirs","titre_suggere":"Vélo","confiance":0.7205,"statut":"auto","top3":[{"label":"bicycle-built-for-two","categorie":"Sport et loisirs","score" ...

# après 40 requêtes authentifiées (dont 20 images de 4.5M qui dépassent le seuil de spool de Starlette)
$ docker diff mkt          # fichiers modifiés dans le conteneur
(vide)
$ docker exec mkt ls -A /tmp | wc -l
1

$ docker logs mkt 2>&1 | grep -E "prediction|auth_refusee" | tail -3
2026-10-30 09:42:28,537 WARNING app.security auth_refusee path=/predict client=172.17.0.1
2026-10-30 09:42:28,547 WARNING app.security auth_refusee path=/predict client=172.17.0.1
2026-10-30 09:42:36,238 INFO app prediction categorie=Vêtements et accessoires confiance=0.102 statut=a_confirmer latence_ms=122.8 modele=resnet50-pytorch-fp32
```

Le seul élément de `/tmp` est `torchinductor_appuser/`, un dossier **vide** créé par l'import de PyTorch au démarrage (présent avant toute requête). Aucune image n'est écrite, ni sur le disque (en lecture seule), ni dans le tmpfs.

Note RGPD : l'adresse IP du client n'apparaît que dans les logs de refus d'authentification (journal de sécurité, intérêt légitime) ; à purger selon une durée de rétention définie en production.
