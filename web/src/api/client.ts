import type {
  ApiErrorBody,
  HealthResponse,
  ModelsResponse,
  PredictionResponse,
} from "./types";

const TOKEN_KEY = "marketplace_api_token";

/** Base API : vide = same-origin (prod StaticFiles) ou proxy Vite en dev. */
export function apiBase(): string {
  const raw = import.meta.env.VITE_API_BASE;
  if (raw === undefined || raw === null || raw === "") return "";
  return raw.replace(/\/$/, "");
}

export function getStoredToken(): string {
  try {
    return sessionStorage.getItem(TOKEN_KEY) ?? "";
  } catch {
    return "";
  }
}

export function setStoredToken(token: string): void {
  try {
    if (token.trim()) sessionStorage.setItem(TOKEN_KEY, token.trim());
    else sessionStorage.removeItem(TOKEN_KEY);
  } catch {
    /* private mode */
  }
}

export function clearStoredToken(): void {
  setStoredToken("");
}

async function parseError(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as ApiErrorBody;
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail) && body.detail[0]?.msg) return body.detail[0].msg!;
  } catch {
    /* ignore */
  }
  return `Erreur HTTP ${res.status}`;
}

export class ApiClientError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
  }
}

export async function fetchModels(): Promise<ModelsResponse> {
  const res = await fetch(`${apiBase()}/api/models`);
  if (!res.ok) throw new ApiClientError(res.status, await parseError(res));
  return res.json() as Promise<ModelsResponse>;
}

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${apiBase()}/api/health`);
  if (!res.ok) throw new ApiClientError(res.status, await parseError(res));
  return res.json() as Promise<HealthResponse>;
}

export async function predictImage(
  file: File,
  modele: string,
  token: string,
  signal?: AbortSignal,
): Promise<PredictionResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("modele", modele);

  const res = await fetch(`${apiBase()}/api/predict`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: form,
    signal,
  });

  if (!res.ok) throw new ApiClientError(res.status, await parseError(res));
  return res.json() as Promise<PredictionResponse>;
}
