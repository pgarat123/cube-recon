import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "./api";
import { AnalysisPanel } from "./components/AnalysisPanel";
import { CubeView } from "./components/CubeView";
import { MoveList } from "./components/MoveList";
import { Scrubber, Timeline } from "./components/Timeline";
import { VideoPlayer, type PlayerHandle } from "./components/VideoPlayer";
import type { CsTimerSolve, LabelSummary, ScrambleSource, Segment, Solve, Stats, TimedMove, VideoMeta } from "./types";
import {
  fmtDuration,
  fmtSec,
  fmtTime,
  frameToMs,
  keyToMove,
  movesBefore,
  msToFrame,
  newId,
  toggleDouble,
  togglePrime,
  toggleWide,
} from "./util";

const RATES = [1, 0.5, 0.25, 0.1];
const IDLE_MS = 60_000;
const DEFAULT_SCHEME = { U: "white", F: "green", R: "red", D: "yellow", L: "orange", B: "blue" };

function emptySolve(video: VideoMeta): Solve {
  return {
    id: newId(),
    created_at: new Date().toISOString().replace(/\.\d{3}Z$/, "+00:00"),
    video: {
      path: `videos/${video.name}`,
      fps: video.fps,
      width: video.width,
      height: video.height,
      duration_ms: video.duration_ms,
    },
    scramble: "",
    color_scheme: { ...DEFAULT_SCHEME },
    calibration: null,
    moves: [],
    segments: [],
    stats: {},
    solve_window: null,
    scramble_source: "manual",
    labeling_time_ms: 0,
  };
}

function insertSorted(moves: TimedMove[], m: TimedMove): [TimedMove[], number] {
  const i = movesBefore(moves, m.t_start_ms);
  return [[...moves.slice(0, i), m, ...moves.slice(i)], i];
}

function isTyping(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null;
  return !!el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.tagName === "SELECT");
}

export function App() {
  const [videos, setVideos] = useState<VideoMeta[]>([]);
  const [videoName, setVideoName] = useState<string | null>(null);
  const [labels, setLabels] = useState<LabelSummary[]>([]);
  const [cstimer, setCstimer] = useState<CsTimerSolve[]>([]);
  const [labelName, setLabelName] = useState<string | null>(null);
  const [solve, setSolve] = useState<Solve | null>(null);
  const [dirty, setDirty] = useState(false);
  const [frame, setFrame] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [rateIdx, setRateIdx] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  const [analysis, setAnalysis] = useState<{ segments: Segment[]; stats: Stats } | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [scrambleError, setScrambleError] = useState<string | null>(null);
  const [timerOn, setTimerOn] = useState(true);
  const [idle, setIdle] = useState(false);
  const [status, setStatus] = useState<{ text: string; error?: boolean } | null>(null);
  const history = useRef<Solve[]>([]);
  const player = useRef<PlayerHandle>(null);
  const lastActivity = useRef(Date.now());
  const revision = useRef(0);

  const video = videos.find((v) => v.name === videoName) ?? null;
  const currentMs = video ? frameToMs(frame, video) : 0;
  const moves = solve?.moves ?? [];
  const doneCount = movesBefore(moves, currentMs);
  const segments = analysis?.segments ?? [];
  const stats = analysis?.stats ?? {};

  const flash = (text: string, error = false) => setStatus({ text, error });

  // ---------- loading ----------
  const refreshLabels = useCallback(async (name: string) => {
    try {
      setLabels(await api.labels(name));
    } catch (e) {
      flash(String(e), true);
    }
  }, []);

  useEffect(() => {
    api
      .videos()
      .then((vs) => {
        setVideos(vs);
        let saved: string | null = null;
        try {
          saved = localStorage.getItem("cuberecon.video");
        } catch {
          /* storage unavailable */
        }
        const first = vs.find((v) => v.name === saved) ?? vs[0];
        if (first) setVideoName(first.name);
      })
      .catch((e) => flash(`API injoignable : ${e}`, true));
    api
      .cstimer()
      .then(setCstimer)
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!videoName) return;
    try {
      localStorage.setItem("cuberecon.video", videoName);
    } catch {
      /* storage unavailable */
    }
    void refreshLabels(videoName);
  }, [videoName, refreshLabels]);

  const confirmDiscard = () => !dirty || window.confirm("Modifications non enregistrées. Les abandonner ?");

  const selectVideo = (name: string) => {
    if (!confirmDiscard()) return;
    setVideoName(name);
    setSolve(null);
    setLabelName(null);
    setDirty(false);
    setAnalysis(null);
    setFrame(0);
    history.current = [];
  };

  const seekMs = (ms: number) => {
    if (video) player.current?.seekFrame(msToFrame(ms, video));
  };

  const openLabel = async (name: string) => {
    if (!confirmDiscard()) return;
    try {
      const { solve: s } = await api.label(name);
      const vname = s.video ? s.video.path.split("/").pop()! : videoName;
      if (vname && vname !== videoName) setVideoName(vname);
      setSolve(s);
      setLabelName(name);
      setDirty(false);
      setSelected(null);
      history.current = [];
      const start = s.solve_window?.t_start_ms ?? s.moves[0]?.t_start_ms;
      if (start !== undefined) setTimeout(() => seekMs(start), 50);
      flash(`${name} chargé`);
    } catch (e) {
      flash(String(e), true);
    }
  };

  const newSolve = () => {
    if (!video || !confirmDiscard()) return;
    setSolve(emptySolve(video));
    setLabelName(null);
    setDirty(false);
    setSelected(null);
    setAnalysis(null);
    history.current = [];
    flash("Nouvelle solve : marque le début avec i");
  };

  // ---------- editing ----------
  const update = (fn: (s: Solve) => Solve, undoable = true) => {
    if (!video) return;
    setSolve((prev) => {
      const base = prev ?? emptySolve(video);
      if (undoable) {
        history.current.push(base);
        if (history.current.length > 300) history.current.shift();
      }
      return fn(base);
    });
    revision.current++;
    setDirty(true);
  };

  const undo = () => {
    const prev = history.current.pop();
    if (!prev) return;
    // Keep the labeling time running: undo restores content, not the chrono.
    setSolve((cur) => ({ ...prev, labeling_time_ms: cur?.labeling_time_ms ?? prev.labeling_time_ms }));
    revision.current++;
    setDirty(true);
    setSelected((i) => (i === null ? null : Math.min(i, prev.moves.length - 1)));
  };

  const addMove = (token: string) => {
    const m: TimedMove = { move: token, t_start_ms: currentMs, t_end_ms: currentMs, confidence: 1, source: "manual" };
    const [next, i] = insertSorted(moves, m);
    update((s) => ({ ...s, moves: next }));
    setSelected(i);
  };

  const editSelected = (fn: (t: string) => string) => {
    if (selected === null || !moves[selected]) return;
    const token = fn(moves[selected].move);
    if (token === moves[selected].move) return;
    update((s) => ({ ...s, moves: s.moves.map((m, i) => (i === selected ? { ...m, move: token } : m)) }));
  };

  const editToken = async (i: number, token: string) => {
    try {
      const r = await api.validateMoves(token);
      if (!r.ok || !r.normalized || r.normalized.includes(" ")) {
        flash(`Mouvement invalide : ${token}`, true);
        return;
      }
      update((s) => ({ ...s, moves: s.moves.map((m, j) => (j === i ? { ...m, move: r.normalized! } : m)) }));
    } catch (e) {
      flash(String(e), true);
    }
  };

  const deleteMove = (i: number) => {
    update((s) => ({ ...s, moves: s.moves.filter((_, j) => j !== i) }));
    // Select the move before the deleted one, so Backspace can be repeated.
    setSelected(moves.length > 1 ? Math.max(0, i - 1) : null);
  };

  const retimeSelected = (endOnly: boolean) => {
    if (selected === null || !moves[selected]) return;
    const m = moves[selected];
    if (endOnly) {
      if (currentMs < m.t_start_ms) {
        flash("La fin doit être après le début du mouvement", true);
        return;
      }
      update((s) => ({ ...s, moves: s.moves.map((x, i) => (i === selected ? { ...x, t_end_ms: currentMs } : x)) }));
      return;
    }
    const dur = m.t_end_ms - m.t_start_ms;
    const rest = moves.filter((_, i) => i !== selected);
    const [next, i] = insertSorted(rest, { ...m, t_start_ms: currentMs, t_end_ms: currentMs + dur });
    update((s) => ({ ...s, moves: next }));
    setSelected(i);
  };

  const setWindowBound = (which: "start" | "end") => {
    update((s) => {
      const w = s.solve_window ?? { t_start_ms: currentMs, t_end_ms: currentMs };
      let { t_start_ms, t_end_ms } = w;
      if (which === "start") {
        t_start_ms = currentMs;
        if (t_end_ms < t_start_ms) t_end_ms = t_start_ms;
      } else {
        t_end_ms = currentMs;
        if (t_start_ms > t_end_ms) t_start_ms = t_end_ms;
      }
      return { ...s, solve_window: { t_start_ms, t_end_ms } };
    });
  };

  const selectMove = (i: number) => {
    if (i < 0 || i >= moves.length) return;
    setSelected(i);
    seekMs(moves[i].t_start_ms);
  };

  const deriveScramble = async () => {
    if (!moves.length) return;
    try {
      const { scramble } = await api.deriveScramble(moves.map((m) => m.move));
      update((s) => ({ ...s, scramble, scramble_source: "derived" }));
      flash("Scramble déduit de la solution");
    } catch (e) {
      flash(String(e), true);
    }
  };

  const save = async () => {
    if (!solve) return;
    const rev = revision.current;
    try {
      const r = labelName ? await api.saveLabel(labelName, solve) : await api.createLabel(solve);
      setLabelName(r.name);
      // Edits made while the request was in flight stay marked as unsaved.
      if (revision.current === rev) setDirty(false);
      flash(`Enregistré dans data/labels/${r.name}.json`);
      if (videoName) void refreshLabels(videoName);
    } catch (e) {
      flash(`Échec de l'enregistrement : ${e}`, true);
    }
  };

  const deleteLabel = async () => {
    if (!labelName || !window.confirm(`Supprimer data/labels/${labelName}.json ?`)) return;
    try {
      await api.deleteLabel(labelName);
      setSolve(null);
      setLabelName(null);
      setDirty(false);
      setAnalysis(null);
      if (videoName) void refreshLabels(videoName);
      flash("Label supprimé");
    } catch (e) {
      flash(String(e), true);
    }
  };

  // ---------- analysis (backend) ----------
  const movesKey = useMemo(() => JSON.stringify(moves), [moves]);
  const scramble = solve?.scramble ?? "";

  useEffect(() => {
    if (!solve) {
      setScrambleError(null);
      return;
    }
    const t = setTimeout(() => {
      api
        .validateMoves(scramble)
        .then((r) => setScrambleError(r.ok ? null : r.error))
        .catch(() => undefined);
    }, 250);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scramble, !!solve]);

  useEffect(() => {
    if (!solve) {
      setAnalysis(null);
      setAnalysisError(null);
      return;
    }
    const t = setTimeout(() => {
      api
        .analyze({ ...solve, segments: [], stats: {} })
        .then((r) => {
          setAnalysis({ segments: r.segments, stats: r.stats });
          setAnalysisError(null);
        })
        .catch((e) => setAnalysisError(String(e)));
    }, 200);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scramble, movesKey, solve?.id]);

  // ---------- labeling chrono ----------
  useEffect(() => {
    const mark = () => {
      lastActivity.current = Date.now();
    };
    window.addEventListener("keydown", mark, true);
    window.addEventListener("mousedown", mark, true);
    window.addEventListener("wheel", mark, true);
    let last = Date.now();
    const tick = setInterval(() => {
      const now = Date.now();
      const delta = now - last;
      last = now;
      const isIdle = now - lastActivity.current > IDLE_MS;
      setIdle(isIdle);
      if (!timerOn || isIdle || document.visibilityState !== "visible") return;
      setSolve((s) => (s ? { ...s, labeling_time_ms: Math.round(s.labeling_time_ms + delta) } : s));
    }, 1000);
    return () => {
      clearInterval(tick);
      window.removeEventListener("keydown", mark, true);
      window.removeEventListener("mousedown", mark, true);
      window.removeEventListener("wheel", mark, true);
    };
  }, [timerOn]);

  useEffect(() => {
    const warn = (e: BeforeUnloadEvent) => {
      if (dirty) e.preventDefault();
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  // ---------- keyboard ----------
  const onKey = useRef<(e: KeyboardEvent) => void>(() => undefined);
  onKey.current = (e: KeyboardEvent) => {
    const mod = e.metaKey || e.ctrlKey;
    if (mod && e.key.toLowerCase() === "s") {
      e.preventDefault();
      void save();
      return;
    }
    if (isTyping(e.target)) return;
    // A focused button would also react to Space / Enter: give the keys back to the tool.
    if (e.target instanceof HTMLButtonElement) e.target.blur();
    if (mod && e.key.toLowerCase() === "z") {
      e.preventDefault();
      undo();
      return;
    }
    if (mod || !video) return;
    const p = player.current;
    let handled = true;
    switch (e.key) {
      case "ArrowRight":
      case "ArrowLeft": {
        const n = e.altKey ? 120 : e.shiftKey ? 10 : 1;
        p?.step(e.key === "ArrowRight" ? n : -n);
        break;
      }
      case "ArrowUp":
        selectMove(selected === null ? doneCount - 1 : selected - 1);
        break;
      case "ArrowDown":
        selectMove(selected === null ? doneCount : selected + 1);
        break;
      case " ":
        p?.togglePlay();
        break;
      case "Backspace":
      case "Delete":
        if (selected !== null) deleteMove(selected);
        break;
      case "Enter":
        retimeSelected(e.shiftKey);
        break;
      case "Escape":
        setSelected(null);
        break;
      case "'":
      case "’":
        editSelected(togglePrime);
        break;
      default:
        handled = false;
    }
    if (!handled) {
      handled = true;
      const k = e.key.toLowerCase();
      if (e.key === "2" || e.code === "Digit2") editSelected(toggleDouble);
      else if (k === "w") editSelected(toggleWide);
      else if (k === "i") setWindowBound("start");
      else if (k === "o") setWindowBound("end");
      else if (k === "v") setRateIdx((r) => (r + (e.shiftKey ? RATES.length - 1 : 1)) % RATES.length);
      else {
        const token = keyToMove(e.key);
        if (token) addMove(e.shiftKey ? togglePrime(token) : token);
        else handled = false;
      }
    }
    if (handled) e.preventDefault();
  };

  useEffect(() => {
    const h = (e: KeyboardEvent) => onKey.current(e);
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, []);

  // ---------- render ----------
  const cubeMoves = useMemo(() => moves.slice(0, doneCount).map((m) => m.move), [moves, doneCount]);
  const win = solve?.solve_window ?? null;
  const usedScrambles = useMemo(() => new Set(labels.map((l) => l.scramble)), [labels]);

  return (
    <div className="app">
      <aside className="sidebar">
        <h1>cube-recon</h1>
        <label className="field">
          <span>Vidéo</span>
          <select value={videoName ?? ""} onChange={(e) => selectVideo(e.target.value)}>
            {videos.map((v) => (
              <option key={v.name} value={v.name}>
                {v.name} · {fmtDuration(v.duration_ms)}
              </option>
            ))}
          </select>
        </label>
        {video && (
          <p className="muted small">
            {video.codec.toUpperCase()} {video.width}×{video.height} · {video.fps.toFixed(2)} fps ·{" "}
            {video.frame_count} images{video.work_copy ? ` · copie ${video.work_copy}` : ""}
          </p>
        )}
        <button className="primary" onClick={newSolve} disabled={!video}>
          Nouvelle solve
        </button>
        <h2>Solves labellisées</h2>
        <ul className="labels">
          {labels.length === 0 && <li className="muted small">Aucune pour cette vidéo.</li>}
          {labels.map((l) => (
            <li
              key={l.name}
              className={l.name === labelName ? "selected" : ""}
              onClick={() => void openLabel(l.name)}
            >
              <span>{l.name}</span>
              <span className="small muted">
                {l.solve_window ? `${fmtTime(l.solve_window.t_start_ms)} · ` : ""}
                {l.move_count} mvts · {fmtSec(l.total_time_ms)} s {l.complete ? "✓" : ""}
              </span>
            </li>
          ))}
        </ul>

        {solve && (
          <section className="current">
            <h2>
              {labelName ?? "Nouvelle solve"} {dirty && <span className="dirty">● non enregistré</span>}
            </h2>
            <div className="chrono">
              <span title="Temps actif passé à labelliser (pause auto après 60 s d'inactivité)">
                ⏱ {fmtDuration(solve.labeling_time_ms)}
              </span>
              <span className="small muted">{!timerOn ? "en pause" : idle ? "inactif" : "en cours"}</span>
              <button onClick={() => setTimerOn((t) => !t)}>{timerOn ? "Pause" : "Reprendre"}</button>
            </div>
            <div className="row">
              <button className="primary" onClick={() => void save()}>
                Enregistrer (⌘S)
              </button>
              {labelName && (
                <button className="danger" onClick={() => void deleteLabel()}>
                  Supprimer
                </button>
              )}
            </div>
          </section>
        )}
        {status && <p className={`status small ${status.error ? "error" : ""}`}>{status.text}</p>}
        <Help />
      </aside>

      <main className="center">
        {video ? (
          <>
            <div className="video-wrap">
              <VideoPlayer
                ref={player}
                video={video}
                src={api.mediaUrl(video.work_copy ?? video.name)}
                rate={RATES[rateIdx]}
                onFrame={setFrame}
                onPlayingChange={setPlaying}
              />
            </div>
            <Scrubber
              durationMs={video.duration_ms}
              currentMs={currentMs}
              labeled={labels
                .filter((l) => l.name !== labelName && l.solve_window)
                .map((l) => l.solve_window!)}
              current={win}
              onSeek={seekMs}
            />
            <div className="transport">
              <button onClick={() => player.current?.step(-10)}>−10</button>
              <button onClick={() => player.current?.step(-1)}>−1</button>
              <button onClick={() => player.current?.togglePlay()}>{playing ? "❚❚" : "▶"}</button>
              <button onClick={() => player.current?.step(1)}>+1</button>
              <button onClick={() => player.current?.step(10)}>+10</button>
              <span className="mono big">#{frame}</span>
              <span className="mono">{fmtTime(currentMs)}</span>
              <span className="muted small mono">/ {fmtTime(video.duration_ms)}</span>
              <span className="rates">
                {RATES.map((r, i) => (
                  <button key={r} className={i === rateIdx ? "on" : ""} onClick={() => setRateIdx(i)}>
                    ×{r}
                  </button>
                ))}
              </span>
              <span className="window mono small">
                <button onClick={() => setWindowBound("start")} title="i">
                  Début
                </button>
                <a onClick={() => win && seekMs(win.t_start_ms)}>{win ? fmtTime(win.t_start_ms) : "–"}</a>
                <button onClick={() => setWindowBound("end")} title="o">
                  Fin
                </button>
                <a onClick={() => win && seekMs(win.t_end_ms)}>{win ? fmtTime(win.t_end_ms) : "–"}</a>
                {win && <span>({fmtSec(win.t_end_ms - win.t_start_ms)} s)</span>}
              </span>
            </div>
            <Timeline
              moves={moves}
              segments={segments}
              window={win}
              currentMs={currentMs}
              durationMs={video.duration_ms}
              onSeek={seekMs}
            />
            {solve && (
              <div className="scramble-row">
                <label className="field grow">
                  <span>Scramble</span>
                  <input
                    value={solve.scramble}
                    placeholder="Colle le scramble csTimer, ou laisse vide et déduis-le de la solution"
                    spellCheck={false}
                    onChange={(e) => update((s) => ({ ...s, scramble: e.target.value }), false)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === "Escape") (e.target as HTMLInputElement).blur();
                    }}
                  />
                </label>
                <label className="field">
                  <span>Source</span>
                  <select
                    value={solve.scramble_source}
                    onChange={(e) => update((s) => ({ ...s, scramble_source: e.target.value as ScrambleSource }))}
                  >
                    <option value="manual">tapé</option>
                    <option value="cstimer">csTimer</option>
                    <option value="derived">déduit</option>
                  </select>
                </label>
                {cstimer.length > 0 && (
                  <label className="field">
                    <span>Export csTimer</span>
                    <select
                      value=""
                      onChange={(e) => {
                        const c = cstimer[Number(e.target.value)];
                        if (c) update((s) => ({ ...s, scramble: c.scramble, scramble_source: "cstimer" }));
                      }}
                    >
                      <option value="">Choisir une solve…</option>
                      {cstimer.map((c, i) => (
                        <option key={`${c.file}-${c.no}`} value={i}>
                          {c.scramble === solve.scramble ? "● " : usedScrambles.has(c.scramble) ? "✓ " : ""}
                          n°{c.no} · {c.time} · {c.date.split(" ")[1] ?? c.date}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
                <button onClick={() => void deriveScramble()} disabled={!moves.length}>
                  Déduire de la solution
                </button>
              </div>
            )}
            {scrambleError && <p className="error small">Scramble invalide : {scrambleError}</p>}
            {solve && !scramble.trim() && moves.length > 0 && (
              <p className="warn-box small">
                Scramble vide : l'analyse partirait d'un cube résolu. Colle le scramble ou clique sur
                « Déduire de la solution » une fois la solve labellisée jusqu'à l'AUF.
              </p>
            )}
            {solve && scramble.trim() !== "" && (
              <AnalysisPanel
                segments={segments}
                stats={stats}
                moves={moves}
                window={win}
                currentMs={currentMs}
                error={analysisError}
                onSeek={seekMs}
              />
            )}
          </>
        ) : (
          <p className="muted">Aucune vidéo dans data/videos/.</p>
        )}
      </main>

      <aside className="right">
        <CubeView scramble={scrambleError ? "" : scramble} moves={cubeMoves} />
        <p className="small muted center-text">
          État après le scramble et {doneCount}/{moves.length} mouvements
        </p>
        {video && solve ? (
          <MoveList
            moves={moves}
            segments={segments}
            video={video}
            selected={selected}
            doneCount={doneCount}
            onSelect={selectMove}
            onEdit={(i, t) => void editToken(i, t)}
            onDelete={deleteMove}
          />
        ) : (
          <p className="muted small">Crée une solve (ou tape un mouvement) pour commencer.</p>
        )}
      </aside>
    </div>
  );
}

function Help() {
  return (
    <details className="help small" open>
      <summary>Clavier</summary>
      <dl>
        <dt>← →</dt>
        <dd>1 image (Maj : 10, Alt : ~1 s)</dd>
        <dt>Espace · v</dt>
        <dd>lecture / pause · vitesse (×1 ×0.5 ×0.25 ×0.1)</dd>
        <dt>i · o</dt>
        <dd>début · fin de la solve</dd>
        <dt>u r f d l b</dt>
        <dd>mouvement à l'image courante (Maj : prime)</dd>
        <dt>m e s · x y z</dt>
        <dd>slices · rotations</dd>
        <dt>' · 2 · w</dt>
        <dd>prime · double · wide sur le mvt sélectionné</dd>
        <dt>↑ ↓</dt>
        <dd>mouvement précédent / suivant</dd>
        <dt>Entrée</dt>
        <dd>recaler le mvt sur l'image (Maj : sa fin)</dd>
        <dt>⌫</dt>
        <dd>supprimer le mvt sélectionné</dd>
        <dt>⌘Z · ⌘S</dt>
        <dd>annuler · enregistrer</dd>
      </dl>
    </details>
  );
}
