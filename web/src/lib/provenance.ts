export type MetricKind = "measured" | "estimated" | "excluded";

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
  "resnet50-onnx-int8": { kind: "measured", qualifier: "historique it. 4" },
  "efficientnet-b0-onnx-int8": { kind: "measured", qualifier: "200 photos, ce run" },
  "mobilenet-v3-small-onnx-int8": { kind: "excluded", qualifier: "pas un résultat" },
  "student-kd-mobilenet-int8": { kind: "excluded", qualifier: "pas un résultat" },
  "clip-vit-b32": { kind: "measured", qualifier: "zero-shot, vocab générique" },
};

export function metricProvenance(modelId: string): MetricProvenance {
  return KNOWN[modelId] ?? { kind: "estimated" };
}
