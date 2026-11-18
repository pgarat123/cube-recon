import type { TimedMove, VideoMeta } from "./types";

/** Presentation time (ms) of frame ``n``: frames are at n * den / num seconds. */
export function frameToMs(n: number, v: VideoMeta): number {
  return Math.round(((n * 1000 * v.fps_den) / v.fps_num) * 1000) / 1000;
}

/** Index of the frame shown at time ``ms`` (nearest frame start). */
export function msToFrame(ms: number, v: VideoMeta): number {
  return Math.round((ms * v.fps_num) / (1000 * v.fps_den));
}

export function fmtTime(ms: number | null | undefined): string {
  if (ms == null || !Number.isFinite(ms)) return "–";
  const sign = ms < 0 ? "-" : "";
  const a = Math.abs(ms);
  const m = Math.floor(a / 60000);
  const s = (a % 60000) / 1000;
  return `${sign}${m}:${s.toFixed(3).padStart(6, "0")}`;
}

export function fmtSec(ms: number | null | undefined, digits = 2): string {
  if (ms == null || !Number.isFinite(ms)) return "–";
  return (ms / 1000).toFixed(digits);
}

export function fmtDuration(ms: number): string {
  const s = Math.floor(ms / 1000);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

/** Number of moves already started at time ``ms`` (moves are sorted by t_start_ms). */
export function movesBefore(moves: TimedMove[], ms: number): number {
  let n = 0;
  while (n < moves.length && moves[n].t_start_ms <= ms + 0.01) n++;
  return n;
}

// Keyboard-entry helpers. They only edit the move token text; parsing and cube state
// are done by the backend (cuberecon.cube) and by twisty-player for display.
const TOKEN_RE = /^([URFDLB]w?|[MES]|[xyz])(2|'|)$/;

export function togglePrime(token: string): string {
  const m = TOKEN_RE.exec(token);
  if (!m) return token;
  if (m[2] === "2") return token;
  return m[1] + (m[2] === "'" ? "" : "'");
}

export function toggleDouble(token: string): string {
  const m = TOKEN_RE.exec(token);
  if (!m) return token;
  return m[1] + (m[2] === "2" ? "" : "2");
}

export function toggleWide(token: string): string {
  const m = TOKEN_RE.exec(token);
  if (!m || !/^[URFDLB]/.test(m[1])) return token;
  const base = m[1].endsWith("w") ? m[1][0] : `${m[1]}w`;
  return base + m[2];
}

/** Move typed with a single key: faces and slices uppercase, rotations lowercase. */
export function keyToMove(key: string): string | null {
  const k = key.toLowerCase();
  if ("urfdlbmes".includes(k) && k.length === 1) return k.toUpperCase();
  if ("xyz".includes(k) && k.length === 1) return k;
  return null;
}

export function newId(): string {
  return crypto.randomUUID().replace(/-/g, "");
}

export const STEP_LABELS: Record<string, string> = {
  inspection: "Inspection",
  cross: "Croix",
  f2l_1: "F2L 1",
  f2l_2: "F2L 2",
  f2l_3: "F2L 3",
  f2l_4: "F2L 4",
  oll: "OLL",
  pll: "PLL",
  auf: "AUF",
};

export const STEP_COLORS: Record<string, string> = {
  inspection: "#6b7280",
  cross: "#e5e7eb",
  f2l_1: "#60a5fa",
  f2l_2: "#38bdf8",
  f2l_3: "#22d3ee",
  f2l_4: "#2dd4bf",
  oll: "#facc15",
  pll: "#f472b6",
  auf: "#a78bfa",
};
