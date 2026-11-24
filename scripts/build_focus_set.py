"""Jeu focal séparé : environ 100 photos × 2 catégories.

Catégories : « Véhicules et pièces » et « Jeux et jouets ».
Le manifeste historique `data/test_set/manifest.csv` (20 × 10) n'est pas réécrit.
Les classes viennent de PLAN (scripts/build_test_set.py). Le mapping ImageNet n'est pas lu.

Ordre de tirage, graine 42, round-robin entre classes :
1. split test Caltech-256, hors photos déjà listées dans le manifeste des 200 ;
2. si le quota manque, split validation du même jeu ;
3. s'il manque encore, split train du même jeu (deux shards).

Les deux catégories n'ont aucune classe Stanford Online Products dans PLAN :
le complément reste dans Caltech-256. Aucune photo n'est dupliquée (chemin source, puis SHA-256).

Noms : `focus_caltech_<shard>_<classe>_<index>.jpg` pour ne pas croiser le jeu historique.

Usage : python scripts/build_focus_set.py [--per-category 100]
         python scripts/build_test_set.py --focus
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import http.client
import io
import json
import random
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from typing import NamedTuple
from urllib.parse import urlparse

import pyarrow as pa
import pyarrow.parquet as pq
from PIL import Image

from build_test_set import PLAN, SEED, round_robin, slugify

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "test_set"
HISTORICAL = OUT_DIR / "manifest.csv"
FOCUS_MANIFEST = OUT_DIR / "focus_manifest.csv"
CACHE = ROOT / "models" / "cache"
HF = "https://huggingface.co/datasets/ilee0022/Caltech-256/resolve/main/data"
UA = "marketplace-ynov"

FOCUS = [name for name in PLAN if name in {"Véhicules et pièces", "Jeux et jouets"}]

# (split logique, shard dans le nom de fichier, fichier parquet, taille attendue)
SHARDS: tuple[tuple[str, str, str, int], ...] = (
    ("test", "test", "test-00000-of-00001.parquet", 118_528_811),
    ("validation", "validation", "validation-00000-of-00001.parquet", 106_166_438),
    ("train", "train0", "train-00000-of-00002.parquet", 451_596_008),
    ("train", "train1", "train-00001-of-00002.parquet", 471_302_660),
)
PHASES = ("test", "validation", "train")
LOCAL_SHARDS = {"test", "validation"}


class Candidate(NamedTuple):
    split: str
    shard: str
    index: int
    cls: str
    path: str


def wanted_classes() -> set[str]:
    classes: set[str] = set()
    for category in FOCUS:
        _sop, caltech = PLAN[category]
        classes.update(caltech)
    return classes


def historical_caltech_indices() -> tuple[set[int], set[str]]:
    indices: set[int] = set()
    names: set[str] = set()
    with HISTORICAL.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            names.add(Path(row["fichier"]).name)
            if row["source"] != "caltech":
                continue
            indices.add(int(Path(row["fichier"]).stem.rsplit("_", 1)[1]))
    return indices, names


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def download(url: str, dest: Path, expected: int) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and dest.stat().st_size == expected:
        print(f"cache {dest.name}", flush=True)
        return
    partial = dest.with_suffix(dest.suffix + ".partial")
    if partial.exists():
        partial.unlink()
    print(f"téléchargement {dest.name}", flush=True)
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(request, timeout=180) as response, partial.open("wb") as out:
            total = 0
            mark = 20 * 1024 * 1024
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
                total += len(chunk)
                if total >= mark:
                    print(f"  {dest.name} {total / 1_048_576:.0f} Mo", flush=True)
                    mark += 20 * 1024 * 1024
    except (urllib.error.URLError, TimeoutError, OSError):
        if partial.exists():
            partial.unlink()
        raise
    with partial.open("rb") as handle:
        start = handle.read(4)
        handle.seek(-4, io.SEEK_END)
        end = handle.read(4)
    if start != b"PAR1" or end != b"PAR1":
        partial.unlink()
        raise OSError(f"parquet invalide : {dest.name}")
    partial.replace(dest)
    print(f"  {dest.name} prêt ({dest.stat().st_size} octets)", flush=True)


class RangeReader(io.RawIOBase):
    """Lecture HTTP par intervalles, connexion réutilisée, sur l'URL signée du CDN."""

    def __init__(self, page_url: str, size: int):
        self.page_url = page_url
        self._size = size
        self.pos = 0
        self.fetched = 0
        self.calls = 0
        self._conn: http.client.HTTPSConnection | None = None
        self._host = ""
        self._path = ""

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def seek(self, offset: int, whence: int = 0) -> int:
        if whence == 0:
            self.pos = int(offset)
        elif whence == 1:
            self.pos += int(offset)
        elif whence == 2:
            self.pos = self._size + int(offset)
        else:
            raise ValueError(whence)
        return self.pos

    def tell(self) -> int:
        return self.pos

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
        super().close()

    def _resolve(self) -> None:
        request = urllib.request.Request(
            self.page_url,
            headers={"Range": "bytes=0-0", "User-Agent": UA},
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            final = response.geturl()
            response.read()
        parsed = urlparse(final)
        if not parsed.hostname or not parsed.path:
            raise OSError(f"redirection vide pour {self.page_url}")
        self._host = parsed.hostname
        self._path = parsed.path + (f"?{parsed.query}" if parsed.query else "")
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def _connection(self) -> http.client.HTTPSConnection:
        if not self._host:
            self._resolve()
        if self._conn is None:
            self._conn = http.client.HTTPSConnection(self._host, timeout=180)
        return self._conn

    def read(self, n: int = -1) -> bytes:
        if n is None or n < 0:
            n = self._size - self.pos
        if self.pos >= self._size or n <= 0:
            return b""
        end = min(self.pos + n - 1, self._size - 1)
        expected = end - self.pos + 1
        last_error: Exception | None = None
        for attempt in range(4):
            try:
                conn = self._connection()
                conn.request(
                    "GET",
                    self._path,
                    headers={"Range": f"bytes={self.pos}-{end}", "User-Agent": UA},
                )
                response = conn.getresponse()
                data = response.read()
                if response.status == 206 and len(data) == expected:
                    self.pos += len(data)
                    self.fetched += len(data)
                    self.calls += 1
                    return data
                if self._conn is not None:
                    self._conn.close()
                self._conn = None
                if response.status in {301, 302, 303, 307, 308, 401, 403}:
                    self._host = ""
                last_error = OSError(f"HTTP {response.status} ({len(data)} octets, attendu {expected})")
            except (http.client.HTTPException, TimeoutError, OSError) as exc:
                if self._conn is not None:
                    self._conn.close()
                self._conn = None
                last_error = exc
            time.sleep(0.4 * (attempt + 1))
        assert last_error is not None
        raise last_error

    def readinto(self, buffer: bytearray) -> int:
        data = self.read(len(buffer))
        buffer[: len(data)] = data
        return len(data)


class ImageStore:
    def __init__(self) -> None:
        self._pf: dict[str, pq.ParquetFile] = {}
        self._readers: list[RangeReader] = []
        self._groups: dict[tuple[str, int], pa.Table] = {}

    def close(self) -> None:
        for reader in self._readers:
            reader.close()

    def open_local(self, shard: str, path: Path) -> None:
        self._pf[shard] = pq.ParquetFile(path)

    def open_remote(self, shard: str, filename: str, size: int) -> None:
        reader = RangeReader(f"{HF}/{filename}", size)
        self._readers.append(reader)
        self._pf[shard] = pq.ParquetFile(pa.PythonFile(reader, mode="r"))

    def labels(self, shard: str) -> tuple[list[str], list[str]]:
        table = self._pf[shard].read(columns=["text", "image.path"])
        texts = table.column("text").to_pylist()
        paths = [row["path"] for row in table.column("image").to_pylist()]
        return texts, paths

    def read(self, item: Candidate) -> tuple[bytes, str]:
        if item.shard not in self._pf:
            spec = next(row for row in SHARDS if row[1] == item.shard)
            if item.shard in LOCAL_SHARDS:
                self.open_local(item.shard, CACHE / spec[2])
            else:
                self.open_remote(item.shard, spec[2], spec[3])
        pf = self._pf[item.shard]
        group, local = _locate(pf, item.index)
        key = (item.shard, group)
        if key not in self._groups:
            self._groups[key] = pf.read_row_group(group, columns=["image"])
        cell = self._groups[key].column("image")[local].as_py()
        return bytes(cell["bytes"]), cell["path"]


def _locate(pf: pq.ParquetFile, index: int) -> tuple[int, int]:
    offset = 0
    for group in range(pf.metadata.num_row_groups):
        count = pf.metadata.row_group(group).num_rows
        if index < offset + count:
            return group, index - offset
        offset += count
    raise IndexError(index)


def cache_file(shard: str) -> Path:
    return CACHE / f"focus-index-{shard}.json"


def load_index_cache(shard: str, size: int) -> list[dict] | None:
    path = cache_file(shard)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if payload.get("version") != 1 or payload.get("size") != size:
        return None
    rows = payload.get("rows")
    if not isinstance(rows, list):
        return None
    return rows


def save_index_cache(shard: str, size: int, rows: list[dict]) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "size": size, "rows": rows}
    cache_file(shard).write_text(json.dumps(payload), encoding="utf-8")


def rows_from_columns(texts: list[str], paths: list[str], classes: set[str]) -> list[dict]:
    rows = []
    for index, (text, path) in enumerate(zip(texts, paths)):
        if text in classes and path:
            rows.append({"index": index, "text": text, "path": path})
    return rows


def add_candidates(catalog: dict[str, dict[str, list[Candidate]]], split: str, shard: str, rows: list[dict]) -> None:
    for row in rows:
        catalog[split].setdefault(row["text"], []).append(
            Candidate(split, shard, int(row["index"]), row["text"], row["path"])
        )


def jpeg_name(item: Candidate) -> str:
    return f"focus_caltech_{item.shard}_{item.cls}_{item.index}.jpg"


def main() -> int:
    parser = argparse.ArgumentParser(description="Construit le jeu focal (manifeste séparé).")
    parser.add_argument("--per-category", type=int, default=100)
    args = parser.parse_args()
    if args.per_category < 1:
        raise SystemExit("--per-category doit être ≥ 1")
    if not HISTORICAL.is_file():
        raise SystemExit(f"Manifeste historique absent : {HISTORICAL}")

    historical_hash = file_sha256(HISTORICAL)
    hist_indices, hist_names = historical_caltech_indices()
    classes = wanted_classes()
    for category in FOCUS:
        sop_classes, _caltech = PLAN[category]
        if sop_classes:
            print(f"{category} : classes SOP ignorées par ce mode ({', '.join(sop_classes)})")

    store = ImageStore()
    catalog: dict[str, dict[str, list[Candidate]]] = {split: {} for split in PHASES}
    blocked_paths: set[str] = set()
    network_notes: list[str] = []

    try:
        test_spec = SHARDS[0]
        test_path = CACHE / test_spec[2]
        try:
            download(f"{HF}/{test_spec[2]}", test_path, test_spec[3])
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            print(f"Échec du téléchargement du split test : {exc}")
            print("Aucun manifeste focal écrit. Relancer la même commande.")
            return 1
        store.open_local("test", test_path)
        test_texts, test_paths = store.labels("test")
        add_candidates(catalog, "test", "test", rows_from_columns(test_texts, test_paths, classes))
        mismatches = 0
        with HISTORICAL.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                if row["source"] != "caltech":
                    continue
                index = int(Path(row["fichier"]).stem.rsplit("_", 1)[1])
                if index >= len(test_texts) or test_texts[index] != row["classe_source"]:
                    mismatches += 1
        if mismatches:
            raise SystemExit(f"Index Caltech incohérent avec le manifeste historique ({mismatches} lignes).")
        probe = Candidate("test", "test", 2062, test_texts[2062], test_paths[2062])
        probe_bytes, probe_path = store.read(probe)
        if probe_path != test_paths[2062] or test_texts[2062] != "teddy-bear" or not probe_bytes:
            raise SystemExit("Sonde Caltech incohérente (teddy-bear, ligne 2062).")
        for index in hist_indices:
            if 0 <= index < len(test_paths) and test_paths[index]:
                blocked_paths.add(test_paths[index])
        print(f"photos historiques écartées (chemin Caltech) : {len(blocked_paths)}", flush=True)

        def ensure_split(split: str) -> bool:
            if any(catalog[split].values()):
                return True
            ok = True
            for split_name, shard, filename, size in SHARDS:
                if split_name != split:
                    continue
                if shard in LOCAL_SHARDS:
                    path = CACHE / filename
                    try:
                        download(f"{HF}/{filename}", path, size)
                    except (urllib.error.URLError, TimeoutError, OSError) as exc:
                        network_notes.append(f"{shard} : téléchargement impossible ({exc})")
                        print(network_notes[-1], flush=True)
                        ok = False
                        continue
                    store.open_local(shard, path)
                    texts, paths = store.labels(shard)
                    add_candidates(catalog, split, shard, rows_from_columns(texts, paths, classes))
                    continue
                cached = load_index_cache(shard, size)
                if cached is None:
                    print(f"index {shard} (colonnes texte seulement)", flush=True)
                    try:
                        store.open_remote(shard, filename, size)
                        texts, paths = store.labels(shard)
                    except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException) as exc:
                        network_notes.append(f"{shard} : index impossible ({exc})")
                        print(network_notes[-1], flush=True)
                        ok = False
                        continue
                    cached = rows_from_columns(texts, paths, classes)
                    save_index_cache(shard, size, cached)
                    print(f"  {shard} : {len(cached)} photos des classes focales", flush=True)
                else:
                    print(f"index {shard} en cache ({len(cached)} photos)", flush=True)
                add_candidates(catalog, split, shard, cached)
            return ok

        rng = random.Random(SEED)
        seen_hashes: set[str] = set()
        rows: list[dict[str, str]] = []

        def load(item: Candidate) -> bytes | None:
            if item.path in blocked_paths:
                return None
            if item.shard == "test" and item.index in hist_indices:
                return None
            name = jpeg_name(item)
            if name in hist_names:
                return None
            try:
                data, path = store.read(item)
            except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException, KeyError, IndexError) as exc:
                print(f"lecture impossible {item.shard}:{item.index} ({exc})", flush=True)
                return None
            if path != item.path or not data:
                print(f"photo inattendue {item.shard}:{item.index}", flush=True)
                return None
            digest = hashlib.sha256(data).hexdigest()
            if digest in seen_hashes:
                return None
            try:
                Image.open(io.BytesIO(data)).convert("RGB")
            except (OSError, ValueError) as exc:
                print(f"image illisible {item.path} ({exc})", flush=True)
                return None
            seen_hashes.add(digest)
            return data

        for category in FOCUS:
            _sop, caltech_classes = PLAN[category]
            chosen: list[tuple[Candidate, bytes]] = []
            for phase in PHASES:
                if len(chosen) >= args.per_category:
                    break
                if phase != "test":
                    ensure_split(phase)
                pools = []
                for cls in caltech_classes:
                    pool = [
                        item
                        for item in catalog[phase].get(cls, [])
                        if item.path not in blocked_paths and not (item.shard == "test" and item.index in hist_indices)
                    ]
                    pools.append(pool)
                batch = round_robin(pools, args.per_category - len(chosen), rng, load)
                for item, data in batch:
                    blocked_paths.add(item.path)
                    chosen.append((item, data))

            folder = OUT_DIR / slugify(category)
            folder.mkdir(parents=True, exist_ok=True)
            saved = 0
            split_counts: Counter[str] = Counter()
            class_counts: Counter[str] = Counter()
            for item, data in chosen:
                name = jpeg_name(item)
                dest = folder / name
                rel = f"{folder.name}/{name}"
                if not name.startswith("focus_") or rel in {row["fichier"] for row in rows}:
                    continue
                try:
                    image = Image.open(io.BytesIO(data)).convert("RGB")
                    partial = dest.with_suffix(".jpg.part")
                    image.save(partial, format="JPEG", quality=92)
                    partial.replace(dest)
                except OSError as exc:
                    print(f"écriture impossible {rel} ({exc})", flush=True)
                    continue
                rows.append(
                    {
                        "fichier": rel,
                        "categorie": category,
                        "source": "caltech",
                        "classe_source": item.cls,
                    }
                )
                saved += 1
                split_counts[item.shard] += 1
                class_counts[item.cls] += 1
            detail = " ".join(f"{key}={split_counts[key]}" for key in ("test", "validation", "train0", "train1") if split_counts[key])
            print(f"{category} : {saved} images ({detail or 'aucune'})", flush=True)
            for cls in caltech_classes:
                print(f"  {cls} : {class_counts[cls]}", flush=True)
            if saved < args.per_category:
                print(f"  plafond réel : {saved} / {args.per_category}", flush=True)

        if not rows:
            print("Aucune image écrite. Manifeste focal non créé.")
            if network_notes:
                print("Réseau : " + " | ".join(network_notes))
            return 1

        FOCUS_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        with FOCUS_MANIFEST.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["fichier", "categorie", "source", "classe_source"])
            writer.writeheader()
            writer.writerows(rows)

        keep = {row["fichier"] for row in rows}
        for category in FOCUS:
            folder = OUT_DIR / slugify(category)
            for old in folder.glob("focus_*.jpg"):
                rel = f"{folder.name}/{old.name}"
                if rel not in keep:
                    old.unlink()

        if file_sha256(HISTORICAL) != historical_hash:
            raise SystemExit("Le manifeste historique a changé pendant la construction.")

        by_source = Counter(row["source"] for row in rows)
        print(f"Total : {len(rows)} images -> {FOCUS_MANIFEST.relative_to(ROOT)}", flush=True)
        print("sources : " + ", ".join(f"{key}={by_source[key]}" for key in sorted(by_source)), flush=True)
        print("SOP : 0 (aucune classe SOP dans PLAN pour ces deux catégories)", flush=True)
        if network_notes:
            print("Réseau : " + " | ".join(network_notes), flush=True)
        return 0
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
