"use client";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { optionalFetch, put, post } from "@/lib/api";
import { lines } from "@/lib/creator.mjs";
import { Field, Job, Status, useAction } from "@/components/workflow/common";

export function useScriptContext(root) {
  const style = useQuery({
    queryKey: ["/me/style-profile"],
    queryFn: () => optionalFetch("/me/style-profile"),
  });
  const campaign = useQuery({
    queryKey: [root + "/campaign-brief"],
    queryFn: () => optionalFetch(root + "/campaign-brief"),
  });
  return { style, campaign };
}

export function StyleProfile({ query }) {
  const [profile, setProfile] = useState(null),
    [job, setJob] = useState(null),
    [suggestion, setSuggestion] = useState(null);
  const [dirty, setDirty] = useState(false),
    [message, setMessage] = useState(""),
    [baseRevision, setBaseRevision] = useState(null);
  const action = useAction();
  useEffect(() => {
    if (!dirty) {
      setProfile(
        query.data?.profile || {
          voice: "",
          pacing: "",
          typical_structure: "",
          preferred_language: null,
          preferred_ctas: [],
          avoided_expressions: [],
          signature_lines: [],
        },
      );
      setBaseRevision(query.data?.revision || null);
    }
  }, [query.data, dirty]);
  const update = (key, value) => {
    setDirty(true);
    setProfile((p) => ({ ...p, [key]: value }));
    setMessage("");
  };
  return (
    <section className="form-section">
      <h2>Your creator style</h2>
      <p className="muted">
        Save the voice and patterns you want to reuse. Suggestions are reviewed
        before becoming your profile.
      </p>
      <Status query={query} error={action.error} />
      {profile && (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            action.run(async () => {
              await put("/me/style-profile", {
                base_revision: baseRevision,
                profile: {
                  ...profile,
                  preferred_ctas: profile.preferred_ctas
                    .map((v) => v.trim())
                    .filter(Boolean),
                  avoided_expressions: profile.avoided_expressions
                    .map((v) => v.trim())
                    .filter(Boolean),
                },
                suggestion_id: suggestion?.id || null,
              });
              setDirty(false);
              setMessage("Creator style saved.");
              setSuggestion(null);
            });
          }}
        >
          <div className="columns">
            {[
              ["voice", "Voice", 500],
              ["pacing", "Pacing", 500],
            ].map(([key, label, max]) => (
              <Field key={key} label={label}>
                <textarea
                  value={profile[key] || ""}
                  maxLength={max}
                  onChange={(event) => update(key, event.target.value)}
                />
              </Field>
            ))}
          </div>
          <Field label="Typical structure">
            <textarea
              value={profile.typical_structure || ""}
              maxLength={1000}
              onChange={(event) =>
                update("typical_structure", event.target.value)
              }
            />
          </Field>
          <div className="columns">
            <Field label="Preferred language">
              <select
                value={profile.preferred_language || ""}
                onChange={(event) =>
                  update("preferred_language", event.target.value || null)
                }
              >
                <option value="">No preference</option>
                {["english", "hindi", "hinglish"].map((v) => (
                  <option key={v}>{v}</option>
                ))}
              </select>
            </Field>
            <Field label="Preferred calls to action (one per line)">
              <textarea
                value={profile.preferred_ctas.join("\n")}
                onChange={(event) =>
                  update("preferred_ctas", event.target.value.split("\n"))
                }
              />
            </Field>
          </div>
          <Field label="Expressions to avoid (one per line)">
            <textarea
              value={profile.avoided_expressions.join("\n")}
              onChange={(event) =>
                update("avoided_expressions", event.target.value.split("\n"))
              }
            />
          </Field>
          <h3>Signature lines</h3>
          {profile.signature_lines.map((line, index) => (
            <div className="columns" key={line.id}>
              <Field label={`Signature line ${index + 1}`}>
                <input
                  value={line.text}
                  required
                  maxLength={240}
                  onChange={(event) =>
                    update(
                      "signature_lines",
                      profile.signature_lines.map((item, i) =>
                        i === index
                          ? { ...item, text: event.target.value }
                          : item,
                      ),
                    )
                  }
                />
              </Field>
              <Field label="Inclusion">
                <select
                  value={line.inclusion_policy}
                  onChange={(event) =>
                    update(
                      "signature_lines",
                      profile.signature_lines.map((item, i) =>
                        i === index
                          ? { ...item, inclusion_policy: event.target.value }
                          : item,
                      ),
                    )
                  }
                >
                  {["always", "when_relevant", "on_request"].map((v) => (
                    <option key={v}>{v}</option>
                  ))}
                </select>
              </Field>
              <Field label="Placement">
                <select
                  value={line.placement}
                  onChange={(event) =>
                    update(
                      "signature_lines",
                      profile.signature_lines.map((item, i) =>
                        i === index
                          ? { ...item, placement: event.target.value }
                          : item,
                      ),
                    )
                  }
                >
                  {["opening", "body", "closing"].map((v) => (
                    <option key={v}>{v}</option>
                  ))}
                </select>
              </Field>
              <button
                type="button"
                className="secondary"
                onClick={() =>
                  update(
                    "signature_lines",
                    profile.signature_lines.filter((_, i) => i !== index),
                  )
                }
              >
                Remove line {index + 1}
              </button>
            </div>
          ))}
          <button
            type="button"
            className="secondary"
            disabled={profile.signature_lines.length >= 10}
            onClick={() =>
              update("signature_lines", [
                ...profile.signature_lines,
                {
                  id: crypto.randomUUID(),
                  text: "",
                  inclusion_policy: "when_relevant",
                  placement: "closing",
                },
              ])
            }
          >
            Add signature line
          </button>
          {dirty && baseRevision !== (query.data?.revision || null) && (
            <p className="notice">
              A newer style was saved. Your changes are preserved; reload the
              saved style before applying a new revision.
            </p>
          )}
          <button
            disabled={
              action.busy || baseRevision !== (query.data?.revision || null)
            }
          >
            Save creator style
          </button>
          <button
            type="button"
            className="secondary"
            onClick={() => setDirty(false)}
          >
            Reload saved style
          </button>
          {message && (
            <p role="status" className="success">
              {message}
            </p>
          )}
        </form>
      )}
      <details>
        <summary>Suggest a style from your examples</summary>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            action.run(async () => {
              const queued = await post(
                "/me/style-profile/suggestions",
                {
                  examples: lines(form.get("examples")).map((text) => ({
                    text,
                  })),
                },
                true,
              );
              setJob(queued.id);
            });
          }}
        >
          <Field label="Up to five short examples (one per line)">
            <textarea name="examples" required maxLength={8000} />
          </Field>
          <button disabled={action.busy}>Analyze my examples</button>
        </form>
        <Job
          id={job}
          onDone={async () => {
            const result = await optionalFetch(
              `/me/style-profile/suggestions/${job}`,
            );
            if (result?.profile) setSuggestion(result);
          }}
        />
        {suggestion && (
          <div className="notice">
            <h3>Suggested profile</h3>
            <p>{suggestion.profile.voice}</p>
            <p>{suggestion.profile.pacing}</p>
            <p>{suggestion.profile.typical_structure}</p>
            <button
              type="button"
              className="secondary"
              onClick={() => {
                setProfile(suggestion.profile);
                setDirty(true);
                setMessage(
                  "Suggestion loaded for review. Save creator style to apply it.",
                );
              }}
            >
              Review this suggestion
            </button>
          </div>
        )}
      </details>
    </section>
  );
}

export function CampaignBrief({ root, query }) {
  const action = useAction(),
    [mode, setMode] = useState("personal"),
    [requirements, setRequirements] = useState([]),
    [message, setMessage] = useState(""),
    [dirty, setDirty] = useState(false),
    [base, setBase] = useState(null);
  useEffect(() => {
    if (!dirty) {
      setBase(query.data || null);
      setMode(query.data?.content_mode || "personal");
      setRequirements(query.data?.brand_brief?.requirements || []);
    }
  }, [query.data, dirty]);
  const brand = base?.brand_brief;
  return (
    <section className="form-section">
      <h2>Personal or brand collaboration</h2>
      <p className="muted">
        Saved campaign requirements are frozen into each generation. Required
        claims never come from an invented brief.
      </p>
      <Status query={query} error={action.error} />
      <form
        key={base?.revision || "new"}
        onChange={() => setDirty(true)}
        onSubmit={(event) => {
          event.preventDefault();
          const f = new FormData(event.currentTarget);
          action.run(async () => {
            const brief =
              mode === "brand"
                ? {
                    brand_name: f.get("brand_name"),
                    product_name: f.get("product_name"),
                    product_description: f.get("product_description"),
                    campaign_goal: f.get("campaign_goal"),
                    campaign_audience: f.get("campaign_audience"),
                    preferred_tone: f.get("preferred_tone") || null,
                    approved_claims: lines(f.get("approved_claims")),
                    forbidden_phrases: lines(f.get("forbidden_phrases")),
                    call_to_action: f.get("call_to_action") || null,
                    discount_code: f.get("discount_code") || null,
                    publishing_destination: f.get("publishing_destination"),
                    target_platforms: f.getAll("platform"),
                    requirements,
                  }
                : null;
            const saved = await put(root + "/campaign-brief", {
              base_revision: base?.revision || null,
              content_mode: mode,
              brand_brief: brief,
            });
            setBase(saved);
            setDirty(false);
            setMessage("Campaign context saved.");
          });
        }}
      >
        <Field label="Content mode">
          <select
            value={mode}
            onChange={(event) => setMode(event.target.value)}
          >
            <option value="personal">Personal content</option>
            <option value="brand">Brand collaboration</option>
          </select>
        </Field>
        {mode === "brand" && (
          <>
            <div className="columns">
              {[
                ["brand_name", "Brand name", 160],
                ["product_name", "Product name", 160],
              ].map(([key, label, max]) => (
                <Field label={label} key={key}>
                  <input
                    name={key}
                    defaultValue={brand?.[key] || ""}
                    required
                    maxLength={max}
                  />
                </Field>
              ))}
            </div>
            {[
              ["product_description", "Product description", 2000],
              ["campaign_goal", "Campaign goal", 500],
              ["campaign_audience", "Campaign audience", 500],
            ].map(([key, label, max]) => (
              <Field label={label} key={key}>
                <textarea
                  name={key}
                  defaultValue={brand?.[key] || ""}
                  required
                  maxLength={max}
                />
              </Field>
            ))}
            <div className="columns">
              <Field label="Preferred tone">
                <input
                  name="preferred_tone"
                  defaultValue={brand?.preferred_tone || ""}
                  maxLength={120}
                />
              </Field>
              <Field label="Publishing destination">
                <select
                  name="publishing_destination"
                  defaultValue={
                    brand?.publishing_destination || "creator_account"
                  }
                >
                  <option value="creator_account">Creator account</option>
                  <option value="brand_account">Brand account</option>
                </select>
              </Field>
            </div>
            <fieldset>
              <legend>Campaign platforms</legend>
              {["instagram", "tiktok", "youtube", "linkedin"].map(
                (platform) => (
                  <label className="check" key={platform}>
                    <input
                      name="platform"
                      value={platform}
                      type="checkbox"
                      defaultChecked={brand?.target_platforms?.includes(
                        platform,
                      )}
                    />
                    {platform}
                  </label>
                ),
              )}
            </fieldset>
            <Field label="Approved claims (one per line)">
              <textarea
                name="approved_claims"
                defaultValue={brand?.approved_claims?.join("\n") || ""}
              />
            </Field>
            <Field label="Forbidden phrases (one per line)">
              <textarea
                name="forbidden_phrases"
                defaultValue={brand?.forbidden_phrases?.join("\n") || ""}
              />
            </Field>
            <div className="columns">
              <Field label="Call to action">
                <input
                  name="call_to_action"
                  defaultValue={brand?.call_to_action || ""}
                  maxLength={500}
                />
              </Field>
              <Field label="Discount code">
                <input
                  name="discount_code"
                  defaultValue={brand?.discount_code || ""}
                  maxLength={80}
                />
              </Field>
            </div>
            <h3>Requirements</h3>
            {requirements.map((r, index) => (
              <div key={r.id}>
                <div className="columns">
                  <Field label={`Requirement ${index + 1}`}>
                    <input
                      value={r.description}
                      required
                      maxLength={1000}
                      onChange={(event) =>
                        setRequirements(
                          requirements.map((item, i) =>
                            i === index
                              ? { ...item, description: event.target.value }
                              : item,
                          ),
                        )
                      }
                    />
                  </Field>
                  <Field label="Requirement kind">
                    <select
                      value={r.kind}
                      onChange={(event) =>
                        setRequirements(
                          requirements.map((item, i) =>
                            i === index
                              ? {
                                  ...item,
                                  kind: event.target.value,
                                  literal_text:
                                    event.target.value === "literal"
                                      ? ""
                                      : null,
                                }
                              : item,
                          ),
                        )
                      }
                    >
                      <option value="talking_point">Talking point</option>
                      <option value="literal">Exact wording</option>
                    </select>
                  </Field>
                </div>
                {r.kind === "literal" && (
                  <Field label="Exact required wording">
                    <input
                      value={r.literal_text || ""}
                      required
                      maxLength={500}
                      onChange={(event) =>
                        setRequirements(
                          requirements.map((item, i) =>
                            i === index
                              ? { ...item, literal_text: event.target.value }
                              : item,
                          ),
                        )
                      }
                    />
                  </Field>
                )}
                <button
                  type="button"
                  className="secondary"
                  onClick={() =>
                    setRequirements(requirements.filter((_, i) => i !== index))
                  }
                >
                  Remove requirement {index + 1}
                </button>
              </div>
            ))}
            <button
              type="button"
              className="secondary"
              disabled={requirements.length >= 20}
              onClick={() =>
                setRequirements([
                  ...requirements,
                  {
                    id: crypto.randomUUID(),
                    kind: "talking_point",
                    description: "",
                    literal_text: null,
                  },
                ])
              }
            >
              Add requirement
            </button>
          </>
        )}
        {dirty &&
          (base?.revision || null) !== (query.data?.revision || null) && (
            <p className="notice">
              A newer campaign context exists. Your form has been preserved;
              reload saved context before applying a new revision.
            </p>
          )}
        <button
          disabled={
            action.busy ||
            (base?.revision || null) !== (query.data?.revision || null)
          }
        >
          Save campaign context
        </button>
        <button
          type="button"
          className="secondary"
          onClick={() => {
            setDirty(false);
            setBase(query.data || null);
          }}
        >
          Reload saved context
        </button>
        {message && (
          <p role="status" className="success">
            {message}
          </p>
        )}
      </form>
    </section>
  );
}
