import { Script } from "@/components/workflow/script";

export default async function Page({ params }) {
  const { projectId } = await params;
  return <Script projectId={projectId} />;
}
