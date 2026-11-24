import raw from "./jury-eval.json?raw";

export type JuryRole = "comparable" | "hors_resultat" | "absent";
export type JuryMetricSource = "measured" | "estimated" | "excluded" | "unmeasured";
export type JuryBanc = "it4" | "ce_run" | "ce_run_clip";
export type JuryProtocolId = "focal" | "proxy";
export type JuryVignetteSource = "focus" | "cas-qualitatifs" | "predictions" | "absent";

export interface JuryModel {
  id: string;
  label: string;
  short: string;
  role: JuryRole;
  accuracy: number | null;
  n: number | null;
  metricSource: JuryMetricSource;
  qualifier: string;
  p50Ms: number | null;
  banc: JuryBanc | null;
  raisonId: string | null;
  scores: Record<string, number | null>;
}

export interface JuryCategory {
  label: string;
  n: number;
}

export interface JuryAccord {
  modeleA: string;
  modeleB: string;
  labelA: string;
  labelB: string;
  n: number;
  partMemeCategorie: number;
  desaccord: number;
}

export interface JuryProtocol {
  id: JuryProtocolId;
  titre: string;
  detail: string;
  n: number;
  headline: boolean;
  categories: JuryCategory[];
  models: JuryModel[];
  accord: JuryAccord[];
}

export interface JuryPred {
  id: string;
  label: string;
  predit: string;
  confiance: number | null;
  top1: string | null;
  correct: boolean;
}

export interface JuryCard {
  fichier: string;
  src: string;
  attendu: string;
  n: number | null;
  mecanisme: string | null;
  commentaire: string | null;
  predictions: JuryPred[];
}

export interface JuryGroup {
  attendu: string;
  n: number | null;
  desaccords: number;
  items: JuryCard[];
}

export interface JuryClipDetail {
  accuracy: number;
  n: number;
  headline: false;
  tailleMo: number | null;
}

export interface JuryWarning {
  modele: string;
  categorie: string;
  nProxy: number;
  accuracyProxy: number;
  nFocal: number;
  accuracyFocal: number;
}

export interface JuryArchive {
  vignettesSource: Exclude<JuryVignetteSource, "focus">;
  groupes: JuryGroup[];
}

export interface JuryView {
  seuil: number;
  protocoles: JuryProtocol[];
  clipDetaille: JuryClipDetail;
  avertissement: JuryWarning;
  vignettesSource: JuryVignetteSource;
  groupes: JuryGroup[];
  archive: JuryArchive | null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNum(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function isNumOrNull(value: unknown): value is number | null {
  return value === null || isNum(value);
}

function isRole(value: unknown): value is JuryRole {
  return value === "comparable" || value === "hors_resultat" || value === "absent";
}

function isMetric(value: unknown): value is JuryMetricSource {
  return (
    value === "measured" ||
    value === "estimated" ||
    value === "excluded" ||
    value === "unmeasured"
  );
}

function isBanc(value: unknown): value is JuryBanc | null {
  return value === null || value === "it4" || value === "ce_run" || value === "ce_run_clip";
}

function isProtocolId(value: unknown): value is JuryProtocolId {
  return value === "focal" || value === "proxy";
}

function isVignetteSource(value: unknown): value is JuryVignetteSource {
  return (
    value === "focus" ||
    value === "cas-qualitatifs" ||
    value === "predictions" ||
    value === "absent"
  );
}

function readScores(value: unknown): Record<string, number | null> | null {
  if (!isRecord(value)) return null;
  const scores: Record<string, number | null> = {};
  for (const [key, score] of Object.entries(value)) {
    if (!isNumOrNull(score)) return null;
    scores[key] = score;
  }
  return scores;
}

function readModel(value: unknown): JuryModel | null {
  if (!isRecord(value)) return null;
  const scores = readScores(value.scores);
  if (
    scores === null ||
    typeof value.id !== "string" ||
    typeof value.label !== "string" ||
    typeof value.short !== "string" ||
    !isRole(value.role) ||
    !isNumOrNull(value.accuracy) ||
    !isNumOrNull(value.n) ||
    !isMetric(value.metric_source) ||
    typeof value.qualifier !== "string" ||
    !isNumOrNull(value.p50_ms) ||
    !isBanc(value.banc) ||
    !(value.raison_id === null || typeof value.raison_id === "string")
  ) {
    return null;
  }
  if (value.role === "absent" || value.metric_source === "unmeasured") {
    if (value.accuracy !== null) return null;
  }
  return {
    id: value.id,
    label: value.label,
    short: value.short,
    role: value.role,
    accuracy: value.accuracy,
    n: value.n,
    metricSource: value.metric_source,
    qualifier: value.qualifier,
    p50Ms: value.p50_ms,
    banc: value.banc,
    raisonId: value.raison_id,
    scores,
  };
}

function readCategory(value: unknown): JuryCategory | null {
  if (!isRecord(value) || typeof value.label !== "string" || !isNum(value.n)) return null;
  return { label: value.label, n: value.n };
}

function readAccord(value: unknown): JuryAccord | null {
  if (!isRecord(value)) return null;
  if (
    typeof value.modele_a !== "string" ||
    typeof value.modele_b !== "string" ||
    typeof value.label_a !== "string" ||
    typeof value.label_b !== "string" ||
    !isNum(value.n) ||
    !isNum(value.part_meme_categorie) ||
    !isNum(value.desaccord)
  ) {
    return null;
  }
  return {
    modeleA: value.modele_a,
    modeleB: value.modele_b,
    labelA: value.label_a,
    labelB: value.label_b,
    n: value.n,
    partMemeCategorie: value.part_meme_categorie,
    desaccord: value.desaccord,
  };
}

function readProtocol(value: unknown): JuryProtocol | null {
  if (!isRecord(value)) return null;
  if (
    !isProtocolId(value.id) ||
    typeof value.titre !== "string" ||
    typeof value.detail !== "string" ||
    !isNum(value.n) ||
    typeof value.headline !== "boolean" ||
    !Array.isArray(value.categories) ||
    !Array.isArray(value.models) ||
    !Array.isArray(value.accord)
  ) {
    return null;
  }
  const categories: JuryCategory[] = [];
  for (const row of value.categories) {
    const category = readCategory(row);
    if (!category) return null;
    categories.push(category);
  }
  const models: JuryModel[] = [];
  for (const row of value.models) {
    const model = readModel(row);
    if (!model) return null;
    models.push(model);
  }
  const accord: JuryAccord[] = [];
  for (const row of value.accord) {
    const pair = readAccord(row);
    if (!pair) return null;
    accord.push(pair);
  }
  return {
    id: value.id,
    titre: value.titre,
    detail: value.detail,
    n: value.n,
    headline: value.headline,
    categories,
    models,
    accord,
  };
}

function readPred(value: unknown): JuryPred | null {
  if (!isRecord(value)) return null;
  if (
    typeof value.id !== "string" ||
    typeof value.label !== "string" ||
    typeof value.predit !== "string" ||
    !isNumOrNull(value.confiance) ||
    !(value.top1 === null || typeof value.top1 === "string") ||
    typeof value.correct !== "boolean"
  ) {
    return null;
  }
  return {
    id: value.id,
    label: value.label,
    predit: value.predit,
    confiance: value.confiance,
    top1: value.top1,
    correct: value.correct,
  };
}

function readCard(value: unknown): JuryCard | null {
  if (!isRecord(value)) return null;
  if (
    typeof value.fichier !== "string" ||
    typeof value.src !== "string" ||
    !value.src.startsWith("/jeu/") ||
    value.src.includes("..") ||
    typeof value.attendu !== "string" ||
    !isNumOrNull(value.n) ||
    !(value.mecanisme === null || typeof value.mecanisme === "string") ||
    !(value.commentaire === null || typeof value.commentaire === "string") ||
    !Array.isArray(value.predictions)
  ) {
    return null;
  }
  const predictions: JuryPred[] = [];
  for (const row of value.predictions) {
    const pred = readPred(row);
    if (!pred) return null;
    predictions.push(pred);
  }
  return {
    fichier: value.fichier,
    src: value.src,
    attendu: value.attendu,
    n: value.n,
    mecanisme: value.mecanisme,
    commentaire: value.commentaire,
    predictions,
  };
}

function readGroup(value: unknown): JuryGroup | null {
  if (!isRecord(value)) return null;
  if (
    typeof value.attendu !== "string" ||
    !isNumOrNull(value.n) ||
    !isNum(value.desaccords) ||
    !Array.isArray(value.items)
  ) {
    return null;
  }
  const items: JuryCard[] = [];
  for (const row of value.items) {
    const card = readCard(row);
    if (!card) return null;
    items.push(card);
  }
  return {
    attendu: value.attendu,
    n: value.n,
    desaccords: value.desaccords,
    items,
  };
}

function readGroups(value: unknown): JuryGroup[] | null {
  if (!Array.isArray(value)) return null;
  const groupes: JuryGroup[] = [];
  for (const row of value) {
    const group = readGroup(row);
    if (!group) return null;
    groupes.push(group);
  }
  return groupes;
}

function readWarning(value: unknown): JuryWarning | null {
  if (!isRecord(value)) return null;
  if (
    typeof value.modele !== "string" ||
    typeof value.categorie !== "string" ||
    !isNum(value.n_proxy) ||
    !isNum(value.accuracy_proxy) ||
    !isNum(value.n_focal) ||
    !isNum(value.accuracy_focal)
  ) {
    return null;
  }
  return {
    modele: value.modele,
    categorie: value.categorie,
    nProxy: value.n_proxy,
    accuracyProxy: value.accuracy_proxy,
    nFocal: value.n_focal,
    accuracyFocal: value.accuracy_focal,
  };
}

function readArchive(value: unknown): JuryArchive | null {
  if (!isRecord(value)) return null;
  if (
    (value.vignettes_source !== "cas-qualitatifs" &&
      value.vignettes_source !== "predictions" &&
      value.vignettes_source !== "absent") ||
    !Array.isArray(value.groupes)
  ) {
    return null;
  }
  const groupes = readGroups(value.groupes);
  if (!groupes) return null;
  return { vignettesSource: value.vignettes_source, groupes };
}

export function readJury(rawJson: string): JuryView | null {
  let parsed: unknown;
  try {
    parsed = JSON.parse(rawJson);
  } catch {
    return null;
  }
  if (!isRecord(parsed)) return null;
  const clip = parsed.clip_detaille;
  const avertissement = readWarning(parsed.avertissement_n20);
  if (
    !isNum(parsed.seuil) ||
    !avertissement ||
    !isRecord(clip) ||
    !isNum(clip.accuracy) ||
    !isNum(clip.n) ||
    clip.headline !== false ||
    !isNumOrNull(clip.taille_mo) ||
    !Array.isArray(parsed.protocoles) ||
    !isVignetteSource(parsed.vignettes_source)
  ) {
    return null;
  }
  const protocoles: JuryProtocol[] = [];
  for (const row of parsed.protocoles) {
    const protocol = readProtocol(row);
    if (!protocol) return null;
    protocoles.push(protocol);
  }
  const groupes = readGroups(parsed.groupes);
  if (!groupes) return null;
  if (parsed.archive_proxy !== undefined && !isRecord(parsed.archive_proxy)) return null;
  const archive = parsed.archive_proxy == null ? null : readArchive(parsed.archive_proxy);
  if (parsed.archive_proxy != null && !archive) return null;
  const headline = protocoles.filter((protocol) => protocol.headline);
  if (headline.length !== 1 || headline[0].id !== "focal") return null;
  return {
    seuil: parsed.seuil,
    protocoles,
    clipDetaille: {
      accuracy: clip.accuracy,
      n: clip.n,
      headline: false,
      tailleMo: clip.taille_mo,
    },
    avertissement,
    vignettesSource: parsed.vignettes_source,
    groupes,
    archive,
  };
}

export const juryView: JuryView | null = readJury(raw);
