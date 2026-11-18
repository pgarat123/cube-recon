import type { Segment, TimedMove, TimeWindow } from "../types";
import { STEP_COLORS } from "../util";

interface Props {
  moves: TimedMove[];
  segments: Segment[];
  window: TimeWindow | null;
  currentMs: number;
  durationMs: number;
  onSeek: (ms: number) => void;
}

/** Zoomed strip around the solve: window, steps, one tick per move, playhead. */
export function Timeline({ moves, segments, window, currentMs, durationMs, onSeek }: Props) {
  let lo: number;
  let hi: number;
  if (window) {
    lo = window.t_start_ms - 1000;
    hi = window.t_end_ms + 1000;
  } else if (moves.length) {
    lo = moves[0].t_start_ms - 2000;
    hi = moves[moves.length - 1].t_end_ms + 2000;
  } else {
    lo = currentMs - 5000;
    hi = currentMs + 5000;
  }
  if (currentMs < lo) lo = currentMs - 500;
  if (currentMs > hi) hi = currentMs + 500;
  lo = Math.max(0, lo);
  hi = Math.min(durationMs, Math.max(hi, lo + 1000));
  const pct = (ms: number) => `${((ms - lo) / (hi - lo)) * 100}%`;

  return (
    <div
      className="timeline"
      onClick={(e) => {
        const r = e.currentTarget.getBoundingClientRect();
        onSeek(lo + ((e.clientX - r.left) / r.width) * (hi - lo));
      }}
    >
      {window && (
        <div
          className="tl-window"
          style={{ left: pct(window.t_start_ms), width: `calc(${pct(window.t_end_ms)} - ${pct(window.t_start_ms)})` }}
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
      <div className="tl-head" style={{ left: pct(currentMs) }} />
      <span className="tl-label tl-lo">{(lo / 1000).toFixed(1)} s</span>
      <span className="tl-label tl-hi">{(hi / 1000).toFixed(1)} s</span>
    </div>
  );
}
