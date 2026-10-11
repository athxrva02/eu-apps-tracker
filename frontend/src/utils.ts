import type { Timestamp } from "./types";

export const countries: Record<string, string> = {
  NL: "Netherlands",
  DE: "Germany",
  GB: "United Kingdom",
  CH: "Switzerland",
  FR: "France",
  BE: "Belgium",
  DK: "Denmark",
  SE: "Sweden",
  ES: "Spain",
  IT: "Italy",
  IE: "Ireland",
  PL: "Poland",
  AT: "Austria",
  NO: "Norway",
  FI: "Finland",
  PT: "Portugal",
  CZ: "Czechia",
  LU: "Luxembourg",
  HU: "Hungary",
  RO: "Romania",
  GR: "Greece",
  BG: "Bulgaria",
  HR: "Croatia",
  SK: "Slovakia",
  SI: "Slovenia",
  EE: "Estonia",
  LV: "Latvia",
  LT: "Lithuania",
  IS: "Iceland",
  MT: "Malta",
  CY: "Cyprus",
};
export function dateTime(
  value: string | null,
  timezone = "Europe/Berlin",
): string {
  if (!value) return "Not yet";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "Unknown"
    : date.toLocaleString("en-GB", {
        timeZone: timezone,
        day: "numeric",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
      });
}
export function publicationLabel(
  evidence: Timestamp | undefined,
  timezone = "Europe/Berlin",
): string {
  if (!evidence?.start) return "Publication unknown";
  if (evidence.precision === "date")
    return `Published ${evidence.raw} · date only`;
  return `Published ${dateTime(evidence.start, timezone)}`;
}
export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong";
}
export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  const token = sessionStorage.getItem("agent-token");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body && !(options.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  const response = await fetch(`/api/v1${path}`, { ...options, headers });
  if (!response.ok) {
    const body = await response
      .json()
      .catch(() => ({ detail: response.statusText }));
    throw new Error(
      typeof body.detail === "string"
        ? body.detail
        : "Check the input fields and try again",
    );
  }
  return response.json() as Promise<T>;
}
