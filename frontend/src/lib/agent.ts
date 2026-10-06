// Agent intelligence helpers — pure, framework-agnostic functions that turn
// raw API data into the reasoning the UI surfaces. No backend calls here.

import type {
  Application,
  ApplicationEvent,
  CandidateKB,
  GeneratedDocument,
  JobPosting,
} from "./types";

// ---------------------------------------------------------------------------
// Skill matching
// ---------------------------------------------------------------------------

// Canonical term -> aliases (mirrors the backend evaluator's vocabulary).
const SKILL_ALIASES: Record<string, string[]> = {
  python: ["py", "python3"],
  pytorch: ["torch", "pytorch-lightning"],
  tensorflow: ["tf", "keras"],
  javascript: ["js", "node.js", "nodejs"],
  typescript: ["ts"],
  "machine learning": ["ml"],
  "deep learning": ["dl"],
  "natural language processing": ["nlp"],
  "computer vision": ["cv"],
  aws: ["amazon web services"],
  gcp: ["google cloud platform"],
  azure: ["microsoft azure"],
  kubernetes: ["k8s"],
  docker: ["containers"],
  sql: ["postgres", "postgresql", "mysql"],
  "ci/cd": ["cicd", "continuous integration"],
  react: ["reactjs", "react.js"],
  "large language models": ["llm", "llms"],
  rag: ["retrieval augmented generation"],
  "fine-tuning": ["finetuning"],
  "prompt engineering": [],
  mlops: ["ml ops"],
  spark: ["pyspark", "apache spark"],
  airflow: ["apache airflow"],
  kafka: ["apache kafka"],
  transformers: ["huggingface", "bert", "gpt"],
  "generative ai": ["genai"],
  "diffusion models": ["stable diffusion"],
  "reinforcement learning": ["rl"],
};

const SKILL_KEYS = Object.keys(SKILL_ALIASES);
const SKILL_ALIAS_VALUES = new Set(
  Object.values(SKILL_ALIASES).flat(),
);

function norm(s: string): string {
  return s.trim().toLowerCase();
}

/** True if two skill strings refer to the same concept (alias-aware). */
export function skillsMatch(a: string, b: string): boolean {
  const na = norm(a);
  const nb = norm(b);
  if (na === nb) return true;
  for (const [canonical, aliases] of Object.entries(SKILL_ALIASES)) {
    const set = [canonical, ...aliases];
    if (set.includes(na) && set.includes(nb)) return true;
  }
  if (na.length > 3 && nb.length > 3 && (na.includes(nb) || nb.includes(na))) {
    return true;
  }
  return false;
}

function isKnownSkill(token: string): boolean {
  const t = norm(token);
  return SKILL_KEYS.includes(t) || SKILL_ALIAS_VALUES.has(t);
}

export interface CandidateSkill {
  id: string;
  name: string;
  verified: boolean;
  disclosure: string;
}

export function extractCandidateSkills(kb: CandidateKB | null): CandidateSkill[] {
  if (!kb) return [];
  const raw = (kb.skills?.skills ?? []) as Array<Record<string, unknown>>;
  return raw.map((s, i) => ({
    id: String(s.id ?? `SKILL-${i}`),
    name: String(s.name ?? ""),
    verified: Boolean(s.verified),
    disclosure: String(s.disclosure ?? "undetermined"),
  }));
}

/** Public, verified candidate skills — the safe set for recommendations. */
export function publicCandidateSkills(kb: CandidateKB | null): CandidateSkill[] {
  return extractCandidateSkills(kb).filter(
    (s) => s.verified && s.disclosure === "public",
  );
}

// ---------------------------------------------------------------------------
// Fit pre-scoring
// ---------------------------------------------------------------------------

export type FitBucket = "recommended" | "review" | "low";

export interface FitReason {
  skill: string;
  matched: boolean;
  required: boolean;
}

export interface FitAssessment {
  score: number;
  bucket: FitBucket;
  matched: string[];
  missing: string[];
  reasons: FitReason[];
  derived: boolean; // skills inferred from description rather than structured
}

function deriveSkillsFromText(text: string, candidateSkills: CandidateSkill[]): string[] {
  const lower = norm(text);
  const found = new Set<string>();
  for (const skill of candidateSkills) {
    if (skill.name && lower.includes(norm(skill.name))) found.add(skill.name);
  }
  for (const key of SKILL_KEYS) {
    if (lower.includes(key)) found.add(key);
  }
  return Array.from(found);
}

export function classifyFit(score: number): FitBucket {
  if (score >= 70) return "recommended";
  if (score >= 45) return "review";
  return "low";
}

/**
 * Deterministic, explainable pre-score of a job against candidate skills.
 * This runs client-side so the entire feed can be ranked without evaluating
 * every job through the backend. Full evaluation remains available on demand.
 */
export function preScoreFit(
  job: JobPosting,
  candidateSkills: CandidateSkill[],
): FitAssessment {
  let required = (job.required_skills ?? []).filter(Boolean) as string[];
  const preferred = (job.preferred_skills ?? []).filter(Boolean) as string[];
  let derived = false;

  if (required.length === 0 && preferred.length === 0) {
    const inferred = deriveSkillsFromText(
      `${job.title} ${job.job_description}`,
      candidateSkills,
    );
    required = inferred;
    derived = true;
  }

  const candidateNames = candidateSkills.map((s) => s.name).filter(Boolean);

  let totalWeight = 0;
  let matchedWeight = 0;
  const matched: string[] = [];
  const missing: string[] = [];
  const reasons: FitReason[] = [];

  const consider = (skill: string, weight: number, isRequired: boolean) => {
    totalWeight += weight;
    const hit = candidateNames.some((cn) => skillsMatch(skill, cn));
    if (hit) {
      matchedWeight += weight;
      matched.push(skill);
    } else {
      missing.push(skill);
    }
    reasons.push({ skill, matched: hit, required: isRequired });
  };

  required.forEach((s) => consider(s, 1, true));
  preferred.forEach((s) => consider(s, 0.5, false));

  const score = totalWeight > 0 ? (100 * matchedWeight) / totalWeight : 50;

  return {
    score: Math.round(score),
    bucket: classifyFit(score),
    matched,
    missing,
    reasons,
    derived,
  };
}

// ---------------------------------------------------------------------------
// Natural-language intent parsing
// ---------------------------------------------------------------------------

const LOCATIONS = [
  "uae",
  "dubai",
  "abu dhabi",
  "united arab emirates",
  "usa",
  "united states",
  "us",
  "uk",
  "united kingdom",
  "london",
  "canada",
  "toronto",
  "vancouver",
  "india",
  "bangalore",
  "bengaluru",
  "hyderabad",
  "pune",
  "berlin",
  "germany",
  "amsterdam",
  "netherlands",
  "singapore",
  "sydney",
  "australia",
];

const ROLE_PHRASES = [
  "ai engineer",
  "ml engineer",
  "machine learning engineer",
  "generative ai engineer",
  "software engineer",
  "data scientist",
  "data engineer",
  "backend engineer",
  "frontend engineer",
  "full stack engineer",
  "devops engineer",
];

export interface ParsedIntent {
  raw: string;
  roles: string[];
  locations: string[];
  skills: string[];
  workMode: string | null;
  cleanQuery: string;
}

export function parseIntent(query: string): ParsedIntent {
  const raw = query.trim();
  const lower = norm(raw);

  const roles = ROLE_PHRASES.filter((r) => lower.includes(r));
  const locations = LOCATIONS.filter((l) => lower.includes(l));

  const skills = [...SKILL_KEYS, ...SKILL_ALIAS_VALUES].filter((s) =>
    lower.includes(s),
  );

  let workMode: string | null = null;
  if (/\bremote\b/.test(lower)) workMode = "remote";
  else if (/\bhybrid\b/.test(lower)) workMode = "hybrid";
  else if (/\bonsite\b|\bon-site\b/.test(lower)) workMode = "onsite";

  return {
    raw,
    roles: Array.from(new Set(roles)),
    locations: Array.from(new Set(locations)),
    skills: Array.from(new Set(skills)),
    workMode,
    cleanQuery: raw,
  };
}

/** Filter a job list against a parsed intent (client-side). */
export function applyIntent(jobs: JobPosting[], intent: ParsedIntent): JobPosting[] {
  return jobs.filter((job) => {
    const hay = norm(
      `${job.title} ${job.company} ${job.location ?? ""} ${job.job_description}`,
    );
    if (intent.workMode) {
      const wm = norm(job.work_mode ?? "");
      const loc = norm(job.location ?? "");
      if (!(wm.includes(intent.workMode) || loc.includes(intent.workMode))) {
        return false;
      }
    }
    if (intent.locations.length > 0) {
      const loc = norm(job.location ?? "");
      if (!intent.locations.some((l) => loc.includes(l) || hay.includes(l))) {
        return false;
      }
    }
    if (intent.roles.length > 0) {
      if (!intent.roles.some((r) => norm(job.title).includes(r))) return false;
    }
    return true;
  });
}

// ---------------------------------------------------------------------------
// Action center
// ---------------------------------------------------------------------------

export type ActionKind =
  | "review-documents"
  | "submit-application"
  | "approve-application"
  | "review-opportunity";

export interface ActionItem {
  id: string;
  kind: ActionKind;
  priority: number; // lower = more urgent
  title: string;
  detail: string;
  href: string;
  count: number;
}

export function buildActionItems(input: {
  documents: GeneratedDocument[];
  applications: Application[];
  jobs: JobPosting[];
  recommendedJobIds: number[];
}): ActionItem[] {
  const { documents, applications, jobs, recommendedJobIds } = input;
  const items: ActionItem[] = [];

  const drafts = documents.filter((d) => d.status === "draft");
  if (drafts.length > 0) {
    items.push({
      id: "drafts",
      kind: "review-documents",
      priority: 1,
      title: `${drafts.length} document${drafts.length > 1 ? "s" : ""} awaiting your review`,
      detail:
        "The agent drafted tailored documents. Review, edit, and approve them.",
      href: "/documents",
      count: drafts.length,
    });
  }

  const readyToSubmit = applications.filter((a) => a.status === "Approved");
  if (readyToSubmit.length > 0) {
    items.push({
      id: "ready",
      kind: "submit-application",
      priority: 1,
      title: `${readyToSubmit.length} application${readyToSubmit.length > 1 ? "s" : ""} ready to submit`,
      detail: "Run a dry run, then submit. The agent never submits silently.",
      href: "/applications",
      count: readyToSubmit.length,
    });
  }

  const needApproval = applications.filter((a) => a.status === "Matched");
  if (needApproval.length > 0) {
    items.push({
      id: "need-approval",
      kind: "approve-application",
      priority: 2,
      title: `${needApproval.length} match${needApproval.length > 1 ? "es" : ""} need document approval`,
      detail: "Approve a resume to move these applications forward.",
      href: "/applications",
      count: needApproval.length,
    });
  }

  const tracked = new Set(applications.map((a) => a.job_posting_id));
  const untrackedRecommended = recommendedJobIds.filter((id) => !tracked.has(id));
  if (untrackedRecommended.length > 0) {
    const job = jobs.find((j) => j.id === untrackedRecommended[0]);
    items.push({
      id: "recommended",
      kind: "review-opportunity",
      priority: 2,
      title: `${untrackedRecommended.length} recommended opportunit${
        untrackedRecommended.length > 1 ? "ies" : "y"
      } to review`,
      detail: job
        ? `Top pick: ${job.title} at ${job.company}.`
        : "Review the highest-fit roles the agent found for you.",
      href: "/opportunities",
      count: untrackedRecommended.length,
    });
  }

  return items.sort((a, b) => a.priority - b.priority);
}

// ---------------------------------------------------------------------------
// Activity timeline
// ---------------------------------------------------------------------------

export type TimelineStage =
  | "discovered"
  | "match"
  | "document"
  | "approval"
  | "application"
  | "error";

export interface TimelineEvent {
  id: string;
  at: string;
  stage: TimelineStage;
  title: string;
  detail?: string;
  href?: string;
}

function push(events: TimelineEvent[], e: TimelineEvent) {
  if (e.at) events.push(e);
}

export function buildTimeline(input: {
  jobs: JobPosting[];
  documents: GeneratedDocument[];
  applications: Application[];
  events: ApplicationEvent[];
}): TimelineEvent[] {
  const { jobs, documents, applications, events } = input;
  const jobById = new Map(jobs.map((j) => [j.id, j]));
  const out: TimelineEvent[] = [];

  for (const job of jobs.slice(0, 25)) {
    push(out, {
      id: `job-${job.id}`,
      at: job.created_at || "",
      stage: "discovered",
      title: `Discovered: ${job.title}`,
      detail: `${job.company} · via ${job.source}`,
      href: "/opportunities",
    });
  }

  for (const doc of documents) {
    const job = jobById.get(doc.job_posting_id);
    push(out, {
      id: `doc-${doc.id}`,
      at: doc.created_at || "",
      stage: "document",
      title: `Prepared ${doc.doc_type.replace("_", " ")}`,
      detail: job ? `For ${job.title} at ${job.company}` : `Job #${doc.job_posting_id}`,
      href: "/documents",
    });
  }

  for (const app of applications) {
    const job = jobById.get(app.job_posting_id);
    push(out, {
      id: `app-${app.id}`,
      at: app.created_at || "",
      stage: "application",
      title: `Tracking application`,
      detail: job ? `${job.title} at ${job.company}` : `Job #${app.job_posting_id}`,
      href: "/applications",
    });
  }

  for (const ev of events) {
    const stage: TimelineStage =
      ev.to_status === "Applied"
        ? "application"
        : ev.to_status === "Approved"
          ? "approval"
          : ev.to_status === "Rejected"
            ? "error"
            : "match";
    push(out, {
      id: `ev-${ev.id}`,
      at: ev.created_at || "",
      stage,
      title: `${ev.from_status ? `${ev.from_status} → ` : ""}${ev.to_status}`,
      detail: ev.reason || `by ${ev.actor}`,
      href: "/applications",
    });
  }

  return out
    .filter((e) => !Number.isNaN(Date.parse(e.at)))
    .sort((a, b) => Date.parse(b.at) - Date.parse(a.at))
    .slice(0, 60);
}

// ---------------------------------------------------------------------------
// Time formatting
// ---------------------------------------------------------------------------

export function relativeTime(iso?: string | null): string {
  if (!iso) return "";
  const then = Date.parse(iso);
  if (Number.isNaN(then)) return "";
  const diff = Date.now() - then;
  const mins = Math.round(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(then).toLocaleDateString();
}

export function isToday(iso?: string | null): boolean {
  if (!iso) return false;
  const d = new Date(iso);
  const now = new Date();
  return (
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate()
  );
}
