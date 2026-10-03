import { ProjectShell } from "@/components/project-shell/project-shell";

export default async function ProjectLayout({ children, params }) {
  const { projectId } = await params;
  return <ProjectShell projectId={projectId}>{children}</ProjectShell>;
}
