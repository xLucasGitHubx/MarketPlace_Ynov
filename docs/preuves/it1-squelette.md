## Itération 1 — preuve

```
$ curl -s localhost:8000/health
{"status":"ok","version":"0.1.0"}
$ curl -s -o /dev/null -w "%{http_code}" localhost:8000/docs
200
$ curl -s -F file=@demo.jpg localhost:8000/predict
{"filename":"demo.jpg","mime_type":"image/jpeg","taille_octets":8229,"largeur":800,"hauteur":600}
```
