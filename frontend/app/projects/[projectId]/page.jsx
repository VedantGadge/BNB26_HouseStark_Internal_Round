import { Overview } from "@/components/workflow/overview";

export default async function Page({ params }) {
  const { projectId } = await params;
  return <Overview projectId={projectId} />;
}
