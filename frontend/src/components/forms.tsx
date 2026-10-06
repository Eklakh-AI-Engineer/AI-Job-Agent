"use client";

import { useRef, useState } from "react";

// ---------------------------------------------------------------------------
// ChipInput — type + Enter/comma to add, chips are removable
// ---------------------------------------------------------------------------

export function ChipInput({
  label,
  value,
  onChange,
  placeholder,
  suggestions = [],
  idPrefix = "chip",
}: {
  label?: string;
  value: string[];
  onChange: (next: string[]) => void;
  placeholder?: string;
  suggestions?: readonly string[];
  idPrefix?: string;
}) {
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  function add(raw: string) {
    const parts = raw
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    if (parts.length === 0) return;
    const next = [...value];
    let added = false;
    for (const p of parts) {
      if (!next.some((v) => v.toLowerCase() === p.toLowerCase())) {
        next.push(p);
        added = true;
      }
    }
    if (added) {
      onChange(next);
      setDraft("");
      setError("");
    } else {
      setError("Already added.");
      setDraft("");
    }
  }

  function remove(index: number) {
    onChange(value.filter((_, i) => i !== index));
  }

  const availableSuggestions = suggestions.filter(
    (s) => !value.some((v) => v.toLowerCase() === s.toLowerCase()),
  );

  return (
    <div>
      {label ? (
        <span className="mb-1 block text-xs font-medium text-muted">{label}</span>
      ) : null}
      <div
        className="flex flex-wrap items-center gap-2 rounded-lg border border-border bg-card px-2 py-2 focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/20"
        onClick={() => inputRef.current?.focus()}
      >
        {value.map((chip, i) => (
          <span
            key={`${idPrefix}-${chip}-${i}`}
            className="inline-flex items-center gap-1 rounded-full border border-primary/20 bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-primary"
          >
            {chip}
            <button
              type="button"
              aria-label={`Remove ${chip}`}
              onClick={(e) => {
                e.stopPropagation();
                remove(i);
              }}
              className="text-primary/70 hover:text-primary"
            >
              ×
            </button>
          </span>
        ))}
        <input
          ref={inputRef}
          value={draft}
          onChange={(e) => {
            setDraft(e.target.value);
            if (error) setError("");
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === ",") {
              e.preventDefault();
              add(draft);
            } else if (e.key === "Backspace" && draft === "" && value.length) {
              remove(value.length - 1);
            }
          }}
          onBlur={() => {
            if (draft.trim()) add(draft);
          }}
          placeholder={value.length === 0 ? placeholder : ""}
          className="min-w-[8rem] flex-1 bg-transparent px-1 py-0.5 text-sm text-foreground placeholder:text-muted focus:outline-none"
        />
      </div>
      {error ? <p className="mt-1 text-xs text-danger">{error}</p> : null}
      {availableSuggestions.length > 0 ? (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {availableSuggestions.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => add(s)}
              className="rounded-full border border-border px-2.5 py-0.5 text-xs text-muted transition-colors hover:border-primary/40 hover:text-foreground"
            >
              + {s}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section — a titled block with a description and optional action
// ---------------------------------------------------------------------------

export function Section({
  title,
  description,
  action,
  children,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-xl border border-border bg-card p-5 shadow-sm">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-foreground">{title}</h2>
          {description ? (
            <p className="mt-0.5 text-sm text-muted">{description}</p>
          ) : null}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

// ---------------------------------------------------------------------------
// RepeatCard — a bordered, removable card for repeatable entries
// ---------------------------------------------------------------------------

export function RepeatCard({
  title,
  onRemove,
  children,
  index,
}: {
  title: string;
  onRemove: () => void;
  children: React.ReactNode;
  index?: number;
}) {
  return (
    <div className="rounded-lg border border-border bg-background/60 p-4">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted">
          {title}
          {index !== undefined ? ` ${index + 1}` : ""}
        </span>
        <button
          type="button"
          onClick={onRemove}
          className="rounded-md px-2 py-1 text-xs font-medium text-muted transition-colors hover:bg-danger/10 hover:text-danger"
        >
          Remove
        </button>
      </div>
      {children}
    </div>
  );
}

// ---------------------------------------------------------------------------
// FieldError — inline validation message
// ---------------------------------------------------------------------------

export function FieldError({ children }: { children?: React.ReactNode }) {
  if (!children) return null;
  return <p className="mt-1 text-xs text-danger">{children}</p>;
}
