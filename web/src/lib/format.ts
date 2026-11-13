const pct = new Intl.NumberFormat("fr-FR", {
  style: "percent",
  maximumFractionDigits: 1,
});

const num = new Intl.NumberFormat("fr-FR", {
  maximumFractionDigits: 1,
});

const usd = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 2,
});

export function formatAccuracy(value: number | null | undefined): string {
  if (value == null) return "—";
  return pct.format(value);
}

export function formatMs(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${num.format(value)}\u00a0ms`;
}

export function formatMb(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${num.format(value)}\u00a0Mo`;
}

export function formatCostPerMillion(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${usd.format(value)}/M`;
}

export function formatConfidence(value: number): string {
  return pct.format(value);
}
