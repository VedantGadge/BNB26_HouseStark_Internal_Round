import Link from "next/link";

const sections = [
  ["Overview", ""],
  ["Script", "/script"],
  ["Assets", "/assets"],
  ["Clips", "/clips"],
  ["Publish", "/publish"],
  ["Insights", "/insights"],
];

export function ProjectShell({ projectId, children }) {
  const root = `/projects/${projectId}`;

  return (
    <div className="min-h-screen md:grid md:grid-cols-[15rem_1fr]">
      <aside className="border-b border-[#e5e5e9] bg-white p-5 md:min-h-screen md:border-r md:border-b-0">
        <Link className="text-lg font-semibold" href="/projects">
          CreatorAI
        </Link>
        <p className="mt-1 truncate text-xs text-[#6c6c75]">{projectId}</p>
        <nav aria-label="Project sections" className="mt-8 flex gap-1 overflow-x-auto md:flex-col">
          {sections.map(([label, suffix]) => (
            <Link
              className="whitespace-nowrap rounded-md px-3 py-2 text-sm text-[#4d4d55] hover:bg-[#f2f2f4] hover:text-[#17171a]"
              href={`${root}${suffix}`}
              key={label}
            >
              {label}
            </Link>
          ))}
        </nav>
      </aside>
      <main className="p-6 md:p-10">{children}</main>
    </div>
  );
}
