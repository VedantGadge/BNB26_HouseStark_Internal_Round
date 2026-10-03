import Link from "next/link";

export default function ProjectsPage() {
  return (
    <main className="mx-auto max-w-4xl px-6 py-16">
      <p className="text-sm font-medium text-[#635bff]">CreatorAI</p>
      <h1 className="mt-3 text-4xl font-semibold tracking-tight">Your projects</h1>
      <p className="mt-4 max-w-xl text-[#6c6c75]">
        The project shell is ready. Connect the projects endpoint to create your first creator workflow.
      </p>
      <Link
        className="mt-8 inline-flex rounded-md bg-[#17171a] px-4 py-2 text-sm font-medium text-white"
        href="/projects/example-project"
      >
        Open the workspace scaffold
      </Link>
    </main>
  );
}
