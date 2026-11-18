import type { CsTimerSolve, LabelSummary, Solve, VideoMeta } from "./types";

async function request<T>(method: string, url: string, body?: unknown): Promise<T> {
  const res = await fetch(url, {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
    } catch {
      /* not JSON */
    }
    throw new Error(`${res.status} ${detail}`);
  }
  return (res.status === 204 ? undefined : await res.json()) as T;
}

export interface SavedLabel {
  name: string;
  solve: Solve;
}

export const api = {
  videos: () => request<VideoMeta[]>("GET", "/api/videos"),
  mediaUrl: (name: string) => `/api/media/${encodeURIComponent(name)}`,
  labels: (video?: string) =>
    request<LabelSummary[]>(
      "GET",
      video ? `/api/labels?video=${encodeURIComponent(video)}` : "/api/labels",
    ),
  label: (name: string) => request<SavedLabel>("GET", `/api/labels/${encodeURIComponent(name)}`),
  createLabel: (solve: Solve) => request<SavedLabel>("POST", "/api/labels", solve),
  saveLabel: (name: string, solve: Solve) =>
    request<SavedLabel>("PUT", `/api/labels/${encodeURIComponent(name)}`, solve),
  deleteLabel: (name: string) =>
    request<void>("DELETE", `/api/labels/${encodeURIComponent(name)}`),
  cstimer: () => request<CsTimerSolve[]>("GET", "/api/cstimer"),
  analyze: (solve: Solve) => request<Solve>("POST", "/api/analyze", solve),
  deriveScramble: (moves: string[]) =>
    request<{ scramble: string }>("POST", "/api/scramble/derive", { moves }),
  validateMoves: (moves: string) =>
    request<{ ok: boolean; normalized: string | null; error: string | null }>(
      "POST",
      "/api/moves/validate",
      { moves },
    ),
};
