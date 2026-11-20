import { useEffect, useState } from "react";
import { ApiClientError, fetchHealth } from "@/api/client";
import type { HealthResponse } from "@/api/types";
import { useAuth } from "@/hooks/useAuth";

export function GardeFousPage() {
  const { isAuthenticated } = useAuth();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchHealth()
      .then((h) => {
        if (!cancelled) {
          setHealth(h);
          setError(null);
        }
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(
          err instanceof ApiClientError ? err.message : "API health indisponible.",
        );
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="fade-in" aria-labelledby="guard-title">
      <p className="page-kicker">Garde-fous</p>
      <h1 id="guard-title" className="page-title">
        La photo est lue en mémoire puis oubliée.
      </h1>
      <div className="guard-zero">
        <p className="guard-zero-num">0</p>
        <p>fichier image écrit sur le disque.</p>
      </div>

      {error ? (
        <p className="alert" data-tone="error" role="alert">
          {error}
        </p>
      ) : null}

      <div className="guard-grid">
        <article className="panel">
          <h2>Mémoire</h2>
          <dl>
            <div className="guard-item">
              <dt>Lecture</dt>
              <dd>
                <code>await file.read()</code>, le temps de l’analyse, puis
                oubli.
              </dd>
            </div>
            <div className="guard-item">
              <dt>Logs</dt>
              <dd>Pas de contenu binaire ni de nom de fichier dans les logs.</dd>
            </div>
            <div className="guard-item">
              <dt>space_only</dt>
              <dd>
                CLIP et jobs GPU restent sur Space HF — pas chargés sur Azure
                CPU.
              </dd>
            </div>
          </dl>
        </article>

        <article className="panel">
          <h2>Authentification</h2>
          <dl>
            <div className="guard-item">
              <dt>Bearer token</dt>
              <dd>
                {isAuthenticated
                  ? "Présent en sessionStorage (onglet courant uniquement)."
                  : "Absent — /api/predict renverra 401."}
              </dd>
            </div>
            <div className="guard-item">
              <dt>Stockage</dt>
              <dd>
                <code>sessionStorage</code> uniquement — jamais dans le dépôt ni
                localStorage.
              </dd>
            </div>
          </dl>
        </article>

        <article className="panel">
          <h2>Limites de l’appel</h2>
          <dl>
            <div className="guard-item">
              <dt>Formats</dt>
              <dd>JPEG, PNG, WebP — MIME réel contrôlé côté serveur.</dd>
            </div>
            <div className="guard-item">
              <dt>Taille</dt>
              <dd>5&nbsp;Mo max · images trop petites / unicolores rejetées.</dd>
            </div>
            <div className="guard-item">
              <dt>Rate-limit</dt>
              <dd>Plafond par token (défaut 60 req/min) → HTTP 429.</dd>
            </div>
            <div className="guard-item">
              <dt>Allowlist modèles</dt>
              <dd>
                IDs catalogue seulement — pas d’ID Hugging Face arbitraire depuis
                le client.
              </dd>
            </div>
          </dl>
        </article>

        <article className="panel">
          <h2>Santé API</h2>
          {health ? (
            <dl>
              <div className="guard-item">
                <dt>Status</dt>
                <dd translate="no">{health.status}</dd>
              </div>
              <div className="guard-item">
                <dt>Version</dt>
                <dd translate="no">{health.version}</dd>
              </div>
              <div className="guard-item">
                <dt>Modèle défaut</dt>
                <dd translate="no">{health.modele ?? "—"}</dd>
              </div>
              <div className="guard-item">
                <dt>Chargés</dt>
                <dd translate="no">
                  {health.modeles_charges.length
                    ? health.modeles_charges.join(", ")
                    : "aucun"}
                </dd>
              </div>
            </dl>
          ) : (
            <p className="empty-state">Chargement de /api/health…</p>
          )}
        </article>
      </div>
    </section>
  );
}
