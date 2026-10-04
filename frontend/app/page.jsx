import Link from "next/link";
import Image from "next/image";
import { ArrowRight, NotePencil, MagnifyingGlass, Scissors, Export } from "@phosphor-icons/react/dist/ssr";
import { Brand, ThemeToggle } from "@/components/ui/studio-ui";
import { HeroPreview, EditDemo } from "@/components/landing/previews";

export default function HomePage() {
  return <div className="landing"><header className="landing-nav"><Brand/><nav aria-label="Main navigation"><Link href="#workflow">Workflow</Link><Link href="/projects">Studio</Link></nav><div className="nav-actions"><ThemeToggle/><Link className="button" href="/projects">Open studio<ArrowRight size={18} weight="light"/></Link></div></header>
    <main id="main-content"><section className="landing-hero"><h1>Turn your footage into<br className="desktop-break"/> your next great story.</h1><p className="hero-copy">Write, find your best moments, shape the edit and export for each channel.<br className="desktop-break"/> One connected creator workspace.</p><div className="hero-action"><Link href="/projects" className="button">Start creating<span className="arrow-tail"><ArrowRight size={18} weight="light"/></span></Link></div><HeroPreview/></section>
      <section className="workflow-rail" id="workflow"><h2>A simpler way from footage to everywhere.</h2><div className="workflow-steps">{[[NotePencil,"Write","Turn your idea into a clear script, in your voice."],[MagnifyingGlass,"Find","Find moments grounded in your source evidence."],[Scissors,"Shape","Trim, correct captions and make the edit your own."],[Export,"Share","Export for Instagram, TikTok, YouTube and LinkedIn."]].map(([Icon,title,copy])=><div className="workflow-step" key={title}><Icon size={28} weight="light"/><div><h3>{title}</h3><p>{copy}</p></div></div>)}</div></section>
      <section className="landing-section"><div><h2>Keep the original.<br/>Own the edit.</h2><p>Your footage stays untouched. Trim the moment, correct the captions and save a new version. You decide what makes the cut.</p><Link className="text-link" href="/projects">Explore the studio<ArrowRight size={19} weight="light"/></Link></div><EditDemo/></section>
      <div className="formats-band"><section className="landing-section"><div><h2>One story.<br/>The right frame.</h2><p>Six export presets with platform safe zones and independent titles, captions and hashtags.</p></div><div className="format-examples">{[["9:16","Reels, TikTok, Shorts"],["1:1","Instagram, LinkedIn"],["16:9","YouTube Video"]].map(([ratio,name])=><div className="format-example" key={ratio}><div className="demo-frame"><Image src="/media/coastline.webp" fill sizes="(max-width:800px) 35vw, 20vw" alt={`Illustrative source framed for ${ratio}`}/></div><p>{ratio} · {name}</p></div>)}</div></section></div>
      <section className="faq"><h2>Frequently asked questions</h2>{[
        ["Will my original footage change?","No. Your source stays intact. Saved edits are immutable recipes, and each export is a separate verified MP4."],
        ["Does CreatorAI publish for me?","You download your exports and publish them yourself. CreatorAI tracks your plans and lets you record the actual post URL and publication time."],
        ["Can I edit the suggestions?","Yes. Choose a hook, edit the script, review assistant proposals, trim clips, correct captions and adjust framing. AI proposals do not apply themselves."],
        ["Which formats can I export?","Instagram Reel, TikTok, YouTube Short, Instagram Feed, LinkedIn Feed and YouTube Video, with preset-specific dimensions and safe zones."],
        ["How are insights measured?","Production activity comes from your workflow records. Performance comes from observations you enter with their source and reporting window. Missing counts stay unknown, not zero."],
      ].map(([question,answer])=><details key={question}><summary>{question}</summary><p>{answer}</p></details>)}</section>
      <section className="landing-close"><h2>Your next story starts here.</h2><Link className="button" href="/projects">Open studio<ArrowRight size={19} weight="light"/></Link></section>
    </main><footer className="landing-footer"><Brand/><p>A connected workspace. Your creative decisions.</p></footer>
  </div>;
}
