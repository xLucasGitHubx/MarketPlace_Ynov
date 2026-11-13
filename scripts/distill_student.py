"""Distillation légère ResNet-50 (teacher) → MobileNetV3-Small (student).

Entraînement Knowledge Distillation (KD) conçu pour tenir dans le budget
ZeroGPU Hugging Face Academia (≈ 40 min/jour) :

- Loss : KL(teacher ∥ student) à température T + CE légère sur les
  pseudo-labels du teacher (pas de labels ImageNet au sol) ;
- 1–3 epochs sur un sous-ensemble Caltech-256 hors jeu de test (2–5k images) ;
- Checkpoint / reprise (`--resume`) pour segmenter une journée GPU ;
- Export ONNX fp32 du student + handoff vers int8 (`student-kd-mobilenet-int8`).

Usage (Space Lulu18 ou machine locale avec torch) :

    # Plan + structure sans téléchargement (toujours possible)
    python scripts/distill_student.py --dry-run

    # Session ZeroGPU (~35 min max pour laisser une marge)
    python scripts/distill_student.py --epochs 2 --max-images 3000 \\
        --max-minutes 35 --checkpoint-dir models/distill

    # Reprise le lendemain
    python scripts/distill_student.py --resume models/distill/last.pt \\
        --max-minutes 35 --export-onnx

    # Export seul depuis un checkpoint déjà entraîné
    python scripts/distill_student.py --resume models/distill/best.pt \\
        --export-onnx --skip-train

Artefacts attendus :
    models/distill/last.pt | best.pt | distill_meta.json
    models/onnx/student-kd-mobilenet-fp32.onnx
    models/onnx/student-kd-mobilenet-int8-static.onnx  (après quantize)
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import random
import sys
import time
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TEACHER_ID = "microsoft/resnet-50"
STUDENT_ID = "facebook/mobilenet_v3_small"
CALTECH_URL = "https://huggingface.co/datasets/ilee0022/Caltech-256/resolve/main/data/test-00000-of-00001.parquet"

# Noms alignés sur app/registry.py (CATALOG student-kd-mobilenet-int8)
STUDENT_FP32_NAME = "student-kd-mobilenet-fp32.onnx"
STUDENT_INT8_NAME = "student-kd-mobilenet-int8-static.onnx"
STUDENT_INT8_ALIAS = "student-kd-mobilenet-int8.onnx"


@dataclass
class DistillConfig:
    teacher_id: str = TEACHER_ID
    student_id: str = STUDENT_ID
    epochs: int = 2
    batch_size: int = 32
    lr: float = 3e-4
    temperature: float = 4.0
    ce_weight: float = 0.1  # alpha : CE légère ; (1-alpha) pour KL
    max_images: int = 3000
    seed: int = 42
    max_minutes: float = 35.0
    image_size: int = 224


def _device() -> str:
    import torch

    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _used_caltech_indices() -> set[int]:
    """Indices Caltech déjà dans le jeu de test proxy (à exclure)."""
    used: set[int] = set()
    manifest = ROOT / "data" / "test_set" / "manifest.csv"
    if not manifest.exists():
        return used
    with manifest.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("source") == "caltech":
                stem = Path(row["fichier"]).stem
                try:
                    used.add(int(stem.rsplit("_", 1)[1]))
                except (IndexError, ValueError):
                    continue
    return used


def load_caltech_subset(
    parquet: Path | None,
    n: int,
    seed: int,
) -> list[bytes]:
    """Charge N images Caltech-256 hors jeu de test (octets JPEG/PNG en mémoire)."""
    import pandas as pd

    src = parquet or io.BytesIO(urllib.request.urlopen(CALTECH_URL, timeout=180).read())  # noqa: S310
    df = pd.read_parquet(src)
    used = _used_caltech_indices()
    candidates = [i for i in df.index if i not in used]
    rng = random.Random(seed)
    if n > len(candidates):
        n = len(candidates)
    picked = rng.sample(candidates, n)
    return [df.loc[i, "image"]["bytes"] for i in picked]


class ByteImageDataset:
    """Dataset minimal : octets image → tenseur NCHW float32 (prétraitement ImageNet)."""

    def __init__(self, blobs: list[bytes], size: int = 224):
        self.blobs = blobs
        self.size = size

    def __len__(self) -> int:
        return len(self.blobs)

    def __getitem__(self, idx: int):
        from PIL import Image

        from app.preprocessing import to_model_input

        img = Image.open(io.BytesIO(self.blobs[idx])).convert("RGB")
        arr = to_model_input(img, size=self.size)  # (1, 3, H, W)
        import torch

        return torch.from_numpy(arr.squeeze(0))


def kd_loss(
    student_logits,
    teacher_logits,
    *,
    temperature: float,
    ce_weight: float,
):
    """KL soft (teacher∥student) + CE légère sur argmax teacher."""
    import torch
    import torch.nn.functional as F

    t = temperature
    soft_t = F.softmax(teacher_logits / t, dim=-1)
    log_soft_s = F.log_softmax(student_logits / t, dim=-1)
    kl = F.kl_div(log_soft_s, soft_t, reduction="batchmean") * (t * t)

    hard = teacher_logits.argmax(dim=-1)
    ce = F.cross_entropy(student_logits, hard)

    alpha = ce_weight
    return (1.0 - alpha) * kl + alpha * ce, kl.detach(), ce.detach()


def load_models(cache_dir: str | None, device: str):
    import torch
    from transformers import AutoModelForImageClassification

    teacher = AutoModelForImageClassification.from_pretrained(
        TEACHER_ID, cache_dir=cache_dir
    ).to(device).eval()
    for p in teacher.parameters():
        p.requires_grad_(False)

    student = AutoModelForImageClassification.from_pretrained(
        STUDENT_ID, cache_dir=cache_dir
    ).to(device)
    student.train()
    return teacher, student


def save_checkpoint(
    path: Path,
    *,
    student,
    optimizer,
    epoch: int,
    global_step: int,
    best_loss: float,
    config: DistillConfig,
    meta_extra: dict | None = None,
) -> None:
    import torch

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "epoch": epoch,
        "global_step": global_step,
        "best_loss": best_loss,
        "student_state_dict": student.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "config": asdict(config),
        "teacher_id": TEACHER_ID,
        "student_id": STUDENT_ID,
        "meta": meta_extra or {},
    }
    torch.save(payload, path)
    print(f"Checkpoint écrit : {path} (epoch={epoch}, step={global_step})")


def export_student_onnx(
    student,
    out_fp32: Path,
    cache_dir: str | None = None,
) -> Path:
    """Exporte le student PyTorch → ONNX fp32 (batch dynamique)."""
    import torch

    out_fp32.parent.mkdir(parents=True, exist_ok=True)
    student = student.cpu().eval()

    class LogitsOnly(torch.nn.Module):
        def __init__(self, m):
            super().__init__()
            self.m = m

        def forward(self, pixel_values):
            return self.m(pixel_values=pixel_values).logits

    dummy = torch.randn(1, 3, 224, 224)
    torch.onnx.export(
        LogitsOnly(student),
        (dummy,),
        str(out_fp32),
        input_names=["pixel_values"],
        output_names=["logits"],
        dynamic_axes={"pixel_values": {0: "batch"}, "logits": {0: "batch"}},
        opset_version=17,
        do_constant_folding=True,
        dynamo=False,
    )
    print(f"ONNX fp32 : {out_fp32} ({out_fp32.stat().st_size / 1_048_576:.1f} Mo)")
    return out_fp32


class _ImageCalibrationReader:
    def __init__(self, images: list):
        from app.preprocessing import to_model_input

        self._it = iter([{"pixel_values": to_model_input(im)} for im in images])

    def get_next(self):
        return next(self._it, None)


def _calibration_images(parquet: Path | None, n: int):
    """Même protocole que scripts/export_onnx.py (Caltech hors jeu de test)."""
    import pandas as pd
    from PIL import Image

    src = parquet or io.BytesIO(urllib.request.urlopen(CALTECH_URL, timeout=120).read())  # noqa: S310
    df = pd.read_parquet(src)
    used = _used_caltech_indices()
    candidates = [i for i in df.index if i not in used]
    picked = random.Random(0).sample(candidates, min(n, len(candidates)))
    return [Image.open(io.BytesIO(df.loc[i, "image"]["bytes"])).convert("RGB") for i in picked]


def quantize_student_int8(
    fp32_path: Path,
    int8_path: Path,
    *,
    calib_parquet: Path | None,
    calib_size: int,
) -> Path:
    """Quantization int8 statique QDQ (même protocole que scripts/export_onnx.py)."""
    from onnxruntime.quantization import (
        CalibrationMethod,
        QuantFormat,
        QuantType,
        quantize_static,
    )
    from onnxruntime.quantization.shape_inference import quant_pre_process

    pre = fp32_path.with_name(fp32_path.stem + "-pre.onnx")
    quant_pre_process(str(fp32_path), str(pre), skip_symbolic_shape=True)
    calib = _calibration_images(calib_parquet, calib_size)
    quantize_static(
        str(pre),
        str(int8_path),
        _ImageCalibrationReader(calib),
        quant_format=QuantFormat.QDQ,
        per_channel=True,
        activation_type=QuantType.QUInt8,
        weight_type=QuantType.QInt8,
        calibrate_method=CalibrationMethod.MinMax,
    )
    pre.unlink(missing_ok=True)

    # Alias catalogue (registry accepte les deux noms)
    alias = int8_path.parent / STUDENT_INT8_ALIAS
    if alias.resolve() != int8_path.resolve():
        alias.write_bytes(int8_path.read_bytes())
        print(f"Alias catalogue : {alias}")

    print(f"ONNX int8 : {int8_path} ({int8_path.stat().st_size / 1_048_576:.1f} Mo)")
    return int8_path


def write_meta(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def dry_run(args: argparse.Namespace, config: DistillConfig) -> None:
    """Sans téléchargement ni GPU : écrit le plan et les chemins d'artefacts."""
    ckpt_dir = Path(args.checkpoint_dir)
    onnx_dir = Path(args.onnx_dir)
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    onnx_dir.mkdir(parents=True, exist_ok=True)

    device = _device()
    meta = {
        "mode": "dry-run",
        "device_detecte": device,
        "config": asdict(config),
        "artefacts_attendus": {
            "checkpoint_last": str(ckpt_dir / "last.pt"),
            "checkpoint_best": str(ckpt_dir / "best.pt"),
            "onnx_fp32": str(onnx_dir / STUDENT_FP32_NAME),
            "onnx_int8": str(onnx_dir / STUDENT_INT8_NAME),
            "onnx_int8_alias": str(onnx_dir / STUDENT_INT8_ALIAS),
            "catalogue_id": "student-kd-mobilenet-int8",
        },
        "handoff_int8": [
            "Après entraînement : python scripts/distill_student.py --resume models/distill/best.pt --skip-train --export-onnx --quantize",
            "Ou exporter le fp32 puis calibrer comme scripts/export_onnx.py (QDQ hors jeu de test).",
        ],
        "budget_zerogpu": {
            "plafond_min_jour": 40,
            "max_minutes_recommande": config.max_minutes,
            "space": "Lulu18 (Academia Ynov)",
        },
    }
    out = ckpt_dir / "distill_meta.json"
    write_meta(out, meta)
    print(json.dumps(meta, indent=2, ensure_ascii=False))
    print(f"\nDry-run OK — méta écrite dans {out}")
    print("Pour entraîner sur Space ZeroGPU : voir docs/preuves/it-hf-space.md")


def train(args: argparse.Namespace, config: DistillConfig) -> Path:
    import torch
    from torch.utils.data import DataLoader

    device = _device()
    print(f"Device : {device}")
    if device == "cpu":
        print(
            "Avertissement : pas de GPU détecté — l'entraînement sera lent. "
            "Préférer le Space Lulu18 ZeroGPU (docs/preuves/it-hf-space.md)."
        )

    ckpt_dir = Path(args.checkpoint_dir)
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    deadline = start + config.max_minutes * 60.0

    print("Chargement teacher / student …")
    teacher, student = load_models(args.cache_dir, device)
    optimizer = torch.optim.AdamW(
        (p for p in student.parameters() if p.requires_grad),
        lr=config.lr,
    )

    start_epoch = 0
    global_step = 0
    best_loss = float("inf")

    if args.resume:
        resume_path = Path(args.resume)
        print(f"Reprise depuis {resume_path}")
        ckpt = torch.load(resume_path, map_location=device, weights_only=False)
        student.load_state_dict(ckpt["student_state_dict"])
        if "optimizer_state_dict" in ckpt and not args.reset_optimizer:
            optimizer.load_state_dict(ckpt["optimizer_state_dict"])
        start_epoch = int(ckpt.get("epoch", 0))
        global_step = int(ckpt.get("global_step", 0))
        best_loss = float(ckpt.get("best_loss", best_loss))
        # Reprendre à l'epoch suivante si le checkpoint a été sauvé en fin d'epoch
        if ckpt.get("meta", {}).get("end_of_epoch"):
            start_epoch += 1

    if args.skip_train:
        return ckpt_dir / "best.pt" if (ckpt_dir / "best.pt").exists() else Path(args.resume)

    print(f"Chargement dataset Caltech ({config.max_images} images hors test) …")
    blobs = load_caltech_subset(args.calib_parquet, config.max_images, config.seed)
    ds = ByteImageDataset(blobs, size=config.image_size)
    loader = DataLoader(
        ds,
        batch_size=config.batch_size,
        shuffle=True,
        num_workers=0,
        drop_last=True,
    )
    print(f"Dataset : {len(ds)} images, {len(loader)} batches/epoch")

    timed_out = False
    last_avg = None
    last_epoch_index = max(start_epoch - 1, -1)

    for epoch in range(start_epoch, config.epochs):
        last_epoch_index = epoch
        if time.monotonic() >= deadline:
            timed_out = True
            break
        student.train()
        running = 0.0
        n_batches = 0
        for batch in loader:
            if time.monotonic() >= deadline:
                timed_out = True
                print(
                    f"Budget temps atteint ({config.max_minutes} min) — "
                    "sauvegarde et arrêt propre."
                )
                break

            batch = batch.to(device)
            with torch.inference_mode():
                t_logits = teacher(pixel_values=batch).logits
            s_logits = student(pixel_values=batch).logits
            loss, kl, ce = kd_loss(
                s_logits,
                t_logits,
                temperature=config.temperature,
                ce_weight=config.ce_weight,
            )
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()

            running += float(loss.item())
            n_batches += 1
            global_step += 1

            if global_step % 20 == 0 or global_step == 1:
                elapsed = (time.monotonic() - start) / 60.0
                print(
                    f"epoch {epoch+1}/{config.epochs} step {global_step} "
                    f"loss={loss.item():.4f} kl={kl.item():.4f} ce={ce.item():.4f} "
                    f"({elapsed:.1f} min)"
                )

            if args.max_steps and global_step >= args.max_steps:
                print(f"--max-steps={args.max_steps} atteint.")
                timed_out = True
                break

        avg = running / max(n_batches, 1)
        last_avg = avg
        print(f"Epoch {epoch+1} moyenne loss={avg:.4f}")

        save_checkpoint(
            ckpt_dir / "last.pt",
            student=student,
            optimizer=optimizer,
            epoch=epoch,
            global_step=global_step,
            best_loss=best_loss,
            config=config,
            meta_extra={"end_of_epoch": not timed_out, "avg_loss": avg},
        )
        if avg < best_loss and n_batches > 0:
            best_loss = avg
            save_checkpoint(
                ckpt_dir / "best.pt",
                student=student,
                optimizer=optimizer,
                epoch=epoch,
                global_step=global_step,
                best_loss=best_loss,
                config=config,
                meta_extra={"end_of_epoch": True, "avg_loss": avg},
            )

        if timed_out:
            break

    write_meta(
        ckpt_dir / "distill_meta.json",
        {
            "mode": "train",
            "device": device,
            "timed_out": timed_out,
            "epochs_config": config.epochs,
            "last_epoch_index": last_epoch_index,
            "global_step": global_step,
            "best_loss": best_loss,
            "last_avg_loss": last_avg,
            "elapsed_min": round((time.monotonic() - start) / 60.0, 2),
            "config": asdict(config),
            "catalogue_id": "student-kd-mobilenet-int8",
            "resume_hint": (
                "python scripts/distill_student.py --resume models/distill/last.pt "
                f"--max-minutes {config.max_minutes}"
            ),
        },
    )
    return ckpt_dir / "best.pt" if (ckpt_dir / "best.pt").exists() else ckpt_dir / "last.pt"


def run_export(args: argparse.Namespace, checkpoint: Path | None) -> None:
    import torch

    device = "cpu"  # export toujours CPU
    onnx_dir = Path(args.onnx_dir)
    onnx_dir.mkdir(parents=True, exist_ok=True)

    _, student = load_models(args.cache_dir, device)
    if checkpoint and checkpoint.is_file():
        ckpt = torch.load(checkpoint, map_location=device, weights_only=False)
        student.load_state_dict(ckpt["student_state_dict"])
        print(f"Poids student chargés depuis {checkpoint}")
    else:
        print(
            "Attention : aucun checkpoint — export des poids HF pré-entraînés "
            "(pas encore distillés)."
        )

    fp32 = onnx_dir / STUDENT_FP32_NAME
    export_student_onnx(student, fp32, cache_dir=args.cache_dir)

    if args.quantize:
        int8 = onnx_dir / STUDENT_INT8_NAME
        quantize_student_int8(
            fp32,
            int8,
            calib_parquet=args.calib_parquet,
            calib_size=args.calib_size,
        )
        print(
            "\nHandoff catalogue : copier/renommer vers models/onnx/ puis "
            "redémarrer l'API (ID `student-kd-mobilenet-int8`)."
        )
    else:
        print(
            "\nProchaine étape int8 :\n"
            f"  python scripts/distill_student.py --resume {checkpoint or 'models/distill/best.pt'} "
            "--skip-train --export-onnx --quantize\n"
            "Ou pipeline catalogue (lorsque disponible) : scripts/export_catalog.py"
        )


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="KD ResNet-50 → MobileNetV3-Small (budget ZeroGPU ≤ 40 min/j)"
    )
    ap.add_argument("--dry-run", action="store_true", help="Plan + méta sans téléchargement")
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--temperature", type=float, default=4.0)
    ap.add_argument("--ce-weight", type=float, default=0.1, help="Poids CE (reste = KL)")
    ap.add_argument("--max-images", type=int, default=3000)
    ap.add_argument("--max-minutes", type=float, default=35.0)
    ap.add_argument("--max-steps", type=int, default=0, help="Stop après N steps (0 = illimité)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--cache-dir", default="models/hf")
    ap.add_argument("--checkpoint-dir", default="models/distill")
    ap.add_argument("--resume", type=Path, default=None)
    ap.add_argument("--reset-optimizer", action="store_true")
    ap.add_argument("--skip-train", action="store_true", help="Pas d'entraînement (export seul)")
    ap.add_argument("--export-onnx", action="store_true")
    ap.add_argument("--quantize", action="store_true", help="Après export fp32 : int8 QDQ statique")
    ap.add_argument("--onnx-dir", default="models/onnx")
    ap.add_argument("--calib-parquet", type=Path, default=None)
    ap.add_argument("--calib-size", type=int, default=64)
    return ap


def main() -> None:
    args = build_parser().parse_args()
    config = DistillConfig(
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        temperature=args.temperature,
        ce_weight=args.ce_weight,
        max_images=args.max_images,
        seed=args.seed,
        max_minutes=args.max_minutes,
    )

    if args.dry_run:
        dry_run(args, config)
        return

    checkpoint: Path | None = None
    if not args.skip_train or args.resume:
        if args.skip_train and args.resume:
            checkpoint = Path(args.resume)
        else:
            checkpoint = train(args, config)

    if args.export_onnx or args.quantize:
        if checkpoint is None and args.resume:
            checkpoint = Path(args.resume)
        run_export(args, checkpoint)


if __name__ == "__main__":
    main()
