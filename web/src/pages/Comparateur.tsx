import { useEffect, useState } from "react";
import { ApiClientError, fetchModels } from "@/api/client";
import type { ModelInfo } from "@/api/types";
import { StatusBadge } from "@/components/StatusBadge";
import {
  formatAccuracy,
  formatCostPerMillion,
  formatMb,
  formatMs,
} from "@/lib/format";

export function ComparateurPage() {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [defaut, setDefaut] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchModels()
      .then((res) => {
        if (cancelled) return;
        setModels(res.modeles);
        setDefaut(res.defaut);
        setError(null);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(
          err instanceof ApiClientError
            ? err.message
            : "Impossible de charger les métriques modèles.",
        );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="fade-in" aria-labelledby="cmp-title">
      <h1 id="cmp-title" className="page-title">
        Comparateur
      </h1>
      <p className="page-lead">
        Perf, coût et taille du catalogue allowlisté. Défaut API&nbsp;:{" "}
        <code translate="no">{defaut || "…"}</code>
      </p>

      {error ? (
        <p className="alert" data-tone="error" role="alert">
          {error}
        </p>
      ) : null}

      {loading ? (
        <p className="empty-state">Chargement du catalogue…</p>
      ) : (
        <div className="table-wrap">
          <table className="compare-table">
            <thead>
              <tr>
                <th scope="col">Modèle</th>
                <th scope="col">Statut</th>
                <th scope="col">Accuracy</th>
                <th scope="col">p50</th>
                <th scope="col">p95</th>
                <th scope="col">Taille</th>
                <th scope="col">$/M</th>
              </tr>
            </thead>
            <tbody>
              {models.map((m) => (
                <tr key={m.id}>
                  <td>
                    <strong>{m.label}</strong>
                    <span className="model-id" translate="no">
                      {m.id}
                    </span>
                  </td>
                  <td>
                    <StatusBadge status={m.statut} />
                  </td>
                  <td className="num">{formatAccuracy(m.accuracy)}</td>
                  <td className="num">{formatMs(m.p50_ms)}</td>
                  <td className="num">{formatMs(m.p95_ms)}</td>
                  <td className="num">{formatMb(m.taille_mo)}</td>
                  <td className="num">{formatCostPerMillion(m.cout_estime_usd_par_million)}</td>
                </tr>
              ))}
              {models.length === 0 ? (
                <tr>
                  <td colSpan={7}>Aucun modèle dans le catalogue.</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
