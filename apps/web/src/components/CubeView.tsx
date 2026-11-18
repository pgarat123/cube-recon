import { useEffect, useRef, useState } from "react";
import { TwistyPlayer } from "cubing/twisty";

interface Props {
  scramble: string;
  moves: string[];
}

/** twisty-player showing the state after the scramble and ``moves`` (display only). */
export function CubeView({ scramble, moves }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const player = useRef<TwistyPlayer | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const p = new TwistyPlayer({
      puzzle: "3x3x3",
      controlPanel: "none",
      background: "none",
      hintFacelets: "floating",
      backView: "none",
      experimentalDragInput: "none",
    });
    p.style.width = "100%";
    p.style.height = "100%";
    host.current?.appendChild(p);
    player.current = p;
    return () => {
      p.remove();
      player.current = null;
    };
  }, []);

  const alg = moves.join(" ");
  useEffect(() => {
    const p = player.current;
    if (!p) return;
    try {
      p.experimentalSetupAlg = scramble;
      p.alg = alg;
      p.jumpToEnd({ flash: false });
      setError(null);
    } catch (e) {
      setError(String(e));
    }
  }, [scramble, alg]);

  return (
    <div className="cube">
      <div className="cube-host" ref={host} />
      {error && <div className="error small">{error}</div>}
    </div>
  );
}
