"use client";

import React from "react";

// ---------------------------------------------------------------------------
// Card
// ---------------------------------------------------------------------------

export function Card({
  children,
  className = "",
  padded = true,
}: {
  children: React.ReactNode;
  className?: string;
  padded?: boolean;
}) {
  return (
    <div
      className={`rounded-xl border border-border bg-card shadow-sm ${
        padded ? "p-5" : ""
      } ${className}`}
    >
      {children}
    </div>
  );
}

export function CardHeader({
  title,
  subtitle,
  action,
}: {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div className="mb-4 flex items-start justify-between gap-4">
      <div>
        <h2 className="text-base font-semibold text-foreground">{title}</h2>
        {subtitle ? (
          <p className="mt-0.5 text-sm text-muted">{subtitle}</p>
        ) : null}
      </div>
      {action}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Button
// ---------------------------------------------------------------------------

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "success";
type ButtonSize = "sm" | "md";

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "bg-primary text-white hover:bg-primary-hover border border-transparent shadow-sm",
  secondary:
    "bg-card text-foreground border border-border hover:bg-background",
  ghost:
    "bg-transparent text-foreground border border-transparent hover:bg-background",
  danger:
    "bg-danger text-white hover:opacity-90 border border-transparent shadow-sm",
  success:
    "bg-success text-white hover:opacity-90 border border-transparent shadow-sm",
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: "px-3 py-1.5 text-xs",
  md: "px-4 py-2 text-sm",
};

export function Button({
  children,
  variant = "primary",
  size = "md",
  className = "",
  loading = false,
  disabled,
  ...props
}: {
  children: React.ReactNode;
  variant?: ButtonVariant;
  size?: ButtonSize;
  className?: string;
  loading?: boolean;
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...props}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
    >
      {loading ? (
        <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/40 border-t-white" />
      ) : null}
      {children}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Badge
// ---------------------------------------------------------------------------

type BadgeTone = "neutral" | "primary" | "success" | "warning" | "danger";

const badgeTones: Record<BadgeTone, string> = {
  neutral: "bg-background text-muted border-border",
  primary: "bg-primary/10 text-primary border-primary/20",
  success: "bg-success/10 text-success border-success/20",
  warning: "bg-warning/10 text-warning border-warning/20",
  danger: "bg-danger/10 text-danger border-danger/20",
};

export function Badge({
  children,
  tone = "neutral",
  className = "",
}: {
  children: React.ReactNode;
  tone?: BadgeTone;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium ${badgeTones[tone]} ${className}`}
    >
      {children}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Stat card
// ---------------------------------------------------------------------------

export function StatCard({
  label,
  value,
  hint,
  accent = "text-foreground",
}: {
  label: string;
  value: React.ReactNode;
  hint?: React.ReactNode;
  accent?: string;
}) {
  return (
    <Card>
      <p className="text-sm font-medium text-muted">{label}</p>
      <p className={`mt-1 text-3xl font-bold leading-none ${accent}`}>{value}</p>
      {hint ? <p className="mt-2 text-xs text-muted">{hint}</p> : null}
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Inputs
// ---------------------------------------------------------------------------

const fieldClass =
  "w-full rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground placeholder:text-muted focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20";

export function Input({
  label,
  className = "",
  ...props
}: { label?: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="block">
      {label ? (
        <span className="mb-1 block text-xs font-medium text-muted">
          {label}
        </span>
      ) : null}
      <input {...props} className={`${fieldClass} ${className}`} />
    </label>
  );
}

export function Textarea({
  label,
  className = "",
  ...props
}: { label?: string } & React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <label className="block">
      {label ? (
        <span className="mb-1 block text-xs font-medium text-muted">
          {label}
        </span>
      ) : null}
      <textarea {...props} className={`${fieldClass} ${className}`} />
    </label>
  );
}

export function Select({
  label,
  children,
  className = "",
  ...props
}: { label?: string } & React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <label className="block">
      {label ? (
        <span className="mb-1 block text-xs font-medium text-muted">
          {label}
        </span>
      ) : null}
      <select {...props} className={`${fieldClass} ${className}`}>
        {children}
      </select>
    </label>
  );
}

// ---------------------------------------------------------------------------
// Feedback
// ---------------------------------------------------------------------------

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-10 text-sm text-muted">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-border border-t-primary" />
      {label || "Loading…"}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-card/50 px-6 py-12 text-center">
      <p className="text-sm font-semibold text-foreground">{title}</p>
      {description ? (
        <p className="mt-1 max-w-md text-sm text-muted">{description}</p>
      ) : null}
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}

export function ErrorText({ children }: { children: React.ReactNode }) {
  if (!children) return null;
  return (
    <p className="rounded-lg border border-danger/20 bg-danger/5 px-3 py-2 text-sm text-danger">
      {children}
    </p>
  );
}

// ---------------------------------------------------------------------------
// Status badges
// ---------------------------------------------------------------------------

const applicationTones: Record<string, BadgeTone> = {
  Discovered: "neutral",
  Matched: "primary",
  Approved: "warning",
  Applied: "success",
  Rejected: "danger",
};

export function ApplicationStatusBadge({ status }: { status: string }) {
  return <Badge tone={applicationTones[status] || "neutral"}>{status}</Badge>;
}

const docTones: Record<string, BadgeTone> = {
  draft: "neutral",
  approved: "success",
  rejected: "danger",
};

export function DocumentStatusBadge({ status }: { status: string }) {
  return <Badge tone={docTones[status] || "neutral"}>{status}</Badge>;
}

export function ScoreBadge({ score }: { score: number | null | undefined }) {
  if (score === null || score === undefined) return <Badge>n/a</Badge>;
  const tone: BadgeTone =
    score >= 80 ? "success" : score >= 60 ? "warning" : "danger";
  return <Badge tone={tone}>{score.toFixed(0)}</Badge>;
}
