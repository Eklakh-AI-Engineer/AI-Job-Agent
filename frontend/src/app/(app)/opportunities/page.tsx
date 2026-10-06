"use client";

import { useMemo, useState } from "react";
import { applicationsApi, evaluationApi, searchApi } from "@/lib/api";
import type { EvaluationResult, JobPosting } from "@/lib/types";
import {
  applyIntent,
  parseIntent,
  preScoreFit,
  type FitBucket,
  type ParsedIntent,
} from "@/lib/agent";
import { useAgentData } from "@/lib/useAgentData";
import { TopBar } from "@/components/TopBar";
import {
  FitRing,
  IntentComposer,
  MatchBreakdown,
} from "@/components/agent";
import {
  Badge,
  Button,
  Card,
  CardHeader,
  EmptyState,
  ErrorText,
  Spinner,
} from "@/components/ui";

const BUCKETS: { key: FitBucket | "all"; label: string }[] = [
  { key: "recommended", label: "Recommended" },
  { key: "review", label: "Worth reviewing" },
  { key: "low", label: "Low fit" },
  { key: "all", label: "All" },
];

export default function OpportunitiesPage() {
  const data = useAgentData();
  const { candidateSkills, loading, error, refresh } = data;

  const [feed, setFeed] = useState<JobPosting[] | null>(null);
  const [intentText, setIntentText] = useState("");
  const [intent, setIntent] = useState<ParsedIntent | null>(null);
  const [searching, setSearching] = useState(false);
  const [bucket, setBucket] = useState<FitBucket | "all">("recommended");

  const [selected, setSelected] = useState<JobPosting | null>(null);
  const [evaluation, setEvaluation] = useState<EvaluationResult | null>(null);
  const [evaluating, setEvaluating] = useState(false);
  const [notice, setNotice] = useState("");
  const [actionError, setActionError] = useState("");

  const source = feed ?? data.jobs;

  const scored = useMemo(() => {
    return source
      .map((job) => ({ job, fit: preScoreFit(job, candidateSkills) }))
      .sort((a, b) => b.fit.score - a.fit.score);
  }, [source, candidateSkills]);

  const filtered = useMemo(() => {
    if (bucket === "all") return scored;
    return scored.filter((s) => s.fit.bucket === bucket);
  }, [scored, bucket]);

  const counts = useMemo(() => {
    return {
      recommended: scored.filter((s) => s.fit.bucket === "recommended").length,
      review: scored.filter((s) => s.fit.bucket === "review").length,
      low: scored.filter((s) => s.fit.bucket === "low").length,
      all: scored.length,
    };
  }, [scored]);

  async function askAgent() {
    const parsed = parseIntent(intentText);
    setIntent(parsed);
    setSearching(true);
    setActionError("");
    setNotice("");
    try {
      let results: JobPosting[] = data.jobs;
      if (parsed.raw) {
        const res = await searchApi.hybrid(parsed.raw, { limit: 100 });
        results = res.items.length > 0 ? res.items : data.jobs;
      }
      const scoped = applyIntent(results, parsed);
      setFeed(scoped.length > 0 ? scoped : results);
      setBucket("all");
    } catch (err) {
      setActionError((err as Error).message);
    } finally {
      setSearching(false);
    }
  }

  function clearIntent() {
    setFeed(null);
    setIntent(null);
    setIntentText("");
    setBucket("recommended");
  }

  async function analyze(job: JobPosting) {
    setSelected(job);
    setEvaluation(null);
    setEvaluating(true);
    setActionError("");
    try {
      const result = await evaluationApi.evaluate(job.id);
      setEvaluation(result);
    } catch (err) {
      setActionError((err as Error).message);
    } finally {
      setEvaluating(false);
    }
  }

  async function track(job: JobPosting) {
    setActionError("");
    setNotice("");
    try {
      await applicationsApi.create(job.id);
      setNotice(`Added "${job.title}" to your pipeline.`);
      await refresh();
    } catch (err) {
      setActionError((err as Error).message);
    }
  }

  const trackedIds = new Set(data.applications.map((a) => a.job_posting_id));

  return (
    <div>
      <TopBar
        title="Opportunities"
        subtitle="Ranked by your fit — not by posting date."
      />

      <div className="mb-6">
        <IntentComposer
          value={intentText}
          onChange={setIntentText}
          onSubmit={askAgent}
          intent={intent}
          loading={searching}
        />
        {feed ? (
          <button
            onClick={clearIntent}
            className="mt-2 text-xs font-medium text-primary"
          >
            ← Clear agent search
          </button>
        ) : null}
      </div>

      {error ? <ErrorText>{error}</ErrorText> : null}
      {actionError ? (
        <div className="mb-4">
          <ErrorText>{actionError}</ErrorText>
        </div>
      ) : null}
      {notice ? (
        <div className="mb-4 rounded-lg border border-success/20 bg-success/5 px-3 py-2 text-sm text-success">
          {notice}
        </div>
      ) : null}

      {/* Buckets */}
      <div className="mb-4 flex flex-wrap gap-2">
        {BUCKETS.map((b) => (
          <button
            key={b.key}
            onClick={() => setBucket(b.key)}
            className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
              bucket === b.key
                ? "border-primary bg-primary/10 text-primary"
                : "border-border text-muted hover:text-foreground"
            }`}
          >
            {b.label} · {counts[b.key]}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        <div className="lg:col-span-3">
          {loading ? (
            <Spinner />
          ) : filtered.length === 0 ? (
            <EmptyState
              title="Nothing in this bucket"
              description="Try another bucket, or refine your profile so the agent can rank more roles."
            />
          ) : (
            <div className="space-y-3">
              {filtered.map(({ job, fit }) => (
                <Card key={job.id}>
                  <div className="flex items-start gap-4">
                    <FitRing score={fit.score} size={60} />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="truncate font-semibold text-foreground">
                            {job.title}
                          </p>
                          <p className="truncate text-xs text-muted">
                            {job.company}
                            {job.location ? ` · ${job.location}` : ""}
                            {job.work_mode ? ` · ${job.work_mode}` : ""}
                          </p>
                        </div>
                        <Badge
                          tone={
                            fit.bucket === "recommended"
                              ? "success"
                              : fit.bucket === "review"
                                ? "warning"
                                : "neutral"
                          }
                        >
                          {fit.bucket === "recommended"
                            ? "Recommended"
                            : fit.bucket === "review"
                              ? "Review"
                              : "Low fit"}
                        </Badge>
                      </div>

                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {fit.matched.slice(0, 5).map((s) => (
                          <Badge key={s} tone="success">
                            {s}
                          </Badge>
                        ))}
                        {fit.missing.slice(0, 3).map((s) => (
                          <Badge key={s} tone="danger">
                            {s}
                          </Badge>
                        ))}
                        {fit.derived ? (
                          <span className="text-[10px] text-muted">
                            (inferred from description)
                          </span>
                        ) : null}
                      </div>

                      <div className="mt-3 flex flex-wrap gap-2">
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => analyze(job)}
                        >
                          Analyze fit
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => track(job)}
                          disabled={trackedIds.has(job.id)}
                        >
                          {trackedIds.has(job.id) ? "In pipeline" : "Track"}
                        </Button>
                        <a
                          href={job.application_url || job.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-foreground hover:bg-background"
                        >
                          Posting →
                        </a>
                      </div>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>

        <div className="lg:col-span-2">
          <div className="sticky top-6">
            {!selected ? (
              <Card>
                <CardHeader
                  title="Explainable fit"
                  subtitle="Select a role and run analysis"
                />
                <p className="text-sm text-muted">
                  The agent breaks each score into skills, role alignment,
                  eligibility, and evidence — then tells you why you fit and
                  where the gaps are.
                </p>
              </Card>
            ) : (
              <Card>
                <CardHeader
                  title={selected.title}
                  subtitle={`${selected.company}${
                    selected.location ? ` · ${selected.location}` : ""
                  }`}
                />
                {evaluating ? (
                  <Spinner label="Analyzing fit…" />
                ) : evaluation ? (
                  <MatchBreakdown evaluation={evaluation} jobTitle={selected.title} />
                ) : (
                  <p className="text-sm text-muted">Press Analyze fit.</p>
                )}
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
