import { useEffect, useRef, useState } from "react";
import type { Segment, TimedMove, VideoMeta } from "../types";
import { STEP_COLORS, fmtTime, msToFrame } from "../util";

interface Props {
  moves: TimedMove[];
  segments: Segment[];
  video: VideoMeta;
  selected: number | null;
  doneCount: number;
  onSelect: (i: number) => void;
  onEdit: (i: number, token: string) => void;
  onDelete: (i: number) => void;
}

function stepOf(i: number, segments: Segment[]): string | null {
  const s = segments.find((seg) => i >= seg.move_range[0] && i < seg.move_range[1]);
  return s ? s.step : null;
}

export function MoveList({ moves, segments, video, selected, doneCount, ...cb }: Props) {
  const [editing, setEditing] = useState<number | null>(null);
  const [draft, setDraft] = useState("");
  const list = useRef<HTMLOListElement>(null);

  useEffect(() => {
    if (selected === null) return;
    list.current
      ?.querySelector(`[data-index="${selected}"]`)
      ?.scrollIntoView({ block: "nearest" });
  }, [selected]);

  if (moves.length === 0) {
    return <p className="muted small">Aucun mouvement. Tape une lettre pour en ajouter un.</p>;
  }

  return (
    <ol className="moves" ref={list}>
      {moves.map((m, i) => {
        const step = stepOf(i, segments);
        const gap = i > 0 ? m.t_start_ms - moves[i - 1].t_end_ms : null;
        const cls = [
          "move",
          i === selected ? "selected" : "",
          i >= doneCount ? "future" : "",
        ].join(" ");
        return (
          <li
            key={i}
            data-index={i}
            className={cls}
            onClick={() => cb.onSelect(i)}
            onDoubleClick={() => {
              setEditing(i);
              setDraft(m.move);
            }}
          >
            <span className="idx">{i + 1}</span>
            <span className="dot" style={{ background: step ? STEP_COLORS[step] : "transparent" }} />
            {editing === i ? (
              <input
                className="token-edit"
                autoFocus
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onBlur={() => setEditing(null)}
                onKeyDown={(e) => {
                  e.stopPropagation();
                  if (e.key === "Enter") {
                    cb.onEdit(i, draft.trim());
                    setEditing(null);
                  } else if (e.key === "Escape") setEditing(null);
                }}
              />
            ) : (
              <span className="token">{m.move}</span>
            )}
            <span className="frame">#{msToFrame(m.t_start_ms, video)}</span>
            <span className="time">{fmtTime(m.t_start_ms)}</span>
            <span className={`gap ${gap !== null && gap >= 300 ? "pause" : ""}`}>
              {gap === null ? "" : `+${Math.round(gap)}`}
            </span>
            <button
              className="icon"
              title="Supprimer"
              onClick={(e) => {
                e.stopPropagation();
                cb.onDelete(i);
              }}
            >
              ×
            </button>
          </li>
        );
      })}
    </ol>
  );
}
