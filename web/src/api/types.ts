export type ModelStatut = "ready" | "building" | "space_only";
export type PredictionStatut = "auto" | "a_confirmer";

export interface ModelInfo {
  id: string;
  label: string;
  source: string;
  statut: ModelStatut;
  charge: boolean;
  accuracy: number | null;
  p50_ms: number | null;
  p95_ms: number | null;
  taille_mo: number | null;
  cout_estime_usd_par_million: number | null;
  space_only: boolean;
}

export interface ModelsResponse {
  defaut: string;
  modeles: ModelInfo[];
}

export interface HealthResponse {
  status: string;
  version: string;
  modele: string | null;
  modele_charge: boolean;
  modeles_charges: string[];
}

export interface TopClass {
  label: string;
  categorie: string;
  score: number;
}

export interface CategoryProposal {
  categorie: string;
  score: number;
  titre: string;
}

export interface PredictionResponse {
  categorie: string;
  titre_suggere: string;
  description_suggeree?: string;
  confiance: number;
  statut: PredictionStatut;
  top3: TopClass[];
  propositions: CategoryProposal[];
  modele: string;
  latence_ms: number;
  cout_estime_usd_par_million: number | null;
}

export interface ApiErrorBody {
  detail?: string | { msg?: string }[];
}
