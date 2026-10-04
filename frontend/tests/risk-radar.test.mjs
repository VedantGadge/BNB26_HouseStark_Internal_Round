import test from "node:test";
import assert from "node:assert/strict";
import {
  riskExportLabel,
  riskOriginLabel,
  riskReadinessLabel,
  sortRiskFindings,
} from "../lib/risk-radar.mjs";

const completedExport = {
  id: "render-1",
  asset_id: "asset-1",
  edit_version_id: "edit-1",
  platform: "instagram",
  preset_name: "instagram_reel",
};

test("RiskRadar labels the selected export", () => {
  assert.equal(riskExportLabel(completedExport), "Instagram · instagram_reel");
});

test("RiskRadar findings are severity-ordered without mutating the API result", () => {
  const findings = [
    { severity: "low", title: "Low" },
    { severity: "high", title: "High" },
    { severity: "medium", title: "Medium" },
  ];
  assert.deepEqual(
    sortRiskFindings(findings).map((finding) => finding.title),
    ["High", "Medium", "Low"],
  );
  assert.deepEqual(
    findings.map((finding) => finding.title),
    ["Low", "High", "Medium"],
  );
});

test("RiskRadar uses honest readiness and origin labels", () => {
  assert.equal(
    riskReadinessLabel("creator_review_required"),
    "Creator review required",
  );
  assert.equal(
    riskReadinessLabel("no_high_or_medium_risks_found"),
    "No high or medium risks found",
  );
  assert.equal(riskOriginLabel("deterministic"), "Detected rule");
  assert.equal(riskOriginLabel("demo"), "Sample review");
  assert.equal(riskOriginLabel("model"), "AI review");
});
