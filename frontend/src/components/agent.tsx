"use client";

import Link from "next/link";
import type { EvaluationResult } from "@/lib/types";
import type {
  ActionItem,
  ParsedIntent,
  TimelineEvent,
  TimelineStage,
} from "@/lib/agent";
import { relativeTime } from "@/lib/agent";
import { Badge, Card, CardHeader } from "./ui";
import { IconSearch, IconSpark } from "./icons";

// ---------------------------------------------------------------------------
// Agent avatar / presence
// ---------------------------------------------------------------------------

export function AgentAvatar({
  size = 40,
  active = false,
}: {
  size?: number;
  active?: boolean;
}) {
  return (
    <div
      className="relative flex items-center justify-center rounded-full bg-primary/10"
      style={{ width: size, height: size }}
    >
      <span
        className={`absolute inset-0 rounded-full bg-primary/20 ${
          active ? "animate-ping" : ""
        }`}
        style={{ animationDuration: "2.5s" }}
      />
      <span
        className="relative flex items-center justify-center rounded-full bg-primary text-white"
        style={{ width: size * 0.66, height: size * 0.66 }}
      >
        <IconSpark size={size * 0.4} />
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Fit ring
// ---------------------------------------------------------------------------

export function FitRing({
  score,
  size = 88,
  label,
}: {
  score: number | null | undefined;
  size?: number;
  label?: string;
}) {
  const value = score ?? 0;
  const stroke = 7;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const offset = c - (value / 100) * c;
  const color =
    value >= 70 ? "#059669" : value >= 45 ? "#D97706" : "#DC2626";

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke="#E2E8F0"
            strokeWidth={stroke}
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke={color}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={c}
            strokeDashoffset={offset}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-xl font-bold" style={{ color }}>
            {score === null || score === undefined ? "—" : Math.round(value)}
          </span>
          {label ? (
            <span className="text-[10px] uppercase text-muted">{label}</span>
          ) : null}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Match breakdown (explainable job intelligence)
// ---------------------------------------------------------------------------

function CategoryBar({
  label,
  value,
}: {
  label: string;
  value: number | null | undefined;
}) {
  const v = value ?? 0;
  const color =
    v >= 70 ? "bg-success" : v >= 45 ? "bg-warning" : "bg-danger";
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs">
        <span className="text-muted">{label}</span>
        <span className="font-medium text-foreground">
          {value === null || value === undefined ? "—" : `${Math.round(v)}%`}
        </span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-background">
        <div className={`h-full ${color}`} style={{ width: `${v}%` }} />
      </div>
    </div>
  );
}

const recommendationTone = (r: string | null | undefined) =>
  r === "APPLY" ? "success" : r === "REJECT" ? "danger" : "warning";

export function MatchBreakdown({
  evaluation,
  jobTitle,
}: {
  evaluation: EvaluationResult;
  jobTitle?: string;
}) {
  const roleScore =
    evaluation.role_match?.status === "EXACT_MATCH"
      ? 100
      : evaluation.role_match?.status === "RELATED_MATCH"
        ? 75
        : evaluation.role_match?.status === "UNCERTAIN"
          ? 50
          : 0;
  const eligibilityScore =
    evaluation.eligibility?.status === "ELIGIBLE"
      ? 100
      : evaluation.eligibility?.status === "UNCERTAIN"
        ? 50
        : 0;

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-5">
        <FitRing score={evaluation.fit_score} label="fit" />
        <div className="space-y-2">
          <div className="flex flex-wrap gap-2">
            <Badge tone="primary">{evaluation.priority || "—"}</Badge>
            <Badge tone={recommendationTone(evaluation.recommendation)}>
              {evaluation.recommendation || "—"}
            </Badge>
          </div>
          <p className="text-xs text-muted">
            {evaluation.role_match
              ? `Role: ${evaluation.role_match.status.replace("_", " ").toLowerCase()}`
              : ""}
            {evaluation.role_match && evaluation.eligibility ? " · " : ""}
            {evaluation.eligibility
              ? `Eligibility: ${evaluation.eligibility.status.toLowerCase()}`
              : ""}
          </p>
        </div>
      </div>

      <div className="space-y-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted">
          Match signals
        </p>
        <CategoryBar label="Technical skills" value={evaluation.technical_match} />
        <CategoryBar label="Role alignment" value={roleScore} />
        <CategoryBar label="Eligibility" value={eligibilityScore} />
        <CategoryBar label="Evidence quality" value={evaluation.evidence_quality} />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-success">
            Why you
          </p>
          <div className="flex flex-wrap gap-1.5">
            {evaluation.matched_skills.length === 0 ? (
              <span className="text-xs text-muted">No verified matches yet</span>
            ) : (
              evaluation.matched_skills.map((s, i) => (
                <Badge key={i} tone="success">
                  {s.skill}
                </Badge>
              ))
            )}
          </div>
          {evaluation.strengths.length > 0 ? (
            <ul className="mt-2 space-y-1 text-xs text-muted">
              {evaluation.strengths.map((s, i) => (
                <li key={i}>• {s}</li>
              ))}
            </ul>
          ) : null}
        </div>

        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-danger">
            Gaps
          </p>
          <div className="flex flex-wrap gap-1.5">
            {evaluation.missing_skills.length === 0 ? (
              <span className="text-xs text-muted">No critical gaps</span>
            ) : (
              evaluation.missing_skills.map((s, i) => (
                <Badge key={i} tone="danger">
                  {s.skill}
                </Badge>
              ))
            )}
            {evaluation.partial_skills.map((s, i) => (
              <Badge key={`p-${i}`} tone="warning">
                {s.skill}
              </Badge>
            ))}
          </div>
          {evaluation.gaps.length > 0 ? (
            <ul className="mt-2 space-y-1 text-xs text-muted">
              {evaluation.gaps.map((g, i) => (
                <li key={i}>• {g}</li>
              ))}
            </ul>
          ) : null}
        </div>
      </div>

      {evaluation.risks.length > 0 ? (
        <div className="rounded-lg border border-warning/20 bg-warning/5 p-3">
          <p className="mb-1 text-xs font-semibold uppercase text-warning">
            Risks
          </p>
          <ul className="space-y-1 text-xs text-muted">
            {evaluation.risks.map((r, i) => (
              <li key={i}>• {r}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {jobTitle ? (
        <p className="text-[11px] text-muted">
          Analysis for <span className="font-medium">{jobTitle}</span>. Every
          signal traces to evidence in your Candidate KB.
        </p>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Action center
// ---------------------------------------------------------------------------

export function ActionCenter({ items }: { items: ActionItem[] }) {
  return (
    <Card>
      <CardHeader
        title="Action Center"
        subtitle="What the agent needs from you next"
      />
      {items.length === 0 ? (
        <p className="text-sm text-muted">
          You&apos;re all caught up. The agent will surface new actions as it
          works.
        </p>
      ) : (
        <ul className="space-y-2">
          {items.map((item) => (
            <li key={item.id}>
              <Link
                href={item.href}
                className="flex items-start gap-3 rounded-lg border border-border p-3 transition-colors hover:border-primary/40 hover:bg-background"
              >
                <span className="mt-0.5 flex h-6 w-6 flex-none items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                  {item.count}
                </span>
                <div className="min-w-0">
                  <p className="text-sm font-medium text-foreground">
                    {item.title}
                  </p>
                  <p className="text-xs text-muted">{item.detail}</p>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Activity timeline
// ---------------------------------------------------------------------------

const stageStyle: Record<
  TimelineStage,
  { dot: string; label: string }
> = {
  discovered: { dot: "bg-secondary", label: "Discovery" },
  match: { dot: "bg-primary", label: "Matching" },
  document: { dot: "bg-warning", label: "Documents" },
  approval: { dot: "bg-success", label: "Approval" },
  application: { dot: "bg-success", label: "Application" },
  error: { dot: "bg-danger", label: "Rejected" },
};

export function ActivityTimeline({ events }: { events: TimelineEvent[] }) {
  if (events.length === 0) {
    return (
      <p className="text-sm text-muted">
        No agent activity yet. Once discovery and matching run, their steps will
        appear here.
      </p>
    );
  }
  return (
    <ol className="relative space-y-4 border-l border-border pl-6">
      {events.map((e) => {
        const style = stageStyle[e.stage];
        return (
          <li key={e.id} className="relative">
            <span
              className={`absolute -left-[27px] mt-1 h-3 w-3 rounded-full ${style.dot} ring-4 ring-card`}
            />
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-medium text-foreground">
                {e.title}
              </span>
              <Badge tone="neutral">{style.label}</Badge>
              <span className="text-xs text-muted">{relativeTime(e.at)}</span>
            </div>
            {e.detail ? (
              <p className="text-xs text-muted">{e.detail}</p>
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}

// ---------------------------------------------------------------------------
// Natural-language intent composer
// ---------------------------------------------------------------------------

export function IntentComposer({
  value,
  onChange,
  onSubmit,
  intent,
  loading,
}: {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  intent: ParsedIntent | null;
  loading?: boolean;
}) {
  const examples = [
    "AI Engineer roles in UAE with strong Python/LLM fit",
    "Remote ML Engineer with PyTorch",
    "Data Scientist in London",
  ];
  return (
    <Card>
      <div className="mb-2 flex items-center gap-2">
        <AgentAvatar size={28} active={loading} />
        <p className="text-sm font-medium text-foreground">
          Ask the agent in plain language
        </p>
      </div>
      <div className="flex flex-col gap-2 sm:flex-row">
        <div className="relative flex-1">
          <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted">
            <IconSearch size={16} />
          </span>
          <input
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") onSubmit();
            }}
            placeholder="Find me AI Engineer roles in UAE with strong Python/LLM fit"
            className="w-full rounded-lg border border-border bg-card py-2 pl-9 pr-3 text-sm text-foreground placeholder:text-muted focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>
        <button
          onClick={onSubmit}
          disabled={loading}
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-hover disabled:opacity-50"
        >
          {loading ? "Thinking…" : "Ask agent"}
        </button>
      </div>

      {intent &&
      (intent.roles.length ||
        intent.locations.length ||
        intent.skills.length ||
        intent.workMode) ? (
        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          <span className="text-xs text-muted">Understood:</span>
          {intent.roles.map((r) => (
            <Badge key={r} tone="primary">
              role: {r}
            </Badge>
          ))}
          {intent.locations.map((l) => (
            <Badge key={l} tone="neutral">
              location: {l}
            </Badge>
          ))}
          {intent.workMode ? (
            <Badge tone="neutral">mode: {intent.workMode}</Badge>
          ) : null}
          {intent.skills.slice(0, 5).map((s) => (
            <Badge key={s} tone="success">
              {s}
            </Badge>
          ))}
        </div>
      ) : (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {examples.map((ex) => (
            <button
              key={ex}
              onClick={() => onChange(ex)}
              className="rounded-full border border-border px-2.5 py-0.5 text-xs text-muted transition-colors hover:text-foreground"
            >
              {ex}
            </button>
          ))}
        </div>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Guided workflow stepper
// ---------------------------------------------------------------------------

export function Stepper({
  steps,
  current,
}: {
  steps: { key: string; label: string }[];
  current: number;
}) {
  return (
    <ol className="flex flex-wrap items-center gap-2">
      {steps.map((s, i) => {
        const done = i < current;
        const active = i === current;
        return (
          <li key={s.key} className="flex items-center gap-2">
            <span
              className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-semibold ${
                done
                  ? "bg-success text-white"
                  : active
                    ? "bg-primary text-white"
                    : "border border-border text-muted"
              }`}
            >
              {done ? "✓" : i + 1}
            </span>
            <span
              className={`text-xs font-medium ${
                active ? "text-foreground" : "text-muted"
              }`}
            >
              {s.label}
            </span>
            {i < steps.length - 1 ? (
              <span className="mx-1 h-px w-6 bg-border" />
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}
