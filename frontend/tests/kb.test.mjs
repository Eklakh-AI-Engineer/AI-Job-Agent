// Regression tests for canonical CandidateKB serialization.
//
// Run with:  node --test tests/kb.test.mjs
//
// Node 24 runs the imported .ts module via built-in type stripping.

import test from "node:test";
import assert from "node:assert/strict";
import {
  buildCandidateKB,
  canonicalizeClaims,
  canonicalizeExperience,
  canonicalizePreferences,
  canonicalizeSkills,
  serializeAdvanced,
} from "../src/lib/kb.ts";
import {
  APPROVED_TARGET_ROLES,
  candidateKBToForm,
  emptyProfileForm,
  formToCandidateKB,
  validateProfileForm,
} from "../src/lib/kb.ts";

const PROFILE = {
  candidateId: "candidate-1",
  fullName: "Ada Lovelace",
  email: "ada@example.com",
  targetRoles: ["AI Engineer"],
  degree: "B.S.",
  fieldOfStudy: "Computer Science",
  institution: "MIT",
  graduationYear: "2024",
  authorizedLocations: ["US"],
  requiresVisa: false,
};

test("canonicalizeSkills wraps a bare array in {skills: [...]}", () => {
  const skills = [{ id: "SKILL-1", name: "Python" }];
  assert.deepEqual(canonicalizeSkills(skills), { skills });
});

test("canonicalizeSkills preserves an already-canonical mapping", () => {
  const value = { skills: [{ id: "SKILL-1", name: "Python" }] };
  assert.deepEqual(canonicalizeSkills(value), value);
});

test("canonicalizeSkills tolerates junk", () => {
  assert.deepEqual(canonicalizeSkills("nonsense"), { skills: [] });
  assert.deepEqual(canonicalizeSkills(null), { skills: [] });
  assert.deepEqual(canonicalizeSkills(undefined), { skills: [] });
});

test("canonicalizeClaims wraps a bare array in {claims: [...]}", () => {
  const claims = [{ id: "CLAIM-1" }];
  assert.deepEqual(canonicalizeClaims(claims), { claims });
});

test("canonicalizeClaims preserves an already-canonical mapping", () => {
  const value = { claims: [{ id: "CLAIM-1" }] };
  assert.deepEqual(canonicalizeClaims(value), value);
});

test("canonicalizeExperience normalizes partial/missing shapes", () => {
  assert.deepEqual(canonicalizeExperience(undefined), {
    work_experience: [],
    projects: [],
  });
  assert.deepEqual(
    canonicalizeExperience({ work_experience: [{ id: "EXP-1" }] }),
    { work_experience: [{ id: "EXP-1" }], projects: [] },
  );
  const full = {
    work_experience: [{ id: "EXP-1" }],
    projects: [{ id: "PROJ-1" }],
  };
  assert.deepEqual(canonicalizeExperience(full), full);
});

test("canonicalizePreferences returns an object", () => {
  assert.deepEqual(canonicalizePreferences({ preferred_work_modes: ["remote"] }), {
    preferred_work_modes: ["remote"],
  });
  assert.deepEqual(canonicalizePreferences("x"), {});
  assert.deepEqual(canonicalizePreferences([1, 2]), {});
});

test("buildCandidateKB fixes legacy array-shaped advanced collections", () => {
  // This is the exact shape the buggy editor previously sent.
  const legacyAdvanced = {
    skills: [{ id: "SKILL-1", name: "Python" }],
    claims: [{ id: "CLAIM-1" }],
    experience: { work_experience: [], projects: [] },
    preferences: {},
  };

  const kb = buildCandidateKB(PROFILE, legacyAdvanced);

  // Must be canonical mappings, NOT bare arrays.
  assert.ok(!Array.isArray(kb.skills), "skills must be a mapping");
  assert.deepEqual(kb.skills, { skills: [{ id: "SKILL-1", name: "Python" }] });
  assert.ok(!Array.isArray(kb.claims), "claims must be a mapping");
  assert.deepEqual(kb.claims, { claims: [{ id: "CLAIM-1" }] });
  assert.deepEqual(kb.experience, { work_experience: [], projects: [] });
  assert.deepEqual(kb.preferences, {});
});

test("buildCandidateKB preserves canonical advanced collections", () => {
  const advanced = {
    skills: { skills: [{ id: "SKILL-1", name: "Python" }] },
    claims: { claims: [{ id: "CLAIM-1" }] },
    experience: { work_experience: [], projects: [{ id: "PROJ-1" }] },
    preferences: { preferred_locations: ["Remote"] },
  };
  const kb = buildCandidateKB(PROFILE, advanced);
  assert.deepEqual(kb.skills, advanced.skills);
  assert.deepEqual(kb.claims, advanced.claims);
  assert.deepEqual(kb.experience, advanced.experience);
  assert.deepEqual(kb.preferences, advanced.preferences);
});

test("profile mapping: graduation year coerces, blanks become null", () => {
  const kb = buildCandidateKB(PROFILE, {});
  assert.equal(kb.profile.education.graduation_year, 2024);
  assert.equal(kb.profile.email, "ada@example.com");

  const blank = buildCandidateKB(
    { ...PROFILE, email: "", graduationYear: "", institution: "" },
    {},
  );
  assert.equal(blank.profile.education.graduation_year, null);
  assert.equal(blank.profile.email, null);
  assert.equal(blank.profile.education.institution, null);
});

test("serializeAdvanced produces canonical mappings that round-trip", () => {
  const kb = {
    profile: {
      candidate_id: "candidate-1",
      full_name: "Ada",
      email: "ada@example.com",
      target_roles: ["AI Engineer"],
      education: { degree: "B.S.", field_of_study: "CS" },
    },
    skills: { skills: [{ id: "SKILL-1", name: "Python" }] },
    claims: { claims: [{ id: "CLAIM-1" }] },
    experience: { work_experience: [], projects: [] },
    preferences: { preferred_locations: ["Remote"] },
  };

  const parsed = JSON.parse(serializeAdvanced(kb));

  // The editor JSON must itself be canonical (mappings, not arrays).
  assert.deepEqual(parsed.skills, kb.skills);
  assert.deepEqual(parsed.claims, kb.claims);
  assert.deepEqual(parsed.experience, kb.experience);

  // Round-trip back through the builder yields the same canonical KB.
  const rebuilt = buildCandidateKB(PROFILE, parsed);
  assert.deepEqual(rebuilt.skills, kb.skills);
  assert.deepEqual(rebuilt.claims, kb.claims);
  assert.deepEqual(rebuilt.experience, kb.experience);
  assert.deepEqual(rebuilt.preferences, kb.preferences);
});

// ---------------------------------------------------------------------------
// String -> record coercion
// ---------------------------------------------------------------------------

test("canonicalizeSkills coerces strings into SkillRecord objects", () => {
  const result = canonicalizeSkills(["Python", "RAG", "LLM"]);
  assert.deepEqual(result, {
    skills: [
      {
        id: "SKILL-AUTO-1",
        name: "Python",
        category: null,
        verified: false,
        evidence_claims: [],
        disclosure: "undetermined",
        transferable_to: [],
      },
      {
        id: "SKILL-AUTO-2",
        name: "RAG",
        category: null,
        verified: false,
        evidence_claims: [],
        disclosure: "undetermined",
        transferable_to: [],
      },
      {
        id: "SKILL-AUTO-3",
        name: "LLM",
        category: null,
        verified: false,
        evidence_claims: [],
        disclosure: "undetermined",
        transferable_to: [],
      },
    ],
  });
});

test("canonicalizeSkills coerces strings inside the {skills: [...]} mapping", () => {
  const result = canonicalizeSkills({ skills: ["Python"] });
  assert.equal(result.skills.length, 1);
  assert.equal(result.skills[0].name, "Python");
  assert.equal(result.skills[0].id, "SKILL-AUTO-1");
});

test("canonicalizeSkills preserves canonical records and avoids id collisions", () => {
  const canonical = { id: "SKILL-AUTO-1", name: "Existing" };
  const result = canonicalizeSkills([canonical, "Python"]);
  // Canonical object preserved unchanged (same reference)
  assert.equal(result.skills[0], canonical);
  // Coerced string must not collide with the existing SKILL-AUTO-1
  assert.equal(result.skills[1].id, "SKILL-AUTO-2");
  assert.equal(result.skills[1].name, "Python");
});

test("canonicalizeSkills gives duplicate strings unique ids", () => {
  const result = canonicalizeSkills(["Python", "Python"]);
  assert.notEqual(result.skills[0].id, result.skills[1].id);
  assert.equal(result.skills[0].name, "Python");
  assert.equal(result.skills[1].name, "Python");
});

test("canonicalizeClaims coerces strings into ClaimRecord objects", () => {
  const result = canonicalizeClaims(["Built a RAG pipeline"]);
  assert.deepEqual(result, {
    claims: [
      {
        id: "CLAIM-AUTO-1",
        title: "Built a RAG pipeline",
        statement: "Built a RAG pipeline",
        verified: false,
        verification_source: null,
        disclosure: "undetermined",
        associated_skills: [],
      },
    ],
  });
});

test("canonicalizeExperience coerces string work experience and projects", () => {
  const result = canonicalizeExperience({
    work_experience: ["ML Intern"],
    projects: ["Vision Model"],
  });
  assert.deepEqual(result, {
    work_experience: [
      {
        id: "EXP-AUTO-1",
        role: "ML Intern",
        company: "",
        location: null,
        work_mode: null,
        start_date: null,
        end_date: null,
        duration_months: null,
        verified: false,
        disclosure: "undetermined",
        claims: [],
      },
    ],
    projects: [
      {
        id: "PROJ-AUTO-1",
        title: "Vision Model",
        domain: [],
        skills_used: [],
        description: null,
        verified: false,
        verification_source: null,
        disclosure: "undetermined",
        claims: [],
      },
    ],
  });
});

test("buildCandidateKB coerces legacy string collections end-to-end", () => {
  const legacyAdvanced = {
    skills: { skills: ["Python", "RAG"] },
    claims: { claims: ["Shipped an LLM feature"] },
    experience: { work_experience: ["ML Intern"], projects: ["Vision Model"] },
    preferences: {},
  };

  const kb = buildCandidateKB(PROFILE, legacyAdvanced);

  assert.equal(kb.skills.skills.length, 2);
  assert.equal(typeof kb.skills.skills[0], "object");
  assert.equal(kb.skills.skills[0].name, "Python");
  assert.equal(kb.claims.claims[0].title, "Shipped an LLM feature");
  assert.equal(kb.claims.claims[0].statement, "Shipped an LLM feature");
  assert.equal(kb.experience.work_experience[0].role, "ML Intern");
  assert.equal(kb.experience.projects[0].title, "Vision Model");
});

test("serializeAdvanced coerces string entries into record objects", () => {
  const kb = {
    profile: {
      candidate_id: "candidate-1",
      full_name: "Ada",
      email: null,
      target_roles: ["AI Engineer"],
      education: { degree: "B.S.", field_of_study: "CS" },
    },
    skills: { skills: ["Python"] },
    claims: { claims: ["Built X"] },
    experience: { work_experience: ["ML Intern"], projects: [] },
    preferences: {},
  };

  const parsed = JSON.parse(serializeAdvanced(kb));
  assert.equal(typeof parsed.skills.skills[0], "object");
  assert.equal(parsed.skills.skills[0].name, "Python");
  assert.equal(parsed.skills.skills[0].verified, false);
  assert.equal(parsed.claims.claims[0].title, "Built X");
  assert.equal(parsed.experience.work_experience[0].role, "ML Intern");
});

test("mixed canonical records and strings keep canonical objects byte-identical", () => {
  const canonicalClaim = {
    id: "CLAIM-1",
    title: "Keep me",
    statement: "Verbatim",
    verified: true,
    disclosure: "public",
    associated_skills: ["Python"],
  };
  const result = canonicalizeClaims([canonicalClaim, "New claim"]);
  assert.deepEqual(result.claims[0], canonicalClaim);
  assert.equal(result.claims[1].title, "New claim");
  assert.notEqual(result.claims[1].id, "CLAIM-1");
});


// ===========================================================================
// Structured profile builder: form <-> canonical CandidateKB
// ===========================================================================

function fullForm() {
  return {
    candidateId: "candidate-1",
    fullName: "Ada Lovelace",
    email: "ada@example.com",
    degree: "B.S.",
    fieldOfStudy: "Computer Science",
    institution: "MIT",
    graduationYear: "2024",
    targetRoles: ["AI Engineer", "ML Engineer"],
    skills: [
      { id: "SKILL-1", name: "Python", verified: true, disclosure: "public" },
      { id: "SKILL-2", name: "RAG", verified: false, disclosure: "public" },
    ],
    experience: [
      {
        id: "EXP-1",
        role: "ML Engineer",
        company: "Acme",
        location: "Remote",
        workMode: "remote",
        startDate: "2023-01",
        endDate: "2024-06",
        description: "Built a RAG pipeline serving 50k queries/month.",
      },
    ],
    projects: [
      {
        id: "PROJ-1",
        title: "Doc Assistant",
        skills: ["Python", "FastAPI"],
        description: "A retrieval-augmented assistant.",
        url: "https://github.com/ada/doc-assistant",
      },
    ],
    claims: [
      {
        id: "CLAIM-1",
        text: "Reduced latency by 40% via caching.",
        relatedSkills: ["Python"],
        disclosure: "public",
      },
    ],
    preferences: {
      workModes: ["remote", "hybrid"],
      preferredLocations: ["Remote", "US"],
      authorizedLocations: ["US"],
      willingToRelocate: true,
      requiresVisaSponsorship: false,
      compensationMin: "150000",
      compensationCurrency: "USD",
      excludedCompanies: ["BadCorp"],
      excludedDomains: ["gambling"],
    },
  };
}

test("formToCandidateKB emits backend-valid skill records", () => {
  const kb = formToCandidateKB(fullForm());
  const skills = kb.skills.skills;
  assert.equal(skills.length, 2);
  assert.equal(skills[0].id, "SKILL-1");
  assert.equal(skills[0].name, "Python");
  assert.equal(skills[0].verified, true);
  assert.equal(skills[0].disclosure, "public");
  assert.deepEqual(skills[0].evidence_claims, []);
  assert.deepEqual(skills[0].transferable_to, []);
  assert.equal(skills[0].category, null);
});

test("formToCandidateKB emits backend-valid claim records", () => {
  const kb = formToCandidateKB(fullForm());
  const standalone = kb.claims.claims.filter(
    (c) => !c.id.startsWith("EXP-CLAIM-"),
  );
  assert.equal(standalone.length, 1);
  assert.equal(standalone[0].statement, "Reduced latency by 40% via caching.");
  assert.deepEqual(standalone[0].associated_skills, ["Python"]);
  assert.equal(standalone[0].disclosure, "public");
  assert.equal(standalone[0].verified, false);
});

test("formToCandidateKB links experience description via a claim", () => {
  const kb = formToCandidateKB(fullForm());
  const exp = kb.experience.work_experience[0];
  assert.equal(exp.id, "EXP-1");
  assert.equal(exp.role, "ML Engineer");
  assert.equal(exp.company, "Acme");
  assert.equal(exp.work_mode, "remote");
  assert.equal(exp.claims.length, 1);
  assert.ok(exp.claims[0].startsWith("EXP-CLAIM-"));

  const linked = kb.claims.claims.find((c) => c.id === exp.claims[0]);
  assert.ok(linked, "linked claim must exist");
  assert.equal(linked.statement, "Built a RAG pipeline serving 50k queries/month.");
});

test("formToCandidateKB emits backend-valid project records", () => {
  const kb = formToCandidateKB(fullForm());
  const proj = kb.experience.projects[0];
  assert.equal(proj.id, "PROJ-1");
  assert.equal(proj.title, "Doc Assistant");
  assert.deepEqual(proj.skills_used, ["Python", "FastAPI"]);
  assert.equal(proj.description, "A retrieval-augmented assistant.");
  assert.equal(proj.verification_source, "https://github.com/ada/doc-assistant");
  assert.deepEqual(proj.claims, []);
});

test("formToCandidateKB emits backend-valid preferences", () => {
  const kb = formToCandidateKB(fullForm());
  assert.deepEqual(kb.preferences.preferred_work_modes, ["remote", "hybrid"]);
  assert.deepEqual(kb.preferences.preferred_locations, ["Remote", "US"]);
  assert.equal(kb.preferences.willing_to_relocate, true);
  assert.deepEqual(kb.preferences.compensation, {
    minimum_annual: 150000,
    currency: "USD",
  });
  assert.deepEqual(kb.preferences.excluded_companies, ["BadCorp"]);
  assert.deepEqual(kb.preferences.excluded_domains, ["gambling"]);
  // visa + authorized locations live on work_authorization
  assert.deepEqual(kb.profile.work_authorization.authorized_locations, ["US"]);
  assert.equal(kb.profile.work_authorization.requires_visa_sponsorship, false);
});

test("formToCandidateKB drops unsupported custom target roles", () => {
  const form = fullForm();
  form.targetRoles = ["AI Engineer", "Applied Scientist"];
  const kb = formToCandidateKB(form);
  assert.deepEqual(kb.profile.target_roles, ["AI Engineer"]);
});

test("form round-trips through the canonical KB", () => {
  const form = fullForm();
  const kb = formToCandidateKB(form);
  const back = candidateKBToForm(kb);
  assert.deepEqual(back.skills, form.skills);
  assert.deepEqual(back.experience, form.experience);
  assert.deepEqual(back.projects, form.projects);
  assert.deepEqual(back.claims, form.claims);
  assert.deepEqual(back.preferences, form.preferences);
  assert.equal(back.fullName, form.fullName);
  assert.deepEqual(back.targetRoles, form.targetRoles);
});

test("load existing KB -> edit -> save -> load again preserves data", () => {
  // 1. Start from a stored canonical KB.
  const storedKB = formToCandidateKB(fullForm());

  // 2. Load into the builder form.
  const loaded = candidateKBToForm(storedKB);
  assert.equal(loaded.skills.length, 2);
  assert.equal(loaded.experience[0].description.includes("RAG pipeline"), true);

  // 3. Edit: add a skill, a claim, and change a preference.
  loaded.skills.push({
    id: "",
    name: "Rust",
    verified: false,
    disclosure: "public",
  });
  loaded.claims.push({
    id: "",
    text: "Shipped a new inference service.",
    relatedSkills: ["Rust"],
    disclosure: "public",
  });
  loaded.preferences.willingToRelocate = false;

  // 4. Save (form -> canonical KB).
  const savedKB = formToCandidateKB(loaded);

  // 5. Load again.
  const reloaded = candidateKBToForm(savedKB);
  const names = reloaded.skills.map((s) => s.name);
  assert.ok(names.includes("Rust"));
  assert.ok(
    reloaded.claims.some(
      (c) => c.text === "Shipped a new inference service.",
    ),
  );
  assert.equal(reloaded.preferences.willingToRelocate, false);
  // Original data still present.
  assert.ok(names.includes("Python"));
  assert.equal(reloaded.experience.length, 1);
});

test("candidateKBToForm migrates legacy string skills and claims", () => {
  const legacyKB = {
    profile: {
      candidate_id: "c",
      full_name: "Legacy",
      email: null,
      target_roles: ["AI Engineer"],
      education: { degree: "B.S.", field_of_study: "CS" },
      work_authorization: { authorized_locations: [], requires_visa_sponsorship: false },
    },
    skills: { skills: ["Python", "RAG"] },
    claims: { claims: ["Built something"] },
    experience: { work_experience: [], projects: [] },
    preferences: {},
  };
  const form = candidateKBToForm(legacyKB);
  assert.deepEqual(
    form.skills.map((s) => s.name),
    ["Python", "RAG"],
  );
  assert.equal(form.claims[0].text, "Built something");
});

test("validateProfileForm flags missing/invalid fields", () => {
  const empty = emptyProfileForm();
  const errors = validateProfileForm(empty);
  assert.ok(errors.fullName);
  assert.ok(errors.targetRoles);

  const bad = fullForm();
  bad.email = "not-an-email";
  bad.graduationYear = "abcd";
  bad.preferences.compensationMin = "lots";
  const badErrors = validateProfileForm(bad);
  assert.ok(badErrors.email);
  assert.ok(badErrors.graduationYear);
  assert.ok(badErrors.compensation);

  assert.deepEqual(validateProfileForm(fullForm()), {});
});

test("validateProfileForm requires at least one supported role", () => {
  const form = fullForm();
  form.targetRoles = ["Applied Scientist"]; // custom only
  const errors = validateProfileForm(form);
  assert.ok(errors.targetRoles);
});
