export type MetricKind = "measured" | "estimated";

export interface MetricProvenance {
  kind: MetricKind;
  /** Précision courte sous le badge, quand « mesuré » ne suffit pas. */
  qualifier?: string;
}

/**
 * Provenance figée, alignée sur docs/preuves/eval/catalog_metrics.json.
 * Un id inconnu reste « estimé » : on n’invente pas une mesure.
 * CLIP est mesuré, mais pas sur le même protocole que le ResNet de prod.
 */
const KNOWN: Record<string, MetricProvenance> = {
  "resnet50-onnx-int8": { kind: "measured" },
  "efficientnet-b0-onnx-int8": { kind: "estimated" },
  "mobilenet-v3-small-onnx-int8": { kind: "estimated" },
  "student-kd-mobilenet-int8": { kind: "estimated" },
  "clip-vit-b32": { kind: "measured", qualifier: "Space · zero-shot" },
};

export function metricProvenance(modelId: string): MetricProvenance {
  return KNOWN[modelId] ?? { kind: "estimated" };
}
