// Types mirroring the backend API schemas.

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface User {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
  profile_data?: string | null;
  created_at?: string | null;
}

export interface JobPosting {
  id: number;
  title: string;
  company: string;
  location: string | null;
  job_description: string;
  url: string;
  source: string;
  source_job_id?: string | null;
  application_url?: string | null;
  work_mode?: string | null;
  posted_date?: string | null;
  closing_date?: string | null;
  experience_requirement?: string | null;
  education_requirement?: string | null;
  required_skills?: string[] | null;
  preferred_skills?: string[] | null;
  eligibility?: string | null;
  compensation?: string | null;
  internship_information?: string | null;
  created_at?: string | null;
}

export interface JobPostingList {
  items: JobPosting[];
  total: number;
  limit: number;
  offset: number;
}

export type SkillMatchStatus =
  | "VERIFIED_MATCH"
  | "PARTIAL_MATCH"
  | "NO_VERIFIED_EVIDENCE"
  | "UNCERTAIN"
  | "NOT_APPLICABLE";

export interface SkillMatch {
  skill: string;
  status: SkillMatchStatus;
  rationale?: string | null;
}

export interface EvaluationResult {
  job_id: string;
  fit_score: number | null;
  priority: string | null;
  recommendation: string | null;
  technical_match?: number | null;
  evidence_quality?: number | null;
  matched_skills: SkillMatch[];
  partial_skills: SkillMatch[];
  missing_skills: SkillMatch[];
  strengths: string[];
  gaps: string[];
  risks: string[];
  eligibility?: { status: string; rationale?: string | null } | null;
  role_match?: { status: string; matched_target_role?: string | null } | null;
}

export type DocumentType = "resume" | "cover_letter";
export type DocumentStatus = "draft" | "approved" | "rejected";

export interface GeneratedDocument {
  id: number;
  user_id: number;
  job_posting_id: number;
  doc_type: DocumentType;
  status: DocumentStatus;
  version: number;
  content: string;
  meta?: Record<string, unknown> | null;
  used_claim_ids?: string[] | null;
  storage_key?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface DocumentList {
  items: GeneratedDocument[];
  total: number;
}

export type ApplicationStatusType =
  | "Discovered"
  | "Matched"
  | "Approved"
  | "Applied"
  | "Rejected";

export interface Application {
  id: number;
  user_id: number;
  job_posting_id: number;
  status: ApplicationStatusType;
  match_score?: number | null;
  tailored_resume_s3_key?: string | null;
  cover_letter_s3_key?: string | null;
  approved_at?: string | null;
  applied_at?: string | null;
  rejected_at?: string | null;
  last_error?: string | null;
  notes?: string | null;
  created_at?: string | null;
}

export interface ApplicationList {
  items: Application[];
  total: number;
}

export interface ApplicationEvent {
  id: number;
  application_id: number;
  from_status?: string | null;
  to_status: string;
  actor: string;
  reason?: string | null;
  idempotency_key?: string | null;
  event_meta?: Record<string, unknown> | null;
  created_at?: string | null;
}

export interface ApplicationSubmitResponse {
  success: boolean;
  dry_run: boolean;
  ats: string;
  apply_url: string;
  fields_filled: Record<string, string>;
  evidence_paths: string[];
  message: string;
  error?: string | null;
  application_id: number;
  application_status: ApplicationStatusType;
}

export interface CandidateKB {
  profile: {
    candidate_id: string;
    full_name: string;
    email?: string | null;
    target_roles: string[];
    education: {
      degree: string;
      field_of_study: string;
      institution?: string | null;
      graduation_year?: number | null;
    };
    work_authorization?: {
      authorized_locations: string[];
      requires_visa_sponsorship: boolean;
    };
  };
  skills: { skills: unknown[] };
  claims: { claims: unknown[] };
  experience: { work_experience: unknown[]; projects: unknown[] };
  preferences: Record<string, unknown>;
}

export interface CandidateKBResponse {
  version: number;
  is_active: boolean;
  change_note?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  data: CandidateKB;
}
