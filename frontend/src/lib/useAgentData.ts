"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  applicationsApi,
  documentsApi,
  jobsApi,
  kbApi,
  ApiError,
} from "./api";
import type {
  Application,
  ApplicationEvent,
  CandidateKB,
  GeneratedDocument,
  JobPosting,
} from "./types";
import {
  buildActionItems,
  preScoreFit,
  publicCandidateSkills,
  type ActionItem,
  type CandidateSkill,
  type FitAssessment,
} from "./agent";

export interface AgentData {
  jobs: JobPosting[];
  documents: GeneratedDocument[];
  applications: Application[];
  events: ApplicationEvent[];
  kb: CandidateKB | null;
  candidateSkills: CandidateSkill[];
  fitByJob: Map<number, FitAssessment>;
  rankedJobs: JobPosting[];
  actionItems: ActionItem[];
  loading: boolean;
  error: string;
  refresh: () => Promise<void>;
}

export function useAgentData(): AgentData {
  const [jobs, setJobs] = useState<JobPosting[]>([]);
  const [documents, setDocuments] = useState<GeneratedDocument[]>([]);
  const [applications, setApplications] = useState<Application[]>([]);
  const [events, setEvents] = useState<ApplicationEvent[]>([]);
  const [kb, setKb] = useState<CandidateKB | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [jobsRes, docsRes, appsRes, kbRes] = await Promise.all([
        jobsApi.list({ limit: 100 }),
        documentsApi.list(),
        applicationsApi.list(),
        kbApi.get(true).catch((err) => {
          if (err instanceof ApiError && err.status === 404) return null;
          throw err;
        }),
      ]);
      setJobs(jobsRes.items);
      setDocuments(docsRes.items);
      setApplications(appsRes.items);
      setKb(kbRes ? kbRes.data : null);

      // Fetch audit events for the most recent applications (bounded).
      const recent = [...appsRes.items]
        .sort((a, b) => b.id - a.id)
        .slice(0, 10);
      const eventLists = await Promise.all(
        recent.map((a) =>
          applicationsApi
            .events(a.id)
            .then((r) => r.items)
            .catch(() => [] as ApplicationEvent[]),
        ),
      );
      setEvents(eventLists.flat());
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const candidateSkills = useMemo(() => publicCandidateSkills(kb), [kb]);

  const fitByJob = useMemo(() => {
    const map = new Map<number, FitAssessment>();
    for (const job of jobs) {
      map.set(job.id, preScoreFit(job, candidateSkills));
    }
    return map;
  }, [jobs, candidateSkills]);

  const rankedJobs = useMemo(() => {
    return [...jobs].sort(
      (a, b) => (fitByJob.get(b.id)?.score ?? 0) - (fitByJob.get(a.id)?.score ?? 0),
    );
  }, [jobs, fitByJob]);

  const recommendedJobIds = useMemo(
    () =>
      rankedJobs
        .filter((j) => fitByJob.get(j.id)?.bucket === "recommended")
        .map((j) => j.id),
    [rankedJobs, fitByJob],
  );

  const actionItems = useMemo(
    () =>
      buildActionItems({
        documents,
        applications,
        jobs,
        recommendedJobIds,
      }),
    [documents, applications, jobs, recommendedJobIds],
  );

  return {
    jobs,
    documents,
    applications,
    events,
    kb,
    candidateSkills,
    fitByJob,
    rankedJobs,
    actionItems,
    loading,
    error,
    refresh,
  };
}
