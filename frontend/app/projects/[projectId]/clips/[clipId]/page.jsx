import { Editor } from "@/components/workflow/editor";

export default async function Page({ params }) {
  const { projectId, clipId } = await params;
  return <Editor projectId={projectId} clipId={clipId} />;
}
