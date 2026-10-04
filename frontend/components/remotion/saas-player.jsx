"use client";

import { Player } from "@remotion/player";
import { useRef } from "react";
import { PreviewTransport } from "./transport";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

function DemoScene({ photo, caption, captionStyle, position }) {
  const frame = useCurrentFrame();
  const scale = interpolate(frame, [0, 239], [1, 1.035], {
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill style={{ background: "#101116", overflow: "hidden" }}>
      {/* Player-only illustrative photography; production exports use the backend renderer. */}
      <img
        src={photo}
        alt=""
        draggable={false}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          objectPosition: `${position}% center`,
          transform: `scale(${scale})`,
        }}
      />
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(ellipse at 50% 35%, transparent 45%, rgba(0,0,0,.35))",
        }}
      />
      {frame >= 12 && frame < 225 && (
        <div
          style={{
            position: "absolute",
            bottom: "8%",
            left: "9%",
            right: "9%",
            textAlign: "center",
            color: captionStyle === "highlight" ? "#ffeb56" : "white",
            fontSize: 33,
            lineHeight: 1.3,
            fontFamily: "var(--font-body)",
            fontWeight: captionStyle === "bold" ? 750 : 550,
          }}
        >
          <span
            style={{
              padding: "5px 12px",
              background:
                captionStyle === "clean" ? "rgba(0,0,0,.68)" : "transparent",
              boxDecorationBreak: "clone",
              textShadow: "0 2px 7px rgba(0,0,0,.85)",
            }}
          >
            {caption}
          </span>
        </div>
      )}
    </AbsoluteFill>
  );
}

export default function SaaSPlayer({
  photo,
  caption,
  captionStyle = "clean",
  position = 50,
  ratio = "16:9",
}) {
  const player = useRef(null);
  const [width, height] =
    ratio === "9:16"
      ? [720, 1280]
      : ratio === "1:1"
        ? [1080, 1080]
        : [1280, 720];
  return (
    <div className="saas-preview-player">
      <Player
        ref={player}
        component={DemoScene}
        inputProps={{ photo, caption, captionStyle, position }}
        durationInFrames={240}
        initialFrame={15}
        compositionWidth={width}
        compositionHeight={height}
        fps={30}
        controls={false}
        loop
        acknowledgeRemotionLicense
        style={{
          width: "100%",
          maxHeight: 380,
          aspectRatio: `${width}/${height}`,
          margin: "auto",
        }}
        aria-label="Illustrative eight-second edit preview"
      />
      <PreviewTransport player={player} frames={240} initialFrame={15} />
    </div>
  );
}
