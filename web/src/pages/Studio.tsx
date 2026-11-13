import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type DragEvent,
} from "react";
import { ApiClientError, fetchModels, predictImage } from "@/api/client";
import type { ModelInfo, PredictionResponse } from "@/api/types";
import { CompteurSession } from "@/components/CompteurSession";
import { StatusBadge } from "@/components/StatusBadge";
import { useAuth } from "@/hooks/useAuth";
import {
  formatConfidence,
  formatCostPerMillion,
  formatMs,
} from "@/lib/format";
import { useSessionConso } from "@/lib/sessionConso";
import { SchemaRequete } from "@/parcours/SchemaRequete";

const ACCEPT = "image/jpeg,image/png,image/webp";
const LAST_ETAPE = 7;
const PIPELINE_STEP_MS = 200;

/**
 * Exact Hugging Face pages.
 * Prod `resnet50-onnx-int8` → microsoft/resnet-50 (app/model.py HF_MODEL_ID).
 * Other ids → ModelSpec.hf_model_id in app/registry.py.
 * `student-kd-mobilenet-int8` has no hf_model_id; no link.
 */
const HF_ORIGINE_URL: Record<string, string> = {
  "resnet50-onnx-int8": "https://huggingface.co/microsoft/resnet-50",
  "efficientnet-b0-onnx-int8": "https://huggingface.co/google/efficientnet-b0",
  "mobilenet-v3-small-onnx-int8": "https://huggingface.co/facebook/mobilenet_v3_small",
  "clip-vit-b32": "https://huggingface.co/openai/clip-vit-base-patch32",
};

function prefersReducedMotion(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function clearStepTimers(ref: { current: number[] }): void {
  for (const id of ref.current) window.clearTimeout(id);
  ref.current = [];
}

function schedulePipeline(
  ref: { current: number[] },
  setEtape: (step: number) => void,
): void {
  clearStepTimers(ref);
  if (prefersReducedMotion()) {
    setEtape(LAST_ETAPE);
    return;
  }
  setEtape(0);
  for (let step = 1; step <= LAST_ETAPE; step += 1) {
    const id = window.setTimeout(() => setEtape(step), step * PIPELINE_STEP_MS);
    ref.current.push(id);
  }
}

export function StudioPage() {
  const { token, isAuthenticated } = useAuth();
  const { ajouter } = useSessionConso();
  const fileInputId = useId();
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [defaultId, setDefaultId] = useState("");
  const [modele, setModele] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PredictionResponse | null>(null);
  const [liveMsg, setLiveMsg] = useState("");
  const [etapeActive, setEtapeActive] = useState(-1);
  const abortRef = useRef<AbortController | null>(null);
  const stepTimersRef = useRef<number[]>([]);
  const requestGen = useRef(0);

  useEffect(() => {
    let cancelled = false;
    fetchModels()
      .then((res) => {
        if (cancelled) return;
        setModels(res.modeles);
        setDefaultId(res.defaut);
        setModele((prev) => prev || res.defaut);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const msg =
          err instanceof ApiClientError
            ? err.message
            : "Impossible de charger le catalogue modèles.";
        setError(msg);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      abortRef.current?.abort();
    };
  }, [previewUrl]);

  useEffect(() => {
    const timers = stepTimersRef;
    return () => {
      clearStepTimers(timers);
    };
  }, []);

  const assignFile = useCallback((next: File | null) => {
    clearStepTimers(stepTimersRef);
    setEtapeActive(-1);
    setResult(null);
    setError(null);
    setFile(next);
    setPreviewUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return next ? URL.createObjectURL(next) : null;
    });
  }, []);

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = e.dataTransfer.files?.[0];
    if (dropped) assignFile(dropped);
  };

  const selected = models.find((m) => m.id === modele);
  const origineHref = HF_ORIGINE_URL[modele];
  const canPredict =
    Boolean(file) &&
    isAuthenticated &&
    Boolean(modele) &&
    selected?.statut === "ready" &&
    !loading;

  async function onAnalyze() {
    if (!file || !token || !modele) return;
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    const generation = ++requestGen.current;
    setLoading(true);
    setError(null);
    setLiveMsg("Analyse en cours…");
    schedulePipeline(stepTimersRef, setEtapeActive);
    try {
      const res = await predictImage(file, modele, token, ctrl.signal);
      if (requestGen.current !== generation) return;
      clearStepTimers(stepTimersRef);
      setEtapeActive(LAST_ETAPE);
      setResult(res);
      ajouter(res.latence_ms, res.cout_estime_usd_par_million);
      setLiveMsg(`Résultat : ${res.categorie}, confiance ${formatConfidence(res.confiance)}.`);
    } catch (err) {
      if (requestGen.current !== generation) return;
      clearStepTimers(stepTimersRef);
      setEtapeActive(-1);
      if (err instanceof DOMException && err.name === "AbortError") return;
      const msg =
        err instanceof ApiClientError
          ? err.status === 401
            ? "Token manquant ou invalide. Vérifie le Bearer token."
            : err.message
          : "Échec de la prédiction.";
      setError(msg);
      setLiveMsg(msg);
    } finally {
      if (requestGen.current === generation) setLoading(false);
    }
  }

  return (
    <section className="fade-in" aria-labelledby="studio-title">
      <h1 id="studio-title" className="page-title">
        Studio
      </h1>
      <p className="page-lead">
        Dépose une photo d’objet, choisis un modèle allowlisté, obtient catégorie, titre et
        confiance.
      </p>

      {error ? (
        <p className="alert" data-tone="error" role="alert">
          {error}
        </p>
      ) : null}

      <div style={{ marginBottom: 24 }}>
        <SchemaRequete etapeActive={etapeActive} />
      </div>

      <div className="grid-studio">
        <div className="panel">
          <h2>Entrée</h2>
          <div
            className="dropzone"
            data-active={dragOver ? "true" : "false"}
            data-has-file={file ? "true" : "false"}
            onDragEnter={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragOver={(e) => e.preventDefault()}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
          >
            <input
              id={fileInputId}
              name="photo"
              type="file"
              accept={ACCEPT}
              aria-label="Choisir une photo d’objet"
              onChange={(e) => assignFile(e.target.files?.[0] ?? null)}
            />
            {previewUrl ? (
              <img
                className="preview"
                src={previewUrl}
                alt="Aperçu de la photo sélectionnée"
                width={280}
                height={210}
              />
            ) : (
              <>
                <p className="dropzone-title">Dépose une photo ici</p>
                <p className="dropzone-hint">JPEG, PNG ou WebP · 5&nbsp;Mo max</p>
              </>
            )}
          </div>

          <div className="field">
            <label htmlFor="modele-select">Modèle</label>
            <select
              id="modele-select"
              name="modele"
              autoComplete="off"
              value={modele}
              onChange={(e) => setModele(e.target.value)}
            >
              {models.length === 0 ? (
                <option value={defaultId || ""}>Chargement…</option>
              ) : (
                models.map((m) => (
                  <option key={m.id} value={m.id} disabled={m.statut !== "ready"}>
                    {m.label} · {m.statut}
                  </option>
                ))
              )}
            </select>
            {selected ? (
              <p className="dropzone-hint" translate="no">
                <StatusBadge status={selected.statut} /> {selected.id}
              </p>
            ) : null}
            {origineHref ? (
              <p className="dropzone-hint">
                <a
                  href={origineHref}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    color: "var(--accent)",
                    textDecoration: "underline",
                    textUnderlineOffset: "0.15em",
                  }}
                >
                  Modèle d’origine
                  <span className="live-region"> (nouvel onglet)</span>
                </a>
              </p>
            ) : null}
          </div>

          <div className="actions">
            <button
              type="button"
              className="btn btn-primary"
              disabled={!canPredict}
              onClick={onAnalyze}
            >
              {loading ? "Analyse…" : "Analyser"}
            </button>
            {!isAuthenticated ? (
              <span className="dropzone-hint">Renseigne le Bearer token pour prédire.</span>
            ) : null}
            {selected && selected.statut !== "ready" ? (
              <span className="dropzone-hint">
                Ce modèle n’est pas prêt sur ce runtime ({selected.statut}).
              </span>
            ) : null}
          </div>
        </div>

        <div className="panel">
          <h2>Résultat</h2>
          <div aria-live="polite">
            {!result ? (
              <p className="empty-state">
                Aucune prédiction pour l’instant. Le panneau se remplit après une analyse réussie.
              </p>
            ) : (
              <>
                <div className="result-hero">
                  <p className="result-category">{result.categorie}</p>
                  <p className="result-title">{result.titre_suggere}</p>
                  {result.description_suggeree ? (
                    <p className="result-title">{result.description_suggeree}</p>
                  ) : null}
                  <StatusBadge status={result.statut} />
                </div>
                <dl className="metrics">
                  <div className="metric">
                    <dt>Confiance</dt>
                    <dd>{formatConfidence(result.confiance)}</dd>
                  </div>
                  <div className="metric">
                    <dt>Latence</dt>
                    <dd>{formatMs(result.latence_ms)}</dd>
                  </div>
                  <div className="metric">
                    <dt>Modèle</dt>
                    <dd translate="no">{result.modele}</dd>
                  </div>
                  <div className="metric">
                    <dt>Coût estimé</dt>
                    <dd>{formatCostPerMillion(result.cout_estime_usd_par_million)}</dd>
                  </div>
                </dl>
                {result.propositions.length > 0 ? (
                  <>
                    <h2>Propositions</h2>
                    <ul className="list-proposals">
                      {result.propositions.map((p) => (
                        <li key={p.categorie}>
                          <span className="label">
                            {p.categorie}
                            <br />
                            <span className="dropzone-hint">{p.titre}</span>
                          </span>
                          <span className="score">{formatConfidence(p.score)}</span>
                        </li>
                      ))}
                    </ul>
                  </>
                ) : null}
              </>
            )}
          </div>
          <div style={{ marginTop: 16 }}>
            <CompteurSession />
          </div>
        </div>
      </div>
      <p className="live-region" aria-live="polite">
        {liveMsg}
      </p>
    </section>
  );
}
