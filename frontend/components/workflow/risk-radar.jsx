"use client";
import { useState } from "react";
import { CheckCircle, Clock, Scan, WarningCircle } from "@phosphor-icons/react";
import {
  riskExportLabel,
  riskOriginLabel,
  riskReadinessLabel,
  sortRiskFindings,
  titleCase,
} from "@/lib/risk-radar.mjs";
import { Field } from "./common";
function demoReview(exportItem) {
  const label = riskExportLabel(exportItem);
  return {
    review_readiness: "creator_review_required",
    summary: `${label} has two sample review prompts for the creator to resolve before packaging. No content was sent to an AI service.`,
    reviewed_reference_count: 6,
    findings: [
      {
        category: "disclosure",
        severity: "medium",
        origin: "demo",
        title: "Partnership context needs a final check",
        description:
          "This prototype result shows how a required disclosure would be surfaced beside the final export.",
        recommendation:
          "Confirm the caption and on-screen disclosure before saving the package.",
        reference_ids: ["Sample caption", "Saved package copy"],
      },
      {
        category: "visual_review",
        severity: "low",
        origin: "demo",
        title: "Review the final frame",
        description:
          "This sample finding keeps the creator-facing visual review step visible in the prototype.",
        recommendation:
          "Play the finished export and confirm that framing and captions are clear.",
        reference_ids: ["Final render"],
      },
    ],
    limitations: [
      "Prototype mode shows sample findings in the browser and does not inspect project content.",
      "A connected RiskRadar scan should remain creator decision support, not legal clearance.",
    ],
  };
}
function Finding({ finding }) {
  return (
    <article className="risk-finding" data-severity={finding.severity}>
      <div className="risk-finding-meta">
        <span className="risk-severity">{titleCase(finding.severity)}</span>
        <span>{titleCase(finding.category)}</span>
        <span>{riskOriginLabel(finding.origin)}</span>
      </div>
      <h3>{finding.title}</h3>
      <p>{finding.description}</p>
      <p className="risk-recommendation">
        <strong>Recommended action:</strong> {finding.recommendation}
      </p>
      <div className="risk-evidence" aria-label="Evidence references">
        <strong>Evidence</strong>
        <ul>
          {finding.reference_ids.map((reference) => (
            <li key={reference}>{reference}</li>
          ))}
        </ul>
      </div>
    </article>
  );
}
export function RiskRadarPanel({ completedExports = [], disabled = false }) {
  const [selectedRenderId, setSelectedRenderId] = useState("");
  const [reviewing, setReviewing] = useState(false);
  const [result, setResult] = useState(null);
  const selected =
    completedExports.find((item) => item.id === selectedRenderId) ||
    completedExports[0];
  function runDemo() {
    if (!selected) return;
    setReviewing(true);
    setResult(null);
    window.setTimeout(() => {
      setResult(demoReview(selected));
      setReviewing(false);
    }, 700);
  }
  return (
    <section className="risk-radar" aria-labelledby="risk-radar-title">
      <div className="risk-radar-inner">
        <div className="risk-radar-heading">
          <div className="risk-radar-mark" aria-hidden="true">
            <Scan size={22} weight="light" />
          </div>
          <div>
            <h2 id="risk-radar-title">Pre-publish RiskRadar</h2>
            <p>
              Prototype preview of saved-content checks before package approval.
            </p>
          </div>
        </div>
        {completedExports.length === 0 ? (
          <p className="risk-radar-empty">
            Finish and verify a platform export before running RiskRadar.
          </p>
        ) : (
          <>
            <Field label="Export to review">
              <select
                value={selected?.id || ""}
                disabled={disabled || reviewing}
                onChange={(event) => {
                  setSelectedRenderId(event.target.value);
                  setResult(null);
                }}
              >
                {completedExports.map((item) => (
                  <option key={item.id} value={item.id}>
                    {riskExportLabel(item)}
                  </option>
                ))}
              </select>
            </Field>
            <div className="risk-radar-actions">
              <button
                type="button"
                disabled={disabled || reviewing}
                onClick={runDemo}
              >
                {result ? "Run demo again" : "Run demo review"}
              </button>
              <p>
                Browser-only prototype. It uses sample findings and does not
                call the backend or an AI provider.
              </p>
            </div>
          </>
        )}
        {reviewing && (
          <div className="risk-radar-progress" role="status" aria-live="polite">
            <Clock size={20} weight="light" aria-hidden="true" />
            <span>Preparing a sample creator review…</span>
          </div>
        )}
        {result && (
          <div className="risk-radar-result" aria-live="polite">
            <div
              className="risk-readiness"
              data-ready={result.review_readiness}
            >
              {result.review_readiness === "creator_review_required" ? (
                <WarningCircle size={21} weight="light" aria-hidden="true" />
              ) : (
                <CheckCircle size={21} weight="light" aria-hidden="true" />
              )}
              <span>{riskReadinessLabel(result.review_readiness)}</span>
            </div>
            <p className="risk-summary">{result.summary}</p>
            <p className="muted">
              Reviewed {result.reviewed_reference_count} saved content reference
              {result.reviewed_reference_count === 1 ? "" : "s"}.
            </p>
            {result.findings.length > 0 && (
              <div className="risk-findings">
                {sortRiskFindings(result.findings).map((finding) => (
                  <Finding
                    key={`${finding.origin}-${finding.category}-${finding.title}`}
                    finding={finding}
                  />
                ))}
              </div>
            )}
            <details className="risk-limitations">
              <summary>What RiskRadar cannot verify</summary>
              <ul>
                {result.limitations.map((limitation) => (
                  <li key={limitation}>{limitation}</li>
                ))}
              </ul>
            </details>
          </div>
        )}
      </div>
    </section>
  );
}
