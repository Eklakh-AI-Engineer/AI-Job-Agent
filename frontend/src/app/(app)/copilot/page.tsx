"use client";

import { useCallback, useEffect, useState } from "react";
import {
  applicationsApi,
  documentsApi,
  evaluationApi,
} from "@/lib/api";
import type {
  Application,
  EvaluationResult,
  GeneratedDocument,
  JobPosting,
} from "@/lib/types";
import { useAgentData } from "@/lib/useAgentData";
import { TopBar } from "@/components/TopBar";
import {
  AgentAvatar,
  MatchBreakdown,
  Stepper,
} from "@/components/agent";
import {
  ApplicationStatusBadge,
  Badge,
  Button,
  Card,
  CardHeader,
  DocumentStatusBadge,
  EmptyState,
  ErrorText,
  Spinner,
} from "@/components/ui";

const STEPS = [
  { key: "choose", label: "Choose job" },
  { key: "analyze", label: "Analyze fit" },
  { key: "resume", label: "Resume" },
  { key: "letter", label: "Cover letter" },
  { key: "apply", label: "Review & apply" },
];

export default function CopilotPage() {
  const data = useAgentData();
  const { rankedJobs, fitByJob, loading } = data;

  const [step, setStep] = useState(0);
  const [job, setJob] = useState<JobPosting | null>(null);
  const [evaluation, setEvaluation] = useState<EvaluationResult | null>(null);
  const [resume, setResume] = useState<GeneratedDocument | null>(null);
  const [letter, setLetter] = useState<GeneratedDocument | null>(null);
  const [application, setApplication] = useState<Application | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const recommended = rankedJobs
    .filter((j) => (fitByJob.get(j.id)?.score ?? 0) >= 45)
    .slice(0, 8);

  const run = useCallback(
    async (fn: () => Promise<void>) => {
      setBusy(true);
      setError("");
      setNotice("");
      try {
        await fn();
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setBusy(false);
      }
    },
    [],
  );

  // Auto-run analysis when entering step 1
  useEffect(() => {
    if (step === 1 && job && !evaluation) {
      void run(async () => {
        setEvaluation(await evaluationApi.evaluate(job.id));
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, job]);

  async function generateResume() {
    if (!job) return;
    await run(async () => {
      setResume(await documentsApi.generate(job.id, "resume"));
      setNotice("Resume drafted from your public evidence.");
    });
  }

  async function generateLetter() {
    if (!job) return;
    await run(async () => {
      setLetter(await documentsApi.generate(job.id, "cover_letter"));
      setNotice("Cover letter drafted.");
    });
  }

  async function approveDoc(doc: GeneratedDocument, setter: (d: GeneratedDocument) => void) {
    await run(async () => {
      const updated = await documentsApi.setStatus(doc.id, "approved");
      setter(updated);
      setNotice("Document approved.");
    });
  }

  async function ensureApplication(): Promise<Application | null> {
    if (!job) return null;
    if (application) return application;
    const created = await applicationsApi.create(job.id);
    setApplication(created);
    return created;
  }

  async function prepareApplication() {
    await run(async () => {
      const app = await ensureApplication();
      if (!app) return;
      if (app.status === "Discovered") {
        setApplication(await applicationsApi.transition(app.id, "Matched"));
      }
      setNotice("Application added to your pipeline.");
    });
  }

  async function approveApplication() {
    if (!application) return;
    await run(async () => {
      setApplication(await applicationsApi.transition(application.id, "Approved"));
      setNotice("Application approved — ready for a dry run.");
    });
  }

  async function dryRun() {
    if (!application) return;
    await run(async () => {
      const res = await applicationsApi.submit(application.id, true);
      setNotice(
        res.success
          ? `Dry run OK via ${res.ats}. Form pre-filled (not submitted).`
          : `Dry run failed: ${res.error}`,
      );
    });
  }

  async function submit() {
    if (!application) return;
    if (!window.confirm("Submit this application for real? This cannot be undone.")) {
      return;
    }
    await run(async () => {
      const res = await applicationsApi.submit(application.id, false);
      if (res.success && !res.dry_run) {
        setApplication((prev) =>
          prev ? { ...prev, status: "Applied" } : prev,
        );
        setNotice(`Submitted via ${res.ats}.`);
      } else {
        setNotice(`Submission failed: ${res.error}`);
      }
    });
  }

  function reset() {
    setStep(0);
    setJob(null);
    setEvaluation(null);
    setResume(null);
    setLetter(null);
    setApplication(null);
    setNotice("");
    setError("");
  }

  const resumeApproved = resume?.status === "approved";

  return (
    <div>
      <TopBar
        title="Application Copilot"
        subtitle="One guided workflow: pick → analyze → documents → apply."
        actions={
          <Button variant="secondary" size="sm" onClick={reset}>
            Restart
          </Button>
        }
      />

      <Card className="mb-6">
        <Stepper steps={STEPS} current={step} />
      </Card>

      {error ? <div className="mb-4"><ErrorText>{error}</ErrorText></div> : null}
      {notice ? (
        <div className="mb-4 rounded-lg border border-success/20 bg-success/5 px-3 py-2 text-sm text-success">
          {notice}
        </div>
      ) : null}

      {/* Step 0: choose */}
      {step === 0 ? (
        <Card>
          <CardHeader
            title="Choose an opportunity"
            subtitle="Ranked by fit against your profile"
          />
          {loading ? (
            <Spinner />
          ) : recommended.length === 0 ? (
            <EmptyState
              title="No ranked roles yet"
              description="Complete your Candidate KB so the agent can recommend roles."
            />
          ) : (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {recommended.map((j) => (
                <button
                  key={j.id}
                  onClick={() => {
                    setJob(j);
                    setStep(1);
                  }}
                  className="rounded-lg border border-border p-4 text-left transition-colors hover:border-primary/40"
                >
                  <p className="font-medium text-foreground">{j.title}</p>
                  <p className="text-xs text-muted">
                    {j.company}
                    {j.location ? ` · ${j.location}` : ""}
                  </p>
                  <div className="mt-2">
                    <Badge tone="primary">
                      fit {fitByJob.get(j.id)?.score ?? "—"}
                    </Badge>
                  </div>
                </button>
              ))}
            </div>
          )}
        </Card>
      ) : null}

      {/* Step 1: analyze */}
      {step === 1 && job ? (
        <Card>
          <CardHeader
            title={`Analyzing: ${job.title}`}
            subtitle={`${job.company}${
              job.location ? ` · ${job.location}` : ""
            }`}
            action={
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => setStep(0)}
                >
                  Back
                </Button>
                <Button
                  size="sm"
                  disabled={!evaluation}
                  onClick={() => setStep(2)}
                >
                  Continue
                </Button>
              </div>
            }
          />
          {busy && !evaluation ? (
            <Spinner label="Running deterministic fit analysis…" />
          ) : evaluation ? (
            <MatchBreakdown evaluation={evaluation} jobTitle={job.title} />
          ) : (
            <p className="text-sm text-muted">Analysis not started.</p>
          )}
        </Card>
      ) : null}

      {/* Step 2: resume */}
      {step === 2 && job ? (
        <Card>
          <CardHeader
            title="Tailored resume"
            subtitle="Generated from public evidence only"
            action={
              <div className="flex gap-2">
                <Button size="sm" variant="ghost" onClick={() => setStep(1)}>
                  Back
                </Button>
                <Button size="sm" onClick={() => setStep(3)} disabled={!resume}>
                  Continue
                </Button>
              </div>
            }
          />
          <div className="mb-3 flex flex-wrap gap-2">
            <Button size="sm" variant="secondary" loading={busy} onClick={generateResume}>
              {resume ? "Regenerate" : "Generate resume"}
            </Button>
            {resume ? <DocumentStatusBadge status={resume.status} /> : null}
            {resume && !resumeApproved ? (
              <Button
                size="sm"
                variant="success"
                loading={busy}
                onClick={() => approveDoc(resume, setResume)}
              >
                Approve resume
              </Button>
            ) : null}
          </div>
          {resume ? (
            <>
              {resume.meta?.ats ? (
                <Badge tone="primary">
                  ATS score:{" "}
                  {(resume.meta.ats as { score?: number }).score ?? "—"}
                </Badge>
              ) : null}
              <pre className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap rounded-lg border border-border bg-background p-4 text-xs text-foreground">
                {resume.content}
              </pre>
            </>
          ) : (
            <p className="text-sm text-muted">
              Generate a resume to continue.
            </p>
          )}
        </Card>
      ) : null}

      {/* Step 3: cover letter */}
      {step === 3 && job ? (
        <Card>
          <CardHeader
            title="Cover letter"
            subtitle="Evidence-grounded, no fabrication"
            action={
              <div className="flex gap-2">
                <Button size="sm" variant="ghost" onClick={() => setStep(2)}>
                  Back
                </Button>
                <Button size="sm" onClick={() => setStep(4)} disabled={!letter}>
                  Continue
                </Button>
              </div>
            }
          />
          <div className="mb-3 flex flex-wrap gap-2">
            <Button size="sm" variant="secondary" loading={busy} onClick={generateLetter}>
              {letter ? "Regenerate" : "Generate cover letter"}
            </Button>
            {letter ? <DocumentStatusBadge status={letter.status} /> : null}
            {letter && letter.status !== "approved" ? (
              <Button
                size="sm"
                variant="success"
                loading={busy}
                onClick={() => approveDoc(letter, setLetter)}
              >
                Approve letter
              </Button>
            ) : null}
          </div>
          {letter ? (
            <pre className="mt-2 max-h-80 overflow-auto whitespace-pre-wrap rounded-lg border border-border bg-background p-4 text-xs text-foreground">
              {letter.content}
            </pre>
          ) : (
            <p className="text-sm text-muted">
              Generate a cover letter to continue.
            </p>
          )}
        </Card>
      ) : null}

      {/* Step 4: apply */}
      {step === 4 && job ? (
        <Card>
          <CardHeader
            title="Review & apply"
            subtitle="The agent never submits without your approval"
            action={
              <Button size="sm" variant="ghost" onClick={() => setStep(3)}>
                Back
              </Button>
            }
          />
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <AgentAvatar size={36} active={busy} />
              <div className="text-sm">
                <p className="font-medium text-foreground">Ready checklist</p>
                <ul className="mt-1 space-y-1 text-xs text-muted">
                  <li>
                    {resumeApproved ? "✓" : "○"} Resume approved
                    {resume ? ` (v${resume.version})` : ""}
                  </li>
                  <li>
                    {letter?.status === "approved" ? "✓" : "○"} Cover letter
                    approved
                  </li>
                  <li>
                    {application?.status === "Approved" ? "✓" : "○"} Application
                    moved to Approved
                  </li>
                </ul>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <Button size="sm" variant="secondary" loading={busy} onClick={prepareApplication}>
                {application ? "In pipeline" : "Add to pipeline"}
              </Button>
              {application ? (
                <ApplicationStatusBadge status={application.status} />
              ) : null}
              {application &&
              application.status === "Matched" &&
              resumeApproved ? (
                <Button size="sm" variant="success" loading={busy} onClick={approveApplication}>
                  Approve application
                </Button>
              ) : null}
              {application?.status === "Approved" ? (
                <>
                  <Button size="sm" variant="secondary" loading={busy} onClick={dryRun}>
                    Dry run
                  </Button>
                  <Button size="sm" loading={busy} onClick={submit}>
                    Submit application
                  </Button>
                </>
              ) : null}
            </div>

            {!resumeApproved ? (
              <p className="text-xs text-warning">
                Approve a resume first — the pipeline requires an approved
                resume before an application can be approved or submitted.
              </p>
            ) : null}
          </div>
        </Card>
      ) : null}
    </div>
  );
}
