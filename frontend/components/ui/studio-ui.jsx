"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Moon, Sun, UserCircle, X } from "@phosphor-icons/react";

export function Brand({ href = "/" }) {
  return <Link className="brand" href={href} aria-label="CreatorAI home">Creator<span>AI</span></Link>;
}
export function ThemeToggle() {
  const [dark, setDark] = useState(false);
  useEffect(() => { setDark(document.documentElement.dataset.theme === "dark"); }, []);
  return <button type="button" className="icon-button" aria-label={`Use ${dark ? "light" : "dark"} theme`} onClick={() => {
    const theme = dark ? "light" : "dark";
    document.documentElement.dataset.theme = theme;
    document.cookie = `creatorai-theme=${theme}; Path=/; Max-Age=31536000; SameSite=Lax`;
    setDark(!dark);
  }}>{dark ? <Sun size={21} weight="light" /> : <Moon size={21} weight="light" />}</button>;
}
export function Modal({ trigger, title, description, children, open, onOpenChange, className = "" }) {
  return <Dialog.Root open={open} onOpenChange={onOpenChange}>
    {trigger && <Dialog.Trigger asChild>{trigger}</Dialog.Trigger>}
    <Dialog.Portal><Dialog.Overlay className="dialog-overlay" /><Dialog.Content className={`dialog-content ${className}`}>
      <div className="dialog-heading"><Dialog.Title>{title}</Dialog.Title><Dialog.Close asChild><button className="icon-button" aria-label="Close dialog"><X size={22} weight="light" /></button></Dialog.Close></div>
      <Dialog.Description className="muted">{description}</Dialog.Description>{children}
    </Dialog.Content></Dialog.Portal>
  </Dialog.Root>;
}
export function SessionControl() {
  const [token, setToken] = useState("");
  const [open, setOpen] = useState(false);
  const cache = useQueryClient();
  return <Modal open={open} onOpenChange={setOpen} title="Creator session" description="Connect your configured identity provider, or use the backend's local demo identity when development mode is enabled." trigger={<button className="quiet-button"><UserCircle size={21} weight="light" />Creator session</button>}>
    <form onSubmit={(event) => {
      event.preventDefault();
      token.trim() ? sessionStorage.setItem("creatorai-token", token.trim()) : sessionStorage.removeItem("creatorai-token");
      Object.keys(sessionStorage).filter((key) => key.startsWith("creatorai-draft:")).forEach((key) => sessionStorage.removeItem(key));
      cache.clear(); setToken(""); setOpen(false);
    }}><label className="field"><span>Provider access token</span><input type="password" value={token} autoComplete="off" spellCheck="false" onChange={(event) => setToken(event.target.value)} /></label>
      <p className="muted">A production sign-in provider is not configured here. Tokens stay in this browser session; never paste API keys.</p>
      <button className="button">{token.trim() ? "Connect session" : "Use local demo session"}</button>
    </form>
  </Modal>;
}
export function PageHeader({ title, description, action }) {
  return <header className="page-heading"><div><h1>{title}</h1>{description && <p>{description}</p>}</div>{action}</header>;
}
export function Empty({ title, children, action }) {
  return <div className="empty-state"><h2>{title}</h2><p>{children}</p>{action}</div>;
}
export function ArrowLink({ href, children, className = "button" }) {
  return <Link href={href} className={className}>{children}<ArrowRight size={19} weight="light" /></Link>;
}
