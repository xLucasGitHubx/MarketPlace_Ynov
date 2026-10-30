"""Étape 9 du pipeline : journalisation de chaque requête dans MLflow.

Activé uniquement si MLFLOW_TRACKING_URI est défini. Chaque instance de l'API
ouvre un run MLflow (expérience « marketplace-api-requests ») et y envoie, par
lots et en arrière-plan, les métriques de chaque prédiction :

- latence_ms, confiance, statut_auto (1 = auto, 0 = à confirmer) ;
- nb_<categorie> : compteur cumulé par catégorie prédite.

Jamais d'image, de nom de fichier ni d'identifiant client : uniquement des chiffres.
Deux transports : API REST MLflow en urllib pour les URI http(s) (production,
aucune dépendance ajoutée à l'image), paquet `mlflow` pour les URI locales.
L'envoi est asynchrone (file + thread) : une panne de MLflow ne ralentit ni ne
casse l'API, les métriques sont simplement perdues et un avertissement est logué.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
import unicodedata
from dataclasses import dataclass

logger = logging.getLogger(__name__)

EXPERIMENT = "marketplace-api-requests"


def slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return "_".join("".join(c if c.isalnum() else " " for c in text).split())


@dataclass
class RequestRecord:
    latency_ms: float
    confidence: float
    category: str
    status: str
    timestamp_ms: int


class NullTracker:
    enabled = False

    def record(self, *args, **kwargs) -> None:  # noqa: D401
        pass

    def close(self) -> None:
        pass


class _RestBackend:
    """Client minimal de l'API REST MLflow (urllib, sans dépendance).

    Utilisé pour les URI http(s) : l'image de production n'a pas besoin du
    paquet mlflow (des dizaines de dépendances) pour envoyer quelques métriques.
    """

    def __init__(self, uri: str, timeout: float = 5.0):
        self.base = uri.rstrip("/") + "/api/2.0/mlflow"
        self.timeout = timeout

    def _call(self, method: str, path: str, payload: dict | None = None) -> dict:
        import json
        import urllib.parse
        import urllib.request

        url = f"{self.base}/{path}"
        data = None
        if method == "GET" and payload:
            url += "?" + urllib.parse.urlencode(payload)
        elif payload is not None:
            data = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:  # noqa: S310 (URI de configuration)
            body = r.read()
        return json.loads(body) if body else {}

    def start_run(self, experiment: str, run_name: str, tags: dict, params: dict) -> str:
        import urllib.error

        try:
            exp_id = self._call("GET", "experiments/get-by-name", {"experiment_name": experiment})["experiment"][
                "experiment_id"
            ]
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                raise
            exp_id = self._call("POST", "experiments/create", {"name": experiment})["experiment_id"]
        run = self._call("POST", "runs/create", {
            "experiment_id": exp_id, "run_name": run_name, "start_time": int(time.time() * 1000),
            "tags": [{"key": k, "value": v} for k, v in tags.items()],
        })
        run_id = run["run"]["info"]["run_id"]
        self._call("POST", "runs/log-batch", {"run_id": run_id,
                                               "params": [{"key": k, "value": v} for k, v in params.items()]})
        return run_id

    def log_metrics(self, run_id: str, metrics: list[dict]) -> None:
        self._call("POST", "runs/log-batch", {"run_id": run_id, "metrics": metrics})

    def terminate(self, run_id: str) -> None:
        self._call("POST", "runs/update", {"run_id": run_id, "status": "FINISHED",
                                            "end_time": int(time.time() * 1000)})


class _ClientBackend:
    """Backend via le paquet mlflow (URI locales : sqlite:///..., file:...)."""

    def __init__(self, uri: str):
        from mlflow.tracking import MlflowClient

        self.client = MlflowClient(tracking_uri=uri)

    def start_run(self, experiment: str, run_name: str, tags: dict, params: dict) -> str:
        exp = self.client.get_experiment_by_name(experiment)
        exp_id = exp.experiment_id if exp else self.client.create_experiment(experiment)
        run_id = self.client.create_run(exp_id, run_name=run_name, tags=tags).info.run_id
        for k, v in params.items():
            self.client.log_param(run_id, k, v)
        return run_id

    def log_metrics(self, run_id: str, metrics: list[dict]) -> None:
        from mlflow.entities import Metric

        self.client.log_batch(run_id, metrics=[Metric(m["key"], m["value"], m["timestamp"], m["step"])
                                               for m in metrics])

    def terminate(self, run_id: str) -> None:
        self.client.set_terminated(run_id)


class MlflowRequestTracker:
    enabled = True

    def __init__(self, tracking_uri: str, model_name: str, app_version: str, flush_interval: float = 2.0):
        is_http = tracking_uri.startswith(("http://", "https://"))
        self.backend = _RestBackend(tracking_uri) if is_http else _ClientBackend(tracking_uri)
        self.run_id = self.backend.start_run(
            EXPERIMENT,
            run_name=f"api-{model_name}-{time.strftime('%Y%m%d-%H%M%S')}",
            tags={"type": "api", "modele": model_name, "version_api": app_version},
            params={"modele": model_name, "version_api": app_version},
        )

        self._queue: queue.Queue[RequestRecord | None] = queue.Queue(maxsize=10_000)
        self._step = 0
        self._counts: dict[str, int] = {}
        self._flush_interval = flush_interval
        self._thread = threading.Thread(target=self._worker, name="mlflow-tracker", daemon=True)
        self._thread.start()
        logger.info("Suivi MLflow actif : %s (run %s)", tracking_uri, self.run_id)

    def record(self, latency_ms: float, confidence: float, category: str, status: str) -> None:
        try:
            self._queue.put_nowait(RequestRecord(latency_ms, confidence, category, status, int(time.time() * 1000)))
        except queue.Full:
            pass  # on préfère perdre une métrique que bloquer une requête

    def _to_metrics(self, records: list[RequestRecord]) -> list[dict]:
        def metric(key: str, value: float, ts: int, step: int) -> dict:
            return {"key": key, "value": float(value), "timestamp": ts, "step": step}

        metrics = []
        for r in records:
            self._step += 1
            self._counts[r.category] = self._counts.get(r.category, 0) + 1
            ts, s = r.timestamp_ms, self._step
            metrics += [
                metric("latence_ms", r.latency_ms, ts, s),
                metric("confiance", r.confidence, ts, s),
                metric("statut_auto", 1.0 if r.status == "auto" else 0.0, ts, s),
                metric(f"nb_{slug(r.category)}", self._counts[r.category], ts, s),
            ]
        metrics.append(metric("nb_requetes", self._step, records[-1].timestamp_ms, self._step))
        return metrics

    def _flush(self, records: list[RequestRecord]) -> None:
        if not records:
            return
        metrics = self._to_metrics(records)
        try:
            for i in range(0, len(metrics), 1000):  # limite MLflow : 1000 métriques par lot
                self.backend.log_metrics(self.run_id, metrics[i : i + 1000])
        except Exception as exc:  # MLflow indisponible : l'API continue
            logger.warning("Envoi MLflow impossible (%s) : %d requêtes non journalisées", type(exc).__name__, len(records))

    def _worker(self) -> None:
        buffer: list[RequestRecord] = []
        last = time.monotonic()
        while True:
            try:
                item = self._queue.get(timeout=0.5)
            except queue.Empty:
                item = ...
            if item is None:  # arrêt demandé
                self._flush(buffer)
                return
            if isinstance(item, RequestRecord):
                buffer.append(item)
            if buffer and (time.monotonic() - last >= self._flush_interval or len(buffer) >= 200):
                self._flush(buffer)
                buffer, last = [], time.monotonic()

    def close(self) -> None:
        self._queue.put(None)
        self._thread.join(timeout=10)
        try:
            self.backend.terminate(self.run_id)
        except Exception:
            pass


def create_tracker(tracking_uri: str | None, model_name: str, app_version: str):
    if not tracking_uri:
        return NullTracker()
    try:
        return MlflowRequestTracker(tracking_uri, model_name, app_version)
    except Exception as exc:
        logger.warning("MLflow indisponible au démarrage (%s) : suivi des requêtes désactivé", type(exc).__name__)
        return NullTracker()
