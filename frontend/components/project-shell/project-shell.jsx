"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ArrowLeft, ChartBar, Files, House, NotePencil, Scissors, ShareNetwork } from "@phosphor-icons/react";
import { Brand, SessionControl, ThemeToggle } from "@/components/ui/studio-ui";
import { useApi } from "@/components/workflow/common";

const sections = [["Overview", "", House], ["Script", "/script", NotePencil], ["Assets", "/assets", Files], ["Clips", "/clips", Scissors], ["Publish", "/publish", ShareNetwork], ["Insights", "/insights", ChartBar]];

export function StudioShell({ projectId, children }) {
  const root = projectId ? `/projects/${projectId}` : "/projects";
  const project = useApi(projectId ? root : null);
  const path = usePathname();
  return <div className="studio-shell"><aside className="studio-sidebar">
    <Brand /><Link className="back-link" href="/projects"><ArrowLeft size={17} weight="light" />All projects</Link>
    {projectId && <div className="project-label">{project.data?.name || "Project workspace"}</div>}
    <nav aria-label={projectId ? "Project sections" : "Studio navigation"}>
      {(projectId ? sections : [["Projects", "", Files]]).map(([label, suffix, Icon]) => {
        const href = root + suffix, active = suffix ? path.startsWith(href) : path === href;
        return <Link key={label} href={href} aria-current={active ? "page" : undefined}><Icon weight="light" size={22} /><span>{label}</span></Link>;
      })}
    </nav>
    <div className="sidebar-footer"><div className="theme-row"><span>Appearance</span><ThemeToggle /></div><SessionControl /></div>
  </aside><main id="main-content" className="studio-main">{children}</main></div>;
}
export function ProjectShell({ projectId, children }) { return <StudioShell projectId={projectId}>{children}</StudioShell>; }
