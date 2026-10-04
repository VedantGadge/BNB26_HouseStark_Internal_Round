"use client";
import { Player } from "@remotion/player";
import { useRef } from "react";
import { PreviewTransport } from "./transport";
import { Video } from "@remotion/media";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";

function wrap(text, limit) {
  return text
    .split(/\s+/)
    .reduce((result, word) => {
      const last = result.at(-1) || "";
      if (last && last.length + word.length + 1 <= limit)
        result[result.length - 1] = last + " " + word;
      else result.push(word);
      return result;
    }, [])
    .join("\n");
}
function CaptionOverlay({ caption, recipe }) {
  const style = recipe.caption_style;
  return (
    <div
      style={{
        position: "absolute",
        bottom: recipe.output.safe_bottom_px,
        left: 40,
        right: 40,
        display: "flex",
        justifyContent: "center",
        textAlign: "center",
      }}
    >
      <span
        style={{
          fontFamily: "Arial,sans-serif",
          fontWeight: 700,
          fontSize: style === "clean" ? 48 : 62,
          lineHeight: 1.15,
          color: style === "bold_highlight" ? "#ffff00" : "#fff",
          background: style === "clean" ? "rgba(0,0,0,.45)" : "rgba(0,0,0,.7)",
          padding: 18,
          whiteSpace: "pre-wrap",
        }}
      >
        {wrap(caption.text, Math.max(12, Math.floor(recipe.output.width / 34)))}
      </span>
    </div>
  );
}
function RecipeScene({ src, recipe, showSafeZones }) {
  const frame = useCurrentFrame(),
    { fps } = useVideoConfig(),
    ms = (frame * 1000) / fps;
  const captions = recipe.captions.map((caption) => ({
    text: caption.text,
    startMs: caption.start_ms,
    endMs: caption.end_ms,
    timestampMs: null,
    confidence: null,
  }));
  const active = captions.find(
    (caption) => caption.startMs <= ms && caption.endMs >= ms,
  );
  const zoom = recipe.emphasis_zooms.find(
    (item) =>
      frame >= Math.round((item.start_ms * fps) / 1000) &&
      frame <= Math.round((item.end_ms * fps) / 1000),
  );
  const title =
    recipe.title && ms >= recipe.title.start_ms && ms <= recipe.title.end_ms
      ? recipe.title
      : null;
  const duration = recipe.source_end_ms - recipe.source_start_ms;
  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      <AbsoluteFill style={{ scale: zoom?.scale || 1 }}>
        <Video
          name="Source clip"
          src={src}
          objectFit={recipe.output.fit === "pad" ? "contain" : "cover"}
          trimBefore={Math.round((recipe.source_start_ms * fps) / 1000)}
          volume={(f) =>
            Math.min(
              1,
              recipe.audio.fade_in_ms
                ? (f * 1000) / fps / recipe.audio.fade_in_ms
                : 1,
              recipe.audio.fade_out_ms
                ? (duration - (f * 1000) / fps) / recipe.audio.fade_out_ms
                : 1,
            )
          }
          style={{
            width: "100%",
            height: "100%",
            objectPosition:
              recipe.output.fit === "pad"
                ? "center"
                : `${recipe.crop.center_x * 100}% ${recipe.crop.center_y * 100}%`,
          }}
        />
      </AbsoluteFill>
      {title && (
        <div
          style={{
            position: "absolute",
            top:
              title.position === "top" ? recipe.output.safe_top_px : undefined,
            bottom:
              title.position === "bottom"
                ? recipe.output.safe_bottom_px
                : undefined,
            left: 40,
            right: 40,
            textAlign: "center",
            display: "flex",
            justifyContent: "center",
          }}
        >
          <span
            style={{
              fontFamily: "Arial,sans-serif",
              fontWeight: 700,
              fontSize: 64,
              lineHeight: 1.15,
              color: "white",
              background: "rgba(0,0,0,.7)",
              padding: 18,
              whiteSpace: "pre-wrap",
            }}
          >
            {wrap(
              title.text,
              Math.max(12, Math.floor(recipe.output.width / 34)),
            )}
          </span>
        </div>
      )}
      {recipe.captions_enabled && active && (
        <CaptionOverlay recipe={recipe} caption={active} />
      )}
      {showSafeZones && (
        <div
          className="safe-zone"
          style={{
            top: recipe.output.safe_top_px,
            bottom: recipe.output.safe_bottom_px,
          }}
        />
      )}
    </AbsoluteFill>
  );
}

export default function RecipePlayer({ src, recipe, showSafeZones }) {
  const player = useRef(null);
  const frames = Math.max(
    1,
    Math.round(((recipe.source_end_ms - recipe.source_start_ms) * 30) / 1000),
  );
  return (
    <div className="recipe-preview">
      <Player
        ref={player}
        component={RecipeScene}
        inputProps={{ src, recipe, showSafeZones }}
        durationInFrames={frames}
        compositionWidth={recipe.output.width}
        compositionHeight={recipe.output.height}
        fps={30}
        controls={false}
        style={{
          width: "100%",
          maxWidth: recipe.output.height > recipe.output.width ? 320 : "100%",
          margin: "0 auto",
          aspectRatio: `${recipe.output.width}/${recipe.output.height}`,
        }}
        className="remotion-player"
        acknowledgeRemotionLicense
        renderError={() => (
          <div className="notice error">
            Live preview could not load. Refresh the source link. Verified
            exports below remain available.
          </div>
        )}
      />
      <PreviewTransport player={player} frames={frames} audio />
    </div>
  );
}
