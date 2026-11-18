// Mirrors of the Python objects returned by the API (cuberecon.io / cuberecon.api).

export interface VideoMeta {
  name: string;
  size_bytes: number;
  codec: string;
  width: number;
  height: number;
  fps: number;
  fps_num: number;
  fps_den: number;
  frame_count: number;
  duration_ms: number;
  start_time_ms: number;
  work_copy: string | null;
}

export type MoveSource = "manual" | "auto" | "corrected";
export type ScrambleSource = "manual" | "cstimer" | "derived";

export interface TimedMove {
  move: string;
  t_start_ms: number;
  t_end_ms: number;
  confidence: number;
  source: MoveSource;
}

export interface Segment {
  step: string;
  t_start_ms: number;
  t_end_ms: number;
  move_range: [number, number];
  case_id: string | null;
}

export interface TimeWindow {
  t_start_ms: number;
  t_end_ms: number;
}

export interface StepStats {
  duration_ms: number;
  recognition_ms: number;
  execution_ms: number;
  moves_etm: number;
  moves_stm: number;
  rotations: number;
  tps_etm: number;
  tps_stm: number;
}

export interface Stats {
  pause_threshold_ms?: number;
  total_time_ms?: number;
  moves_etm?: number;
  moves_stm?: number;
  rotations?: number;
  tps_etm?: number;
  tps_stm?: number;
  pauses?: { after_move: number; duration_ms: number }[];
  total_pause_ms?: number;
  steps?: Record<string, StepStats>;
  complete?: boolean;
  cross_color?: string | null;
}

export interface Solve {
  schema_version?: number;
  id: string;
  created_at: string;
  video: { path: string; fps: number; width: number; height: number; duration_ms: number } | null;
  scramble: string;
  color_scheme: Record<string, string>;
  calibration: Record<string, number[][]> | null;
  moves: TimedMove[];
  segments: Segment[];
  stats: Stats;
  solve_window: TimeWindow | null;
  scramble_source: ScrambleSource;
  labeling_time_ms: number;
}

export interface LabelSummary {
  name: string;
  id: string;
  video: string | null;
  solve_window: TimeWindow | null;
  scramble: string;
  move_count: number;
  complete: boolean;
  total_time_ms: number | null;
  labeling_time_ms: number;
}

export interface CsTimerSolve {
  file: string;
  no: number;
  time: string;
  time_ms: number | null;
  penalty: string | null;
  scramble: string;
  date: string;
  comment: string;
}
