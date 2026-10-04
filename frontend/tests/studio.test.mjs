import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  stageGroup,
  workflowPosition,
  nextProjectPath,
} from "../lib/studio.mjs";

test("every backend workflow stage has an honest project lane", () => {
  assert.equal(stageGroup("idea"), "ideas");
  for (const stage of ["assets", "editing"])
    assert.equal(stageGroup(stage), "creating");
  for (const stage of ["review", "approved", "exported", "published"])
    assert.equal(stageGroup(stage), "delivery");
  assert.equal(stageGroup("future-stage"), "creating");
});

test("workflow navigation preserves the established project routes", () => {
  assert.equal(nextProjectPath("demo", "idea"), "/projects/demo/script");
  assert.equal(nextProjectPath("demo", "assets"), "/projects/demo/assets");
  assert.equal(nextProjectPath("demo", "editing"), "/projects/demo/clips");
  assert.equal(nextProjectPath("demo", "exported"), "/projects/demo/publish");
  assert.equal(workflowPosition("published"), 3);
});

function luminance(hex) {
  const rgb = hex
    .slice(1)
    .match(/../g)
    .map((value) => parseInt(value, 16) / 255)
    .map((value) =>
      value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4,
    );
  return rgb.reduce(
    (sum, value, index) => sum + value * [0.2126, 0.7152, 0.0722][index],
    0,
  );
}
function contrast(a, b) {
  const x = luminance(a),
    y = luminance(b);
  return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
}

test("Instagram-inspired text and selection tokens stay readable in both themes", () => {
  const css = readFileSync(
    new URL("../app/globals.css", import.meta.url),
    "utf8",
  );
  for (const theme of [
    css.match(/:root\s*\{([^}]+)\}/)[1],
    css.match(/html\[data-theme="dark"\]\s*\{([^}]+)\}/)[1],
  ]) {
    const token = (name) =>
      theme.match(new RegExp("--" + name + ":\\s*(#[0-9a-f]{6})"))[1];
    for (const [text, background] of [
      ["foreground", "background"],
      ["muted", "background"],
      ["accent", "background"],
      ["accent", "accent-soft"],
    ])
      assert.ok(
        contrast(token(text), token(background)) >= 4.5,
        text + " / " + background,
      );
  }
  for (const rejected of [
    "#5548e8",
    "#aaa2ff",
    "#a69aff",
    "#342c69",
    "#b3a7ff",
  ])
    assert.equal(css.includes(rejected), false);
});
