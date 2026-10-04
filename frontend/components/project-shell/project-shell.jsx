"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ArrowLeft,
  ArrowUpRight,
  ChartBar,
  Files,
  House,
  NotePencil,
  Scissors,
  ShareNetwork,
  Stack,
  CaretRight,
} from "@phosphor-icons/react";
import { Brand, SessionControl, ThemeToggle } from "@/components/ui/studio-ui";
import { useApi } from "@/components/workflow/common";

const sections = [
  ["Overview", "", House],
  ["Script", "/script", NotePencil],
  ["Assets", "/assets", Files],
  ["Clips", "/clips", Scissors],
  ["Publish", "/publish", ShareNetwork],
  ["Insights", "/insights", ChartBar],
];

export function StudioShell({ projectId, children }) {
  const root = projectId ? `/projects/${projectId}` : "/projects";
  const project = useApi(projectId ? root : null);
  const path = usePathname();
  const current =
    sections.find(
      ([, suffix]) => suffix && path.startsWith(root + suffix),
    )?.[0] || (projectId ? "Overview" : "Projects");
  return (
    <div className="studio-shell">
      <aside className="studio-sidebar">
        <Brand />
        <Link className="back-link" href="/projects">
          <ArrowLeft size={17} weight="light" />
          All projects
        </Link>
        {projectId && (
          <div className="project-label">
            {project.data?.name || "Project workspace"}
          </div>
        )}
        <nav aria-label={projectId ? "Project sections" : "Studio navigation"}>
          {(projectId ? sections : [["Projects", "", Files]]).map(
            ([label, suffix, Icon]) => {
              const href = root + suffix,
                active = suffix ? path.startsWith(href) : path === href;
              return (
                <Link
                  key={label}
                  href={href}
                  aria-current={active ? "page" : undefined}
                >
                  <Icon weight="light" size={22} />
                  <span>{label}</span>
                </Link>
              );
            },
          )}
        </nav>
        <div className="sidebar-footer">
          <div className="workspace-identity">
            <Stack size={21} weight="light" />
            <div>
              <strong>Creator studio</strong>
              <span>Local workspace</span>
            </div>
          </div>
          <Link className="back-link" href="/">
            Visit website <ArrowUpRight size={16} />
          </Link>
        </div>
      </aside>
      <main id="main-content" className="studio-main">
        <header className="studio-topbar">
          <nav aria-label="Breadcrumb">
            <Link href="/projects">Studio</Link>
            <CaretRight size={14} />
            {projectId && (
              <>
                <Link href={root}>{project.data?.name || "Project"}</Link>
                <CaretRight size={14} />
              </>
            )}
            <span aria-current="page">{current}</span>
          </nav>
          <div className="studio-topbar-actions">
            <ThemeToggle />
            <SessionControl />
          </div>
        </header>
        <div className="studio-content">{children}</div>
      </main>
    </div>
  );
}
export function ProjectShell({ projectId, children }) {
  return <StudioShell projectId={projectId}>{children}</StudioShell>;
}
