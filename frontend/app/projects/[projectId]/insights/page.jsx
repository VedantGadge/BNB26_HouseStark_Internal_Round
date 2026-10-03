import { Insights } from "@/components/workflow/insights";

export default async function Page({ params }) {
  const { projectId } = await params;
  return <Insights projectId={projectId} />;
}
