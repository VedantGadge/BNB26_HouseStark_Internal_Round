/** Spoken content deliberately excludes headings, descriptions and production notes. */
export function spokenScript(content) {
  if (!content) return "";
  const hook = content.hooks.find((item) => item.id === content.selected_hook_id)?.text || "";
  const sections = [...content.sections].sort((a, b) => a.position - b.position).map((item) => item.text.trim());
  const cta = content.call_to_action.trim();
  const last = sections.at(-1) || "";
  return [hook, ...sections, ...(cta && !last.endsWith(cta) ? [cta] : [])].filter(Boolean).join("\n\n");
}

/** Overlay clocks are output-relative; source trim changes shift and clip every overlay. */
export function remapTrim(recipe, start, end) {
  const delta = start - recipe.source_start_ms, duration = end - start;
  const remap = (item) => ({ ...item, start_ms: Math.max(0, item.start_ms - delta), end_ms: Math.min(duration, item.end_ms - delta) });
  const visible = (item) => item.end_ms > item.start_ms;
  const title = recipe.title ? remap(recipe.title) : null;
  return { ...recipe, source_start_ms: start, source_end_ms: end,
    captions: recipe.captions.map(remap).filter(visible),
    emphasis_zooms: recipe.emphasis_zooms.map(remap).filter(visible),
    title: title && visible(title) ? title : null };
}

export const presets = [
  { id: "instagram_reel", name: "Instagram Reel", platform: "instagram", width: 1080, height: 1920, safeTop: 220, safeBottom: 360 },
  { id: "tiktok", name: "TikTok", platform: "tiktok", width: 1080, height: 1920, safeTop: 180, safeBottom: 380 },
  { id: "youtube_short", name: "YouTube Short", platform: "youtube", width: 1080, height: 1920, safeTop: 160, safeBottom: 280 },
  { id: "instagram_feed", name: "Instagram Feed", platform: "instagram", width: 1080, height: 1080, safeTop: 80, safeBottom: 130 },
  { id: "linkedin_feed", name: "LinkedIn Feed", platform: "linkedin", width: 1080, height: 1080, safeTop: 80, safeBottom: 130 },
  { id: "youtube_video", name: "YouTube Video", platform: "youtube", width: 1920, height: 1080, safeTop: 70, safeBottom: 100 },
];

export const humanize = (value) => String(value || "").replaceAll("_", " ");
export const lines = (value) => String(value || "").split("\n").map((line) => line.trim()).filter(Boolean);
export const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

export function localDate(value) {
  if (!value) return "";
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return "";
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}
