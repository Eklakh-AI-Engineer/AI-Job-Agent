// Canonical CandidateKB (de)serialization for the Profile editor.
//
// The backend CandidateKB schema nests collections in mappings, and each
// entry is a full record object:
//
//   skills:     { skills: [SkillRecord, ...] }
//   claims:     { claims: [ClaimRecord, ...] }
//   experience: { work_experience: [WorkExperienceRecord, ...],
//                 projects: [ProjectRecord, ...] }
//   preferences:{ ... }
//
// The editor keeps an "advanced" JSON blob for these collections. These
// helpers guarantee the blob is emitted in the canonical shape:
//   - bare arrays are wrapped in the correct mapping,
//   - bare strings are coerced into the exact record schema the backend
//     expects (e.g. "Python" -> SkillRecord),
//   - already-canonical record objects are preserved unchanged.

import type { CandidateKB } from "./types";

type AnyRecord = Record<string, unknown>;

const DISCLOSURE_UNDETERMINED = "undetermined";

function isPlainObject(value: unknown): value is AnyRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function asRecord(value: unknown): AnyRecord {
  return isPlainObject(value) ? value : {};
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

/** Allocate a unique id within a list, avoiding collisions with user ids. */
function allocateId(used: Set<string>, prefix: string): string {
  let n = 1;
  let id = `${prefix}-${n}`;
  while (used.has(id)) {
    n += 1;
    id = `${prefix}-${n}`;
  }
  used.add(id);
  return id;
}

/** Seed the used-id set from the canonical objects already in the list. */
function collectIds(list: unknown[]): Set<string> {
  const used = new Set<string>();
  for (const item of list) {
    if (isPlainObject(item) && typeof item.id === "string" && item.id) {
      used.add(item.id);
    }
  }
  return used;
}

// ---------------------------------------------------------------------------
// Record coercion
// ---------------------------------------------------------------------------

function coerceSkill(item: unknown, used: Set<string>): unknown {
  if (typeof item === "string") {
    const name = item.trim();
    return {
      id: allocateId(used, "SKILL-AUTO"),
      name,
      category: null,
      verified: false,
      evidence_claims: [],
      disclosure: DISCLOSURE_UNDETERMINED,
      transferable_to: [],
    };
  }
  // Preserve canonical record objects unchanged.
  return item;
}

function coerceClaim(item: unknown, used: Set<string>): unknown {
  if (typeof item === "string") {
    const text = item.trim();
    return {
      id: allocateId(used, "CLAIM-AUTO"),
      title: text,
      statement: text,
      verified: false,
      verification_source: null,
      disclosure: DISCLOSURE_UNDETERMINED,
      associated_skills: [],
    };
  }
  return item;
}

function coerceWorkExperience(item: unknown, used: Set<string>): unknown {
  if (typeof item === "string") {
    const role = item.trim();
    return {
      id: allocateId(used, "EXP-AUTO"),
      role,
      company: "",
      location: null,
      work_mode: null,
      start_date: null,
      end_date: null,
      duration_months: null,
      verified: false,
      disclosure: DISCLOSURE_UNDETERMINED,
      claims: [],
    };
  }
  return item;
}

function coerceProject(item: unknown, used: Set<string>): unknown {
  if (typeof item === "string") {
    const title = item.trim();
    return {
      id: allocateId(used, "PROJ-AUTO"),
      title,
      domain: [],
      skills_used: [],
      description: null,
      verified: false,
      verification_source: null,
      disclosure: DISCLOSURE_UNDETERMINED,
      claims: [],
    };
  }
  return item;
}

function coerceList(
  list: unknown[],
  coerce: (item: unknown, used: Set<string>) => unknown,
): unknown[] {
  const used = collectIds(list);
  return list.map((item) => coerce(item, used));
}

// ---------------------------------------------------------------------------
// Public canonicalizers
// ---------------------------------------------------------------------------

export function canonicalizeSkills(input: unknown): { skills: unknown[] } {
  const list = Array.isArray(input) ? input : asArray(asRecord(input).skills);
  return { skills: coerceList(list, coerceSkill) };
}

export function canonicalizeClaims(input: unknown): { claims: unknown[] } {
  const list = Array.isArray(input) ? input : asArray(asRecord(input).claims);
  return { claims: coerceList(list, coerceClaim) };
}

export function canonicalizeExperience(input: unknown): {
  work_experience: unknown[];
  projects: unknown[];
} {
  // A bare array is treated as a list of work experiences.
  const rec = Array.isArray(input) ? {} : asRecord(input);
  const workRaw = Array.isArray(input)
    ? input
    : asArray(rec.work_experience);
  return {
    work_experience: coerceList(workRaw, coerceWorkExperience),
    projects: coerceList(asArray(rec.projects), coerceProject),
  };
}

export function canonicalizePreferences(input: unknown): Record<string, unknown> {
  return asRecord(input);
}

// ---------------------------------------------------------------------------
// Editor state <-> KB
// ---------------------------------------------------------------------------

export interface ProfileDraft {
  candidateId: string;
  fullName: string;
  email: string;
  targetRoles: string[];
  degree: string;
  fieldOfStudy: string;
  institution: string;
  graduationYear: string;
  authorizedLocations: string[];
  requiresVisa: boolean;
}

/** Build a canonical, backend-valid CandidateKB from editor state. */
export function buildCandidateKB(
  profile: ProfileDraft,
  advanced: unknown,
): CandidateKB {
  const adv = asRecord(advanced);
  return {
    profile: {
      candidate_id: profile.candidateId,
      full_name: profile.fullName,
      email: profile.email || null,
      target_roles: profile.targetRoles,
      education: {
        degree: profile.degree,
        field_of_study: profile.fieldOfStudy,
        institution: profile.institution || null,
        graduation_year: profile.graduationYear
          ? Number(profile.graduationYear)
          : null,
      },
      work_authorization: {
        authorized_locations: profile.authorizedLocations,
        requires_visa_sponsorship: profile.requiresVisa,
      },
    },
    skills: canonicalizeSkills(adv.skills) as CandidateKB["skills"],
    claims: canonicalizeClaims(adv.claims) as CandidateKB["claims"],
    experience: canonicalizeExperience(adv.experience) as CandidateKB["experience"],
    preferences: canonicalizePreferences(adv.preferences),
  };
}

/** Serialize a KB's advanced collections into canonical JSON for the editor. */
export function serializeAdvanced(kb: CandidateKB): string {
  return JSON.stringify(
    {
      skills: canonicalizeSkills(kb.skills),
      claims: canonicalizeClaims(kb.claims),
      experience: canonicalizeExperience(kb.experience),
      preferences: canonicalizePreferences(kb.preferences),
    },
    null,
    2,
  );
}

// ===========================================================================
// Structured profile builder: form model <-> canonical CandidateKB
// ===========================================================================

export const APPROVED_TARGET_ROLES = [
  "AI Engineer",
  "ML Engineer",
  "Generative AI Engineer",
  "Software Engineer",
  "Data Scientist",
] as const;

export const WORK_MODES = ["remote", "hybrid", "onsite"] as const;

/** Prefix used for claims that store a work experience's description. */
const EXP_CLAIM_PREFIX = "EXP-CLAIM-";

export interface SkillForm {
  id: string;
  name: string;
  verified: boolean;
  disclosure: string;
}

export interface ExperienceForm {
  id: string;
  role: string;
  company: string;
  location: string;
  workMode: string;
  startDate: string;
  endDate: string;
  description: string;
}

export interface ProjectForm {
  id: string;
  title: string;
  skills: string[];
  description: string;
  url: string;
}

export interface ClaimForm {
  id: string;
  text: string;
  relatedSkills: string[];
  disclosure: string;
}

export interface PreferencesForm {
  workModes: string[];
  preferredLocations: string[];
  authorizedLocations: string[];
  willingToRelocate: boolean;
  requiresVisaSponsorship: boolean;
  compensationMin: string;
  compensationCurrency: string;
  excludedCompanies: string[];
  excludedDomains: string[];
}

export interface ProfileForm {
  candidateId: string;
  fullName: string;
  email: string;
  degree: string;
  fieldOfStudy: string;
  institution: string;
  graduationYear: string;
  targetRoles: string[];
  skills: SkillForm[];
  experience: ExperienceForm[];
  projects: ProjectForm[];
  claims: ClaimForm[];
  preferences: PreferencesForm;
}

export function emptyProfileForm(): ProfileForm {
  return {
    candidateId: "candidate-1",
    fullName: "",
    email: "",
    degree: "",
    fieldOfStudy: "",
    institution: "",
    graduationYear: "",
    targetRoles: [],
    skills: [],
    experience: [],
    projects: [],
    claims: [],
    preferences: {
      workModes: [],
      preferredLocations: [],
      authorizedLocations: [],
      willingToRelocate: false,
      requiresVisaSponsorship: false,
      compensationMin: "",
      compensationCurrency: "USD",
      excludedCompanies: [],
      excludedDomains: [],
    },
  };
}

// --- small helpers ---

function ensureId(provided: string | undefined, used: Set<string>, prefix: string): string {
  const candidate = (provided || "").trim();
  if (candidate && !used.has(candidate)) {
    used.add(candidate);
    return candidate;
  }
  return allocateId(used, prefix);
}

function deriveClaimTitle(text: string): string {
  const firstLine = (text || "").trim().split("\n")[0];
  const firstSentence = firstLine.split(/[.!?]/)[0].trim();
  const title = (firstSentence || firstLine || "Achievement").slice(0, 80);
  return title || "Achievement";
}

function toStrArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((v): v is string => typeof v === "string") : [];
}

// --- form -> canonical KB ---

export function formToCandidateKB(form: ProfileForm): CandidateKB {
  const usedSkillIds = new Set<string>();
  const usedClaimIds = new Set<string>();
  const usedExpIds = new Set<string>();
  const usedProjIds = new Set<string>();

  const skills = form.skills
    .filter((s) => s.name.trim())
    .map((s) => ({
      id: ensureId(s.id, usedSkillIds, "SKILL"),
      name: s.name.trim(),
      category: null,
      verified: Boolean(s.verified),
      evidence_claims: [] as string[],
      disclosure: s.disclosure || "public",
      transferable_to: [] as string[],
    }));

  const claims: AnyRecord[] = [];
  for (const c of form.claims) {
    if (!c.text.trim()) continue;
    claims.push({
      id: ensureId(c.id, usedClaimIds, "CLAIM"),
      title: deriveClaimTitle(c.text),
      statement: c.text.trim(),
      verified: false,
      verification_source: null,
      disclosure: c.disclosure || "public",
      associated_skills: c.relatedSkills.filter(Boolean),
    });
  }

  const experience = form.experience.map((e) => {
    const id = ensureId(e.id, usedExpIds, "EXP");
    const claimIds: string[] = [];
    if (e.description.trim()) {
      const cid = `${EXP_CLAIM_PREFIX}${id}`;
      usedClaimIds.add(cid);
      claims.push({
        id: cid,
        title: `${e.role || "Experience"}${e.company ? ` @ ${e.company}` : ""}`,
        statement: e.description.trim(),
        verified: false,
        verification_source: null,
        disclosure: "public",
        associated_skills: [],
      });
      claimIds.push(cid);
    }
    return {
      id,
      role: e.role.trim(),
      company: e.company.trim(),
      location: e.location.trim() || null,
      work_mode: e.workMode || null,
      start_date: e.startDate.trim() || null,
      end_date: e.endDate.trim() || null,
      duration_months: null,
      verified: false,
      disclosure: "public",
      claims: claimIds,
    };
  });

  const projects = form.projects
    .filter((p) => p.title.trim())
    .map((p) => ({
      id: ensureId(p.id, usedProjIds, "PROJ"),
      title: p.title.trim(),
      domain: [] as string[],
      skills_used: p.skills.filter(Boolean),
      description: p.description.trim() || null,
      verified: false,
      verification_source: p.url.trim() || null,
      disclosure: "public",
      claims: [] as string[],
    }));

  const approvedRoles = form.targetRoles.filter((r) =>
    (APPROVED_TARGET_ROLES as readonly string[]).includes(r),
  );

  const prefs = form.preferences;
  const compensation =
    prefs.compensationMin.trim() !== ""
      ? {
          minimum_annual: Number(prefs.compensationMin),
          currency: prefs.compensationCurrency.trim() || "USD",
        }
      : null;

  return {
    profile: {
      candidate_id: form.candidateId || "candidate-1",
      full_name: form.fullName.trim(),
      email: form.email.trim() || null,
      target_roles: approvedRoles,
      education: {
        degree: form.degree.trim(),
        field_of_study: form.fieldOfStudy.trim(),
        institution: form.institution.trim() || null,
        graduation_year: form.graduationYear.trim()
          ? Number(form.graduationYear)
          : null,
      },
      work_authorization: {
        authorized_locations: prefs.authorizedLocations.filter(Boolean),
        requires_visa_sponsorship: prefs.requiresVisaSponsorship,
      },
    },
    skills: { skills } as CandidateKB["skills"],
    claims: { claims } as CandidateKB["claims"],
    experience: { work_experience: experience, projects } as CandidateKB["experience"],
    preferences: {
      preferred_work_modes: prefs.workModes.filter(Boolean),
      preferred_locations: prefs.preferredLocations.filter(Boolean),
      willing_to_relocate: prefs.willingToRelocate,
      compensation,
      excluded_companies: prefs.excludedCompanies.filter(Boolean),
      excluded_domains: prefs.excludedDomains.filter(Boolean),
    },
  };
}

// --- canonical KB -> form (with legacy migration) ---

export function candidateKBToForm(kb: CandidateKB): ProfileForm {
  const form = emptyProfileForm();
  const profile = asRecord(kb.profile);
  const education = asRecord(profile.education);
  const workAuth = asRecord(profile.work_authorization);

  form.candidateId = String(profile.candidate_id || "candidate-1");
  form.fullName = String(profile.full_name || "");
  form.email = String(profile.email || "");
  form.degree = String(education.degree || "");
  form.fieldOfStudy = String(education.field_of_study || "");
  form.institution = String(education.institution || "");
  form.graduationYear = education.graduation_year
    ? String(education.graduation_year)
    : "";
  form.targetRoles = toStrArray(profile.target_roles);

  // --- skills (migrate bare strings) ---
  const rawSkills = asArray(asRecord(kb.skills).skills);
  form.skills = rawSkills.map((item, i) => {
    if (typeof item === "string") {
      return {
        id: `SKILL-${i + 1}`,
        name: item,
        verified: false,
        disclosure: "public",
      };
    }
    const rec = asRecord(item);
    return {
      id: String(rec.id || `SKILL-${i + 1}`),
      name: String(rec.name || ""),
      verified: Boolean(rec.verified),
      disclosure: String(rec.disclosure || "public"),
    };
  });

  // --- claims: split experience-descriptions from standalone claims ---
  const rawClaims = asArray(asRecord(kb.claims).claims);
  const claimById = new Map<string, AnyRecord>();
  for (const item of rawClaims) {
    if (isPlainObject(item) && typeof item.id === "string") {
      claimById.set(item.id, item);
    }
  }

  form.claims = rawClaims
    .map((item, i) => {
      if (typeof item === "string") {
        return {
          id: `CLAIM-${i + 1}`,
          text: item,
          relatedSkills: [] as string[],
          disclosure: "public",
        };
      }
      const rec = asRecord(item);
      return {
        id: String(rec.id || `CLAIM-${i + 1}`),
        text: String(rec.statement || rec.title || ""),
        relatedSkills: toStrArray(rec.associated_skills),
        disclosure: String(rec.disclosure || "public"),
      };
    })
    .filter((c) => !c.id.startsWith(EXP_CLAIM_PREFIX));

  // --- experience ---
  const rawExp = asArray(asRecord(kb.experience).work_experience);
  form.experience = rawExp.map((item, i) => {
    const rec = asRecord(item);
    const description = toStrArray(rec.claims)
      .filter((cid) => cid.startsWith(EXP_CLAIM_PREFIX))
      .map((cid) => String(claimById.get(cid)?.statement || ""))
      .filter(Boolean)
      .join("\n\n");
    return {
      id: String(rec.id || `EXP-${i + 1}`),
      role: String(rec.role || ""),
      company: String(rec.company || ""),
      location: rec.location ? String(rec.location) : "",
      workMode: rec.work_mode ? String(rec.work_mode) : "",
      startDate: rec.start_date ? String(rec.start_date) : "",
      endDate: rec.end_date ? String(rec.end_date) : "",
      description,
    };
  });

  // --- projects ---
  const rawProj = asArray(asRecord(kb.experience).projects);
  form.projects = rawProj.map((item, i) => {
    const rec = asRecord(item);
    return {
      id: String(rec.id || `PROJ-${i + 1}`),
      title: String(rec.title || ""),
      skills: toStrArray(rec.skills_used),
      description: rec.description ? String(rec.description) : "",
      url: rec.verification_source ? String(rec.verification_source) : "",
    };
  });

  // --- preferences ---
  const prefs = asRecord(kb.preferences);
  const comp = asRecord(prefs.compensation);
  form.preferences = {
    workModes: toStrArray(prefs.preferred_work_modes),
    preferredLocations: toStrArray(prefs.preferred_locations),
    authorizedLocations: toStrArray(workAuth.authorized_locations),
    willingToRelocate: Boolean(prefs.willing_to_relocate),
    requiresVisaSponsorship: Boolean(workAuth.requires_visa_sponsorship),
    compensationMin:
      comp.minimum_annual !== undefined && comp.minimum_annual !== null
        ? String(comp.minimum_annual)
        : "",
    compensationCurrency: comp.currency ? String(comp.currency) : "USD",
    excludedCompanies: toStrArray(prefs.excluded_companies),
    excludedDomains: toStrArray(prefs.excluded_domains),
  };

  return form;
}

// --- form validation (inline UX) ---

export interface ProfileFormErrors {
  fullName?: string;
  email?: string;
  targetRoles?: string;
  graduationYear?: string;
  experience?: string;
  compensation?: string;
}

export function validateProfileForm(form: ProfileForm): ProfileFormErrors {
  const errors: ProfileFormErrors = {};
  if (!form.fullName.trim()) errors.fullName = "Full name is required.";
  if (form.email.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) {
    errors.email = "Enter a valid email address.";
  }
  if (form.targetRoles.length === 0) {
    errors.targetRoles = "Select at least one target role.";
  } else if (
    !form.targetRoles.some((r) =>
      (APPROVED_TARGET_ROLES as readonly string[]).includes(r),
    )
  ) {
    errors.targetRoles = "Select at least one supported role.";
  }
  if (form.graduationYear.trim() && Number.isNaN(Number(form.graduationYear))) {
    errors.graduationYear = "Graduation year must be a number.";
  }
  if (
    form.preferences.compensationMin.trim() &&
    Number.isNaN(Number(form.preferences.compensationMin))
  ) {
    errors.compensation = "Compensation must be a number.";
  }
  return errors;
}
