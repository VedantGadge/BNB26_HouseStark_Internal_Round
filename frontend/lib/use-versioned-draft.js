"use client";
import { useEffect, useState } from "react";
import { same } from "./creator.mjs";

/** Never replace a dirty buffer when polling discovers a newer saved version. */
export function useVersionedDraft(latest, field, storageKey) {
  const [base, setBase] = useState(null);
  const [draft, setDraft] = useState(null);
  const [restored, setRestored] = useState(false);
  const dirty = Boolean(base && draft && !same(base[field], draft));
  useEffect(() => {
    if (!latest) return;
    if (!base) {
      try {
        const stored = JSON.parse(sessionStorage.getItem(storageKey));
        if (stored?.base?.id && stored?.draft) { setBase(stored.base); setDraft(stored.draft); setRestored(true); return; }
      } catch { /* A corrupt or unavailable browser cache never replaces saved data. */ }
      setBase(latest); setDraft(structuredClone(latest[field]));
    } else if (latest.id !== base.id && !dirty) {
      setBase(latest); setDraft(structuredClone(latest[field]));
    }
  }, [latest, base, dirty, field, storageKey]);
  useEffect(() => {
    if (!base) return;
    try { dirty ? sessionStorage.setItem(storageKey, JSON.stringify({ base, draft })) : sessionStorage.removeItem(storageKey); }
    catch { /* Keep the live draft even if browser storage is unavailable. */ }
  }, [base, draft, dirty, storageKey]);
  useEffect(() => {
    if (!dirty) return;
    const warn = (event) => { event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);
  function reset(version = latest) {
    if (!version) return;
    setBase(version); setDraft(structuredClone(version[field])); setRestored(false);
  }
  return { base, draft, setDraft, dirty, restored, reset, stale: Boolean(base && latest && latest.id !== base.id) };
}
