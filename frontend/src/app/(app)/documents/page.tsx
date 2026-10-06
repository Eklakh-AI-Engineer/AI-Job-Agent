"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { documentsApi } from "@/lib/api";
import type { GeneratedDocument } from "@/lib/types";
import { relativeTime } from "@/lib/agent";
import { useAgentData } from "@/lib/useAgentData";
import { TopBar } from "@/components/TopBar";
import {
  Badge,
  Button,
  Card,
  CardHeader,
  DocumentStatusBadge,
  EmptyState,
  ErrorText,
  Select,
  Spinner,
  Textarea,
} from "@/components/ui";

type DocType = "resume" | "cover_letter";
type Tab = "preview" | "why" | "versions";

export default function DocumentsWorkspacePage() {
  const data = useAgentData();
  const [docs, setDocs] = useState<GeneratedDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");

  const [jobId, setJobId] = useState<string>("");
  const [selected, setSelected] = useState<GeneratedDocument | null>(null);
  const [draft, setDraft] = useState("");
  const [tab, setTab] = useState<Tab>("preview");

  const loadDocs = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await documentsApi.list();
      setDocs(res.items);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDocs();
  }, [loadDocs]);

  useEffect(() => {
    if (!jobId && data.jobs[0]) setJobId(String(data.jobs[0].id));
  }, [data.jobs, jobId]);

  const versions = useMemo(() => {
    if (!selected) return [];
    return docs
      .filter(
        (d) =>
          d.job_posting_id === selected.job_posting_id &&
          d.doc_type === selected.doc_type,
      )
      .sort((a, b) => b.version - a.version);
  }, [docs, selected]);

  const ats = useMemo(() => {
    const raw = selected?.meta?.ats as
      | {
          score?: number;
          matched_keywords?: string[];
          missing_keywords?: string[];
          coverage_ratio?: number;
          recommendations?: string[];
        }
      | undefined;
    return raw;
  }, [selected]);

  function open(doc: GeneratedDocument) {
    setSelected(doc);
    setDraft(doc.content);
    setTab("preview");
    setNotice("");
  }

  async function generate(docType: DocType) {
    if (!jobId) return;
    setBusy(true);
    setError("");
    try {
      const doc = await documentsApi.generate(Number(jobId), docType);
      open(doc);
      await loadDocs();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function saveEdit() {
    if (!selected) return;
    setBusy(true);
    setError("");
    try {
      const updated = await documentsApi.edit(selected.id, draft);
      setSelected(updated);
      await loadDocs();
      setNotice("Edit saved (reset to draft).");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function setStatus(status: "approved" | "rejected") {
    if (!selected) return;
    setBusy(true);
    setError("");
    try {
      const updated = await documentsApi.setStatus(selected.id, status);
      setSelected(updated);
      await loadDocs();
      setNotice(status === "approved" ? "Document approved." : "Document rejected.");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <TopBar
        title="Document Workspace"
        subtitle="Why each document was written, what evidence it used, and how it scores."
        actions={
          <Button variant="secondary" size="sm" onClick={loadDocs}>
            Refresh
          </Button>
        }
      />

      <Card className="mb-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="flex-1">
            <Select
              label="Tailor for job"
              value={jobId}
              onChange={(e) => setJobId(e.target.value)}
            >
              {data.jobs.length === 0 ? <option value="">No jobs available</option> : null}
              {data.jobs.map((job) => (
                <option key={job.id} value={job.id}>
                  {job.title} — {job.company}
                </option>
              ))}
            </Select>
          </div>
          <div className="flex gap-2">
            <Button size="sm" loading={busy} onClick={() => generate("resume")}>
              Generate resume
            </Button>
            <Button
              size="sm"
              variant="secondary"
              loading={busy}
              onClick={() => generate("cover_letter")}
            >
              Generate cover letter
            </Button>
          </div>
        </div>
      </Card>

      {error ? <div className="mb-4"><ErrorText>{error}</ErrorText></div> : null}
      {notice ? (
        <div className="mb-4 rounded-lg border border-success/20 bg-success/5 px-3 py-2 text-sm text-success">
          {notice}
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        <div className="lg:col-span-2">
          {loading ? (
            <Spinner />
          ) : docs.length === 0 ? (
            <EmptyState
              title="No documents yet"
              description="Select a job above and generate a tailored document."
            />
          ) : (
            <div className="space-y-3">
              {docs.map((doc) => (
                <Card
                  key={doc.id}
                  className={`cursor-pointer transition-colors hover:border-primary/40 ${
                    selected?.id === doc.id ? "border-primary" : ""
                  }`}
                >
                  <div onClick={() => open(doc)}>
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-semibold capitalize text-foreground">
                        {doc.doc_type.replace("_", " ")}
                      </span>
                      <DocumentStatusBadge status={doc.status} />
                    </div>
                    <p className="mt-1 text-xs text-muted">
                      Job #{doc.job_posting_id} · v{doc.version} ·{" "}
                      {relativeTime(doc.created_at)}
                    </p>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>

        <div className="lg:col-span-3">
          {!selected ? (
            <Card>
              <CardHeader
                title="Workspace"
                subtitle="Select a document to inspect it"
              />
              <p className="text-sm text-muted">
                The agent shows the reasoning behind every generated document:
                the evidence used, the ATS score, and any missing requirements.
              </p>
            </Card>
          ) : (
            <Card>
              <CardHeader
                title={`${selected.doc_type.replace("_", " ")} · v${selected.version}`}
                subtitle={`Job #${selected.job_posting_id}`}
                action={<DocumentStatusBadge status={selected.status} />}
              />

              {/* Tabs */}
              <div className="mb-4 flex gap-1 rounded-lg border border-border p-0.5">
                {(["preview", "why", "versions"] as Tab[]).map((t) => (
                  <button
                    key={t}
                    onClick={() => setTab(t)}
                    className={`flex-1 rounded-md px-3 py-1.5 text-xs font-medium capitalize transition-colors ${
                      tab === t
                        ? "bg-primary text-white"
                        : "text-muted hover:text-foreground"
                    }`}
                  >
                    {t === "why" ? "Why this doc" : t}
                  </button>
                ))}
              </div>

              {tab === "preview" ? (
                <>
                  <Textarea
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    rows={16}
                    className="font-mono text-xs"
                  />
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Button size="sm" variant="secondary" loading={busy} onClick={saveEdit}>
                      Save edit
                    </Button>
                    <Button
                      size="sm"
                      variant="success"
                      loading={busy}
                      onClick={() => setStatus("approved")}
                    >
                      Approve
                    </Button>
                    <Button
                      size="sm"
                      variant="danger"
                      loading={busy}
                      onClick={() => setStatus("rejected")}
                    >
                      Reject
                    </Button>
                  </div>
                </>
              ) : null}

              {tab === "why" ? (
                <div className="space-y-4">
                  {ats ? (
                    <div>
                      <div className="mb-2 flex items-center gap-3">
                        <Badge tone="primary">ATS score: {ats.score ?? "—"}</Badge>
                        <span className="text-xs text-muted">
                          coverage {Math.round((ats.coverage_ratio ?? 0) * 100)}%
                        </span>
                      </div>
                      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                        <div>
                          <p className="mb-1 text-xs font-semibold uppercase text-success">
                            Matched keywords
                          </p>
                          <div className="flex flex-wrap gap-1.5">
                            {(ats.matched_keywords ?? []).length === 0 ? (
                              <span className="text-xs text-muted">None</span>
                            ) : (
                              (ats.matched_keywords ?? []).map((k) => (
                                <Badge key={k} tone="success">
                                  {k}
                                </Badge>
                              ))
                            )}
                          </div>
                        </div>
                        <div>
                          <p className="mb-1 text-xs font-semibold uppercase text-danger">
                            Missing requirements
                          </p>
                          <div className="flex flex-wrap gap-1.5">
                            {(ats.missing_keywords ?? []).length === 0 ? (
                              <span className="text-xs text-muted">None</span>
                            ) : (
                              (ats.missing_keywords ?? []).map((k) => (
                                <Badge key={k} tone="danger">
                                  {k}
                                </Badge>
                              ))
                            )}
                          </div>
                        </div>
                      </div>
                      {(ats.recommendations ?? []).length > 0 ? (
                        <ul className="mt-3 space-y-1 text-xs text-muted">
                          {(ats.recommendations ?? []).map((r, i) => (
                            <li key={i}>• {r}</li>
                          ))}
                        </ul>
                      ) : null}
                    </div>
                  ) : (
                    <p className="text-sm text-muted">
                      No ATS analysis recorded for this document.
                    </p>
                  )}

                  <div>
                    <p className="mb-1 text-xs font-semibold uppercase text-muted">
                      Evidence used
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {(selected.used_claim_ids ?? []).length === 0 ? (
                        <span className="text-xs text-muted">
                          No claim references recorded.
                        </span>
                      ) : (
                        (selected.used_claim_ids ?? []).map((id) => (
                          <Badge key={id} tone="neutral">
                            {id}
                          </Badge>
                        ))
                      )}
                    </div>
                    <p className="mt-2 text-[11px] text-muted">
                      Only public evidence is ever included. Restricted claims
                      are excluded by design.
                    </p>
                  </div>
                </div>
              ) : null}

              {tab === "versions" ? (
                <div className="space-y-2">
                  {versions.map((v) => (
                    <button
                      key={v.id}
                      onClick={() => open(v)}
                      className={`flex w-full items-center justify-between rounded-lg border p-3 text-left transition-colors ${
                        v.id === selected.id
                          ? "border-primary"
                          : "border-border hover:border-primary/40"
                      }`}
                    >
                      <div>
                        <p className="text-sm font-medium text-foreground">
                          Version {v.version}
                        </p>
                        <p className="text-xs text-muted">
                          {relativeTime(v.created_at)}
                        </p>
                      </div>
                      <DocumentStatusBadge status={v.status} />
                    </button>
                  ))}
                </div>
              ) : null}
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
