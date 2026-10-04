"use client";
import { useEffect, useState } from "react";
import { Pause, Play, SpeakerHigh } from "@phosphor-icons/react";

/** Transport is outside the composition so it never covers authored captions. */
export function PreviewTransport({
  player,
  frames,
  initialFrame = 0,
  audio = false,
}) {
  const [frame, setFrame] = useState(initialFrame),
    [playing, setPlaying] = useState(false),
    [volume, setVolume] = useState(1);
  useEffect(() => {
    const instance = player.current;
    if (!instance) return;
    const update = (event) => setFrame(event.detail.frame);
    const play = () => setPlaying(true),
      pause = () => setPlaying(false);
    instance.addEventListener("frameupdate", update);
    instance.addEventListener("play", play);
    instance.addEventListener("pause", pause);
    instance.addEventListener("ended", pause);
    return () => {
      instance.removeEventListener("frameupdate", update);
      instance.removeEventListener("play", play);
      instance.removeEventListener("pause", pause);
      instance.removeEventListener("ended", pause);
    };
  }, [player]);
  return (
    <div className="preview-transport">
      <button
        type="button"
        aria-label={playing ? "Pause video" : "Play video"}
        onClick={() => player.current?.toggle()}
      >
        {playing ? (
          <Pause size={19} weight="light" />
        ) : (
          <Play size={19} weight="light" />
        )}
      </button>
      <input
        type="range"
        min={0}
        max={frames - 1}
        value={Math.min(frame, frames - 1)}
        aria-label="Preview playback position"
        aria-valuetext={`${(frame / 30).toFixed(1)} seconds`}
        onChange={(event) => player.current?.seekTo(Number(event.target.value))}
      />
      <span className="preview-clock">
        {(frame / 30).toFixed(1)}s / {(frames / 30).toFixed(1)}s
      </span>
      {audio && (
        <label className="preview-volume">
          <SpeakerHigh size={16} weight="light" />
          <input
            aria-label="Preview volume"
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={volume}
            onChange={(event) => {
              const value = Number(event.target.value);
              setVolume(value);
              player.current?.setVolume(value);
            }}
          />
        </label>
      )}
    </div>
  );
}
