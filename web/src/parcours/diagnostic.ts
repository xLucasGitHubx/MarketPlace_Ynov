/**
 * Performance diagnosis shown in Parcours → Mesure.
 * Numbers are copied from the proof files named on each constant.
 * Unmeasured notebook figures stay absent: the UI marks them, it does not invent them.
 */

export const DIAGNOSTIC_PARTS = [
  {
    id: "qualite",
    nav: "Qualité",
    title: "Une photo, une catégorie.",
    course: "Hors notebook. Accuracy déjà montrée au jury.",
  },
  {
    id: "question",
    nav: "Question",
    title: "Mesurer avant d’optimiser.",
    course: "Introduction et §12",
  },
  {
    id: "modele",
    nav: "Modèle",
    title: "ResNet-50, sur CPU.",
    course: "§1, §2 et §2.1",
  },
  {
    id: "controle",
    nav: "Contrôle",
    title: "Le contrôle se fait au Studio.",
    course: "§2, figure du top 5",
  },
  {
    id: "entrees",
    nav: "Entrées",
    title: "Deux entrées, deux questions.",
    course: "§3",
  },
  {
    id: "indicateurs",
    nav: "Indicateurs",
    title: "Quatre questions, quatre réponses.",
    course: "§4",
  },
  {
    id: "protocole",
    nav: "Protocole",
    title: "Le chrono ne démarre pas à froid.",
    course: "§5",
  },
  {
    id: "percentiles",
    nav: "Percentiles",
    title: "La moyenne cache la queue.",
    course: "§5.1",
  },
  {
    id: "debit",
    nav: "Débit",
    title: "Beaucoup d’images, ou une réponse courte.",
    course: "§6",
  },
  {
    id: "charge",
    nav: "Charge",
    title: "Le débit plafonne. L’attente, non.",
    course: "§6.1, analogue HTTP",
  },
  {
    id: "memoire",
    nav: "Mémoire",
    title: "24,9 Mo ne font pas tourner le service.",
    course: "§7 et §7.1",
  },
  {
    id: "chaine",
    nav: "Chaîne",
    title: "Deux chronos. On ne les soustrait pas.",
    course: "§8 et §8.1",
  },
  {
    id: "reference",
    nav: "Référence",
    title: "L’int8 dynamique est le mauvais gain.",
    course: "§9",
  },
  {
    id: "trace",
    nav: "Trace",
    title: "Les JSON tiennent lieu de CSV.",
    course: "§9.1",
  },
  {
    id: "retenir",
    nav: "Retenir",
    title: "Cinq idées, déjà décidées.",
    course: "§10",
  },
  {
    id: "questions",
    nav: "Questions",
    title: "Ce que le cours fait demander.",
    course: "§11",
  },
] as const;

export type DiagnosticPartId = (typeof DIAGNOSTIC_PARTS)[number]["id"];

export function partIndex(id: string | null): number {
  if (!id) return 0;
  const index = DIAGNOSTIC_PARTS.findIndex((part) => part.id === id);
  return index >= 0 ? index : 0;
}

export function fr1(value: number): string {
  return value.toLocaleString("fr-FR", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  });
}

export function frMs(value: number): string {
  return `${fr1(value)}\u00a0ms`;
}

export function frReq(value: number): string {
  return `${fr1(value)}\u00a0req/s`;
}

export function frPct(ratio: number): string {
  const pct = Math.round(ratio * 1000) / 10;
  return `${pct.toLocaleString("fr-FR", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })}\u00a0%`;
}

/** docs/preuves/eval/eval-onnx-int8-static.json */
export const INT8_STATIC = {
  accuracy: 0.685,
  p50: 21.5,
  p95: 28.6,
  mean: 22.3,
  n: 200,
  threshold: 0.6,
  file: "docs/preuves/eval/eval-onnx-int8-static.json",
} as const;

/** docs/preuves/eval/eval-pytorch-fp32.json — file size from it4, not this JSON. */
export const PYTORCH_FP32 = {
  accuracy: 0.69,
  p50: 105.2,
  p95: 141.6,
  mean: 108.8,
  fileMb: "97,7 Mo",
  file: "docs/preuves/eval/eval-pytorch-fp32.json",
} as const;

/** docs/preuves/eval/eval-onnx-fp32.json and docs/preuves/eval/onnx-export-report.json */
export const ONNX_FP32 = {
  accuracy: 0.69,
  p50: 56.2,
  p95: 72.7,
  mean: 57.1,
  fileMb: "97,4 Mo",
  file: "docs/preuves/eval/eval-onnx-fp32.json",
} as const;

/** docs/preuves/eval/eval-onnx-int8-dynamic.json and onnx-export-report.json */
export const INT8_DYNAMIC = {
  accuracy: 0.62,
  p50: 358.6,
  p95: 442.5,
  mean: 358.1,
  fileMb: "24,6 Mo",
  file: "docs/preuves/eval/eval-onnx-int8-dynamic.json",
} as const;

export const BASELINE = [
  {
    id: "pytorch-fp32",
    label: "PyTorch fp32",
    decision: "Référence",
    tone: "neutral",
    accuracy: PYTORCH_FP32.accuracy,
    p50: PYTORCH_FP32.p50,
    p95: PYTORCH_FP32.p95,
    mean: PYTORCH_FP32.mean,
    fileMb: PYTORCH_FP32.fileMb,
    file: PYTORCH_FP32.file,
  },
  {
    id: "onnx-fp32",
    label: "ONNX fp32",
    decision: "Export",
    tone: "neutral",
    accuracy: ONNX_FP32.accuracy,
    p50: ONNX_FP32.p50,
    p95: ONNX_FP32.p95,
    mean: ONNX_FP32.mean,
    fileMb: ONNX_FP32.fileMb,
    file: ONNX_FP32.file,
  },
  {
    id: "int8-dynamic",
    label: "ONNX int8 dynamique",
    decision: "Écartée",
    tone: "bad",
    accuracy: INT8_DYNAMIC.accuracy,
    p50: INT8_DYNAMIC.p50,
    p95: INT8_DYNAMIC.p95,
    mean: INT8_DYNAMIC.mean,
    fileMb: INT8_DYNAMIC.fileMb,
    file: INT8_DYNAMIC.file,
  },
  {
    id: "int8-static",
    label: "ONNX int8 statique",
    decision: "Retenue",
    tone: "keep",
    accuracy: INT8_STATIC.accuracy,
    p50: INT8_STATIC.p50,
    p95: INT8_STATIC.p95,
    mean: INT8_STATIC.mean,
    fileMb: "24,9 Mo",
    file: INT8_STATIC.file,
  },
] as const;

/** docs/preuves/charge/onnx-int8-1vcpu-ramp.json */
export const CPU1_RAMP = [
  { users: 1, rps: 17.87, p50: 67.9, p95: 90.3, p99: 130.7 },
  { users: 2, rps: 21.23, p50: 93.9, p95: 161.5, p99: 177.2 },
  { users: 4, rps: 22.77, p50: 177.5, p95: 283.4, p99: 372.4 },
  { users: 8, rps: 24.13, p50: 321.6, p95: 495.0, p99: 575.1 },
  { users: 16, rps: 28.17, p50: 586.2, p95: 802.0, p99: 923.8 },
] as const;

/** docs/preuves/charge/onnx-int8-ramp.json — 2 vCPU shared with the generator. */
export const CPU2_PEAK = { users: 20, rps: 49.64, p50: 389.6 } as const;
export const CPU2_DROP = { users: 40, rps: 45.08, p50: 895.3 } as const;

/** docs/preuves/charge/onnx-int8-rate.json */
export const RATE_10 = {
  n: 3000,
  rps: 10.0,
  p50: 30.9,
  p95: 50.9,
  p99: 81.8,
  mean: 33.5,
} as const;

export const SOURCE_IT4 = "docs/preuves/it4-optimisation.md";
export const SOURCE_IT5 = "docs/preuves/it5-charge.md";
export const SOURCE_CPU1 = "docs/preuves/charge/onnx-int8-1vcpu-ramp.json";
export const SOURCE_CPU2 = "docs/preuves/charge/onnx-int8-ramp.json";
export const SOURCE_RATE = "docs/preuves/charge/onnx-int8-rate.json";
export const SOURCE_EXPORT = "docs/preuves/eval/onnx-export-report.json";
export const SOURCE_EVALUATE = "scripts/evaluate.py";
export const SOURCE_MODEL = "app/model.py";
export const SOURCE_IT8 = "docs/preuves/it8-mlflow.md";

export function rampAt(users: number): (typeof CPU1_RAMP)[number] {
  const row = CPU1_RAMP.find((item) => item.users === users);
  if (!row) {
    throw new Error(`Missing 1 vCPU ramp row for ${users} users.`);
  }
  return row;
}

export const HF_RESNET50 = "https://huggingface.co/microsoft/resnet-50";
export const HF_RESNET18 = "https://huggingface.co/microsoft/resnet-18";
