"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Field } from "@/components/workflow/common";

export function TrendPicker({ root, selected, onSelect }) {
  const [country, setCountry] = useState("IN");
  const [focus, setFocus] = useState("");
  const path = `${root}/trends?${new URLSearchParams({ country, focus })}`;
  const query = useQuery({
    queryKey: [path],
    queryFn: () => apiFetch(path),
    enabled: false,
    retry: false,
  });
  const findTrends = () => {
    onSelect(null);
    query.refetch();
  };

  return (
    <details className="trend-picker">
      <summary>Recent trends · optional</summary>
      <p className="muted">
        Find Google searches that share terms with your saved brief. Choose a
        topic only when it fits your story.
      </p>
      <Field label="Trend region">
        <select
          value={country}
          disabled={query.isFetching}
          onChange={(event) => {
            setCountry(event.target.value);
            onSelect(null);
          }}
        >
          {[
            ["IN", "India"],
            ["US", "United States"],
            ["GB", "United Kingdom"],
            ["CA", "Canada"],
            ["AU", "Australia"],
          ].map(([code, label]) => (
            <option key={code} value={code}>
              {label}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Focus topics (optional)">
        <input
          value={focus}
          maxLength={200}
          placeholder="e.g. smartphones, cooking, cricket"
          disabled={query.isFetching}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              findTrends();
            }
          }}
          onChange={(event) => {
            setFocus(event.target.value);
            onSelect(null);
          }}
        />
      </Field>
      <button
        type="button"
        className="secondary"
        disabled={query.isFetching}
        onClick={findTrends}
      >
        {query.isFetching ? "Finding trends…" : "Find relevant trends"}
      </button>
      {query.isFetching && <p role="status">Checking Google Trends…</p>}
      {query.isError && (
        <p role="alert" className="notice error">
          {query.error.message} You can still generate without a trend.
        </p>
      )}
      {query.data && !query.isFetching && !query.isError && (
        <>
          <p className="muted">
            Past {query.data.lookback_hours} hours · fetched{" "}
            {new Date(query.data.fetched_at).toLocaleString()}
          </p>
          {query.data.topics.length === 0 && (
            <p role="status">
              No recent trends share terms with this brief. Try specific focus
              topics, or generate from your brief.
            </p>
          )}
          {query.data.topics.map((topic) => (
            <article className="trend-topic" key={topic.id}>
              <label className="check">
                <input
                  type="checkbox"
                  checked={selected?.topic_id === topic.id}
                  onChange={(event) =>
                    onSelect(
                      event.target.checked
                        ? { country: topic.country, topic_id: topic.id }
                        : null,
                    )
                  }
                />
                {topic.title}
              </label>
              <p className="muted">{topic.relevance_reason}</p>
              <p className="muted">
                Started {new Date(topic.published_at).toLocaleString()}
                {topic.approximate_traffic &&
                  ` · approx. ${topic.approximate_traffic} searches`}
              </p>
              <a href={topic.source_url} target="_blank" rel="noreferrer">
                Google Trends
              </a>
              {topic.articles[0] && (
                <p>
                  <a
                    href={topic.articles[0].url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {topic.articles[0].title}
                  </a>
                </p>
              )}
            </article>
          ))}
        </>
      )}
      {selected && (
        <p role="status">
          One topic selected. The script will use it only if it fits your brief.{" "}
          <button
            type="button"
            className="secondary"
            onClick={() => onSelect(null)}
          >
            Clear trend
          </button>
        </p>
      )}
    </details>
  );
}
