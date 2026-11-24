import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiClientError, fetchModels } from "@/api/client";
import type { ModelInfo } from "@/api/types";
import { StatusBadge } from "@/components/StatusBadge";
import {
  formatAccuracy,
  formatCostPerMillion,
  formatMb,
  formatMs,
} from "@/lib/format";
import { JuryEval } from "@/components/JuryEval";
import { metricProvenance, type MetricKind } from "@/lib/provenance";

const PROOF_LABEL: Record<MetricKind, string> = {
  measured: "mesuré",
  estimated: "estimé",
  excluded: "écarté",
};

function ProvenanceBadge({ modelId }: { modelId: string }) {
  const provenance = metricProvenance(modelId);
  const kind: MetricKind = provenance.kind;
  return (
    <span className="provenance-cell">
      <span className={`provenance provenance-${kind}`}>
        {PROOF_LABEL[kind]}
      </span>
      {provenance.qualifier ? (
        <span className="provenance-sub">{provenance.qualifier}</span>
      ) : null}
    </span>
  );
}

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
      <p className="page-kicker">Comparateur</p>
      <h1 id="cmp-title" className="page-title">
        Mesuré et estimé ne se comparent pas.
      </h1>
      <p className="page-lead">
        Défaut API&nbsp;: <code translate="no">{defaut || "…"}</code>
      </p>

      <JuryEval />

      <p className="page-lead">
        <Link className="inline-link" to="/parcours?etape=mesure&partie=reference">
          Référence d’optimisation
        </Link>
        , PyTorch contre ONNX&nbsp;: parcours, étape Mesure. Ce tableau-ci
        compare le catalogue, pas les quatre variantes du même ResNet.
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
                <th scope="col">Preuve</th>
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
                <tr key={m.id} data-model={m.id}>
                  <td>
                    <strong>{m.label}</strong>
                    <span className="model-id" translate="no">
                      {m.id}
                    </span>
                  </td>
                  <td>
                    <ProvenanceBadge modelId={m.id} />
                  </td>
                  <td>
                    <StatusBadge status={m.statut} />
                  </td>
                  <td className="num">
                    {metricProvenance(m.id).kind === "excluded"
                      ? "—"
                      : formatAccuracy(m.accuracy)}
                  </td>
                  <td className="num">
                    {metricProvenance(m.id).kind === "excluded" ? "—" : formatMs(m.p50_ms)}
                  </td>
                  <td className="num">
                    {metricProvenance(m.id).kind === "excluded" ? "—" : formatMs(m.p95_ms)}
                  </td>
                  <td className="num">
                    {metricProvenance(m.id).kind === "excluded" ? "—" : formatMb(m.taille_mo)}
                  </td>
                  <td className="num">
                    {metricProvenance(m.id).kind === "excluded"
                      ? "—"
                      : formatCostPerMillion(m.cout_estime_usd_par_million)}
                  </td>
                </tr>
              ))}
              {models.length === 0 ? (
                <tr>
                  <td colSpan={8}>Aucun modèle dans le catalogue.</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
