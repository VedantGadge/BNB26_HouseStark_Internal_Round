import Link from "next/link";
import { ArrowRight } from "@phosphor-icons/react/dist/ssr";
import { Brand, ThemeToggle } from "@/components/ui/studio-ui";
import { SaaSDemo, FeatureBento } from "@/components/landing/saas-demo";
import { SaaSStory, WorkflowAccordion } from "@/components/landing/saas-story";

export default function HomePage() {
  return (
    <div className="landing saas-landing">
      <header className="landing-nav">
        <Brand />
        <nav aria-label="Main navigation">
          <Link href="#workflow">Workflow</Link>
          <Link href="/projects">Studio</Link>
        </nav>
        <div className="nav-actions">
          <ThemeToggle />
          <Link className="button secondary" href="/projects">
            Open studio
            <ArrowRight size={17} weight="light" />
          </Link>
        </div>
      </header>
      <main id="main-content" className="saas-main">
        <section className="saas-hero">
          <h1>
            One workspace.
            <br className="desktop-break" /> From idea to{" "}
            <span className="keep-word">publish-ready.</span>
          </h1>
          <p className="hero-copy">
            Write in your voice, find grounded clips and shape every edit.
            <br className="desktop-break" /> Export verified videos, then track
            what you publish.
          </p>
          <div className="hero-action">
            <Link href="/projects" className="button">
              Start creating
              <ArrowRight size={18} weight="light" />
            </Link>
            <Link href="#workflow" className="button secondary">
              Explore the workflow
            </Link>
          </div>
          <SaaSDemo />
        </section>
        <section
          className="saas-interest"
          aria-label="Explore the creator tools"
        >
          <FeatureBento />
        </section>
        <WorkflowAccordion />
        <SaaSStory />
        <section className="faq saas-faq">
          <h2>A few things worth knowing.</h2>
          {[
            [
              "Will my original footage change?",
              "No. Your source stays intact. Saved edits are immutable recipes, and each export is a separate verified MP4.",
            ],
            [
              "Does CreatorAI publish for me?",
              "You download your exports and publish them yourself. CreatorAI tracks your plans and lets you record the actual post URL and publication time.",
            ],
            [
              "Can I edit the suggestions?",
              "Yes. Choose a hook, edit the script, review assistant proposals, trim clips, correct captions and adjust framing. AI proposals do not apply themselves.",
            ],
            [
              "Which formats can I export?",
              "Instagram Reel, TikTok, YouTube Short, Instagram Feed, LinkedIn Feed and YouTube Video, with preset-specific dimensions and safe zones.",
            ],
            [
              "How are insights measured?",
              "Production activity comes from your workflow records. Performance comes from observations you enter with their source and reporting window. Missing counts stay unknown, not zero.",
            ],
          ].map(([question, answer]) => (
            <details key={question}>
              <summary>{question}</summary>
              <p>{answer}</p>
            </details>
          ))}
        </section>
        <section className="saas-action">
          <h2>
            Make your next story.
            <br />
            Keep every decision yours.
          </h2>
          <p>One place to write, edit and get your work ready for the world.</p>
          <Link href="/projects" className="button">
            Start creating
            <ArrowRight size={20} weight="light" />
          </Link>
        </section>
      </main>
      <footer className="landing-footer">
        <Brand />
        <p>Your work. Your voice. Your creative decisions.</p>
      </footer>
    </div>
  );
}
