import { Publish } from "@/components/workflow/publish";

export default async function Page({ params }) {
  const { projectId } = await params;
  return <Publish projectId={projectId} />;
}
