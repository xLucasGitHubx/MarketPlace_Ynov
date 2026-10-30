# Itération 3 — L'Isolement : preuves

Dockerfile multi-stage (`python:3.11-slim`) : l'étape *builder* installe les dépendances et télécharge ResNet-50 depuis Hugging Face au build ; l'étape *runtime* ne garde que le venv, le modèle (98 Mo) et `app/`, tourne en utilisateur non-root (uid 1000), hors-ligne (`HF_HUB_OFFLINE=1`) et avec un healthcheck.

```bash
docker build -t marketplace-api:pytorch .
docker run -d --name mkt -p 8000:8000 marketplace-api:pytorch
curl -s localhost:8000/health
curl -s -F file=@canape.jpg localhost:8000/predict
```

Résultat :

```
$ docker images marketplace-api:pytorch
marketplace-api:pytorch   2.04GB   (dont venv 1,3 Go : torch + transformers ; modèle 98 Mo)

$ curl -s localhost:8000/health          # prêt 7 s après docker run
{"status":"ok","version":"0.2.0","modele":"resnet50-pytorch-fp32","modele_charge":true}

$ curl -s -F file=@canape.jpg localhost:8000/predict
{"categorie":"Maison et meubles","titre_suggere":"Canapé","confiance":0.9991,"statut":"auto", ...}

$ docker exec mkt id
uid=1000(appuser) gid=1000(appuser)

$ docker history --no-trunc marketplace-api:pytorch | grep -ciE "proxy|token="
0        # aucun secret dans les couches (token HF passé en secret de build)
```

**Constat :** l'image PyTorch pèse 2.04GB, dont 1,3 Go pour torch. C'est le problème que l'itération 4 traite : l'image ONNX n'embarque que ONNX Runtime.

Secrets de build optionnels :
- `--secret id=hf_token,env=HF_TOKEN` : token Hugging Face (inutile pour `microsoft/resnet-50`, public) ;
- `--secret id=ca_bundle,src=ca.crt` : certificat d'un proxy d'entreprise qui intercepte le TLS.
