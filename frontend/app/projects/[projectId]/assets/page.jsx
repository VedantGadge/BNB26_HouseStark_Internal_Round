import { Assets } from "@/components/workflow/assets";

export default async function Page({ params }) {
  const { projectId } = await params;
  return <Assets projectId={projectId} />;
}
