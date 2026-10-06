"use client";

import { useMemo, useState } from "react";
import { buildTimeline, type TimelineStage } from "@/lib/agent";
import { useAgentData } from "@/lib/useAgentData";
import { TopBar } from "@/components/TopBar";
import { ActivityTimeline, AgentAvatar } from "@/components/agent";
import { Badge, Card, CardHeader, Spinner } from "@/components/ui";

const FILTERS: { key: TimelineStage | "all"; label: string }[] = [
  { key: "all", label: "All" },
  { key: "discovered", label: "Discovery" },
  { key: "match", label: "Matching" },
  { key: "document", label: "Documents" },
  { key: "approval", label: "Approval" },
  { key: "application", label: "Applications" },
  { key: "error", label: "Rejected" },
];

export default function ActivityPage() {
  const data = useAgentData();
  const { jobs, documents, applications, events, loading, error } = data;
  const [filter, setFilter] = useState<TimelineStage | "all">("all");

  const timeline = useMemo(
    () => buildTimeline({ jobs, documents, applications, events }),
    [jobs, documents, applications, events],
  );

  const filtered = useMemo(
    () =>
      filter === "all"
        ? timeline
        : timeline.filter((e) => e.stage === filter),
    [timeline, filter],
  );

  return (
    <div>
      <TopBar
        title="Agent Activity"
        subtitle="Everything your agent has done, in order."
      />

      <Card className="mb-6">
        <div className="flex items-center gap-3">
          <AgentAvatar size={40} active={loading} />
          <div>
            <p className="text-sm font-medium text-foreground">
              {loading
                ? "Loading agent history…"
                : `${timeline.length} recorded step${
                    timeline.length === 1 ? "" : "s"
                  } across discovery, matching, documents, and applications.`}
            </p>
            <p className="text-xs text-muted">
              Built from real timestamps and audit events — nothing simulated.
            </p>
          </div>
        </div>
      </Card>

      {error ? (
        <Card className="mb-4 border-danger/20 bg-danger/5">
          <p className="text-sm text-danger">{error}</p>
        </Card>
      ) : null}

      <div className="mb-4 flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
              filter === f.key
                ? "border-primary bg-primary/10 text-primary"
                : "border-border text-muted hover:text-foreground"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      <Card>
        <CardHeader
          title="Timeline"
          subtitle={
            filter === "all"
              ? "Newest first"
              : `Filtered: ${filter}`
          }
          action={<Badge tone="neutral">{filtered.length}</Badge>}
        />
        {loading ? <Spinner /> : <ActivityTimeline events={filtered} />}
      </Card>
    </div>
  );
}
