"use client";

import { useCallback, useEffect, useState } from "react";
import { applicationsApi, jobsApi } from "@/lib/api";
import type { Application, JobPosting } from "@/lib/types";
import { TopBar } from "@/components/TopBar";
import {
  ApplicationStatusBadge,
  Badge,
  Button,
  Card,
  CardHeader,
  EmptyState,
  ErrorText,
  ScoreBadge,
  Select,
  Spinner,
} from "@/components/ui";

const COLUMNS = [
  "Discovered",
  "Matched",
  "Approved",
  "Applied",
  "Rejected",
] as const;

const NEXT_STAGE: Record<string, string | null> = {
  Discovered: "Matched",
  Matched: "Approved",
  Approved: null,
  Applied: null,
  Rejected: null,
};

export default function ApplicationsPage() {
  const [apps, setApps] = useState<Application[]>([]);
  const [jobs, setJobs] = useState<JobPosting[]>([]);
  const [jobId, setJobId] = useState("");
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await applicationsApi.list();
      setApps(res.items);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    (async () => {
      try {
        const res = await jobsApi.list({ limit: 100 });
        setJobs(res.items);
        if (res.items[0]) setJobId(String(res.items[0].id));
      } catch {
        // non-fatal
      }
    })();
  }, [load]);

  async function withBusy(id: number, fn: () => Promise<void>) {
    setBusyId(id);
    setError("");
    setNotice("");
    try {
      await fn();
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusyId(null);
    }
  }

  async function createApp() {
    if (!jobId) return;
    setError("");
    setNotice("");
    try {
      await applicationsApi.create(Number(jobId));
      await load();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function advance(app: Application) {
    const next = NEXT_STAGE[app.status];
    if (!next) return;
    await withBusy(app.id, async () => {
      await applicationsApi.transition(app.id, next);
    });
  }

  async function reject(app: Application) {
    await withBusy(app.id, async () => {
      await applicationsApi.transition(app.id, "Rejected", "Rejected via dashboard");
    });
  }

  async function submit(app: Application, dryRun: boolean) {
    if (
      !dryRun &&
      !window.confirm(
        "Submit this application for real? This requires an approved resume and will mark it Applied.",
      )
    ) {
      return;
    }
    await withBusy(app.id, async () => {
      const res = await applicationsApi.submit(app.id, dryRun);
      setNotice(
        res.success
          ? `${dryRun ? "Dry run" : "Submission"} OK via ${res.ats}. ` +
              (res.dry_run
                ? "Form pre-filled (not submitted)."
                : "Application marked Applied.")
          : `Submission failed: ${res.error}`,
      );
    });
  }

  return (
    <div>
      <TopBar
        title="Applications"
        subtitle="Guarded pipeline: approve documents before submitting."
        actions={
          <Button variant="secondary" size="sm" onClick={load}>
            Refresh
          </Button>
        }
      />

      <Card className="mb-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="flex-1">
            <Select
              label="Track a job"
              value={jobId}
              onChange={(e) => setJobId(e.target.value)}
            >
              {jobs.length === 0 ? <option value="">No jobs available</option> : null}
              {jobs.map((job) => (
                <option key={job.id} value={job.id}>
                  {job.title} — {job.company}
                </option>
              ))}
            </Select>
          </div>
          <Button size="sm" onClick={createApp} disabled={!jobId}>
            Add to pipeline
          </Button>
        </div>
      </Card>

      {error ? <div className="mb-4"><ErrorText>{error}</ErrorText></div> : null}
      {notice ? (
        <div className="mb-4 rounded-lg border border-primary/20 bg-primary/5 px-3 py-2 text-sm text-primary">
          {notice}
        </div>
      ) : null}

      {loading ? (
        <Spinner />
      ) : apps.length === 0 ? (
        <EmptyState
          title="No applications yet"
          description="Add a job to the pipeline to start tracking it."
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3 xl:grid-cols-5">
          {COLUMNS.map((col) => {
            const items = apps.filter((a) => a.status === col);
            return (
              <div key={col} className="flex flex-col gap-3">
                <div className="flex items-center justify-between px-1">
                  <ApplicationStatusBadge status={col} />
                  <span className="text-xs font-medium text-muted">
                    {items.length}
                  </span>
                </div>

                {items.map((app) => (
                  <Card key={app.id} className="p-3">
                    <div className="flex items-start justify-between gap-2">
                      <span className="text-sm font-medium text-foreground">
                        App #{app.id}
                      </span>
                      <ScoreBadge score={app.match_score} />
                    </div>
                    <p className="mt-1 text-xs text-muted">
                      Job #{app.job_posting_id}
                    </p>

                    {app.last_error ? (
                      <p className="mt-2 rounded bg-danger/5 px-2 py-1 text-xs text-danger">
                        {app.last_error}
                      </p>
                    ) : null}

                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {NEXT_STAGE[app.status] ? (
                        <Button
                          size="sm"
                          variant="secondary"
                          loading={busyId === app.id}
                          onClick={() => advance(app)}
                        >
                          → {NEXT_STAGE[app.status]}
                        </Button>
                      ) : null}

                      {app.status === "Approved" ? (
                        <>
                          <Button
                            size="sm"
                            variant="secondary"
                            loading={busyId === app.id}
                            onClick={() => submit(app, true)}
                          >
                            Dry run
                          </Button>
                          <Button
                            size="sm"
                            loading={busyId === app.id}
                            onClick={() => submit(app, false)}
                          >
                            Submit
                          </Button>
                        </>
                      ) : null}

                      {app.status !== "Rejected" && app.status !== "Applied" ? (
                        <Button
                          size="sm"
                          variant="ghost"
                          loading={busyId === app.id}
                          onClick={() => reject(app)}
                        >
                          Reject
                        </Button>
                      ) : null}
                    </div>
                  </Card>
                ))}

                {items.length === 0 ? (
                  <div className="rounded-lg border border-dashed border-border px-3 py-6 text-center text-xs text-muted">
                    Empty
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      )}

      <Card className="mt-6">
        <CardHeader
          title="How submission works"
          subtitle="Two-phase, human-gated automation"
        />
        <ul className="space-y-2 text-sm text-muted">
          <li>
            <Badge tone="success">1</Badge> Approve a tailored resume document
            (Documents page).
          </li>
          <li>
            <Badge tone="success">2</Badge> Move the application to{" "}
            <strong>Approved</strong>.
          </li>
          <li>
            <Badge tone="success">3</Badge> Run a <strong>Dry run</strong> to
            pre-fill the ATS form and capture evidence.
          </li>
          <li>
            <Badge tone="success">4</Badge> <strong>Submit</strong> to apply —
            idempotent and audited.
          </li>
        </ul>
      </Card>
    </div>
  );
}
