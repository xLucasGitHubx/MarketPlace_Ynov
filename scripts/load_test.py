"""Itération 5 : flux continu d'images vers l'API (test de charge).

Simule des vendeurs qui envoient des photos en continu, en tournant sur les
images du jeu de test. Deux modes :

- ramp : montée progressive du nombre d'utilisateurs simultanés (boucle fermée :
         chaque utilisateur renvoie une photo dès qu'il a sa réponse) ;
         montre où l'API sature (débit max, latence qui décroche).
- rate : débit constant imposé (boucle ouverte, N requêtes/s quoi qu'il arrive) ;
         vérifie le critère de la spec : p95 < 500 ms à 10 req/s, < 1 % d'erreurs sur 5 min.

Sorties : CSV de toutes les requêtes, résumé JSON par palier, graphique PNG.

Usage :
    python scripts/load_test.py --url http://localhost:8000 --token $API_TOKEN --mode ramp --users 1,2,5,10,20 --step 30
    python scripts/load_test.py --url http://localhost:8000 --token $API_TOKEN --mode rate --rate 10 --duration 300
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import itertools
import json
import os
import statistics
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
TEST_DIR = ROOT / "data" / "test_set"


def load_images(limit: int | None = None) -> list[tuple[str, bytes]]:
    files = sorted(TEST_DIR.glob("*/*.jpg"))[:limit]
    if not files:
        raise SystemExit("Aucune image : lancer d'abord scripts/build_test_set.py")
    return [(f.name, f.read_bytes()) for f in files]


def pct(values: list[float], p: float) -> float:
    if not values:
        return float("nan")
    s = sorted(values)
    k = (len(s) - 1) * p / 100
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


class Recorder:
    def __init__(self) -> None:
        self.rows: list[dict] = []
        self.t0 = time.perf_counter()

    def add(self, stage: str, start: float, latency_ms: float, status: int, error: str = "") -> None:
        self.rows.append({"palier": stage, "t_s": round(start - self.t0, 3), "latence_ms": round(latency_ms, 1),
                          "status": status, "erreur": error})


async def send(client: httpx.AsyncClient, url: str, image: tuple[str, bytes], rec: Recorder, stage: str) -> None:
    start = time.perf_counter()
    try:
        r = await client.post(url, files={"file": (image[0], image[1], "image/jpeg")})
        rec.add(stage, start, (time.perf_counter() - start) * 1000, r.status_code)
    except Exception as exc:  # timeout, connexion refusée...
        rec.add(stage, start, (time.perf_counter() - start) * 1000, 0, type(exc).__name__)


async def run_ramp(client, url, images, rec, users_levels: list[int], step_s: float) -> None:
    cycle = itertools.cycle(images)
    for users in users_levels:
        stage = f"{users} utilisateur{'s' if users > 1 else ''}"
        deadline = time.perf_counter() + step_s

        async def user():
            while time.perf_counter() < deadline:
                await send(client, url, next(cycle), rec, stage)

        print(f"  palier : {stage} pendant {step_s:.0f} s")
        await asyncio.gather(*(user() for _ in range(users)))


async def run_rate(client, url, images, rec, rate: float, duration_s: float) -> None:
    cycle = itertools.cycle(images)
    stage = f"{rate:g} req/s"
    interval = 1.0 / rate
    tasks = []
    start = time.perf_counter()
    n = 0
    print(f"  débit constant : {stage} pendant {duration_s:.0f} s")
    while (now := time.perf_counter()) - start < duration_s:
        tasks.append(asyncio.create_task(send(client, url, next(cycle), rec, stage)))
        n += 1
        await asyncio.sleep(max(0.0, start + n * interval - time.perf_counter()))
    await asyncio.gather(*tasks)


def summarize(rows: list[dict]) -> list[dict]:
    out = []
    for stage, group in itertools.groupby(rows, key=lambda r: r["palier"]):
        g = list(group)
        ok = [r["latence_ms"] for r in g if r["status"] == 200]
        span = (max(r["t_s"] for r in g) - min(r["t_s"] for r in g)) or 1e-9
        errors = sum(1 for r in g if r["status"] != 200)
        out.append({
            "palier": stage, "requetes": len(g), "debit_req_s": round(len(g) / span, 2),
            "p50_ms": round(pct(ok, 50), 1), "p95_ms": round(pct(ok, 95), 1), "p99_ms": round(pct(ok, 99), 1),
            "moy_ms": round(statistics.mean(ok), 1) if ok else None,
            "erreurs": errors, "taux_erreur_pct": round(100 * errors / len(g), 2),
        })
    return out


def plot(rows: list[dict], summary: list[dict], path: Path, title: str) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True, gridspec_kw={"height_ratios": [3, 2]})
    ok = [r for r in rows if r["status"] == 200]
    ko = [r for r in rows if r["status"] != 200]
    ax1.scatter([r["t_s"] for r in ok], [r["latence_ms"] for r in ok], s=4, alpha=0.35, color="#2f6fdf",
                label="requête OK")
    if ko:
        ax1.scatter([r["t_s"] for r in ko], [r["latence_ms"] for r in ko], s=10, color="#d64545", label="erreur")
    # p50 / p95 glissants sur des fenêtres de 5 s
    win = 5.0
    t_max = max(r["t_s"] for r in rows)
    xs, p50s, p95s, thr = [], [], [], []
    t = 0.0
    while t < t_max:
        w = [r["latence_ms"] for r in ok if t <= r["t_s"] < t + win]
        n_all = sum(1 for r in rows if t <= r["t_s"] < t + win)
        if w:
            xs.append(t + win / 2)
            p50s.append(pct(w, 50))
            p95s.append(pct(w, 95))
            thr.append(n_all / win)
        t += win
    ax1.plot(xs, p50s, color="#1b3d7a", lw=2, label="p50 (5 s)")
    ax1.plot(xs, p95s, color="#e08a00", lw=2, label="p95 (5 s)")
    ax1.axhline(500, color="#d64545", ls="--", lw=1, label="cible p95 = 500 ms")
    ax1.set_ylabel("latence (ms)")
    ax1.set_yscale("log")
    ax1.legend(loc="upper left", fontsize=8, ncol=3)
    ax1.set_title(title)
    ax2.plot(xs, thr, color="#2e7d4f", lw=2)
    ax2.set_ylabel("débit (req/s)")
    ax2.set_xlabel("temps (s)")
    # séparation des paliers
    for s in summary:
        starts = [r["t_s"] for r in rows if r["palier"] == s["palier"]]
        x0 = min(starts)
        for ax in (ax1, ax2):
            ax.axvline(x0, color="#999", lw=0.6, ls=":")
        ax2.annotate(s["palier"], (x0, ax2.get_ylim()[1] * 0.9), fontsize=8, color="#555")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


async def main_async(args) -> None:
    images = load_images()
    url = args.url.rstrip("/") + "/predict"
    headers = {"Authorization": f"Bearer {args.token}"} if args.token else {}
    limits = httpx.Limits(max_connections=200, max_keepalive_connections=200)
    rec = Recorder()
    async with httpx.AsyncClient(headers=headers, timeout=args.timeout, limits=limits) as client:
        # Échauffement (non compté) : évite de mesurer le premier appel à froid
        for img in images[:3]:
            await client.post(url, files={"file": (img[0], img[1], "image/jpeg")})
        rec.t0 = time.perf_counter()
        if args.mode == "ramp":
            await run_ramp(client, url, images, rec, [int(u) for u in args.users.split(",")], args.step)
        else:
            await run_rate(client, url, images, rec, args.rate, args.duration)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    name = f"{args.label}-{args.mode}"
    with (out / f"{name}.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rec.rows[0]))
        w.writeheader()
        w.writerows(rec.rows)
    summary = summarize(rec.rows)
    (out / f"{name}.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    plot(rec.rows, summary, out / f"{name}.png", f"Test de charge — {args.label} — mode {args.mode}")

    print(f"\n{'palier':<16}{'req':>6}{'req/s':>8}{'p50':>8}{'p95':>8}{'p99':>8}{'err %':>7}")
    for s in summary:
        print(f"{s['palier']:<16}{s['requetes']:>6}{s['debit_req_s']:>8}{s['p50_ms']:>8}{s['p95_ms']:>8}"
              f"{s['p99_ms']:>8}{s['taux_erreur_pct']:>7}")
    print(f"\nRésultats : {out}/{name}.(csv|json|png)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--token", default=os.getenv("API_TOKEN"))
    ap.add_argument("--mode", choices=["ramp", "rate"], default="ramp")
    ap.add_argument("--users", default="1,2,5,10,20", help="paliers d'utilisateurs simultanés (mode ramp)")
    ap.add_argument("--step", type=float, default=30, help="durée d'un palier en secondes (mode ramp)")
    ap.add_argument("--rate", type=float, default=10, help="requêtes par seconde (mode rate)")
    ap.add_argument("--duration", type=float, default=300, help="durée en secondes (mode rate)")
    ap.add_argument("--timeout", type=float, default=30)
    ap.add_argument("--label", default="api")
    ap.add_argument("--out", default=str(ROOT / "docs" / "preuves" / "charge"))
    asyncio.run(main_async(ap.parse_args()))


if __name__ == "__main__":
    main()
