import { Clips } from "@/components/workflow/clips";

export default async function Page({ params }) {
  const { projectId } = await params;
  return <Clips projectId={projectId} />;
}
