"""Gradio Space — distillation KD ResNet-50 → MobileNetV3-Small (ZeroGPU).

Hardware : ZeroGPU (Settings Space). Quota Academia/PRO ≈ 40 min/jour.
Ne pas tester l'API Azure ici — ce Space produit uniquement l'artefact student ONNX.
"""

from __future__ import annotations

import io
import sys
import traceback
from argparse import Namespace
from contextlib import redirect_stdout
from pathlib import Path

import spaces  # avant tout import CUDA / torch
import gradio as gr

from distill_student import DistillConfig, dry_run, run_export, train

ROOT = Path(__file__).resolve().parent
AZURE_API = (
    "https://marketplace-api.whitepond-81c2f971.swedencentral.azurecontainerapps.io"
)
DEFAULT_CKPT = "models/distill"
DEFAULT_ONNX = "models/onnx"
DEFAULT_CACHE = "/data/hf"  # persistant si volume ; sinon models/hf


def _capture(fn) -> tuple[str, Exception | None]:
    buf = io.StringIO()
    err: Exception | None = None
    try:
        with redirect_stdout(buf):
            fn()
    except Exception as exc:  # noqa: BLE001 — surface à l'UI
        err = exc
        buf.write("\n--- ERREUR ---\n")
        buf.write(traceback.format_exc())
    return buf.getvalue(), err


def _ns(**kwargs) -> Namespace:
    base = dict(
        dry_run=False,
        epochs=2,
        batch_size=32,
        lr=3e-4,
        temperature=4.0,
        ce_weight=0.1,
        max_images=3000,
        max_minutes=35.0,
        max_steps=0,
        seed=42,
        cache_dir=DEFAULT_CACHE,
        checkpoint_dir=DEFAULT_CKPT,
        resume=None,
        reset_optimizer=False,
        skip_train=False,
        export_onnx=False,
        quantize=False,
        onnx_dir=DEFAULT_ONNX,
        calib_parquet=None,
        calib_size=64,
    )
    base.update(kwargs)
    return Namespace(**base)


def _artifact_files() -> list[str | None]:
    """Chemins téléchargeables s'ils existent."""
    candidates = [
        ROOT / DEFAULT_CKPT / "distill_meta.json",
        ROOT / DEFAULT_CKPT / "last.pt",
        ROOT / DEFAULT_CKPT / "best.pt",
        ROOT / DEFAULT_ONNX / "student-kd-mobilenet-fp32.onnx",
        ROOT / DEFAULT_ONNX / "student-kd-mobilenet-int8-static.onnx",
        ROOT / DEFAULT_ONNX / "student-kd-mobilenet-int8.onnx",
    ]
    return [str(p) if p.is_file() else None for p in candidates]


def run_dry_run(
    epochs: int,
    max_images: int,
    max_minutes: float,
    batch_size: int,
) -> tuple[str, list]:
    """Sans GPU : plan + méta JSON."""
    args = _ns(
        dry_run=True,
        epochs=int(epochs),
        max_images=int(max_images),
        max_minutes=float(max_minutes),
        batch_size=int(batch_size),
        cache_dir=str(ROOT / "models" / "hf"),
    )
    config = DistillConfig(
        epochs=args.epochs,
        batch_size=args.batch_size,
        max_images=args.max_images,
        max_minutes=args.max_minutes,
    )

    def _go():
        dry_run(args, config)

    log, err = _capture(_go)
    status = "✅ Dry-run OK (aucun GPU consommé)." if err is None else f"❌ {err}"
    files = [f for f in _artifact_files() if f] or None
    return f"{status}\n\n{log}", files


def _gpu_duration(
    epochs,
    max_images,
    max_minutes,
    batch_size,
    resume_path,
    do_export,
    do_quantize,
) -> int:
    """Réserve le quota ZeroGPU = plafond session (secondes) + marge download."""
    minutes = float(max_minutes or 35.0)
    # Marge 2 min pour chargement HF / dataset ; plafond soft 38 min (quota ~40)
    return int(min(max(minutes, 1.0) + 2.0, 38.0) * 60)


@spaces.GPU(duration=_gpu_duration)
def run_distill(
    epochs: int,
    max_images: int,
    max_minutes: float,
    batch_size: int,
    resume_path: str,
    do_export: bool,
    do_quantize: bool,
) -> tuple[str, list]:
    """Entraînement KD sur ZeroGPU (≤ max_minutes)."""
    resume = (resume_path or "").strip() or None
    cache = DEFAULT_CACHE if Path("/data").is_dir() else str(ROOT / "models" / "hf")
    args = _ns(
        epochs=int(epochs),
        max_images=int(max_images),
        max_minutes=float(max_minutes),
        batch_size=int(batch_size),
        cache_dir=cache,
        resume=Path(resume) if resume else None,
        export_onnx=bool(do_export),
        quantize=bool(do_quantize),
    )
    config = DistillConfig(
        epochs=args.epochs,
        batch_size=args.batch_size,
        max_images=args.max_images,
        max_minutes=args.max_minutes,
    )

    checkpoint = None

    def _go():
        nonlocal checkpoint
        print(
            f"KD démarré — epochs={args.epochs} images={args.max_images} "
            f"batch={args.batch_size} max_minutes={args.max_minutes} "
            f"resume={args.resume}"
        )
        checkpoint = train(args, config)
        print(f"Checkpoint principal : {checkpoint}")
        if args.export_onnx or args.quantize:
            run_export(args, checkpoint)

    log, err = _capture(_go)
    if err is None:
        status = (
            "✅ Distillation terminée (ou arrêt propre sur budget temps). "
            "Voir les artefacts ci-dessous."
        )
    else:
        status = f"❌ Échec : {err}"
    files = [f for f in _artifact_files() if f] or None
    return f"{status}\n\n{log}", files


def run_export_only(
    resume_path: str,
    do_quantize: bool,
) -> tuple[str, list]:
    """Export ONNX (+ int8) sur CPU — pas de décorateur ZeroGPU."""
    resume = (resume_path or "").strip() or str(ROOT / DEFAULT_CKPT / "best.pt")
    cache = DEFAULT_CACHE if Path("/data").is_dir() else str(ROOT / "models" / "hf")
    args = _ns(
        skip_train=True,
        resume=Path(resume),
        export_onnx=True,
        quantize=bool(do_quantize),
        cache_dir=cache,
    )

    def _go():
        if not Path(resume).is_file():
            raise FileNotFoundError(
                f"Checkpoint introuvable : {resume}. "
                "Lancez d'abord une distillation ou uploadez best.pt / last.pt."
            )
        run_export(args, Path(resume))

    log, err = _capture(_go)
    status = "✅ Export terminé." if err is None else f"❌ {err}"
    files = [f for f in _artifact_files() if f] or None
    return f"{status}\n\n{log}", files


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="MarketPlace Ynov — Distillation KD") as demo:
        gr.Markdown(
            f"""
# MarketPlace Ynov — Distillation KD (ZeroGPU)

Teacher `microsoft/resnet-50` → student `facebook/mobilenet_v3_small`.  
Budget recommandé : **≤ 35 min** / session (quota Academia/PRO ≈ **40 min/jour**).

API Azure (prod, ONNX CPU) : [{AZURE_API}]({AZURE_API})

**Pas de test local requis** — utilisez les boutons ci-dessous sur ce Space.
            """
        )

        with gr.Row():
            epochs = gr.Slider(1, 3, value=2, step=1, label="Epochs")
            max_images = gr.Slider(
                500, 5000, value=3000, step=100, label="Images max (Caltech hors test)"
            )
            max_minutes = gr.Slider(
                5, 38, value=35, step=1, label="Max minutes GPU (stop propre)"
            )
            batch_size = gr.Slider(8, 64, value=32, step=8, label="Batch size")

        resume_path = gr.Textbox(
            label="Reprise checkpoint (optionnel)",
            placeholder="models/distill/last.pt",
            value="",
        )
        with gr.Row():
            do_export = gr.Checkbox(
                label="Après train : export ONNX fp32", value=False
            )
            do_quantize = gr.Checkbox(
                label="Après export : quantize int8 QDQ", value=False
            )

        with gr.Row():
            btn_dry = gr.Button("Dry-run (sans GPU)", variant="secondary")
            btn_train = gr.Button("Lancer la distillation (ZeroGPU)", variant="primary")
            btn_export = gr.Button("Export seul (CPU)", variant="secondary")

        logs = gr.Textbox(label="Statut / logs", lines=22, max_lines=40)
        artifacts = gr.File(
            label="Artefacts téléchargeables (meta, checkpoints, ONNX)",
            file_count="multiple",
        )

        gr.Markdown(
            """
### Après téléchargement (handoff Azure)

1. Récupérer `student-kd-mobilenet-int8-static.onnx` (et l'alias `…-int8.onnx` si présent).
2. Le placer dans le dépôt Ynov : `artifacts/onnx/` (ou `models/onnx/` pour un run local).
3. Rebuild / redeploy l'image Azure ONNX-only — ID catalogue : `student-kd-mobilenet-int8`.

### Reprise le lendemain

Si le log indique un timeout (`timed_out`) : renseigner `models/distill/last.pt` puis relancer.
            """
        )

        inputs_train = [
            epochs,
            max_images,
            max_minutes,
            batch_size,
            resume_path,
            do_export,
            do_quantize,
        ]
        btn_dry.click(
            run_dry_run,
            inputs=[epochs, max_images, max_minutes, batch_size],
            outputs=[logs, artifacts],
        )
        btn_train.click(
            run_distill,
            inputs=inputs_train,
            outputs=[logs, artifacts],
        )
        btn_export.click(
            run_export_only,
            inputs=[resume_path, do_quantize],
            outputs=[logs, artifacts],
        )

    return demo


if __name__ == "__main__":
    # Assurer import local distill_student / preprocessing
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    build_ui().queue(default_concurrency_limit=1).launch()
