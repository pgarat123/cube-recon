import { useRef, type PointerEvent as ReactPointerEvent } from "react";
import type { Segment, TimedMove, TimeWindow } from "../types";
import { STEP_COLORS, fmtTime } from "../util";

/** Click or drag on a bar mapping [lo, hi] (ms) to its width. */
function useScrub(lo: number, hi: number, onSeek: (ms: number) => void) {
  const dragging = useRef(false);
  const at = (e: ReactPointerEvent<HTMLDivElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    const x = Math.min(1, Math.max(0, (e.clientX - r.left) / r.width));
    return lo + x * (hi - lo);
  };
  return {
    onPointerDown: (e: ReactPointerEvent<HTMLDivElement>) => {
      if (e.button !== 0) return;
      dragging.current = true;
      e.currentTarget.setPointerCapture(e.pointerId);
      onSeek(at(e));
    },
    onPointerMove: (e: ReactPointerEvent<HTMLDivElement>) => {
      if (dragging.current) onSeek(at(e));
    },
    onPointerUp: (e: ReactPointerEvent<HTMLDivElement>) => {
      dragging.current = false;
      e.currentTarget.releasePointerCapture(e.pointerId);
    },
  };
}

interface ScrubberProps {
  durationMs: number;
  currentMs: number;
  /** Solve windows already labeled in this video, and the one being edited. */
  labeled: TimeWindow[];
  current: TimeWindow | null;
  onSeek: (ms: number) => void;
}

/** Whole-video bar: click or drag anywhere to seek. */
export function Scrubber({ durationMs, currentMs, labeled, current, onSeek }: ScrubberProps) {
  const handlers = useScrub(0, durationMs, onSeek);
  const pct = (ms: number) => `${(Math.min(Math.max(ms, 0), durationMs) / durationMs) * 100}%`;
  const span = (w: TimeWindow) => ({
    left: pct(w.t_start_ms),
    width: `max(3px, calc(${pct(w.t_end_ms)} - ${pct(w.t_start_ms)}))`,
  });
  return (
    <div className="scrubber-row">
      <span className="mono small muted">{fmtTime(currentMs)}</span>
      <div className="scrubber" {...handlers} title="Cliquer ou glisser pour se déplacer dans la vidéo">
        <div className="sc-fill" style={{ width: pct(currentMs) }} />
        {labeled.map((w, i) => (
          <div key={i} className="sc-solve" style={span(w)} />
        ))}
        {current && <div className="sc-solve current" style={span(current)} />}
        <div className="sc-head" style={{ left: pct(currentMs) }} />
      </div>
      <span className="mono small muted">{fmtTime(durationMs)}</span>
    </div>
  );
}

interface TimelineProps {
  moves: TimedMove[];
  segments: Segment[];
  window: TimeWindow | null;
  currentMs: number;
  durationMs: number;
  onSeek: (ms: number) => void;
}

/**
 * Zoom on the solve being labeled: window, steps, one tick per move, playhead.
 * The range is fixed by the solve (window ± 1 s, else the moves ± 2 s), it does not
 * follow the playhead, so a click always lands at the same place.
 */
export function Timeline({ moves, segments, window, currentMs, durationMs, onSeek }: TimelineProps) {
  let lo = 0;
  let hi = 0;
  if (window) {
    lo = window.t_start_ms - 1000;
    hi = window.t_end_ms + 1000;
  } else if (moves.length) {
    lo = moves[0].t_start_ms - 2000;
    hi = moves[moves.length - 1].t_end_ms + 2000;
  }
  lo = Math.max(0, lo);
  hi = Math.min(durationMs, Math.max(hi, lo + 2000));
  const handlers = useScrub(lo, hi, onSeek);
  if (!window && !moves.length) return null;

  const pct = (ms: number) => `${((ms - lo) / (hi - lo)) * 100}%`;
  const headInside = currentMs >= lo && currentMs <= hi;

  return (
    <div className="timeline" {...handlers} title="Zoom sur la solve : cliquer ou glisser">
      {window && (
        <div
          className="tl-window"
          style={{
            left: pct(window.t_start_ms),
            width: `calc(${pct(window.t_end_ms)} - ${pct(window.t_start_ms)})`,
          }}
        />
      )}
      {segments
        .filter((s) => s.move_range[1] > s.move_range[0])
        .map((s) => (
          <div
            key={s.step}
            className="tl-seg"
            title={s.step}
            style={{
              left: pct(s.t_start_ms),
              width: `max(2px, calc(${pct(s.t_end_ms)} - ${pct(s.t_start_ms)}))`,
              background: STEP_COLORS[s.step],
            }}
          />
        ))}
      {moves.map((m, i) => (
        <div key={i} className="tl-tick" style={{ left: pct(m.t_start_ms) }} title={m.move} />
      ))}
      {headInside ? (
        <div className="tl-head" style={{ left: pct(currentMs) }} />
      ) : (
        <span className={`tl-out ${currentMs < lo ? "left" : "right"}`}>
          {currentMs < lo ? "◀ curseur avant la solve" : "curseur après la solve ▶"}
        </span>
      )}
      <span className="tl-label tl-lo">{fmtTime(lo)}</span>
      <span className="tl-label tl-hi">{fmtTime(hi)}</span>
    </div>
  );
}
