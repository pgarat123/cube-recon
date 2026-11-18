import { useEffect, useImperativeHandle, useRef, type Ref } from "react";
import type { VideoMeta } from "../types";

export interface PlayerHandle {
  seekFrame(n: number): void;
  step(delta: number): void;
  togglePlay(): void;
  pause(): void;
  setRate(rate: number): void;
}

interface Props {
  video: VideoMeta;
  src: string;
  rate: number;
  onFrame: (frame: number) => void;
  onPlayingChange: (playing: boolean) => void;
  ref?: Ref<PlayerHandle>;
}

/**
 * Frame-accurate player. Seeks target the middle of a frame (avoids rounding onto the
 * previous one) and the shown frame is read back from requestVideoFrameCallback
 * (mediaTime is the presentation time of the frame actually displayed).
 */
export function VideoPlayer({ video, src, rate, onFrame, onPlayingChange, ref }: Props) {
  const el = useRef<HTMLVideoElement>(null);
  const frame = useRef(0);
  const target = useRef<number | null>(null);
  const seeking = useRef(false);
  const fpsRatio = video.fps_num / video.fps_den;

  const report = (n: number) => {
    if (n !== frame.current) {
      frame.current = n;
    }
    onFrame(n);
  };

  const issueSeek = () => {
    const v = el.current;
    const n = target.current;
    if (!v || n === null) return;
    target.current = null;
    seeking.current = true;
    v.currentTime = (n + 0.5) / fpsRatio;
  };

  const seekFrame = (n: number) => {
    const v = el.current;
    if (!v) return;
    if (!v.paused) v.pause();
    const clamped = Math.max(0, Math.min(video.frame_count - 1, Math.round(n)));
    target.current = clamped;
    report(clamped); // optimistic, corrected by the frame callback
    if (!seeking.current) issueSeek();
  };

  useImperativeHandle(ref, () => ({
    seekFrame,
    step: (delta: number) => seekFrame((target.current ?? frame.current) + delta),
    togglePlay: () => {
      const v = el.current;
      if (!v) return;
      if (v.paused) void v.play();
      else v.pause();
    },
    pause: () => el.current?.pause(),
    setRate: (r: number) => {
      if (el.current) el.current.playbackRate = r;
    },
  }));

  useEffect(() => {
    const v = el.current;
    if (!v) return;
    v.playbackRate = rate;
  }, [rate]);

  useEffect(() => {
    const v = el.current;
    if (!v) return;
    frame.current = 0;
    target.current = null;
    seeking.current = false;
    let handle = 0;
    const onVideoFrame: VideoFrameRequestCallback = (_now, meta) => {
      if (target.current === null && !seeking.current) {
        report(Math.round(meta.mediaTime * fpsRatio));
      }
      handle = v.requestVideoFrameCallback(onVideoFrame);
    };
    handle = v.requestVideoFrameCallback(onVideoFrame);
    const onSeeked = () => {
      seeking.current = false;
      if (target.current !== null) issueSeek();
      else report(Math.floor(v.currentTime * fpsRatio));
    };
    const onPlay = () => onPlayingChange(true);
    const onPause = () => onPlayingChange(false);
    v.addEventListener("seeked", onSeeked);
    v.addEventListener("play", onPlay);
    v.addEventListener("pause", onPause);
    return () => {
      v.cancelVideoFrameCallback(handle);
      v.removeEventListener("seeked", onSeeked);
      v.removeEventListener("play", onPlay);
      v.removeEventListener("pause", onPause);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [src]);

  return (
    <video
      ref={el}
      className="video"
      src={src}
      preload="auto"
      muted
      playsInline
      onLoadedData={(e) => {
        e.currentTarget.playbackRate = rate;
      }}
    />
  );
}
