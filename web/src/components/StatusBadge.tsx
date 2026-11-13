import type { ModelStatut, PredictionStatut } from "@/api/types";

type Status = ModelStatut | PredictionStatut;

const LABELS: Record<Status, string> = {
  ready: "ready",
  building: "building",
  space_only: "space_only",
  auto: "auto",
  a_confirmer: "a_confirmer",
};

export function StatusBadge({ status }: { status: Status }) {
  const tone =
    status === "ready" || status === "auto"
      ? "status-ready"
      : status === "building" || status === "a_confirmer"
        ? "status-building"
        : "status-space_only";

  return <span className={`status-pill ${tone}`}>{LABELS[status]}</span>;
}
