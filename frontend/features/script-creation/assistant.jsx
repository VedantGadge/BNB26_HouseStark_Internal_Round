"use client";
import { useEffect, useState } from "react";
import { post } from "@/lib/api";
import { spokenScript, humanize } from "@/lib/creator.mjs";
import {
  Field,
  Job,
  Status,
  useAction,
  useApi,
} from "@/components/workflow/common";

function Proposal({ proposal, root, latest, dirty, onApplied }) {
  const action = useAction(),
    [ack, setAck] = useState([]);
  const eligible =
    proposal.status === "pending" &&
    proposal.base_version === latest.version &&
    !dirty;
  return (
    <article className="proposal">
      <h3>{humanize(proposal.status)} proposal</h3>
      <p>{proposal.explanation}</p>
      <Status error={action.error} />
      {proposal.changes.map((change, index) => (
        <div key={index} className="proposal-diff">
          <div>
            <strong>Before</strong>
            <p>{change.before || "Full saved script"}</p>
          </div>
          <div>
            <strong>After · proposed</strong>
            <p>
              {change.after ||
                (change.content_after
                  ? spokenScript(change.content_after)
                  : "")}
            </p>
            {change.content_after && (
              <details>
                <summary>Proposed supporting copy</summary>
                <p>{change.content_after.title}</p>
                <p>{change.content_after.description}</p>
              </details>
            )}
          </div>
        </div>
      ))}
      {proposal.requirement_checks.map((check) => (
        <p
          key={check.requirement_id}
          className={check.status === "satisfied" ? "muted" : "error"}
        >
          {check.status}: {check.message || check.requirement_id}
        </p>
      ))}
      {proposal.warning_ids.map((id) => (
        <label className="check" key={id}>
          <input
            type="checkbox"
            checked={ack.includes(id)}
            onChange={(event) =>
              setAck(
                event.target.checked
                  ? [...ack, id]
                  : ack.filter((value) => value !== id),
              )
            }
          />
          I reviewed warning: {id}
        </label>
      ))}
      {proposal.status === "pending" && (
        <>
          <button
            disabled={
              !eligible ||
              action.busy ||
              proposal.warning_ids.some((id) => !ack.includes(id))
            }
            onClick={() =>
              action.run(async () => {
                const result = await post(
                  `${root}/assistant/proposals/${proposal.id}/apply`,
                  { acknowledged_warning_ids: ack },
                );
                onApplied(result);
              })
            }
          >
            Apply proposal
          </button>
          <button
            className="secondary"
            disabled={action.busy}
            onClick={() =>
              action.run(() =>
                post(`${root}/assistant/proposals/${proposal.id}/discard`, {}),
              )
            }
          >
            Discard proposal
          </button>
          {!eligible && (
            <p className="muted">
              {dirty
                ? "Save or revert your draft before applying this proposal."
                : "This proposal targets an older version. Request a new proposal for the current script."}
            </p>
          )}
        </>
      )}
    </article>
  );
}

export function Assistant({ root, latest, dirty, onApplied }) {
  const action = useAction(),
    [conversationId, setConversationId] = useState(null),
    [job, setJob] = useState(null),
    [scope, setScope] = useState("script");
  const conversation = useApi(
    conversationId ? `${root}/assistant/conversations/${conversationId}` : null,
  );
  const key = `creatorai-assistant:${root}`;
  useEffect(() => {
    try {
      const saved = JSON.parse(sessionStorage.getItem(key));
      setConversationId(saved?.conversation || null);
      setJob(saved?.job || null);
    } catch {}
  }, [key]);
  return (
    <section className="form-section">
      <h2>Refine this script</h2>
      <p className="muted">
        Ask for a change. Review the proposal before it creates a new saved
        version.
      </p>
      <Status error={action.error} />
      {dirty && (
        <p className="notice">
          Your unsaved draft stays here. Save or revert it before asking the
          assistant to revise the saved script.
        </p>
      )}
      <form
        onSubmit={(event) => {
          event.preventDefault();
          const form = new FormData(event.currentTarget);
          const [target_scope, target_id] = scope.split(":");
          action.run(async () => {
            const queued = await post(
              root + "/assistant/messages",
              {
                base_version: latest.version,
                message: form.get("message"),
                target_scope,
                ...(target_id ? { target_id } : {}),
                conversation_id: conversationId,
              },
              true,
            );
            setJob(queued.id);
            setConversationId(queued.conversation_id);
            sessionStorage.setItem(
              key,
              JSON.stringify({
                conversation: queued.conversation_id,
                job: queued.id,
              }),
            );
          });
        }}
      >
        <Field label="Revision scope">
          <select
            value={scope}
            onChange={(event) => setScope(event.target.value)}
          >
            <option value="script">Full script</option>
            <option value="cta">Call to action</option>
            <option value="supporting_copy">Supporting copy</option>
            {latest.content.hooks.map((hook, index) => (
              <option key={hook.id} value={`hook:${hook.id}`}>
                Hook {index + 1}
              </option>
            ))}
            {latest.content.sections.map((section) => (
              <option key={section.id} value={`section:${section.id}`}>
                {section.heading}
              </option>
            ))}
          </select>
        </Field>
        <Field label="What would you like to change?">
          <textarea
            name="message"
            required
            maxLength={2000}
            placeholder="Make the selected hook more specific, keeping my voice."
          />
        </Field>
        <button disabled={action.busy || dirty}>Request a proposal</button>
      </form>
      <Job id={job} onDone={() => conversation.refetch()} />
      {conversationId && (
        <>
          <Status query={conversation} />
          {conversation.data?.messages.length > 0 && (
            <details>
              <summary>Conversation history</summary>
              {conversation.data.messages.map((message) => (
                <p key={message.id}>
                  <strong>{humanize(message.role)}:</strong> {message.content}
                </p>
              ))}
            </details>
          )}
          {conversation.data?.proposals.map((proposal) => (
            <Proposal
              key={proposal.id}
              proposal={proposal}
              root={root}
              latest={latest}
              dirty={dirty}
              onApplied={onApplied}
            />
          ))}
        </>
      )}
    </section>
  );
}
