import { useCallback, useSyncExternalStore } from "react";

const STORAGE_KEY = "marketplace-session-conso";

interface SessionTotals {
  images: number;
  latenceTotaleMs: number;
  usdEstime: number;
}

export interface SessionConso extends SessionTotals {
  ajouter: (latenceMs: number, usdParMillion: number | null) => void;
}

const EMPTY: SessionTotals = {
  images: 0,
  latenceTotaleMs: 0,
  usdEstime: 0,
};

function finiteNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function readTotals(): SessionTotals {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...EMPTY };
    const parsed: unknown = JSON.parse(raw);
    if (typeof parsed !== "object" || parsed === null) return { ...EMPTY };
    const record = parsed as Record<string, unknown>;
    return {
      images: finiteNumber(record.images) ?? 0,
      latenceTotaleMs: finiteNumber(record.latenceTotaleMs) ?? 0,
      usdEstime: finiteNumber(record.usdEstime) ?? 0,
    };
  } catch {
    return { ...EMPTY };
  }
}

function writeTotals(totals: SessionTotals): void {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(totals));
  } catch {
    /* sessionStorage unavailable */
  }
}

let snapshot: SessionTotals = readTotals();
const listeners = new Set<() => void>();

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function getSnapshot(): SessionTotals {
  return snapshot;
}

function publish(next: SessionTotals): void {
  snapshot = next;
  writeTotals(next);
  for (const listener of listeners) listener();
}

function applyAddition(
  current: SessionTotals,
  latenceMs: number,
  usdParMillion: number | null,
): SessionTotals {
  const latencyDelta = Number.isFinite(latenceMs) ? latenceMs : 0;
  const usdDelta =
    typeof usdParMillion === "number" && Number.isFinite(usdParMillion)
      ? usdParMillion / 1_000_000
      : 0;
  return {
    images: current.images + 1,
    latenceTotaleMs: current.latenceTotaleMs + latencyDelta,
    usdEstime: current.usdEstime + usdDelta,
  };
}

export function useSessionConso(): SessionConso {
  const totals = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
  const ajouter = useCallback((latenceMs: number, usdParMillion: number | null) => {
    publish(applyAddition(snapshot, latenceMs, usdParMillion));
  }, []);

  return {
    images: totals.images,
    latenceTotaleMs: totals.latenceTotaleMs,
    usdEstime: totals.usdEstime,
    ajouter,
  };
}
