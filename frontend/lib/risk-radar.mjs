export const riskSeverityRank = { high: 0, medium: 1, low: 2 };

export function sortRiskFindings(findings = []) {
  return [...findings].sort(
    (left, right) =>
      (riskSeverityRank[left.severity] ?? 3) -
      (riskSeverityRank[right.severity] ?? 3),
  );
}

export function riskExportLabel(exportItem) {
  if (!exportItem) return "";
  return `${titleCase(exportItem.platform)} · ${exportItem.preset_name}`;
}

export function riskReadinessLabel(readiness) {
  return readiness === "creator_review_required"
    ? "Creator review required"
    : "No high or medium risks found";
}

export function riskOriginLabel(origin) {
  if (origin === "deterministic") return "Detected rule";
  if (origin === "demo") return "Sample review";
  return "AI review";
}

export function titleCase(value) {
  return String(value || "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}
