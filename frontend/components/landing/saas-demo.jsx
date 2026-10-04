"use client";

import dynamic from "next/dynamic";
import Image from "next/image";
import { useState } from "react";
import { Check, Scissors, TextT, Export } from "@phosphor-icons/react";
import { presets } from "@/lib/creator.mjs";

const DemoPlayer = dynamic(() => import("@/components/remotion/saas-player"), {
  ssr: false,
  loading: () => (
    <div className="saas-player-loading">
      <Image
        src="/media/creator-preview.webp"
        fill
        loading="eager"
        sizes="(max-width:800px) 90vw, 60vw"
        alt="Illustrative creator filming a coastal story"
      />
    </div>
  ),
});
const views = [
  { name: "Seaside intro", photo: "/media/creator-preview.webp", position: 40 },
  { name: "Coastline story", photo: "/media/coastline.webp", position: 50 },
  { name: "Sea stacks", photo: "/media/coastline.webp", position: 85 },
];
const hooks = [
  "This coastline is unreal. Let me show you a different perspective.",
  "One coastline. A completely different point of view.",
  "Sometimes the best story starts when you stop and look.",
];

export function SaaSDemo() {
  const [view, setView] = useState(0),
    [tab, setTab] = useState("Edit"),
    [caption, setCaption] = useState(
      "This coastline is unreal, and today I’m taking you behind the scenes.",
    ),
    [style, setStyle] = useState("clean"),
    [saved, setSaved] = useState(null),
    [preset, setPreset] = useState(presets[0].id),
    [hook, setHook] = useState(0);
  const chosen = presets.find((item) => item.id === preset);
  const ratio =
    tab === "Export"
      ? chosen.width === chosen.height
        ? "1:1"
        : chosen.width > chosen.height
          ? "16:9"
          : "9:16"
      : "16:9";
  return (
    <div className="saas-demo">
      <div className="saas-demo-bar">
        <span>Illustrative workflow</span>
        <div className="saas-demo-tabs" aria-label="Demonstration stage">
          {[
            [TextT, "Script"],
            [Scissors, "Edit"],
            [Export, "Export"],
          ].map(([Icon, label]) => (
            <button
              key={label}
              aria-pressed={tab === label}
              onClick={() => setTab(label)}
            >
              <Icon size={16} weight="light" />
              {label}
            </button>
          ))}
        </div>
      </div>
      <div className="saas-demo-grid">
        <aside className="demo-sources">
          <h2>Sources</h2>
          <p>Illustrative photo views</p>
          {views.map((item, index) => (
            <button
              key={item.name}
              aria-pressed={view === index}
              onClick={() => setView(index)}
            >
              <span className="source-thumb">
                <Image
                  src={item.photo}
                  fill
                  sizes="90px"
                  alt=""
                  style={{ objectPosition: `${item.position}% center` }}
                />
              </span>
              <span>
                <strong>{item.name}</strong>
                <small>Demo source</small>
              </span>
            </button>
          ))}
          <div className="source-original">
            <Check size={15} />
            Original stays untouched
          </div>
        </aside>
        <div className="saas-canvas">
          <DemoPlayer
            photo={views[view].photo}
            position={views[view].position}
            caption={tab === "Script" ? hooks[hook] : caption}
            captionStyle={style}
            ratio={ratio}
          />
        </div>
        <aside className="demo-inspector">
          <h2>{tab}</h2>
          {tab === "Edit" ? (
            <>
              <fieldset>
                <legend>Caption style</legend>
                <div className="demo-style-options">
                  {["clean", "bold", "highlight"].map((item) => (
                    <button
                      key={item}
                      aria-label={`${item} caption style`}
                      aria-pressed={style === item}
                      onClick={() => setStyle(item)}
                    >
                      <span className={item}>Aa</span>
                      <small>{item}</small>
                    </button>
                  ))}
                </div>
              </fieldset>
              <label className="field">
                <span>Caption text</span>
                <textarea
                  rows={4}
                  maxLength={120}
                  value={caption}
                  onChange={(event) => {
                    setCaption(event.target.value);
                    setSaved(null);
                  }}
                />
              </label>
              <button
                className="demo-save"
                disabled={!caption.trim()}
                onClick={() => setSaved(caption)}
              >
                {saved ? (
                  <>
                    <Check size={16} />
                    Demo version saved
                  </>
                ) : (
                  "Save demo version"
                )}
              </button>
              <p className="demo-note" aria-live="polite">
                {saved
                  ? "Your original is intact. This example stays on this page."
                  : "Try the edit. Changes stay in this demonstration."}
              </p>
            </>
          ) : tab === "Script" ? (
            <>
              <p>Choose an opening</p>
              <div className="demo-hook-options">
                {hooks.map((text, index) => (
                  <button
                    key={text}
                    aria-pressed={hook === index}
                    onClick={() => setHook(index)}
                  >
                    {text}
                  </button>
                ))}
              </div>
              <p className="demo-note">
                Illustrative script alternatives. In your studio, generate from
                your own brief.
              </p>
            </>
          ) : (
            <>
              <label className="field">
                <span>Platform preset</span>
                <select
                  value={preset}
                  onChange={(event) => setPreset(event.target.value)}
                >
                  {presets.map((item) => (
                    <option value={item.id} key={item.id}>
                      {item.name}
                    </option>
                  ))}
                </select>
              </label>
              <p className="preset-dimensions">
                {chosen.width} × {chosen.height}
              </p>
              <p className="demo-note">
                Preview the framing here. Verified video exports are created
                inside your project.
              </p>
            </>
          )}
        </aside>
      </div>
    </div>
  );
}

export function FeatureBento() {
  const [position, setPosition] = useState(50),
    [ratio, setRatio] = useState("16:9"),
    [hook, setHook] = useState(0),
    [preset, setPreset] = useState(0);
  return (
    <div className="saas-bento">
      <section className="bento-edit">
        <h3>Keep the original. Own the edit.</h3>
        <p>
          Frame the moment, correct the captions and save your next version.
        </p>
        <div className="bento-edit-surface">
          <div
            className="bento-crop"
            style={{ aspectRatio: ratio.replace(":", "/") }}
          >
            <Image
              src="/media/creator-preview.webp"
              fill
              sizes="(max-width:800px) 90vw, 45vw"
              alt="Illustrative creator source showing adjustable framing"
              style={{ objectPosition: `${position}% center` }}
            />
            <div className="crop-guides" aria-hidden="true" />
          </div>
          <div className="bento-crop-controls">
            <fieldset>
              <legend>Try a frame</legend>
              {["16:9", "1:1", "9:16"].map((item) => (
                <button
                  key={item}
                  aria-pressed={ratio === item}
                  onClick={() => setRatio(item)}
                >
                  {item}
                </button>
              ))}
            </fieldset>
            <label>
              Horizontal position
              <input
                aria-label="Demo crop horizontal position"
                type="range"
                min={0}
                max={100}
                value={position}
                onChange={(event) => setPosition(Number(event.target.value))}
              />
            </label>
            <p>Illustrative crop · source unchanged</p>
          </div>
        </div>
      </section>
      <section className="bento-script">
        <h3>Find your opening.</h3>
        <p>Explore different takes, then make the script yours.</p>
        <div className="bento-hooks">
          {hooks.map((text, index) => (
            <button
              key={text}
              aria-pressed={hook === index}
              onClick={() => setHook(index)}
            >
              <span className="radio-mark" aria-hidden="true" />
              {text}
            </button>
          ))}
        </div>
        <p className="bento-footnote">Illustrative hook alternatives</p>
      </section>
      <section className="bento-export">
        <h3>One story. Six destinations.</h3>
        <p>Platform dimensions, safe zones and independent post metadata.</p>
        <div className="preset-strip">
          {presets.map((item, index) => (
            <button
              key={item.id}
              aria-pressed={preset === index}
              onClick={() => setPreset(index)}
            >
              <span className="preset-thumb">
                <Image src="/media/coastline.webp" fill sizes="100px" alt="" />
              </span>
              <span>{item.name}</span>
            </button>
          ))}
        </div>
        <p className="bento-footnote" aria-live="polite">
          {presets[preset].name} · {presets[preset].width} ×{" "}
          {presets[preset].height}
        </p>
      </section>
    </div>
  );
}
