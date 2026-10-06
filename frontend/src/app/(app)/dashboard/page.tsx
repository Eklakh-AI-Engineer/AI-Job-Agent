"use client";

import Link from "next/link";
import { useAgentData } from "@/lib/useAgentData";
import { buildTimeline, isToday, relativeTime } from "@/lib/agent";
import { ActionCenter, ActivityTimeline, AgentAvatar, FitRing } from "@/components/agent";
import { Badge, Button, Card, CardHeader, EmptyState, Spinner, StatCard } from "@/components/ui";

export default function CommandCenterPage() {
  const data = useAgentData();
  const {
    jobs,
    documents,
    applications,
    events,
    rankedJobs,
    fitByJob,
    actionItems,
    loading,
    error,
  } = data;

  const discoveredToday = jobs.filter((j) => isToday(j.created_at)).length;
  const recommended = rankedJobs.filter(
    (j) => fitByJob.get(j.id)?.bucket === "recommended",
  );
  const pendingDocs = documents.filter((d) => d.status === "draft").length;
  const readyToSubmit = applications.filter((a) => a.status === "Approved").length;

  const timeline = buildTimeline({ jobs, documents, applications, events }).slice(0, 6);
  const topPicks = recommended.slice(0, 3);

  return (
    <div className="space-y-6">
      {/* Agent hero */}
      <Card className="border-primary/20 bg-gradient-to-br from-primary/5 to-transparent">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4">
            <AgentAvatar size={52} active={loading} />
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-foreground">
                Command Center
              </h1>
              <p className="text-sm text-muted">
                {loading
                  ? "The agent is scanning your pipeline…"
                  : `Your agent is working across ${jobs.length} opportunit${
                      jobs.length === 1 ? "y" : "ies"
                    } and ${applications.length} application${
                      applications.length === 1 ? "" : "s"
                    }.`}
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <Link href="/copilot">
              <Button size="sm">Start with Copilot</Button>
            </Link>
            <Link href="/opportunities">
              <Button size="sm" variant="secondary">
                View opportunities
              </Button>
            </Link>
          </div>
        </div>
      </Card>

      {error ? (
        <Card className="border-danger/20 bg-danger/5">
          <p className="text-sm text-danger">{error}</p>
        </Card>
      ) : null}

      {/* Daily summary */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Discovered today"
          value={loading ? "—" : discoveredToday}
          hint="New roles the agent found"
          accent="text-primary"
        />
        <StatCard
          label="Strong-fit roles"
          value={loading ? "—" : recommended.length}
          hint="Ranked against your profile"
          accent="text-success"
        />
        <StatCard
          label="Awaiting your review"
          value={loading ? "—" : pendingDocs}
          hint="Drafted documents to approve"
          accent="text-warning"
        />
        <StatCard
          label="Ready to submit"
          value={loading ? "—" : readyToSubmit}
          hint="Approved applications"
          accent="text-foreground"
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Action center */}
        <div className="lg:col-span-1">
          {loading ? <Spinner /> : <ActionCenter items={actionItems} />}
        </div>

        {/* Recommended opportunities */}
        <div className="lg:col-span-2">
          <Card padded={false}>
            <div className="p-5">
              <CardHeader
                title="Top recommendations"
                subtitle="Ranked by fit against your Candidate KB"
                action={
                  <Link href="/opportunities" className="text-sm font-medium text-primary">
                    See all →
                  </Link>
                }
              />
              {loading ? (
                <Spinner />
              ) : topPicks.length === 0 ? (
                <EmptyState
                  title="No strong-fit roles yet"
                  description="Build your Candidate KB in Profile, then the agent can rank opportunities for you."
                  action={
                    <Link href="/profile">
                      <Button size="sm">Complete profile</Button>
                    </Link>
                  }
                />
              ) : (
                <div className="space-y-3">
                  {topPicks.map((job) => {
                    const fit = fitByJob.get(job.id);
                    return (
                      <Link
                        key={job.id}
                        href="/opportunities"
                        className="flex items-center gap-4 rounded-lg border border-border p-3 transition-colors hover:border-primary/40"
                      >
                        <FitRing score={fit?.score} size={56} />
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-semibold text-foreground">
                            {job.title}
                          </p>
                          <p className="truncate text-xs text-muted">
                            {job.company}
                            {job.location ? ` · ${job.location}` : ""}
                          </p>
                          <div className="mt-1 flex flex-wrap gap-1">
                            {(fit?.matched ?? []).slice(0, 4).map((s) => (
                              <Badge key={s} tone="success">
                                {s}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      </Link>
                    );
                  })}
                </div>
              )}
            </div>
          </Card>
        </div>
      </div>

      {/* Activity + pipeline */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader
            title="Agent activity"
            subtitle="Discovery → matching → documents → review"
            action={
              <Link href="/activity" className="text-sm font-medium text-primary">
                Full timeline →
              </Link>
            }
          />
          {loading ? <Spinner /> : <ActivityTimeline events={timeline} />}
        </Card>

        <Card>
          <CardHeader title="Pipeline" subtitle="Applications by stage" />
          {loading ? (
            <Spinner />
          ) : applications.length === 0 ? (
            <p className="text-sm text-muted">No applications tracked yet.</p>
          ) : (
            <ul className="space-y-3">
              {["Discovered", "Matched", "Approved", "Applied", "Rejected"].map(
                (stage) => (
                  <li
                    key={stage}
                    className="flex items-center justify-between text-sm"
                  >
                    <span className="text-muted">{stage}</span>
                    <span className="font-semibold text-foreground">
                      {applications.filter((a) => a.status === stage).length}
                    </span>
                  </li>
                ),
              )}
            </ul>
          )}
          {!loading && applications.length > 0 ? (
            <p className="mt-4 text-xs text-muted">
              Last activity{" "}
              {relativeTime(
                [...applications].sort((a, b) => b.id - a.id)[0]?.created_at,
              )}
            </p>
          ) : null}
        </Card>
      </div>
    </div>
  );
}
