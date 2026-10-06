// Central API client for the AI Job Agent backend.
//
// All requests go through `apiFetch`, which attaches the bearer token and
// normalises error handling. The token is kept in localStorage for simplicity;
// swap for an httpOnly cookie flow before shipping to production.

import type {
  Application,
  ApplicationEvent,
  ApplicationList,
  ApplicationStatusType,
  ApplicationSubmitResponse,
  CandidateKB,
  CandidateKBResponse,
  DocumentList,
  DocumentType,
  EvaluationResult,
  GeneratedDocument,
  JobPosting,
  JobPostingList,
  TokenResponse,
  User,
} from "./types";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

const TOKEN_KEY = "aja_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

type RequestOptions = {
  method?: string;
  body?: unknown;
  auth?: boolean;
  query?: Record<string, string | number | boolean | undefined | null>;
};

function buildUrl(path: string, query?: RequestOptions["query"]): string {
  const url = new URL(path.startsWith("http") ? path : `${API_URL}${path}`);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, String(value));
      }
    }
  }
  return url.toString();
}

export async function apiFetch<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { method = "GET", body, auth = true, query } = options;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (auth) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(buildUrl(path, query), {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      cache: "no-store",
    });
  } catch (err) {
    throw new ApiError(0, `Network error: ${(err as Error).message}`);
  }

  if (response.status === 401 && auth) {
    clearToken();
  }

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const data = await response.json();
      if (typeof data?.detail === "string") detail = data.detail;
      else if (Array.isArray(data?.detail)) {
        detail = data.detail
          .map((d: { msg?: string }) => d?.msg || JSON.stringify(d))
          .join(", ");
      }
    } catch {
      // ignore body parse errors
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) return undefined as T;
  const text = await response.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

// --- Auth ---
export const authApi = {
  register: (email: string, password: string, full_name?: string) =>
    apiFetch<User>("/api/v1/auth/register", {
      method: "POST",
      auth: false,
      body: { email, password, full_name },
    }),
  login: (email: string, password: string) =>
    apiFetch<TokenResponse>("/api/v1/auth/login", {
      method: "POST",
      auth: false,
      body: { email, password },
    }),
  me: () => apiFetch<User>("/api/v1/users/me"),
  updateMe: (payload: { full_name?: string; profile_data?: string }) =>
    apiFetch<User>("/api/v1/users/me", { method: "PATCH", body: payload }),
};

// --- Jobs ---
export const jobsApi = {
  list: (params?: { limit?: number; offset?: number; company?: string; source?: string }) =>
    apiFetch<JobPostingList>("/api/v1/jobs", { query: params }),
  get: (id: number) => apiFetch<JobPosting>(`/api/v1/jobs/${id}`),
  ingest: (payload: Partial<JobPosting>) =>
    apiFetch<JobPosting>("/api/v1/jobs", { method: "POST", body: payload }),
};

// --- Evaluation ---
export const evaluationApi = {
  evaluate: (jobId: number) =>
    apiFetch<EvaluationResult>(`/api/v1/evaluation/${jobId}`, { method: "POST" }),
};

// --- Semantic search ---
export const searchApi = {
  semantic: (q: string, params?: { limit?: number; threshold?: number }) =>
    apiFetch<JobPostingList>("/api/v1/search/semantic", {
      query: { q, ...params },
    }),
  hybrid: (q: string, params?: { limit?: number; threshold?: number }) =>
    apiFetch<JobPostingList>("/api/v1/search/hybrid", {
      query: { q, ...params },
    }),
};

// --- Candidate KB ---
export const kbApi = {
  get: (includeRestricted = false) =>
    apiFetch<CandidateKBResponse>("/api/v1/profile/kb", {
      query: { include_restricted: includeRestricted },
    }),
  save: (data: CandidateKB, changeNote?: string) =>
    apiFetch<CandidateKBResponse>("/api/v1/profile/kb", {
      method: "PUT",
      body: { data, change_note: changeNote },
    }),
  validate: (data: CandidateKB) =>
    apiFetch<{ valid: boolean; errors: string[]; warnings: string[] }>(
      "/api/v1/profile/kb/validate",
      { method: "POST", body: { data } },
    ),
  remove: () =>
    apiFetch<{ deleted: number }>("/api/v1/profile/kb", { method: "DELETE" }),
};

// --- Documents ---
export const documentsApi = {
  generate: (jobId: number, docType: DocumentType) =>
    apiFetch<GeneratedDocument>("/api/v1/documents/generate", {
      method: "POST",
      body: { job_id: jobId, doc_type: docType, store_artifact: true },
    }),
  list: (params?: { job_id?: number; doc_type?: string; status?: string }) =>
    apiFetch<DocumentList>("/api/v1/documents", { query: params }),
  get: (id: number) => apiFetch<GeneratedDocument>(`/api/v1/documents/${id}`),
  edit: (id: number, content: string) =>
    apiFetch<GeneratedDocument>(`/api/v1/documents/${id}`, {
      method: "PATCH",
      body: { content },
    }),
  setStatus: (id: number, status: string) =>
    apiFetch<GeneratedDocument>(`/api/v1/documents/${id}/status`, {
      method: "POST",
      body: { status },
    }),
  regenerate: (id: number) =>
    apiFetch<GeneratedDocument>(`/api/v1/documents/${id}/regenerate`, {
      method: "POST",
    }),
};

// --- Applications ---
export const applicationsApi = {
  create: (jobId: number, matchScore?: number) =>
    apiFetch<Application>("/api/v1/applications", {
      method: "POST",
      body: { job_id: jobId, match_score: matchScore },
    }),
  list: (status?: ApplicationStatusType) =>
    apiFetch<ApplicationList>("/api/v1/applications", { query: { status } }),
  get: (id: number) => apiFetch<Application>(`/api/v1/applications/${id}`),
  events: (id: number) =>
    apiFetch<{ items: ApplicationEvent[]; total: number }>(
      `/api/v1/applications/${id}/events`,
    ),
  transition: (id: number, toStatus: string, reason?: string, idempotencyKey?: string) =>
    apiFetch<Application>(`/api/v1/applications/${id}/transition`, {
      method: "POST",
      body: { to_status: toStatus, reason, idempotency_key: idempotencyKey },
    }),
  submit: (id: number, dryRun = true) =>
    apiFetch<ApplicationSubmitResponse>(`/api/v1/applications/${id}/submit`, {
      method: "POST",
      body: { dry_run: dryRun },
    }),
};
