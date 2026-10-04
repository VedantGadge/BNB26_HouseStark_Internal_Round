"use client";

import { useRef, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useGSAP } from "@gsap/react";
import {
  ArrowLeft,
  ArrowRight,
  NotePencil,
  MagnifyingGlass,
  Scissors,
  Export,
} from "@phosphor-icons/react";

gsap.registerPlugin(useGSAP, ScrollTrigger);
const stages = [
  {
    name: "Write",
    icon: NotePencil,
    copy: "Start with your idea. Shape a script in your voice, compare hooks and review changes before they apply.",
    detail: "Saved creator style · Editable scripts · Proposal review",
    image: "/media/creator-preview.webp",
    destination: "Script",
  },
  {
    name: "Find",
    icon: MagnifyingGlass,
    copy: "Bring in your source. Find candidate moments grounded in transcript and visual evidence—or choose a range yourself.",
    detail: "Private sources · Timestamped evidence · Manual clips",
    image: "/media/coastline.webp",
    destination: "Assets and clips",
  },
  {
    name: "Shape",
    icon: Scissors,
    copy: "Keep the original untouched. Trim, correct captions, adjust framing and save an immutable edit version.",
    detail: "Editable captions · Crop controls · Version history",
    image: "/media/creator-preview.webp",
    destination: "Editor",
  },
  {
    name: "Share",
    icon: Export,
    copy: "Export a verified video for each platform. Review the final output, record your publication and learn from your observations.",
    detail: "Six presets · Approval workflow · Recorded insights",
    image: "/media/coastline.webp",
    destination: "Publish and insights",
  },
];
const examples = [
  {
    task: "A stronger opening",
    before: "Today I’m going to talk about this coastline.",
    after: "One coastline. A completely different point of view.",
    explanation:
      "Compare hooks, choose your opening and keep the wording that feels like you.",
  },
  {
    task: "A clearer caption",
    before: "Makingroomforanewperspective.",
    after: "Make room for a new perspective.",
    explanation:
      "Correct the words and timing yourself. A new edit version preserves the original.",
  },
  {
    task: "The right frame",
    before: "A landscape story for every destination.",
    after: "Portrait for Shorts. Square for the feed. Landscape for YouTube.",
    explanation:
      "Choose a supported preset and review the actual exported video before publishing.",
  },
];

export function WorkflowAccordion() {
  const [open, setOpen] = useState(0);
  return (
    <section id="workflow" className="saas-chapter workflow-chapter">
      <h2>
        Make{" "}
        <span className="inline-photo">
          <Image src="/media/coastline.webp" fill sizes="140px" alt="" />
        </span>{" "}
        every moment count.
      </h2>
      <p className="chapter-copy">
        From a first idea to the final post. Each step carries your creative
        decisions forward.
      </p>
      <div className="horizontal-accordion">
        {stages.map((stage, index) => (
          <article
            className={`workflow-slice ${open === index ? "is-open" : ""}`}
            key={stage.name}
          >
            <button
              className="workflow-toggle"
              aria-expanded={open === index}
              aria-controls={`workflow-panel-${index}`}
              onClick={() => setOpen(index)}
              onPointerEnter={(event) => {
                if (event.pointerType === "mouse") setOpen(index);
              }}
            >
              <stage.icon size={25} weight="light" />
              <span>{stage.name}</span>
            </button>
            <div
              className="workflow-panel"
              id={`workflow-panel-${index}`}
              hidden={open !== index}
            >
              <div className="workflow-photo">
                <Image
                  src={stage.image}
                  fill
                  sizes="(max-width:800px) 85vw, 45vw"
                  alt="Illustrative coastal creator story"
                />
              </div>
              <p>{stage.copy}</p>
              <p className="workflow-detail">{stage.detail}</p>
              <Link href="/projects" className="text-link">
                Explore {stage.destination.toLowerCase()}
                <ArrowRight size={18} weight="light" />
              </Link>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

export function SaaSStory() {
  const root = useRef(null),
    [example, setExample] = useState(0);
  useGSAP(
    () => {
      const media = gsap.matchMedia();
      media.add("(prefers-reduced-motion: no-preference)", () => {
        gsap.fromTo(
          ".reveal-word",
          { opacity: 0.65 },
          {
            opacity: 1,
            stagger: 0.18,
            ease: "none",
            scrollTrigger: {
              trigger: ".scrub-copy",
              start: "top 75%",
              end: "bottom 45%",
              scrub: 0.7,
            },
          },
        );
        const timeline = gsap.timeline({
          scrollTrigger: {
            trigger: ".story-media",
            start: "top bottom",
            end: "bottom top",
            scrub: 0.8,
          },
        });
        timeline
          .fromTo(
            ".story-media-image",
            { scale: 0.8, opacity: 1 },
            { scale: 1, opacity: 1, duration: 1, ease: "none" },
          )
          .to(".story-media-image", {
            opacity: 0.2,
            duration: 1,
            ease: "none",
          });
      });
      return () => media.revert();
    },
    { scope: root },
  );
  const current = examples[example];
  return (
    <div ref={root} className="saas-desire">
      <section className="saas-chapter story-chapter">
        <div className="scrub-copy">
          <h2 aria-label="Your voice. Your footage. Your final say.">
            <span aria-hidden="true">
              {"Your voice. Your footage. Your final say."
                .split(" ")
                .map((word, index) => (
                  <span key={index} className="reveal-word">
                    {word}{" "}
                  </span>
                ))}
            </span>
          </h2>
        </div>
        <p className="chapter-copy">
          AI offers a starting point. You choose the hook, review the proposal
          and shape the final edit. Nothing publishes itself.
        </p>
        <div className="story-media">
          <div className="story-media-image">
            <Image
              src="/media/coastline.webp"
              fill
              sizes="(max-width:800px) 100vw, 1160px"
              alt=""
            />
            <div className="story-media-caption">Keep your perspective.</div>
          </div>
        </div>
      </section>
      <section className="saas-chapter feedback-chapter">
        <div>
          <h2>
            Small decisions.
            <br />A story that feels yours.
          </h2>
          <p className="chapter-copy">
            See how the workflow supports a creative choice. These are
            illustrative examples, not customer testimonials.
          </p>
        </div>
        <div
          className="feedback-carousel"
          aria-roledescription="carousel"
          aria-label="Illustrative editing examples"
        >
          <div className="feedback-top">
            <h3>{current.task}</h3>
            <div className="carousel-actions">
              <button
                className="icon-button"
                aria-label="Previous editing example"
                onClick={() =>
                  setExample((example + examples.length - 1) % examples.length)
                }
              >
                <ArrowLeft size={20} weight="light" />
              </button>
              <button
                className="icon-button"
                aria-label="Next editing example"
                onClick={() => setExample((example + 1) % examples.length)}
              >
                <ArrowRight size={20} weight="light" />
              </button>
            </div>
          </div>
          <div
            className="feedback-content"
            aria-live="polite"
            aria-atomic="true"
          >
            <p className="feedback-before">{current.before}</p>
            <p className="feedback-after">{current.after}</p>
            <p>{current.explanation}</p>
            <span className="carousel-position">
              Example {example + 1} of {examples.length}
            </span>
          </div>
        </div>
      </section>
    </div>
  );
}
