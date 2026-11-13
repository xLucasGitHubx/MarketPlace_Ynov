"""Gradio Space — distillation KD ResNet-50 → MobileNetV3-Small (ZeroGPU).

Hardware : ZeroGPU (Settings Space). Quota Academia/PRO ≈ 40 min/jour.
Ne pas tester l'API Azure ici — ce Space produit uniquement l'artefact student ONNX.
"""

from __future__ import annotations

import io
import sys
import traceback
from argparse import Namespace
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any, Generator

import spaces  # avant tout import CUDA / torch
import gradio as gr

from distill_student import DistillConfig, dry_run, run_export, train

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

AZURE_API = (
    "https://marketplace-api.whitepond-81c2f971.swedencentral.azurecontainerapps.io"
)
DEFAULT_CKPT = "models/distill"
DEFAULT_ONNX = "models/onnx"
DEFAULT_CACHE = "/data/hf"  # persistant si volume ; sinon models/hf

CSS = """
#main-col { max-width: 920px; margin: 0 auto; }
#status-box textarea {
  font-weight: 600;
  min-height: 3.2rem !important;
}
#logs-box textarea {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.85rem;
  line-height: 1.35;
}
.dark .gradio-container { color: var(--body-text-color); }
"""


def _capture(fn) -> tuple[str, Exception | None]:
    """Capture stdout+stderr pour l'UI (jamais silencieux)."""
    buf = io.StringIO()
    err: Exception | None = None
    try:
        with redirect_stdout(buf), redirect_stderr(buf):
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
        max_images=2000,
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


def _artifact_files() -> list[str]:
    """Chemins téléchargeables s'ils existent."""
    candidates = [
        ROOT / DEFAULT_CKPT / "distill_meta.json",
        ROOT / DEFAULT_CKPT / "last.pt",
        ROOT / DEFAULT_CKPT / "best.pt",
        ROOT / DEFAULT_ONNX / "student-kd-mobilenet-fp32.onnx",
        ROOT / DEFAULT_ONNX / "student-kd-mobilenet-int8-static.onnx",
        ROOT / DEFAULT_ONNX / "student-kd-mobilenet-int8.onnx",
    ]
    return [str(p) for p in candidates if p.is_file()]


def _pack(status: str, log: str, files: list[str] | None = None) -> tuple[str, str, list[str] | None]:
    artifacts = files if files else None
    return status, log, artifacts


def run_dry_run(
    epochs: int,
    max_images: int,
    max_minutes: float,
    batch_size: int,
) -> Generator[tuple[str, str, list[str] | None], None, None]:
    """Sans GPU : plan + méta JSON — feedback immédiat dans Statut/logs."""
    yield _pack(
        "⏳ Dry-run en cours…",
        "Préparation du plan (aucun GPU, aucun téléchargement)…\n",
    )
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
        print("=== Dry-run MarketPlace Ynov ===", flush=True)
        print(
            f"params: epochs={args.epochs} max_images={args.max_images} "
            f"max_minutes={args.max_minutes} batch_size={args.batch_size}",
            flush=True,
        )
        dry_run(args, config)

    log, err = _capture(_go)
    files = _artifact_files()
    if err is None:
        status = "✅ Dry-run OK — aucun GPU consommé."
    else:
        status = f"❌ Dry-run échoué : {err}"
    yield _pack(status, log or "(aucun log capturé)", files)


def _gpu_duration(*args: Any, **kwargs: Any) -> int:
    """Réserve le quota ZeroGPU = plafond session (secondes) + marge download.

    Signature souple : Gradio peut passer progress= en positionnel.
    Ordre attendu des inputs train : epochs, max_images, max_minutes, ...
    """
    max_minutes = 35.0
    if len(args) >= 3:
        try:
            max_minutes = float(args[2] or 35.0)
        except (TypeError, ValueError):
            max_minutes = 35.0
    if "max_minutes" in kwargs:
        try:
            max_minutes = float(kwargs["max_minutes"] or 35.0)
        except (TypeError, ValueError):
            max_minutes = 35.0
    # Marge 2 min pour chargement HF / dataset ; plafond soft 38 min (quota ~40)
    return int(min(max(max_minutes, 1.0) + 2.0, 38.0) * 60)


@spaces.GPU(duration=_gpu_duration)
def run_distill(
    epochs: int,
    max_images: int,
    max_minutes: float,
    batch_size: int,
    resume_path: str,
    do_export: bool,
    do_quantize: bool,
) -> Generator[tuple[str, str, list[str] | None], None, None]:
    """Entraînement KD sur ZeroGPU (≤ max_minutes) — logs streamés via yields."""
    yield _pack(
        "🚀 GPU alloué — démarrage de la distillation…",
        "ZeroGPU worker démarré.\n"
        f"epochs={epochs} images={max_images} batch={batch_size} "
        f"max_minutes={max_minutes}\n"
        "Chargement teacher/student + dataset (peut prendre 1–2 min)…\n",
    )

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
            f"resume={args.resume}",
            flush=True,
        )
        checkpoint = train(args, config)
        print(f"Checkpoint principal : {checkpoint}", flush=True)
        if args.export_onnx or args.quantize:
            run_export(args, checkpoint)

    log, err = _capture(_go)
    files = _artifact_files()
    if err is None:
        status = (
            "✅ Distillation terminée (ou arrêt propre sur budget temps). "
            "Voir artefacts ci-dessous."
        )
    else:
        status = f"❌ Échec distillation : {err}"
    yield _pack(status, log or "(aucun log capturé)", files)


def mark_queued() -> tuple[str, str, list[str] | None]:
    """Feedback immédiat avant l'allocation ZeroGPU (évite le silence)."""
    return _pack(
        "⏳ En file ZeroGPU — allocation GPU en cours…",
        "Requête mise en file. Attente d'un worker ZeroGPU "
        "(parfois 10–60 s à froid ; ne pas re-cliquer).\n",
    )


def run_export_only(
    resume_path: str,
    do_quantize: bool,
) -> Generator[tuple[str, str, list[str] | None], None, None]:
    """Export ONNX (+ int8) sur CPU — pas de décorateur ZeroGPU."""
    yield _pack("⏳ Export ONNX en cours (CPU)…", "Recherche du checkpoint…\n")

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
        print(f"Export depuis {resume} (quantize={args.quantize})", flush=True)
        run_export(args, Path(resume))

    log, err = _capture(_go)
    files = _artifact_files()
    status = "✅ Export terminé." if err is None else f"❌ Export échoué : {err}"
    yield _pack(status, log or "(aucun log capturé)", files)


def build_ui() -> gr.Blocks:
    with gr.Blocks(
        title="MarketPlace Ynov — Distillation KD",
        theme=gr.themes.Soft(
            primary_hue="blue",
            secondary_hue="slate",
            neutral_hue="slate",
        ),
        css=CSS,
    ) as demo:
        with gr.Column(elem_id="main-col"):
            gr.Markdown(
                f"""
# MarketPlace Ynov — Distillation KD
Teacher `microsoft/resnet-50` → student `facebook/mobilenet_v3_small` sur **ZeroGPU**.

Budget recommandé : **≤ 35 min** / session (quota Academia/PRO ≈ **40 min/jour**).  
API Azure (prod ONNX CPU) : [{AZURE_API}]({AZURE_API})

1. **Dry-run** d'abord (sans GPU) — doit afficher un plan JSON tout de suite.  
2. Puis **Lancer la distillation** — le statut passe par *file → GPU → logs*.
                """
            )

            with gr.Row():
                with gr.Column(scale=1):
                    epochs = gr.Slider(1, 3, value=2, step=1, label="Epochs")
                    max_images = gr.Slider(
                        500,
                        5000,
                        value=2000,
                        step=100,
                        label="Images max (Caltech hors test)",
                        info="2000 ≈ session confortable sous 35 min",
                    )
                with gr.Column(scale=1):
                    max_minutes = gr.Slider(
                        5,
                        38,
                        value=35,
                        step=1,
                        label="Max minutes GPU (stop propre)",
                    )
                    batch_size = gr.Slider(
                        8, 64, value=32, step=8, label="Batch size"
                    )

            with gr.Accordion("Options avancées", open=False):
                resume_path = gr.Textbox(
                    label="Reprise checkpoint (laisser vide au 1er run)",
                    placeholder="models/distill/last.pt  — vide = nouveau run",
                    value="",
                    lines=1,
                )
                with gr.Row():
                    do_export = gr.Checkbox(
                        label="Après train : export ONNX fp32", value=False
                    )
                    do_quantize = gr.Checkbox(
                        label="Après export : quantize int8 QDQ", value=False
                    )

            with gr.Row():
                btn_dry = gr.Button(
                    "Dry-run (sans GPU)", variant="secondary", scale=1
                )
                btn_train = gr.Button(
                    "Lancer la distillation (ZeroGPU)", variant="primary", scale=2
                )
                btn_export = gr.Button("Export seul (CPU)", variant="secondary", scale=1)

            status = gr.Textbox(
                label="Statut",
                value="Prêt — cliquez Dry-run pour vérifier l'UI (sans GPU).",
                interactive=False,
                lines=2,
                max_lines=4,
                elem_id="status-box",
            )
            logs = gr.Textbox(
                label="Logs",
                value="",
                interactive=False,
                lines=18,
                max_lines=40,
                elem_id="logs-box",
            )
            artifacts = gr.File(
                label="Artefacts téléchargeables (meta, checkpoints, ONNX)",
                file_count="multiple",
                interactive=False,
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
        outputs = [status, logs, artifacts]

        # Dry-run : générateur → premier yield immédiat (jamais silencieux)
        btn_dry.click(
            run_dry_run,
            inputs=[epochs, max_images, max_minutes, batch_size],
            outputs=outputs,
            show_progress="full",
        )

        # Distill : statut « en file » tout de suite, puis worker ZeroGPU
        btn_train.click(
            mark_queued,
            inputs=None,
            outputs=outputs,
            show_progress="full",
        ).then(
            run_distill,
            inputs=inputs_train,
            outputs=outputs,
            show_progress="full",
        )

        btn_export.click(
            run_export_only,
            inputs=[resume_path, do_quantize],
            outputs=outputs,
            show_progress="full",
        )

    return demo


demo = build_ui()
demo.queue(default_concurrency_limit=1)

if __name__ == "__main__":
    demo.launch()
