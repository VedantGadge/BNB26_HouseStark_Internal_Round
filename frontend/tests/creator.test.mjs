import test from "node:test";
import assert from "node:assert/strict";
import { spokenScript, remapTrim, presets, localDate } from "../lib/creator.mjs";

const script = { hooks: [{ id: "a", text: "Selected hook" }, { id: "b", text: "Unused hook" }], selected_hook_id: "a", sections: [{ position: 2, text: "Ending. Follow along." }, { position: 1, text: "First beat" }], call_to_action: "Follow along.", title: "Metadata only" };
test("spoken read uses selected hook, sorted sections and no duplicate closing CTA", () => assert.equal(spokenScript(script), "Selected hook\n\nFirst beat\n\nEnding. Follow along."));
test("a separate CTA is included exactly once", () => assert.ok(spokenScript({ ...script, call_to_action: "Save this." }).endsWith("\n\nSave this.")));
test("missing script is readable empty state", () => assert.equal(spokenScript(null), ""));
const recipe = { source_start_ms: 1000, source_end_ms: 10000, captions: [{ start_ms: 0, end_ms: 1500, text: "removed" }, { start_ms: 2000, end_ms: 5000, text: "retained" }], emphasis_zooms: [{ start_ms: 0, end_ms: 4000, scale: 1.08 }], title: { start_ms: 0, end_ms: 1000, text: "Title" } };
test("trim remaps output clocks without mutating original", () => {
  const result = remapTrim(recipe, 3000, 5500);
  assert.deepEqual(result.captions, [{ start_ms: 0, end_ms: 2500, text: "retained" }]);
  assert.equal(result.title, null); assert.equal(result.emphasis_zooms[0].end_ms, 2000); assert.equal(recipe.captions.length, 2);
});
test("expanding source trim moves overlays later", () => assert.equal(remapTrim(recipe, 0, 10000).captions[0].start_ms, 1000));
test("six presets preserve safe zones and platform matching", () => { assert.equal(presets.length, 6); assert.equal(presets.find((p) => p.id === "instagram_reel").safeBottom, 360); assert.equal(presets.find((p) => p.id === "youtube_video").platform, "youtube"); });
test("local dates tolerate missing and invalid values", () => { assert.equal(localDate(null), ""); assert.equal(localDate("invalid"), ""); assert.equal(localDate("2026-01-01T12:00:00Z").length, 16); });
