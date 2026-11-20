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
const MODEL_STEP = 4;
/** Assez long pour que l’œil suive une étape avant la suivante. */
const PIPELINE_STEP_MS = 720;

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

type PendingPrediction = {
  generation: number;
  response: PredictionResponse;
};

function prefersReducedMotion(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
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
  const requestGen = useRef(0);
  const pendingRef = useRef<PendingPrediction | null>(null);
  const filmCancelRef = useRef<(() => void) | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      filmCancelRef.current?.();
    };
  }, []);

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

  const commitResult = useCallback(
    (generation: number, response: PredictionResponse) => {
      if (!mountedRef.current || requestGen.current !== generation) return;
      setEtapeActive(LAST_ETAPE);
      setResult(response);
      ajouter(response.latence_ms, response.cout_estime_usd_par_million);
      setLiveMsg(
        `Résultat : ${response.categorie}, confiance ${formatConfidence(response.confiance)}.`,
      );
      setLoading(false);
    },
    [ajouter],
  );

  const stopFilm = useCallback(() => {
    filmCancelRef.current?.();
    filmCancelRef.current = null;
  }, []);

  const startFilm = useCallback(
    (generation: number) => {
      stopFilm();
      if (prefersReducedMotion()) {
        setEtapeActive(LAST_ETAPE);
        return;
      }
      let step = 0;
      let timer = 0;
      let cancelled = false;
      setEtapeActive(0);
      const tick = () => {
        if (cancelled || !mountedRef.current || requestGen.current !== generation) return;
        const pending = pendingRef.current;
        const ready = pending !== null && pending.generation === generation;
        if (step < MODEL_STEP || (ready && step < LAST_ETAPE)) {
          step += 1;
          setEtapeActive(step);
        }
        if (pending && pending.generation === generation && step >= LAST_ETAPE) {
          commitResult(generation, pending.response);
          return;
        }
        timer = window.setTimeout(tick, PIPELINE_STEP_MS);
      };
      timer = window.setTimeout(tick, PIPELINE_STEP_MS);
      filmCancelRef.current = () => {
        cancelled = true;
        window.clearTimeout(timer);
      };
    },
    [commitResult, stopFilm],
  );

  const assignFile = useCallback((next: File | null) => {
    stopFilm();
    requestGen.current += 1;
    pendingRef.current = null;
    setLoading(false);
    setEtapeActive(-1);
    setResult(null);
    setError(null);
    setFile(next);
    setPreviewUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return next ? URL.createObjectURL(next) : null;
    });
  }, [stopFilm]);

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
    pendingRef.current = null;
    setLoading(true);
    setError(null);
    setResult(null);
    setLiveMsg("Analyse en cours…");
    const reduced = prefersReducedMotion();
    startFilm(generation);
    try {
      const res = await predictImage(file, modele, token, ctrl.signal);
      if (requestGen.current !== generation || !mountedRef.current) return;
      if (reduced) {
        commitResult(generation, res);
        return;
      }
      pendingRef.current = { generation, response: res };
    } catch (err) {
      if (requestGen.current !== generation || !mountedRef.current) return;
      stopFilm();
      setEtapeActive(-1);
      setLoading(false);
      if (err instanceof DOMException && err.name === "AbortError") return;
      const msg =
        err instanceof ApiClientError
          ? err.status === 401
            ? "Token manquant ou invalide. Vérifie le Bearer token."
            : err.message
          : "Échec de la prédiction.";
      setError(msg);
      setLiveMsg(msg);
    }
  }

  return (
    <section className="fade-in" aria-labelledby="studio-title">
      <p className="page-kicker">Studio</p>
      <h1 id="studio-title" className="page-title">
        Une photo devient une annonce.
      </h1>
      <ol className="product-equation" aria-label="Ce que l’API renvoie">
        <li>Catégorie</li>
        <li>Titre</li>
        <li>Confiance</li>
        <li>
          <span className="product-status">auto</span>
          <span className="product-or">ou</span>
          <span className="product-status">a_confirmer</span>
        </li>
      </ol>

      <div className="studio-film">
        <SchemaRequete etapeActive={etapeActive} />
      </div>

      {error ? (
        <p className="alert" data-tone="error" role="alert">
          {error}
        </p>
      ) : null}

      <div className="grid-studio">
        <div className="panel">
          <h2>Photo</h2>
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
              <span className="dropzone-hint">Renseigne le jeton pour prédire.</span>
            ) : null}
            {selected && selected.statut !== "ready" ? (
              <span className="dropzone-hint">
                Ce modèle n’est pas prêt sur ce runtime ({selected.statut}).
              </span>
            ) : null}
          </div>
        </div>

        <div className="panel">
          <h2>Annonce</h2>
          <div aria-live="polite">
          {!result ? (
            <div className="result-hero" data-state="waiting">
              <p className="slot-label">Catégorie</p>
              <p className="result-category">—</p>
              <p className="slot-label">Titre</p>
              <p className="result-title">En attente d’une photo</p>
              <p className="slot-label">Confiance</p>
              <p className="result-title">—</p>
              <p className="slot-label">Statut</p>
              <p className="status-pair">
                <StatusBadge status="auto" />
                <span>ou</span>
                <StatusBadge status="a_confirmer" />
              </p>
            </div>
          ) : (
            <>
              <div className="result-hero">
                <p className="slot-label">Catégorie</p>
                <p className="result-category">{result.categorie}</p>
                <p className="slot-label">Titre</p>
                <p className="result-title">{result.titre_suggere}</p>
                <p className="slot-label">Description</p>
                {result.description_suggeree ? (
                  <p className="result-title">{result.description_suggeree}</p>
                ) : (
                  <p className="result-title">—</p>
                )}
                <p className="rule-caption">
                  Règle sur le titre et la catégorie. Pas un second modèle.
                </p>
                <p className="slot-label">Confiance</p>
                <p className="result-title">{formatConfidence(result.confiance)}</p>
                <p className="slot-label">Statut</p>
                <StatusBadge status={result.statut} />
              </div>
              <dl className="metrics">
                <div className="metric">
                  <dt>Inférence, cette requête</dt>
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
              <p className="latency-note">
                Référence it.&nbsp;4, inférence CPU&nbsp;: p50 21,5&nbsp;ms, p95 28,6&nbsp;ms.
                La requête complète dans le conteneur (it.&nbsp;5, 1&nbsp;vCPU) est à
                ~68&nbsp;ms p50&nbsp;: c’est ce chiffre qui entre dans la facture.
              </p>
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
