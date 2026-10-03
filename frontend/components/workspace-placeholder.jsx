export function WorkspacePlaceholder({ title, description }) {
  return (
    <section className="max-w-3xl">
      <h1 className="text-3xl font-semibold tracking-tight">{title}</h1>
      <p className="mt-3 text-[#6c6c75]">{description}</p>
      <div className="mt-8 rounded-lg border border-dashed border-[#d7d7dc] bg-white p-6 text-sm text-[#6c6c75]">
        This route is reserved and ready for its feature module.
      </div>
    </section>
  );
}
