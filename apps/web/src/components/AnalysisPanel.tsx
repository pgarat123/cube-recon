import type { Segment, Stats, TimedMove, TimeWindow } from "../types";
import { STEP_COLORS, STEP_LABELS, fmtSec } from "../util";

interface Props {
  segments: Segment[];
  stats: Stats;
  moves: TimedMove[];
  window: TimeWindow | null;
  currentMs: number;
  error: string | null;
  onSeek: (ms: number) => void;
}

const COLOR_FR: Record<string, string> = {
  white: "blanc",
  yellow: "jaune",
  green: "vert",
  blue: "bleu",
  red: "rouge",
  orange: "orange",
};

export function AnalysisPanel({ segments, stats, moves, window, currentMs, error, onSeek }: Props) {
  if (error) return <p className="error">Analyse impossible : {error}</p>;
  if (!moves.length) return <p className="muted small">L'analyse apparaît dès le premier mouvement.</p>;
  const steps = stats.steps ?? {};
  const pauses = stats.pauses ?? [];
  return (
    <div className="analysis">
      <div className="kpis">
        <Kpi label="Temps (1er → dernier mvt)" value={`${fmtSec(stats.total_time_ms)} s`} />
        <Kpi
          label="Fenêtre solve"
          value={window ? `${fmtSec(window.t_end_ms - window.t_start_ms)} s` : "–"}
        />
        <Kpi label="STM / ETM" value={`${stats.moves_stm ?? 0} / ${stats.moves_etm ?? 0}`} />
        <Kpi label="TPS (STM)" value={(stats.tps_stm ?? 0).toFixed(2)} />
        <Kpi label="Rotations" value={String(stats.rotations ?? 0)} />
        <Kpi
          label="Pauses ≥ 300 ms"
          value={`${pauses.length} · ${fmtSec(stats.total_pause_ms)} s`}
        />
        <Kpi
          label="Croix"
          value={stats.cross_color ? (COLOR_FR[stats.cross_color] ?? stats.cross_color) : "–"}
        />
        <Kpi
          label="Statut"
          value={stats.complete ? "résolu ✓" : "incomplet"}
          tone={stats.complete ? "ok" : "warn"}
        />
      </div>
      <table className="steps">
        <thead>
          <tr>
            <th>Étape</th>
            <th>Cas</th>
            <th>Mouvements</th>
            <th>Durée</th>
            <th>Reco</th>
            <th>Exec</th>
            <th>STM</th>
            <th>TPS</th>
          </tr>
        </thead>
        <tbody>
          {segments.map((seg) => {
            const st = steps[seg.step];
            const active =
              seg.move_range[1] > seg.move_range[0] &&
              currentMs >= seg.t_start_ms &&
              currentMs <= seg.t_end_ms;
            const text = moves
              .slice(seg.move_range[0], seg.move_range[1])
              .map((m) => m.move)
              .join(" ");
            return (
              <tr
                key={seg.step}
                className={active ? "active" : ""}
                onClick={() => onSeek(seg.t_start_ms)}
              >
                <td>
                  <span className="dot" style={{ background: STEP_COLORS[seg.step] }} />
                  {STEP_LABELS[seg.step] ?? seg.step}
                </td>
                <td>{seg.case_id ?? ""}</td>
                <td className="alg">{text || <span className="muted">–</span>}</td>
                <td>{st ? fmtSec(st.duration_ms) : ""}</td>
                <td>{st ? fmtSec(st.recognition_ms) : ""}</td>
                <td>{st ? fmtSec(st.execution_ms) : ""}</td>
                <td>{st ? st.moves_stm : seg.move_range[1] - seg.move_range[0]}</td>
                <td>{st ? st.tps_stm.toFixed(1) : ""}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {pauses.length > 0 && (
        <div className="pauses small">
          Pauses :{" "}
          {pauses.map((p) => (
            <button
              key={p.after_move}
              className="chip"
              onClick={() => onSeek(moves[p.after_move].t_end_ms)}
            >
              après {p.after_move + 1} ({moves[p.after_move]?.move}) · {fmtSec(p.duration_ms)} s
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function Kpi({ label, value, tone }: { label: string; value: string; tone?: "ok" | "warn" }) {
  return (
    <div className={`kpi ${tone ?? ""}`}>
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
    </div>
  );
}
